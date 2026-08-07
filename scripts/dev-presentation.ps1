param(
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 8601,
    [string]$WorkspaceRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if ($WorkspaceRoot -eq "") {
    $LocalRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:TEMP }
    $WorkspaceRoot = Join-Path $LocalRoot "StatisticalTwinPresentation"
}

$previousProfile = $env:STATISTICAL_TWIN_PROFILE
$previousFrontendProfile = $env:VITE_STATISTICAL_TWIN_PROFILE
$previousWorkspace = $env:DATALAB_WORKSPACE_ROOT
$previousCors = $env:DATALAB_CORS_ALLOWED_ORIGINS
try {
    $env:STATISTICAL_TWIN_PROFILE = "presentation"
    $env:VITE_STATISTICAL_TWIN_PROFILE = "presentation"
    $env:DATALAB_WORKSPACE_ROOT = $WorkspaceRoot
    $env:DATALAB_CORS_ALLOWED_ORIGINS = "[`"http://127.0.0.1:$FrontendPort`",`"http://localhost:$FrontendPort`"]"
    Write-Host "Presentation profile: backend 127.0.0.1:$BackendPort, frontend 127.0.0.1:$FrontendPort"
    Write-Host "Presentation workspace: $WorkspaceRoot"
    & (Join-Path $PSScriptRoot "dev.ps1") -BackendPort $BackendPort -FrontendPort $FrontendPort
}
finally {
    $env:STATISTICAL_TWIN_PROFILE = $previousProfile
    $env:VITE_STATISTICAL_TWIN_PROFILE = $previousFrontendProfile
    $env:DATALAB_WORKSPACE_ROOT = $previousWorkspace
    $env:DATALAB_CORS_ALLOWED_ORIGINS = $previousCors
}
