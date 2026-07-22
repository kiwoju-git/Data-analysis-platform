# Regression Prediction Contract

Last updated: 2026-07-22

## Scope

`regression.predict` predicts confirmed local dataset versions from safe JSON
OLS manifests created by `regression.linear_model`. It is catalog-available
with `execution_mode=dedicated` through both the Linear Model panel and
`/analysis/regression/regression.predict`. The generic analysis-run endpoint
rejects it without creating a run or result.

Implemented scope:

- same-dataset and explicitly selected cross-dataset batch prediction
- app-created OLS manifests only; external pickle/joblib upload is forbidden
- canonical target rows and explicit complete-case handling
- exact reconstruction of numeric, categorical treatment-coded, quadratic,
  and numeric interaction terms stored by the source model
- predicted mean, mean-response confidence interval, individual prediction
  interval, warnings, exclusions, and dependency provenance
- at most 1,000 raw-predictor-free rows in the initial response
- all valid rows in checksum-recorded NDJSON with 25-row UI paging
- checksum-recorded full CSV creation/download without raw predictors
- metadata-only catalog labels: an optional user label is shown first, with a
  response/predictor-count/creation-time fallback; label edits never rewrite
  or weaken checksum validation of the selected model

Target schema-hash differences and unique display-name mappings are compatibility
warnings, not source-model freshness errors. The UI groups repeated mapping
warnings and retains predictor type/range detail. A stale source model, missing
or ambiguous predictor, incompatible type, unseen categorical level, or zero
usable target row remains blocking. Range extrapolation remains non-blocking
and is summarized per predictor with training bounds and outside-row count.

Manual single-row entry, non-OLS prediction, external models, automatic
imputation/transformation, response optimization, and chart-image export remain
out of scope.

## API

```text
POST /api/v1/regression-models/{model_id}/prediction-preflight
POST /api/v1/regression-models/{model_id}/predictions
GET  /api/v1/regression-models?limit=20&offset=0
GET  /api/v1/regression-models/predictions/{prediction_id}/rows?limit=25&offset=0
GET  /api/v1/dataset-versions?limit=20&offset=0
POST /api/v1/regression-models/predictions/{prediction_id}/exports/csv
```

Prediction request:

```json
{
  "dataset_version_id": "target-dataset-version-uuid",
  "confidence_level": 0.95,
  "missing_policy": "complete_case",
  "include_intervals": true
}
```

Response identity fields:

```json
{
  "prediction_id": "prediction-analysis-run-uuid",
  "model_id": "model-uuid",
  "analysis_id": "source-analysis-uuid",
  "source_analysis_id": "source-analysis-uuid",
  "source_dataset_version_id": "training-version-uuid",
  "target_dataset_version_id": "target-version-uuid",
  "model_manifest_sha256": "sha256",
  "target_schema_hash": "sha256"
}
```

`analysis_id` is retained as a compatibility alias for
`source_analysis_id`. The stored prediction analysis-run ID is
`prediction_id`. Page requests accept `limit=1..200` and a non-negative
`offset`.

## Source Model Freshness

Preflight validates source dependencies before scanning the target:

- the source analysis exists and is `regression.linear_model`
- the source analysis points to the model's source dataset
- analysis, model record, manifest metadata, and registry method versions agree
- the source analysis is not stale
- the source dataset version and canonical artifact still exist and validate
- the current source schema hash equals the schema hash stored at fit
- model manifest IDs, schema metadata, path metadata, and SHA-256 agree

Source issues are intentionally distinct:

- `regression_prediction_source_analysis_missing`
- `regression_prediction_source_analysis_invalid`
- `regression_prediction_source_model_stale`
- `regression_prediction_source_schema_mismatch`
- `regression_prediction_source_method_version_mismatch`

Any source error makes `prediction_ready=false`. Prediction execution shares
the same validation and returns HTTP 409
`regression_prediction_preflight_failed` with structured issue codes and a
refit instruction. Source-model staleness is not merged with target
schema/column incompatibility. A source schema no-op PATCH does not mark the
analysis stale and does not block prediction.

## Target Validation

For a separately confirmed target dataset, a different schema hash and
different internal predictor IDs are not automatically blocking. The frontend
groups repeated `prediction_column_matched_by_display_name` warnings and lets
the user inspect each source/target ID, display name, predictor kind, and match
status. It also explains that a schema-hash difference can be normal for a
separate immutable target when names are unique and types are compatible.

Numeric preflight presentation includes the manifest training minimum and
maximum beside below/above-range counts. These bounds were already used by the
preflight calculation; exposing them in the typed preflight response does not
change prediction formulas or persisted result/config schemas. If
`prediction_ready=true` and usable rows remain, warnings are shown as an
executable-with-review state. Source stale/schema errors remain visibly
blocking. Missing, ambiguous, or incompatible predictors block; unseen,
missing, or nonnumeric row values remain explicit row exclusions, and zero
usable rows block execution.

After source validation, preflight requires:

- an existing target version with a checksum-valid canonical artifact
- exact column-ID mapping or unambiguous display-name fallback
- compatible predictor kinds and recorded numeric parsing conventions
- categorical values limited to training levels
- explicit missing, non-numeric, unseen-level, and unusable-row counts
- visible numeric training-range/extrapolation warnings

Rows are excluded under the recorded complete-case policy, never silently
coerced or imputed. No raw target cell sample or internal path is returned.

## Statistical Contract

The design matrix is reconstructed from the stored manifest:

- manifest-controlled intercept
- original numeric predictor values
- stored categorical reference level and deterministic level order
- stored numeric quadratic source column
- stored numeric-by-numeric interaction columns

Intervals require the coefficient vector, inverse cross-product covariance
basis, residual variance, residual degrees of freedom, confidence level, and
package metadata. Missing or invalid uncertainty metadata returns
`regression_prediction_manifest_uncertainty_missing` or
`regression_prediction_manifest_invalid`; no alternate calculation or fake
interval is substituted.

Every result preserves warnings that predictions are model-based rather than
causal, OLS interval assumptions still apply, and extrapolation may be
unreliable.

## Provenance

The stored result and `RegressionPredictionProvenance` record:

- source analysis ID and stale state at prediction time
- source dataset version, fit/current schema hashes, and canonical SHA-256
- target dataset version, schema hash, and canonical SHA-256
- model ID, manifest SHA-256, and model-manifest schema version
- method ID/version and prediction schema version
- app version, Python version, platform, build commit, NumPy and SciPy versions
- missing policy, confidence level, interval flag, and creation time

Runtime/build/package fields reuse the common analysis provenance helper.
Provenance never records an internal path, original filename, or raw predictor
value.

## Storage And Consistency

Prediction persistence uses relative workspace paths and atomic result/row
writes. The prediction analysis run and rows artifact metadata are inserted in
one SQLite transaction; failed metadata persistence removes both files.

The NDJSON file begins with a raw-value-free relationship header and then stores
all valid prediction rows. Page and export reads verify the full file SHA-256,
header/schema, row schema, and expected row count.

A shared consistency validator requires these records to agree:

- `analysis_runs` DB record and `config_json`
- stored `result.json` envelope/provenance
- `regression_prediction_rows` artifact metadata and NDJSON header/body
- regression model record and model manifest metadata

It compares prediction/analysis ID, method ID/version, model ID, source analysis
ID, source/target dataset versions, manifest SHA-256, target schema hash,
predicted/expected row totals, result checksum, and rows checksum/count. It is
used by result restore, page retrieval, full CSV creation, prediction export
listing, and prediction export download.

Stable relationship errors are:

- `regression_prediction_metadata_invalid`
- `regression_prediction_result_config_mismatch`
- `regression_prediction_model_mismatch`
- `regression_prediction_artifact_mismatch`

The full UTF-8-SIG CSV includes prediction/model/source-target IDs, hashes,
confidence/interval metadata, row index, predicted values, intervals, and
warning codes. It never includes predictor columns or raw target cell values.

## Versions

- `METHOD_VERSIONS["regression.predict"]`: `0.2.0`
- persisted prediction result schema: `2`
- internal prediction config schema: `3`
- prediction rows artifact/header schema: `2`
- linear-model manifest schema: `2` (unchanged)
- prediction CSV export schema: `1` (unchanged)

The method receives a minor bump because required dependency provenance and
cross-artifact identity fields change the persisted result contract and restore
interpretation. Prediction formulas, predictor coding, intervals, and CSV
columns do not change. Registry `METHOD_VERSIONS` is the sole method-version
source; tests require catalog, service, DB run, result envelope, and provenance
versions to agree.

Existing `0.1.0` and older-schema artifacts are not silently rewritten.
Incompatible prediction artifacts return explicit recovery/consistency errors.

## Tests

Backend coverage includes:

- same- and cross-dataset predicted means and both interval types
- statsmodels 0.14.6 independent full-precision reference values
- numeric/categorical/quadratic/interaction design reconstruction
- source stale/schema drift, source missing/wrong method, method-version drift,
  manifest metadata drift, and source schema no-op behavior
- target mapping, range, missing/non-numeric, and unseen-level behavior
- complete retrieval and export of 1,005 rows beyond the inline cap
- checksum, schema, count, config, result, rows cross-link, model, method,
  target-version, prediction-ID, and manifest-SHA tampering
- restore/page/export/list/download rejection without paths or raw values

Frontend coverage executes actual history, export, comparison, restore,
prediction-target, prediction-export, preflight/prediction, and row-page hooks
with delayed Promises completed out of order. Reset/model/target/prediction
changes preserve the newest state and leave loading flags false.

Playwright covers real 12-row OLS fitting, separate four-row target selection,
preflight, prediction, interval rendering, row paging, full CSV creation and
download, and absence of raw predictor values.

## Current UI Policy

Prediction uses one shared `RegressionPredictionPanel` inside both the
`regression.linear_model` panel and the top-level dedicated Predict route. The
top-level route selects from a paged metadata-only model catalog, then calls the
existing checksum-validated full model endpoint. Catalog output excludes
coefficients, raw predictor values/levels, original filenames, and storage
paths. Model or target changes invalidate preflight, prediction, page, and
export state. ID-only `model_id`, `target_version_id`, and `prediction_id`
query fields restore source selection and the existing prediction after reload.
Restore calls the stored analysis-result consistency path; it does not
recompute. Method, prediction ID, model ID, target version, config/result/rows
relations, and checksums must all match. A missing/deleted model blocks new
preflight and prediction but does not make its already verified immutable
prediction result disappear; manifest or relationship integrity failures still
block restore.

Dedicated Predict does not render generic dataset-scoped analysis history or
generic export UI. Its own paged rows and prediction CSV creation/download are
the relevant result controls.

This entrypoint/catalog-only change keeps method `0.2.0`, result schema `2`,
config schema `3`, and rows schema `2`; calculation, predictor coding,
intervals, and persisted result meaning are unchanged.

The model catalog remains paged at 20 items and verifies each summary against
its app-owned manifest. This favors correctness but can be costly with hundreds
of models. Future work may add a lightweight verified summary/index, search,
filters, exact-ID lookup, and a large-catalog benchmark. Selecting a source
must always repeat full checksum and freshness validation.

## Page Performance Baseline

Measured 2026-07-14 through the real FastAPI/TestClient cross-dataset path on
Windows 10 build 19045, CPython 3.10.11, four logical CPUs, NumPy 2.2.6, SciPy
1.15.3, CPU only. Page size was 25. Values are one-run wall-clock time and
incremental `tracemalloc` Python peak allocation; native NumPy/SciPy memory is
not included.

| Predicted rows | First page | Middle page | Last page | Full CSV create |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.181 s / 3.817 MiB | 0.244 s / 3.775 MiB | 0.188 s / 3.783 MiB | 0.366 s / 5.159 MiB |
| 10,000 | 0.997 s / 3.799 MiB | 0.925 s / 3.789 MiB | 0.854 s / 3.506 MiB | 2.224 s / 5.783 MiB |
| 100,000 | 7.910 s / 3.798 MiB | 7.966 s / 3.789 MiB | 7.829 s / 3.784 MiB | 19.916 s / 5.502 MiB |

Every page intentionally rereads the complete immutable NDJSON artifact before
returning data. Similar first/middle/last times confirm the current O(N) safety
cost. Verification is not bypassed in this PR. Future candidates are a verified
immutable-artifact cache, row-offset index, chunk-hash manifest, and verified
session cache; each requires a separate invalidation, memory, and tamper-safety
review.
