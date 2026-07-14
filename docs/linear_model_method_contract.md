# Linear Model Method Contract

Last updated: 2026-07-14

## Scope

`regression.linear_model` is the third narrow Gate C1 executable method for a single confirmed dataset version.

Current supported input:

- one dataset-backed numeric response column
- one or more dataset-backed numeric predictor columns
- categorical main-effect predictor columns with treatment coding
- optional numeric quadratic terms
- optional numeric-by-numeric interaction terms
- intercept-included ordinary least squares main effects
- complete-case missing handling across response and selected predictors
- explicit `alpha` and confidence level
- standard OLS covariance only
- residual, leverage, and Cook's distance diagnostic payloads
- safe app-created JSON model manifest storage with checksum-validated retrieval
- stored-model prediction preflight for a target dataset version
- backend stored-model prediction from app-created OLS manifests through `regression.predict`
- frontend same/cross-dataset prediction execution, paged raw-value-free result
  display, and full prediction CSV export

Current out of scope:

- categorical interactions, factor-by-numeric interactions, higher-order interactions, arbitrary formulas, and no-intercept models
- HC3 or other robust covariance estimators
- diagnostic chart artifacts
- manual single-row prediction input and response optimization
- automatic causal interpretation

## Statistical Policy

- The model is fit with NumPy least squares on a validated design matrix with an intercept column.
- Categorical predictors use deterministic treatment coding with the first sorted observed level as the reference and `k - 1` design columns.
- Optional quadratic and interaction terms are built only from selected numeric predictors. They are explicit request options, not auto-selected diagnostics.
- Coefficient p-values and confidence intervals use SciPy t distributions with residual degrees of freedom.
- The model-level F test uses SciPy F survival probabilities.
- Missing or non-numeric values in any selected model column are excluded under one complete-case policy with explicit counts.
- Constant response columns, constant numeric predictor columns, constant extra terms, single-level categorical predictors, excessive categorical levels, rank-deficient designs, too-small residual degrees of freedom, zero residual variance, and non-finite standard errors are rejected without returning fake statistics.
- The result reports N, exclusions, model terms, categorical reference levels, coefficient estimates, standard errors, t statistics, p-values, confidence intervals, R², adjusted R², residual standard error, F test, VIF, condition number, residual summary, leverage summary, Cook's distance summary, capped diagnostic points, warning codes, package versions, and provenance.
- The result always warns that regression coefficients from observational data are not causal effects and that OLS relies on linearity, independence, homoscedasticity, residual-normality, and outlier/influence assumptions.
- Diagnostic points include row index, fitted value, residual, standardized residual, leverage, and Cook's distance only. They do not include raw input cell values and are capped for UI payload size while summary diagnostics use all complete-case rows.

## API Contract

`POST /api/v1/analysis-runs` options:

```json
{
  "response_column_id": "response-column-id",
  "predictor_column_ids": ["x1-column-id", "x2-column-id"],
  "quadratic_terms": ["x1-column-id"],
  "interaction_terms": [
    {"left_column_id": "x1-column-id", "right_column_id": "x2-column-id"}
  ],
  "alpha": 0.05,
  "confidence_level": 0.95,
  "missing_policy": "complete_case",
  "include_intercept": true,
  "covariance_type": "standard"
}
```

The analysis reads validated canonical JSONL rows for the provided `dataset_version_id`, writes an `analysis_row_snapshot` artifact, persists the result envelope, writes a safe JSON `regression_model_manifest` artifact, and supports checksum-validated result retrieval through `GET /api/v1/analysis-runs/{analysis_id}/result`.

The persisted result includes a model-manifest pointer:

```json
{
  "model_manifest": {
    "model_id": "model-uuid",
    "manifest_schema_version": 2,
    "manifest_sha256": "sha256"
  }
}
```

`GET /api/v1/regression-models/{model_id}` returns the stored manifest after validating the manifest path and SHA-256. The manifest stores the app-created OLS specification, coefficients, fit summary, diagnostic summary, dataset version, schema hash, canonical artifact hash, row snapshot hash, package versions, limitations, and prediction basis for OLS intervals. It is JSON only; pickle/joblib and uploaded external model artifacts remain forbidden.

`POST /api/v1/regression-models/{model_id}/prediction-preflight` accepts a target `dataset_version_id` and validates the stored manifest checksum before scanning the target dataset's canonical rows. The response reports schema-hash match, required-column mapping by exact column ID or one-to-one display name fallback, numeric target missing/non-numeric counts, numeric values outside the training range, categorical unseen-level counts, usable row count, and structured warning/error issues. It does not expose raw cell samples or absolute paths.

Before target checks, prediction preflight validates that the source analysis
still exists, is a fresh `regression.linear_model` run, has a method version
matching the model metadata, and still points to a source schema hash equal to
the fit-time manifest hash. A stale source model or source schema mismatch
makes preflight not ready and requires refitting; target incompatibility remains
a separate issue class. Source schema no-op updates do not block prediction.

`POST /api/v1/regression-models/{model_id}/predictions` accepts a target `dataset_version_id`, confidence level, complete-case missing policy, and interval flag. It reuses the same freshness/preflight path, rejects error-severity failures, reconstructs the OLS design matrix from the stored manifest, returns predicted means plus mean-response confidence intervals and individual prediction intervals, stores the result as a `regression.predict` analysis result envelope with source/target/model provenance, and does not expose raw cell values. Restore, paging, and full CSV export validate the result/config/rows/model relationships as well as each artifact checksum.

The prediction calculation contract and remaining frontend/paged-result requirements are tracked separately in `docs/regression_prediction_contract.md`.

Current result payload `schema_version`: `4`.
Current model manifest `manifest_schema_version`: `2`.

## Independent Reference Validation

- `backend/tests/reference/fixtures/regression_linear_model_reference.csv` is
  a compact synthetic training dataset with one numeric predictor and one
  three-level categorical predictor.
- `backend/tests/reference/fixtures/regression_linear_model_reference.json`
  records full-precision statsmodels 0.14.6 OLS results generated in a temporary
  Python 3.10 environment. statsmodels is not added to production or test
  dependencies.
- The reference formula uses an intercept, numeric `x`, and explicit treatment
  coding with level `A` as the categorical reference. Application and
  statsmodels term arrays have different order, so coefficients are compared by
  the recorded term-name mapping.
- The fixture cross-checks N/df, coefficients, standard errors, t statistics,
  p-values, coefficient intervals, residual sigma, R-squared, adjusted
  R-squared, F statistic/p-value, VIF, and condition number with `1e-8` absolute
  tolerance.
- Three synthetic prediction rows cross-check predicted means, mean-response
  confidence intervals, and individual prediction intervals against
  `OLSResults.get_prediction(...).summary_frame(alpha=0.05)`.
- A paired failure case rejects a categorical predictor with only one observed
  level. No fallback model or fabricated statistic is returned.
- The fixture does not pin a model-manifest SHA-256 because the safe JSON
  manifest contains generated analysis/model IDs and provenance. API tests
  independently verify manifest checksum equality, validated retrieval,
  checksum-mismatch recovery, row-snapshot provenance, and no pickle/joblib
  loading.
- The data is synthetic and validates arithmetic/coding only; it does not prove
  causation, assumption satisfaction, or adequacy for real data.

## Testing

Required coverage for this method:

- hand-checkable small sample for model shape, R², and coefficient estimates
- generated reference fixture cross-checked with independent statsmodels 0.14.6
  calculations from a synthetic CSV
- categorical factor treatment-coding fixture with explicit reference level and coefficient checks
- numeric quadratic and numeric-by-numeric interaction fixture with explicit term metadata and coefficient checks
- residual, leverage, Cook's distance, and capped diagnostic-point reference checks
- missing and non-numeric complete-case exclusion counts
- invalid-input failures for too-small residual degrees of freedom, constant response, constant numeric predictor, constant extra term, single-level factor, excessive factor levels, unsupported predictor type, invalid extra term requests, non-numeric extra term requests, and rank-deficient design
- API execution from a dataset version after raw upload mutation
- stored result retrieval equality and row snapshot provenance
- regression model manifest metadata persistence, checksum-validated API retrieval, checksum mismatch recovery error, and cleanup after metadata-insert failure
- prediction preflight for same-version clean data and target-version schema drift, display-name mapping, extrapolation, missing/non-numeric values, and unseen categorical levels
- backend prediction API for same-version OLS predicted means, mean-response confidence intervals, individual prediction intervals, stored result retrieval, and preflight-error rejection
- Playwright browser flow for synthetic TSV registration, explicit
  response/predictor selection, real fit/manifest creation, same-version
  prediction preflight, prediction execution, summary/table checks, and
  interval-line rendering
