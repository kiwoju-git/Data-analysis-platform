import json
from pathlib import Path
from uuid import UUID

from fastapi import status

from app.api.v1.schemas.analyses import (
    AnalysisRunListItemResponse,
    AnalysisRunListResponse,
    AnalysisRunState,
    AnalysisRunStatusResponse,
)
from app.core.errors import ApiError
from app.services.analysis_run_execution import utc_now as _utc_now
from app.storage.metadata import (
    AnalysisRunRecord,
    count_analysis_artifact_records,
    get_analysis_run_record,
    list_analysis_run_records,
    update_analysis_run_status_record,
)

CANCELLABLE_STATES = {AnalysisRunState.QUEUED.value, AnalysisRunState.RUNNING.value}
TERMINAL_STATES = {
    AnalysisRunState.SUCCEEDED.value,
    AnalysisRunState.FAILED.value,
    AnalysisRunState.CANCELLED.value,
}


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


def list_analysis_runs(
    workspace_root: Path,
    *,
    dataset_version_id: UUID | None,
    method_id: str | None,
    run_status: AnalysisRunState | None,
    stale: bool | None,
    result_available: bool | None,
    limit: int,
    offset: int,
) -> AnalysisRunListResponse:
    records = list_analysis_run_records(
        workspace_root,
        dataset_version_id=None if dataset_version_id is None else str(dataset_version_id),
        method_id=method_id,
        status=None if run_status is None else run_status.value,
        stale=stale,
        result_available=result_available,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(records) > limit
    records = records[:limit]
    items = [
        _to_list_item_response(
            workspace_root,
            record,
        )
        for record in records
    ]
    return AnalysisRunListResponse(
        dataset_version_id=dataset_version_id,
        method_id=method_id,
        status=run_status,
        stale=stale,
        result_available=result_available,
        limit=limit,
        offset=offset,
        returned_count=len(items),
        has_more=has_more,
        runs=items,
    )


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


def _to_list_item_response(
    workspace_root: Path,
    record: AnalysisRunRecord,
) -> AnalysisRunListItemResponse:
    artifact_count = count_analysis_artifact_records(workspace_root, record.analysis_id)
    return AnalysisRunListItemResponse(
        analysis_id=UUID(record.analysis_id),
        method_id=record.method_id,
        method_version=record.method_version,
        dataset_version_id=None
        if record.dataset_version_id is None
        else UUID(record.dataset_version_id),
        status=AnalysisRunState(record.status),
        stale=record.stale,
        result_available=record.result_path is not None and record.result_sha256 is not None,
        artifact_count=artifact_count,
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
