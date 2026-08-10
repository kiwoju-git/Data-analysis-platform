Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $RepoRoot "scripts\dev-presentation.ps1") `
    -Profile "presentation" `
    -BackendPort 8001 `
    -FrontendPort 8701
