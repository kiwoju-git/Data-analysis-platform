import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import status

from app.api.v1.schemas.datasets import ConfirmedParsingOptions
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.row_readers import iter_source_rows
from app.storage.atomic import atomic_replace, atomic_write_text
from app.storage.metadata import (
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetRecord,
    DatasetVersionRecord,
)

CANONICAL_ROWS_KIND = "canonical_rows"
CANONICAL_MANIFEST_KIND = "canonical_manifest"
CANONICAL_ROWS_MEDIA_TYPE = "application/x-ndjson"
CANONICAL_MANIFEST_MEDIA_TYPE = "application/json"
CANONICAL_FORMAT = "datalab.canonical.rows-jsonl"
CANONICAL_MANIFEST_SCHEMA_VERSION = 1


def materialize_canonical_dataset_artifacts(
    settings: Settings,
    dataset: DatasetRecord,
    version: DatasetVersionRecord,
    columns: list[DatasetColumnRecord],
    parsing: ConfirmedParsingOptions,
) -> list[DatasetArtifactRecord]:
    if parsing.kind not in {"delimited_text", "xlsx"}:
        raise ApiError(
            code="canonical_artifact_not_supported",
            message="현재 canonical artifact는 구분 텍스트와 XLSX 데이터셋 버전만 지원합니다.",
        )

    source_path = _safe_workspace_path(settings.workspace_root, dataset.stored_path)
    rows_relative_path = _canonical_rows_relative_path(dataset.dataset_id, version.version_id)
    manifest_relative_path = _canonical_manifest_relative_path(
        dataset.dataset_id,
        version.version_id,
    )
    rows_path = settings.workspace_root / rows_relative_path
    manifest_path = settings.workspace_root / manifest_relative_path
    created_at = version.created_at

    rows_sha256, rows_size_bytes, materialized_row_count = _write_canonical_rows_jsonl(
        target_path=rows_path,
        source_path=source_path,
        parsing=parsing,
        column_count=len(columns),
    )
    if materialized_row_count != version.row_count:
        raise ApiError(
            code="canonical_row_count_mismatch",
            message="canonical artifact 행 수가 데이터셋 버전 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    rows_record = DatasetArtifactRecord(
        artifact_id=str(uuid4()),
        version_id=version.version_id,
        kind=CANONICAL_ROWS_KIND,
        path=rows_relative_path.as_posix(),
        sha256=rows_sha256,
        media_type=CANONICAL_ROWS_MEDIA_TYPE,
        size_bytes=rows_size_bytes,
        created_at=created_at,
    )

    manifest_payload = {
        "manifest_schema_version": CANONICAL_MANIFEST_SCHEMA_VERSION,
        "artifact_format": CANONICAL_FORMAT,
        "dataset_id": dataset.dataset_id,
        "version_id": version.version_id,
        "source_sha256": version.source_sha256,
        "schema_hash_at_creation": version.schema_hash,
        "row_count": version.row_count,
        "column_count": version.column_count,
        "columns": [
            {
                "column_id": column.column_id,
                "column_index": column.column_index,
                "original_name": column.original_name,
                "data_type": column.data_type,
            }
            for column in columns
        ],
        "data": {
            "kind": rows_record.kind,
            "path": rows_record.path,
            "sha256": rows_record.sha256,
            "media_type": rows_record.media_type,
            "size_bytes": rows_record.size_bytes,
        },
        "created_at": created_at,
    }
    manifest_text = (
        json.dumps(
            manifest_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    atomic_write_text(manifest_path, manifest_text, encoding="utf-8")
    manifest_bytes = manifest_text.encode("utf-8")

    manifest_record = DatasetArtifactRecord(
        artifact_id=str(uuid4()),
        version_id=version.version_id,
        kind=CANONICAL_MANIFEST_KIND,
        path=manifest_relative_path.as_posix(),
        sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        media_type=CANONICAL_MANIFEST_MEDIA_TYPE,
        size_bytes=len(manifest_bytes),
        created_at=created_at,
    )
    return [rows_record, manifest_record]


def _write_canonical_rows_jsonl(
    *,
    target_path: Path,
    source_path: Path,
    parsing: ConfirmedParsingOptions,
    column_count: int,
) -> tuple[str, int, int]:
    digest = hashlib.sha256()
    size_bytes = 0
    row_count = 0

    def writer(temp_path: Path) -> None:
        nonlocal size_bytes, row_count
        with temp_path.open("wb") as handle:
            for row_index, values in enumerate(
                iter_source_rows(source_path, parsing, column_count),
            ):
                payload = (
                    json.dumps(
                        {"row_index": row_index, "values": values},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
                digest.update(payload)
                size_bytes += len(payload)
                row_count += 1
                handle.write(payload)

            handle.flush()
            os.fsync(handle.fileno())

    atomic_replace(target_path, writer)
    return digest.hexdigest(), size_bytes, row_count


def _canonical_rows_relative_path(dataset_id: str, version_id: str) -> Path:
    return (
        Path("workspaces")
        / "datasets"
        / dataset_id
        / "versions"
        / version_id
        / "canonical.rows.jsonl"
    )


def _canonical_manifest_relative_path(dataset_id: str, version_id: str) -> Path:
    return (
        Path("workspaces")
        / "datasets"
        / dataset_id
        / "versions"
        / version_id
        / "canonical.manifest.json"
    )


def _safe_workspace_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="stored_upload_invalid",
            message="저장된 업로드 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    source_path = workspace_root / relative_path
    if not source_path.exists():
        raise ApiError(
            code="stored_upload_missing",
            message="저장된 원본 업로드 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return source_path
