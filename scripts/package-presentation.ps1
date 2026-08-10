param(
    [ValidateSet("presentation", "presentation-regression")]
    [string]$Profile = "presentation",
    [string]$OutputDirectory = ".\.tmp\releases"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceCommit = (Get-Content -LiteralPath (Join-Path $RepoRoot "SOURCE_COMMIT.txt") -Raw).Trim()
$ShortCommit = $SourceCommit.Substring(0, 8)
$DateStamp = Get-Date -Format "yyyyMMdd"
$IsRegressionProfile = $Profile -eq "presentation-regression"
$ProfileSlug = if ($IsRegressionProfile) { "regression" } else { "core" }
$ReadmeTemplate = if ($IsRegressionProfile) {
    "PRESENTATION_README_REGRESSION.md"
}
else {
    "PRESENTATION_README_CORE.md"
}
$BackendPort = if ($IsRegressionProfile) { 8002 } else { 8001 }
$FrontendPort = if ($IsRegressionProfile) { 8702 } else { 8701 }
$OutputRoot = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $OutputDirectory))
$StagingRoot = Join-Path $OutputRoot "presentation-$ProfileSlug-staging-$ShortCommit"
$ZipPath = Join-Path $OutputRoot "statistical-twin-presentation-$ProfileSlug-$DateStamp-$ShortCommit.zip"

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
if (Test-Path -LiteralPath $StagingRoot) { Remove-Item -LiteralPath $StagingRoot -Recurse -Force }
if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
New-Item -ItemType Directory -Force -Path $StagingRoot | Out-Null

Push-Location $RepoRoot
try {
    $trackedFiles = @(git ls-files)
    if ($LASTEXITCODE -ne 0 -or $trackedFiles.Count -eq 0) {
        throw "Unable to enumerate tracked release files."
    }
    foreach ($relativePath in $trackedFiles) {
        $source = Join-Path $RepoRoot $relativePath
        $target = Join-Path $StagingRoot $relativePath
        $targetParent = Split-Path -Parent $target
        New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
        Copy-Item -LiteralPath $source -Destination $target
    }

    Copy-Item -LiteralPath (Join-Path $StagingRoot $ReadmeTemplate) `
        -Destination (Join-Path $StagingRoot "README.md") -Force
    foreach ($path in @(
        "PRESENTATION_README_CORE.md",
        "PRESENTATION_README_REGRESSION.md",
        "START_PRESENTATION.ps1",
        "START_PRESENTATION_REGRESSION.ps1"
    )) {
        $stagedPath = Join-Path $StagingRoot $path
        if (Test-Path -LiteralPath $stagedPath) { Remove-Item -LiteralPath $stagedPath -Force }
    }
    $launcher = @"
Set-StrictMode -Version Latest
`$ErrorActionPreference = "Stop"
`$RepoRoot = Split-Path -Parent `$MyInvocation.MyCommand.Path
& (Join-Path `$RepoRoot "scripts\dev-presentation.ps1") ``
    -Profile "$Profile" ``
    -BackendPort $BackendPort ``
    -FrontendPort $FrontendPort
"@
    [System.IO.File]::WriteAllText(
        (Join-Path $StagingRoot "START_HERE.ps1"),
        $launcher,
        [System.Text.UTF8Encoding]::new($false)
    )
    [System.IO.File]::WriteAllText(
        (Join-Path $StagingRoot "RELEASE_PROFILE.txt"),
        "$Profile`n",
        [System.Text.UTF8Encoding]::new($false)
    )
    $ReleaseCommit = (git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve the release commit." }
    [System.IO.File]::WriteAllText(
        (Join-Path $StagingRoot "RELEASE_COMMIT.txt"),
        "$ReleaseCommit`n",
        [System.Text.UTF8Encoding]::new($false)
    )

    $checksumLines = Get-ChildItem -LiteralPath $StagingRoot -Recurse -File |
        Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($StagingRoot.Length + 1).Replace("\", "/")
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$hash  $relative"
        }
    [System.IO.File]::WriteAllLines(
        (Join-Path $StagingRoot "SHA256SUMS.txt"),
        $checksumLines,
        [System.Text.UTF8Encoding]::new($false)
    )
    Compress-Archive -Path (Join-Path $StagingRoot "*") -DestinationPath $ZipPath -CompressionLevel Optimal
    $zipHash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "Release asset: $ZipPath"
    Write-Host "Profile: $Profile"
    Write-Host "Ports: backend $BackendPort, frontend $FrontendPort"
    Write-Host "SHA-256: $zipHash"
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $StagingRoot) {
        Remove-Item -LiteralPath $StagingRoot -Recurse -Force
    }
}
