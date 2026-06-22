Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    & $Python -m pytest .\backend\tests
    npm --prefix .\frontend run test -- --run
}
finally {
    Pop-Location
}
