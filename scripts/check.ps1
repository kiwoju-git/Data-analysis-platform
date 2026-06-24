Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Push-Location $RepoRoot
try {
    Invoke-CheckedCommand "backend ruff check" { & $Python -m ruff check .\backend }
    Invoke-CheckedCommand "backend ruff format check" { & $Python -m ruff format --check .\backend }
    Invoke-CheckedCommand "backend mypy" { & $Python -m mypy .\backend\app }
    Invoke-CheckedCommand "backend pytest" { & $Python -m pytest .\backend\tests }
    Invoke-CheckedCommand "frontend lint" { npm --prefix .\frontend run lint }
    Invoke-CheckedCommand "frontend typecheck" { npm --prefix .\frontend run typecheck }
    Invoke-CheckedCommand "frontend test" { npm --prefix .\frontend run test -- --run }
    Invoke-CheckedCommand "frontend build" { npm --prefix .\frontend run build }
}
finally {
    Pop-Location
}
