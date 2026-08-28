param(
    [ValidateSet("presentation", "presentation-regression", "presentation-four-domains")]
    [string]$Profile = "presentation-four-domains",
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0,
    [string]$WorkspaceRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$IsRegressionProfile = $Profile -eq "presentation-regression"
$IsFourDomainProfile = $Profile -eq "presentation-four-domains"
if ($BackendPort -eq 0) {
    $BackendPort = if ($IsFourDomainProfile) { 8002 } elseif ($IsRegressionProfile) { 8002 } else { 8001 }
}
if ($FrontendPort -eq 0) {
    $FrontendPort = if ($IsFourDomainProfile) { 8602 } elseif ($IsRegressionProfile) { 8702 } else { 8701 }
}
if ($WorkspaceRoot -eq "") {
    $LocalRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:TEMP }
    $WorkspaceName = if ($IsFourDomainProfile) {
        "StatisticalTwinPresentationFourDomains"
    }
    elseif ($IsRegressionProfile) {
        "StatisticalTwinPresentationRegression"
    }
    else {
        "StatisticalTwinPresentationCore"
    }
    $WorkspaceRoot = Join-Path $LocalRoot $WorkspaceName
}

$previousProfile = $env:STATISTICAL_TWIN_PROFILE
$previousFrontendProfile = $env:VITE_STATISTICAL_TWIN_PROFILE
$previousWorkspace = $env:DATALAB_WORKSPACE_ROOT
$previousCors = $env:DATALAB_CORS_ALLOWED_ORIGINS
try {
    $env:STATISTICAL_TWIN_PROFILE = $Profile
    $env:VITE_STATISTICAL_TWIN_PROFILE = $Profile
    $env:DATALAB_WORKSPACE_ROOT = $WorkspaceRoot
    $env:DATALAB_CORS_ALLOWED_ORIGINS = "[`"http://127.0.0.1:$FrontendPort`",`"http://localhost:$FrontendPort`"]"
    Write-Host "Presentation profile: $Profile"
    Write-Host "Presentation ports: backend 127.0.0.1:$BackendPort, frontend 127.0.0.1:$FrontendPort"
    Write-Host "Presentation workspace: $WorkspaceRoot"
    & (Join-Path $PSScriptRoot "dev.ps1") -BackendPort $BackendPort -FrontendPort $FrontendPort
}
finally {
    $env:STATISTICAL_TWIN_PROFILE = $previousProfile
    $env:VITE_STATISTICAL_TWIN_PROFILE = $previousFrontendProfile
    $env:DATALAB_WORKSPACE_ROOT = $previousWorkspace
    $env:DATALAB_CORS_ALLOWED_ORIGINS = $previousCors
}
