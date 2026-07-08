from fastapi import status

from app.analyses.registry import get_analysis_method
from app.api.v1.schemas.analyses import (
    AnalysisResultEnvelope,
    AnalysisRunRequest,
    MethodAvailability,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_method_handlers import (
    MethodExecutionHandler,
    build_method_execution_handlers,
)
from app.services.analysis_run_comparisons import compare_analysis_runs
from app.services.analysis_run_exports import (
    _sanitize_csv_cell,
    create_analysis_result_csv_export,
    create_analysis_result_html_report_export,
    create_analysis_result_json_export,
    get_analysis_result_export_download,
    list_analysis_result_exports,
)
from app.services.analysis_run_history import (
    get_analysis_run_status,
    list_analysis_runs,
    request_analysis_run_cancellation,
)
from app.services.analysis_run_results import get_analysis_run_result
from app.services.analysis_runners_categorical import (
    run_chi_square_association_analysis,
    run_one_proportion_analysis,
    run_two_proportion_analysis,
)
from app.services.analysis_runners_eda import (
    run_descriptive_analysis,
    run_equal_variances_analysis,
    run_graphical_summary_analysis,
    run_normality_analysis,
)
from app.services.analysis_runners_hypothesis import (
    run_equivalence_tost_analysis,
    run_kruskal_wallis_analysis,
    run_mann_whitney_analysis,
    run_one_sample_t_analysis,
    run_one_sample_wilcoxon_analysis,
    run_one_way_anova_analysis,
    run_paired_t_analysis,
    run_two_sample_t_analysis,
)
from app.services.analysis_runners_quality import (
    run_capability_analysis,
    run_gage_rr_analysis,
    run_gage_run_chart_analysis,
    run_individuals_chart_analysis,
    run_run_chart_analysis,
    run_subgroup_chart_analysis,
)
from app.services.analysis_runners_regression import (
    run_linear_model_analysis,
    run_pearson_analysis,
    run_xy_correlation_analysis,
)

__all__ = [
    "_METHOD_EXECUTION_HANDLERS",
    "_sanitize_csv_cell",
    "compare_analysis_runs",
    "create_analysis_result_csv_export",
    "create_analysis_result_html_report_export",
    "create_analysis_result_json_export",
    "create_analysis_run",
    "get_analysis_result_export_download",
    "get_analysis_run_result",
    "get_analysis_run_status",
    "list_analysis_result_exports",
    "list_analysis_runs",
    "request_analysis_run_cancellation",
]


def create_analysis_run(
    settings: Settings,
    request: AnalysisRunRequest,
) -> AnalysisResultEnvelope:
    method = get_analysis_method(request.method_id)
    if method is None:
        raise ApiError(
            code="analysis_method_not_found",
            message="요청한 분석 메서드를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if method.method_version != request.method_version:
        raise ApiError(
            code="analysis_method_version_mismatch",
            message="요청한 분석 메서드 버전이 현재 registry와 일치하지 않습니다.",
            status_code=status.HTTP_409_CONFLICT,
        )

    if method.availability != MethodAvailability.AVAILABLE:
        raise ApiError(
            code="analysis_method_not_available",
            message="이 분석 메서드는 아직 실행할 수 없습니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail=method.availability.value,
        )

    handler = _METHOD_EXECUTION_HANDLERS.get(request.method_id)
    if handler is not None:
        return handler.run(settings, request)

    if request.method_id == "doe.factorial_design":
        raise ApiError(
            code="analysis_method_uses_dedicated_api",
            message="이 메서드는 DOE 설계 자산 API를 통해 실행해야 합니다.",
            status_code=status.HTTP_409_CONFLICT,
            developer_detail="/api/v1/doe-designs/factorial",
        )

    raise ApiError(
        code="analysis_method_not_available",
        message="이 분석 메서드는 아직 실행할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
        developer_detail=method.availability.value,
    )


_METHOD_EXECUTION_HANDLERS: dict[str, MethodExecutionHandler] = build_method_execution_handlers(
    {
        "eda.descriptive": run_descriptive_analysis,
        "eda.graphical_summary": run_graphical_summary_analysis,
        "eda.normality": run_normality_analysis,
        "eda.equal_variances": run_equal_variances_analysis,
        "hypothesis.one_sample_t": run_one_sample_t_analysis,
        "hypothesis.paired_t": run_paired_t_analysis,
        "hypothesis.one_sample_wilcoxon": run_one_sample_wilcoxon_analysis,
        "hypothesis.two_sample_t": run_two_sample_t_analysis,
        "hypothesis.mann_whitney": run_mann_whitney_analysis,
        "hypothesis.kruskal_wallis": run_kruskal_wallis_analysis,
        "hypothesis.one_way_anova": run_one_way_anova_analysis,
        "hypothesis.equivalence_tost": run_equivalence_tost_analysis,
        "categorical.one_proportion": run_one_proportion_analysis,
        "categorical.two_proportion": run_two_proportion_analysis,
        "categorical.chi_square_association": run_chi_square_association_analysis,
        "regression.pearson": run_pearson_analysis,
        "regression.xy_correlation": run_xy_correlation_analysis,
        "regression.linear_model": run_linear_model_analysis,
        "quality.individuals_chart": run_individuals_chart_analysis,
        "quality.subgroup_chart": run_subgroup_chart_analysis,
        "quality.run_chart": run_run_chart_analysis,
        "quality.capability": run_capability_analysis,
        "quality.gage_rr": run_gage_rr_analysis,
        "quality.gage_run_chart": run_gage_run_chart_analysis,
    }
)
