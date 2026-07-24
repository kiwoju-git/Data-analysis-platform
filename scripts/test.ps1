Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    & $Python -m pytest .\backend\tests
    if ($LASTEXITCODE -ne 0) {
        throw "Backend test suite failed with exit code $LASTEXITCODE."
    }
    npm --prefix .\frontend run test -- --run
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend test suite failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
