from fastapi import APIRouter, Request

from app.api.v1.schemas.analyses import (
    GageRrPreflightRequest,
    GageRrPreflightResponse,
)
from app.services.gage_rr import get_gage_rr_preflight

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post("/gage-rr/preflight", response_model=GageRrPreflightResponse)
def get_gage_rr_preflight_route(
    request: Request,
    body: GageRrPreflightRequest,
) -> GageRrPreflightResponse:
    return get_gage_rr_preflight(
        settings=request.app.state.settings,
        body=body,
    )
