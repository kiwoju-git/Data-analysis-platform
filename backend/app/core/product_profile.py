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
PRESENTATION_FOUR_DOMAIN_MODULE_IDS = frozenset(
    {
        AnalysisModuleId.EXPLORATION,
        AnalysisModuleId.HYPOTHESIS,
        AnalysisModuleId.CATEGORICAL,
        AnalysisModuleId.REGRESSION,
    }
)
PRESENTATION_FOUR_DOMAIN_METHOD_IDS = frozenset(
    {
        "eda.descriptive",
        "eda.graphical_summary",
        "eda.normality",
        "hypothesis.one_sample_t",
        "hypothesis.paired_t",
        "hypothesis.two_sample_t",
        "hypothesis.one_way_anova",
        "hypothesis.equivalence_tost",
        "hypothesis.two_sample_equivalence_tost",
        "hypothesis.paired_equivalence_tost",
        "hypothesis.one_sample_wilcoxon",
        "hypothesis.mann_whitney",
        "hypothesis.kruskal_wallis",
        "categorical.one_proportion",
        "categorical.two_proportion",
        "categorical.chi_square_association",
        "regression.pearson",
        "regression.xy_correlation",
        "regression.linear_model",
        "regression.partial_least_squares",
        "regression.predict",
        "regression.predict_pasted",
        "regression.linear_model_optimizer",
    }
)
PRESENTATION_MODULE_IDS_BY_PROFILE = {
    "presentation": PRESENTATION_CORE_MODULE_IDS,
    "presentation-regression": PRESENTATION_REGRESSION_MODULE_IDS,
    "presentation-four-domains": PRESENTATION_FOUR_DOMAIN_MODULE_IDS,
}


def presentation_module_ids(settings: Settings) -> frozenset[AnalysisModuleId] | None:
    return PRESENTATION_MODULE_IDS_BY_PROFILE.get(settings.product_profile)


def is_presentation_profile(settings: Settings) -> bool:
    return presentation_module_ids(settings) is not None


def presentation_profile_includes_regression(settings: Settings) -> bool:
    module_ids = presentation_module_ids(settings)
    return module_ids is not None and AnalysisModuleId.REGRESSION in module_ids


def is_four_domain_presentation_profile(settings: Settings) -> bool:
    return settings.product_profile == "presentation-four-domains"


def presentation_method_ids(settings: Settings) -> frozenset[str] | None:
    if is_four_domain_presentation_profile(settings):
        return PRESENTATION_FOUR_DOMAIN_METHOD_IDS
    module_ids = presentation_module_ids(settings)
    if module_ids is None:
        return None
    candidate_method_ids = (
        "eda.descriptive",
        "eda.graphical_summary",
        "eda.normality",
        "eda.equal_variances",
        "hypothesis.one_sample_t",
        "hypothesis.paired_t",
        "hypothesis.two_sample_t",
        "hypothesis.one_way_anova",
        "hypothesis.equivalence_tost",
        "hypothesis.two_sample_equivalence_tost",
        "hypothesis.paired_equivalence_tost",
        "hypothesis.one_sample_wilcoxon",
        "hypothesis.mann_whitney",
        "hypothesis.kruskal_wallis",
        "regression.pearson",
        "regression.xy_correlation",
        "regression.linear_model",
        "regression.partial_least_squares",
        "regression.predict",
        "regression.predict_pasted",
        "regression.linear_model_optimizer",
    )
    return frozenset(
        method_id
        for method_id in candidate_method_ids
        if (method := get_analysis_method(method_id)) is not None and method.module_id in module_ids
    )


def require_available_presentation_method(settings: Settings, method_id: str) -> None:
    method_ids = presentation_method_ids(settings)
    if method_ids is None or method_id in method_ids:
        return
    raise ApiError(
        code="presentation_profile_method_unavailable",
        message="This analysis is unavailable in the selected presentation profile.",
        status_code=status.HTTP_403_FORBIDDEN,
    )
