"""Bounded immutable report files with transactional owners and crash recovery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
from contextlib import closing
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from types import TracebackType
from typing import Literal
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError

from app.api.v1.schemas.reports import (
    BayesianHistoryReportSource,
    LhsDesignReportSource,
    ReportSourceRef,
)
from app.storage.metadata import metadata_db_path
from app.storage.workspace_archive import WorkspaceBackupError, checked_path

MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_REPORTS_PER_OWNER = 100
MAX_METADATA_BYTES = 65536
ManagedSource = LhsDesignReportSource | BayesianHistoryReportSource
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ADAPTER: TypeAdapter[ReportSourceRef] = TypeAdapter(ReportSourceRef)


class ManagedReportStorageError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ManagedReportArtifact:
    report_id: str
    source_kind: str
    design_version_id: str | None
    study_version_id: str | None
    history_revision_id: str | None
    recommendation_id: str | None
    batch_id: str | None
    source_ref_json: str
    source_ref_sha256: str
    source_payload_sha256: str
    artifact_schema_version: int
    locale: Literal["en", "ko"]
    renderer_id: str
    renderer_version: str
    report_level: Literal["full", "summary"]
    section_manifest_json: str
    artifact_path: str
    sha256: str
    media_type: str
    size_bytes: int
    created_at: str


MANAGED_REPORT_COLUMNS = tuple(field.name for field in fields(ManagedReportArtifact))
_COLUMNS = ", ".join(MANAGED_REPORT_COLUMNS)


def _json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _error(code: str = "managed_report_integrity_invalid") -> ManagedReportStorageError:
    return ManagedReportStorageError(code)


def _uuid(value: str) -> str:
    try:
        if str(UUID(value)) != value:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise _error() from exc
    return value


def _canonical_source(source: ManagedSource) -> str:
    return _json(source.model_dump(mode="json"))


def _parse_source(record: ManagedReportArtifact) -> ManagedSource:
    try:
        if not 2 <= len(record.source_ref_json.encode("utf-8")) <= MAX_METADATA_BYTES:
            raise ValueError
        source = _ADAPTER.validate_json(record.source_ref_json)
        if not isinstance(source, LhsDesignReportSource | BayesianHistoryReportSource):
            raise ValueError
        if (
            _canonical_source(source) != record.source_ref_json
            or _sha(record.source_ref_json.encode("utf-8")) != record.source_ref_sha256
            or source.kind != record.source_kind
            or source.expected_source_sha256 != record.source_payload_sha256
            or _owners(source)
            != (
                record.design_version_id,
                record.study_version_id,
                record.history_revision_id,
                record.recommendation_id,
                record.batch_id,
            )
        ):
            raise ValueError
    except (ValueError, TypeError, ValidationError) as exc:
        raise _error() from exc
    return source


def _owners(source: ManagedSource) -> tuple[str | None, ...]:
    if isinstance(source, LhsDesignReportSource):
        return str(source.design_version_id), None, None, None, None
    attachment = source.attachment
    return (
        None,
        str(source.study_version_id),
        str(source.history_revision_id),
        str(attachment.recommendation_id) if attachment.kind == "recommendation" else None,
        str(attachment.batch_id) if attachment.kind == "batch" else None,
    )


def _validate_record(record: ManagedReportArtifact) -> None:
    for field in fields(record):
        value = getattr(record, field.name)
        if field.name in {"artifact_schema_version", "size_bytes"}:
            if type(value) is not int:
                raise _error()
        elif field.name in {
            "design_version_id",
            "study_version_id",
            "history_revision_id",
            "recommendation_id",
            "batch_id",
        }:
            if value is not None and not isinstance(value, str):
                raise _error()
        elif not isinstance(value, str):
            raise _error()
    _uuid(record.report_id)
    _parse_source(record)
    try:
        if not 2 <= len(record.section_manifest_json.encode("utf-8")) <= MAX_METADATA_BYTES:
            raise ValueError
        sections = json.loads(record.section_manifest_json)
        if not isinstance(sections, list | dict) or _json(sections) != record.section_manifest_json:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise _error() from exc
    if (
        record.artifact_schema_version != 1
        or record.locale not in {"en", "ko"}
        or record.report_level not in {"full", "summary"}
        or not record.renderer_id
        or len(record.renderer_id) > 128
        or not record.renderer_version
        or len(record.renderer_version) > 64
        or record.artifact_path != f"workspaces/reports/{record.report_id}/report.html"
        or not _SHA.fullmatch(record.sha256)
        or record.media_type != "text/html"
        or not 1 <= record.size_bytes <= MAX_REPORT_BYTES
    ):
        raise _error()


def _validate_source(connection: sqlite3.Connection, source: ManagedSource) -> None:
    """CAS immutable identities; the service validates stored payload semantics first."""
    if isinstance(source, LhsDesignReportSource):
        owner = connection.execute(
            "SELECT version.design_sha256, design.method_id "
            "FROM experiment_design_versions version "
            "JOIN experiment_designs design ON design.design_id=version.design_id "
            "WHERE version.design_version_id=? AND version.design_id=?",
            (str(source.design_version_id), str(source.design_id)),
        ).fetchone()
        if owner is None:
            raise _error("managed_report_source_not_found")
        if tuple(owner) != (source.expected_source_sha256, "doe.latin_hypercube"):
            raise _error("managed_report_source_conflict")
        for revision in source.response_revisions:
            row = connection.execute(
                "SELECT response_sha256 FROM experiment_response_revisions "
                "WHERE response_revision_id=? AND design_version_id=?",
                (str(revision.response_revision_id), str(source.design_version_id)),
            ).fetchone()
            if row is None or tuple(row) != (revision.response_revision_sha256,):
                raise _error("managed_report_source_conflict")
        return
    row = connection.execute(
        "SELECT version.definition_sha256, history.observation_history_sha256, study.method_id "
        "FROM bayesian_study_versions version JOIN bayesian_observation_history_revisions history "
        "ON history.study_version_id=version.study_version_id "
        "JOIN bayesian_studies study ON study.study_id=version.study_id "
        "WHERE version.study_version_id=? AND version.study_id=? AND history.history_revision_id=?",
        (str(source.study_version_id), str(source.study_id), str(source.history_revision_id)),
    ).fetchone()
    if row is None:
        raise _error("managed_report_source_not_found")
    if tuple(row) != (
        source.definition_sha256,
        source.expected_source_sha256,
        "doe.bayesian_optimization",
    ):
        raise _error("managed_report_source_conflict")
    attachment = source.attachment
    if attachment.kind == "none":
        return
    table, id_column, attachment_id = (
        ("bayesian_recommendations", "recommendation_id", str(attachment.recommendation_id))
        if attachment.kind == "recommendation"
        else ("bayesian_recommendation_batches", "batch_id", str(attachment.batch_id))
    )
    payload_column = "result_payload_sha256" if attachment.kind == "recommendation" else "NULL"
    row = connection.execute(
        f"SELECT result_sha256, {payload_column}, result_json, "
        f"source_observation_history_sha256, method_id FROM {table} "
        f"WHERE {id_column}=? AND study_version_id=? AND source_history_revision_id=? "
        "AND length(CAST(result_json AS BLOB)) <= ?",
        (
            attachment_id,
            str(source.study_version_id),
            str(source.history_revision_id),
            MAX_REPORT_BYTES,
        ),
    ).fetchone()
    payload_sha = None
    if row is not None:
        try:
            payload_sha = (
                row[1]
                if attachment.kind == "recommendation"
                else json.loads(row[2]).get("result_sha256")
            )
        except (ValueError, AttributeError, TypeError) as exc:
            raise _error("managed_report_source_conflict") from exc
    if (
        row is None
        or row[0] != attachment.result_json_sha256
        or payload_sha != attachment.result_payload_sha256
        or _sha(str(row[2]).encode("utf-8")) != row[0]
        or row[3] != source.expected_source_sha256
        or row[4] != "doe.bayesian_optimization"
    ):
        raise _error("managed_report_source_conflict")


def _safe_path(root: Path, report_id: str, filename: str = "report.html") -> Path:
    _uuid(report_id)
    try:
        return checked_path(root / "workspaces" / "reports" / report_id / filename)
    except WorkspaceBackupError as exc:
        raise _error("managed_report_path_invalid") from exc


def _fsync_directory(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _write_new(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _read_file(path: Path, *, sha256: str, size_bytes: int) -> bytes:
    try:
        path = checked_path(path, file=True)
        before = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != size_bytes
            or not 1 <= size_bytes <= MAX_REPORT_BYTES
        ):
            raise _error()
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise _error()
            content = stream.read(MAX_REPORT_BYTES + 1)
        if len(content) != size_bytes or _sha(content) != sha256:
            raise _error()
        return content
    except (OSError, WorkspaceBackupError) as exc:
        raise _error("managed_report_file_unavailable") from exc


def create_managed_report(
    root: Path,
    *,
    source: ManagedSource,
    expected_source_ref_sha256: str,
    content: bytes,
    locale: Literal["en", "ko"],
    renderer_id: str,
    renderer_version: str,
    report_level: Literal["full", "summary"],
    section_manifest_json: str,
    created_at: str,
    report_id: str | None = None,
) -> ManagedReportArtifact:
    if not isinstance(source, LhsDesignReportSource | BayesianHistoryReportSource):
        raise _error("managed_report_source_invalid")
    source_json = _canonical_source(source)
    source_sha = _sha(source_json.encode("utf-8"))
    if source_sha != expected_source_ref_sha256:
        raise _error("managed_report_source_conflict")
    if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_REPORT_BYTES:
        raise _error("managed_report_size_invalid")
    report_id = str(uuid4()) if report_id is None else _uuid(report_id)
    design, study, history, recommendation, batch = _owners(source)
    record = ManagedReportArtifact(
        report_id,
        source.kind,
        design,
        study,
        history,
        recommendation,
        batch,
        source_json,
        source_sha,
        source.expected_source_sha256,
        1,
        locale,
        renderer_id,
        renderer_version,
        report_level,
        section_manifest_json,
        f"workspaces/reports/{report_id}/report.html",
        _sha(content),
        "text/html",
        len(content),
        created_at,
    )
    _validate_record(record)
    path = _safe_path(root, report_id)
    marker = path.parent / f".create-{record.sha256}-{record.size_bytes}.q"
    created = committed = False
    with closing(sqlite3.connect(metadata_db_path(root), isolation_level=None)) as connection:
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            _validate_source(connection, source)
            column, owner_id = (
                ("design_version_id", design) if design else ("study_version_id", study)
            )
            count = connection.execute(
                f"SELECT count(*) FROM managed_report_artifacts WHERE {column}=?", (owner_id,)
            ).fetchone()[0]
            if count >= MAX_REPORTS_PER_OWNER:
                raise _error("managed_report_limit_exceeded")
            path.parent.parent.mkdir(parents=True, exist_ok=True)
            _safe_path(root, report_id)
            try:
                path.parent.mkdir()
            except FileExistsError as exc:
                raise _error("managed_report_conflict") from exc
            created = True
            _fsync_directory(path.parent.parent)
            _write_new(marker, b"pending\n")
            _write_new(path, content)
            _fsync_directory(path.parent)
            connection.execute(
                f"INSERT INTO managed_report_artifacts ({_COLUMNS}) "
                f"VALUES ({','.join('?' for _ in fields(record))})",
                tuple(asdict(record).values()),
            )
            connection.commit()
            committed = True
        except Exception:
            connection.rollback()
            if created:
                path.unlink(missing_ok=True)
                marker.unlink(missing_ok=True)
                path.parent.rmdir()
                _fsync_directory(path.parent.parent)
            raise
        finally:
            if committed:
                # A leftover marker after commit is harmless and recoverable on startup.
                try:
                    marker.unlink(missing_ok=True)
                    _fsync_directory(path.parent)
                except OSError:
                    pass
    return record


def _records(
    connection: sqlite3.Connection, where: str, params: tuple[object, ...]
) -> list[ManagedReportArtifact]:
    bounded_columns = ", ".join(
        f"CASE WHEN length(CAST({column} AS BLOB)) <= {MAX_METADATA_BYTES} "
        f"THEN {column} ELSE NULL END"
        if column in {"source_ref_json", "section_manifest_json"}
        else column
        for column in MANAGED_REPORT_COLUMNS
    )
    rows = connection.execute(
        f"SELECT {bounded_columns} FROM managed_report_artifacts {where}",
        params,
    ).fetchall()
    records = [ManagedReportArtifact(*row) for row in rows]
    for record in records:
        _validate_record(record)
    return records


def validate_managed_report_record(
    connection: sqlite3.Connection, record: ManagedReportArtifact
) -> None:
    """Read-only metadata/source validation for the versioned backup inventory."""
    _validate_record(record)
    _validate_source(connection, _parse_source(record))


def get_managed_report(root: Path, report_id: str) -> ManagedReportArtifact | None:
    _uuid(report_id)
    with closing(sqlite3.connect(metadata_db_path(root))) as connection:
        records = _records(connection, "WHERE report_id=?", (report_id,))
    return records[0] if records else None


def list_managed_reports(
    root: Path,
    *,
    source: ManagedSource | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[ManagedReportArtifact]:
    if offset < 0 or not 1 <= limit <= 100:
        raise _error("managed_report_pagination_invalid")
    clause = ""
    params: tuple[object, ...] = ()
    if source is not None:
        clause, params = (
            "WHERE source_ref_sha256=?",
            (_sha(_canonical_source(source).encode("utf-8")),),
        )
    with closing(sqlite3.connect(metadata_db_path(root))) as connection:
        return _records(
            connection,
            f"{clause} ORDER BY created_at DESC, report_id LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )


def read_managed_report(root: Path, record: ManagedReportArtifact) -> bytes:
    _validate_record(record)
    return _read_file(
        _safe_path(root, record.report_id), sha256=record.sha256, size_bytes=record.size_bytes
    )


def owner_reports(
    connection: sqlite3.Connection,
    *,
    design_id: str | None = None,
    study_id: str | None = None,
) -> tuple[ManagedReportArtifact, ...]:
    if (design_id is None) == (study_id is None):
        raise ValueError("managed_report_owner_required")
    if design_id is not None:
        where = (
            "WHERE design_version_id IN (SELECT design_version_id "
            "FROM experiment_design_versions WHERE design_id=?)"
        )
    else:
        where = (
            "WHERE study_version_id IN (SELECT study_version_id "
            "FROM bayesian_study_versions WHERE study_id=?)"
        )
    return tuple(_records(connection, where + " ORDER BY report_id", (design_id or study_id,)))


def managed_reports_manifest(records: tuple[ManagedReportArtifact, ...]) -> str:
    return _sha(
        _json(
            [asdict(record) for record in sorted(records, key=lambda item: item.report_id)]
        ).encode("utf-8")
    )


class ReportQuarantine:
    """Caller holds BEGIN IMMEDIATE until commit/rollback and then finishes this move set."""

    def __init__(self, root: Path, records: tuple[ManagedReportArtifact, ...]) -> None:
        self.root = root
        self.records = records
        self.moved: list[tuple[Path, Path]] = []

    def __enter__(self) -> ReportQuarantine:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

    def move(self) -> None:
        try:
            for record in self.records:
                read_managed_report(self.root, record)
                path = _safe_path(self.root, record.report_id)
                quarantine = path.parent / f".delete-{record.sha256}-{record.size_bytes}.q"
                if quarantine.exists():
                    raise _error("managed_report_quarantine_conflict")
                path.rename(quarantine)
                self.moved.append((path, quarantine))
                _fsync_directory(path.parent)
        except OSError as exc:
            self.rollback()
            raise _error("managed_report_quarantine_failed") from exc
        except Exception:
            self.rollback()
            raise

    def rollback(self) -> None:
        for path, quarantine in reversed(self.moved):
            if path.exists():
                raise _error("managed_report_quarantine_conflict")
            quarantine.rename(path)
            _fsync_directory(path.parent)
        self.moved.clear()

    def commit(self) -> None:
        for path, quarantine in self.moved:
            try:
                quarantine.unlink()
                _fsync_directory(path.parent)
                path.parent.rmdir()
                _fsync_directory(path.parent.parent)
            except OSError:
                # Metadata is committed; exact named/hash-verified recovery completes cleanup.
                continue
        self.moved.clear()


def delete_managed_report(
    root: Path,
    *,
    report_id: str,
    expected_sha256: str,
    expected_source_ref_sha256: str,
) -> None:
    quarantine = ReportQuarantine(root, ())
    with closing(sqlite3.connect(metadata_db_path(root), isolation_level=None)) as connection:
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            records = _records(connection, "WHERE report_id=?", (_uuid(report_id),))
            if not records:
                raise _error("managed_report_not_found")
            record = records[0]
            if (
                record.sha256 != expected_sha256
                or record.source_ref_sha256 != expected_source_ref_sha256
            ):
                raise _error("managed_report_conflict")
            quarantine = ReportQuarantine(root, tuple(records))
            quarantine.move()
            connection.execute(
                "DELETE FROM managed_report_artifacts WHERE report_id=?", (report_id,)
            )
            connection.commit()
        except Exception:
            connection.rollback()
            quarantine.rollback()
            raise
    quarantine.commit()


def recover_managed_report_files(root: Path) -> tuple[int, int, int]:
    """Run under the workspace lease, after metadata initialization; never remove unknown files."""
    restored = deleted = pending = 0
    try:
        base = checked_path(root / "workspaces" / "reports")
    except WorkspaceBackupError:
        return 0, 0, 1
    if not base.exists():
        return restored, deleted, pending
    for directory in base.iterdir():
        try:
            path = _safe_path(root, directory.name)
            if not directory.is_dir():
                continue
            for marker in directory.iterdir():
                match = re.fullmatch(r"\.(create|delete)-([0-9a-f]{64})-([0-9]+)\.q", marker.name)
                if match is None:
                    continue
                kind, digest, size = match.groups()
                record = get_managed_report(root, directory.name)
                if record is not None and (
                    record.sha256 != digest or record.size_bytes != int(size)
                ):
                    raise _error()
                if marker.is_symlink():
                    raise _error()
                if kind == "delete":
                    _read_file(marker, sha256=digest, size_bytes=int(size))
                    if record is not None:
                        if path.exists():
                            raise _error()
                        marker.rename(path)
                        restored += 1
                    else:
                        marker.unlink()
                        deleted += 1
                else:
                    _read_file(marker, sha256=_sha(b"pending\n"), size_bytes=8)
                    if path.exists():
                        _read_file(path, sha256=digest, size_bytes=int(size))
                        if record is None:
                            path.unlink()
                    elif record is not None:
                        raise _error()
                    marker.unlink()
                    deleted += 1
                _fsync_directory(directory)
            if not any(directory.iterdir()):
                directory.rmdir()
                _fsync_directory(base)
        except (ManagedReportStorageError, OSError, ValueError):
            pending += 1
    return restored, deleted, pending
