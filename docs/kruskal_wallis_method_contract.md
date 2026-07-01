# Kruskal-Wallis Method Contract

Status: implemented for the current Gate B2 slice.

Method ID: `hypothesis.kruskal_wallis`

Implementation:

- Backend domain module: `backend/app/statistics/kruskal_wallis.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/KruskalWallisPanel.tsx`

## Scope

This method computes one independent 3-or-more-group rank-based comparison from one numeric response column and one group column:

- tie-corrected Kruskal-Wallis H statistic, df, and p-value
- group N, mean, median, IQR, rank sum, and mean rank
- epsilon-squared effect size using the documented tie-corrected H definition
- Dunn pairwise comparisons with Holm-adjusted p-values only when the overall test rejects at the selected alpha

It does not run one-way ANOVA, Welch ANOVA, Mann-Whitney U, repeated-measures tests, or any automatic method switch based on normality/equal-variance diagnostics. It must not be described as a generic median-only test.

## Inputs

- `dataset_version_id`: required
- `options.response_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.group_column_id`: required, non-ID, different from response
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
- `options.posthoc_method`: optional, `dunn_holm` or `none`, default `dunn_holm`
- `options.posthoc_policy`: optional, currently only `after_significant`
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

The result payload has `summary_type="kruskal_wallis_test"` and includes:

- `response` and `group` column metadata
- `groups[]` summaries with N, mean, median, IQR, min, max, rank sum, and mean rank
- `test` with H statistic, df, p-value, reject decision, and epsilon-squared effect size
- `posthoc` with Dunn/Holm policy, execution reason, and raw/adjusted p-values when performed
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

## Blocking Conditions

The API rejects the run instead of returning fake statistics when:

- usable group count is fewer than 3
- any usable group has fewer than 1 observation
- all usable response values are identical
- H statistic or p-value is non-finite
- Dunn post-hoc rank variance is zero or non-finite

## Warnings

Current stable warning codes:

- `kruskal_wallis_independence_assumption`
- `kruskal_wallis_not_median_test`
- `dunn_holm_after_significant`
- `posthoc_skipped_overall_not_significant`
- `kruskal_wallis_ties_detected`
- `missing_values_excluded`
- `non_numeric_values_excluded`
- `constant_group`
- `small_group_size`
- `group_size_imbalance`

`kruskal_wallis_not_median_test` must be present because the rank-based result should not be reduced to a simple median-difference statement.

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `kruskal_wallis_response_required`
- `kruskal_wallis_group_required`
- `kruskal_wallis_same_response_and_group`
- `kruskal_wallis_response_column_not_found`
- `kruskal_wallis_group_column_not_found`
- `kruskal_wallis_response_column_is_id`
- `kruskal_wallis_response_column_not_numeric`
- `kruskal_wallis_group_column_is_id`
- `invalid_kruskal_wallis_alpha`
- `invalid_kruskal_wallis_posthoc_method`
- `invalid_kruskal_wallis_posthoc_policy`
- `kruskal_wallis_missing_policy_unsupported`
- `kruskal_wallis_requires_at_least_three_groups`
- `kruskal_wallis_group_n_too_small`
- `kruskal_wallis_all_values_identical`
- `kruskal_wallis_statistic_not_finite`
- `kruskal_wallis_posthoc_variance_zero`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/kruskal_wallis_input.json`
- `backend/tests/reference/fixtures/kruskal_wallis_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_kruskal_wallis.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_kruskal_wallis_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
