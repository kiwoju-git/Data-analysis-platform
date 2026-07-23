$script:ExpectedApiContractVersion = 3
$script:RequiredRuntimeCapabilities = @(
    "asset_management",
    "dataset_version_metadata",
    "dataset_version_deletion",
    "dataset_version_archiving",
    "dataset_version_cascade_deletion",
    "dataset_version_preserve_unverified_cleanup",
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
        [Parameter(Mandatory = $true)][Alias("ExpectedCommit")][string] $ExpectedBuildId,
        [switch] $RequireExactCommit
    )

    if ($RuntimeInfo.service -ne "datalab-studio-api") { return $false }
    if ([int]$RuntimeInfo.api_contract_version -ne $script:ExpectedApiContractVersion) {
        return $false
    }
    if ([int]$RuntimeInfo.metadata_schema_version -lt 16) { return $false }
    foreach ($capability in $script:RequiredRuntimeCapabilities) {
        $property = $RuntimeInfo.capabilities.PSObject.Properties[$capability]
        if ($null -eq $property -or $property.Value -ne $true) { return $false }
    }
    if ($RequireExactCommit) {
        if ([string]$RuntimeInfo.build_commit -eq "unknown") { return $false }
        if ([string]$RuntimeInfo.build_commit -ne $ExpectedBuildId) { return $false }
    }
    return $true
}

function Get-DevSourceFingerprintFiles {
    param([Parameter(Mandatory = $true)][string] $RepoRoot)

    $resolvedRoot = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $rootPrefix = $resolvedRoot + [System.IO.Path]::DirectorySeparatorChar
    $relativePaths = New-Object "System.Collections.Generic.HashSet[string]" (
        [System.StringComparer]::Ordinal
    )

    foreach ($relativeRoot in @("backend/app", "frontend/src", "scripts")) {
        $sourceRoot = Join-Path $resolvedRoot ($relativeRoot -replace "/", "\")
        if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
            continue
        }
        foreach ($file in Get-ChildItem -LiteralPath $sourceRoot -File -Recurse -Force) {
            $fullPath = [System.IO.Path]::GetFullPath($file.FullName)
            if (-not $fullPath.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
            $relativePath = $fullPath.Substring($rootPrefix.Length).Replace("\", "/")
            if (
                $relativePath -match "(^|/)(__pycache__|node_modules|dist|logs?|\.tmp|test-results|playwright-report)(/|$)" -or
                $relativePath -match "(^|/)\.(pytest_cache|mypy_cache|ruff_cache)(/|$)" -or
                $relativePath -match "(~|\.bak|\.swp|\.tmp|\.log)$"
            ) {
                continue
            }
            [void]$relativePaths.Add($relativePath)
        }
    }

    $explicitRelativePaths = @(
        "backend/pyproject.toml",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/index.html",
        ".gitattributes"
    )
    foreach ($relativePath in $explicitRelativePaths) {
        $fullPath = Join-Path $resolvedRoot ($relativePath -replace "/", "\")
        if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
            [void]$relativePaths.Add($relativePath)
        }
    }

    foreach ($pattern in @(
        "backend/*.lock",
        "backend/requirements*.txt",
        "frontend/tsconfig*.json",
        "frontend/vite.config.*"
    )) {
        $parent = Split-Path -Parent $pattern
        $leaf = Split-Path -Leaf $pattern
        $directory = Join-Path $resolvedRoot ($parent -replace "/", "\")
        if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
            continue
        }
        foreach ($file in Get-ChildItem -LiteralPath $directory -File -Filter $leaf) {
            $fullPath = [System.IO.Path]::GetFullPath($file.FullName)
            $relativePath = $fullPath.Substring($rootPrefix.Length).Replace("\", "/")
            [void]$relativePaths.Add($relativePath)
        }
    }

    $sortedPaths = [string[]]$relativePaths
    [System.Array]::Sort($sortedPaths, [System.StringComparer]::Ordinal)
    return $sortedPaths
}

function Get-DevArchiveSourceFingerprint {
    param([Parameter(Mandatory = $true)][string] $RepoRoot)

    $resolvedRoot = [System.IO.Path]::GetFullPath($RepoRoot)
    $sourcePaths = @(Get-DevSourceFingerprintFiles -RepoRoot $resolvedRoot)
    if ($sourcePaths.Count -eq 0) {
        throw "No runtime source files were found for the archive fingerprint."
    }

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $aggregateHash = [System.Security.Cryptography.SHA256]::Create()
    try {
        foreach ($relativePath in $sourcePaths) {
            $fullPath = Join-Path $resolvedRoot ($relativePath -replace "/", "\")
            $fileHash = (Get-FileHash -LiteralPath $fullPath -Algorithm SHA256).Hash.ToLowerInvariant()
            $entryBytes = $utf8.GetBytes($relativePath + [char]0 + $fileHash + "`n")
            [void]$aggregateHash.TransformBlock(
                $entryBytes,
                0,
                $entryBytes.Length,
                $entryBytes,
                0
            )
        }
        [void]$aggregateHash.TransformFinalBlock((New-Object byte[] 0), 0, 0)
        $fingerprint = (
            [System.BitConverter]::ToString($aggregateHash.Hash).Replace("-", "").ToLowerInvariant()
        )
        return "archive-sha256-$fingerprint"
    }
    finally {
        $aggregateHash.Dispose()
    }
}

function Get-DevRepositoryBuildId {
    param([Parameter(Mandatory = $true)][string] $RepoRoot)

    $gitMetadata = Join-Path $RepoRoot ".git"
    $gitCommand = $null
    if (Test-Path -LiteralPath $gitMetadata) {
        $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    }

    if ($null -ne $gitCommand) {
        $previousErrorActionPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = "Continue"
            $commitOutput = & $gitCommand.Source -C $RepoRoot rev-parse --verify HEAD 2>$null
            $gitExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }
        $commit = [string]($commitOutput | Select-Object -First 1)
        if ($gitExitCode -eq 0 -and $commit.Trim() -match "^[0-9a-fA-F]{40}$") {
            return $commit.Trim().ToLowerInvariant()
        }
    }

    return Get-DevArchiveSourceFingerprint -RepoRoot $RepoRoot
}

function Get-DevRepositoryCommit {
    param([Parameter(Mandatory = $true)][string] $RepoRoot)
    return Get-DevRepositoryBuildId -RepoRoot $RepoRoot
}

function Format-DevSourceIdentity {
    param([Parameter(Mandatory = $true)][string] $BuildId)

    if ($BuildId -match "^archive-sha256-([0-9a-f]{64})$") {
        return "archive fingerprint $($Matches[1].Substring(0, 12))"
    }
    if ($BuildId -match "^[0-9a-f]{40}$") {
        return "git $($BuildId.Substring(0, 12))"
    }
    return "source identity unavailable"
}
