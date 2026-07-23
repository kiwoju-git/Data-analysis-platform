# Data And Regression Model Management Contract

Last updated: 2026-07-23

## Current Scope

The route-level lazy-loaded `/manage` page provides two tabs: `데이터셋` and
`회귀모델`. Confirmed dataset versions and app-created regression models are
already stored locally; the page does not add a misleading save operation.
Users can page and refresh each catalog, assign an optional name and note, pin
an item, activate a dataset version, open a model in Predict, and run the
existing deletion impact workflows.

The page is mounted only after the API contract-2 runtime handshake succeeds.
A generic HTTP 404 from a missing route is reported as a frontend/backend
version mismatch, while stable dataset/model not-found, optimistic metadata
conflict, dependency blocker, and integrity failure remain separate states.

## Operational Metadata

SQLite schema 15 adds `dataset_version_user_metadata` and
`regression_model_user_metadata`. Each row is owned by one existing version or
model and contains nullable `user_label`, nullable `note`, `pinned`, and
`updated_at`. Owner deletion cascades only this operational metadata row.

SQLite schema 16 extends dataset-version metadata only with `archived` and
`archived_at`. Existing rows migrate to visible state. Archiving is reversible,
does not touch files or dependent assets, and does not alter schema hashes,
analysis freshness, model manifests, or statistical results. The normal
dataset catalog defaults to `visibility=visible`; the management page can
request `visible`, `archived`, or `all`. Exact-ID lookup remains available for
restored audit links.

- labels are trimmed and limited to 120 characters;
- notes are trimmed and limited to 500 characters;
- control characters are rejected and empty strings become null;
- an optional `expected_metadata_updated_at` provides optimistic conflict
  detection;
- metadata changes do not mutate dataset rows, schema hash, analysis stale
  state, regression model manifest bytes, or manifest SHA;
- original filenames remain separate catalog metadata and are never replaced
  by a user label.

The update APIs are:

- `PATCH /api/v1/dataset-versions/{version_id}/metadata`
- `PATCH /api/v1/regression-models/{model_id}/metadata`

The dataset metadata PATCH also accepts `archived`. An active dataset is
protected in the UI and must be replaced before archiving. Archived datasets
are omitted from ordinary dataset selectors but remain available under the
management page's `보관됨` filter and can be restored with `archived=false`.

Catalogs sort pinned items first, then by metadata/creation time and a stable ID
tie-break. They return no raw rows, coefficients, predictor levels, manifest
path, or internal absolute path. The active dataset selector and Predict model
catalog display `user_label` first and retain a safe fallback.

## UI And Safety

The dataset tab uses `현재 분석 데이터셋으로 사용`, `이름 저장`,
`목록 새로고침`, and `삭제 영향 확인`. An active dataset version must be
replaced before its delete control is enabled. The model tab states that models
are automatically saved after a successful fit and reuses checksum-validated
availability and deletion preflight. `Predict에서 열기` places only the model
UUID in the URL.

No raw value, filename, note, or label is logged or written to browser storage.
Only the active dataset version ID continues to use session storage.

Successful metadata updates show an explicit saved state and refresh the
catalog metadata timestamp. A dependency-blocked deletion is an intended
protection state with counts, not a failed or missing API route. Dataset
integrity failures can offer metadata-only cleanup only when all dependency
counts are zero; unverified files remain untouched. Model impact shows bounded
dependent-prediction descriptors, Report Center links, individual prediction
deletion through the existing analysis-run contract, and an opt-in atomic
model-plus-predictions operation guarded by a separate irreversible
confirmation.

## Version Decision

This is operational metadata. It requires SQLite schema 15 and migration tests,
but no statistical method, result, config, dataset schema, or model manifest
version changes.
