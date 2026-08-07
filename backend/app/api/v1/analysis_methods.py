from fastapi import APIRouter, Request

from app.analyses.registry import analysis_method_catalog
from app.api.v1.schemas.analyses import AnalysisMethodListResponse
from app.core.product_profile import PRESENTATION_MODULE_IDS, is_presentation_profile

router = APIRouter(prefix="/analysis-methods", tags=["analysis-methods"])


@router.get("", response_model=AnalysisMethodListResponse)
def list_analysis_methods(request: Request) -> AnalysisMethodListResponse:
    module_ids = (
        PRESENTATION_MODULE_IDS if is_presentation_profile(request.app.state.settings) else None
    )
    return analysis_method_catalog(module_ids=module_ids)
