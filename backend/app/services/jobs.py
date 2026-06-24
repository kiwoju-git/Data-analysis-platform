from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import status

from app.api.v1.schemas.common import JobState, JobStatusResponse
from app.core.errors import ApiError
from app.storage.metadata import JobRecord, get_job_record, update_job_cancellation_record

CANCELLABLE_STATES = {JobState.QUEUED.value, JobState.RUNNING.value}
TERMINAL_STATES = {JobState.SUCCEEDED.value, JobState.FAILED.value, JobState.CANCELLED.value}


def get_job_status(workspace_root: Path, job_id: UUID) -> JobStatusResponse:
    record = get_job_record(workspace_root, str(job_id))
    if record is None:
        raise ApiError(
            code="job_not_found",
            message="요청한 작업을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _to_response(record)


def request_job_cancellation(workspace_root: Path, job_id: UUID) -> JobStatusResponse:
    record = get_job_record(workspace_root, str(job_id))
    if record is None:
        raise ApiError(
            code="job_not_found",
            message="요청한 작업을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if record.state in TERMINAL_STATES:
        raise ApiError(
            code="job_not_cancellable",
            message="이미 종료된 작업은 취소 요청할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=record.state,
        )

    if record.state in CANCELLABLE_STATES:
        updated = update_job_cancellation_record(
            workspace_root=workspace_root,
            job_id=str(job_id),
            updated_at=_utc_now(),
        )
        if updated is not None:
            record = updated

    return _to_response(record)


def _to_response(record: JobRecord) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=UUID(record.job_id),
        analysis_id=None if record.analysis_id is None else UUID(record.analysis_id),
        job_type=record.job_type,
        state=JobState(record.state),
        progress=record.progress,
        cancel_requested=record.cancel_requested,
        error_code=record.error_code,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
