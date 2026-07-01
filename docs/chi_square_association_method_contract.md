# Chi-square Association Method Contract

Last updated: 2026-06-30

## Scope

`categorical.chi_square_association` is a narrow Gate B2 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed row categorical column
- one dataset-backed column categorical column
- complete-case missing handling
- Pearson chi-square test of independence
- explicit `alpha`
- Cramer's V effect size

Current out of scope:

- summary-count contingency table input
- automatic Fisher exact execution
- Fisher exact p-value output
- chi-square tests for user-entered aggregate counts
- mosaic or residual chart rendering
- automatic method switching based on expected counts

## Statistical Policy

- The p-value is calculated with SciPy `stats.chi2_contingency(..., correction=False)`.
- Missing row/column values are excluded with an explicit count.
- The result reports observed counts, expected counts, row/column/total percentages, standardized residuals, chi-square statistic, df, p-value, reject decision, Cramer's V, warning codes, and provenance.
- The result always warns that independence is a user-confirmed design assumption and that Yates continuity correction is not applied.
- Expected-count rule-of-thumb diagnostics are reported but do not automatically switch methods.
- Sparse 2x2 tables add a Fisher exact recommendation in `recommended_alternative_tests`; no Fisher p-value is fabricated.
- More than 100 observed levels on either axis are rejected to avoid accidental high-cardinality ID-style tables.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "row_column_id": "row-column-id",
  "column_column_id": "column-column-id",
  "alpha": 0.05,
  "missing_policy": "complete_case"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, and supports checksum-validated retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

## Testing

Required coverage for this method:

- hand-checkable 2x2 contingency table
- generated reference fixture cross-checked with SciPy
- missing-value exclusion and sparse 2x2 Fisher recommendation behavior
- invalid-input failures without fallback statistics
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance
