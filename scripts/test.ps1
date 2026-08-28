Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PreviousPythonPath = $env:PYTHONPATH

Push-Location $RepoRoot
try {
    $env:PYTHONPATH = Join-Path $RepoRoot "backend"
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
    $env:PYTHONPATH = $PreviousPythonPath
    Pop-Location
}
