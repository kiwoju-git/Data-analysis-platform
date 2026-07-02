# Regression Prediction Contract

Last updated: 2026-07-01

## Scope

This contract covers the next Gate C1 slice for `regression.predict`, limited to predictions from app-created OLS `regression.linear_model` manifests.

Current implemented state:

- `POST /api/v1/regression-models/{model_id}/prediction-preflight` validates a target dataset version before prediction.
- The preflight returns schema, column mapping, numeric range, missing/non-numeric, categorical unseen-level, and usable-row counts.
- `regression.linear_model` manifest schema version `2` stores the coefficient order, inverse cross-product matrix, residual variance, and residual degrees of freedom needed for OLS prediction intervals.
- `POST /api/v1/regression-models/{model_id}/predictions` produces real backend prediction values from app-created OLS manifests after the same preflight path passes.
- Prediction results are stored as `regression.predict` analysis result envelopes with relative workspace paths and SHA-256 validation.
- The Linear Model UI can run prediction after successful preflight and renders a capped, raw-value-free prediction result table.

Current backend implementation scope:

- batch prediction for a confirmed target `dataset_version_id`
- app-created OLS manifests only
- canonical target rows only
- complete-case prediction rows only
- deterministic reconstruction of the original model design matrix from the stored JSON manifest
- predicted mean, mean-response confidence interval, individual prediction interval, row index, exclusion reason counts, warning metadata, and provenance
- inline response capped at 1,000 predicted rows

Out of scope until later contracts:

- manual single-row prediction UI
- selecting a different target dataset version in the prediction UI
- paged prediction result retrieval
- external model upload
- pickle/joblib model loading
- non-OLS regression, logistic regression, general ML prediction, response optimizer, DOE/RSM prediction
- automatic transformation or imputation of target data
- chart rendering and export

## API

Implemented endpoint:

```text
POST /api/v1/regression-models/{model_id}/predictions
```

Request:

```json
{
  "dataset_version_id": "target-dataset-version-uuid",
  "confidence_level": 0.95,
  "missing_policy": "complete_case",
  "include_intervals": true
}
```

Response envelope:

```json
{
  "prediction_id": "prediction-run-uuid",
  "model_id": "model-uuid",
  "analysis_id": "source-analysis-uuid",
  "source_dataset_version_id": "training-dataset-version-uuid",
  "target_dataset_version_id": "target-dataset-version-uuid",
  "model_manifest_sha256": "sha256",
  "target_schema_hash": "sha256",
  "row_count_total": 100,
  "row_count_predicted": 97,
  "row_count_excluded": 3,
  "row_count_omitted": 0,
  "row_limit": 1000,
  "truncated": false,
  "confidence_level": 0.95,
  "warnings": [],
  "provenance": {},
  "columns": [],
  "rows": []
}
```

Rows are currently capped in the inline API response. A later paged retrieval endpoint is required before large prediction outputs are exposed in the UI.

## Validation Policy

Prediction must call the existing preflight logic first or share the same validation path. It must refuse to produce predictions when preflight reports an error severity issue.

Required checks:

- model manifest path and SHA-256 match metadata
- source row snapshot path and SHA-256 match manifest metadata
- target dataset version exists and has a valid canonical artifact
- required predictors map by exact column ID or explicit one-to-one display-name fallback
- target predictor types are compatible with the stored predictor kind
- numeric target values parse with the target dataset's recorded decimal/thousands options
- categorical target values must be present in the stored training levels
- missing, non-numeric, unseen, and structurally invalid rows are counted and excluded, not silently coerced
- numeric extrapolation is warned and recorded, not hidden

## Statistical Contract

OLS prediction must reconstruct the design matrix exactly from the stored manifest:

- intercept handling from the manifest
- numeric main effects by original predictor value
- categorical treatment coding with the stored reference level and level order
- numeric quadratic terms from the stored source column ID
- numeric-by-numeric interaction terms from the stored source column IDs

Prediction intervals require the stored model information needed to compute uncertainty:

- coefficient vector
- residual variance
- residual degrees of freedom
- inverse cross-product or equivalent covariance basis
- confidence level
- package versions

If the current manifest does not contain enough information for valid intervals, the prediction endpoint returns `regression_prediction_manifest_uncertainty_missing` or `regression_prediction_manifest_invalid` instead of fabricating intervals.

## Result Payload Requirements

Each predicted row must include:

- target row index
- predicted mean
- mean-response confidence interval when available
- individual prediction interval when available
- extrapolation warning flag
- display-safe exclusion or warning codes

Rows must not include raw input cell values unless a separate privacy-reviewed result-view contract explicitly allows them.

Required warnings:

- regression predictions are model-based estimates, not causal effects
- extrapolation beyond training ranges may be unreliable
- unseen categorical levels are excluded unless a future explicit policy supports them
- prediction intervals rely on OLS assumptions and the training residual variance

## Storage

Prediction results are stored as app-owned `regression.predict` analysis result envelopes with:

- relative workspace path only
- SHA-256
- prediction schema version
- model ID and manifest SHA-256
- source and target dataset version IDs
- target canonical artifact SHA-256
- request options
- package versions

If a result file is written before metadata insert and metadata insert fails, the file must be deleted.

## Tests

Implemented backend coverage:

- same-dataset OLS prediction API returns predicted mean, mean-response CI, and individual prediction interval
- stored prediction result is retrievable through the existing checksum-validated analysis result API
- stored prediction result checksum mismatch returns the existing recovery error without exposing internal paths
- missing required predictor rejects prediction execution through `regression_prediction_preflight_failed`
- categorical treatment-coded manifest terms are reconstructed for prediction
- numeric quadratic and numeric-by-numeric interaction terms are reconstructed for prediction
- insufficient manifest uncertainty metadata returns `regression_prediction_manifest_uncertainty_missing`

Implemented frontend coverage:

- Linear Model panel renders preflight, enables prediction only after `prediction_ready=true`, and displays prediction summary plus row index, predicted mean, mean-response CI, individual prediction interval, and warning codes without raw target cell values

Still required before expanding prediction:

- hand-checkable small fixture for mean prediction and intervals
- independent NumPy/SciPy reference fixture
- schema mismatch and missing predictor failure
- unseen categorical level exclusion
- numeric non-numeric/missing exclusion
- extrapolation warning
- manifest checksum mismatch recovery error
- interactive browser/E2E coverage for the upload-fit-preflight-predict flow

## Current UI Policy

The current UI runs prediction only for the active dataset version after successful stored-model preflight. It displays a small inline result table and must not imply causation or expose raw target cell values.
