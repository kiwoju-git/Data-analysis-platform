# Local Workspace Asset Management Contract

Last updated: 2026-08-06

## Current Scope

The route-level lazy-loaded `/manage` page is `자산 관리` and provides `전체`,
`데이터셋`, `분석 결과`, `모델`, and `실험 설계·스터디` tabs. Confirmed
dataset versions, succeeded analysis runs, app-created regression models,
Factorial/LHS/RSM designs, and Bayesian Studies are already stored locally;
the page does not add a misleading save operation.
Users can page and refresh each catalog, assign an optional name and note, pin
an item, activate a dataset version, open a model in Predict, and run the
existing type-specific deletion impact workflows. The default catalog is a
compact `result-table`; a single selected row reveals detail and actions rather
than rendering an editable card for every stored asset.

`GET /api/v1/assets` is a bounded, read-only union catalog with category,
search, offset, and limit filters. Its descriptors expose safe display
metadata, status, dependency counts, and an application route. They do not
expose raw values, absolute/internal paths, SQL, full checksums, coefficients,
or model predictor levels. The endpoint does not imply a generic deletion
operation: each deletion action delegates to the owning retention contract.

The page is mounted only after the API contract-12 runtime handshake succeeds.
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
- `PATCH /api/v1/assets/{asset_type}/{asset_id}/metadata` for
  `analysis_run`, `doe_design`, and `bayesian_study`

The dataset metadata PATCH also accepts `archived`. An active dataset is
protected in the UI and must be replaced before archiving. Archived datasets
are omitted from ordinary dataset selectors but remain available under the
management page's `보관됨` filter and can be restored with `archived=false`.

Catalogs sort pinned items first, then by metadata/creation time and a stable ID
tie-break. They return no raw rows, coefficients, predictor levels, manifest
path, or internal absolute path. The active dataset selector and Predict model
catalog display `user_label` first and retain a safe fallback.

## UI And Safety

The unified catalog filter uses the neutral `CompactSettingsTable` component,
which is also the implementation behind the DOE compatibility wrapper. Search,
status, sort, and pinned-only controls therefore share the DOE header, input,
focus, disabled, and responsive table rules. Refresh remains a heading action.

No row is selected on initial load. Selecting `상세` inserts a valid detail
`<tr><td colspan=...>` immediately after that asset row; selecting it again
closes it and selecting another asset moves the single open detail. Dataset,
model, analysis, design, and study tabs use the same inline placement. Deletion
uses the type-owned retention preflight and an accessible in-app dialog rather
than `window.confirm()`.

The dataset tab uses `현재 분석 데이터셋으로 사용`, `이름 저장`,
`목록 새로고침`, and `삭제 영향 확인`. An active dataset version must be
replaced before its delete control is enabled. The model tab states that models
are automatically saved after a successful fit and reuses checksum-validated
availability and deletion preflight. `예측 입력 열기` places only the model
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

Dataset, model, analysis, export, archive, and restore mutations publish one
monotonic workspace-asset revision. The mounted management page revalidates
both dataset and regression-model catalogs after any revision rather than
refreshing only the tab that initiated the mutation. A row action that races
with another tab and receives a stable owner-not-found code clears the stale
row, refreshes the bounded catalog, normalizes an empty last page, and displays
a non-blocking informational notice. Direct links to an unknown owner retain
the explicit not-found empty state.

## Version Decision

User labels require SQLite schema 15 and dataset archive visibility requires
schema 16. SQLite schema 19 adds `workspace_asset_user_metadata` for analysis
runs, DOE designs, and Bayesian Studies because those owners previously had no
safe operational metadata relation. Cleanup triggers follow owner deletion;
optimistic updates use `expected_metadata_updated_at`. Stored result/design/
study JSON, checksums, dataset schema hashes, and model manifests are never
rewritten. This storage migration does not change a statistical method version.
