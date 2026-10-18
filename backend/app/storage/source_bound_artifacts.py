"""Atomic source checks for new analysis-owned immutable completed artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import UUID

from app.storage.metadata import AnalysisArtifactRecord, metadata_db_path
from app.storage.workspace_archive import WorkspaceBackupError, checked_path

MAX_COMPLETED_ARTIFACT_BYTES = 16 * 1024 * 1024
MAX_COMPLETED_ARTIFACTS = 100
_JOURNAL_LIMIT = 4096
_COLUMNS = "artifact_id,analysis_id,kind,path,sha256,media_type,created_at"
_KINDS = {
    "gp_completed_prediction": ("completed-prediction.json", "application/json"),
    "pls_completed_prediction": ("completed-prediction.json", "application/json"),
    "managed_source_html_report": ("managed-report.html", "text/html"),
}
SOURCE_BOUND_ARTIFACT_KINDS = frozenset(_KINDS)


class SourceBoundArtifactError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def insert_source_bound_artifact(
    root: Path,
    record: AnalysisArtifactRecord,
    content: bytes,
    *,
    expected_source_sha256: str,
    model_id: str | None = None,
    model_manifest_sha256: str | None = None,
    dependency_artifact: tuple[str, str] | None = None,
) -> None:
    if not 0 < len(content) <= MAX_COMPLETED_ARTIFACT_BYTES:
        raise SourceBoundArtifactError("stored_report_size_limit")
    if hashlib.sha256(content).hexdigest() != record.sha256:
        raise SourceBoundArtifactError("stored_report_checksum_mismatch")
    path = _record_path(root, record)
    journal = path.with_name(f".create-{record.artifact_id}.source-bound.json")
    journal_created = False
    try:
        with sqlite3.connect(metadata_db_path(root)) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("BEGIN IMMEDIATE")
            source = connection.execute(
                "SELECT result_sha256,status,stale FROM analysis_runs WHERE analysis_id=?",
                (record.analysis_id,),
            ).fetchone()
            if source is None or source[:2] != (expected_source_sha256, "succeeded"):
                raise SourceBoundArtifactError("stored_report_source_changed")
            if model_id is not None:
                model = connection.execute(
                    "SELECT m.manifest_sha256,m.analysis_id,m.schema_hash,v.schema_hash "
                    "FROM regression_models m JOIN dataset_versions v "
                    "ON v.version_id=m.dataset_version_id WHERE m.model_id=?",
                    (model_id,),
                ).fetchone()
                if (
                    source[2]
                    or model is None
                    or model[0] != model_manifest_sha256
                    or model[1] != record.analysis_id
                    or model[2] != model[3]
                ):
                    raise SourceBoundArtifactError("completed_prediction_source_changed")
            if dependency_artifact is not None:
                dependency = connection.execute(
                    "SELECT sha256 FROM analysis_artifacts WHERE analysis_id=? AND artifact_id=?",
                    (record.analysis_id, dependency_artifact[0]),
                ).fetchone()
                if dependency is None or dependency[0] != dependency_artifact[1]:
                    raise SourceBoundArtifactError("completed_prediction_source_changed")
            count = connection.execute(
                "SELECT COUNT(*) FROM analysis_artifacts WHERE analysis_id=? AND kind=?",
                (record.analysis_id, record.kind),
            ).fetchone()[0]
            if count >= MAX_COMPLETED_ARTIFACTS:
                raise SourceBoundArtifactError("stored_report_count_limit")
            if path.exists() or journal.exists():
                raise SourceBoundArtifactError("stored_report_artifact_exists")
            path.parent.mkdir(parents=True, exist_ok=True)
            _record_path(root, record)
            _sync_directory(path.parent.parent)
            journal_content = json.dumps(
                {"schema_version": 1, "record": asdict(record), "size_bytes": len(content)},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(journal_content) > _JOURNAL_LIMIT:
                raise SourceBoundArtifactError("stored_report_artifact_invalid")
            _write_completed_file(journal, journal_content)
            journal_created = True
            # The row becomes visible only after the complete immutable file is durable.
            _write_completed_file(path, content)
            _insert_record(connection, record)
            connection.commit()
        try:
            _remove_journal(journal)
        except OSError:
            # A committed row plus its exact journal is safe for startup recovery.
            pass
    except BaseException:
        if journal_created:
            _recover_journal(root, journal)
        raise


def _insert_record(connection: sqlite3.Connection, record: AnalysisArtifactRecord) -> None:
    connection.execute(
        f"INSERT INTO analysis_artifacts ({_COLUMNS}) VALUES (?,?,?,?,?,?,?)",
        tuple(asdict(record).values()),
    )


def _sync_directory(directory: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _write_completed_file(path: Path, content: bytes) -> None:
    with path.open("xb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    _sync_directory(path.parent)


def _remove_journal(path: Path) -> None:
    path.unlink()
    _sync_directory(path.parent)


def _record_path(root: Path, record: AnalysisArtifactRecord) -> Path:
    try:
        if (
            str(UUID(record.artifact_id)) != record.artifact_id
            or str(UUID(record.analysis_id)) != record.analysis_id
            or record.kind not in _KINDS
            or re.fullmatch(r"[0-9a-f]{64}", record.sha256) is None
            or not isinstance(record.created_at, str)
            or not 0 < len(record.created_at) <= 128
        ):
            raise ValueError("invalid artifact record")
        suffix, media_type = _KINDS[record.kind]
        relative = (
            Path("workspaces")
            / "analyses"
            / record.analysis_id
            / "exports"
            / f"{record.artifact_id}.{suffix}"
        )
        if record.path != relative.as_posix() or record.media_type != media_type:
            raise ValueError("invalid artifact contract")
        return checked_path(root / relative)
    except (ValueError, TypeError, AttributeError, WorkspaceBackupError) as exc:
        raise SourceBoundArtifactError("stored_report_artifact_invalid") from exc


def _read_checked(path: Path, limit: int) -> bytes:
    try:
        path = checked_path(path, file=True)
        before = path.stat()
        if not 0 < before.st_size <= limit:
            raise SourceBoundArtifactError("stored_report_size_limit")
        with path.open("rb") as source:
            actual = os.fstat(source.fileno())
            if (before.st_dev, before.st_ino) != (actual.st_dev, actual.st_ino):
                raise SourceBoundArtifactError("stored_report_artifact_invalid")
            content = source.read(limit + 1)
        if len(content) != before.st_size:
            raise SourceBoundArtifactError("stored_report_size_limit")
        return content
    except (OSError, WorkspaceBackupError) as exc:
        raise SourceBoundArtifactError("stored_report_artifact_invalid") from exc


def read_source_bound_artifact(root: Path, record: AnalysisArtifactRecord) -> bytes:
    content = _read_checked(_record_path(root, record), MAX_COMPLETED_ARTIFACT_BYTES)
    if hashlib.sha256(content).hexdigest() != record.sha256:
        raise SourceBoundArtifactError("stored_report_checksum_mismatch")
    return content


def _recover_journal(root: Path, journal: Path) -> Literal["preserved", "deleted", "pending"]:
    try:
        data = json.loads(_read_checked(journal, _JOURNAL_LIMIT))
        if (
            not isinstance(data, dict)
            or set(data) != {"schema_version", "record", "size_bytes"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
            or type(data["size_bytes"]) is not int
            or not 0 < data["size_bytes"] <= MAX_COMPLETED_ARTIFACT_BYTES
            or not isinstance(data["record"], dict)
        ):
            return "pending"
        record = AnalysisArtifactRecord(**data["record"])
        path = _record_path(root, record)
        expected_journal = path.with_name(f".create-{record.artifact_id}.source-bound.json")
        if checked_path(journal) != expected_journal:
            return "pending"
        with sqlite3.connect(metadata_db_path(root)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM analysis_artifacts WHERE artifact_id=?",
                (record.artifact_id,),
            ).fetchone()
            if row is not None and AnalysisArtifactRecord(*row) != record:
                return "pending"
            other = connection.execute(
                "SELECT 1 FROM analysis_artifacts WHERE path=? AND artifact_id!=?",
                (record.path, record.artifact_id),
            ).fetchone()
            if other is not None:
                return "pending"
            if path.exists():
                content = read_source_bound_artifact(root, record)
                if len(content) != data["size_bytes"]:
                    return "pending"
                if row is None:
                    path.unlink()
                    _sync_directory(path.parent)
            elif row is not None:
                return "pending"
            _remove_journal(journal)
        return "preserved" if row is not None else "deleted"
    except (
        OSError,
        ValueError,
        TypeError,
        sqlite3.Error,
        SourceBoundArtifactError,
        WorkspaceBackupError,
    ):
        # Corrupt or partial files require inspection, never unverified deletion.
        return "pending"


def recover_source_bound_artifact_files(root: Path) -> tuple[int, int, int]:
    """Recover only exact owned creation journals while the workspace lease is held."""
    preserved = deleted = pending = 0
    try:
        base = checked_path(root / "workspaces" / "analyses")
        if not base.exists():
            return 0, 0, 0
        for owner in base.iterdir():
            try:
                if str(UUID(owner.name)) != owner.name:
                    continue
                exports = checked_path(owner / "exports")
                if not exports.exists():
                    continue
                for journal in exports.glob(".create-*.source-bound.json"):
                    outcome = _recover_journal(root, journal)
                    preserved += outcome == "preserved"
                    deleted += outcome == "deleted"
                    pending += outcome == "pending"
            except (OSError, WorkspaceBackupError):
                pending += 1
            except ValueError:
                continue
    except (OSError, WorkspaceBackupError):
        pending += 1
    return preserved, deleted, pending
