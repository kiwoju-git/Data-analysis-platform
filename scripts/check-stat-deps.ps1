param(
    [string] $OutputPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$SmokeScript = Join-Path $PSScriptRoot "stat_dependency_smoke.py"

Push-Location $RepoRoot
try {
    if (-not (Test-Path $Python)) {
        throw "Python virtual environment not found at $Python. Run .\scripts\bootstrap.ps1 first."
    }

    $SmokeOutput = & $Python $SmokeScript
    $SmokeExitCode = $LASTEXITCODE
    $SmokeOutput | Write-Output
    if ($OutputPath -ne "") {
        $ResolvedOutputPath = $OutputPath
        if (-not [System.IO.Path]::IsPathRooted($ResolvedOutputPath)) {
            $ResolvedOutputPath = Join-Path $RepoRoot $ResolvedOutputPath
        }
        $OutputDirectory = Split-Path -Parent $ResolvedOutputPath
        if ($OutputDirectory -ne "" -and -not (Test-Path $OutputDirectory)) {
            New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
        }
        $SmokeOutput | Set-Content -Path $ResolvedOutputPath -Encoding UTF8
    }
    if ($SmokeExitCode -ne 0) {
        throw "stat dependency smoke check failed with exit code $SmokeExitCode"
    }
}
finally {
    Pop-Location
}
