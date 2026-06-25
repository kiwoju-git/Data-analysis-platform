from uuid import UUID

from fastapi import APIRouter, Request, status

from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    AnalysisRunStatusResponse,
)
from app.services.analysis_runs import (
    create_analysis_run,
    get_analysis_run_result,
    get_analysis_run_status,
    request_analysis_run_cancellation,
)

router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])


@router.post(
    "",
    response_model=AnalysisResultEnvelope,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_run_route(
    request: Request,
    body: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    return create_analysis_run(
        settings=request.app.state.settings,
        request=body,
    )


@router.get("/{analysis_id}/result", response_model=AnalysisResultEnvelope)
def get_analysis_run_result_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisResultEnvelope:
    return get_analysis_run_result(
        settings=request.app.state.settings,
        analysis_id=analysis_id,
    )


@router.get("/{analysis_id}", response_model=AnalysisRunStatusResponse)
def get_analysis_run_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    return get_analysis_run_status(
        workspace_root=request.app.state.settings.workspace_root,
        analysis_id=analysis_id,
    )


@router.delete("/{analysis_id}", response_model=AnalysisRunStatusResponse)
def cancel_analysis_run_route(
    request: Request,
    analysis_id: UUID,
) -> AnalysisRunStatusResponse:
    return request_analysis_run_cancellation(
        workspace_root=request.app.state.settings.workspace_root,
        analysis_id=analysis_id,
    )
