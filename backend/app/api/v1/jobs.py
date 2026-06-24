from uuid import UUID

from fastapi import APIRouter, Request

from app.api.v1.schemas.common import JobStatusResponse
from app.services.jobs import get_job_status, request_job_cancellation

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_route(
    request: Request,
    job_id: UUID,
) -> JobStatusResponse:
    return get_job_status(
        workspace_root=request.app.state.settings.workspace_root,
        job_id=job_id,
    )


@router.delete("/{job_id}", response_model=JobStatusResponse)
def cancel_job_route(
    request: Request,
    job_id: UUID,
) -> JobStatusResponse:
    return request_job_cancellation(
        workspace_root=request.app.state.settings.workspace_root,
        job_id=job_id,
    )
