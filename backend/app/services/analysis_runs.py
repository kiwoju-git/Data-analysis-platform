import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import (
    AnalysisFilterSnapshot,
    AnalysisProvenance,
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunState,
    AnalysisRunStatusResponse,
    AnalysisWarning,
    MethodAvailability,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.dataset_rows import (
    DatasetRowsContext,
    get_dataset_rows_context,
    iter_dataset_rows,
)
from app.statistics.descriptive import DescriptiveColumn, describe_numeric_columns
from app.storage.atomic import atomic_write_bytes
from app.storage.metadata import (
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetColumnRecord,
    count_analysis_artifact_records,
    get_analysis_run_record,
    insert_analysis_run_record_with_artifacts,
    update_analysis_run_status_record,
)

APP_VERSION = "0.1.0"
CONFIG_SCHEMA_VERSION = 2
ROW_SNAPSHOT_SCHEMA_VERSION = 1
ROW_SNAPSHOT_ARTIFACT_KIND = "analysis_row_snapshot"
ROW_SNAPSHOT_MEDIA_TYPE = "application/json"
MAX_DESCRIPTIVE_COLUMNS = 100
MAX_FILTER_CONDITIONS = 20
MAX_FILTER_STRING_LENGTH = 200
NUMERIC_DATA_TYPES = {"integer", "decimal"}
FILTER_OPERATORS = {
    "is_missing",
    "is_not_missing",
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
}
NUMERIC_FILTER_OPERATORS = {"gt", "gte", "lt", "lte"}
CANCELLABLE_STATES = {AnalysisRunState.QUEUED.value, AnalysisRunState.RUNNING.value}
TERMINAL_STATES = {
    AnalysisRunState.SUCCEEDED.value,
    AnalysisRunState.FAILED.value,
    AnalysisRunState.CANCELLED.value,
}


@dataclass(frozen=True)
class _RowSnapshotArtifact:
    record: AnalysisArtifactRecord
    relative_path: Path
    payload: dict[str, Any]
    included_row_indices: tuple[int, ...] | None


@dataclass(frozen=True)
class _FilterCondition:
    column: DatasetColumnRecord
    operator: str
    value: object | None = None


def create_analysis_run(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    method = get_analysis_method(request.method_id)
    if method is None:
        raise ApiError(
            code="analysis_method_not_found",
            message="요청한 분석 메서드를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if method.method_version != request.method_version:
        raise ApiError(
            code="analysis_method_version_mismatch",
            message="요청한 분석 메서드 버전이 현재 registry와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    if method.availability != MethodAvailability.AVAILABLE:
        raise ApiError(
            code="analysis_method_not_available",
            message="이 분석 메서드는 아직 실행할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=method.availability.value,
        )

    if request.method_id == "eda.descriptive":
        return _run_descriptive_analysis(settings, request)

    raise ApiError(
        code="analysis_method_not_available",
        message="이 분석 메서드는 아직 실행할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
        developer_detail=method.availability.value,
    )


def get_analysis_run_status(
    workspace_root: Path,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    record = get_analysis_run_record(workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _to_response(workspace_root, record)


def get_analysis_run_result(
    settings: Settings,
    analysis_id: UUID,
) -> AnalysisResultEnvelope:
    record = get_analysis_run_record(settings.workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if record.result_path is None or record.result_sha256 is None:
        raise ApiError(
            code="analysis_result_not_available",
            message="저장된 분석 결과가 아직 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    result_path = _safe_result_path(settings.workspace_root, record.result_path)
    if not result_path.exists():
        raise ApiError(
            code="analysis_result_file_missing",
            message="저장된 분석 결과 파일을 찾을 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    result_bytes = result_path.read_bytes()
    if hashlib.sha256(result_bytes).hexdigest() != record.result_sha256:
        raise ApiError(
            code="analysis_result_checksum_mismatch",
            message="저장된 분석 결과 파일이 메타데이터와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    try:
        return AnalysisResultEnvelope.model_validate_json(result_bytes)
    except ValidationError as exc:
        raise ApiError(
            code="analysis_result_envelope_invalid",
            message="저장된 분석 결과 형식이 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        ) from exc


def request_analysis_run_cancellation(
    workspace_root: Path,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    record = get_analysis_run_record(workspace_root, str(analysis_id))
    if record is None:
        raise ApiError(
            code="analysis_run_not_found",
            message="요청한 분석 실행을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if record.status in TERMINAL_STATES:
        raise ApiError(
            code="analysis_run_not_cancellable",
            message="이미 종료된 분석 실행은 취소 요청할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=record.status,
        )

    if record.status in CANCELLABLE_STATES:
        updated = update_analysis_run_status_record(
            workspace_root=workspace_root,
            analysis_id=str(analysis_id),
            status=AnalysisRunState.CANCEL_REQUESTED.value,
            updated_at=_utc_now(),
        )
        if updated is not None:
            record = updated

    return _to_response(workspace_root, record)


def _run_descriptive_analysis(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    if request.dataset_version_id is None:
        raise ApiError(
            code="dataset_version_required",
            message="기술통계 실행에는 데이터셋 버전이 필요합니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_descriptive_columns(context, request.options)
    analysis_id = uuid4()
    completed_at = _utc_now()
    row_snapshot = _create_row_snapshot_artifact(
        settings=settings,
        analysis_id=str(analysis_id),
        context=context,
        filter_snapshot=request.filter_snapshot,
        created_at=completed_at,
    )
    result_path: Path | None = None

    try:
        result = describe_numeric_columns(
            _iter_rows_for_snapshot(context, row_snapshot),
            selected_columns,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        warnings = _descriptive_warnings(result)
        provenance = AnalysisProvenance(
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            source_schema_hash=context.version.schema_hash,
            filter_snapshot_sha256=str(row_snapshot.payload["filter_snapshot_sha256"]),
            row_snapshot_sha256=row_snapshot.record.sha256,
            row_count_total=context.version.row_count,
            row_count_included=int(row_snapshot.payload["selection"]["row_count_included"]),
            app_version=APP_VERSION,
        )
        envelope = AnalysisResultEnvelope(
            analysis_id=analysis_id,
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=request.dataset_version_id,
            status="succeeded",
            warnings=warnings,
            provenance=provenance,
            result=result,
        )

        result_bytes = _canonical_json_bytes(envelope.model_dump(mode="json"))
        result_relative_path = _analysis_result_relative_path(str(analysis_id))
        result_path = settings.workspace_root / result_relative_path
        atomic_write_bytes(result_path, result_bytes)
        result_sha256 = hashlib.sha256(result_bytes).hexdigest()

        insert_analysis_run_record_with_artifacts(
            settings.workspace_root,
            AnalysisRunRecord(
                analysis_id=str(analysis_id),
                method_id=request.method_id,
                method_version=request.method_version,
                dataset_version_id=str(request.dataset_version_id),
                config_json=_analysis_config_json(request, row_snapshot),
                status=AnalysisRunState.SUCCEEDED.value,
                result_path=result_relative_path.as_posix(),
                result_sha256=result_sha256,
                stale=False,
                created_at=completed_at,
                updated_at=completed_at,
                completed_at=completed_at,
                app_version=APP_VERSION,
            ),
            artifacts=[row_snapshot.record],
        )
    except Exception:
        _remove_file_if_exists(settings.workspace_root / row_snapshot.relative_path)
        if result_path is not None:
            _remove_file_if_exists(result_path)
        raise
    return envelope


def _selected_descriptive_columns(
    context: DatasetRowsContext,
    options: dict[str, Any],
) -> list[DescriptiveColumn]:
    column_ids = options.get("column_ids")
    if not isinstance(column_ids, list) or not column_ids:
        raise ApiError(
            code="descriptive_columns_required",
            message="기술통계를 계산할 컬럼을 하나 이상 선택해야 합니다.",
        )
    if len(column_ids) > MAX_DESCRIPTIVE_COLUMNS:
        raise ApiError(
            code="too_many_descriptive_columns",
            message="한 번에 요청한 기술통계 컬럼 수가 허용 범위를 초과했습니다.",
        )
    if any(not isinstance(column_id, str) or not column_id for column_id in column_ids):
        raise ApiError(
            code="invalid_descriptive_columns",
            message="기술통계 컬럼 ID 목록이 올바르지 않습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    seen: set[str] = set()
    selected: list[DescriptiveColumn] = []
    for column_id in column_ids:
        if column_id in seen:
            raise ApiError(
                code="duplicate_descriptive_column",
                message="기술통계 컬럼 ID가 중복되었습니다.",
            )
        seen.add(column_id)

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="descriptive_column_not_found",
                message="요청한 기술통계 컬럼을 찾을 수 없습니다.",
            )
        _validate_descriptive_column(column)
        selected.append(
            DescriptiveColumn(
                column_id=column.column_id,
                column_index=column.column_index,
                display_name=column.display_name,
                data_type=column.data_type,
                measurement_level=column.measurement_level,
                role=column.role,
                unit=column.unit,
            ),
        )
    return selected


def _validate_descriptive_column(column: DatasetColumnRecord) -> None:
    if column.role == "id" or column.measurement_level == "id":
        raise ApiError(
            code="descriptive_column_is_id",
            message="ID 컬럼은 기술통계 계산 대상에서 제외해야 합니다.",
        )
    if column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="descriptive_column_not_numeric",
            message="기술통계는 현재 숫자형 컬럼만 지원합니다.",
        )


def _descriptive_warnings(result: dict[str, object]) -> list[AnalysisWarning]:
    warnings: list[AnalysisWarning] = []
    columns = result.get("columns")
    if not isinstance(columns, list):
        return warnings

    for column in columns:
        if not isinstance(column, dict):
            continue
        column_warnings = column.get("warnings")
        display_name = column.get("display_name")
        if not isinstance(column_warnings, list) or not isinstance(display_name, str):
            continue
        if "non_numeric_values_excluded" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="non_numeric_values_excluded",
                    severity="warning",
                    message=f"{display_name}: 숫자로 해석할 수 없는 값은 제외했습니다.",
                ),
            )
        if "no_numeric_values" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="no_numeric_values",
                    severity="warning",
                    message=f"{display_name}: 사용할 수 있는 숫자 값이 없습니다.",
                ),
            )
        if "constant_column" in column_warnings:
            warnings.append(
                AnalysisWarning(
                    code="constant_column",
                    severity="info",
                    message=f"{display_name}: 모든 사용 값이 동일합니다.",
                ),
            )
    return warnings


def _create_row_snapshot_artifact(
    *,
    settings: Settings,
    analysis_id: str,
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
    created_at: str,
) -> _RowSnapshotArtifact:
    filter_snapshot_payload = filter_snapshot.model_dump(mode="json")
    filter_snapshot_sha256 = hashlib.sha256(
        _canonical_json_bytes(filter_snapshot_payload),
    ).hexdigest()
    included_row_indices = _freeze_row_indices(context, filter_snapshot)
    row_count_included = (
        context.version.row_count if included_row_indices is None else len(included_row_indices)
    )
    row_count_excluded = context.version.row_count - row_count_included
    selection: dict[str, Any] = {
        "kind": "all_rows" if included_row_indices is None else "row_ranges",
        "row_count_total": context.version.row_count,
        "row_count_included": row_count_included,
        "row_count_excluded": row_count_excluded,
    }
    if included_row_indices is not None:
        selection["row_ranges"] = _row_ranges(included_row_indices)

    artifact_id = str(uuid4())
    relative_path = _row_snapshot_relative_path(analysis_id)
    payload: dict[str, Any] = {
        "artifact_schema_version": ROW_SNAPSHOT_SCHEMA_VERSION,
        "artifact_kind": ROW_SNAPSHOT_ARTIFACT_KIND,
        "analysis_id": analysis_id,
        "dataset_version_id": context.version.version_id,
        "source_schema_hash": context.version.schema_hash,
        "source_canonical_artifact": {
            "kind": context.canonical_rows_artifact.kind,
            "sha256": context.canonical_rows_artifact.sha256,
            "media_type": context.canonical_rows_artifact.media_type,
            "size_bytes": context.canonical_rows_artifact.size_bytes,
        },
        "filter_snapshot": filter_snapshot_payload,
        "filter_snapshot_sha256": filter_snapshot_sha256,
        "row_identity": {
            "kind": "canonical_row_index",
            "base": 0,
        },
        "selection": selection,
        "created_at": created_at,
    }
    artifact_bytes = _canonical_json_bytes(payload)
    artifact_path = settings.workspace_root / relative_path
    atomic_write_bytes(artifact_path, artifact_bytes)

    return _RowSnapshotArtifact(
        record=AnalysisArtifactRecord(
            artifact_id=artifact_id,
            analysis_id=analysis_id,
            kind=ROW_SNAPSHOT_ARTIFACT_KIND,
            path=relative_path.as_posix(),
            sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            media_type=ROW_SNAPSHOT_MEDIA_TYPE,
            created_at=created_at,
        ),
        relative_path=relative_path,
        payload=payload,
        included_row_indices=included_row_indices,
    )


def _freeze_row_indices(
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
) -> tuple[int, ...] | None:
    if not filter_snapshot.conditions:
        return None

    conditions = _parse_filter_conditions(context, filter_snapshot)
    included_row_indices: list[int] = []
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if all(_row_matches_condition(row, condition, context) for condition in conditions):
            included_row_indices.append(row_index)
    return tuple(included_row_indices)


def _parse_filter_conditions(
    context: DatasetRowsContext,
    filter_snapshot: AnalysisFilterSnapshot,
) -> list[_FilterCondition]:
    if filter_snapshot.expression_version != 1:
        raise ApiError(
            code="filter_expression_version_unsupported",
            message="지원하지 않는 필터 표현식 버전입니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if len(filter_snapshot.conditions) > MAX_FILTER_CONDITIONS:
        raise ApiError(
            code="too_many_filter_conditions",
            message="필터 조건 수가 허용 범위를 초과했습니다.",
        )

    columns_by_id = {column.column_id: column for column in context.columns}
    conditions: list[_FilterCondition] = []
    for raw_condition in filter_snapshot.conditions:
        if not isinstance(raw_condition, dict):
            raise _invalid_filter_condition()

        column_id = raw_condition.get("column_id")
        operator = raw_condition.get("operator")
        if not isinstance(column_id, str) or not column_id:
            raise _invalid_filter_condition()
        if not isinstance(operator, str) or operator not in FILTER_OPERATORS:
            raise ApiError(
                code="filter_operator_not_supported",
                message="지원하지 않는 필터 연산자입니다.",
            )

        column = columns_by_id.get(column_id)
        if column is None:
            raise ApiError(
                code="filter_column_not_found",
                message="필터 컬럼을 찾을 수 없습니다.",
            )

        if operator in {"is_missing", "is_not_missing"}:
            conditions.append(_FilterCondition(column=column, operator=operator))
            continue

        if "value" not in raw_condition:
            raise ApiError(
                code="filter_value_required",
                message="필터 조건 값이 필요합니다.",
            )
        value = raw_condition["value"]
        _validate_filter_value(column, operator, value)
        conditions.append(_FilterCondition(column=column, operator=operator, value=value))

    return conditions


def _validate_filter_value(
    column: DatasetColumnRecord,
    operator: str,
    value: object,
) -> None:
    if value is None:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    if operator in NUMERIC_FILTER_OPERATORS and column.data_type not in NUMERIC_DATA_TYPES:
        raise ApiError(
            code="filter_operator_not_supported_for_column",
            message="이 컬럼에는 요청한 필터 연산자를 사용할 수 없습니다.",
        )
    if column.data_type in NUMERIC_DATA_TYPES:
        _filter_decimal_value(value)
        return
    if not isinstance(value, str) or len(value) > MAX_FILTER_STRING_LENGTH:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )


def _row_matches_condition(
    row: list[str | None],
    condition: _FilterCondition,
    context: DatasetRowsContext,
) -> bool:
    value = row[condition.column.column_index] if condition.column.column_index < len(row) else None
    missing = value is None or value.strip() == ""

    if condition.operator == "is_missing":
        return missing
    if condition.operator == "is_not_missing":
        return not missing
    if missing:
        return False
    assert value is not None

    if condition.column.data_type in NUMERIC_DATA_TYPES:
        row_value = _parse_filter_decimal(
            value,
            decimal=context.parsing.decimal,
            thousands=context.parsing.thousands,
        )
        filter_value = _filter_decimal_value(condition.value)
        if row_value is None:
            return False
        return _compare_values(row_value, filter_value, condition.operator)

    string_filter_value = condition.value
    if not isinstance(string_filter_value, str):
        return False
    return _compare_values(value, string_filter_value, condition.operator)


def _iter_rows_for_snapshot(
    context: DatasetRowsContext,
    row_snapshot: _RowSnapshotArtifact,
) -> Iterator[list[str | None]]:
    if row_snapshot.included_row_indices is None:
        yield from iter_dataset_rows(context)
        return

    included = set(row_snapshot.included_row_indices)
    for row_index, row in enumerate(iter_dataset_rows(context)):
        if row_index in included:
            yield row


def _compare_values(left: Any, right: Any, operator: str) -> bool:
    if operator == "eq":
        return left == right
    if operator == "ne":
        return left != right
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    return False


def _parse_filter_decimal(
    value: str,
    *,
    decimal: str,
    thousands: str | None,
) -> Decimal | None:
    normalized = value.strip()
    if normalized == "":
        return None
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return parsed


def _filter_decimal_value(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    if not isinstance(value, int | float | str):
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    try:
        parsed = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        ) from exc
    if not parsed.is_finite():
        raise ApiError(
            code="filter_value_invalid",
            message="필터 조건 값이 올바르지 않습니다.",
        )
    return parsed


def _row_ranges(row_indices: tuple[int, ...]) -> list[dict[str, int]]:
    if not row_indices:
        return []

    ranges: list[dict[str, int]] = []
    range_start = row_indices[0]
    previous = row_indices[0]
    for row_index in row_indices[1:]:
        if row_index == previous + 1:
            previous = row_index
            continue
        ranges.append({"start": range_start, "end": previous + 1})
        range_start = row_index
        previous = row_index
    ranges.append({"start": range_start, "end": previous + 1})
    return ranges


def _invalid_filter_condition() -> ApiError:
    return ApiError(
        code="invalid_filter_condition",
        message="필터 조건 형식이 올바르지 않습니다.",
    )


def _analysis_config_json(
    request: AnalysisRunRequest,
    row_snapshot: _RowSnapshotArtifact,
) -> str:
    return json.dumps(
        {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "filter_snapshot": request.filter_snapshot.model_dump(mode="json"),
            "filter_snapshot_sha256": row_snapshot.payload["filter_snapshot_sha256"],
            "row_snapshot": {
                "artifact_id": row_snapshot.record.artifact_id,
                "kind": row_snapshot.record.kind,
                "path": row_snapshot.record.path,
                "sha256": row_snapshot.record.sha256,
                "media_type": row_snapshot.record.media_type,
                "row_count_total": row_snapshot.payload["selection"]["row_count_total"],
                "row_count_included": row_snapshot.payload["selection"]["row_count_included"],
            },
            "roles": request.roles,
            "options": request.options,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _analysis_result_relative_path(analysis_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / "result.json"


def _row_snapshot_relative_path(analysis_id: str) -> Path:
    return Path("workspaces") / "analyses" / analysis_id / "row_snapshot.json"


def _safe_result_path(workspace_root: Path, stored_path: str) -> Path:
    relative_path = Path(stored_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ApiError(
            code="analysis_result_path_invalid",
            message="저장된 분석 결과 메타데이터가 올바르지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return workspace_root / relative_path


def _remove_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _to_response(workspace_root: Path, record: AnalysisRunRecord) -> AnalysisRunStatusResponse:
    config_schema_version = _config_schema_version(record.config_json)
    artifact_count = count_analysis_artifact_records(workspace_root, record.analysis_id)
    return AnalysisRunStatusResponse(
        analysis_id=UUID(record.analysis_id),
        method_id=record.method_id,
        method_version=record.method_version,
        dataset_version_id=None
        if record.dataset_version_id is None
        else UUID(record.dataset_version_id),
        status=AnalysisRunState(record.status),
        config_schema_version=config_schema_version,
        result_available=record.result_path is not None and record.result_sha256 is not None,
        artifact_count=artifact_count,
        stale=record.stale,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


def _config_schema_version(config_json: str) -> int:
    try:
        payload = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    if not isinstance(payload, dict):
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ApiError(
            code="analysis_run_metadata_invalid",
            message="분석 실행 메타데이터를 읽을 수 없습니다.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return schema_version


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
