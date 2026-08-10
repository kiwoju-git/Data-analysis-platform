param(
    [int]$FullBackendPort = 8000,
    [int]$FullFrontendPort = 8600,
    [int]$PresentationBackendPort = 8001,
    [int]$PresentationFrontendPort = 8701,
    [int]$RegressionBackendPort = 8002,
    [int]$RegressionFrontendPort = 8702,
    [string]$DiagnosticsRoot = ".\.tmp\presentation-profile-diagnostics"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
. (Join-Path $PSScriptRoot "dev_runtime_helpers.ps1")

function Wait-HttpReady {
    param([string]$Url, [int]$TimeoutSeconds = 45)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        }
        catch { Start-Sleep -Milliseconds 250 }
    }
    throw "Timed out waiting for $Url"
}

Push-Location $RepoRoot
$jobs = @()
$oldPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $RepoRoot "backend"
    foreach ($port in @(
        $FullBackendPort,
        $FullFrontendPort,
        $PresentationBackendPort,
        $PresentationFrontendPort,
        $RegressionBackendPort,
        $RegressionFrontendPort
    )) {
        if ($null -ne (Get-DevPortOwner -Port $port)) {
            throw "Presentation smoke requires free port $port."
        }
    }
    $BuildId = Get-DevRepositoryBuildId -RepoRoot $RepoRoot
    $SmokeRoot = Join-Path $RepoRoot ".tmp\presentation-profile-smoke"
    $FullWorkspace = Join-Path $SmokeRoot "full-workspace"
    $PresentationWorkspace = Join-Path $SmokeRoot "presentation-core-workspace"
    $RegressionWorkspace = Join-Path $SmokeRoot "presentation-regression-workspace"
    $ResolvedWorkspaces = @(
        [System.IO.Path]::GetFullPath($FullWorkspace),
        [System.IO.Path]::GetFullPath($PresentationWorkspace),
        [System.IO.Path]::GetFullPath($RegressionWorkspace)
    ) | Select-Object -Unique
    if ($ResolvedWorkspaces.Count -ne 3) {
        throw "Full, core preview, and regression preview workspaces must differ."
    }
    New-Item -ItemType Directory -Force -Path $FullWorkspace, $PresentationWorkspace, $RegressionWorkspace, $DiagnosticsRoot | Out-Null

    & $Python -m pytest backend/tests/unit/test_presentation_profile.py
    if ($LASTEXITCODE -ne 0) { throw "Presentation backend tests failed." }
    npm --prefix .\frontend test -- --run src/productProfile.test.ts
    if ($LASTEXITCODE -ne 0) { throw "Presentation frontend tests failed." }
    $oldFrontendProfile = $env:VITE_STATISTICAL_TWIN_PROFILE
    try {
        $env:VITE_STATISTICAL_TWIN_PROFILE = "presentation"
        npm --prefix .\frontend run build
        if ($LASTEXITCODE -ne 0) { throw "Core presentation frontend build failed." }
        $env:VITE_STATISTICAL_TWIN_PROFILE = "presentation-regression"
        npm --prefix .\frontend run build
        if ($LASTEXITCODE -ne 0) { throw "Regression presentation frontend build failed." }
    }
    finally { $env:VITE_STATISTICAL_TWIN_PROFILE = $oldFrontendProfile }

    $jobs += Start-Job -ScriptBlock {
        param($PythonPath, $Root, $Port, $Workspace, $Commit, $Cors)
        Set-Location $Root
        $env:STATISTICAL_TWIN_PROFILE = "full"
        $env:DATALAB_WORKSPACE_ROOT = $Workspace
        $env:DATALAB_GIT_COMMIT = $Commit
        $env:DATALAB_CORS_ALLOWED_ORIGINS = $Cors
        & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port
    } -ArgumentList $Python, $RepoRoot, $FullBackendPort, $FullWorkspace, $BuildId, "[`"http://127.0.0.1:$FullFrontendPort`"]"
    $jobs += Start-Job -ScriptBlock {
        param($PythonPath, $Root, $Port, $Workspace, $Commit, $Cors)
        Set-Location $Root
        $env:STATISTICAL_TWIN_PROFILE = "presentation"
        $env:DATALAB_WORKSPACE_ROOT = $Workspace
        $env:DATALAB_GIT_COMMIT = $Commit
        $env:DATALAB_CORS_ALLOWED_ORIGINS = $Cors
        & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port
    } -ArgumentList $Python, $RepoRoot, $PresentationBackendPort, $PresentationWorkspace, $BuildId, "[`"http://127.0.0.1:$PresentationFrontendPort`"]"
    $jobs += Start-Job -ScriptBlock {
        param($PythonPath, $Root, $Port, $Workspace, $Commit, $Cors)
        Set-Location $Root
        $env:STATISTICAL_TWIN_PROFILE = "presentation-regression"
        $env:DATALAB_WORKSPACE_ROOT = $Workspace
        $env:DATALAB_GIT_COMMIT = $Commit
        $env:DATALAB_CORS_ALLOWED_ORIGINS = $Cors
        & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port
    } -ArgumentList $Python, $RepoRoot, $RegressionBackendPort, $RegressionWorkspace, $BuildId, "[`"http://127.0.0.1:$RegressionFrontendPort`"]"

    Wait-HttpReady "http://127.0.0.1:$FullBackendPort/api/v1/health"
    Wait-HttpReady "http://127.0.0.1:$PresentationBackendPort/api/v1/health"
    Wait-HttpReady "http://127.0.0.1:$RegressionBackendPort/api/v1/health"

    $jobs += Start-Job -ScriptBlock {
        param($Root, $Port, $BackendPort, $Commit)
        Set-Location $Root
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        $env:VITE_GIT_COMMIT = $Commit
        $env:VITE_STATISTICAL_TWIN_PROFILE = "full"
        npm --prefix .\frontend run dev -- --host 127.0.0.1 --port $Port --strictPort
    } -ArgumentList $RepoRoot, $FullFrontendPort, $FullBackendPort, $BuildId
    $jobs += Start-Job -ScriptBlock {
        param($Root, $Port, $BackendPort, $Commit)
        Set-Location $Root
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        $env:VITE_GIT_COMMIT = $Commit
        $env:VITE_STATISTICAL_TWIN_PROFILE = "presentation"
        npm --prefix .\frontend run dev -- --host 127.0.0.1 --port $Port --strictPort
    } -ArgumentList $RepoRoot, $PresentationFrontendPort, $PresentationBackendPort, $BuildId
    $jobs += Start-Job -ScriptBlock {
        param($Root, $Port, $BackendPort, $Commit)
        Set-Location $Root
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        $env:VITE_GIT_COMMIT = $Commit
        $env:VITE_STATISTICAL_TWIN_PROFILE = "presentation-regression"
        npm --prefix .\frontend run dev -- --host 127.0.0.1 --port $Port --strictPort
    } -ArgumentList $RepoRoot, $RegressionFrontendPort, $RegressionBackendPort, $BuildId

    Wait-HttpReady "http://127.0.0.1:$FullFrontendPort"
    Wait-HttpReady "http://127.0.0.1:$PresentationFrontendPort"
    Wait-HttpReady "http://127.0.0.1:$RegressionFrontendPort"

    $catalog = Invoke-RestMethod "http://127.0.0.1:$PresentationBackendPort/api/v1/analysis-methods"
    if (($catalog.modules.module_id -join ",") -ne "exploration,hypothesis") {
        throw "Presentation backend catalog exposed an unexpected module."
    }
    $regressionCatalog = Invoke-RestMethod "http://127.0.0.1:$RegressionBackendPort/api/v1/analysis-methods"
    if (($regressionCatalog.modules.module_id -join ",") -ne "exploration,hypothesis,regression") {
        throw "Regression presentation backend catalog exposed an unexpected module."
    }
    & $Python .\scripts\presentation_profile_smoke.py `
        --full-url "http://127.0.0.1:$FullFrontendPort" `
        --core-url "http://127.0.0.1:$PresentationFrontendPort" `
        --regression-url "http://127.0.0.1:$RegressionFrontendPort" `
        --diagnostics-root $DiagnosticsRoot
    if ($LASTEXITCODE -ne 0) { throw "Concurrent browser profile smoke failed." }
    Write-Host "Presentation profile smoke passed."
    Write-Host "Full workspace: $FullWorkspace"
    Write-Host "Presentation workspace: $PresentationWorkspace"
    Write-Host "Regression presentation workspace: $RegressionWorkspace"
    Write-Host "Diagnostics: $DiagnosticsRoot"
}
catch {
    foreach ($job in $jobs) {
        Write-Host "--- Job $($job.Id) state=$($job.State) ---"
        Receive-Job -Job $job -Keep -ErrorAction SilentlyContinue | Out-Host
    }
    throw
}
finally {
    foreach ($job in $jobs) {
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
    $env:PYTHONPATH = $oldPythonPath
    Pop-Location
}
