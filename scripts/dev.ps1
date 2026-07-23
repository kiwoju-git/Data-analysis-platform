param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$ReuseCompatibleBackend,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$StartupTimeoutSeconds = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$FrontendNodeModules = Join-Path $RepoRoot "frontend\node_modules"
. (Join-Path $PSScriptRoot "dev_runtime_helpers.ps1")

Push-Location $RepoRoot
try {
    if ($BackendOnly -and $FrontendOnly) {
        throw "Choose only one of -BackendOnly or -FrontendOnly."
    }
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Python virtual environment not found. Run .\scripts\bootstrap.ps1 first."
    }
    if (-not $BackendOnly) {
        if ($null -eq (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "npm was not found. Install the supported Node version and run bootstrap.ps1."
        }
        if (-not (Test-Path -LiteralPath $FrontendNodeModules)) {
            throw "Frontend dependencies not found. Run .\scripts\bootstrap.ps1 first."
        }
    }

    $RepositoryBuildId = Get-DevRepositoryBuildId -RepoRoot $RepoRoot
    Write-Host "Source identity: $(Format-DevSourceIdentity -BuildId $RepositoryBuildId)"
    $BackendOwner = Get-DevPortOwner -Port $BackendPort
    $UsingExistingBackend = $false

    if ($null -ne $BackendOwner) {
        $RuntimeInfo = Get-DevRuntimeInfo -BackendPort $BackendPort
        $Compatible = $null -ne $RuntimeInfo -and (
            Test-DevRuntimeCompatibility `
                -RuntimeInfo $RuntimeInfo `
                -ExpectedBuildId $RepositoryBuildId `
                -RequireExactCommit
        )
        if (($ReuseCompatibleBackend -or $FrontendOnly) -and $Compatible) {
            Write-Host "Reusing compatible backend on port $BackendPort."
            Write-Host (Format-DevPortOwner -Owner $BackendOwner)
            $UsingExistingBackend = $true
        }
        else {
            $runtimeSummary = if ($null -eq $RuntimeInfo) {
                "runtime-info unavailable"
            }
            else {
                "contract=$($RuntimeInfo.api_contract_version), schema=$($RuntimeInfo.metadata_schema_version), build=$($RuntimeInfo.build_commit)"
            }
            throw "Backend port $BackendPort is already in use by $(Format-DevPortOwner -Owner $BackendOwner). $runtimeSummary. Stop the previous DataLab process yourself, or use -ReuseCompatibleBackend only for an exact compatible build."
        }
    }
    elseif ($FrontendOnly) {
        throw "No backend is listening on port $BackendPort. Start the matching backend first or run dev.ps1 without -FrontendOnly."
    }

    if (-not $BackendOnly) {
        $FrontendOwner = Get-DevPortOwner -Port $FrontendPort
        if ($null -ne $FrontendOwner) {
            throw "Frontend port $FrontendPort is already in use by $(Format-DevPortOwner -Owner $FrontendOwner). Open that process intentionally or stop it yourself; DataLab will not move to another port automatically."
        }
    }

    if ($BackendOnly) {
        if ($UsingExistingBackend) {
            Write-Host "Compatible backend is already ready at http://127.0.0.1:$BackendPort"
            exit
        }
        $env:DATALAB_GIT_COMMIT = $RepositoryBuildId
        & $Python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $BackendPort
        exit
    }

    if ($FrontendOnly) {
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        $env:VITE_GIT_COMMIT = $RepositoryBuildId
        npm --prefix .\frontend run dev -- --port $FrontendPort --strictPort
        exit
    }

    $BackendJob = $null
    $previousApiBase = $env:VITE_API_BASE_URL
    $previousFrontendCommit = $env:VITE_GIT_COMMIT
    try {
        if (-not $UsingExistingBackend) {
            $BackendJob = Start-Job -ScriptBlock {
            param($PythonPath, $Root, $Port, $Commit)
            Set-Location $Root
            $env:DATALAB_GIT_COMMIT = $Commit
            & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $Port
            } -ArgumentList $Python, $RepoRoot, $BackendPort, $RepositoryBuildId

            $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
            $RuntimeInfo = $null
            while ([DateTime]::UtcNow -lt $deadline) {
                $BackendJob = Get-Job -Id $BackendJob.Id
                if ($BackendJob.State -in @("Completed", "Failed", "Stopped")) {
                    $backendOutput = Receive-Job -Job $BackendJob -Keep 2>&1 | Out-String
                    throw "Backend exited before becoming ready. State=$($BackendJob.State)`n$backendOutput"
                }
                $RuntimeInfo = Get-DevRuntimeInfo -BackendPort $BackendPort
                if ($null -ne $RuntimeInfo) { break }
                Start-Sleep -Milliseconds 250
            }
            if ($null -eq $RuntimeInfo) {
                $backendOutput = Receive-Job -Job $BackendJob -Keep 2>&1 | Out-String
                throw "Backend did not become ready within $StartupTimeoutSeconds seconds.`n$backendOutput"
            }
            if (-not (Test-DevRuntimeCompatibility -RuntimeInfo $RuntimeInfo -ExpectedBuildId $RepositoryBuildId -RequireExactCommit)) {
                throw "Started backend returned an incompatible runtime contract. contract=$($RuntimeInfo.api_contract_version), schema=$($RuntimeInfo.metadata_schema_version), build=$($RuntimeInfo.build_commit)"
            }
            Write-Host "Backend ready: http://127.0.0.1:$BackendPort (contract $($RuntimeInfo.api_contract_version), schema $($RuntimeInfo.metadata_schema_version), build $($RuntimeInfo.build_commit))"
        }

        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        $env:VITE_GIT_COMMIT = $RepositoryBuildId
        Write-Host "Frontend starting: http://127.0.0.1:$FrontendPort"
        npm --prefix .\frontend run dev -- --port $FrontendPort --strictPort
    }
    finally {
        $env:VITE_API_BASE_URL = $previousApiBase
        $env:VITE_GIT_COMMIT = $previousFrontendCommit
        if ($null -ne $BackendJob) {
            Stop-Job $BackendJob -ErrorAction SilentlyContinue
            Remove-Job $BackendJob -ErrorAction SilentlyContinue
        }
    }
}
finally {
    Pop-Location
}
