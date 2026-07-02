# Statistical Dependency Spike

This document records the opt-in NumPy/SciPy compatibility spike required before SciPy-backed statistical methods become executable.

## Scope

- Candidate packages only: NumPy and SciPy.
- Target runtime: Windows 11, CPython 3.10.x, CPU-only, local `.venv`.
- Methods gated by this spike:
  - `eda.normality`
  - `eda.equal_variances`
  - `hypothesis.one_sample_t`
  - `hypothesis.paired_t`
  - `hypothesis.one_sample_wilcoxon`
  - `hypothesis.two_sample_t`
  - `hypothesis.mann_whitney`
  - `hypothesis.kruskal_wallis`
  - `hypothesis.one_way_anova`
  - `hypothesis.equivalence_tost`
  - `categorical.one_proportion`
  - `categorical.two_proportion`
  - `categorical.chi_square_association`
- This spike does not approve pandas, statsmodels, PyTorch, GPU packages, or any external service.

## Commands

Install candidate wheels into the local `.venv` and run the smoke check:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
```

By default, the command writes the smoke JSON to:

```text
logs\stat-dependency-smoke.json
```

Run only the smoke check after dependencies are already installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-stat-deps.ps1
```

Validate a recorded smoke JSON file:

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json
```

Render a markdown record block from a validated smoke JSON file:

```powershell
.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json
```

Generate normality reference output after the dependency spike passes and versions are recorded:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py
.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py
```

The install script uses wheel-only installation and defaults to:

- `numpy==2.2.6`
- `scipy==1.15.3`

## Required Result Record

Fill this in after running from native Windows PowerShell:

```text
Date:
Windows version:
Python command:
Python version:
NumPy version:
SciPy version:
Install command:
Smoke command:
Smoke result:
Smoke result file:
Smoke result validation command:
Smoke result validation:
Rendered record command:
Normality reference command:
Normality reference validation command:
Full check command:
Full check result:
Wheel-only install confirmed:
License review:
Offline runtime note:
Startup/import time note:
Known warnings:
Decision:
```

## Pass Criteria

- `.venv` uses CPython 3.10.x.
- `pip install --only-binary=:all:` succeeds without source builds.
- `scripts/check-stat-deps.ps1` returns `status: passed`.
- Smoke output includes finite statistics and valid p-values for:
  - Shapiro-Wilk
  - Anderson-Darling normality critical values
  - Levene centered at mean
  - Brown-Forsythe via Levene centered at median
- `scripts/check.ps1` passes from native Windows PowerShell after any dependency pin changes.
- Reference fixtures are added before gated methods change from `planned` to `available`.

## Current Status

Native Windows dependency spike passed with candidate wheels on 2026-06-29 KST.
The validated versions, NumPy 2.2.6 and SciPy 1.15.3, are now production-pinned
for `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`,
`hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`,
`hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`,
`hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association`. `eda.equal_variances`,
`hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`,
`hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`,
`hypothesis.equivalence_tost`,
`categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` each received their own reference-backed implementation
slices before becoming executable.

## Recorded Result

- Date: 2026-06-29 KST (`logs/stat-dependency-smoke.json` timestamp rendered as 2026-06-28T22:22:25+00:00)
- Windows version: `Windows-10-10.0.19045-SP0`
- Python command: `.\.venv\Scripts\python.exe`
- Python version: 3.10.11
- NumPy version: 2.2.6
- SciPy version: 1.15.3
- Install command: `powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1`
- Smoke command: `powershell -ExecutionPolicy Bypass -File .\scripts\check-stat-deps.ps1`
- Smoke result: passed
- Smoke result file: `logs\stat-dependency-smoke.json`
- Smoke result validation command: `.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json`
- Smoke result validation: passed
- Rendered record command: `.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json`
- Normality reference command: `.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py`
- Normality reference validation command: `.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py`
- Full check command: `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`
- Full check result: passed; backend ruff, format check, mypy, backend pytest 78 tests, frontend lint, frontend typecheck, Vitest 16 tests, and frontend build all passed
- Wheel-only install confirmed: yes, `install-stat-deps-spike.ps1` uses `pip install --only-binary=:all:` and installed `cp310-win_amd64` wheels.
- License review: installed wheel metadata classifiers report `License :: OSI Approved :: BSD License` for NumPy and SciPy.
- Offline runtime note: smoke and reference generation run locally after wheel install; no external runtime service is required.
- Startup/import time note: not benchmarked in this spike.
- Known warnings: SciPy emits the documented Shapiro-Wilk p-value accuracy warning for the synthetic `N=6001` reference case.
- Decision: candidate dependency spike passed and supported the narrow production dependency pin plus `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` implementations. Re-run the smoke before changing these pins or adding another SciPy-backed method.

### Smoke Summary

- Shapiro-Wilk: statistic=0.992482913099, pvalue=0.998958234608
- Anderson-Darling normal: statistic=0.102736576779, critical_values=5
- Levene mean: statistic=1.71428571429, pvalue=0.221377349508
- Brown-Forsythe: statistic=1.71428571429, pvalue=0.221377349508

## Attempt Log

### 2026-06-29 Native Windows PowerShell Spike

Result: passed.

Commands run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json
.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json
.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py
.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py
```

Generated reference fixture:

```text
backend\tests\reference\fixtures\normality_scipy_reference.json
```

The first smoke-only check before installation failed with stable error
`stat_dependency_missing` for `numpy`, confirming the dependencies were not
already present in `.venv`.

### 2026-06-29 Initial WSL-Agent Attempt

Result: blocked before Windows command execution in the initial sandboxed WSL path.
The later native Windows PowerShell spike above supersedes this blocked attempt.

Commands attempted from WSL:

```powershell
powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion"
cmd.exe /c .venv\Scripts\python.exe -V
```

Both commands failed before PowerShell/Python startup with:

```text
WSL (2 - ) ERROR: UtilBindVsockAnyPort:309: socket failed 1
```

Decision: do not mark NumPy/SciPy as validated and do not change `eda.normality` from `planned`.

Next native Windows PowerShell commands:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json
.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json
.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py
.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py
```

WSL Python is 3.12.3 in the current agent session, so direct WSL smoke execution correctly fails with `python_version_unsupported`.
