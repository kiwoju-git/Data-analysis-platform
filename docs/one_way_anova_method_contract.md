# One-Way ANOVA Method Contract

Last updated: 2026-06-30

## Scope

`hypothesis.one_way_anova` is a narrow Gate B2 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed numeric response column
- one dataset-backed grouping column with at least two usable groups
- at least two usable numeric response values per group
- complete-case missing handling
- `anova_type="standard"`
- `posthoc_method="tukey_kramer"` or `posthoc_method="none"`
- `posthoc_policy="after_significant"`
- `confidence_level` and `alpha`

Current out of scope:

- Welch ANOVA
- Games-Howell post-hoc
- two-way ANOVA, ANCOVA, repeated-measures ANOVA, mixed models
- summary-statistic ANOVA input
- automatic switching from normality/equal-variance diagnostics to another method

## Statistical Policy

- The omnibus test is a standard fixed-effect one-way ANOVA with between-groups and within-groups sums of squares.
- The p-value is calculated from the F distribution with `df_between` and `df_within`.
- Effect sizes include eta squared and omega squared.
- Tukey-Kramer pairwise comparisons are run only when the omnibus ANOVA rejects at `alpha` and `posthoc_method="tukey_kramer"`.
- Tukey-Kramer comparisons report mean difference, Tukey-adjusted p-value, an unadjusted pooled pairwise t p-value for transparency, and Tukey-Kramer simultaneous confidence intervals.
- The result always warns that independence, residual normality, and equal variance are design/assumption checks and that diagnostics do not automatically switch the selected method.
- All-missing/one-group, too-small group, all-identical response, zero residual variance, invalid alpha/confidence, unsupported ANOVA type, and unsupported post-hoc policies fail with stable error codes.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "response_column_id": "response-column-id",
  "group_column_id": "group-column-id",
  "alpha": 0.05,
  "confidence_level": 0.95,
  "anova_type": "standard",
  "posthoc_method": "tukey_kramer",
  "posthoc_policy": "after_significant",
  "missing_policy": "complete_case"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, and supports checksum-validated retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

## Testing

Required coverage for this method:

- hand-checkable balanced-group ANOVA table fixture
- independent SciPy `f_oneway` reference fixture with explicit tolerances
- Tukey-Kramer pairwise comparison values and simultaneous CI checks
- missing/non-numeric exclusion behavior
- invalid-input failures without fallback statistics
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance
