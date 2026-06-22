# Dependency Review

Last reviewed: 2026-06-22

This file records direct dependencies introduced for the Gate A scaffold. Transitive dependency and vulnerability review must be refreshed when lockfiles are generated or dependency versions change.

## Backend

| Dependency | Version | Purpose | Python 3.10 / Windows / CPU-only | License note |
| --- | --- | --- | --- | --- |
| `fastapi` | `0.115.6` | HTTP API framework required by the product decision. | Supports Python 3.10 and does not require GPU. | MIT |
| `pydantic-settings` | `2.7.0` | Typed environment-based settings without custom parsing. | Supports Python 3.10 and does not require GPU. | MIT |
| `python-multipart` | `0.0.32` | Multipart form parsing for browser file uploads through FastAPI `UploadFile`. | Supports Python 3.10 and does not require GPU. | Apache-2.0 |
| `uvicorn[standard]` | `0.32.1` | Local ASGI development server bound to `127.0.0.1`. | Supports Python 3.10 and does not require GPU. | BSD-3-Clause |

## Backend Dev

| Dependency | Version | Purpose | Compatibility note | License note |
| --- | --- | --- | --- | --- |
| `httpx` | `0.28.1` | FastAPI `TestClient` support. | Python 3.10 compatible. | BSD-3-Clause |
| `mypy` | `1.13.0` | Static type checking. | Python 3.10 compatible. | MIT |
| `pytest` | `8.3.4` | Unit and integration tests. | Python 3.10 compatible. | MIT |
| `ruff` | `0.8.4` | Linting and format checks. | Windows binary available; CPU-only. | MIT |

## Frontend

| Dependency | Version | Purpose | Runtime behavior | License note |
| --- | --- | --- | --- | --- |
| `react` | `18.3.1` | UI rendering. | Bundled locally; no CDN. | MIT |
| `react-dom` | `18.3.1` | Browser DOM rendering. | Bundled locally; no CDN. | MIT |
| `vite` | `8.0.16` | Local dev server and build tool. | Dev server binds to `127.0.0.1`; requires Node `^20.19.0 || >=22.12.0`. | MIT |
| `@vitejs/plugin-react` | `6.0.2` | React transform for Vite. | Build-time only; requires Node `^20.19.0 || >=22.12.0`. | MIT |
| `typescript` | `5.6.3` | Strict TypeScript compilation. | Build-time only. | Apache-2.0 |
| `vitest` | `4.1.9` | Frontend tests. | Build/test-time only. | MIT |
| `eslint` and plugins | pinned in `frontend/package.json` | Frontend linting. | Build/test-time only. | MIT |

## Review Notes

- Standard library alone is insufficient for the required FastAPI backend and React/Vite frontend.
- No dependency is added for telemetry, external data upload, GPU, PyTorch, PyCaret, Optuna, SHAP, LIME, Docker, Redis, or a CDN.
- No GPL, AGPL, SSPL, commercial, or evaluation-only direct dependency is introduced.
- Direct dependency versions are pinned. `frontend/package-lock.json` must be generated with `npm --prefix .\frontend install --package-lock-only --ignore-scripts` before using `npm ci`.
