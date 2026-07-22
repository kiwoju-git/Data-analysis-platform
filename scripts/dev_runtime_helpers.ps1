$script:ExpectedApiContractVersion = 2
$script:RequiredRuntimeCapabilities = @(
    "asset_management",
    "dataset_version_metadata",
    "dataset_version_deletion",
    "regression_model_metadata",
    "regression_model_deletion",
    "dedicated_predict",
    "dedicated_response_optimizer",
    "bayesian_optimization"
)

function Get-DevPortOwner {
    param([Parameter(Mandatory = $true)][int] $Port)

    $match = netstat -ano -p tcp |
        Select-String -Pattern "^\s*TCP\s+127\.0\.0\.1:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$" |
        Select-Object -First 1
    if ($null -eq $match -or $match.Line -notmatch "LISTENING\s+(\d+)\s*$") {
        return $null
    }
    $processId = [int]$Matches[1]
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    return [pscustomobject]@{
        Port = $Port
        ProcessId = $processId
        Name = if ($null -eq $process) { "unknown" } else { [string]$process.Name }
        CommandLine = if ($null -eq $process) { "unavailable" } else { [string]$process.CommandLine }
    }
}

function Format-DevPortOwner {
    param([Parameter(Mandatory = $true)] $Owner)
    return "PID $($Owner.ProcessId) ($($Owner.Name)): $($Owner.CommandLine)"
}

function Get-DevRuntimeInfo {
    param(
        [int] $BackendPort = 8000,
        [int] $TimeoutSec = 2
    )
    try {
        return Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/runtime-info" `
            -Headers @{ Accept = "application/json"; "Cache-Control" = "no-cache" } `
            -TimeoutSec $TimeoutSec
    }
    catch {
        return $null
    }
}

function Test-DevRuntimeCompatibility {
    param(
        [Parameter(Mandatory = $true)] $RuntimeInfo,
        [Parameter(Mandatory = $true)][string] $ExpectedCommit,
        [switch] $RequireExactCommit
    )

    if ($RuntimeInfo.service -ne "datalab-studio-api") { return $false }
    if ([int]$RuntimeInfo.api_contract_version -ne $script:ExpectedApiContractVersion) {
        return $false
    }
    if ([int]$RuntimeInfo.metadata_schema_version -lt 15) { return $false }
    foreach ($capability in $script:RequiredRuntimeCapabilities) {
        $property = $RuntimeInfo.capabilities.PSObject.Properties[$capability]
        if ($null -eq $property -or $property.Value -ne $true) { return $false }
    }
    if ($RequireExactCommit) {
        if ([string]$RuntimeInfo.build_commit -eq "unknown") { return $false }
        if ([string]$RuntimeInfo.build_commit -ne $ExpectedCommit) { return $false }
    }
    return $true
}

function Get-DevRepositoryCommit {
    param([Parameter(Mandatory = $true)][string] $RepoRoot)
    $commit = (& git -C $RepoRoot rev-parse HEAD 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($commit)) {
        return "unknown"
    }
    return $commit.Trim()
}
