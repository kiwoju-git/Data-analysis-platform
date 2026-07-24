from fastapi import APIRouter, Request

from app.api.v1.schemas.visualizations import GraphPreviewRequest, GraphPreviewResponse
from app.services.visualization_preview import create_graph_preview

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


@router.post("/preview", response_model=GraphPreviewResponse)
def preview_visualization(
    payload: GraphPreviewRequest,
    request: Request,
) -> GraphPreviewResponse:
    return create_graph_preview(request.app.state.settings, payload)
