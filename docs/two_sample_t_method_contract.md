# Two-Sample t-Test Method Contract

Status: implemented for the first Gate B2 slice.

Method ID: `hypothesis.two_sample_t`

Implementation:

- Backend domain module: `backend/app/statistics/two_sample_t.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/TwoSampleTPanel.tsx`

## Scope

This method computes one independent two-group mean comparison from one numeric response column and one group column:

- Welch two-sample t-test by default
- Pooled Student t-test only when the user explicitly selects `variance_assumption="pooled"`
- Mean difference as first encountered group minus second encountered group
- t statistic, degrees of freedom, p-value, confidence interval, Cohen's d, and Hedges' g

It does not run paired t-test, one-sample t-test, ANOVA, post-hoc tests, or any automatic method switch based on normality/equal-variance diagnostics.

## Inputs

- `dataset_version_id`: required
- `options.response_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.group_column_id`: required, non-ID, different from response
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
- `options.confidence_level`: optional, default `0.95`, must be `0 < confidence_level < 1`
- `options.alternative`: `two_sided`, `greater`, or `less`
- `options.variance_assumption`: `welch` or `pooled`, default `welch`
- `options.null_difference`: optional numeric finite value, default `0`
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

The result payload has `summary_type="two_sample_t_test"` and includes:

- `response` and `group` column metadata
- `groups[]` summaries with N, mean, median, variance, standard deviation, min, max
- `contrast` with estimate, standard error, t statistic, df, p-value, CI, and effect size
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

## Blocking Conditions

The API rejects the run instead of returning fake statistics when:

- usable group count is not exactly 2
- either group has fewer than 2 usable observations
- standard error is zero or non-finite

## Warnings

Current stable warning codes:

- `two_sample_t_independence_assumption`
- `two_sample_t_not_auto_switched`
- `pooled_variance_assumption_selected`
- `missing_values_excluded`
- `non_numeric_values_excluded`
- `constant_group`
- `group_size_imbalance`

`two_sample_t_not_auto_switched` must be present because normality and equal-variance diagnostics do not automatically choose Welch or pooled Student t-tests.

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `two_sample_t_response_required`
- `two_sample_t_group_required`
- `two_sample_t_same_response_and_group`
- `two_sample_t_response_column_not_found`
- `two_sample_t_group_column_not_found`
- `two_sample_t_response_column_is_id`
- `two_sample_t_response_column_not_numeric`
- `two_sample_t_group_column_is_id`
- `invalid_two_sample_t_alpha`
- `invalid_two_sample_t_confidence_level`
- `invalid_two_sample_t_alternative`
- `invalid_two_sample_t_variance_assumption`
- `invalid_two_sample_t_null_difference`
- `two_sample_t_missing_policy_unsupported`
- `two_sample_t_requires_exactly_two_groups`
- `two_sample_t_group_n_too_small`
- `two_sample_t_standard_error_zero`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/two_sample_t_input.json`
- `backend/tests/reference/fixtures/two_sample_t_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_two_sample_t.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_two_sample_t_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
