"""Explicit generic-analysis report contracts, checked against the method registry."""

from functools import lru_cache

from app.api.v1.schemas.report_capabilities import (
    MethodReportContract,
    ReportSectionContract,
    ReportVariantContract,
)
from app.services.report_contract import (
    ReportDefinition,
    ReportSectionDefinition,
    ReportVariantDefinition,
)

# method_id -> (summary_type, supported stored schema versions)
INLINE_REPORT_CONTRACTS: dict[str, tuple[str, frozenset[int]]] = {
    "quality.two_variances": ("two_variances_test", frozenset({1})),
    "eda.descriptive": ("descriptive_statistics", frozenset({1, 2})),
    "eda.graphical_summary": ("graphical_summary", frozenset({1, 2})),
    "eda.normality": ("normality_test", frozenset({1, 2})),
    "eda.principal_components": ("principal_components_analysis", frozenset({1})),
    "eda.equal_variances": ("equal_variances_test", frozenset({1, 2})),
    "hypothesis.one_sample_t": ("one_sample_t_test", frozenset({1})),
    "hypothesis.paired_t": ("paired_t_test", frozenset({1})),
    "hypothesis.two_sample_t": ("two_sample_t_test", frozenset({1})),
    "hypothesis.one_way_anova": ("one_way_anova", frozenset({1, 2})),
    "hypothesis.equivalence_tost": ("equivalence_tost", frozenset({1, 2})),
    "hypothesis.two_sample_equivalence_tost": ("equivalence_tost", frozenset({1, 2})),
    "hypothesis.paired_equivalence_tost": ("equivalence_tost", frozenset({1, 2})),
    "hypothesis.one_sample_wilcoxon": ("one_sample_wilcoxon_signed_rank_test", frozenset({1})),
    "hypothesis.mann_whitney": ("mann_whitney_u_test", frozenset({1, 2})),
    "hypothesis.kruskal_wallis": ("kruskal_wallis_test", frozenset({1})),
    "categorical.one_proportion": ("one_proportion_test", frozenset({1})),
    "categorical.two_proportion": ("two_proportion_test", frozenset({1})),
    "categorical.chi_square_association": ("chi_square_association", frozenset({1})),
    "regression.pearson": ("pearson_correlation", frozenset({1})),
    "regression.xy_correlation": ("xy_correlation_matrix", frozenset({1})),
    "regression.linear_model": ("linear_model", frozenset({1, 2, 3, 4, 5, 6})),
    "regression.partial_least_squares": ("partial_least_squares_regression", frozenset({1})),
    "regression.gaussian_process": ("gaussian_process_regression", frozenset({1, 2, 3})),
    "quality.attribute_control_chart": ("attribute_control_chart", frozenset({1, 2, 3})),
    "quality.subgroup_chart": ("subgroup_chart", frozenset({1})),
    "quality.individuals_chart": ("individuals_chart", frozenset({1})),
    "quality.run_chart": ("run_chart", frozenset({1, 2})),
    "quality.capability": ("capability_analysis", frozenset({1})),
    "quality.gage_rr": ("gage_rr", frozenset({1})),
    "quality.gage_run_chart": ("gage_run_chart", frozenset({1})),
}


@lru_cache(maxsize=1)
def report_definitions() -> dict[str, ReportDefinition]:
    """Declarations share renderer-owned section contracts, never a UI support list."""
    from app.services.basic_eda_report import BASIC_EDA_REPORT_VARIANTS_BY_METHOD
    from app.services.categorical_report import CATEGORICAL_REPORT_VARIANTS_BY_METHOD
    from app.services.correlation_report import CORRELATION_REPORT_VARIANTS
    from app.services.gaussian_process_report import GP_SURFACE_DEFINITIONS
    from app.services.hypothesis_report import HYPOTHESIS_REPORT_VARIANTS_BY_METHOD
    from app.services.linear_model_report import LINEAR_REPORT_VARIANTS
    from app.services.normality_report import NORMALITY_REPORT_VARIANTS
    from app.services.pls_regression_report import PLS_REPORT_VARIANTS
    from app.services.principal_components_report import PCA_REPORT_VARIANTS
    from app.services.quality_report import QUALITY_REPORT_VARIANTS

    variants = {
        "normality_test": NORMALITY_REPORT_VARIANTS,
        "principal_components_analysis": PCA_REPORT_VARIANTS,
        "linear_model": LINEAR_REPORT_VARIANTS,
        "partial_least_squares_regression": PLS_REPORT_VARIANTS,
        "gaussian_process_regression": tuple(
            ReportVariantDefinition(
                mode,
                (
                    ReportSectionDefinition("gp_results", True),
                    *(
                        ReportSectionDefinition(key)
                        for key in (
                            "gp_reproducibility",
                            "gp_optimization",
                            "gp_training_plot",
                            "gp_cv_plot",
                            "gp_residual_plot",
                            "gp_uncertainty_plot",
                            "gp_profiles",
                            "gp_surface_values",
                        )
                    ),
                    *GP_SURFACE_DEFINITIONS,
                    ReportSectionDefinition("gp_comparison", mode == "compare"),
                ),
            )
            for mode in ("single", "compare")
        ),
        **CORRELATION_REPORT_VARIANTS,
        **QUALITY_REPORT_VARIANTS,
    }
    method_variants = {
        **BASIC_EDA_REPORT_VARIANTS_BY_METHOD,
        **HYPOTHESIS_REPORT_VARIANTS_BY_METHOD,
        **CATEGORICAL_REPORT_VARIANTS_BY_METHOD,
    }
    return {
        method_id: ReportDefinition(
            method_id=method_id,
            summary_type=summary_type,
            accepted_schemas=tuple(sorted(schemas)),
            renderer_id=summary_type,
            renderer_version="2.0.0",
            variants=method_variants.get(
                method_id,
                variants.get(
                    summary_type,
                    (
                        ReportVariantDefinition(
                            "default", (ReportSectionDefinition("results", True),)
                        ),
                    ),
                ),
            ),
        )
        for method_id, (summary_type, schemas) in INLINE_REPORT_CONTRACTS.items()
    }


def method_report_contract(method_id: str) -> MethodReportContract | None:
    definition = report_definitions().get(method_id)
    if definition is None:
        return None
    return MethodReportContract(
        method_id=definition.method_id,
        summary_type=definition.summary_type,
        accepted_schema_versions=list(definition.accepted_schemas),
        renderer_id=definition.renderer_id,
        renderer_version=definition.renderer_version,
        variants=[
            ReportVariantContract(
                variant_id=variant.variant_id,
                sections=[
                    ReportSectionContract(section_id=section.section_id, core=section.core)
                    for section in variant.sections
                ],
            )
            for variant in definition.variants
        ],
    )
