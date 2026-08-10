from fastapi import status

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import AnalysisModuleId
from app.core.config import Settings
from app.core.errors import ApiError

PRESENTATION_CORE_MODULE_IDS = frozenset(
    {
        AnalysisModuleId.EXPLORATION,
        AnalysisModuleId.HYPOTHESIS,
    }
)
PRESENTATION_REGRESSION_MODULE_IDS = frozenset(
    {
        *PRESENTATION_CORE_MODULE_IDS,
        AnalysisModuleId.REGRESSION,
    }
)
PRESENTATION_MODULE_IDS_BY_PROFILE = {
    "presentation": PRESENTATION_CORE_MODULE_IDS,
    "presentation-regression": PRESENTATION_REGRESSION_MODULE_IDS,
}


def presentation_module_ids(settings: Settings) -> frozenset[AnalysisModuleId] | None:
    return PRESENTATION_MODULE_IDS_BY_PROFILE.get(settings.product_profile)


def is_presentation_profile(settings: Settings) -> bool:
    return presentation_module_ids(settings) is not None


def presentation_profile_includes_regression(settings: Settings) -> bool:
    module_ids = presentation_module_ids(settings)
    return module_ids is not None and AnalysisModuleId.REGRESSION in module_ids


def require_available_presentation_method(settings: Settings, method_id: str) -> None:
    module_ids = presentation_module_ids(settings)
    if module_ids is None:
        return
    method = get_analysis_method(method_id)
    if method is not None and method.module_id in module_ids:
        return
    raise ApiError(
        code="presentation_profile_method_unavailable",
        message="발표용 기능 미리보기에서는 이 분석 방법을 실행할 수 없습니다.",
        status_code=status.HTTP_403_FORBIDDEN,
    )
