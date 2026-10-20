# Runtime Compatibility Contract

## DOE Expansion (API 25)

API 25 adds the regular-fraction model preflight, structured alias view and
factorial result 4/config 5 (method 0.10.0). It reserves this integrated DOE
expansion contract for the subsequent RSM request/response additions. Metadata
remains 22: these additions do not require a SQL migration. Legacy artifact
readers remain explicit; runtime mismatch must still block execution.

## Pilot Follow-up After 0849aaa

API contract 24 adds full group identity and stable group indexes to newly
computed Equal Variances (method 0.3.0/result 3), Two-Sample t (0.2.0/result 2)
and Kruskal-Wallis (0.2.0/result 2) results. Previously accepted stored schemas
remain readable without rewriting artifact bytes or reconstructing truncated
names. Metadata remains 22: there is no new SQL structure. Frontend/backend
and Windows startup use 24; Linux reads the backend contract constant.
Axis/measurement formatting and local VOC diagnostics are presentation-only.
Historical contract numbers below describe earlier releases.

## 2026-10-18 Update

API contract 23 requires `expected_schema_hash` on dataset schema PATCH requests.
The value identifies the schema on which the user's draft was based. Storage
checks it atomically with column/hash/stale updates; a stale draft returns
`409 dataset_schema_conflict`, including when its values match a newer schema.
A valid no-op does not mark results stale. Frontend conflict resolution preserves
the draft and requires an explicit choice before rebasing; no automatic retry
with a newly fetched hash is allowed.

The backend, frontend and PowerShell startup require contract 24; Linux startup
and release builds read the same backend constant. CAS alone uses existing
columns. A12 added metadata 21 for source-bound LHS/BO reports and the DOE HTML
schema constraint, not for CAS. A13 advances the current metadata requirement to
22 for a nullable analysis-run failure code used by interrupted-execution recovery.
Statistical method/result/model versions and
historical artifact bytes are unchanged. Historical notes below retain their
original numbers and are not current handshake requirements.

A11 adds report capability schema 1 under this same integrated API 23 update.
Catalog method report declarations and stored-result capability use the same
renderer contracts. Generic HTML artifact schema 4 adds level/renderer/sections;
optional expected source SHA binds a create request to its capability. A11 alone
does not change metadata or analysis result/model schemas, and old HTML bytes are not
rewritten. See `html_report_coverage_matrix.md` for the actual per-payload scope.

A12 adds typed `/api/v1/reports` source, capability, explicit read-only snapshot,
create/list/download/delete APIs under the integrated API 23 contract. The six
source kinds are discriminated unions, with exact revision and source hashes.
PLS/GP point-prediction requests add `save_result=false`; successful opt-in saves
return a server-created `saved_prediction` reference. Existing requests and
stored prediction/model numerical values retain their prior meaning. New DOE
HTML assets use schema 2; existing schema 1 HTML/prediction bytes are preserved.
See `managed_report_storage_contract.md` for migration, deletion and recovery.

A13 explicitly declares method execution/cancellation/progress capabilities and
persists `execution_interrupted_on_restart` for abandoned nonterminal runs, after
the exclusive workspace lease is acquired. The integrated API remains 23. Offline
backup/restore accepts exact metadata schemas 20, 21 and 22 without migrating the
source or restored database; normal server startup applies pending migrations.

## 2026-10-08 Update

API contract22 adds the Two Variances preflight/execution contract; minimum
metadata schema remains20. Windows and Linux startup validate the same service,
API/schema/capabilities/build identity. Linux source archives use the same
archive-sha256 fingerprint inputs as PowerShell. Built releases take identity
from verified BUILD_INFO.json; they do not disable compatibility checks or use
"unknown" as a successful release identity. See linux_release_contract.md.

2026-09-18 startup extension: `dev.ps1` now exposes the frontend on
`0.0.0.0:8600` for trusted LAN development, with an unchanged loopback backend
and same-origin `/api` proxy. `-LocalOnly` restores local-only binding. Exact
commit, API 21 and metadata 20 checks remain required. No wire/schema version
change is needed. See `trusted_lan_development.md` for network/security scope.

Last updated: 2026-09-17

API contract 21 adds explicit standalone GPR length-scale coordinates/bounds and
optimizer selection. GP writes method 0.3.0/result 3/manifest 3; legacy omitted
options retain 0.01..100/L-BFGS-B. Metadata remains 20: JSON extensions need no
relational migration. PLS report and navigation fixes do not change calculations.

API contract 20 adds server-owned DOE term catalogs/manual policies and typed
standalone GP single/compare kernel selection to the final-model workflows.
Backend, frontend and PowerShell
startup checks use the same contract value. Historical release notes below keep
their original version numbers; they are not current handshake requirements.

Minimum metadata schema is 20. Migration 20 adds an analysis-owned prediction/
HTML artifact relation; generic analysis-run artifacts cannot reference DOE
analyses safely. Existing design/result/revision data are not rewritten.

## Purpose

Statistical Twin must not run a new frontend against an older backend that happens
to own the same localhost port. A liveness response alone is insufficient: the
frontend and destructive management workflows require an explicit API contract
and capability handshake.

## Reproduced Failure

The failure was reproduced from starting main SHA
`6cc097a6f3d2983feab1fd7e4ccc2c5ab16f765d` while an older process was already
listening on `127.0.0.1:8000`.

- PID `25740` ran `python -m uvicorn app.main:app ... --port 8000` and returned
  a ready health response.
- Its OpenAPI document had none of the dataset/model metadata and deletion
  routes and no runtime-info route.
- Dataset/model metadata PATCH and deletion-preflight GET requests returned
  HTTP 404 with the generic `not_found` wrapper.
- Its method catalog returned Predict and Response Optimizer as
  `disabled/inline`, and Bayesian Optimization as `planned/inline`.
- Starting the current backend on port 8000 failed with Windows socket error
  10048. The previous `dev.ps1` did not surface that child failure.
- PID `26084` already owned port 5173. Vite silently selected 5174, so a new
  frontend remained usable while still calling the old backend at port 8000.

No existing process was terminated during reproduction. The observed response
combination establishes a mixed-version runtime, not missing routes in current
source.

## Backend Handshake

`GET /api/v1/runtime-info` returns a typed, `Cache-Control: no-store` response:

- service and app version;
- `api_contract_version` (currently `23`);
- the actual metadata schema constant (currently `22`);
- configured build commit or `unknown`;
- boolean capabilities for asset management, dataset/model metadata and
  deletion, dedicated Predict/Response Optimizer, Bayesian Optimization, and
  Graph Builder preview, immutable dataset cell correction, standalone LHS
  design, Bayesian LHS initial design, typed Bayesian objective goals, and
  atomic Bayesian recommendation batches, and standalone Gaussian Process
  Regression.

The response contains no workspace path, filename, or raw data. Existing
`GET /api/v1/health` retains its liveness/readiness meaning.

## Frontend Gate

Contract 18 adds OLS/Ridge/Lasso/Elastic Net options under the existing
`regression.linear_model`, discriminated schema-4 JSON manifests, point-only
regularized prediction and model-kind optimizer metadata. Metadata schema 19
and existing artifact ownership remain sufficient; no migration or stored
checksum rewrite is performed. Exact frontend/backend matching is required.

The frontend expects API contract `25`, schema 22 or later, and every required
capability before it renders the workspace or method catalog. A missing route,
old contract, malformed response, missing capability, or known build-commit
mismatch blocks the app and provides retry and restart instructions. Management
PATCH/DELETE requests therefore cannot be sent through the normal UI while the
gate is blocked.

Contract 12 extends Graph Preview scatter roles to fixed-X/multiple-Y and
multiple-X/fixed-Y, returns schema-2 descriptive, graphical-summary, and
equal-variance results, creates human-readable HTML report artifacts, and adds
optimistic user metadata editing for unified assets. Exact contract matching
prevents an older backend from accepting only part of these requests. Metadata
schema 19 adds user label, note, and pin ownership for analysis runs, DOE
designs, and Bayesian studies without rewriting the immutable result or design
artifacts they describe.

Contract 13 adds the typed `en`/`ko` HTML-report request and records
`report_locale` on new artifact-schema-3 responses. Locale changes presentation
only: API field names, statistical values, result schemas, stored result
checksums, and existing schema-1/2 HTML artifacts are unchanged. Every frontend
request sends the current locale in `Accept-Language`; exact contract matching
prevents an older backend from silently ignoring the localized-report body.

Contract 14 adds `regression.partial_least_squares` to the method catalog,
extends regression-model catalog identities to distinguish OLS and PLS, and
adds the typed PLS point-prediction route. Metadata schema 19 remains valid;
model kind and prediction coefficients are stored in the checksummed JSON
manifest rather than a new SQLite relation.

Contract 15 adds the discriminated stacked/unstacked Mann-Whitney request,
selected levels for stacked variables with more than two groups, schema-2
Mann-Whitney results, and numeric/categorical two-level factorial factor
contracts. New two-level factorial writes use design schema 2 and can store
actual text levels while retaining the existing coded `-1/+1` matrix. Metadata
schema 19 remains sufficient because factors and runs are already stored as
checksummed JSON; no SQLite migration or legacy artifact rewrite is performed.

Contract 16 adds standalone Gaussian Process Regression and its safe model
artifact/prediction contracts. Contract 17 adds executable
`eda.principal_components`, raises validated LHS and Bayesian factor definitions
to ten, exposes ten-factor factorial/general-factorial authoring with explicit
run feasibility, and adds the catalog-backed 12-run Plackett-Burman screening
design. Metadata remains schema 19 because all new meanings fit existing
checksummed JSON artifacts; existing results and checksums are not rewritten.

Contract 16 adds the available `regression.gaussian_process` catalog method,
typed analysis result, safe model-owned numeric artifact, and probabilistic
point-prediction route. Metadata schema stays at 19 because the existing
generic regression-model and artifact ownership records cover the JSON
manifest and NPZ state. PLS and Bayesian calculation contracts are unchanged.

Build commit `unknown` is not treated as proof of a mismatch. When both commits
are known, they must match for this strict local runtime.

## Development Startup

`scripts/dev.ps1` now:

1. verifies the Python virtual environment, npm, and `node_modules`;
2. rejects occupied backend/frontend ports and prints PID/process details;
3. never kills an existing process;
4. starts the backend and polls runtime-info;
5. stops before Vite when the backend exits early or readiness times out;
6. starts Vite with an explicit API base and `--strictPort` only after the
   handshake passes;
7. cleans up only the backend job it created.

`-ReuseCompatibleBackend` is explicit and accepts only the same known build,
contract, schema, and capability set. `scripts/diagnose-dev.ps1` reports ports,
runtime contract, management OpenAPI paths, and the three dedicated method
states without changing processes or repository settings.

The default browser entry point is `http://127.0.0.1:8600`. Vite dev/preview,
the PowerShell startup and diagnostics scripts, backend CORS defaults, and the
runtime mismatch guidance use this same loopback port. Port 8000 remains the
backend-only API listener.

## Error Boundary

Management clients preserve HTTP status, stable error code, route-not-found
classification, and correlation ID. The UI distinguishes:

- generic route 404: runtime/API contract mismatch;
- stable dataset/model not-found: deleted asset or stale catalog;
- `asset_user_metadata_conflict`: refresh before retry;
- dependency blockers: intended no-cascade protection with counts;
- checksum/path/manifest errors: integrity failure, not deletion.

No dependency blocker or integrity validation is weakened by this contract.
