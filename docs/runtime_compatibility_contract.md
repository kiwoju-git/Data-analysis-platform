# Runtime Compatibility Contract

Last updated: 2026-07-23

## Purpose

DataLab Studio must not run a new frontend against an older backend that happens
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
- `api_contract_version` (currently `2`);
- the actual metadata schema constant (currently `15`);
- configured build commit or `unknown`;
- boolean capabilities for asset management, dataset/model metadata and
  deletion, dedicated Predict/Response Optimizer, and Bayesian Optimization.

The response contains no workspace path, filename, or raw data. Existing
`GET /api/v1/health` retains its liveness/readiness meaning.

## Frontend Gate

The frontend expects API contract `2`, schema 15 or later, and every required
capability before it renders the workspace or method catalog. A missing route,
old contract, malformed response, missing capability, or known build-commit
mismatch blocks the app and provides retry and restart instructions. Management
PATCH/DELETE requests therefore cannot be sent through the normal UI while the
gate is blocked.

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

## Error Boundary

Management clients preserve HTTP status, stable error code, route-not-found
classification, and correlation ID. The UI distinguishes:

- generic route 404: runtime/API contract mismatch;
- stable dataset/model not-found: deleted asset or stale catalog;
- `asset_user_metadata_conflict`: refresh before retry;
- dependency blockers: intended no-cascade protection with counts;
- checksum/path/manifest errors: integrity failure, not deletion.

No dependency blocker or integrity validation is weakened by this contract.
