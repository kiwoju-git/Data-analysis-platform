# BO Capacity Finalization Evidence

## Scope And Identity

- Baseline: `0a4f6ec5fd94217210a7b4ec11b37e611fe667ae`.
- Isolated branch: `feat/bo-500-observations`.
- Approved scope: 500-observation BO, actionable X/Y import field feedback,
  up to six desirability responses, local preview and verified main integration.
- API46 / metadata39. No BO acquisition, normalization or desirability formula
  change. No native JMP numerical-equivalence claim.
- Linux archive verification remains required; Release publication is deferred.
- Synthetic data only. User datasets, artifacts and private JMP material are not
  included in the commit or diagnostic artifacts.

## Review And Fix

An independent read-only reviewer found a real persistence gap: the application
allowed24MiB snapshots, but SQLite still enforced16MiB. The new real INSERT test
failed at that CHECK before the fix. Additive migration39 widens **model snapshots**
to24MiB; candidate, selection and view documents remain16MiB. Owner/workspace
quotas are unchanged. Existing JSON is copied byte-for-byte, not reserialized.

The migration tests cover actual large INSERT/read-back, unchanged historical
rows and foreign keys, and rollback after an injected migration failure. These
use synthetic padding to isolate SQL capacity, not a claimed fitted GP artifact.
The combined migration/benchmark fixture tests passed8 cases in18.00s.

A second read-only review of the new E2E/benchmark/CI files found no blocking
source issue. It explicitly limits the performance claim to bounded domain
calculation, not default-budget convergence or500x6 HTTP/UI persistence.

## Resource Measurements

Windows10 build19045, CPython3.10.11, CPU-only, one BLAS thread,8GiB host RAM.
Measurements are serial, separate processes with four numeric predictors,500
distinct raw observations and six independently fitted synthetic responses.
Mixed adds one nominal predictor with three levels. All models use Matérn5/2,
estimated noise, zero restarts and the unchanged60-second calculation budget.

| Case | Explicit iteration limit | Result | Fit seconds | Fit + disk restore/predict seconds | Process peak MiB | JSON bytes |
|---|---:|---|---:|---:|---:|---:|
| Numeric |100|time budget exceeded|60.10|60.10|185.73|not saved|
| Numeric |5|completed with convergence warnings|31.44|69.08|332.63|21,852,433|
| Mixed |5|completed with convergence warnings|52.79|110.15|334.92|22,337,775|

All six optimizers in the bounded runs reached their iteration limit. Completion
does **not** mean convergence or a recommended production tuning setting. The
first failure is retained; no timeout, row count, candidate budget or convergence
tolerance was loosened. The five-iteration setting is explicit, not an automatic
fallback. 500x6 with every option is not guaranteed to fit the existing budget.

The benchmark checks exact source preservation, canonical JSON bytes and exact
before/after prediction equality. It exercises domain fitting plus disk JSON
restoration, **not** an HTTP journey or the production worker's additional
validation deadline. Peak memory is a process lifetime observation, not a hard
OS-enforced cap or whole-system peak. These local measurements used a dirty
worktree; CI records clean commit provenance separately.

Reproduce from the worktree in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_bo_capacity.py --kind numeric --rows 500 --responses 6 --iterations 5 --output "$env:TEMP\bo-500x6-numeric.json"
.\.venv\Scripts\python.exe scripts/benchmark_bo_capacity.py --kind mixed --rows 500 --responses 6 --iterations 5 --output "$env:TEMP\bo-500x6-mixed.json"
```

Native resource CI runs these explicitly bounded numeric/mixed measurements on
Windows3.10 and Linux3.12, preserving warnings and settings in its receipts.

## Local Preview

The API46/metadata38 preview was applied and the existing localhost8620 tab was
refreshed. A Windows `File.Replace` null-backup argument initially interrupted
the replacement; the guarded helper was corrected and resumed after checking
the exact prior index/backup and an unoccupied port. No study was rewritten.
The final metadata39 matching build and final refresh are pending.

## Verification Ledger

- Fresh full-check attempts retained: missing worktree Ruff launcher corrected
  using the already installed binary; one full run intentionally stopped when
  the SQL blocker was discovered; generated capability inventory refreshed for39.
- Complete local regression: running, no pass claim yet.
- Built UI numeric/mixed/mixture six-response journeys: pending.
- Native Windows/Linux/Python3.11/security/release-ready/archive: pending.
- Main commit/push: pending.

Earlier results in `bo_500_capacity.md` and `bo_six_responses.md` are historical
checkpoints, not substitutes for this ledger's final-source verification.

## Rollback Boundary

Revert only this work's commits in reverse order, never reset unrelated main
changes or delete a workspace. Code revert does not downgrade metadata39.
Old code must use a separately restored, verified pre-upgrade backup; do not
point it at the upgraded workspace. New500-row/six-response artifacts may exceed
old readers' limits. Keep the current workspace and backup independently.
