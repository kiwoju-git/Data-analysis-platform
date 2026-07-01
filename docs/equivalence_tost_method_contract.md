# Equivalence TOST Method Contract

Last updated: 2026-06-30

## Scope

`hypothesis.equivalence_tost` is a narrow Gate B2 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed numeric response column
- one-sample mean equivalence design only
- explicit reference mean
- explicit lower and upper equivalence bounds in raw response units, defined for `mean - reference_mean`
- complete-case missing handling
- explicit `alpha` with `0 < alpha < 0.5`
- Cohen dz and Hedges-corrected standardized effect

Current out of scope:

- paired mean-difference TOST
- independent two-sample TOST
- ratio-scale equivalence, standardized-margin input, or percent-margin input
- automatic equivalence-bound suggestions
- nonparametric equivalence tests
- automatic method switching from normality or equal-variance diagnostics

## Statistical Policy

- The estimate is `sample_mean - reference_mean`.
- The lower one-sided test uses `t = (estimate - lower_bound) / standard_error` and right-tail p-value.
- The upper one-sided test uses `t = (estimate - upper_bound) / standard_error` and left-tail p-value.
- The TOST p-value is the larger of the two one-sided p-values.
- Equivalence is reported only when both one-sided tests reject at `alpha`.
- The confidence interval level is `1 - 2 * alpha`; it is reported next to the user-supplied equivalence bounds.
- The result always warns that equivalence bounds are user-defined and that non-significance from a difference test is not equivalence.
- Missing and non-numeric response values are excluded with explicit counts.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "design": "one_sample_mean",
  "response_column_id": "response-column-id",
  "reference_mean": 10,
  "lower_bound": -0.8,
  "upper_bound": 0.8,
  "alpha": 0.05,
  "missing_policy": "complete_case"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, and supports checksum-validated retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

## Result Shape

The result payload has `summary_type="equivalence_tost"` and includes:

- response column metadata
- `design="one_sample_mean"`
- `reference_mean`
- `equivalence_bounds`
- N totals and exclusion counts
- sample summary
- mean-difference estimate and standard error
- lower and upper one-sided test records
- TOST decision and p-value
- `1 - 2 * alpha` confidence interval
- Cohen dz and Hedges-corrected effect
- package versions and stable warning codes

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `equivalence_tost_response_required`
- `equivalence_tost_response_column_not_found`
- `equivalence_tost_response_column_is_id`
- `equivalence_tost_response_column_not_numeric`
- `equivalence_tost_design_unsupported`
- `invalid_equivalence_tost_reference_mean`
- `invalid_equivalence_tost_bounds`
- `equivalence_tost_bounds_order_invalid`
- `invalid_equivalence_tost_alpha`
- `equivalence_tost_missing_policy_unsupported`
- `equivalence_tost_n_too_small`
- `equivalence_tost_standard_error_zero`

## Warnings

Current stable warning codes:

- `equivalence_tost_design_assumption`
- `equivalence_bounds_user_defined`
- `non_significance_is_not_equivalence`
- `missing_values_excluded`
- `non_numeric_values_excluded`

## Testing

Required coverage for this method:

- hand-checkable one-sample TOST fixture
- SciPy reference fixture for equivalent and not-equivalent cases
- missing and non-numeric exclusion reporting
- invalid-input failures without fallback statistics
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance

Reference fixtures:

- `backend/tests/reference/fixtures/equivalence_tost_input.json`
- `backend/tests/reference/fixtures/equivalence_tost_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_equivalence_tost.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_equivalence_tost_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
