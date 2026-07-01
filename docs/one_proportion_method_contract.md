# 1-Proportion Method Contract

Last updated: 2026-06-30

## Scope

`categorical.one_proportion` is a narrow Gate B2 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed binary response column
- explicit `event_level`
- complete-case missing handling
- explicit `null_proportion` (`0 < p0 < 1`)
- `alternative` in `two_sided`, `greater`, or `less`
- `confidence_level` and `alpha`
- confidence interval method `wilson` or `clopper_pearson`

Current out of scope:

- summary-count input such as event count plus total count
- automatic event/non-event level inference
- two-proportion tests
- chi-square/Fisher tests
- automatic method switching based on sample size

## Statistical Policy

- The p-value is calculated with SciPy `stats.binomtest`.
- The default confidence interval is Wilson score.
- Clopper-Pearson exact confidence intervals are available through explicit `ci_method="clopper_pearson"`.
- The result reports event count, non-event count, total N, missing exclusions, sample proportion, difference from `p0`, odds where finite, p-value, confidence interval, reject decision, and Cohen's h.
- The result always warns that the binary event/non-event design and independence are user-confirmed design assumptions.
- More than two observed non-missing levels are rejected with `one_proportion_requires_binary_column`.
- Empty usable data is rejected with `one_proportion_n_too_small`.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "response_column_id": "column-id",
  "event_level": "yes",
  "null_proportion": 0.5,
  "alpha": 0.05,
  "confidence_level": 0.95,
  "alternative": "two_sided",
  "ci_method": "wilson",
  "missing_policy": "complete_case"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, and supports checksum-validated retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

## Testing

Required coverage for this method:

- hand-checkable exact binomial p-value and Wilson interval fixture
- generated reference fixture for an independent SciPy result
- missing and single-level warning behavior
- invalid-input failures without fallback statistics
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance
