import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import status

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import (
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
    AnalysisRunRecord,
    DatasetColumnRecord,
    count_analysis_artifact_records,
    get_analysis_run_record,
    insert_analysis_run_record,
    update_analysis_run_status_record,
)

APP_VERSION = "0.1.0"
CONFIG_SCHEMA_VERSION = 1
MAX_DESCRIPTIVE_COLUMNS = 100
NUMERIC_DATA_TYPES = {"integer", "decimal"}
CANCELLABLE_STATES = {AnalysisRunState.QUEUED.value, AnalysisRunState.RUNNING.value}
TERMINAL_STATES = {
    AnalysisRunState.SUCCEEDED.value,
    AnalysisRunState.FAILED.value,
    AnalysisRunState.CANCELLED.value,
}


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

    if request.filter_snapshot.conditions:
        raise ApiError(
            code="analysis_filters_not_supported",
            message="현재 기술통계 slice는 필터 스냅샷 실행을 아직 지원하지 않습니다.",
        )

    context = get_dataset_rows_context(settings, request.dataset_version_id)
    selected_columns = _selected_descriptive_columns(context, request.options)
    result = describe_numeric_columns(
        iter_dataset_rows(context),
        selected_columns,
        decimal=context.parsing.decimal,
        thousands=context.parsing.thousands,
    )
    warnings = _descriptive_warnings(result)
    analysis_id = uuid4()
    completed_at = _utc_now()
    provenance = AnalysisProvenance(
        method_id=request.method_id,
        method_version=request.method_version,
        dataset_version_id=request.dataset_version_id,
        source_schema_hash=context.version.schema_hash,
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
    atomic_write_bytes(settings.workspace_root / result_relative_path, result_bytes)
    result_sha256 = hashlib.sha256(result_bytes).hexdigest()

    insert_analysis_run_record(
        settings.workspace_root,
        AnalysisRunRecord(
            analysis_id=str(analysis_id),
            method_id=request.method_id,
            method_version=request.method_version,
            dataset_version_id=str(request.dataset_version_id),
            config_json=_analysis_config_json(request),
            status=AnalysisRunState.SUCCEEDED.value,
            result_path=result_relative_path.as_posix(),
            result_sha256=result_sha256,
            stale=False,
            created_at=completed_at,
            updated_at=completed_at,
            completed_at=completed_at,
            app_version=APP_VERSION,
        ),
    )
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


def _analysis_config_json(request: AnalysisRunRequest) -> str:
    return json.dumps(
        {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "filter_snapshot": request.filter_snapshot.model_dump(mode="json"),
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
