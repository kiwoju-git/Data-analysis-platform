"""Atomic dataset ownership and global import-request idempotency."""

import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path

from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.metadata import metadata_db_path


def commit_dataset_import(
    workspace_root: Path,
    request_id: str,
    request_sha256: str,
    create: Callable[[sqlite3.Connection], str],
) -> str:
    with closing(sqlite3.connect(metadata_db_path(workspace_root))) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                "SELECT version.study_id, imported.request_sha256 "
                "FROM bayesian_dataset_imports imported JOIN bayesian_study_versions version "
                "ON version.study_version_id=imported.study_version_id WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if replay is not None:
                if replay[1] != request_sha256:
                    raise BayesianStorageConflict("bayesian_import_request_id_conflict")
                return str(replay[0])
            # Source reads run while the same write lock excludes schema/deletion commits.
            return create(connection)


def validate_import_reference(
    workspace_root: Path, study_version_id: str, expected: tuple[object, ...]
) -> bool:
    with closing(sqlite3.connect(metadata_db_path(workspace_root))) as connection:
        row = connection.execute(
            "SELECT dataset_version_id,request_id,request_sha256,preflight_sha256,"
            "source_schema_hash,source_canonical_sha256,import_schema_version "
            "FROM bayesian_dataset_imports WHERE study_version_id=?",
            (study_version_id,),
        ).fetchone()
    return row == expected
