param(
    [int]$FullBackendPort = 8010,
    [int]$FullFrontendPort = 9201,
    [int]$PresentationBackendPort = 8012,
    [int]$PresentationFrontendPort = 9202,
    [string]$DiagnosticsRoot = ".\.tmp\presentation-four-domains-diagnostics"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Node = (Get-Command node -ErrorAction Stop).Source
$ViteScript = Join-Path $RepoRoot "frontend\node_modules\vite\bin\vite.js"
. (Join-Path $PSScriptRoot "dev_runtime_helpers.ps1")

function Wait-HttpReady {
    param([string]$Url, [int]$TimeoutSeconds = 180)
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
    $SmokeRoot = Join-Path $RepoRoot ".tmp\presentation-four-domain-smoke"
    $FullDist = Join-Path $SmokeRoot "full-dist"
    $PresentationDist = Join-Path $SmokeRoot "presentation-dist"
    foreach ($path in @($FullDist, $PresentationDist)) {
        $resolved = [System.IO.Path]::GetFullPath($path)
        if (-not $resolved.StartsWith([System.IO.Path]::GetFullPath((Join-Path $RepoRoot ".tmp")))) {
            throw "Smoke build path escaped the repository temp directory: $resolved"
        }
        if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
    }
    foreach ($port in @(
        $FullBackendPort,
        $FullFrontendPort,
        $PresentationBackendPort,
        $PresentationFrontendPort
    )) {
        if ($null -ne (Get-DevPortOwner -Port $port)) {
            throw "Presentation smoke requires free port $port."
        }
    }

    & $Python -m pytest backend/tests/unit/test_presentation_profile.py
    if ($LASTEXITCODE -ne 0) { throw "Presentation backend tests failed." }
    npm --prefix .\frontend test -- --run src/productProfile.test.ts src/analysisDomains.test.tsx src/sidebarNavigationModel.test.ts
    if ($LASTEXITCODE -ne 0) { throw "Presentation frontend tests failed." }

    $BuildId = Get-DevRepositoryBuildId -RepoRoot $RepoRoot
    $oldFrontendProfile = $env:VITE_STATISTICAL_TWIN_PROFILE
    $oldFrontendApiBase = $env:VITE_API_BASE_URL
    $oldFrontendCommit = $env:VITE_GIT_COMMIT
    try {
        $env:VITE_STATISTICAL_TWIN_PROFILE = "full"
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$FullBackendPort"
        $env:VITE_GIT_COMMIT = $BuildId
        npm --prefix .\frontend run build
        if ($LASTEXITCODE -ne 0) { throw "Full frontend build failed." }
        Copy-Item -LiteralPath (Join-Path $RepoRoot "frontend\dist") -Destination $FullDist -Recurse
        $env:VITE_STATISTICAL_TWIN_PROFILE = "presentation-four-domains"
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$PresentationBackendPort"
        npm --prefix .\frontend run build
        if ($LASTEXITCODE -ne 0) { throw "Four-domain presentation build failed." }
        Copy-Item -LiteralPath (Join-Path $RepoRoot "frontend\dist") -Destination $PresentationDist -Recurse
    }
    finally {
        $env:VITE_STATISTICAL_TWIN_PROFILE = $oldFrontendProfile
        $env:VITE_API_BASE_URL = $oldFrontendApiBase
        $env:VITE_GIT_COMMIT = $oldFrontendCommit
    }

    $FullWorkspace = Join-Path $SmokeRoot "full-workspace"
    $PresentationWorkspace = Join-Path $SmokeRoot "presentation-workspace"
    if ([System.IO.Path]::GetFullPath($FullWorkspace) -eq [System.IO.Path]::GetFullPath($PresentationWorkspace)) {
        throw "Full and presentation workspaces must differ."
    }
    New-Item -ItemType Directory -Force -Path $FullWorkspace, $PresentationWorkspace, $DiagnosticsRoot | Out-Null

    $jobs += Start-Job -ScriptBlock {
        param($PythonPath, $Root, $Port, $Workspace, $Commit, $Cors, $Profile)
        Set-Location $Root
        $env:STATISTICAL_TWIN_PROFILE = $Profile
        $env:DATALAB_WORKSPACE_ROOT = $Workspace
        $env:DATALAB_GIT_COMMIT = $Commit
        $env:DATALAB_CORS_ALLOWED_ORIGINS = $Cors
        & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port
    } -ArgumentList $Python, $RepoRoot, $FullBackendPort, $FullWorkspace, $BuildId, "[`"http://127.0.0.1:$FullFrontendPort`"]", "full"
    $jobs += Start-Job -ScriptBlock {
        param($PythonPath, $Root, $Port, $Workspace, $Commit, $Cors, $Profile)
        Set-Location $Root
        $env:STATISTICAL_TWIN_PROFILE = $Profile
        $env:DATALAB_WORKSPACE_ROOT = $Workspace
        $env:DATALAB_GIT_COMMIT = $Commit
        $env:DATALAB_CORS_ALLOWED_ORIGINS = $Cors
        & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port
    } -ArgumentList $Python, $RepoRoot, $PresentationBackendPort, $PresentationWorkspace, $BuildId, "[`"http://127.0.0.1:$PresentationFrontendPort`"]", "presentation-four-domains"

    Wait-HttpReady "http://127.0.0.1:$FullBackendPort/api/v1/health"
    Wait-HttpReady "http://127.0.0.1:$PresentationBackendPort/api/v1/health"

    $jobs += Start-Job -ScriptBlock {
        param($NodePath, $VitePath, $Root, $Dist, $Port)
        Set-Location $Root
        & $NodePath $VitePath preview --host 127.0.0.1 --port $Port --strictPort --outDir $Dist
    } -ArgumentList $Node, $ViteScript, $RepoRoot, $FullDist, $FullFrontendPort
    Wait-HttpReady "http://127.0.0.1:$FullFrontendPort"

    $jobs += Start-Job -ScriptBlock {
        param($NodePath, $VitePath, $Root, $Dist, $Port)
        Set-Location $Root
        & $NodePath $VitePath preview --host 127.0.0.1 --port $Port --strictPort --outDir $Dist
    } -ArgumentList $Node, $ViteScript, $RepoRoot, $PresentationDist, $PresentationFrontendPort

    Wait-HttpReady "http://127.0.0.1:$PresentationFrontendPort"

    $catalog = Invoke-RestMethod "http://127.0.0.1:$PresentationBackendPort/api/v1/analysis-methods"
    $methods = @{}
    foreach ($method in $catalog.methods) { $methods[$method.method_id] = $method.availability }
    foreach ($methodId in @(
        "eda.descriptive",
        "hypothesis.mann_whitney",
        "categorical.chi_square_association",
        "regression.partial_least_squares"
    )) {
        if ($methods[$methodId] -ne "available") { throw "Expected available method $methodId." }
    }
    foreach ($methodId in @("eda.equal_variances", "quality.run_chart", "doe.factorial_design")) {
        if ($methods[$methodId] -ne "planned") { throw "Expected planned method $methodId." }
    }

    & $Python .\scripts\presentation_profile_smoke.py `
        --full-url "http://127.0.0.1:$FullFrontendPort" `
        --preview-url "http://127.0.0.1:$PresentationFrontendPort" `
        --diagnostics-root $DiagnosticsRoot
    if ($LASTEXITCODE -ne 0) { throw "Concurrent browser profile smoke failed." }
    Write-Host "Four-domain presentation profile smoke passed."
    Write-Host "Full workspace: $FullWorkspace"
    Write-Host "Presentation workspace: $PresentationWorkspace"
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
