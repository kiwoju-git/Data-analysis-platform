$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found. Run .\scripts\bootstrap.ps1 first."
}

& $python (Join-Path $PSScriptRoot "tutorial_smoke.py") @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
