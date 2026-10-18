from pathlib import Path
from uuid import UUID

from fastapi import status

from app.api.v1.schemas.common import JobState, JobStatusResponse
from app.core.errors import ApiError
from app.storage.metadata import JobRecord, get_job_record


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

    raise ApiError(
        code="job_cancellation_unsupported",
        message="현재 작업은 서버 취소를 지원하지 않습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


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
