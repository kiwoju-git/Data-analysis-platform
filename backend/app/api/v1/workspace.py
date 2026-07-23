from fastapi import APIRouter, Request

from app.api.v1.schemas.common import WorkspaceSummaryResponse
from app.storage.metadata import get_workspace_summary_counts

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/summary", response_model=WorkspaceSummaryResponse)
def get_workspace_summary_route(request: Request) -> WorkspaceSummaryResponse:
    counts = get_workspace_summary_counts(request.app.state.settings.workspace_root)
    return WorkspaceSummaryResponse(**counts.__dict__)
