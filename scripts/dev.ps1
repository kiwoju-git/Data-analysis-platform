param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

Push-Location $RepoRoot
try {
    if ($BackendOnly -and $FrontendOnly) {
        throw "Choose only one of -BackendOnly or -FrontendOnly."
    }

    if ($BackendOnly) {
        & $Python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
        exit
    }

    if ($FrontendOnly) {
        npm --prefix .\frontend run dev -- --host 127.0.0.1
        exit
    }

    $BackendJob = Start-Job -ScriptBlock {
        param($PythonPath, $Root)
        Set-Location $Root
        & $PythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
    } -ArgumentList $Python, $RepoRoot

    try {
        npm --prefix .\frontend run dev -- --host 127.0.0.1
    }
    finally {
        Stop-Job $BackendJob -ErrorAction SilentlyContinue
        Remove-Job $BackendJob -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
}
