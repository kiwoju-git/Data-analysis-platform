param(
    [string]$OutputDirectory = ".\.tmp\releases"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourceCommit = (Get-Content -LiteralPath (Join-Path $RepoRoot "SOURCE_COMMIT.txt") -Raw).Trim()
$ShortCommit = $SourceCommit.Substring(0, 8)
$DateStamp = Get-Date -Format "yyyyMMdd"
$OutputRoot = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $OutputDirectory))
$StagingRoot = Join-Path $OutputRoot "presentation-staging-$ShortCommit"
$ZipPath = Join-Path $OutputRoot "statistical-twin-presentation-preview-$DateStamp-$ShortCommit.zip"

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
    Write-Host "SHA-256: $zipHash"
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $StagingRoot) {
        Remove-Item -LiteralPath $StagingRoot -Recurse -Force
    }
}
