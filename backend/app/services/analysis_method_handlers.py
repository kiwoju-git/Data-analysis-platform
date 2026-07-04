from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.analyses import AnalysisResultEnvelope, AnalysisRunRequest
from app.core.config import Settings

AnalysisRunner = Callable[[Settings, AnalysisRunRequest], AnalysisResultEnvelope]


@dataclass(frozen=True)
class MethodExecutionHandler:
    method_id: str
    method_version: str
    result_summary_type: str
    run: AnalysisRunner


@dataclass(frozen=True)
class MethodExecutionHandlerSpec:
    method_id: str
    method_version: str
    result_summary_type: str


METHOD_EXECUTION_HANDLER_SPECS: tuple[MethodExecutionHandlerSpec, ...] = (
    MethodExecutionHandlerSpec(
        method_id="eda.descriptive",
        method_version=METHOD_VERSIONS["eda.descriptive"],
        result_summary_type="descriptive_statistics",
    ),
    MethodExecutionHandlerSpec(
        method_id="eda.graphical_summary",
        method_version=METHOD_VERSIONS["eda.graphical_summary"],
        result_summary_type="graphical_summary",
    ),
    MethodExecutionHandlerSpec(
        method_id="eda.normality",
        method_version=METHOD_VERSIONS["eda.normality"],
        result_summary_type="normality",
    ),
    MethodExecutionHandlerSpec(
        method_id="eda.equal_variances",
        method_version=METHOD_VERSIONS["eda.equal_variances"],
        result_summary_type="equal_variances",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.one_sample_t",
        method_version=METHOD_VERSIONS["hypothesis.one_sample_t"],
        result_summary_type="one_sample_t_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.paired_t",
        method_version=METHOD_VERSIONS["hypothesis.paired_t"],
        result_summary_type="paired_t_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.one_sample_wilcoxon",
        method_version=METHOD_VERSIONS["hypothesis.one_sample_wilcoxon"],
        result_summary_type="one_sample_wilcoxon_signed_rank_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.two_sample_t",
        method_version=METHOD_VERSIONS["hypothesis.two_sample_t"],
        result_summary_type="two_sample_t_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.mann_whitney",
        method_version=METHOD_VERSIONS["hypothesis.mann_whitney"],
        result_summary_type="mann_whitney_u_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.kruskal_wallis",
        method_version=METHOD_VERSIONS["hypothesis.kruskal_wallis"],
        result_summary_type="kruskal_wallis_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.one_way_anova",
        method_version=METHOD_VERSIONS["hypothesis.one_way_anova"],
        result_summary_type="one_way_anova",
    ),
    MethodExecutionHandlerSpec(
        method_id="hypothesis.equivalence_tost",
        method_version=METHOD_VERSIONS["hypothesis.equivalence_tost"],
        result_summary_type="equivalence_tost",
    ),
    MethodExecutionHandlerSpec(
        method_id="categorical.one_proportion",
        method_version=METHOD_VERSIONS["categorical.one_proportion"],
        result_summary_type="one_proportion_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="categorical.two_proportion",
        method_version=METHOD_VERSIONS["categorical.two_proportion"],
        result_summary_type="two_proportion_test",
    ),
    MethodExecutionHandlerSpec(
        method_id="categorical.chi_square_association",
        method_version=METHOD_VERSIONS["categorical.chi_square_association"],
        result_summary_type="chi_square_association",
    ),
    MethodExecutionHandlerSpec(
        method_id="regression.pearson",
        method_version=METHOD_VERSIONS["regression.pearson"],
        result_summary_type="pearson_correlation",
    ),
    MethodExecutionHandlerSpec(
        method_id="regression.xy_correlation",
        method_version=METHOD_VERSIONS["regression.xy_correlation"],
        result_summary_type="xy_correlation_matrix",
    ),
    MethodExecutionHandlerSpec(
        method_id="regression.linear_model",
        method_version=METHOD_VERSIONS["regression.linear_model"],
        result_summary_type="linear_model",
    ),
    MethodExecutionHandlerSpec(
        method_id="quality.individuals_chart",
        method_version=METHOD_VERSIONS["quality.individuals_chart"],
        result_summary_type="individuals_chart",
    ),
    MethodExecutionHandlerSpec(
        method_id="quality.subgroup_chart",
        method_version=METHOD_VERSIONS["quality.subgroup_chart"],
        result_summary_type="subgroup_chart",
    ),
    MethodExecutionHandlerSpec(
        method_id="quality.run_chart",
        method_version=METHOD_VERSIONS["quality.run_chart"],
        result_summary_type="run_chart",
    ),
    MethodExecutionHandlerSpec(
        method_id="quality.capability",
        method_version=METHOD_VERSIONS["quality.capability"],
        result_summary_type="capability_analysis",
    ),
    MethodExecutionHandlerSpec(
        method_id="quality.gage_rr",
        method_version=METHOD_VERSIONS["quality.gage_rr"],
        result_summary_type="gage_rr",
    ),
    MethodExecutionHandlerSpec(
        method_id="quality.gage_run_chart",
        method_version=METHOD_VERSIONS["quality.gage_run_chart"],
        result_summary_type="gage_run_chart",
    ),
)


def build_method_execution_handlers(
    runners: Mapping[str, AnalysisRunner],
) -> dict[str, MethodExecutionHandler]:
    missing_method_ids = sorted(
        spec.method_id for spec in METHOD_EXECUTION_HANDLER_SPECS if spec.method_id not in runners
    )
    if missing_method_ids:
        raise RuntimeError("Missing analysis execution runners: " + ", ".join(missing_method_ids))

    return {
        spec.method_id: MethodExecutionHandler(
            method_id=spec.method_id,
            method_version=spec.method_version,
            result_summary_type=spec.result_summary_type,
            run=runners[spec.method_id],
        )
        for spec in METHOD_EXECUTION_HANDLER_SPECS
    }
