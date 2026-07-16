Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$PythonLock = Join-Path $RepoRoot "backend\requirements-py310-win.lock"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path $Python)) {
        Invoke-CheckedCommand "Python virtual environment creation" { py -3.10 -m venv .venv }
    }
    if (-not (Test-Path -LiteralPath $PythonLock)) {
        throw "Python dependency lock not found at $PythonLock"
    }

    Invoke-CheckedCommand "Python hash-locked dependency install" {
        & $Python -m pip install --require-hashes --only-binary=:all: --requirement $PythonLock
    }
    Invoke-CheckedCommand "Backend editable install" {
        & $Python -m pip install --no-deps --no-build-isolation -e ".\backend"
    }
    Invoke-CheckedCommand "Python dependency check" { & $Python -m pip check }
    Invoke-CheckedCommand "Frontend dependency install" { npm --prefix .\frontend ci }
}
finally {
    Pop-Location
}
