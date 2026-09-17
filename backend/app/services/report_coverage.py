"""Explicit generic-analysis report contracts, checked against the method registry."""

# method_id -> (summary_type, supported stored schema versions)
INLINE_REPORT_CONTRACTS: dict[str, tuple[str, frozenset[int]]] = {
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

# These existing renderers expose useful tables, but not every interactive plot.
SUMMARY_REPORT_METHODS = frozenset(
    {
        "eda.normality",
        "regression.pearson",
        "regression.xy_correlation",
        "regression.linear_model",
        *(
            key
            for key in INLINE_REPORT_CONTRACTS
            if key.startswith(("hypothesis.", "categorical.", "quality."))
        ),
    }
)
