param(
    [string] $OutputRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$InputPath = Join-Path $RepoRoot "backend\requirements-py310-win.in"
$LockPath = Join-Path $RepoRoot "backend\requirements-py310-win.lock"
$Generator = Join-Path $PSScriptRoot "generate_python_lock.py"
$Validator = Join-Path $PSScriptRoot "validate_python_lock.py"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found. Run .\scripts\bootstrap.ps1 first."
}
if ($OutputRoot -eq "") {
    $OutputRoot = Join-Path $env:TEMP "datalab-python-lock\$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
$RepoFullPath = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
if ($OutputRoot.StartsWith($RepoFullPath + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Python lock wheelhouse must stay outside the repository."
}
if (Test-Path -LiteralPath $OutputRoot) {
    throw "Python lock output already exists: $OutputRoot"
}
$Wheelhouse = Join-Path $OutputRoot "wheelhouse"
New-Item -ItemType Directory -Path $Wheelhouse -Force | Out-Null

Push-Location $RepoRoot
try {
    & $Python -m pip download --dest $Wheelhouse --only-binary=:all: --platform win_amd64 --implementation cp --python-version 310 --abi cp310 --requirement $InputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Python lock wheel download failed with exit code $LASTEXITCODE"
    }
    & $Python $Generator $Wheelhouse $LockPath
    if ($LASTEXITCODE -ne 0) {
        throw "Python lock generation failed with exit code $LASTEXITCODE"
    }
    & $Python $Validator $LockPath
    if ($LASTEXITCODE -ne 0) {
        throw "Python lock validation failed with exit code $LASTEXITCODE"
    }
    $WheelCount = (Get-ChildItem -LiteralPath $Wheelhouse -Filter "*.whl" -File).Count
    Write-Output "Generated validated Python lock from $WheelCount wheels in $Wheelhouse."
}
finally {
    Pop-Location
}
