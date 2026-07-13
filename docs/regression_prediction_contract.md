# Regression Prediction Contract

Last updated: 2026-07-13

## Scope

This contract covers the next Gate C1 slice for `regression.predict`, limited to predictions from app-created OLS `regression.linear_model` manifests.

Current implemented state:

- `POST /api/v1/regression-models/{model_id}/prediction-preflight` validates a target dataset version before prediction.
- The preflight returns schema, column mapping, numeric range, missing/non-numeric, categorical unseen-level, and usable-row counts.
- `regression.linear_model` manifest schema version `2` stores the coefficient order, inverse cross-product matrix, residual variance, and residual degrees of freedom needed for OLS prediction intervals.
- `POST /api/v1/regression-models/{model_id}/predictions` produces real backend prediction values from app-created OLS manifests after the same preflight path passes.
- Prediction results are stored as `regression.predict` analysis result envelopes with relative workspace paths and SHA-256 validation.
- Every valid prediction row is written atomically to a checksum-recorded, raw-predictor-free NDJSON analysis artifact.
- `GET /api/v1/regression-models/predictions/{prediction_id}/rows` returns checksum-validated pages of stored prediction rows.
- `GET /api/v1/dataset-versions` returns paged, raw-row-free target candidates across confirmed local datasets.
- `POST /api/v1/regression-models/predictions/{prediction_id}/exports/csv` streams every checksum-validated stored prediction row into a wide CSV export.
- The Linear Model UI can select a confirmed target version, run prediction after successful preflight, and render 25-row pages without exposing raw predictor values.

Current backend implementation scope:

- batch prediction for a confirmed target `dataset_version_id`
- app-created OLS manifests only
- canonical target rows only
- complete-case prediction rows only
- deterministic reconstruction of the original model design matrix from the stored JSON manifest
- predicted mean, mean-response confidence interval, individual prediction interval, row index, exclusion reason counts, warning metadata, and provenance
- inline POST response capped at 1,000 predicted rows for compatibility; all valid rows remain available through paged retrieval

Out of scope until later contracts:

- manual single-row prediction UI
- external model upload
- pickle/joblib model loading
- non-OLS regression, logistic regression, general ML prediction, response optimizer, DOE/RSM prediction
- automatic transformation or imputation of target data
- generated chart artifact export

## API

Implemented endpoint:

```text
POST /api/v1/regression-models/{model_id}/predictions
GET  /api/v1/regression-models/predictions/{prediction_id}/rows?limit=25&offset=0
GET  /api/v1/dataset-versions?limit=20&offset=0
POST /api/v1/regression-models/predictions/{prediction_id}/exports/csv
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

Rows are capped only in the inline POST response. The page endpoint accepts
`limit=1..200` and a non-negative `offset`, and returns `total`, `returned`,
`has_previous`, `has_next`, and raw-predictor-free prediction rows.

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

All valid rows are additionally stored as `application/x-ndjson` under a
relative workspace path and registered as a `regression_prediction_rows`
analysis artifact with SHA-256. Retrieval verifies the full artifact checksum,
row schema, and expected row count before returning a page. Analysis-run and
artifact metadata are inserted in one SQLite transaction. If metadata insertion
fails, both `result.json` and `prediction_rows.jsonl` are removed.

Prediction CSV exports are registered as
`regression_prediction_csv_export` analysis artifacts and use the existing
checksum-validated analysis export download route. The UTF-8-SIG wide CSV
contains prediction/model/source-target version provenance, manifest/schema
hashes, confidence level, row index, predicted mean, mean CI, prediction
interval, and warning codes. It never contains predictor input columns or raw
target cell values. Export generation exhausts the verified NDJSON iterator, so
the CSV is not published when row schema, count, or checksum validation fails.

If a result file is written before metadata insert and metadata insert fails, the file must be deleted.

## Tests

Implemented backend coverage:

- same-dataset OLS prediction API returns predicted mean, mean-response CI, and individual prediction interval
- a 1,005-row prediction preserves 1,000 inline rows and retrieves the remaining five through the page endpoint
- page rows contain only row index, prediction values, intervals, and warning codes
- NDJSON checksum/schema tampering returns a stable recovery error without exposing internal paths
- metadata insertion failure removes both result artifacts
- a 1,005-row prediction CSV contains all 1,005 stored rows, including rows omitted from the inline response
- prediction CSV download SHA matches metadata and its columns exclude raw predictors
- tampered prediction row artifacts block both page retrieval and CSV export
- stored prediction result is retrievable through the existing checksum-validated analysis result API
- stored prediction result checksum mismatch returns the existing recovery error without exposing internal paths
- missing required predictor rejects prediction execution through `regression_prediction_preflight_failed`
- categorical treatment-coded manifest terms are reconstructed for prediction
- numeric quadratic and numeric-by-numeric interaction terms are reconstructed for prediction
- insufficient manifest uncertainty metadata returns `regression_prediction_manifest_uncertainty_missing`
- `regression_linear_model_reference.json` cross-checks three treatment-coded
  predicted means, mean-response confidence intervals, and individual
  prediction intervals against statsmodels 0.14.6 full-precision output

Implemented frontend coverage:

- Linear Model panel renders preflight, enables prediction only after `prediction_ready=true`, and displays paged row index, predicted mean, mean-response CI, individual prediction interval, and warning codes without raw target cell values
- prediction page state is passed as one grouped prop contract and stale page responses cannot overwrite a newer prediction request
- prediction target catalog/selection state is owned by a dedicated hook; changing target cancels and clears older preflight, prediction, and row-page state
- prediction CSV generation/download state is owned by a dedicated latest-request-guarded hook and resets when prediction ID changes
- Playwright critical path registers a synthetic `y`/`x`/`group` dataset,
  separately registers a compatible four-row target, performs a real
  linear-model fit on 12 training rows, selects the other dataset version,
  verifies the stored-manifest preflight is ready for all four target rows,
  executes prediction, and checks the four-row summary, interval table, and
  rendered prediction-interval lines before creating and downloading the full
  prediction CSV

## Current UI Policy

The current UI defaults to the active dataset version and can explicitly select
another confirmed local dataset version from a paged catalog. Target changes
invalidate prior asynchronous prediction state. The UI displays 25-row result
pages and must not imply causation or expose raw target cell values.
After prediction, the UI can generate and download a checksum-recorded CSV of
all stored prediction rows; target selection is locked while export work is in
progress.

This storage and retrieval addition does not change prediction calculations or
the persisted statistical result fields, so `regression.predict` remains at
method version `0.1.0`. The internal prediction config schema is version `2`.
The CSV export schema is independently versioned at `1` and does not change the
`regression.predict` calculation or stored result interpretation.
