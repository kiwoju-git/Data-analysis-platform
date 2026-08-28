param(
    [ValidateSet("presentation", "presentation-regression", "presentation-four-domains")]
    [string]$Profile = "presentation-four-domains",
    [int]$BackendPort = 0,
    [int]$FrontendPort = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$IsRegressionProfile = $Profile -eq "presentation-regression"
$IsFourDomainProfile = $Profile -eq "presentation-four-domains"
if ($BackendPort -eq 0) { $BackendPort = if ($IsFourDomainProfile) { 8002 } elseif ($IsRegressionProfile) { 8002 } else { 8001 } }
if ($FrontendPort -eq 0) { $FrontendPort = if ($IsFourDomainProfile) { 8602 } elseif ($IsRegressionProfile) { 8702 } else { 8701 } }
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
Write-Host "Expected profile: $Profile"
Write-Host "Expected workspace: $WorkspaceRoot"
Write-Host "Expected public scope: Home, Datasets, Analysis; domains 1-4 available, domains 5-8 planned"
& (Join-Path $PSScriptRoot "diagnose-dev.ps1") -BackendPort $BackendPort -FrontendPort $FrontendPort

$Catalog = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/analysis-methods" `
    -Headers @{ Accept = "application/json" } `
    -TimeoutSec 5
$ExpectedModules = if ($IsFourDomainProfile) {
    "exploration,hypothesis,categorical,regression,quality,doe"
}
elseif ($IsRegressionProfile) {
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
