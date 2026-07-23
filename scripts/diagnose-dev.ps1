param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "dev_runtime_helpers.ps1")

$buildId = Get-DevRepositoryBuildId -RepoRoot $RepoRoot
Write-Host "Repository: $RepoRoot"
Write-Host "Source identity: $(Format-DevSourceIdentity -BuildId $buildId)"

$python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
Write-Host "Python: $python"
if (Test-Path -LiteralPath $python) { & $python --version }
Write-Host "Node: $(& node --version 2>$null)"

foreach ($port in @($BackendPort, $FrontendPort)) {
    $owner = Get-DevPortOwner -Port $port
    if ($null -eq $owner) {
        Write-Host "Port ${port}: available"
    }
    else {
        Write-Host "Port ${port}: $(Format-DevPortOwner -Owner $owner)"
    }
}

$runtime = Get-DevRuntimeInfo -BackendPort $BackendPort
if ($null -eq $runtime) {
    Write-Host "Runtime info: unavailable (the backend may be old or stopped)"
}
else {
    Write-Host "Runtime info: contract=$($runtime.api_contract_version), schema=$($runtime.metadata_schema_version), build=$($runtime.build_commit)"
    Write-Host "Runtime compatible with this source: $(Test-DevRuntimeCompatibility -RuntimeInfo $runtime -ExpectedBuildId $buildId -RequireExactCommit)"
}

try {
    $openapi = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/openapi.json" -TimeoutSec 3
    $paths = $openapi.paths.PSObject.Properties.Name
    foreach ($path in @(
        "/api/v1/runtime-info",
        "/api/v1/dataset-versions/{version_id}/metadata",
        "/api/v1/dataset-versions/{version_id}/deletion-preflight",
        "/api/v1/regression-models/{model_id}/metadata",
        "/api/v1/regression-models/{model_id}/deletion-preflight"
    )) {
        Write-Host "OpenAPI ${path}: $($paths -contains $path)"
    }
    $catalog = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/analysis-methods" -TimeoutSec 3
    $catalog.methods |
        Where-Object { $_.method_id -in @("regression.predict", "regression.response_optimizer", "doe.bayesian_optimization") } |
        Select-Object method_id, availability, execution_mode |
        Format-Table -AutoSize
}
catch {
    Write-Host "OpenAPI/catalog diagnostics unavailable: $($_.Exception.Message)"
}
