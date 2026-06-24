import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import status

from app.api.v1.schemas.datasets import ConfirmedParsingOptions
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.canonical_artifacts import (
    CANONICAL_ROWS_KIND,
    CANONICAL_ROWS_MEDIA_TYPE,
)
from app.storage.metadata import (
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetRecord,
    DatasetVersionRecord,
    get_dataset_artifact_record,
    get_dataset_record,
    get_dataset_version_record,
    list_dataset_column_records,
)


@dataclass(frozen=True)
class DatasetRowsContext:
    version: DatasetVersionRecord
    dataset: DatasetRecord
    columns: list[DatasetColumnRecord]
    parsing: ConfirmedParsingOptions
    source_path: Path
    canonical_rows_artifact: DatasetArtifactRecord
    canonical_rows_path: Path


def get_dataset_rows_context(settings: Settings, version_id: UUID) -> DatasetRowsContext:
    version = get_dataset_version_record(settings.workspace_root, str(version_id))
    if version is None:
        raise ApiError(
            code="dataset_version_not_found",
            message="요청한 데이터셋 버전을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    dataset = get_dataset_record(settings.workspace_root, version.dataset_id)
    if dataset is None:
        raise ApiError(
            code="dataset_not_found",
            message="요청한 데이터셋을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    parsing = ConfirmedParsingOptions.model_validate(json.loads(version.parsing_options_json))
    if parsing.kind != "delimited_text":
        raise ApiError(
            code="dataset_rows_not_supported",
            message="현재 분석은 구분 텍스트 데이터셋 버전만 지원합니다.",
        )

    columns = list_dataset_column_records(settings.workspace_root, version.version_id)
    canonical_rows_artifact = get_dataset_artifact_record(
        settings.workspace_root,
        version.version_id,
        CANONICAL_ROWS_KIND,
    )
    if canonical_rows_artifact is None:
        raise ApiError(
            code="canonical_artifact_missing",
            message="canonical parsed artifact 메타데이터가 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return DatasetRowsContext(
        version=version,
        dataset=dataset,
        columns=columns,
        parsing=parsing,
        source_path=_safe_workspace_path(settings.workspace_root, dataset.stored_path),
        canonical_rows_artifact=canonical_rows_artifact,
        canonical_rows_path=_safe_artifact_path(
            settings.workspace_root,
            canonical_rows_artifact.path,
        ),
    )


def iter_dataset_rows(context: DatasetRowsContext) -> Iterator[list[str | None]]:
    yield from _iter_canonical_rows_jsonl(
        path=context.canonical_rows_path,
        artifact=context.canonical_rows_artifact,
        expected_row_count=context.version.row_count,
        column_count=len(context.columns),
    )


def _iter_canonical_rows_jsonl(
    *,
    path: Path,
    artifact: DatasetArtifactRecord,
    expected_row_count: int,
    column_count: int,
) -> Iterator[list[str | None]]:
    if artifact.kind != CANONICAL_ROWS_KIND or artifact.media_type != CANONICAL_ROWS_MEDIA_TYPE:
        raise ApiError(
            code="canonical_artifact_metadata_invalid",
            message="canonical parsed artifact 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    digest = hashlib.sha256()
    size_bytes = 0
    row_count = 0
    try:
        with path.open("rb") as handle:
            for raw_line in handle:
                size_bytes += len(raw_line)
                digest.update(raw_line)
                values = _canonical_values_from_line(
                    raw_line,
                    expected_row_index=row_count,
                    column_count=column_count,
                )
                row_count += 1
                yield values
    except UnicodeDecodeError as exc:
        raise _canonical_artifact_error() from exc
    except json.JSONDecodeError as exc:
        raise _canonical_artifact_error() from exc

    if (
        row_count != expected_row_count
        or size_bytes != artifact.size_bytes
        or digest.hexdigest() != artifact.sha256
    ):
        raise _canonical_artifact_error()


def _canonical_values_from_line(
    raw_line: bytes,
    *,
    expected_row_index: int,
    column_count: int,
) -> list[str | None]:
    payload = json.loads(raw_line.decode("utf-8"))
    if not isinstance(payload, dict):
        raise _canonical_artifact_error()

    row_index = payload.get("row_index")
    values = payload.get("values")
    if row_index != expected_row_index or not isinstance(values, list):
        raise _canonical_artifact_error()
    if len(values) != column_count:
        raise _canonical_artifact_error()
    if any(value is not None and not isinstance(value, str) for value in values):
        raise _canonical_artifact_error()
    return values


def _canonical_artifact_error() -> ApiError:
    return ApiError(
        code="canonical_artifact_invalid",
        message="canonical parsed artifact가 손상되었거나 메타데이터와 일치하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
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


def _safe_artifact_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="canonical_artifact_path_invalid",
            message="canonical parsed artifact 경로 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    artifact_path = workspace_root / relative_path
    if not artifact_path.exists():
        raise ApiError(
            code="canonical_artifact_file_missing",
            message="canonical parsed artifact 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return artifact_path
