# BO Completion and Verification Ledger

## Delivery Scope

Owner requested finishing the remaining BO work, recording evidence in Markdown,
and integrating normally into `main`. Linux Release publication remains deferred.
Fetched base: `52f567091aab347f29aec5b8e1f7b6c052b88e3d`.
All test workspaces and browser data in this checkpoint are synthetic. No supplied
JMP slides, private example rows, derived comparison tables, user workspace,
credentials or model files belong in this change.

Already integrated and preserved: noise-aware latent EI/ETI, multi-response
desirability, target curves, persistent candidate revisions, manual ordered
selection, saved-state Profiler, explicit augmentation, nominal/ordinal factors,
source-locked atomic confirmation and managed reports. This change does not
reimplement those features or alter recent DOE/RSM/Gage/GPR calculations.

This follow-up delivers:

- Explicit search controls and strict input validation in the existing UI.
- Saved-model conditional row-LOO diagnostics, numeric and mixed factors.
- Source-locked Auto advice with editable R-squared threshold and explicit Apply.
- Server-verified Auto evidence retained through Review, Confirm, exact-source
  restore and managed HTML for numeric and mixed-factor augmentation.
- Independent numeric, metamorphic, corruption, replay and built-browser tests.

## Contract and Meaning

Integrated contract: API42 / metadata33 / BO method0.16.0. Numeric Auto selection4,
calculation2 and batch11; mixed Auto selection5, calculation4 and batch12.
Evidence schema1 is immutable. Legacy selection2/3 and batch9/10 retain their
original contract and hash inputs. A real additive-compatible CHECK migration
enables the new records; stored payloads are not rewritten.

Conditional LOO fixes the full-fit hyperparameters and normalization. It is not
refitted LOO, external validation or a group/time validation claim. Auto uses the
documented product policy: any response below the threshold suggests exploration;
all available responses passing suggests Refine. Confirm remains a manual choice.
Mixed-factor exploration uses the existing typed maximin policy, not numeric
MaxPro applied to category codes.

The browser supplies only the threshold, exact routing-model identity and expected
decision hash. The server recomputes advice in the same bounded worker as review.
Model-free selection still has `model_id=null` and zero prediction evaluations;
the separate routing model explains the suggestion, not predicted candidate scores.
Reads and report exports validate saved evidence without fitting or rerunning LOO.

## Execution Evidence

Environment: Windows10 Home19045, CPython3.10.11, Node24.17.0,
Chromium149.0.7827.55, CPU-only and single-thread BLAS. One heavy test suite at a
time, with one subagent for scoped implementation/source review.

This is an incremental ledger, not a claim that unfinished checks passed.

| Check | Actual Outcome |
| --- | --- |
| Numeric Auto API, independent LOO and tutorial regression | 22 passed in101.05s, including commit-time routing-source conflict |
| Final combined frontend | 157 files /1407 tests passed in179.47s with one worker |
| Numeric built UI | Passed advice/apply/manual-detach/review/confirm, lost-confirmation retry without duplicate trials, exact restore, KO/EN1024/1440, managed HTML checksum and offline visible metrics; no page errors |
| Final static/build checks | Ruff/format602 files, mypy327 modules, TypeScript/Vite2269 modules and localization3005 strings/4685 keys passed; ESLint0 errors/12 pre-existing Fast Refresh warnings |
| Installed dependencies | `pip check` passed; fresh npm runtime and full audits both reported0 vulnerabilities; native Python advisory gates remain CI responsibilities |
| Full backend attempts before combined scope | First interrupted after stale current-version assertions; second interrupted to consolidate mixed completion. Neither is a full pass |
| Mixed evidence API and migration, first pass | 14 passed in173.58s, nominal/ordinal model-free and Refine paths, legacy bytes, confirm/replay/report/backup/restore |
| Combined new BO/API/migration/OpenAPI/E2E-registration checks | 369 passed in437.07s, including numeric and mixed worker-to-commit routing hash conflicts |
| Mixed/numeric frontend evidence guards | 37 passed across3 files; new source/version/digest/policy mismatch cases and legacy preservation |
| Mixed evidence built browser | Passed on the final combined build: actual UI review/confirm, lost-response retry without duplicate trials, exact restore, KO/EN1024/1440 and offline managed HTML; no page errors |
| Final complete built BO journey | Passed `bo_vector_history.py`: q1/q2, fit-quality settings, stored target curves, typed history entry, candidate pagination/manual selection, Profiler, separate augmentation, mixed planning and both Auto evidence journeys; every recorded pageerror list empty |
| Full local Windows context E2E on0ecda6e | Passed fresh isolated workspace/source server on8682/8683: analysis completion, Report Center, RSM, BO noise/replicates and complete BO, API translation preservation, chart precision, local feedback privacy, English text and actual zoom/layout |
| Initial native CI run42927248274 | Python3.11:4352 passed/8 failed/26 skipped in1002.82s; Linux3.12:4352 passed/8 failed/26 skipped in1041.44s. Both failed only the eight explicit migration-history expectations missing33. Not a product-gate pass |
| Migration expectation correction | Local red reproduced the same missing33 assertion; after adding the explicit tuple to all eight expectations, metadata and Auto migration modules passed35 tests in116.86s. Production code and exact equality assertions unchanged |
| Native dependency/resource gates in first run | All Python runtime/dev and npm security jobs plus dependency-security passed; Windows3.10 and Linux3.12 GP resource jobs passed |
| Final native full-product CI | Still required after the test/docs-only correction. Inspect PR7 checks below; local narrow tests do not substitute for Windows/Linux/Python3.11/security/archive gates |

First failures are retained in the task evidence: missing method0.16 reader
allowlist, backup metadata33 acceptance and batch11 report URL dispatch were found
by real API runs and corrected. Tutorial current-version assertions were updated
to0.16 while legacy0.6 outputs, fixture bytes and numeric tolerances were retained.
Final mixed static checks also caught import formatting and union narrowing;
explicit typed `isinstance` dispatch fixed the latter without changing selection.
No production dependency or numerical tolerance changed in this checkpoint.
The final read-only integration reviewer found no confirmed P1/P2 issue in
numeric/mixed provenance, transaction fences, version dispatch or UI ownership.
That review is source inspection, not a separate execution claim.

The final built journey's synthetic HTML SHA-256 values (downloaded bytes also
opened offline and compared with the saved metrics) were:

- Numeric Auto: `6f02108ff00b72bffb5519429523c75e0c41b3218ccef3a49267973ab16c2f03`.
- Mixed Auto: `75ce6a8f1f173eb564a975ae44c0538745c7d2dc0a79db2002f9136481f70cfb`.

These are report checksums, not Linux distribution checksums. Local screenshots,
traces and synthetic workspace files are not committed. The registered CI suite
regenerates its own synthetic evidence.

Representative commands, from the repository root (PowerShell):

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_auto_evidence_api.py backend/tests/unit/test_bo_mixed_auto_evidence_api.py backend/tests/unit/test_bo_auto_evidence_migration.py backend/tests/unit/test_bo_auto_strategy.py backend/tests/unit/test_bo_auto_strategy_api.py backend/tests/unit/test_bo_loo.py backend/tests/unit/test_bo_loo_api.py backend/tests/unit/test_e2e_suite_partition.py backend/tests/unit/test_openapi_frontend_contract.py -q
npm --prefix frontend run test -- --run --maxWorkers=1
.\.venv\Scripts\python.exe -m mypy backend/app
.\.venv\Scripts\python.exe -m pip check
npm --prefix frontend audit --omit=dev --audit-level=low
npm --prefix frontend audit --audit-level=low
.\.venv\Scripts\python.exe tests/e2e/bo_mixed_workflow.py --base-url http://127.0.0.1:8681 --output "$env:TEMP\bo-evidence-final-20261111\mixed-auto" --auto-evidence-only
.\.venv\Scripts\python.exe tests/e2e/bo_vector_history.py --base-url http://127.0.0.1:8681 --output "$env:TEMP\bo-evidence-final-20261111\full-bo"
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -Suite context -BackendPort 8682 -FrontendPort 8683 -WorkspaceRoot "$env:TEMP\bo-evidence-final-20261111\context-workspace" -DiagnosticsRoot "$env:TEMP\bo-evidence-final-20261111\context-diagnostics" -KeepWorkspace
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_metadata_store.py backend/tests/unit/test_bo_auto_evidence_migration.py -q --tb=short
```

The browser scripts require an isolated synthetic built-UI server; never point
these mutation tests at a real user workspace. Their `--auto-evidence-only`
journeys are also registered alongside the original full journeys in the existing
`bo_vector_history.py` context suite, not as replacements for it.

## Further Verification

- Independent deleted-row Cholesky checks validate LOO values.
- Response unit/offset changes, sign reversal and row permutation validate
  R-squared/routing invariance with appropriately transformed noise units.
- Exact-source hashes, deliberately substituted evidence and commit-time source
  changes exercise ownership rather than merely checking successful HTTP status.
- Lost confirmation responses test idempotency against the entire saved study,
  not only equal response IDs.
- Visible browser metrics and offline HTML are compared with saved numeric values;
  screenshots alone are not the oracle.
- Migration, offline backup/restore and old readers protect stored artifacts.

Actual JMP runtime parity still requires matching JMP output for the same data,
kernel/noise/normalization/optimizer/candidate/seed/settings. Public formulas and
provided educational examples establish only their documented comparison scope.
This implementation is not claimed to reproduce undisclosed JMP algorithms.

## Explicit Limits

No standalone managed LOO-only report is added: diagnostics have their existing
JSON download and Auto evidence is included in the selected-batch managed report.
This optional export is distinct from the completed planning lifecycle.
Existing strict numerical failures are not converted to successful recommendations
by increasing tolerances. A documented synthetic q2 estimate-noise setting
(pool64, one local start,5 local iterations,80 GP iterations) can reject with
`bayesian_desirability_beta_precision_unsupported`; this is not an all-options
q2 success claim. Its source and no-partial-commit evidence remain in
`jmp_gp_bo_alignment.md`. No global optimum or universally faster/better batch
claim is made. No live JMP, physical company-LAN/firewall or Linux Release run is
inferred from Windows/built-app testing.

## Rollback

No rollback is performed. Revert only the exact delivery commits, newest first,
using `git revert <commit>` and normal push after checking the result. Do not use
a broad range that includes earlier BO/DOE work, reset/force-push, or delete user
workspaces, data, models or results. Code revert does not downgrade metadata33.
Older code cannot read the new Auto selections/batches. Run old code only against
a verified pre-upgrade offline backup restored into a new empty destination;
retain the newer workspace intact. Frontend/backend API42 must move together.

## Integration Evidence

Delivery branch: `fix/bo-search-option-alignment`. This committed ledger records
the local evidence and first CI failures, not an advance claim that final remote
jobs passed. Implementation commit: `0ecda6e8145cf4df043a54461db6218a4a5dc062`.
The first CI checks out merge ref `fd86ebff880cf2286c899c2b22e3c6f710ca2bdc`, not
the PR head; its failure is retained in
[run42927248274](https://github.com/kiwoju-git/Data-analysis-platform/actions/runs/42927248274).
[PR7](https://github.com/kiwoju-git/Data-analysis-platform/pull/7) contains the
normal follow-up test/docs commit and the final head's checks.
[Delivery CI history](https://github.com/kiwoju-git/Data-analysis-platform/actions?query=branch%3Afix%2Fbo-search-option-alignment)
and the branch's pull request retain exact head/merge SHAs, native job outcomes
and synthetic diagnostics. Integration must use ordinary push/merge only after
all required product/security/archive gates succeed. Skipped diagnostic-only
jobs are not required-product successes.

No Linux Release/tag/assets are published by this task. CI may build and verify
its normal intermediate archive without publishing a GitHub Release.
