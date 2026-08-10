Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $RepoRoot "scripts\dev-presentation.ps1") `
    -Profile "presentation-regression" `
    -BackendPort 8002 `
    -FrontendPort 8702
