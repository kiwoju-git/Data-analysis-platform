param(
    [string] $ScikitLearnVersion = "1.7.2",
    [string] $NumPyVersion = "2.2.6",
    [string] $SciPyVersion = "1.15.3",
    [string] $JoblibVersion = "1.5.2",
    [string] $ThreadpoolctlVersion = "3.6.0",
    [string] $OutputRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$VersionPattern = '^\d+\.\d+\.\d+([A-Za-z0-9\.\-]+)?$'
foreach ($Candidate in @($ScikitLearnVersion, $NumPyVersion, $SciPyVersion, $JoblibVersion, $ThreadpoolctlVersion)) {
    if ($Candidate -notmatch $VersionPattern) {
        throw "Invalid package version: $Candidate"
    }
}
if ($ScikitLearnVersion -ne "1.7.2" -or $NumPyVersion -ne "2.2.6" -or $SciPyVersion -ne "1.15.3" -or $JoblibVersion -ne "1.5.2" -or $ThreadpoolctlVersion -ne "3.6.0") {
    throw "Spike evidence schema 2 is pinned to the reviewed candidate set. Update the validator and contract before changing versions."
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BootstrapPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$ProbeScript = Join-Path $PSScriptRoot "scikit_learn_gp_probe.py"
$ValidatorScript = Join-Path $PSScriptRoot "validate_scikit_learn_spike.py"
if (-not (Test-Path -LiteralPath $BootstrapPython)) {
    throw "Python virtual environment not found. Run .\scripts\bootstrap.ps1 first."
}

if ($OutputRoot -eq "") {
    $RunId = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputRoot = Join-Path $env:TEMP "datalab-scikit-learn-spike\$RunId"
}
$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
$RepoFullPath = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
if ($OutputRoot.StartsWith($RepoFullPath + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Spike output must stay outside the repository. Use a TEMP directory."
}
if (Test-Path -LiteralPath $OutputRoot) {
    throw "Spike output already exists: $OutputRoot"
}

$Wheelhouse = Join-Path $OutputRoot "wheelhouse"
$EnvironmentRoot = Join-Path $OutputRoot "offline-env"
$SpikePython = Join-Path $EnvironmentRoot "Scripts\python.exe"
$ResultPath = Join-Path $OutputRoot "scikit-learn-spike.json"
$ProcessOutput = Join-Path $OutputRoot "process-output"
New-Item -ItemType Directory -Path $Wheelhouse, $ProcessOutput -Force | Out-Null

function Invoke-Checked {
    param([string] $Executable, [string[]] $Arguments, [string] $FailureMessage)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (exit code $LASTEXITCODE)"
    }
}

function Invoke-MeasuredProbe {
    param([string] $Mode, [int] $Index)
    $Stdout = Join-Path $ProcessOutput "$Mode-$Index.stdout.json"
    $Stderr = Join-Path $ProcessOutput "$Mode-$Index.stderr.txt"
    $Arguments = "`"$ProbeScript`" --mode $Mode --hold-seconds 0.25"
    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $SpikePython
    $StartInfo.Arguments = $Arguments
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo
    $Stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not $Process.Start()) {
        throw "Probe mode $Mode could not start"
    }
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()
    $PeakWorkingSetBytes = 0L
    $MonitoredProcessIds = @($Process.Id)
    $ChildProcessFound = $false
    while (-not $Process.HasExited) {
        if (-not $ChildProcessFound) {
            $ChildProcesses = @(
                Get-CimInstance Win32_Process -Filter "ParentProcessId = $($Process.Id)" |
                    Where-Object { $_.Name -eq "python.exe" }
            )
            if ($ChildProcesses.Count -gt 0) {
                $MonitoredProcessIds += @($ChildProcesses | ForEach-Object { [int] $_.ProcessId })
                $ChildProcessFound = $true
            }
        }
        $CurrentWorkingSetBytes = 0L
        foreach ($ProcessId in $MonitoredProcessIds) {
            try {
                $CurrentWorkingSetBytes += (Get-Process -Id $ProcessId -ErrorAction Stop).WorkingSet64
            }
            catch {
                continue
            }
        }
        if ($CurrentWorkingSetBytes -gt $PeakWorkingSetBytes) {
            $PeakWorkingSetBytes = $CurrentWorkingSetBytes
        }
        Start-Sleep -Milliseconds 10
    }
    $Process.WaitForExit()
    $StdoutText = $StdoutTask.Result
    $StderrText = $StderrTask.Result
    $StdoutText | Set-Content -LiteralPath $Stdout -Encoding UTF8
    $StderrText | Set-Content -LiteralPath $Stderr -Encoding UTF8
    $Stopwatch.Stop()
    if ($Process.ExitCode -ne 0) {
        throw "Probe mode $Mode failed: $StderrText"
    }
    return [pscustomobject]@{
        elapsed_ms = [Math]::Round($Stopwatch.Elapsed.TotalMilliseconds, 3)
        peak_working_set_mib = [Math]::Round($PeakWorkingSetBytes / 1MB, 3)
        output = ($StdoutText | ConvertFrom-Json)
    }
}

function Get-MetricSummary {
    param([object[]] $Samples)
    $Elapsed = @($Samples | ForEach-Object { $_.elapsed_ms } | Sort-Object)
    $Memory = @($Samples | ForEach-Object { $_.peak_working_set_mib } | Sort-Object)
    $Middle = [int][Math]::Floor($Elapsed.Count / 2)
    return [ordered]@{
        min_elapsed_ms = $Elapsed[0]
        median_elapsed_ms = $Elapsed[$Middle]
        max_elapsed_ms = $Elapsed[-1]
        median_peak_working_set_mib = $Memory[$Middle]
    }
}

Push-Location $RepoRoot
try {
    $PythonVersion = (& $BootstrapPython -c "import platform; print(platform.python_version())").Trim()
    if (-not $PythonVersion.StartsWith("3.10.")) {
        throw "The dependency spike requires CPython 3.10.x, got $PythonVersion"
    }

    $Packages = @(
        "numpy==$NumPyVersion",
        "scipy==$SciPyVersion",
        "scikit-learn==$ScikitLearnVersion",
        "joblib==$JoblibVersion",
        "threadpoolctl==$ThreadpoolctlVersion"
    )
    $DownloadArguments = @(
        "-m", "pip", "download",
        "--dest", $Wheelhouse,
        "--only-binary=:all:",
        "--platform", "win_amd64",
        "--implementation", "cp",
        "--python-version", "310",
        "--abi", "cp310"
    ) + $Packages
    Invoke-Checked $BootstrapPython $DownloadArguments "Wheel-only download failed"

    Invoke-Checked $BootstrapPython @("-m", "venv", $EnvironmentRoot) "Temporary venv creation failed"
    $InstallArguments = @(
        "-m", "pip", "install", "--no-index", "--find-links", $Wheelhouse,
        "--only-binary=:all:"
    ) + $Packages
    Invoke-Checked $SpikePython $InstallArguments "Offline wheel install failed"
    Invoke-Checked $SpikePython @("-m", "pip", "check") "pip check failed"

    $Metadata = Invoke-RestMethod -Uri "https://pypi.org/pypi/scikit-learn/$ScikitLearnVersion/json"
    $CandidateWheel = @($Metadata.urls | Where-Object { $_.filename -match 'cp310-cp310-win_amd64\.whl$' })
    if ($CandidateWheel.Count -ne 1) {
        throw "Expected exactly one CPython 3.10 Windows AMD64 candidate wheel"
    }

    $WheelRecords = @(
        Get-ChildItem -LiteralPath $Wheelhouse -File | Sort-Object Name | ForEach-Object {
            [ordered]@{
                filename = $_.Name
                size_bytes = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    )
    if ($WheelRecords.Count -ne 5) {
        throw "Expected five pinned wheels, got $($WheelRecords.Count)"
    }

    $PreviousEnvironment = @{}
    foreach ($Name in @("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "PIP_NO_INDEX", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")) {
        $PreviousEnvironment[$Name] = [System.Environment]::GetEnvironmentVariable($Name, "Process")
    }
    try {
        $env:OMP_NUM_THREADS = "1"
        $env:MKL_NUM_THREADS = "1"
        $env:OPENBLAS_NUM_THREADS = "1"
        $env:PIP_NO_INDEX = "1"
        $env:HTTP_PROXY = "http://127.0.0.1:9"
        $env:HTTPS_PROXY = "http://127.0.0.1:9"
        $env:ALL_PROXY = "http://127.0.0.1:9"
        $env:NO_PROXY = ""

        $BaselineSamples = @(1..5 | ForEach-Object { Invoke-MeasuredProbe "empty" $_ })
        $ImportSamples = @(1..5 | ForEach-Object { Invoke-MeasuredProbe "import" $_ })
        $GpSamples = @(1..5 | ForEach-Object { Invoke-MeasuredProbe "gp" $_ })
    }
    finally {
        foreach ($Name in $PreviousEnvironment.Keys) {
            [System.Environment]::SetEnvironmentVariable($Name, $PreviousEnvironment[$Name], "Process")
        }
    }

    $BaselineMetric = Get-MetricSummary $BaselineSamples
    $ImportMetric = Get-MetricSummary $ImportSamples
    $GpMetric = Get-MetricSummary $GpSamples
    $FirstSmoke = $GpSamples[0].output
    $SecondFingerprint = $GpSamples[1].output.deterministic_fingerprint
    $Fingerprints = @($FirstSmoke.deterministic_fingerprint, $SecondFingerprint)
    $Deterministic = $Fingerprints[0] -eq $Fingerprints[1]
    if (-not $Deterministic) {
        throw "GP smoke fingerprints differ across isolated processes"
    }

    $OperatingSystem = Get-CimInstance Win32_OperatingSystem
    $WindowsBuildNumber = [int] $OperatingSystem.BuildNumber
    $WindowsProductType = [int] $OperatingSystem.ProductType
    $Windows11Verified = $WindowsProductType -eq 1 -and $WindowsBuildNumber -ge 22000
    $Result = [ordered]@{
        schema_version = 2
        status = "passed"
        recorded_at = [DateTimeOffset]::UtcNow.ToString("o")
        environment = [ordered]@{
            platform = "$($OperatingSystem.Caption) build $WindowsBuildNumber"
            os_caption = $OperatingSystem.Caption
            os_build_number = $WindowsBuildNumber
            os_product_type = $WindowsProductType
            python_version = $PythonVersion
            architecture = $FirstSmoke.architecture
            cpu_only = $true
            thread_limit = 1
            windows_11_verified = $Windows11Verified
        }
        candidates = [ordered]@{
            numpy = $NumPyVersion
            scipy = $SciPyVersion
            "scikit-learn" = $ScikitLearnVersion
            joblib = $JoblibVersion
            threadpoolctl = $ThreadpoolctlVersion
        }
        candidate_metadata = [ordered]@{
            requires_python = $Metadata.info.requires_python
            license_expression = $Metadata.info.license_expression
            windows_cp310_wheel = $CandidateWheel[0].filename
            windows_cp310_wheel_size_bytes = $CandidateWheel[0].size
            windows_cp310_wheel_sha256 = $CandidateWheel[0].digests.sha256
        }
        installation = [ordered]@{
            wheel_only = $true
            offline_install = $true
            pip_check_passed = $true
            wheels = $WheelRecords
        }
        offline_runtime = [ordered]@{
            no_index = $true
            invalid_proxy = $true
            run_count = 2
            deterministic = $Deterministic
            fingerprints = $Fingerprints
        }
        smoke = $FirstSmoke
        benchmarks = [ordered]@{
            runs = 5
            baseline = $BaselineMetric
            scientific_import = $ImportMetric
            gp_smoke = $GpMetric
            median_import_elapsed_delta_ms = [Math]::Round($ImportMetric.median_elapsed_ms - $BaselineMetric.median_elapsed_ms, 3)
            median_import_peak_working_set_delta_mib = [Math]::Round($ImportMetric.median_peak_working_set_mib - $BaselineMetric.median_peak_working_set_mib, 3)
        }
        decision = [ordered]@{
            candidate_approved_for_future_pin = $Windows11Verified
            production_dependency_changed = $false
            gp_api_added = $false
            note = if ($Windows11Verified) {
                "Candidate passed the Windows 11 dependency gate for a future reviewed implementation slice."
            } else {
                "Candidate remains conditional until the same spike passes on Windows 11."
            }
        }
    }
    $Result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
    Invoke-Checked $BootstrapPython @($ValidatorScript, $ResultPath) "Spike result validation failed"
    Write-Output "Validated spike result: $ResultPath"
}
finally {
    Pop-Location
}
