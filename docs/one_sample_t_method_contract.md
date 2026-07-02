# One-Sample t-Test Method Contract

Status: implemented for the second Gate B2 slice.

Method ID: `hypothesis.one_sample_t`

Implementation:

- Backend domain module: `backend/app/statistics/one_sample_t.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/OneSampleTPanel.tsx`

## Scope

This method compares one numeric response column against one explicit reference mean:

- One-sample t-test
- Mean difference as sample mean minus `null_mean`
- t statistic, degrees of freedom, p-value, confidence interval, Cohen dz, and Hedges-corrected standardized effect

It does not run paired t-test, two-sample t-test, Wilcoxon signed-rank, or any automatic method switch based on normality diagnostics.

## Inputs

- `dataset_version_id`: required
- `options.response_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.null_mean`: optional numeric finite value, default `0`
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
- `options.confidence_level`: optional, default `0.95`, must be `0 < confidence_level < 1`
- `options.alternative`: `two_sided`, `greater`, or `less`
- `options.missing_policy`: optional, currently only `complete_case`
- `filter_snapshot`: supported through the common Workbench AND-filter engine

The method reads only validated canonical JSONL rows for the confirmed immutable dataset version. It must not reparse the raw upload.

## Missing And Invalid Values

Rows are excluded before calculation when:

- response is missing
- response cannot be parsed as a finite number using the dataset parsing decimal/thousands settings

The result reports `n_total`, `n_used`, `n_missing`, and `n_non_numeric`.

## Result Shape

The result payload has `summary_type="one_sample_t_test"` and includes:

- `response` column metadata
- `sample` summary with N, mean, median, variance, standard deviation, min, max
- `contrast` with estimate, standard error, t statistic, df, p-value, CI, and effect size
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

## Blocking Conditions

The API rejects the run instead of returning fake statistics when:

- fewer than 2 usable observations remain
- standard error is zero or non-finite

## Warnings

Current stable warning codes:

- `one_sample_t_design_assumption`
- `one_sample_t_not_auto_switched`
- `missing_values_excluded`
- `non_numeric_values_excluded`

`one_sample_t_not_auto_switched` must be present because normality diagnostics do not automatically switch this method to a nonparametric alternative.

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `one_sample_t_response_required`
- `one_sample_t_response_column_not_found`
- `one_sample_t_response_column_is_id`
- `one_sample_t_response_column_not_numeric`
- `invalid_one_sample_t_alpha`
- `invalid_one_sample_t_confidence_level`
- `invalid_one_sample_t_alternative`
- `invalid_one_sample_t_null_mean`
- `one_sample_t_missing_policy_unsupported`
- `one_sample_t_n_too_small`
- `one_sample_t_standard_error_zero`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/one_sample_t_input.json`
- `backend/tests/reference/fixtures/one_sample_t_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_one_sample_t.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_one_sample_t_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
