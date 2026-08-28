from fastapi import APIRouter, Request

from app.analyses.registry import analysis_method_catalog
from app.api.v1.schemas.analyses import AnalysisMethodListResponse, MethodAvailability
from app.core.product_profile import (
    is_four_domain_presentation_profile,
    presentation_method_ids,
    presentation_module_ids,
)

router = APIRouter(prefix="/analysis-methods", tags=["analysis-methods"])


@router.get("", response_model=AnalysisMethodListResponse)
def list_analysis_methods(request: Request) -> AnalysisMethodListResponse:
    settings = request.app.state.settings
    if is_four_domain_presentation_profile(settings):
        catalog = analysis_method_catalog()
        allowed_method_ids = presentation_method_ids(settings) or frozenset()
        return catalog.model_copy(
            update={
                "methods": [
                    method
                    if method.method_id in allowed_method_ids
                    else method.model_copy(
                        update={
                            "availability": MethodAvailability.PLANNED,
                            "disabled_reason": (
                                "This analysis is planned for a later presentation profile."
                            ),
                        }
                    )
                    for method in catalog.methods
                ]
            }
        )
    module_ids = presentation_module_ids(settings)
    return analysis_method_catalog(module_ids=set(module_ids) if module_ids is not None else None)
