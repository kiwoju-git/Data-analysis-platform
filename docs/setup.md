# DataLab Studio Setup

DataLab Studio is developed as a local single-user application for Windows 11, PowerShell, Python 3.10.x, CPU-only execution, and localhost access.

## Runtime Tool Versions

- Python: CPython 3.10.x
- Node.js: 22 LTS is recommended. The current Vite toolchain requires Node.js 20.19+ or 22.12+.

## Initial Setup

Run from the repository root in PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
npm --prefix .\frontend ci
```

After `scripts/` are available, prefer the shared entry points:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

## Browser E2E Smoke

The browser critical-path smoke is opt-in because it requires a local Chromium
browser binary. After bootstrap installs the Python dev dependencies, install
the browser once:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -InstallBrowsers
```

Run the smoke without reinstalling the browser:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics
```

For CI-style debugging, keep the temporary workspace and diagnostics under
separate known directories:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -WorkspaceRoot .\.tmp\e2e-workspace -DiagnosticsRoot .\.tmp\e2e-diagnostics -KeepWorkspace
```

The script starts backend and frontend servers on loopback-only test ports,
uses a temporary `DATALAB_WORKSPACE_ROOT`, runs the browser flow, and removes
the temporary workspace unless `-KeepWorkspace` is passed.

GitHub Actions runs the same browser smoke in a separate `e2e` job after the
Windows check job succeeds. CI uploads only diagnostics-root log files, failure
screenshots, and failure HTML snapshots as `e2e-logs`; it does not upload the
temporary data workspace. Local
`scripts/check.ps1` intentionally remains browser-free so routine checks do not
require a Playwright browser install.

The current smoke covers pasted TSV intake, XLSX and CSV file upload, empty-file
upload recovery, parser option editing for header row, missing tokens,
delimiter selection, named XLSX sheet selection, and CP949 text encoding
selection, parser error recovery for missing XLSX sheet names and text decoding
failure, parsing confirmation, dataset version creation, representative analyses,
saved-result restore/comparison, JSON/CSV/HTML export creation, JSON download,
schema stale UI behavior, regression prediction target-version selection, and
the prediction page API's first-page rendering plus full prediction CSV
generation/download. It also covers the P attribute control chart, two-level
factorial DOE analysis, response-surface CCD/full-quadratic fit and contour,
and the bounded Response Optimizer recommendation/desirability workflow.

NumPy and SciPy are part of the backend base install for the current `eda.normality` slice. The statistical dependency spike scripts remain available for revalidating or reviewing future SciPy-backed methods:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check-stat-deps.ps1
```

`install-stat-deps-spike.ps1` installs the candidate NumPy/SciPy wheels into `.venv` for local validation. `check-stat-deps.ps1` expects SciPy and NumPy to already be installed and does not install or pin new dependencies by itself. Record the result in `docs/stat_dependency_spike.md` before changing or expanding SciPy-backed method coverage.

The default spike output is `logs\stat-dependency-smoke.json`. Validate it with:

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json
```

Render a markdown record for `docs/stat_dependency_spike.md` with:

```powershell
.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json
```

## Development Servers

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm --prefix .\frontend run dev -- --host 127.0.0.1
```

The backend remains bound to loopback only. The default CORS allowlist accepts
the Vite UI at both `http://127.0.0.1:5173` and `http://localhost:5173`; no LAN
origin or wildcard is enabled.

## Local Data

Runtime workspaces, exports, logs, temp files, and SQLite data must not be stored in Git. The default backend workspace root is `%LOCALAPPDATA%\DataLabStudio\` on Windows, with `DATALAB_WORKSPACE_ROOT` available for development overrides.

The metadata database is initialized at `db\metadata.sqlite3` under the configured workspace root. See `docs/storage.md` for migration notes.

The default upload size limit is 100 MB and can be adjusted with `DATALAB_MAX_UPLOAD_BYTES` for development.
