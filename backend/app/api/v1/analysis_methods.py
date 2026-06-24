from fastapi import APIRouter

from app.analyses.registry import analysis_method_catalog
from app.api.v1.schemas.analyses import AnalysisMethodListResponse

router = APIRouter(prefix="/analysis-methods", tags=["analysis-methods"])


@router.get("", response_model=AnalysisMethodListResponse)
def list_analysis_methods() -> AnalysisMethodListResponse:
    return analysis_method_catalog()
