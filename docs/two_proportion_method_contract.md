# 2-Proportion Method Contract

Last updated: 2026-06-30

## Scope

`categorical.two_proportion` is a narrow Gate B2 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed binary response column
- one dataset-backed group column with exactly two usable groups
- explicit `event_level`
- complete-case missing handling
- `alternative` in `two_sided`, `greater`, or `less`
- `confidence_level` and `alpha`

Current out of scope:

- summary-count input such as event count plus total count for each group
- automatic event/non-event level inference
- more than two groups
- chi-square association tests
- automatic method switching based on expected counts

## Statistical Policy

- The p-value is calculated with SciPy `stats.fisher_exact` for the 2x2 table.
- The proportion difference is reported as group 1 event proportion minus group 2 event proportion.
- The confidence interval for the proportion difference uses the Newcombe-Wilson method.
- Risk ratio and odds ratio estimates are reported when mathematically finite.
- Log-Wald confidence intervals for risk ratio and odds ratio are reported only when all required cell counts support finite estimates.
- The result reports group event counts, non-event counts, total N, missing exclusions, group proportions, expected counts, p-value, confidence interval, reject decision, risk ratio, odds ratio, warning codes, and provenance.
- The result always warns that the binary event/non-event design and independence are user-confirmed design assumptions.
- More than two observed non-missing response levels are rejected with `two_proportion_requires_binary_response`.
- More or fewer than two usable groups are rejected with `two_proportion_requires_exactly_two_groups`.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "response_column_id": "response-column-id",
  "group_column_id": "group-column-id",
  "event_level": "yes",
  "alpha": 0.05,
  "confidence_level": 0.95,
  "alternative": "two_sided",
  "missing_policy": "complete_case"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, and supports checksum-validated retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

## Testing

Required coverage for this method:

- hand-checkable 2x2 event/non-event counts and Fisher exact p-value
- generated reference fixture for an independent SciPy result
- missing, sparse-cell, and zero-cell warning behavior
- invalid-input failures without fallback statistics
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance
