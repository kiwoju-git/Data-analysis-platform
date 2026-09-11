"""Bounded SQLite-owned artifacts with atomic source binding and deletion."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.storage.metadata import WorkspaceAssetStorageConflict, metadata_db_path

MAX_ASSET_BYTES = 16 * 1024 * 1024
MAX_ASSETS_PER_ANALYSIS = 100
AssetKind = Literal["prediction", "html_report"]


@dataclass(frozen=True)
class FactorialAnalysisAsset:
    asset_id: str
    analysis_id: str
    kind: AssetKind
    schema_version: int
    locale: str | None
    source_analysis_sha256: str
    sha256: str
    media_type: str
    size_bytes: int
    created_at: str


_COLUMNS = (
    "asset_id,analysis_id,kind,schema_version,locale,source_analysis_sha256,"
    "sha256,media_type,size_bytes,created_at"
)


def insert_asset(root: Path, record: FactorialAnalysisAsset, content: bytes) -> None:
    if not 0 < len(content) <= MAX_ASSET_BYTES or len(content) != record.size_bytes:
        raise WorkspaceAssetStorageConflict("doe_analysis_asset_size_invalid")
    if hashlib.sha256(content).hexdigest() != record.sha256:
        raise WorkspaceAssetStorageConflict("doe_analysis_asset_checksum_mismatch")
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        source = connection.execute(
            "SELECT result_json,result_sha256 FROM experiment_design_analyses WHERE analysis_id=?",
            (record.analysis_id,),
        ).fetchone()
        if (
            source is None
            or source[1] != record.source_analysis_sha256
            or hashlib.sha256(source[0].encode("utf-8")).hexdigest() != source[1]
        ):
            raise WorkspaceAssetStorageConflict("doe_factorial_prediction_source_changed")
        count = connection.execute(
            "SELECT COUNT(*) FROM experiment_design_analysis_assets WHERE analysis_id=?",
            (record.analysis_id,),
        ).fetchone()[0]
        if count >= MAX_ASSETS_PER_ANALYSIS:
            raise WorkspaceAssetStorageConflict("doe_analysis_asset_count_limit")
        connection.execute(
            f"INSERT INTO experiment_design_analysis_assets ({_COLUMNS},content) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.asset_id,
                record.analysis_id,
                record.kind,
                record.schema_version,
                record.locale,
                record.source_analysis_sha256,
                record.sha256,
                record.media_type,
                record.size_bytes,
                record.created_at,
                content,
            ),
        )


def list_assets(
    root: Path, analysis_id: str, kind: AssetKind | None = None
) -> list[FactorialAnalysisAsset]:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        rows = connection.execute(
            f"SELECT {_COLUMNS} FROM experiment_design_analysis_assets "
            "WHERE analysis_id=? AND (? IS NULL OR kind=?) ORDER BY created_at DESC,asset_id DESC",
            (analysis_id, kind, kind),
        ).fetchall()
    return [FactorialAnalysisAsset(*row) for row in rows]


def get_asset(
    root: Path, analysis_id: str, asset_id: str
) -> tuple[FactorialAnalysisAsset, bytes] | None:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        row = connection.execute(
            f"SELECT {_COLUMNS},content FROM experiment_design_analysis_assets "
            "WHERE analysis_id=? AND asset_id=?",
            (analysis_id, asset_id),
        ).fetchone()
    if row is None:
        return None
    record = FactorialAnalysisAsset(*row[:-1])
    content = bytes(row[-1])
    if len(content) != record.size_bytes or hashlib.sha256(content).hexdigest() != record.sha256:
        raise WorkspaceAssetStorageConflict("doe_analysis_asset_checksum_mismatch")
    return record, content


def delete_asset(root: Path, analysis_id: str, asset_id: str, expected_sha256: str) -> bool:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        deleted = connection.execute(
            "DELETE FROM experiment_design_analysis_assets "
            "WHERE analysis_id=? AND asset_id=? AND sha256=?",
            (analysis_id, asset_id, expected_sha256),
        )
        if deleted.rowcount != 1:
            raise WorkspaceAssetStorageConflict("doe_analysis_asset_deletion_conflict")
    return True


def analysis_deletion_snapshot(root: Path, analysis_id: str) -> tuple[str, int, int] | None:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        return _deletion_snapshot(connection, analysis_id)


def _deletion_snapshot(
    connection: sqlite3.Connection, analysis_id: str
) -> tuple[str, int, int] | None:
    analysis = connection.execute(
        "SELECT result_sha256 FROM experiment_design_analyses WHERE analysis_id=?", (analysis_id,)
    ).fetchone()
    if analysis is None:
        return None
    assets = connection.execute(
        "SELECT asset_id,kind,sha256 FROM experiment_design_analysis_assets "
        "WHERE analysis_id=? ORDER BY asset_id",
        (analysis_id,),
    ).fetchall()
    manifest = hashlib.sha256(
        json.dumps([analysis_id, analysis[0], assets], separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return (
        manifest,
        sum(row[1] == "prediction" for row in assets),
        sum(row[1] == "html_report" for row in assets),
    )


def delete_analysis(root: Path, analysis_id: str, expected_manifest: str) -> tuple[str, int, int]:
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        snapshot = _deletion_snapshot(connection, analysis_id)
        if snapshot is None or snapshot[0] != expected_manifest:
            raise WorkspaceAssetStorageConflict("doe_analysis_deletion_conflict")
        connection.execute(
            "DELETE FROM experiment_design_analysis_response_revisions WHERE analysis_id=?",
            (analysis_id,),
        )
        connection.execute(
            "DELETE FROM experiment_design_analyses WHERE analysis_id=?", (analysis_id,)
        )
    return snapshot
