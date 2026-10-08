from fastapi import APIRouter, Request

from app.analyses.registry import analysis_method_catalog
from app.api.v1.schemas.analyses import (
    AnalysisMethodListResponse,
    TwoVariancesPreflightRequest,
    TwoVariancesPreflightResponse,
)
from app.services.two_variances_preflight import get_two_variances_preflight

router = APIRouter(prefix="/analysis-methods", tags=["analysis-methods"])


@router.get("", response_model=AnalysisMethodListResponse)
def list_analysis_methods() -> AnalysisMethodListResponse:
    return analysis_method_catalog()


@router.post("/quality.two_variances/preflight", response_model=TwoVariancesPreflightResponse)
def two_variances_preflight_route(
    request: Request, body: TwoVariancesPreflightRequest
) -> TwoVariancesPreflightResponse:
    return get_two_variances_preflight(request.app.state.settings, body)
