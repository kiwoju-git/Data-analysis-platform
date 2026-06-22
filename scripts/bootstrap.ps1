Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    if (-not (Test-Path $Python)) {
        py -3.10 -m venv .venv
    }

    & $Python -m pip install --upgrade pip
    & $Python -m pip install -e ".\backend[dev]"
    npm --prefix .\frontend ci
}
finally {
    Pop-Location
}
