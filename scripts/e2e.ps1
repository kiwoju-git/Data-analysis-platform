param(
    [int]$BackendPort = 8011,
    [int]$FrontendPort = 5199,
    [string]$WorkspaceRoot = "",
    [string]$DiagnosticsRoot = "",
    [switch]$InstallBrowsers,
    [switch]$KeepWorkspace
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    if (-not (Test-Path $Python)) {
        throw "Python virtual environment not found. Run .\scripts\bootstrap.ps1 first."
    }

    & $Python -c "import playwright" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Playwright is not installed. Run .\scripts\bootstrap.ps1 after updating dependencies."
    }

    if ($InstallBrowsers) {
        & $Python -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            throw "Playwright Chromium install failed with exit code $LASTEXITCODE"
        }
    }

    $Args = @(
        ".\tests\e2e\critical_path.py",
        "--backend-port",
        "$BackendPort",
        "--frontend-port",
        "$FrontendPort"
    )
    if ($WorkspaceRoot -ne "") {
        $Args += @("--workspace-root", "$WorkspaceRoot")
    }
    if ($DiagnosticsRoot -ne "") {
        $Args += @("--diagnostics-root", "$DiagnosticsRoot")
    }
    if ($KeepWorkspace) {
        $Args += "--keep-workspace"
    }

    & $Python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "E2E critical path failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
