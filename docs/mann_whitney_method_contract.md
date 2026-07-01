# Mann-Whitney U Method Contract

Status: implemented for the current Gate B2 slice.

Method ID: `hypothesis.mann_whitney`

Implementation:

- Backend domain module: `backend/app/statistics/mann_whitney.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/MannWhitneyPanel.tsx`

## Scope

This method computes one independent two-group rank-based comparison from one numeric response column and one group column:

- Mann-Whitney U statistic for the first encountered group against the second encountered group
- exact p-value when requested or automatically selected for small no-tie samples
- asymptotic p-value when requested or automatically selected for ties/larger samples
- rank summaries, rank-biserial effect size, and common-language probability

It does not run paired Wilcoxon, Kruskal-Wallis, post-hoc tests, or any automatic method switch based on normality/equal-variance diagnostics. It must not be described as a generic median-only test.

## Inputs

- `dataset_version_id`: required
- `options.response_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.group_column_id`: required, non-ID, different from response
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
- `options.alternative`: `two_sided`, `greater`, or `less`
- `options.method`: `auto`, `exact`, or `asymptotic`, default `auto`
- `options.missing_policy`: optional, currently only `complete_case`
- `filter_snapshot`: supported through the common Workbench AND-filter engine

The method reads only validated canonical JSONL rows for the confirmed immutable dataset version. It must not reparse the raw upload.

## Missing And Invalid Values

Rows are excluded before calculation when:

- response is missing
- group is missing
- response cannot be parsed as a finite number using the dataset parsing decimal/thousands settings

The result reports `n_total`, `n_used`, `n_excluded_missing_response`, `n_excluded_missing_group`, and `n_excluded_non_numeric_response`.

## Result Shape

The result payload has `summary_type="mann_whitney_u_test"` and includes:

- `response` and `group` column metadata
- `groups[]` summaries with N, mean, median, min, max, rank sum, and mean rank
- `test` with U statistic, p-value, exact/asymptotic method, tie flag, reject decision, rank-biserial effect size, and common-language probability
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

## Blocking Conditions

The API rejects the run instead of returning fake statistics when:

- usable group count is not exactly 2
- either group has fewer than 1 usable observation
- `method="exact"` is requested while ties are present
- U statistic or p-value is non-finite

## Warnings

Current stable warning codes:

- `mann_whitney_independence_assumption`
- `mann_whitney_not_median_test`
- `mann_whitney_ties_detected`
- `mann_whitney_auto_asymptotic_due_to_ties`
- `missing_values_excluded`
- `non_numeric_values_excluded`
- `constant_group`
- `small_group_size`
- `group_size_imbalance`

`mann_whitney_not_median_test` must be present because the rank-based result should not be reduced to a simple median-difference statement.

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `mann_whitney_response_required`
- `mann_whitney_group_required`
- `mann_whitney_same_response_and_group`
- `mann_whitney_response_column_not_found`
- `mann_whitney_group_column_not_found`
- `mann_whitney_response_column_is_id`
- `mann_whitney_response_column_not_numeric`
- `mann_whitney_group_column_is_id`
- `invalid_mann_whitney_alpha`
- `invalid_mann_whitney_alternative`
- `invalid_mann_whitney_method`
- `mann_whitney_missing_policy_unsupported`
- `mann_whitney_requires_exactly_two_groups`
- `mann_whitney_group_n_too_small`
- `mann_whitney_exact_with_ties`
- `mann_whitney_statistic_not_finite`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/mann_whitney_input.json`
- `backend/tests/reference/fixtures/mann_whitney_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_mann_whitney.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_mann_whitney_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
