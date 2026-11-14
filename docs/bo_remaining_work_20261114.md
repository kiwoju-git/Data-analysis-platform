# BO Remaining Work: 2026-11-14

## Scope And Baseline

- User-owned: native JMP exact numerical parity. No new parity claim is made here.
- Product work: remaining profiler matrix/persistence, mixture-domain support,
  explicit legacy review renewal, and regressions discovered during validation.
- BASE_SHA: `a9abb4bac0f6104b8fd6ac270edcc80a5bc32050` (fresh `origin/main`).
- Isolated existing worktree reused on `feat/bo-remaining44`; root `main` and
  untracked private JMP documents/images are untouched.
- Linux Release publication remains deferred. Existing native/archive gates stay.
- At most two auxiliary agents; one heavy local verification operation at a time.

## Evidence Ledger

| Item | Evidence | Status |
| --- | --- | --- |
| Previous exact-head PR CI | Run 43422017563 succeeded | Historical evidence only |
| Subsequent main CI | Run 43433553668: Windows workflows failed; release-ready failed | Verified baseline failure; corrected local workflows run2 passed; new remote CI pending |
| Failing child page | `gage-followup/gage-followup/failure.json`; `/src/useAnalysisReportCapability.ts` failed with `net::ERR_NO_BUFFER_SPACE`, then dynamic App import failed | CI-reproduced asset-load failure |
| Socket attribution | Host total 671, TIME_WAIT 618; aggregate only | Browser leak/root OS cause unproven |
| Persisted augmentation simultaneous confirmation | Stale unconfirmed read followed by another request's successful commit | Reproduced; fixed; 16 real SQLite/API-boundary tests passed |
| Legacy first confirmation | Persisted absent-policy augmentation uses strict legacy EI replay | Source-confirmed; renewal path pending |
| Ephemeral recommendation reviews | Memory-only, 20-minute TTL, cleared on restart | Not portable workspace artifacts; do not broaden legacy handling |
| Profiler constraints | Saved-model evaluator returns constraint status; grid and detailed chart ignored it | Reproduced; fixed; 20 component tests and fresh built numeric browser journey passed |
| Whole-factor profiler | Current grid covers responses at one applied axis | Not yet implemented |
| Persistent profiler/standalone LOO view | Existing batch/Auto reports exist; standalone view does not | Not yet implemented |
| Mixture closure/pseudocomponents | Numeric/category factors are independently encoded | Not yet implemented; domain design review required |

CI diagnostics used only synthetic fixtures. Downloaded diagnostic archive SHA-256:
`d13acf720bc79408f5311baf6340bde41ceed478dc4474e40cc480070e556b50`.
It is outside Git; no workspace or raw diagnostic archive is committed.

## Acceptance And Risks

- Keep every E2E stage, four Windows suites and fault-injection test. Do not
  mask asset failures with retry, increased timeout or unconditional readiness.
- Concurrent confirmation may return only the already-committed batch belonging
  to the same selection/study and exact expected hashes. Preserve real failures.
- Historical records remain immutable. A renewed review must be explicit, use a
  new request ID and the exact saved model/configuration, and must never silently
  confirm, refit or switch source/history. Current worker validation stays strict.
- Profiler values outside constraints remain predictions, not valid candidates.
  Show status without dropping points, changing coordinates or color-only cues.
- Whole-factor matrices require bounded sequential evaluation, one model/hash and
  applied holds, complete request invalidation and no partial-success display.
- Mixtures need a joint closure domain, not paired independent inequalities.
  Preserve actual coordinates and versioned transform on all storage paths.
- No new statistical value, source mutation, dependency or DB migration is
  justified by a display-only change.

## Execution Evidence

This section will record commands and fresh results as each slice is verified.
Unit, API, built browser, native CI and archive evidence are separate levels.
Unexecuted steps above are not completed features.

### Confirmation Replay

The fresh confirmation reread validates the owner-scoped selection, both expected
hashes and its confirmed batch ID before invoking the existing strict batch
reader. An unconfirmed failure is re-raised; no partial trials are removed and
no historical calculation is recomputed under a new policy.

`test_bo_augmentation_confirmation_race.py` first reproduced the stale source
guard failure (one failing test). The corrected focused run passed 16 tests in
72.37 seconds with real synthetic SQLite/API artifacts. The model-free worker
entrypoint ran in-process for deterministic scheduling, not a native-worker
stress test. Cases include pending/source/budget/storage interleavings, unchanged
original errors, malformed/mismatched hashes and owner rejection. The first
attempt failed because the temporary parent directory was absent; that setup
failure is not counted as the product RED result. Scoped Ruff and mypy passed.

### Profiler Constraint Display

The response grid first failed two KO/EN component tests, then passed 11 focused
grid/mixed tests. Two additional RED tests exposed the same missing status on
the detailed numeric/composite and mixed profiles. Both detailed and overview
charts now retain exact coordinates/values and use diamond markers plus textual
constraint status. The corrected three-file suite passed 20 tests in 5.14s.
These are source-rendered component checks, not the built localization plugin
or browser evidence. A prior TypeScript check passed before the detailed-chart
follow-up; a fresh complete check is still required.

```powershell
npm --prefix frontend test -- --run src/features/bayesian/BayesianPlanningPanel.test.tsx src/features/bayesian/BayesianMixedPlanningPanel.test.tsx src/features/bayesian/BayesianProfileGrid.test.tsx --maxWorkers=1
```

Read-only independent review found the false-constraint browser fixture was only
reachable by a manual flag. It is now a named `bo_profile_constraints` built
workflow stage, immediately after dataset import. An intermediate context-suite
connection was removed to avoid a duplicate fit. No prior successful test is
credited for this new path. Built workflows run1 successfully built the source and completed the
X/Y import stage, then failed because a dev-only chart fixture was routed to the
built server (`/tests/chart-interaction.html`, HTTP404). That failure is retained
under the external synthetic `workflows1-diagnostics` directory; the runner's
fixture routing is being corrected, not masked by retries.

Built workflows run2 passed the fresh constrained numeric profiler journey:
two responses plus composite desirability, 21 exact points per chart and eight
constraint violations per chart. It checked detailed composite/response mean,
latent SD and predictive SD markers, grid coordinates, accessible constraint
labels, keyboard pin/clear/navigation, KO/EN at 1024/1440 px, DOM bounds and
screenshots. One real model fit occurred; locale/resize/display emitted no
mutating API calls. No page errors were recorded and study history was unchanged.
Root visually inspected the English 1440px grid. Synthetic evidence is outside
Git at `workflows2-diagnostics/bo-profile-constraints`; the source was a dirty
working-tree production build, not a final commit or release archive. Remaining
workflow stages and native CI are not promoted to passed by this receipt.

The manual PowerShell test-server harness was rejected by tool policy before
execution; it created no test evidence. The repository-owned E2E runner was used
instead, so this check is repeatable in the existing workflow CI partition.

### Integrated Local Workflow Result

The entire second workflow run then exited successfully. It covered the new
built profiler stage, built X/Y import/next recommendation, long-group analyses,
fractional selection, CCD/contours, Gage input and six panels, BO noise/replicates,
and the retained Vite fixtures/legacy upload, regression, GP/PLS, stored results,
reports, lazy module failures, locale/storage recovery and Two Variances checks.
Build, stage routing, source-module fault injection and actual browser execution
were tested together. No assertion, retry or timeout was removed/increased.

Fresh local environment: Windows build 19045 (`platform.platform()` reports
`Windows-10-10.0.19045-SP0`), CPython3.10.11 AMD64, Chromium149.0.7827.55,
CPU-only, BLAS/OMP/MKL threads=1. This is not a Windows11 or native Linux run.
Only synthetic, separate workspaces were used. Both runner-owned servers closed;
unrelated user previews were not stopped. Evidence from failed run1 remains.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
.\.venv\Scripts\python.exe tests/e2e/critical_path.py --suite workflows --backend-port 8027 --frontend-port 5227 --workspace-root "$env:TEMP\bo-remaining-20261114\workflows2" --diagnostics-root "$env:TEMP\bo-remaining-20261114\workflows2-diagnostics" --keep-workspace
```

Whole-backend Ruff passed; 620 backend files passed format checking. Changed E2E
helpers also passed Ruff. `pip check` reported no broken requirements. Whole
frontend ESLint exited0 with 12 existing Fast Refresh warnings outside changed
files and no errors. No lint rules or dependency versions were changed.
The full frontend test run passed 167 files / 1,503 tests in 157.48 seconds with
one Vitest worker. This includes the four added constraint-display tests.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check backend tests/e2e/critical_path.py tests/e2e/result_charts.py tests/e2e/bo_persistent_planning.py tests/e2e/bo_profile_graphs.py
.\.venv\Scripts\python.exe -m ruff format --check backend
npm --prefix frontend run lint
npm --prefix frontend run test -- --run --maxWorkers=1
```

Independent final source review found no confirmed P1/P2 in the scoped fixes;
that review did not execute tests and is not substituted for the runs above.
Remote native/security/aggregate CI and a release archive remain unverified for
this checkpoint. Linux publication is intentionally deferred.

The final focused backend regression passed 231 tests in 113.46 seconds with
five existing Starlette deprecation warnings. It combines the actual DB/API race
fixture, augmentation API/contract, historical stored readers, Beta numerical
policy, runner partition/diagnostics and documentation-marker contract. Whole
application mypy passed 335 source files; final frontend TypeScript also passed.
The complete backend test collection and the other three E2E partitions were
not rerun locally in this slice. This result does not imply new remote CI passed.

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_bo_augmentation_confirmation_race.py backend/tests/unit/test_bo_augmentation_api.py backend/tests/unit/test_bo_augmentation_contract.py backend/tests/unit/test_bo_legacy_stored_readers.py backend/tests/unit/test_bo_beta_numerical_policy.py backend/tests/unit/test_e2e_suite_partition.py backend/tests/unit/test_e2e_diagnostics.py backend/tests/unit/test_openapi_frontend_contract.py::test_e2e_coverage_doc_tracks_current_smoke_step_markers -q -p no:cacheprovider --basetemp "$env:TEMP\bo-remaining-20261114\focused-regression"
.\.venv\Scripts\python.exe -m mypy backend/app
npm --prefix frontend run typecheck
```

## Remaining Product Work

The proposed design is in
`docs/superpowers/specs/2026-11-14-bo-remaining-design.md`. An independent builder
check clarified mixture goal/metric separation and historical view ownership.
User confirmation of the proposed scope is still pending; none of these four
features is claimed implemented by this stability checkpoint:

1. Whole-factor/all-response Profiler matrix.
2. Immutable saved Profiler/standalone LOO views and attached reports.
3. Explicit renewed review of unconfirmed legacy augmentation selections.
4. First-class mixture closure and pseudocomponent domain.

The proposed first mixture slice is one continuous mixture group plus process
factors on the existing 1-4-response desirability workflow. Multiple mixture
groups and scalar EI/ETI mixture studies are not silently substituted. Exact
native JMP output parity remains user-owned. No main push or Linux publication
has occurred for this checkpoint.

## Local Checkpoint Commits

- `acaebb5`: owner/hash-validated replay after concurrent augmentation confirmation.
- `0a14d42`: detailed/overview constraint markers, localized status and regression tests.
- `a9449fc`: built workflow stages, retained source-only fixtures and actual-child diagnostics.

These commits remain on `feat/bo-remaining44`, not remote main. Their combined
code was tested before committing; no product edits followed the successful
runs. This document is an evidence checkpoint, not completion of the remaining
functional design. API43 / metadata34 and calculation method versions stay the
same because this checkpoint adds no data/model/schema contract.

Rollback, only when requested, reverts this checkpoint's commits newest first
on the appropriate integration branch. For code-only rollback the order is
`a9449fc`, `0a14d42`, `acaebb5`; documentation commits can be reverted separately.
No workspace, dataset, saved model or result deletion is required or authorized.
No rollback was executed here.

## Workflow Runner Asset Boundary

The synthetic `gage-followup` trace from main CI run `43433553668` contains
303 recorded network exchanges, including 267 `/src/` requests. Together with
the failed source-module request, this establishes unbundled development-module
fan-out in the failing child. It does not establish browser socket leakage or
prove that the host-wide TIME_WAIT count caused the failure.

The runner now builds the current source into each workflow run's fresh temporary
`frontend-dist` directory, fails before server/browser startup on a build error
or absent `index.html`, and runs the real application `workflows` stages against
the existing loopback built-UI/API server. The four-suite partition and relative
ordering of every original stage are preserved. The three development-only chart/resize
fixture stages and all legacy checks remain on Vite, including
the `/src/App.tsx` and `RegressionAnalysisPanels.ts*` fault-injection cases.
Other partitions, `full`, and focused flags retain their previous source mode.
No retries, timeouts, product controls or readiness assertions were changed.
The suite manifest identifies each stage's frontend mode, and the existing CI
log glob also captures `frontend-build.log`. This is not Linux publication.

Runner TDD selected the new `runner_builds_only`, `focused_checks_keep`,
`workflow_build_failure` and `workflow_dispatch_uses` cases:

- Before the runner edit: 4 failed, 15 passed. Failures showed the absent build,
  failure gating and separate built-workflow origin.
- After the edit: 19 passed. These are runner boundary tests with external
  subprocess/browser execution replaced, not actual build/browser evidence.
- The first broader check mistakenly used the parent checkout's virtual
  environment and stopped at collection because `contourpy` was absent. No tests
  ran in that attempt. The corrected interpreter, `app.__file__` and
  `contourpy.__file__` were verified to resolve within this isolated worktree.
- Corrected combined runner, diagnostics and documentation-marker checks:
  110 passed in 11.29 seconds, with two existing Starlette deprecation warnings.
  Ruff check passed; Ruff format was applied to the new runner test layout.
- A separate relative-workspace regression failed before the output path was
  resolved: npm scripts would interpret the relative `--outDir` under
  `frontend/`. The absolute-path correction then passed the combined checks:
  111 passed in 9.90 seconds, with the same two warnings. Final scoped Ruff check
  and runner-test format check both passed.
- The first actual runner build succeeded and the measured X/Y import journey
  completed, then the chart-interaction fixture failed: the built server correctly
  returned 404 for `/tests/chart-interaction.html`. This was a runner-routing
  error, not a product failure. An audit also identified `/tests/result-charts.html`
  and `/tests/desktop-resize.html`; all three stages now use Vite and the manifest
  labels them `dev`. Context's report-center/chart-formatting fixture stages
  already remained on Vite. All chart assertions are unchanged.
- The same failure exposed missing actual-child diagnostics in the chart fixture.
  It now uses the existing `diagnosed_page` boundary, preserving the original
  exception and viewport while recording its trace/DOM/screenshot evidence.
- Routing/manifest and actual-child regression checks reproduced RED:
  3 failed, 4 passed. Built/browser rerun remains required after this correction.
- The subsequent combined check had 111 passes and one contract-test failure:
  the newly added constrained-profiler journey was counted as a second ordinary
  planning journey. The contract now explicitly requires one ordinary, one
  constrained-profile and one Auto-evidence numeric journey, retaining the two
  separate mixed journeys. Final combined checks: 112 passed in 10.00 seconds,
  with the same two deprecation warnings; scoped Ruff and format checks passed.
- The constrained-profiler journey is now the named `bo_profile_constraints`
  stage immediately after `bo_dataset_import` in `workflows` and the full order.
  It runs against the built origin in `workflows`, through the existing repository
  runner and the existing constrained-only helper flag. Its extra context call
  was removed to avoid a duplicate fit; ordinary and Auto-evidence journeys stay
  in context. Existing profiler assertions and all original stage modes remain
  unchanged. Integration TDD: 5 failed/4 passed before registration, then the
  combined checks passed 113 tests in 9.77 seconds with the same two warnings.
  Scoped Ruff checks passed; only new helper-test layout required formatting.

The corrected combined check ran from the isolated worktree:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'backend')
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_e2e_suite_partition.py backend/tests/unit/test_e2e_diagnostics.py backend/tests/unit/test_openapi_frontend_contract.py::test_e2e_coverage_doc_tracks_current_smoke_step_markers -q
```
