# One-Sample Wilcoxon Signed-Rank Method Contract

Status: implemented for the current Gate B2 slice.

Method ID: `hypothesis.one_sample_wilcoxon`

Implementation:

- Backend domain module: `backend/app/statistics/one_sample_wilcoxon.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/OneSampleWilcoxonPanel.tsx`

## Scope

This method computes one signed-rank comparison from one numeric response column and one explicit reference location:

- signed ranks for `x - null_location`
- exact p-value when requested or automatically selected for small no-zero/no-tie samples
- asymptotic p-value when requested or automatically selected for zero differences, ties, or larger samples
- positive/negative rank sums and rank-biserial effect size

It does not run paired Wilcoxon, Mann-Whitney, Kruskal-Wallis, or any automatic method switch based on normality diagnostics. It must not be described as a median-only test without the signed-difference symmetry caveat.

## Inputs

- `dataset_version_id`: required
- `options.response_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
- `options.alternative`: `two_sided`, `greater`, or `less`
- `options.null_location`: explicit finite numeric reference location, default `0`
- `options.method`: `auto`, `exact`, or `asymptotic`, default `auto`
- `options.zero_method`: `wilcox`, `pratt`, or `zsplit`, default `wilcox`
- `options.missing_policy`: optional, currently only `complete_case`
- `filter_snapshot`: supported through the common Workbench AND-filter engine

The method reads only validated canonical JSONL rows for the confirmed immutable dataset version. It must not reparse the raw upload.

## Missing And Invalid Values

Rows are excluded before calculation when:

- response is missing
- response cannot be parsed as a finite number using the dataset parsing decimal/thousands settings

The result reports `n_total`, `n_used`, `n_missing`, `n_non_numeric`, `n_nonzero`, and `zero_difference_count`.

## Result Shape

The result payload has `summary_type="one_sample_wilcoxon_signed_rank_test"` and includes:

- `response` column metadata
- `sample` summary with N, mean, median, min, max, median difference, and sign counts
- `test` with W statistic, p-value, exact/asymptotic method, zero method, tie count, positive/negative rank sums, zero rank sum, total rank sum, and rank-biserial effect size
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

## Blocking Conditions

The API rejects the run instead of returning fake statistics when:

- all usable values equal `null_location`
- `method="exact"` is requested while zero differences or absolute-difference ties are present
- W statistic or p-value is non-finite

## Warnings

Current stable warning codes:

- `one_sample_wilcoxon_symmetry_assumption`
- `one_sample_wilcoxon_not_median_test`
- `one_sample_wilcoxon_not_auto_switched`
- `zero_differences_detected`
- `signed_rank_ties_detected`
- `one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties`
- `small_nonzero_n`
- `missing_values_excluded`
- `non_numeric_values_excluded`

`one_sample_wilcoxon_not_median_test` must be present because the signed-rank result should not be reduced to a simple median-difference statement without the symmetry assumption.

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `one_sample_wilcoxon_response_required`
- `one_sample_wilcoxon_response_column_not_found`
- `one_sample_wilcoxon_response_column_is_id`
- `one_sample_wilcoxon_response_column_not_numeric`
- `invalid_one_sample_wilcoxon_alpha`
- `invalid_one_sample_wilcoxon_alternative`
- `invalid_one_sample_wilcoxon_null_location`
- `invalid_one_sample_wilcoxon_method`
- `invalid_one_sample_wilcoxon_zero_method`
- `one_sample_wilcoxon_missing_policy_unsupported`
- `one_sample_wilcoxon_no_nonzero_differences`
- `one_sample_wilcoxon_exact_with_zeros_or_ties`
- `one_sample_wilcoxon_statistic_not_finite`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/one_sample_wilcoxon_input.json`
- `backend/tests/reference/fixtures/one_sample_wilcoxon_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_one_sample_wilcoxon.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_one_sample_wilcoxon_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
