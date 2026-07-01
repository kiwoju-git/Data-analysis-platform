# Dependency Review

Last reviewed: 2026-06-29

This file records direct dependencies introduced for the Gate A scaffold. Transitive dependency and vulnerability review must be refreshed when lockfiles are generated or dependency versions change.

## Backend

| Dependency | Version | Purpose | Python 3.10 / Windows / CPU-only | License note |
| --- | --- | --- | --- | --- |
| `fastapi` | `0.115.6` | HTTP API framework required by the product decision. | Supports Python 3.10 and does not require GPU. | MIT |
| `numpy` | `2.2.6` | SciPy numeric runtime dependency pinned after the Windows statistical dependency spike. | `cp310-win_amd64` wheel validated; CPU-only. | BSD |
| `pydantic-settings` | `2.7.0` | Typed environment-based settings without custom parsing. | Supports Python 3.10 and does not require GPU. | MIT |
| `python-multipart` | `0.0.32` | Multipart form parsing for browser file uploads through FastAPI `UploadFile`. | Supports Python 3.10 and does not require GPU. | Apache-2.0 |
| `scipy` | `1.15.3` | Shapiro-Wilk, Anderson-Darling, Levene/Brown-Forsythe, t-test, rank-test, and exact binomial statistical calculations. | `cp310-win_amd64` wheel validated; CPU-only. | BSD |
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

## Statistical Dependencies

NumPy 2.2.6 and SciPy 1.15.3 are now production-pinned for the current SciPy-backed EDA, Gate B2 hypothesis, and first two categorical slices after a native Windows Python 3.10.11 wheel-only smoke passed.

Before additional SciPy-backed methods become `available`, the implementation PR must record:

- exact SciPy version and any NumPy transitive version resolved for Python 3.10 on Windows;
- CPU-only import and smoke calculations for Shapiro-Wilk, Anderson-Darling, Levene, and Brown-Forsythe;
- license and wheel availability review;
- reference fixtures and edge-case tests for p-values, warnings, constant inputs, small N, large N, missing values, and non-finite values;
- full `scripts/check.ps1` pass from native Windows PowerShell.

The opt-in install-and-smoke command is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
```

The smoke-only command is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-stat-deps.ps1
```

`install-stat-deps-spike.ps1` installs candidate wheel-only NumPy/SciPy versions into the local `.venv` for validation. `check-stat-deps.ps1` runs `scripts/stat_dependency_smoke.py` against the existing `.venv`; it does not install SciPy/NumPy or change lockfiles. The default recorded smoke output is `logs\stat-dependency-smoke.json`, which can be checked with `scripts/validate_stat_dependency_smoke.py`. Record native Windows results in `docs/stat_dependency_spike.md`.

Recorded candidate spike result:

- Windows Python 3.10.11 `.venv` smoke passed with NumPy 2.2.6 and SciPy 1.15.3.
- Installed wheel metadata classifiers report `License :: OSI Approved :: BSD License` for both packages.
- Full `scripts/check.ps1` passed after the candidate spike in the local `.venv`.
- Production dependency pins have been added to `backend/pyproject.toml`.
- `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` are available with reference-backed tests. Re-run the dependency smoke before changing these pins or adding another SciPy-backed method.

Passing the dependency smoke remains necessary but not sufficient for any future SciPy-backed method.
