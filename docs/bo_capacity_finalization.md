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

First native run `43717196485`, source `1a23587`:

| Native target | Case | Fit seconds | Total seconds | Peak bytes |
|---|---|---:|---:|---:|
| Windows3.10 | Numeric500x6,5 iterations |10.39|23.77|344,367,104|
| Windows3.10 | Mixed500x6,5 iterations |16.33|35.72|346,542,080|
| Linux3.12 | Numeric500x6,5 iterations |6.97|16.03|377,303,040|
| Linux3.12 | Mixed500x6,5 iterations |10.04|22.56|382,328,832|

These resource jobs and dependency-security passed; that does not mean the
whole first CI run passed. Python3.11 and Linux3.12 each reported4 failures,
4710 passes and34 skips. Four stale expectations remained: backup metadata38,
five-response rejection, OpenAPI maximum4, and a missing E2E step in the coverage
document. They were corrected to the actual39/six-response contract, with the
invalid vector boundary moved to seven. The focused rerun passed17 tests.

## Worker Teardown Regression

The first built six-response mixture workflow completed import, fitting,
candidate generation and saved/offline profiler reporting, but selection failed
with `bayesian_desirability_worker_failed`. The identical retained synthetic
request replayed independently with clean exit0 in1.157s, so the original failure
is not conclusively attributed to teardown delay or resource pressure.

Source inspection did find a separately reproducible bug: after a complete frame,
a fixed two-second join rejected otherwise successful clean teardown despite time
remaining. A three-second delayed-exit regression failed before the correction.
The parent now uses short joins within its **original deadline**, continues checking
cancel, and still requires exit0. It does not accept bytes from a crashed worker
or extend computation budgets. Post-result cancellation, timeout, nonzero exit,
cleanup and existing planning-worker tests passed44 cases, with one existing
Windows-inapplicable POSIX-frame test skipped. A fresh built six-response mixture
workflow then passed import, fit, candidates, all-factor profiler, saved/offline
HTML, two actual six-value observations, refit and historical-view restoration.
This successful rerun does not retrospectively prove the first failure's cause.

## Local Preview

The API46/metadata38 preview was applied and the existing localhost8620 tab was
refreshed. A Windows `File.Replace` null-backup argument initially interrupted
the replacement; the guarded helper was corrected and resumed after checking
the exact prior index/backup and an unoccupied port. No study was rewritten.
The final API46/metadata39 build was subsequently applied. A standalone SQLite
backup was created through SQLite's backup API before the restart. Verification
confirmed unchanged contents of all43 business tables and checksums of all4
existing stored assets. Only migration metadata changed. The existing Edge tab
was refreshed and showed the mounted application, sidebar and API-ready state.
The preview serves an external build directory, independent of later build cleanup.
Backup, preservation receipts and user-specific paths remain local, outside Git.

## Native Mixture Failure Investigation

Run `43720248024` (`1bf2f75`) passed Python3.11:4718 tests,34 skips. Linux3.12
also passed all4718 backend tests and1613 frontend tests, then failed the real
mixture E2E's first model creation with `bayesian_mixture_planning_input_invalid`.
The failed request had six responses, three deterministic starts,1000 total
optimizer evaluations and the unchanged60-second limit. Its trace and first
failure remain retained; Windows built success is not substituted for this failure.

Independent review confirmed error masking: `BayesianOptimizationError` inherits
`ValueError`, and the mixture dispatcher rewrote typed budget/numerical exceptions
as input errors. Four computation-free tests reproduced this before the fix.
Typed errors now reach the existing outer public-code allowlist unchanged;
unknown exceptions remain redacted. Transport/worker regression:51 passed,
one existing POSIX-only test skipped on Windows. A synthetic default-settings
probe records the native cause and preceding model evaluation counts without
changing budgets or claiming its diagnostic output is acceptance evidence.
The exact captured factor/response IDs give the same Windows result as sequential
IDs: six completed fits used129/129/212/212/129/129 evaluations,940 of1000 total,
in19.52s including probe setup. In run `43724178882`, Linux3.12 reproduced
`bayesian_optimization_budget_exhausted` in3.55s. Four completed responses used
168/168/262/262 evaluations (860 total), then the next fit exhausted the shared
1000-evaluation budget. The retained E2E trace and probe have identical design,
objective, fit options, coordinates and responses. This distinguishes the native
budget failure from incorrect input, a60-second timeout or a fixture mismatch.
The diagnostic job exits successfully for allowlisted failures by design; it is
not a passing mixture workflow and does not replace the strict native E2E gate.

The mixture UI now exposes the already supported1-3 deterministic starts in
collapsed advanced fit settings. Default3, total1000 evaluations and60 seconds
remain unchanged. The saved model displays its own applied count, not the current
draft. Typed budget/time failures have specific local recovery instructions.
Two draft/control tests failed before this change, then all12 focused tests passed.
The E2E keeps the first default attempt: either a complete model or the exact
budget failure with unchanged study and no partial model is required. It then
explicitly selects1 through the UI and requires successful fit, stored settings,
profiler/report, candidates, observations and refit. Other errors still fail.
The fresh Windows built journey passed: default fit201, explicit1-start fit,
six responses,8 then10 completed observations, saved/offline profiler,32 next
candidates and historical view retention. An earlier test attempt manipulated
advanced settings before the refreshed history reached the UI and timed out on
a collapsed input. The test now waits for the exact new history hash before
interacting; product source ownership was not relaxed.

## Windows Check Partition

Run `43717196485` reached its unchanged90-minute deadline while still advancing
through72% of pytest. It was not observed to hang. Two earlier assertion failures
in that run are among the stale expectations already corrected in `1bf2f75`;
the timeout's teardown exceptions are not treated as separate product defects.
Integration/API tests live inside `backend/tests/unit`, so splitting directories
would not balance the work. Two native Windows jobs now collect the full suite
and assign sorted test files round-robin. No test or assertion is removed.
Each emits its complete/selected node IDs. The existing `windows` gate requires
both jobs to succeed and verifies identical full collections, exact partitions,
disjoint selected sets and complete union before static/frontend checks. The
four Windows E2E suites and `release-ready` dependencies remain unchanged.
Local `scripts/check.ps1` still runs everything by default. Its explicit CI-only
`-SkipBackendTests` path is used only after those native shard and coverage gates.
Focused shard/readiness tests passed98 cases. Two independent real collection
runs covered4798 tests exactly once (2318/2480), and the standalone validator
passed. The first local collection attempt used the root editable installation
instead of the isolated worktree and correctly failed an import; explicit
worktree `PYTHONPATH` fixed the environment without changing production code.
This collection check proves coverage, not that all4798 tests passed locally.
An independent final read-only review found no blocking gate issue: failure,
cancellation and skipped shards cannot pass the Windows aggregate; collection
receipts are not treated as execution success. Native completion remains required.

Run `43726720150` at `fe64788` completed both Linux3.12 and Python3.11 backend
suites with4763 passed/34 skipped and one stale workflow-contract assertion.
That assertion still classified `windows` as an ordinary job rather than the
new always-run shard aggregate. It was reproduced locally, then corrected to
require the exact aggregate guard for `windows` and the exact ordinary guard
for `windows-backend`. No calculation or workflow behavior changed. The full
partition/shard/release-readiness test group then passed195 tests; Ruff and
format checks passed. Independent review found no other contradictory Windows
gate assertion. These failed native runs remain evidence, not a passing final CI.

The same run's Windows shard1 exposed two additional archive-fingerprint test
failures (`Get-FileHash` unavailable). The new shard launched Python directly
from PowerShell7; Python's Windows PowerShell5.1 children inherited incompatible
PS7 module paths. This is the intermediate-process case documented by
[Microsoft PSModulePath](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath?view=powershell-7.3).
Only the shard execution shell now uses Windows PowerShell, restoring the
original check.ps1 process ancestry. Hashing, child environments, test assertions
and budgets are unchanged. An exact-shell regression failed before that change.
The complete local startup/partition/shard/readiness group then passed230 tests
in159.17s; Ruff/format passed. Independent review accepted the narrow environment
fix. Native Windows confirmation is still required.

## Verification Ledger

- Fresh full-check attempts retained: missing worktree Ruff launcher corrected
  using the already installed binary; one full run intentionally stopped when
  the SQL blocker was discovered; generated capability inventory refreshed for39.
- Local Ruff/format/mypy359 files, capability sync and final frontend build passed.
  The4748-test local backend run was stopped early to free memory for serial UI
  verification; no full local backend pass is claimed. Native full checks remain
  mandatory, not replaced by that partial run.
- Fresh local frontend checks passed:3047 source strings/4727 translation keys,
  lint with0 errors and12 existing warnings, typecheck,184 test files/1613 tests.
  Tests used one worker and no file parallelism on the8GiB host.
- Built UI numeric/mixed six-response journeys and field validation passed on
  Chromium149, KO/EN,1024/1440. Initial240-row import through241st observation,
  exact restore/offline report and501-row atomic rejection passed. A fresh run also
  imported and reopened exactly500 rows through the actual built UI. Receipt:
  `500_imported_and_restored=true`, `501_rejected_atomically=true`, no page errors.
  The500-row synthetic CSV SHA-256 is
  `0f43db1ea00cb8aedac58d9541b9e6ec7204384f088ab56700b0947974424dbe`.
  The fresh six-response mixture rerun passed as described above. These built
  source workflows are not yet proof of an installed Linux archive.
- A further fresh mixture run passed after batching per-cell DOM reads in the
  saved-profiler test. Every point ID, original X/Y value and metric remains
  asserted; unexpected/duplicate markers are rejected. An independent read-only
  reviewer found no blocking verification loss or new readiness race. The receipt
  records six responses,8 then10 completed trials,32 new candidates, changed
  next-model identity and preserved historical view identity. No product renderer
  or calculation changed in this test optimization.
- Native Windows/Linux/Python3.11/security/release-ready/archive: pending.
- Feature commit `1a23587` and worker/CI follow-up `1bf2f75` pushed;
  [PR11](https://github.com/kiwoju-git/Data-analysis-platform/pull/11)
  targets main. Main merge is blocked until all required gates pass.

Earlier results in `bo_500_capacity.md` and `bo_six_responses.md` are historical
checkpoints, not substitutes for this ledger's final-source verification.

## Rollback Boundary

Revert only this work's commits in reverse order, never reset unrelated main
changes or delete a workspace. Code revert does not downgrade metadata39.
Old code must use a separately restored, verified pre-upgrade backup; do not
point it at the upgraded workspace. New500-row/six-response artifacts may exceed
old readers' limits. Keep the current workspace and backup independently.

500 is the total trial/history limit, including future experiments. Importing500
completed observations leaves no additional trial slots. No silent filtering,
downsampling or budget expansion is used to create those slots.
