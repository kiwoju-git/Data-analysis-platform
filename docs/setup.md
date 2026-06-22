# DataLab Studio Setup

DataLab Studio is developed as a local single-user application for Windows 11, PowerShell, Python 3.10.x, CPU-only execution, and localhost access.

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

## Development Servers

Backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm --prefix .\frontend run dev -- --host 127.0.0.1
```

## Local Data

Runtime workspaces, exports, logs, temp files, and SQLite data must not be stored in Git. The default backend workspace root is `%LOCALAPPDATA%\DataLabStudio\` on Windows, with `DATALAB_WORKSPACE_ROOT` available for development overrides.

The metadata database is initialized at `db\metadata.sqlite3` under the configured workspace root. See `docs/storage.md` for migration notes.

The default upload size limit is 100 MB and can be adjusted with `DATALAB_MAX_UPLOAD_BYTES` for development.
