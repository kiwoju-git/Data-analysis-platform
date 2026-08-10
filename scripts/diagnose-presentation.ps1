param(
    [ValidateSet("presentation", "presentation-regression")]
    [string]$Profile = "presentation",
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$IsRegressionProfile = $Profile -eq "presentation-regression"
if ($BackendPort -eq 0) { $BackendPort = if ($IsRegressionProfile) { 8002 } else { 8001 } }
if ($FrontendPort -eq 0) { $FrontendPort = if ($IsRegressionProfile) { 8702 } else { 8701 } }
$LocalRoot = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:TEMP }
$WorkspaceName = if ($IsRegressionProfile) {
    "StatisticalTwinPresentationRegression"
}
else {
    "StatisticalTwinPresentationCore"
}
$WorkspaceRoot = Join-Path $LocalRoot $WorkspaceName
Write-Host "Expected profile: $Profile"
Write-Host "Expected workspace: $WorkspaceRoot"
Write-Host "Expected public scope: Home, Dataset, EDA, Hypothesis$(if ($IsRegressionProfile) { ', Regression' } else { '' })"
& (Join-Path $PSScriptRoot "diagnose-dev.ps1") -BackendPort $BackendPort -FrontendPort $FrontendPort

$Catalog = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/analysis-methods" `
    -Headers @{ Accept = "application/json" } `
    -TimeoutSec 5
$ExpectedModules = if ($IsRegressionProfile) {
    "exploration,hypothesis,regression"
}
else {
    "exploration,hypothesis"
}
$ActualModules = $Catalog.modules.module_id -join ","
if ($ActualModules -ne $ExpectedModules) {
    throw "Presentation profile mismatch. Expected modules $ExpectedModules but received $ActualModules."
}
Write-Host "Presentation module catalog verified: $ActualModules"
