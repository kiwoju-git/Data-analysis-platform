Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    & $Python -m ruff check .\backend
    & $Python -m ruff format --check .\backend
    & $Python -m mypy .\backend\app
    & $Python -m pytest .\backend\tests
    npm --prefix .\frontend run lint
    npm --prefix .\frontend run typecheck
    npm --prefix .\frontend run test -- --run
    npm --prefix .\frontend run build
}
finally {
    Pop-Location
}
