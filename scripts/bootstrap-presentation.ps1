Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot
try {
    & (Join-Path $PSScriptRoot "bootstrap.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Presentation bootstrap failed with exit code $LASTEXITCODE"
    }
    Write-Host "Presentation dependencies are ready. Run .\scripts\dev-presentation.ps1."
}
finally {
    Pop-Location
}
