# Pearson Correlation Method Contract

Last updated: 2026-07-01

## Scope

`regression.pearson` is the first narrow Gate C1 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed numeric X column
- one dataset-backed numeric Y column
- complete-case missing handling
- two-sided Pearson product-moment correlation test against population correlation 0
- explicit `alpha` and confidence level
- Fisher z confidence interval when the sample correlation is not perfect
- capped scatterplot point payload for frontend visualization

Current out of scope:

- X-set by Y-set correlation matrix
- Spearman or Kendall correlation
- pairwise deletion with changing N by pair
- generated scatterplot artifact/export
- outlier influence diagnostics
- regression model fitting, model manifest storage, or prediction
- automatic causal interpretation

## Statistical Policy

- The p-value is calculated with SciPy `stats.pearsonr`.
- The confidence interval uses the Fisher z transform and the requested confidence level.
- Missing or non-numeric X/Y values are excluded with explicit counts under one complete-case policy.
- X or Y columns with no variation are rejected without returning a fake statistic.
- The result reports N, exclusions, X/Y sample summaries, covariance, Pearson r, r-squared, p-value, reject decision, confidence interval, warning codes, package versions, capped scatterplot point payload, and provenance.
- The scatterplot payload is derived from complete-case numeric pairs, is capped at 500 points by default, is deterministic, and does not include row indices, raw string values, or source file paths.
- The result always warns that correlation is not causation, Pearson summarizes linear association, and the statistic is sensitive to outliers.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "x_column_id": "x-column-id",
  "y_column_id": "y-column-id",
  "alpha": 0.05,
  "confidence_level": 0.95,
  "missing_policy": "complete_case"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, and supports checksum-validated retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

Result payload addition:

```json
{
  "scatterplot": {
    "x_column_id": "x-column-id",
    "y_column_id": "y-column-id",
    "point_count": 120,
    "points_truncated": false,
    "point_limit": 500,
    "points": [{ "x": 1.0, "y": 2.0 }]
  }
}
```

## Testing

Required coverage for this method:

- hand-checkable small sample for covariance, r, p-value, and CI
- generated reference fixture cross-checked with SciPy
- missing and non-numeric complete-case exclusion counts
- capped scatterplot payload without row identity
- invalid-input failures for too-small N and constant X/Y columns
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance
