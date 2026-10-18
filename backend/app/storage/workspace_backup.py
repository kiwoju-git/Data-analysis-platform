"""Offline, hash-verified backup and fresh-target restore of managed workspaces.

No initializer, recovery routine, model loader, or statistical runner is called.
The process lease is cooperative; local administrators are outside this boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import struct
import sys
import tempfile
import time
import zipfile
from contextlib import closing
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from app.storage.metadata import MIGRATIONS
from app.storage.workspace_archive import (
    CHUNK_SIZE,
    DEFAULT_LIMITS,
    BackupLimits,
    WorkspaceBackupError,
    check_zip_directory,
    checked_path,
    relative_path,
    stream_file,
)
from app.storage.workspace_lease import acquire_workspace_lease

__all__ = [
    "BackupLimits",
    "WorkspaceBackupError",
    "backup_workspace",
    "restore_workspace",
    "verify_backup",
]

_DATABASE = "db/metadata.sqlite3"
_RESTORE_MARKER = ".workspace-restore-in-progress"
_HASH = re.compile(r"^[0-9a-f]{64}$")
_DATASET_KINDS = {
    "canonical_rows": "canonical.rows.jsonl",
    "canonical_manifest": "canonical.manifest.json",
    "dataset_cell_correction_manifest": "cell-correction.manifest.json",
}
_ANALYSIS_KINDS = {
    "analysis_row_snapshot": "row_snapshot.json",
    "regression_prediction_rows": "prediction_rows.jsonl",
    "regression_pasted_prediction_input": "pasted_input.json",
    "regression_pasted_prediction_rows": "prediction_rows.json",
}
_EXPORT_KINDS = {
    "analysis_result_json_export": "analysis-result.json",
    "analysis_result_csv_export": "analysis-result.csv",
    "analysis_result_html_report": "analysis-result.html",
    "regression_prediction_csv_export": "regression-prediction.csv",
    "gp_completed_prediction": "completed-prediction.json",
    "pls_completed_prediction": "completed-prediction.json",
    "managed_source_html_report": "managed-report.html",
}
SUPPORTED_BACKUP_METADATA_VERSIONS = frozenset({20, 21})


def _check_limits(limits: BackupLimits) -> None:
    if (
        any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in (
                limits.max_files,
                limits.max_file_bytes,
                limits.max_total_bytes,
                limits.max_manifest_bytes,
            )
        )
        or isinstance(limits.max_seconds, bool)
        or not isinstance(limits.max_seconds, int | float)
        or not 0 < limits.max_seconds <= 86400
        or not math.isfinite(limits.max_seconds)
    ):
        raise WorkspaceBackupError("workspace_backup_invalid_limits")


def _deadline(start: float, limits: BackupLimits) -> None:
    if time.monotonic() - start > limits.max_seconds:
        raise WorkspaceBackupError("workspace_backup_time_limit")


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_directory(source: Path, destination: Path) -> None:
    if os.name == "nt":
        source.rename(destination)
        return
    if not sys.platform.startswith("linux"):
        raise WorkspaceBackupError("workspace_restore_platform_unsupported")
    import ctypes

    library = ctypes.CDLL(None, use_errno=True)
    try:
        rename = library.renameat2
    except AttributeError as exc:
        raise WorkspaceBackupError("workspace_restore_platform_unsupported") from exc
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    # AT_FDCWD and RENAME_NOREPLACE: an existing empty directory must also survive.
    if rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _read_only(path: Path, start: float, limits: BackupLimits) -> sqlite3.Connection:
    checked_path(path, file=True)
    if path.stat().st_size > min(limits.max_file_bytes, limits.max_total_bytes):
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    connection = sqlite3.connect(
        "file:" + quote(str(path), safe="/:") + "?mode=ro", uri=True, timeout=2
    )
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.row_factory = sqlite3.Row
    connection.set_progress_handler(
        lambda: int(time.monotonic() - start > limits.max_seconds), 10000
    )
    return connection


def _hash_matches(value: object, expected: object) -> bool:
    return isinstance(expected, str) and bool(_HASH.fullmatch(expected)) and value == expected


def _schema_definition(connection: sqlite3.Connection) -> tuple[tuple[str, ...], ...]:
    return tuple(
        (row[0], row[1], row[2], re.sub(r"\s+", " ", row[3]).strip())
        for row in connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT GLOB 'sqlite_*' ORDER BY type,name"
        )
    )


@lru_cache(maxsize=2)
def _known_schema_definition(version: int) -> tuple[tuple[str, ...], ...]:
    # Compile only application-owned DDL in RAM. Never migrate the source/restore DB.
    with closing(sqlite3.connect(":memory:")) as reference:
        for migration in MIGRATIONS:
            if migration.version <= version:
                reference.executescript(migration.sql)
        return _schema_definition(reference)


def _validate_database(connection: sqlite3.Connection, limits: BackupLimits) -> dict[str, int]:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version not in SUPPORTED_BACKUP_METADATA_VERSIONS:
        raise WorkspaceBackupError("workspace_backup_unsupported_schema")
    schema_filter = "name NOT GLOB 'sqlite_*'"
    if connection.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE {schema_filter}").fetchone()[
        0
    ] != len(_known_schema_definition(version)):
        raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
    if connection.execute(
        f"SELECT 1 FROM sqlite_master WHERE {schema_filter} AND "
        "(length(name)>128 OR length(tbl_name)>128 OR "
        "length(CAST(sql AS BLOB))>32768 OR sql IS NULL) LIMIT 1"
    ).fetchone():
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT GLOB 'sqlite_*'"
        )
    }
    expected_tables = {item[1] for item in _known_schema_definition(version) if item[0] == "table"}
    if tables != expected_tables:
        raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
    if _schema_definition(connection) != _known_schema_definition(version):
        raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
    if connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] != version:
        raise WorkspaceBackupError("workspace_backup_unsupported_schema")
    migrations = [
        row[0]
        for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")
    ]
    if migrations != list(range(1, version + 1)):
        raise WorkspaceBackupError("workspace_backup_unsupported_schema")
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise WorkspaceBackupError("workspace_backup_database_invalid")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise WorkspaceBackupError("workspace_backup_database_invalid")
    for table, column in (("analysis_runs", "status"), ("jobs", "state")):
        if connection.execute(
            f"SELECT 1 FROM {table} "
            f"WHERE {column} IN ('queued','running','cancel_requested') LIMIT 1"
        ).fetchone():
            raise WorkspaceBackupError("workspace_backup_recovery_required")
    if connection.execute(
        "SELECT 1 FROM analysis_runs WHERE (result_path IS NULL) != (result_sha256 IS NULL) "
        "OR (status='succeeded' AND result_path IS NULL) LIMIT 1"
    ).fetchone():
        raise WorkspaceBackupError("workspace_backup_database_invalid")
    _validate_database_assets(connection, limits)
    return {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in sorted(tables)
    }


def _validate_database_assets(connection: sqlite3.Connection, limits: BackupLimits) -> None:
    if connection.execute("PRAGMA user_version").fetchone()[0] >= 21:
        _validate_managed_reports(connection, limits)
    if connection.execute(
        "SELECT 1 FROM experiment_design_analysis_assets " "WHERE length(content) > ? LIMIT 1",
        (min(limits.max_file_bytes, 16777216),),
    ).fetchone():
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    for row in connection.execute(
        "SELECT asset.content, asset.sha256, asset.size_bytes, asset.source_analysis_sha256, "
        "analysis.result_sha256 FROM experiment_design_analysis_assets asset "
        "JOIN experiment_design_analyses analysis USING(analysis_id)"
    ):
        content, expected, size, source_hash, actual_source = row
        if (
            not isinstance(content, bytes)
            or size != len(content)
            or size > min(limits.max_file_bytes, 16777216)
        ):
            raise WorkspaceBackupError("workspace_backup_database_invalid")
        if (
            not _hash_matches(hashlib.sha256(content).hexdigest(), expected)
            or source_hash != actual_source
        ):
            raise WorkspaceBackupError("workspace_backup_asset_corrupt")
    for table, content_column, hash_column in (
        ("experiment_design_analyses", "result_json", "result_sha256"),
        ("bayesian_recommendations", "config_json", "config_sha256"),
        ("bayesian_recommendations", "result_json", "result_sha256"),
        ("bayesian_recommendation_batches", "config_json", "config_sha256"),
        ("bayesian_recommendation_batches", "result_json", "result_sha256"),
        ("bayesian_recommendation_batch_items", "item_result_json", "item_result_sha256"),
    ):
        if connection.execute(
            f"SELECT 1 FROM {table} WHERE length(CAST({content_column} AS BLOB)) > ? LIMIT 1",
            (limits.max_manifest_bytes,),
        ).fetchone():
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
        for row in connection.execute(f"SELECT {content_column}, {hash_column} FROM {table}"):
            if not isinstance(row[0], str) or not _hash_matches(
                hashlib.sha256(row[0].encode("utf-8")).hexdigest(), row[1]
            ):
                raise WorkspaceBackupError("workspace_backup_asset_corrupt")


def _validate_managed_reports(connection: sqlite3.Connection, limits: BackupLimits) -> None:
    from app.storage.managed_report_artifacts import (
        MANAGED_REPORT_COLUMNS,
        ManagedReportArtifact,
        ManagedReportStorageError,
        validate_managed_report_record,
    )

    if connection.execute(
        "SELECT 1 FROM managed_report_artifacts WHERE size_bytes>? "
        "OR length(CAST(source_ref_json AS BLOB))>? "
        "OR length(CAST(section_manifest_json AS BLOB))>? LIMIT 1",
        (
            limits.max_file_bytes,
            min(limits.max_manifest_bytes, 65536),
            min(limits.max_manifest_bytes, 65536),
        ),
    ).fetchone():
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    try:
        for row in connection.execute(
            f"SELECT {','.join(MANAGED_REPORT_COLUMNS)} FROM managed_report_artifacts"
        ):
            validate_managed_report_record(connection, ManagedReportArtifact(*row))
    except ManagedReportStorageError as exc:
        raise WorkspaceBackupError("workspace_backup_asset_corrupt") from exc


def _inventory(
    connection: sqlite3.Connection, limits: BackupLimits
) -> tuple[dict[str, dict[str, Any]], bool]:
    files: dict[str, dict[str, Any]] = {}
    folded: dict[str, str] = {}
    legacy_paths = False
    inventory_bytes = 0
    for table, columns in (
        ("datasets", ("dataset_id", "stored_path", "sha256")),
        ("dataset_versions", ("version_id", "dataset_id")),
        ("dataset_artifacts", ("artifact_id", "version_id", "kind", "path", "sha256")),
        ("analysis_runs", ("analysis_id", "result_path", "result_sha256")),
        ("analysis_artifacts", ("artifact_id", "analysis_id", "kind", "path", "sha256")),
        ("regression_models", ("model_id", "analysis_id", "manifest_path", "manifest_sha256")),
        ("attribute_control_limit_sets", ("limit_set_id", "asset_path", "asset_sha256")),
    ):
        expressions = " OR ".join(f"length(CAST({column} AS BLOB))>4096" for column in columns)
        if connection.execute(f"SELECT 1 FROM {table} WHERE {expressions} LIMIT 1").fetchone():
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    if connection.execute(
        "SELECT 1 FROM dataset_versions v WHERE "
        "NOT EXISTS(SELECT 1 FROM dataset_artifacts a WHERE a.version_id=v.version_id "
        "AND a.kind='canonical_rows') OR "
        "NOT EXISTS(SELECT 1 FROM dataset_artifacts a WHERE a.version_id=v.version_id "
        "AND a.kind='canonical_manifest') LIMIT 1"
    ).fetchone():
        raise WorkspaceBackupError("workspace_backup_asset_missing")

    def add(path: object, expected: str, sha: object, size: object, owner: str) -> None:
        nonlocal legacy_paths, inventory_bytes
        if isinstance(path, str) and "\\" in path:
            legacy_paths = True
        name = relative_path(path, legacy_windows=True)
        if name != relative_path(expected) or not isinstance(sha, str) or not _HASH.fullmatch(sha):
            raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
        if size is not None and (type(size) is not int or size < 0 or size > limits.max_file_bytes):
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
        if name.casefold() in folded and folded[name.casefold()] != name:
            raise WorkspaceBackupError("workspace_backup_unsafe_path")
        folded[name.casefold()] = name
        inventory_bytes += len(name.encode("utf-8")) + len(owner.encode("utf-8")) + 256
        if inventory_bytes > limits.max_manifest_bytes:
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
        existing = files.get(name)
        if existing:
            if (
                existing["sha256"] != sha
                or size is not None
                and existing["size_bytes"] not in (None, size)
            ):
                raise WorkspaceBackupError("workspace_backup_asset_corrupt")
            existing["owners"].append(owner)
            if size is not None:
                existing["size_bytes"] = size
        else:
            files[name] = {"path": name, "sha256": sha, "size_bytes": size, "owners": [owner]}
        if len(files) + 1 > limits.max_files:
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")

    for row in connection.execute(
        "SELECT dataset_id, stored_path, sha256, size_bytes FROM datasets"
    ):
        name = relative_path(row[1], legacy_windows=True)
        if Path(name).name not in {
            "source.csv",
            "source.tsv",
            "source.txt",
            "source.xlsx",
            "source.upload",
        }:
            raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
        add(
            row[1],
            f"workspaces/datasets/{row[0]}/raw/{Path(name).name}",
            row[2],
            row[3],
            f"datasets:{row[0]}",
        )
    for row in connection.execute(
        "SELECT a.artifact_id,a.version_id,a.kind,a.path,a.sha256,a.size_bytes,v.dataset_id "
        "FROM dataset_artifacts a JOIN dataset_versions v USING(version_id)"
    ):
        artifact_id, version, kind, path, sha, size, dataset = row
        if kind == "profile_summary":
            suffix = f"p/{artifact_id.replace('-', '')[:16]}.json"
        elif kind in _DATASET_KINDS:
            suffix = _DATASET_KINDS[kind]
        else:
            raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
        add(
            path,
            f"workspaces/datasets/{dataset}/versions/{version}/{suffix}",
            sha,
            size,
            f"dataset_artifacts:{artifact_id}",
        )
    for row in connection.execute(
        "SELECT analysis_id,result_path,result_sha256 FROM analysis_runs "
        "WHERE result_path IS NOT NULL"
    ):
        add(
            row[1],
            f"workspaces/analyses/{row[0]}/result.json",
            row[2],
            None,
            f"analysis_runs:{row[0]}",
        )
    model_bytes = connection.execute(
        "SELECT COALESCE(SUM(length(CAST(model_id AS BLOB)) + "
        "length(CAST(analysis_id AS BLOB)) + length(CAST(manifest_path AS BLOB)) + 256),0) "
        "FROM regression_models"
    ).fetchone()[0]
    if model_bytes > limits.max_manifest_bytes:
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    models = {}
    for row in connection.execute(
        "SELECT model_id,analysis_id,manifest_path,manifest_sha256 FROM regression_models"
    ):
        models[row[0]] = row
        if len(models) > limits.max_files:
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    for row in connection.execute(
        "SELECT artifact_id,analysis_id,kind,path,sha256 FROM analysis_artifacts"
    ):
        artifact_id, analysis_id, kind, path, sha = row
        if kind in _ANALYSIS_KINDS:
            suffix = _ANALYSIS_KINDS[kind]
        elif kind in _EXPORT_KINDS:
            suffix = f"exports/{artifact_id}.{_EXPORT_KINDS[kind]}"
        elif kind in {"regression_model_manifest", "gaussian_process_model_numeric_state"}:
            extension = ".json" if kind == "regression_model_manifest" else ".npz"
            matching = [item for item in models.values() if item[1] == analysis_id]
            if len(matching) != 1:
                raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
            suffix = f"model-{matching[0][0]}{extension}"
        else:
            raise WorkspaceBackupError("workspace_backup_unsupported_inventory")
        add(
            path,
            f"workspaces/analyses/{analysis_id}/{suffix}",
            sha,
            None,
            f"analysis_artifacts:{artifact_id}",
        )
    for model_id, analysis_id, path, sha in models.values():
        name = relative_path(path, legacy_windows=True)
        if name not in files:
            raise WorkspaceBackupError("workspace_backup_asset_missing")
        add(
            path,
            f"workspaces/analyses/{analysis_id}/model-{model_id}.json",
            sha,
            None,
            f"regression_models:{model_id}",
        )
    for row in connection.execute(
        "SELECT limit_set_id,asset_path,asset_sha256 FROM attribute_control_limit_sets"
    ):
        add(
            row[1],
            f"artifacts/attribute-control-limit-sets/{row[0]}/limit-set.json",
            row[2],
            None,
            f"attribute_control_limit_sets:{row[0]}",
        )
    if connection.execute("PRAGMA user_version").fetchone()[0] >= 21:
        for row in connection.execute(
            "SELECT report_id,artifact_path,sha256,size_bytes FROM managed_report_artifacts"
        ):
            add(
                row[1],
                f"workspaces/reports/{row[0]}/report.html",
                row[2],
                row[3],
                f"managed_report_artifacts:{row[0]}",
            )
    for item in files.values():
        item["owners"].sort()
    return files, legacy_paths


def _scan_managed(root: Path, expected: set[str], limits: BackupLimits, start: float) -> None:
    if os.path.lexists(root / _RESTORE_MARKER):
        raise WorkspaceBackupError("workspace_backup_recovery_required")
    found: set[str] = set()
    scanned = 0
    for namespace in ("db", "workspaces", "artifacts"):
        base = root / namespace
        if not base.exists():
            continue
        checked_path(base)
        pending = [base]
        while pending:
            _deadline(start, limits)
            with os.scandir(pending.pop()) as children:
                for child in children:
                    scanned += 1
                    if scanned > limits.max_files * 8:
                        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
                    path = Path(child.path)
                    checked_path(path)
                    if (
                        child.name.startswith(".delete-")
                        or child.name == ".cell-correction.pending.json"
                    ):
                        raise WorkspaceBackupError("workspace_backup_recovery_required")
                    if child.is_dir(follow_symlinks=False):
                        pending.append(path)
                        continue
                    checked_path(path, file=True)
                    relative = path.relative_to(root).as_posix()
                    if relative in {"db/metadata.sqlite3-wal", "db/metadata.sqlite3-shm"}:
                        continue
                    found.add(relative)
                    if relative not in expected:
                        raise WorkspaceBackupError("workspace_backup_unregistered_file")
    if found != expected:
        raise WorkspaceBackupError("workspace_backup_asset_missing")


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        value[key] = item
    return value


def _read_json(path: Path, limits: BackupLimits) -> Any:
    if path.stat().st_size > limits.max_manifest_bytes:
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    with path.open("rb") as source:
        return json.load(source, object_pairs_hook=_json_object, parse_constant=_invalid_constant)


def _invalid_constant(_: str) -> Any:
    raise WorkspaceBackupError("workspace_backup_archive_invalid")


def _validate_model_references(
    root: Path, files: dict[str, dict[str, Any]], limits: BackupLimits
) -> None:
    for item in files.values():
        if not any(owner.startswith("regression_models:") for owner in item["owners"]):
            continue
        model = _read_json(root / item["path"], limits)
        if not isinstance(model, dict):
            raise WorkspaceBackupError("workspace_backup_asset_corrupt")
        prediction_state = model.get("prediction_state")
        if model.get("manifest_kind") == "gaussian_process_model_manifest" and (
            not isinstance(prediction_state, dict) or "numeric_artifact" not in prediction_state
        ):
            raise WorkspaceBackupError("workspace_backup_asset_corrupt")
        if isinstance(prediction_state, dict) and "numeric_artifact" in prediction_state:
            numeric = prediction_state["numeric_artifact"]
            if not isinstance(numeric, dict):
                raise WorkspaceBackupError("workspace_backup_asset_corrupt")
            name = relative_path(numeric.get("path"), legacy_windows=True)
            entry = files.get(name)
            if (
                entry is None
                or name != item["path"].removesuffix(".json") + ".npz"
                or numeric.get("kind") != "gaussian_process_model_numeric_state"
                or entry["sha256"] != numeric.get("sha256")
            ):
                raise WorkspaceBackupError("workspace_backup_asset_corrupt")


def _safe_external(path: Path, root: Path) -> Path:
    result = checked_path(path)
    if result == root or root in result.parents:
        raise WorkspaceBackupError("workspace_backup_destination_inside_source")
    return result


def backup_workspace(
    source_root: Path, archive_path: Path, *, limits: BackupLimits = DEFAULT_LIMITS
) -> dict[str, Any]:
    _check_limits(limits)
    start = time.monotonic()
    root = checked_path(source_root)
    if not root.is_dir() or not (root / _DATABASE).is_file():
        raise WorkspaceBackupError("workspace_backup_source_invalid")
    output = _safe_external(archive_path, root)
    if output.exists():
        raise WorkspaceBackupError("workspace_backup_output_exists")
    if not output.parent.is_dir():
        raise WorkspaceBackupError("workspace_backup_destination_invalid")
    try:
        with acquire_workspace_lease(root):
            if os.path.lexists(root / _RESTORE_MARKER):
                raise WorkspaceBackupError("workspace_backup_recovery_required")
            with tempfile.TemporaryDirectory(
                prefix=".workspace-backup-", dir=output.parent
            ) as temporary:
                stage = Path(temporary)
                copied_db = stage / _DATABASE
                copied_db.parent.mkdir()
                with closing(_read_only(root / _DATABASE, start, limits)) as source:
                    _validate_database(source, limits)
                    with closing(sqlite3.connect(copied_db)) as destination:
                        source.backup(
                            destination, pages=256, progress=lambda *_: _deadline(start, limits)
                        )
                with closing(_read_only(copied_db, start, limits)) as connection:
                    row_counts = _validate_database(connection, limits)
                    metadata_version = connection.execute("PRAGMA user_version").fetchone()[0]
                    files, legacy_paths = _inventory(connection, limits)
                _scan_managed(root, {*files, _DATABASE}, limits, start)
                db_size, db_sha = stream_file(
                    copied_db, limits, deadline=start + limits.max_seconds
                )
                if db_size > limits.max_total_bytes:
                    raise WorkspaceBackupError("workspace_backup_limit_exceeded")
                entries: list[dict[str, Any]] = [
                    {
                        "path": _DATABASE,
                        "sha256": db_sha,
                        "size_bytes": db_size,
                        "owners": ["metadata"],
                    }
                ]
                total = db_size
                archive = stage / "backup.zip"
                with zipfile.ZipFile(
                    archive, "w", compression=zipfile.ZIP_STORED, allowZip64=True
                ) as target:
                    target.write(copied_db, _DATABASE)
                    for name, entry in sorted(files.items()):
                        _deadline(start, limits)
                        with target.open(name, "w", force_zip64=True) as sink:
                            size, digest = stream_file(
                                root / name,
                                replace(
                                    limits,
                                    max_file_bytes=min(
                                        limits.max_file_bytes, limits.max_total_bytes - total
                                    ),
                                ),
                                sink,
                                deadline=start + limits.max_seconds,
                            )
                        if digest != entry["sha256"] or entry["size_bytes"] not in (None, size):
                            raise WorkspaceBackupError("workspace_backup_asset_corrupt")
                        total += size
                        if total > limits.max_total_bytes:
                            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
                        entries.append({**entry, "size_bytes": size})
                    _validate_model_references(root, files, limits)
                    manifest = {
                        "schema_version": 1,
                        "metadata_schema_version": metadata_version,
                        "legacy_windows_paths": legacy_paths,
                        "scope": "registered_workspace_assets",
                        "database": {"path": _DATABASE, "row_counts": row_counts},
                        "files": sorted(entries, key=lambda item: item["path"]),
                    }
                    encoded = json.dumps(
                        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                    if len(encoded) > limits.max_manifest_bytes:
                        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
                    target.writestr("manifest.json", encoded)
                _verify_to_stage(archive, stage / "verified", limits, start)
                with archive.open("r+b") as completed:
                    os.fsync(completed.fileno())
                try:
                    # Link publication cannot overwrite a concurrently created destination.
                    os.link(archive, output)
                except FileExistsError as exc:
                    raise WorkspaceBackupError("workspace_backup_output_exists") from exc
                archive.unlink()
                _sync_directory(output.parent)
                return manifest
    except WorkspaceBackupError:
        raise
    except (
        sqlite3.Error,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        RecursionError,
        OverflowError,
        NotImplementedError,
        struct.error,
    ) as exc:
        _deadline(start, limits)
        raise WorkspaceBackupError("workspace_backup_failed") from exc


def _verify_to_stage(
    archive_path: Path, stage: Path, limits: BackupLimits, start: float
) -> dict[str, Any]:
    check_zip_directory(archive_path, limits)
    stage.mkdir()
    with zipfile.ZipFile(archive_path, "r") as archive:
        infos = archive.infolist()
        names: set[str] = set()
        folded: set[str] = set()
        total = 0
        for info in infos:
            name = relative_path(info.filename)
            kind = stat.S_IFMT(info.external_attr >> 16)
            if (
                name in names
                or name.casefold() in folded
                or info.orig_filename != info.filename
                or kind not in (0, stat.S_IFREG)
                or info.is_dir()
                or info.external_attr & 0x10
                or info.flag_bits & 1
                or info.compress_type != zipfile.ZIP_STORED
            ):
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            bound = limits.max_manifest_bytes if name == "manifest.json" else limits.max_file_bytes
            if info.file_size > bound or info.compress_size != info.file_size:
                raise WorkspaceBackupError("workspace_backup_limit_exceeded")
            total += info.file_size
            if total > limits.max_total_bytes + limits.max_manifest_bytes:
                raise WorkspaceBackupError("workspace_backup_limit_exceeded")
            names.add(name)
            folded.add(name.casefold())
        if len(infos) > limits.max_files + 1 or "manifest.json" not in names:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        with archive.open("manifest.json") as source:
            manifest = json.loads(
                source.read(limits.max_manifest_bytes + 1),
                object_pairs_hook=_json_object,
                parse_constant=_invalid_constant,
            )
        if (
            not isinstance(manifest, dict)
            or type(manifest.get("schema_version")) is not int
            or manifest.get("schema_version") != 1
            or type(manifest.get("metadata_schema_version")) is not int
            or manifest.get("metadata_schema_version") not in SUPPORTED_BACKUP_METADATA_VERSIONS
            or manifest.get("scope") != "registered_workspace_assets"
            or type(manifest.get("legacy_windows_paths")) is not bool
        ):
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) > limits.max_files:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        files: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            name = relative_path(entry.get("path"))
            size = entry.get("size_bytes")
            if (
                name in files
                or type(size) is not int
                or size < 0
                or not isinstance(entry.get("sha256"), str)
                or not _HASH.fullmatch(entry["sha256"])
            ):
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            if name != _DATABASE and not name.startswith(
                (
                    "workspaces/datasets/",
                    "workspaces/analyses/",
                    "workspaces/reports/",
                    "artifacts/attribute-control-limit-sets/",
                )
            ):
                raise WorkspaceBackupError("workspace_backup_unsafe_path")
            files[name] = entry
        if names != {*files, "manifest.json"} or _DATABASE not in files:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        if sum(entry["size_bytes"] for entry in files.values()) > limits.max_total_bytes:
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
        for name, entry in files.items():
            _deadline(start, limits)
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            size = 0
            if archive.getinfo(name).file_size != entry["size_bytes"]:
                raise WorkspaceBackupError("workspace_backup_asset_corrupt")
            with archive.open(name) as source, target.open("xb") as sink:
                while chunk := source.read(CHUNK_SIZE):
                    _deadline(start, limits)
                    size += len(chunk)
                    if size > min(entry["size_bytes"], limits.max_file_bytes):
                        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
                    sink.write(chunk)
                    digest.update(chunk)
                sink.flush()
                os.fsync(sink.fileno())
            if size != entry["size_bytes"] or digest.hexdigest() != entry["sha256"]:
                raise WorkspaceBackupError("workspace_backup_asset_corrupt")
    with closing(_read_only(stage / _DATABASE, start, limits)) as connection:
        row_counts = _validate_database(connection, limits)
        metadata_version = connection.execute("PRAGMA user_version").fetchone()[0]
        expected, legacy = _inventory(connection, limits)
    if (
        metadata_version != manifest["metadata_schema_version"]
        or legacy != manifest["legacy_windows_paths"]
        or manifest.get("database") != {"path": _DATABASE, "row_counts": row_counts}
        or set(files) != {*expected, _DATABASE}
    ):
        raise WorkspaceBackupError("workspace_backup_archive_invalid")
    for name, entry in expected.items():
        actual = files[name]
        if (
            entry["sha256"] != actual["sha256"]
            or entry["size_bytes"] not in (None, actual["size_bytes"])
            or entry["owners"] != actual.get("owners")
        ):
            raise WorkspaceBackupError("workspace_backup_asset_corrupt")
    if files[_DATABASE].get("owners") != ["metadata"]:
        raise WorkspaceBackupError("workspace_backup_archive_invalid")
    database = manifest.get("database")
    if (
        not isinstance(database, dict)
        or not isinstance(database.get("row_counts"), dict)
        or any(type(count) is not int for count in database["row_counts"].values())
    ):
        raise WorkspaceBackupError("workspace_backup_archive_invalid")
    _scan_managed(stage, set(files), limits, start)
    _validate_model_references(stage, expected, limits)
    return manifest


def verify_backup(archive_path: Path, *, limits: BackupLimits = DEFAULT_LIMITS) -> dict[str, Any]:
    _check_limits(limits)
    start = time.monotonic()
    archive = checked_path(archive_path, file=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=".workspace-verify-", dir=archive.parent
        ) as temporary:
            return _verify_to_stage(archive, Path(temporary) / "workspace", limits, start)
    except WorkspaceBackupError:
        raise
    except (
        sqlite3.Error,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        RecursionError,
        OverflowError,
        NotImplementedError,
        struct.error,
    ) as exc:
        _deadline(start, limits)
        raise WorkspaceBackupError("workspace_backup_archive_invalid") from exc


def restore_workspace(
    archive_path: Path, target_root: Path, *, limits: BackupLimits = DEFAULT_LIMITS
) -> dict[str, Any]:
    _check_limits(limits)
    start = time.monotonic()
    target = checked_path(target_root)
    archive = _safe_external(archive_path, target)
    if not target.parent.is_dir():
        raise WorkspaceBackupError("workspace_backup_destination_invalid")
    if target.exists() and (
        not target.is_dir() or any(item.name != ".workspace.lock" for item in target.iterdir())
    ):
        raise WorkspaceBackupError("workspace_restore_target_not_empty")
    target.mkdir(exist_ok=True)
    try:
        with acquire_workspace_lease(target):
            if any(item.name != ".workspace.lock" for item in target.iterdir()):
                raise WorkspaceBackupError("workspace_restore_target_not_empty")
            with tempfile.TemporaryDirectory(
                prefix=".workspace-restore-", dir=target.parent
            ) as temporary:
                stage = Path(temporary) / "workspace"
                manifest = _verify_to_stage(archive, stage, limits, start)
                if manifest["legacy_windows_paths"] and os.name != "nt":
                    raise WorkspaceBackupError("workspace_restore_legacy_windows_paths")
                for directory, _, _ in os.walk(stage, topdown=False):
                    _sync_directory(Path(directory))
                marker = target / _RESTORE_MARKER
                with marker.open("x", encoding="ascii") as stream:
                    stream.write(str(uuid4()))
                    stream.flush()
                    os.fsync(stream.fileno())
                _sync_directory(target)
                moved: list[str] = []
                try:
                    for name in ("db", "workspaces", "artifacts"):
                        source = stage / name
                        if source.exists():
                            if (target / name).exists():
                                raise WorkspaceBackupError("workspace_restore_target_not_empty")
                            _publish_directory(source, target / name)
                            moved.append(name)
                            _sync_directory(stage)
                            _sync_directory(target)
                    marker.unlink()
                    _sync_directory(target)
                except BaseException:
                    # Only move this operation's published directories back to its private staging.
                    for name in reversed(moved):
                        (target / name).rename(stage / name)
                    marker.unlink()
                    _sync_directory(target)
                    raise
                return manifest
    except WorkspaceBackupError:
        raise
    except (
        sqlite3.Error,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        RecursionError,
        OverflowError,
        NotImplementedError,
        struct.error,
    ) as exc:
        _deadline(start, limits)
        raise WorkspaceBackupError("workspace_restore_failed") from exc


def main(argv: list[str] | None = None) -> int:
    """Also available from an installed application wheel, without source scripts."""
    import argparse
    import sys

    from app.storage.workspace_lease import WorkspaceLeaseError

    parser = argparse.ArgumentParser(description="Offline verified workspace backup and restore")
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--workspace", required=True, type=Path)
    backup.add_argument("--output", required=True, type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("--archive", required=True, type=Path)
    restore.add_argument("--workspace", required=True, type=Path)
    verify = commands.add_parser("verify")
    verify.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            manifest = backup_workspace(args.workspace, args.output)
        elif args.command == "restore":
            manifest = restore_workspace(args.archive, args.workspace)
        else:
            manifest = verify_backup(args.archive)
    except (WorkspaceBackupError, WorkspaceLeaseError) as exc:
        print(json.dumps({"status": "failed", "code": exc.code}), file=sys.stderr)
        return 1
    except OSError:
        print(
            json.dumps({"status": "failed", "code": "workspace_backup_io_failed"}), file=sys.stderr
        )
        return 1
    print(
        json.dumps(
            {
                "status": "verified" if args.command != "restore" else "restored",
                "files": len(manifest["files"]),
                "metadata_schema_version": manifest["metadata_schema_version"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
