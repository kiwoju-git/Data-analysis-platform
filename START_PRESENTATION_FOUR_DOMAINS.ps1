param(
    [int]$BackendPort = 8002,
    [int]$FrontendPort = 8602
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $RepoRoot "scripts\dev-presentation.ps1") `
    -Profile "presentation-four-domains" `
    -BackendPort $BackendPort `
    -FrontendPort $FrontendPort
