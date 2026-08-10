Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot
try {
    & (Join-Path $PSScriptRoot "bootstrap.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "Presentation bootstrap failed with exit code $LASTEXITCODE"
    }
    if (Test-Path -LiteralPath (Join-Path $RepoRoot "START_HERE.ps1")) {
        Write-Host "Presentation dependencies are ready. Run .\START_HERE.ps1."
    }
    else {
        Write-Host "Presentation dependencies are ready. Run a profile-specific presentation launcher."
    }
}
finally {
    Pop-Location
}
