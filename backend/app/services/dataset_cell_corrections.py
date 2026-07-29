import hashlib
import json
import math
import os
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, Literal
from uuid import UUID, uuid4

from fastapi import status

from app.api.v1.schemas.datasets import (
    ConfirmedParsingOptions,
    DatasetCellCorrectionRequest,
    DatasetCellCorrectionResponse,
    DatasetColumnDataType,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.canonical_artifacts import (
    CANONICAL_FORMAT,
    CANONICAL_MANIFEST_KIND,
    CANONICAL_MANIFEST_MEDIA_TYPE,
    CANONICAL_MANIFEST_SCHEMA_VERSION,
    CANONICAL_ROWS_KIND,
    CANONICAL_ROWS_MEDIA_TYPE,
)
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
    verify_canonical_rows_artifact,
)
from app.services.dataset_versions import dataset_version_response_from_records
from app.storage.atomic import atomic_replace, atomic_write_text
from app.storage.metadata import (
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetVersionLineageRecord,
    DatasetVersionStorageConflict,
    get_dataset_version_record,
    insert_dataset_cell_correction_version_records,
)

CELL_CORRECTION_SCHEMA_VERSION: Final[Literal[1]] = 1
CELL_CORRECTION_MANIFEST_KIND = "dataset_cell_correction_manifest"
CELL_CORRECTION_MANIFEST_MEDIA_TYPE = "application/json"
CELL_CORRECTION_PENDING_NAME = ".cell-correction.pending.json"
_CELL_CORRECTION_FILES = (
    "canonical.rows.jsonl",
    "canonical.manifest.json",
    "cell-correction.manifest.json",
)
_FILE_ATTRIBUTE_REPARSE_POINT = getattr(
    stat,
    "FILE_ATTRIBUTE_REPARSE_POINT",
    0x400,
)


@dataclass(frozen=True)
class DatasetCellCorrectionRecovery:
    retained: int
    deleted: int
    pending: int


def create_dataset_cell_correction(
    settings: Settings,
    *,
    parent_version_id: UUID,
    body: DatasetCellCorrectionRequest,
) -> DatasetCellCorrectionResponse:
    if body.confirmation_parent_version_id != parent_version_id:
        raise _error(
            "dataset_cell_correction_confirmation_mismatch",
            "확인한 원본 버전과 요청한 버전이 일치하지 않습니다.",
            status.HTTP_409_CONFLICT,
        )
    context = get_dataset_rows_context(settings, parent_version_id)
    if (
        context.version.schema_hash != body.expected_parent_schema_hash
        or context.canonical_rows_artifact.sha256 != body.expected_parent_canonical_sha256
    ):
        raise _source_changed()
    verify_canonical_rows_artifact(context)

    edit = body.edits[0]
    if edit.row_index >= context.version.row_count:
        raise _error(
            "dataset_cell_correction_row_out_of_range",
            "수정할 행이 데이터셋 범위를 벗어났습니다.",
        )
    parent_column = next(
        (item for item in context.columns if item.column_id == str(edit.column_id)),
        None,
    )
    if parent_column is None:
        raise _error(
            "dataset_cell_correction_column_not_found",
            "수정할 변수를 현재 데이터셋 버전에서 찾을 수 없습니다.",
        )
    new_value = None if edit.operation == "set_missing" else edit.value
    _validate_value(parent_column.data_type, new_value, context.parsing)

    child_version_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    child_columns = [
        DatasetColumnRecord(
            column_id=str(uuid4()),
            version_id=child_version_id,
            column_index=item.column_index,
            original_name=item.original_name,
            display_name=item.display_name,
            data_type=item.data_type,
            measurement_level=item.measurement_level,
            role=item.role,
            unit=item.unit,
        )
        for item in context.columns
    ]
    child_column = child_columns[parent_column.column_index]
    base_dir = (
        Path("workspaces") / "datasets" / context.version.dataset_id / "versions" / child_version_id
    )
    rows_relative = base_dir / "canonical.rows.jsonl"
    canonical_manifest_relative = base_dir / "canonical.manifest.json"
    correction_manifest_relative = base_dir / "cell-correction.manifest.json"
    rows_path = settings.workspace_root / rows_relative
    canonical_manifest_path = settings.workspace_root / canonical_manifest_relative
    correction_manifest_path = settings.workspace_root / correction_manifest_relative
    pending_path = settings.workspace_root / base_dir / CELL_CORRECTION_PENDING_NAME
    written_paths = [
        rows_path,
        canonical_manifest_path,
        correction_manifest_path,
        pending_path,
    ]

    try:
        atomic_write_text(
            pending_path,
            _canonical_json(
                {
                    "schema_version": 1,
                    "dataset_id": context.version.dataset_id,
                    "child_version_id": child_version_id,
                }
            )
            + "\n",
        )
        rows_sha256, rows_size, old_value = _write_corrected_rows(
            source=context,
            target_path=rows_path,
            row_index=edit.row_index,
            column_index=parent_column.column_index,
            value=new_value,
        )
        if old_value == new_value:
            raise _error(
                "dataset_cell_correction_no_change",
                "기존 값과 동일하여 새 버전을 만들지 않았습니다.",
            )

        canonical_record = DatasetArtifactRecord(
            artifact_id=str(uuid4()),
            version_id=child_version_id,
            kind=CANONICAL_ROWS_KIND,
            path=rows_relative.as_posix(),
            sha256=rows_sha256,
            media_type=CANONICAL_ROWS_MEDIA_TYPE,
            size_bytes=rows_size,
            created_at=created_at,
        )
        canonical_manifest_record = _write_canonical_manifest(
            target_path=canonical_manifest_path,
            relative_path=canonical_manifest_relative,
            context=context,
            child_version_id=child_version_id,
            child_columns=child_columns,
            canonical=canonical_record,
            created_at=created_at,
        )
        before_hash = _cell_envelope_sha256(
            version_id=context.version.version_id,
            row_index=edit.row_index,
            column_id=parent_column.column_id,
            value=old_value,
        )
        after_hash = _cell_envelope_sha256(
            version_id=child_version_id,
            row_index=edit.row_index,
            column_id=child_column.column_id,
            value=new_value,
        )
        correction_manifest_record, operation_sha256 = _write_correction_manifest(
            target_path=correction_manifest_path,
            relative_path=correction_manifest_relative,
            parent_version_id=context.version.version_id,
            child_version_id=child_version_id,
            parent_canonical_sha256=context.canonical_rows_artifact.sha256,
            child_canonical_sha256=rows_sha256,
            row_index=edit.row_index,
            parent_column_id=parent_column.column_id,
            child_column_id=child_column.column_id,
            operation=edit.operation,
            before_hash=before_hash,
            after_hash=after_hash,
            created_at=created_at,
        )

        # Re-read the complete parent immediately before the write transaction.
        verify_canonical_rows_artifact(context)
        try:
            child_version = insert_dataset_cell_correction_version_records(
                settings.workspace_root,
                parent_version_id=context.version.version_id,
                expected_parent_schema_hash=body.expected_parent_schema_hash,
                expected_parent_canonical_sha256=body.expected_parent_canonical_sha256,
                child_version_id=child_version_id,
                source_sha256=context.version.source_sha256,
                parsing_options_json=context.version.parsing_options_json,
                row_count=context.version.row_count,
                column_count=context.version.column_count,
                schema_hash=context.version.schema_hash,
                created_at=created_at,
                columns=child_columns,
                artifacts=[
                    canonical_record,
                    canonical_manifest_record,
                    correction_manifest_record,
                ],
                lineage=DatasetVersionLineageRecord(
                    child_version_id=child_version_id,
                    parent_version_id=context.version.version_id,
                    operation_kind="cell_correction",
                    operation_schema_version=CELL_CORRECTION_SCHEMA_VERSION,
                    affected_cell_count=1,
                    operation_sha256=operation_sha256,
                    created_at=created_at,
                ),
            )
        except DatasetVersionStorageConflict as exc:
            if exc.code == "dataset_cell_correction_source_changed":
                raise _source_changed() from exc
            if exc.code == "dataset_cell_correction_parent_not_found":
                raise _error(
                    exc.code,
                    "원본 데이터셋 버전을 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ) from exc
            raise _error(
                exc.code,
                "다른 요청이 먼저 새 버전을 생성했습니다. 목록을 새로고침하세요.",
                status.HTTP_409_CONFLICT,
            ) from exc
    except Exception:
        _remove_files(written_paths)
        raise
    try:
        pending_path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        # Startup recovery removes this marker after confirming the DB row.
        pass

    response_version = dataset_version_response_from_records(
        child_version,
        child_columns,
        canonical_record,
        lineage=DatasetVersionLineageRecord(
            child_version_id=child_version_id,
            parent_version_id=context.version.version_id,
            operation_kind="cell_correction",
            operation_schema_version=CELL_CORRECTION_SCHEMA_VERSION,
            affected_cell_count=1,
            operation_sha256=operation_sha256,
            created_at=created_at,
        ),
    )
    return DatasetCellCorrectionResponse(
        correction_schema_version=CELL_CORRECTION_SCHEMA_VERSION,
        parent_version_id=parent_version_id,
        new_version=response_version,
        changed_cell_count=1,
        lineage_sha256=operation_sha256,
        created_at=created_at,
    )


def recover_dataset_cell_correction_files(
    workspace_root: Path,
) -> DatasetCellCorrectionRecovery:
    retained = deleted = pending = 0
    for marker in _iter_pending_markers(workspace_root):
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
            version_dir = marker.parent
            dataset_dir = version_dir.parent.parent
            if (
                not isinstance(payload, dict)
                or payload.get("schema_version") != 1
                or payload.get("dataset_id") != dataset_dir.name
                or payload.get("child_version_id") != version_dir.name
            ):
                pending += 1
                continue
            if get_dataset_version_record(workspace_root, version_dir.name) is not None:
                marker.unlink()
                retained += 1
                continue
            for filename in _CELL_CORRECTION_FILES:
                try:
                    (version_dir / filename).unlink()
                except FileNotFoundError:
                    pass
            marker.unlink()
            deleted += 1
        except (OSError, ValueError, TypeError):
            pending += 1
    return DatasetCellCorrectionRecovery(
        retained=retained,
        deleted=deleted,
        pending=pending,
    )


def _iter_pending_markers(workspace_root: Path) -> Iterator[Path]:
    datasets_root = workspace_root / "workspaces" / "datasets"
    if not datasets_root.is_dir():
        return
    try:
        dataset_entries = list(os.scandir(datasets_root))
    except OSError:
        return
    for dataset_entry in dataset_entries:
        if not _safe_directory_entry(dataset_entry):
            continue
        versions_root = Path(dataset_entry.path) / "versions"
        if _path_is_reparse_point(versions_root) or not versions_root.is_dir():
            continue
        try:
            version_entries = list(os.scandir(versions_root))
        except OSError:
            continue
        for version_entry in version_entries:
            if not _safe_directory_entry(version_entry):
                continue
            marker = Path(version_entry.path) / CELL_CORRECTION_PENDING_NAME
            if not _path_is_reparse_point(marker) and marker.is_file():
                yield marker


def _safe_directory_entry(entry: os.DirEntry[str]) -> bool:
    try:
        attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
        return entry.is_dir(follow_symlinks=False) and not (
            attributes & _FILE_ATTRIBUTE_REPARSE_POINT
        )
    except OSError:
        return False


def _path_is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return False


def _write_corrected_rows(
    *,
    source: DatasetRowsContext,
    target_path: Path,
    row_index: int,
    column_index: int,
    value: str | None,
) -> tuple[str, int, str | None]:
    digest = hashlib.sha256()
    size_bytes = 0
    old_value: str | None = None
    found = False

    def writer(temp_path: Path) -> None:
        nonlocal size_bytes, old_value, found
        with temp_path.open("wb") as handle:
            for current_index, values in enumerate(iter_dataset_rows(source)):
                if current_index == row_index:
                    old_value = values[column_index]
                    values[column_index] = value
                    found = True
                payload = (
                    json.dumps(
                        {"row_index": current_index, "values": values},
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
                digest.update(payload)
                size_bytes += len(payload)
                handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())

    atomic_replace(target_path, writer)
    if not found:
        raise _error(
            "dataset_cell_correction_row_out_of_range",
            "수정할 행이 데이터셋 범위를 벗어났습니다.",
        )
    return digest.hexdigest(), size_bytes, old_value


def _write_canonical_manifest(
    *,
    target_path: Path,
    relative_path: Path,
    context: DatasetRowsContext,
    child_version_id: str,
    child_columns: list[DatasetColumnRecord],
    canonical: DatasetArtifactRecord,
    created_at: str,
) -> DatasetArtifactRecord:
    version = context.version
    payload = {
        "manifest_schema_version": CANONICAL_MANIFEST_SCHEMA_VERSION,
        "artifact_format": CANONICAL_FORMAT,
        "dataset_id": version.dataset_id,
        "version_id": child_version_id,
        "source_sha256": version.source_sha256,
        "schema_hash_at_creation": version.schema_hash,
        "row_count": version.row_count,
        "column_count": version.column_count,
        "columns": [
            {
                "column_id": item.column_id,
                "column_index": item.column_index,
                "original_name": item.original_name,
                "data_type": item.data_type,
            }
            for item in child_columns
        ],
        "data": {
            "kind": canonical.kind,
            "path": canonical.path,
            "sha256": canonical.sha256,
            "media_type": canonical.media_type,
            "size_bytes": canonical.size_bytes,
        },
        "created_at": created_at,
    }
    text = _canonical_json(payload) + "\n"
    atomic_write_text(target_path, text)
    encoded = text.encode("utf-8")
    return DatasetArtifactRecord(
        artifact_id=str(uuid4()),
        version_id=child_version_id,
        kind=CANONICAL_MANIFEST_KIND,
        path=relative_path.as_posix(),
        sha256=hashlib.sha256(encoded).hexdigest(),
        media_type=CANONICAL_MANIFEST_MEDIA_TYPE,
        size_bytes=len(encoded),
        created_at=created_at,
    )


def _write_correction_manifest(
    *,
    target_path: Path,
    relative_path: Path,
    parent_version_id: str,
    child_version_id: str,
    parent_canonical_sha256: str,
    child_canonical_sha256: str,
    row_index: int,
    parent_column_id: str,
    child_column_id: str,
    operation: str,
    before_hash: str,
    after_hash: str,
    created_at: str,
) -> tuple[DatasetArtifactRecord, str]:
    payload = {
        "correction_schema_version": CELL_CORRECTION_SCHEMA_VERSION,
        "operation_kind": "cell_correction",
        "parent_version_id": parent_version_id,
        "child_version_id": child_version_id,
        "parent_canonical_sha256": parent_canonical_sha256,
        "child_canonical_sha256": child_canonical_sha256,
        "row_index": row_index,
        "parent_column_id": parent_column_id,
        "child_column_id": child_column_id,
        "operation": operation,
        "before_cell_envelope_sha256": before_hash,
        "after_cell_envelope_sha256": after_hash,
        "affected_cell_count": 1,
        "created_at": created_at,
    }
    operation_sha256 = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    stored = {**payload, "operation_sha256": operation_sha256}
    text = _canonical_json(stored) + "\n"
    atomic_write_text(target_path, text)
    encoded = text.encode("utf-8")
    return (
        DatasetArtifactRecord(
            artifact_id=str(uuid4()),
            version_id=child_version_id,
            kind=CELL_CORRECTION_MANIFEST_KIND,
            path=relative_path.as_posix(),
            sha256=hashlib.sha256(encoded).hexdigest(),
            media_type=CELL_CORRECTION_MANIFEST_MEDIA_TYPE,
            size_bytes=len(encoded),
            created_at=created_at,
        ),
        operation_sha256,
    )


def _cell_envelope_sha256(
    *,
    version_id: str,
    row_index: int,
    column_id: str,
    value: str | None,
) -> str:
    return hashlib.sha256(
        _canonical_json(
            {
                "version_id": version_id,
                "row_index": row_index,
                "column_id": column_id,
                "canonical_value": value,
            }
        ).encode("utf-8")
    ).hexdigest()


def _validate_value(
    data_type: str,
    value: str | None,
    parsing: ConfirmedParsingOptions,
) -> None:
    if value is None or data_type == DatasetColumnDataType.TEXT.value:
        return
    if value == "":
        raise _invalid_value()
    if data_type in {
        DatasetColumnDataType.INTEGER.value,
        DatasetColumnDataType.DECIMAL.value,
    }:
        normalized = value
        thousands = parsing.thousands
        decimal = parsing.decimal
        if thousands is not None:
            normalized = normalized.replace(thousands, "")
        if decimal != ".":
            normalized = normalized.replace(decimal, ".")
        try:
            number = Decimal(normalized)
        except InvalidOperation as exc:
            raise _invalid_value() from exc
        if not number.is_finite():
            raise _invalid_value()
        if (
            data_type == DatasetColumnDataType.INTEGER.value
            and number != number.to_integral_value()
        ):
            raise _invalid_value()
        return
    if data_type == DatasetColumnDataType.BOOLEAN.value:
        if value.strip().lower() not in {"true", "false", "yes", "no"}:
            raise _invalid_value()
        return
    if data_type == DatasetColumnDataType.DATETIME.value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise _invalid_value() from exc
        if not math.isfinite(parsed.timestamp()):
            raise _invalid_value()


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _remove_files(paths: list[Path]) -> None:
    for path in reversed(paths):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _invalid_value() -> ApiError:
    return _error(
        "dataset_cell_correction_value_invalid",
        "입력한 값이 변수의 데이터 타입과 일치하지 않습니다.",
    )


def _source_changed() -> ApiError:
    return _error(
        "dataset_cell_correction_source_changed",
        "원본 데이터셋 버전이 확인 이후 변경되었습니다. 다시 불러오세요.",
        status.HTTP_409_CONFLICT,
    )


def _error(code: str, message: str, status_code: int = 422) -> ApiError:
    return ApiError(code=code, message=message, status_code=status_code)
