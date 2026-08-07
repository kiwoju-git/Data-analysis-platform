param(
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 8601
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$LocalRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:TEMP }
$WorkspaceRoot = Join-Path $LocalRoot "StatisticalTwinPresentation"
Write-Host "Expected profile: presentation"
Write-Host "Expected workspace: $WorkspaceRoot"
Write-Host "Expected public scope: Home, Dataset, EDA, Hypothesis"
& (Join-Path $PSScriptRoot "diagnose-dev.ps1") -BackendPort $BackendPort -FrontendPort $FrontendPort
