param(
    [ValidateRange(1, 5)]
    [int] $Repetitions = 3
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Benchmark = Join-Path $PSScriptRoot "benchmark_bayesian_catalog.py"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found. Run .\scripts\bootstrap.ps1 first."
}

& $Python $Benchmark --repetitions $Repetitions
if ($LASTEXITCODE -ne 0) {
    throw "Bayesian catalog benchmark failed with exit code $LASTEXITCODE"
}
