# Paired t-Test Method Contract

Status: implemented for the current Gate B2 slice.

Method ID: `hypothesis.paired_t`

Implementation:

- Backend domain module: `backend/app/statistics/paired_t.py`
- API dispatch: `POST /api/v1/analysis-runs`
- Result retrieval: `GET /api/v1/analysis-runs/{analysis_id}/result`
- Frontend panel: `frontend/src/PairedTPanel.tsx`

## Scope

This slice supports wide paired data only:

- one numeric `before_column_id`
- one numeric `after_column_id`
- one pair per canonical row
- pair difference defined as `after - before`

Long format paired data with subject ID, condition, and response columns remains out of scope for this slice. The method must not be used as an independent two-sample test.

## Inputs

- `dataset_version_id`: required
- `options.before_column_id`: required, non-ID, numeric `integer` or `decimal`
- `options.after_column_id`: required, non-ID, numeric `integer` or `decimal`, different from before
- `options.alpha`: optional, default `0.05`, must be `0 < alpha < 1`
- `options.confidence_level`: optional, default `0.95`, must be `0 < confidence_level < 1`
- `options.alternative`: `two_sided`, `greater`, or `less`
- `options.null_difference`: explicit finite numeric reference difference, default `0`
- `options.missing_policy`: optional, currently only `complete_pair`
- `filter_snapshot`: supported through the common Workbench AND-filter engine

The method reads only validated canonical JSONL rows for the confirmed immutable dataset version. It must not reparse the raw upload.

## Missing And Invalid Values

Rows are excluded before calculation when either side of the pair is missing or cannot be parsed as a finite number using the dataset parsing decimal/thousands settings.

The result reports:

- `n_total`
- `n_used`
- `n_incomplete_pairs`
- `n_missing_before`
- `n_missing_after`
- `n_non_numeric_pairs`
- `n_non_numeric_before`
- `n_non_numeric_after`

## Result Shape

The result payload has `summary_type="paired_t_test"` and includes:

- `before` and `after` column metadata
- `design="wide_two_measurement_columns"`
- `difference_definition="after_minus_before"`
- `paired_sample` with before/after means, mean/median difference, difference SD/variance, min/max difference, and sign counts
- `contrast` with estimate, standard error, t statistic, df, p-value, confidence interval, and paired effect size
- `package_versions.numpy` and `package_versions.scipy`
- stable warning codes

The paired effect size currently reports Cohen dz standardized by the SD of pair differences and a Hedges-corrected standardized effect.

## Blocking Conditions

The API rejects the run instead of returning fake statistics when:

- fewer than two complete numeric pairs remain
- all pair differences are constant, producing zero standard error
- before/after columns are missing, identical, ID columns, or non-numeric
- alpha, confidence level, alternative, null difference, or missing policy is invalid

## Warnings

Current stable warning codes:

- `paired_t_design_assumption`
- `paired_t_not_auto_switched`
- `incomplete_pairs_excluded`
- `non_numeric_pairs_excluded`

`paired_t_design_assumption` must be present because the app cannot prove that each row truly represents the same subject/pair measured twice.

## Error Codes

Current stable request/calculation error codes:

- `dataset_version_required`
- `paired_t_before_column_required`
- `paired_t_after_column_required`
- `paired_t_same_before_and_after_column`
- `paired_t_before_column_not_found`
- `paired_t_after_column_not_found`
- `paired_t_before_column_is_id`
- `paired_t_after_column_is_id`
- `paired_t_before_column_not_numeric`
- `paired_t_after_column_not_numeric`
- `invalid_paired_t_alpha`
- `invalid_paired_t_confidence_level`
- `invalid_paired_t_alternative`
- `invalid_paired_t_null_difference`
- `paired_t_missing_policy_unsupported`
- `paired_t_n_too_small`
- `paired_t_standard_error_zero`

## Tests

Reference fixtures:

- `backend/tests/reference/fixtures/paired_t_input.json`
- `backend/tests/reference/fixtures/paired_t_scipy_reference.json`

Unit/API coverage:

- `backend/tests/unit/test_paired_t.py`
- `backend/tests/unit/test_api_contracts.py::test_analysis_run_executes_paired_t_from_dataset_version`

Frontend rendering coverage:

- `frontend/src/App.test.tsx`
