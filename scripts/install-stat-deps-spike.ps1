param(
    [string] $NumPyVersion = "2.2.6",
    [string] $SciPyVersion = "1.15.3",
    [string] $OutputPath = "logs\stat-dependency-smoke.json",
    [switch] $SkipSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$VersionPattern = '^\d+\.\d+\.\d+([A-Za-z0-9\.\-]+)?$'
if ($NumPyVersion -notmatch $VersionPattern) {
    throw "Invalid NumPy version: $NumPyVersion"
}
if ($SciPyVersion -notmatch $VersionPattern) {
    throw "Invalid SciPy version: $SciPyVersion"
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$SmokeScript = Join-Path $PSScriptRoot "check-stat-deps.ps1"

Push-Location $RepoRoot
try {
    if (-not (Test-Path $Python)) {
        throw "Python virtual environment not found at $Python. Run .\scripts\bootstrap.ps1 first."
    }

    & $Python -m pip install --only-binary=:all: "numpy==$NumPyVersion" "scipy==$SciPyVersion"
    if ($LASTEXITCODE -ne 0) {
        throw "stat dependency spike install failed with exit code $LASTEXITCODE"
    }

    if (-not $SkipSmoke) {
        powershell -ExecutionPolicy Bypass -File $SmokeScript -OutputPath $OutputPath
        if ($LASTEXITCODE -ne 0) {
            throw "stat dependency smoke check failed with exit code $LASTEXITCODE"
        }
    }
}
finally {
    Pop-Location
}
