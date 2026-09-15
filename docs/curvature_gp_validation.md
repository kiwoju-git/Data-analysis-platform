# Curvature and GP Kernel Selection Release Record

Status: implementation and focused validation complete; final post-rebase
release gates and publication are pending. A pending check is not a pass.

## Scope, Risks and Outcomes

1. Starting origin/main: `2062546bdf26cf87334264c5e13ec39a40ed20fe`.
2. Center was classified as fixed; changing that flag alone would leave the
   empty factor set as a subset of every factorial term. Explicit independent,
   factorial and structural hierarchy roles fix both issues.
3. Intercept/blocks remain forced. Center and factorial blocks default to
   candidate, with forced/excluded policies. Strong hierarchy includes forced
   interactions but excludes independent Center from subset tests.
4. The supplied 11-run Titer reference gives Center p=0.7129624401 first,
   AB p=0.6115479682 second. Final A/B/C/AC/BC retains B (p=0.2180783400)
   for BC. Full-model AB p=0.6582444755. Forcing Center reproduces AB-first
   and Center p approximately 0.676363.
5. Minitab-like removal order and rounded summaries match the supplied values;
   no claim is made of running a licensed Minitab executable. Independent
   NumPy/SciPy equations provide the static full-precision test oracle.
6. Server catalog IDs drive both full and General Full editors. Users can
   exclude BC before fitting or force Center. Whole multi-DF blocks, not one
   dummy, are selected. Unknown policies/structural removal/hierarchy violations
   are rejected. Catalog estimability comes from the actual matrix null space.
7. Step 0 is displayed as Step 1. Desktop matrices and mobile selectors show
   current-model coefficients/p-values, S/R/adjusted/predicted R/PRESS/DF.
   General Full shows block DF/P with expandable level coefficients.
8. Cp uses the initially specified model's residual MSE, otherwise null with
   a reason. Titer Cp is 8, 6.1636137025, 4.4029157382. No saturated Cp is invented.
9. Omitted Center remains in residual Error. Curvature and other lack-of-fit
   partition aggregate lack-of-fit, and center replicate variation remains
   pure error. Final inclusion is separate from design Center availability.
10. Saved prediction uses the final basis: removed Center permits in-range
    numeric interpolation; retained Center keeps corner/actual-center limits.
    Existing response paste, revisions, residuals, plots and managed HTML remain.
11. WhiteKernel is IID observation-noise variance, not a signal candidate.
    Estimate adds it to every signal; fixed squares response-unit SD onto the
    training diagonal; near-noiseless uses jitter only. Jitter is not new
    observation noise. There is no duplicate RBF+White preset.
12. CV restarts are 0..5/default 0, final restarts 0..10/default 3. Five means
    six starts per fold. Finite bounds and deterministic seeds are required.
13. A strict single/compare union normalizes legacy preset-only requests.
    Compare uses 2..4 unique presets, identical usable rows and shared split
    indices, fold-local scaling/normalization and kernel fitting.
14. Default criterion is observation-predictive NLPD; RMSE/MAE are alternatives.
    Primary/secondary/coverage-distance/preset-priority ties are deterministic.
    Failed candidates keep null metrics/stable codes, cannot win, and all-failed
    runs fail. A selected final-refit failure never substitutes another model.
15. Optional candidate details retain bounded diagnostics/parameters, not
    prediction artifacts or full profiles/surfaces. Exactly one selected model
    asset is created. Reports render stored comparison metrics and selection
    bias warnings without refitting. Compare CV is not an independent test.
16. Start cap 256 plus a 5..600-second global budget; no hidden grid/restart
    reduction. Candidate CV shares 75% fairly, leaving 25% for full refits.
    Nonselected detail failures remain distinct from successful candidate CV.
17. New writes: API 20, Factorial .9/config 4/result 3/envelope 2; General Full
    .4/config 3/result 3/envelope 1; GP .2/result 2/manifest 2. Metadata remains
    20: existing JSON and ownership relations suffice. No new migration.
18. Legacy DOE .8/config 3/result 2 and GP manifest 1 are restored without
    rewriting bytes. Selected GP schema-2 metadata has an independent canonical
    candidate-summary SHA. Numeric NPZ state and no-pickle policy are unchanged.
19. Bayesian optimization/batch calculation, OLS and PLS source files were not
    changed. Four captured old GP kernel fixtures remain within their explicit
    tolerance; independent GP CV fixtures cover smooth/rough/multiscale/noisy
    responses. Final complete-suite results are recorded below when observed.

## Baseline and Development Checks

Host: Intel i7-6500U (2 cores/4 logical), Windows 10 Home build 19045,
PowerShell 5.1, CPython 3.10.11, portable Node 22.23.2. Windows 11 remains the
product target, not a host claimed to have been exercised here. Existing
NumPy 2.2.6/SciPy 1.15.3/scikit-learn 1.7.2; numerical threads limited to one.

- Isolated baseline backend: 1,135 passed, 2 failed in 1,502.11s. Both startup
  failures were due to the detached worktree lacking its own `.venv`; actual
  root-worktree startup checks passed. This is not recorded as a clean baseline.
- Baseline frontend: 328 tests / 43 files passed; strict types, build and full
  Chromium E2E passed. An interrupted initial root check was not counted as passed.
- A failing Titer regression was first reproduced (Center incorrectly fixed).
- Development DOE focused: 59 passed; catalog/API/OpenAPI/startup: 232 passed.
- GP old single-mode unit suite: 17 passed. Independent/legacy GP and API:
  20 passed; expanded GP/DOE persistence and restoration suite: 31 passed.
- Final local DOE catalog/selection checks: 37 passed in 35.82s.
- Full frontend initially found four stale-fixture/assertion failures. Runtime
  fixtures were upgraded to API 20; response locking now checks the actual
  input rather than forbidding every unrelated live loading region. A mistaken
  intermediate RSM assertion edit was reverted before final validation.
- Strict TypeScript and mypy (154 source files) passed during development.
- Focused DOE Chromium E2E and full critical-path E2E passed, including existing
  regression/PLS/PCA/DOE/LHS/Bayesian/asset/navigation paths. Final rerun follows
  the rebase. Localization: 2,969 source strings / 3,790 keys passed initially.

## Benchmark

The 36-case subprocess benchmark uses a 30-second cap per case. Seventeen
completed, nineteen timed out; zero post-fix fit failures. N/d=50/2 completed
all 12 cases in 2.672..19.500s (about 89.4..90.3 MiB process peak). N/d=200/5
completed 5 cases in 13.235..24.188s, with 7 timeouts (about 95.1..97.5 MiB).
All N/d=500/12 cases timed out; reported partial peaks were 143.4..158.0 MiB.
For four cases no fit completed before timeout, so memory is unavailable, not
zero. Wall time includes interpreter startup. Timed-out partial convergence
counts are not interpreted as successful candidate results.

An initial measurement script lacked a Windows HANDLE signature and failed;
that run was discarded and the entire grid rerun after correcting measurement.
The raw diagnostic files stay outside Git. These measurements motivate separate
start/time guards, not a claim that every allowed request finishes in 30 seconds.
The 256 cap preserves default legacy 200-row LOO (204 starts). A 4-kernel,
10-fold, CV-restart-5, final-restart-10 details request has 284 starts and is
rejected before fitting, with the same count shown in the UI.

## Commands

PowerShell used portable Node 22 prepended to PATH; no dependency was installed
or changed. The actual relevant commands include:

```powershell
git fetch origin
git switch -c feat/factorial-curvature-and-gp-kernel-selection origin/main
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_factorial_center_selection.py
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_term_block_model_selection.py backend/tests/unit/test_factorial_center_selection.py backend/tests/unit/test_factorial_model_selection_api.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gaussian_process_regression_api.py backend/tests/unit/test_gaussian_process_kernel_selection.py backend/tests/unit/test_factorial_model_selection_api.py -q
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m mypy backend/app
npm --prefix frontend test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run build
node scripts/check_frontend_localization.mjs
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 18011 -FrontendPort 18599 -FactorialWorkflowOnly -DiagnosticsRoot .tmp/e2e-diagnostics-curvature-doe-focused
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 18011 -FrontendPort 18599 -DiagnosticsRoot .tmp/e2e-diagnostics-factorial-curvature-gp-kernel
```

## Final Release Gates

Post-rebase focused/full backend, frontend, typecheck/build, localization,
test.ps1, check.ps1 and Chromium E2E: pending. Publication: pending.
No failing state will be pushed to main. Exact final counts, exit codes and
the resulting publication SHA/CI observation will be added after execution.

## Diagnostics and Limitations

Diagnostics remain in `.tmp/e2e-diagnostics-factorial-curvature-gp-kernel`.
Required desktop/mobile captures include term selection, Center candidate/
forced, step matrix/mobile, final Titer model, kernel settings/noise help,
comparison/details/budget blocking/mobile. Desktop tables are internally
scrollable. Viewports: 1440x900, 1280x800 and 390x844. Screenshots are not committed.
Initial mobile capture caught the sidebar transition; final capture waits for
the closed sidebar to leave the viewport, with a bounding assertion.

Minitab itself and Windows 11 were not executed. The referenced image #1 was
not attached; the requested semantic matrix layout was implemented. Nested
kernel-family CV remains P1. Exact GP can time out on larger inputs; no sparse
fallback or silent sampling is performed. LOO's UI count before complete-case
filtering is an upper estimate; the backend enforces the exact usable-row count.
Existing ESLint fast-refresh warnings are nonfatal; no error is suppressed.
The user-owned untracked `examples/image2.png` is intentionally excluded from Git.

## Publication

Feature branch: `feat/factorial-curvature-and-gp-kernel-selection`.
Initial contract commit: `d20353d`. Remaining logical commits and changed-file
inventory are available from the branch diff against the base SHA. Local/main
SHAs, push or permitted-PR method, GitHub commit URL and observed CI status will
be reported after the final gate; no force push is permitted.
