# Equal Variances Method Contract

Status: implemented for Gate B1.

Method ID: `eda.equal_variances`

Implementation:

- Backend domain module: `backend/app/statistics/equal_variances.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/EqualVariancesPanel.tsx`

## Scope

This method computes real equal-variance diagnostics for one numeric response column grouped by one group column:

- Brown-Forsythe test using SciPy Levene with `center="median"`
- Levene test using SciPy Levene with `center="mean"`
- Group summaries: N, mean, median, sample variance, sample standard deviation, min, max

It does not compute Bartlett, F-test, t-test, ANOVA, post-hoc tests, or any automatic downstream method switch.

## Inputs

- `dataset_version_id`: required
- `options.response_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.group_column_id`: required, non-ID, different from response
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
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

The result payload has `summary_type="equal_variances_test"` and includes:

- `response` and `group` column metadata
- `groups[]` summaries
- `tests[]` entries for `brown_forsythe` and `levene_mean`
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

Each test result includes:

- `computed`
- `statistic`
- `p_value`
- `alpha`
- `reject_equal_variances`
- `valid_group_n_min`
- `warnings`

If there are fewer than two groups, any group has fewer than two usable observations, all usable response values are constant, or SciPy returns a non-finite statistic/p-value, the test entry must set `computed=false` and must not fabricate statistic or p-value values.

## Warnings

Current stable warning codes:

- `equal_variances_not_method_switch`
- `missing_values_excluded`
- `non_numeric_values_excluded`
- `equal_variances_insufficient_groups`
- `equal_variances_group_n_too_small`
- `constant_response`
- `constant_group`
- `equal_variances_statistic_not_finite`

`equal_variances_not_method_switch` must be present because this diagnostic does not automatically choose pooled/Welch t-test or standard/Welch ANOVA.

## Error Codes

Current stable request validation error codes:

- `dataset_version_required`
- `equal_variances_response_required`
- `equal_variances_group_required`
- `equal_variances_same_response_and_group`
- `equal_variances_response_column_not_found`
- `equal_variances_group_column_not_found`
- `equal_variances_response_column_is_id`
- `equal_variances_response_column_not_numeric`
- `equal_variances_group_column_is_id`
- `invalid_equal_variances_alpha`
- `equal_variances_missing_policy_unsupported`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/equal_variances_input.json`
- `backend/tests/reference/fixtures/equal_variances_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_equal_variances.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_equal_variances_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
