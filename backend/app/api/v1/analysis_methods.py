from fastapi import APIRouter, Request

from app.analyses.registry import analysis_method_catalog
from app.api.v1.schemas.analyses import AnalysisMethodListResponse
from app.core.product_profile import presentation_module_ids

router = APIRouter(prefix="/analysis-methods", tags=["analysis-methods"])


@router.get("", response_model=AnalysisMethodListResponse)
def list_analysis_methods(request: Request) -> AnalysisMethodListResponse:
    module_ids = presentation_module_ids(request.app.state.settings)
    return analysis_method_catalog(module_ids=set(module_ids) if module_ids is not None else None)
