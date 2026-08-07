from fastapi import status

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import AnalysisModuleId
from app.core.config import Settings
from app.core.errors import ApiError

PRESENTATION_MODULE_IDS = {
    AnalysisModuleId.EXPLORATION,
    AnalysisModuleId.HYPOTHESIS,
}


def is_presentation_profile(settings: Settings) -> bool:
    return settings.product_profile == "presentation"


def require_available_presentation_method(settings: Settings, method_id: str) -> None:
    if not is_presentation_profile(settings):
        return
    method = get_analysis_method(method_id)
    if method is not None and method.module_id in PRESENTATION_MODULE_IDS:
        return
    raise ApiError(
        code="presentation_profile_method_unavailable",
        message="발표용 기능 미리보기에서는 이 분석 방법을 실행할 수 없습니다.",
        status_code=status.HTTP_403_FORBIDDEN,
    )
