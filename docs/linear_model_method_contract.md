# Linear Model Method Contract

Last updated: 2026-07-01

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
- frontend prediction execution and capped raw-value-free prediction result display for the active dataset version

Current out of scope:

- categorical interactions, factor-by-numeric interactions, higher-order interactions, arbitrary formulas, and no-intercept models
- HC3 or other robust covariance estimators
- diagnostic chart artifacts
- selecting a different target dataset version in the prediction UI, paged prediction result retrieval, and response optimization
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

`POST /api/v1/regression-models/{model_id}/predictions` accepts a target `dataset_version_id`, confidence level, complete-case missing policy, and interval flag. It reuses the same preflight path, rejects error-severity preflight failures, reconstructs the OLS design matrix from the stored manifest, returns predicted means plus mean-response confidence intervals and individual prediction intervals, stores the result as a `regression.predict` analysis result envelope, and does not expose raw cell values.

The prediction calculation contract and remaining frontend/paged-result requirements are tracked separately in `docs/regression_prediction_contract.md`.

Current result payload `schema_version`: `4`.
Current model manifest `manifest_schema_version`: `2`.

## Testing

Required coverage for this method:

- hand-checkable small sample for model shape, R², and coefficient estimates
- generated reference fixture cross-checked with independent NumPy calculations
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
