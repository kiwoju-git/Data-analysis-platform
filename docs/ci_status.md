# CI Status

Last updated: 2026-07-16

## Workflow Configuration

- Workflow file: `.github/workflows/ci.yml`
- Triggers: `workflow_dispatch`, `pull_request`, and `push` to `main`
- Required runner in file: `windows-latest`
- Runtime setup in file: Python `3.10`, Node `22`
- Main check job command in file: `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`
- Browser E2E job command in file: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1`
- Browser E2E job dependency: runs after the Windows check job succeeds
- Browser install/cache: the `e2e` job sets `PLAYWRIGHT_BROWSERS_PATH` to `${{ runner.temp }}\ms-playwright`, caches that path with `actions/cache@v4`, and installs Chromium with `.\.venv\Scripts\python.exe -m playwright install chromium`
- Browser E2E diagnostics: the `e2e` job runs with `-WorkspaceRoot "${{ runner.temp }}\datalab-e2e" -DiagnosticsRoot "${{ runner.temp }}\datalab-e2e-diagnostics" -KeepWorkspace`. The E2E runner writes step markers to `logs\e2e-diagnostics.log`, records backend/frontend logs, and on browser-flow failure records the current URL, page title, screenshot, and HTML snapshot. Failure screenshot and HTML filenames include the current step slug. Playwright wait timeouts include the current step, URL, and page title. Backend/frontend readiness failures print the exited process name plus recent log tail, and readiness URL timeouts print recent backend/frontend log tails even when the processes are still running. GitHub uploads only diagnostics-root `logs\*.log`, `screenshots\*.png`, and `html\*.html` files as the `e2e-logs` artifact with `if: always()`.

This satisfies the current repository-side requirement that main pushes should start the Windows CI workflow and the browser E2E smoke workflow job.

## Local Validation

- The immutable attribute-control-limit-set storage/API foundation was
  validated locally on 2026-07-16 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with Ruff/format over 150 Python files, mypy over
  98 source files, backend pytest 663 tests, frontend lint/typecheck, frontend
  Vitest 95 tests, and the production build. The targeted OpenAPI/frontend
  contract suite contains 116 tests. Assets are 465.72 kB / 109.65 kB gzip for
  main, 41.53 kB / 8.37 kB for Regression, 59.29 kB / 10.79 kB for Quality,
  and 75.02 kB / 17.11 kB for DOE.
- The host C drive had insufficient space for pytest's selected ESTsoft temp
  directory. Two initial full runs therefore ended in temp-directory and
  SQLite `database or disk is full` errors rather than code regressions. The
  successful full run explicitly set
  `PYTEST_ADDOPTS=--basetemp=D:\codex\data\.tmp\pytest-full-attribute-limit-set-final`;
  generated pytest temp directories from the failed runs were removed only
  after their resolved paths were verified under the pytest temp root.
- Browser E2E passed on 2026-07-16 using backend/frontend ports `8025`/`5225`,
  workspace `.tmp\e2e-workspace-attribute-limit-set-storage`, and diagnostics
  root `.tmp\e2e-diagnostics-attribute-limit-set-storage`. The storage API has
  no Phase II browser control yet; the smoke therefore proves existing Phase
  I, prediction/export, Factorial, RSM/Optimizer, Bayesian, parser-recovery,
  and lazy-route/error-boundary flows remain intact without claiming Phase II
  monitoring coverage.
- The measured host remains Windows 10 Home build 19045 with CPython 3.10.11
  and Node 24.17.0. These local results are not Windows 11 release evidence.
  Windows 11 x64/CPython 3.10/Node 22/CPU-only validation remains a mandatory
  release gate. The `gh` CLI is unavailable, so remote GitHub Actions and
  artifacts were not independently verified.
- The Phase II attribute-control-chart contract/reference foundation was
  validated locally on 2026-07-16 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with Ruff/format over 147 Python files, mypy over
  96 source files, backend pytest 640 tests, frontend lint/typecheck, frontend
  Vitest 95 tests, and the production build. The OpenAPI/frontend contract
  suite remains 110 tests. Assets are 465.27 kB / 109.56 kB gzip for main,
  41.53 kB / 8.36 kB for Regression, 59.29 kB / 10.79 kB for Quality, and
  75.02 kB / 17.11 kB for DOE.
- Browser E2E passed on 2026-07-16 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-attribute-phase2-contract`. The
  attribute-chart path verifies the current Phase I-only/stored-Phase-II-not-
  applied notice and result limit source before retaining the real P-chart,
  prediction/export, Factorial, RSM/Optimizer, Bayesian, parser-recovery, and
  lazy-route/error-boundary flows.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. These local results are not Windows 11 release evidence. Actual
  Windows 11 x64/CPython 3.10/CPU-only validation remains a mandatory release
  gate rather than a development blocker. The `gh` CLI is unavailable, so
  remote GitHub Actions and artifacts were not independently verified.
- The Bayesian sequential-lifecycle stabilization was validated locally on
  2026-07-15 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with Ruff/format over 146 Python files, mypy over
  96 source files, backend pytest 635 tests, frontend lint/typecheck, frontend
  Vitest 95 tests, and the production build. The OpenAPI/frontend contract
  suite remains 110 tests. Assets are 465.22 kB / 109.54 kB gzip for main,
  41.53 kB / 8.37 kB for Regression, 58.83 kB / 10.62 kB for Quality, and
  75.02 kB / 17.11 kB for DOE.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-bayesian-lifecycle-stabilization`.
  The Bayesian flow now creates an actual-unit constrained study and verifies
  the stored equation and recommendation feasibility, while all existing
  upload/parser, saved-result, prediction/export, attribute-chart, Factorial,
  RSM/Optimizer, and lazy-route/error-boundary paths remain covered.
- The three-repeat local worker benchmark on Windows 10 Home build 19045 and
  CPython 3.10.11 measured a `475.103 ms` empty-spawn median. Median worker
  round trips were `3086.439`, `2890.613`, and `3135.319 ms` for the 1-factor/
  8-observation, 2-factor/20-observation, and 4-factor/48-observation cases.
  Detailed fit/non-fit timings and definitions are in
  `docs/bayesian_optimization_contract.md`; they are descriptive rather than
  CI performance thresholds.
- These are local Windows 10 results before commit/push, not Windows 11 release
  evidence or remote GitHub Actions verification. Actual Windows 11 validation
  remains a mandatory release gate. The `gh` CLI remains unavailable, so the
  current remote workflow state was not independently verified.
- The bounded Bayesian GP/EI executable slice was validated locally on
  2026-07-15 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with Ruff/format, mypy over 96 source files,
  backend pytest 633 tests, frontend lint/typecheck, frontend Vitest 94 tests,
  and the production build. The OpenAPI/frontend contract suite contains 110
  tests. The production assets are 465.22 kB / 109.54 kB gzip for main,
  41.53 kB / 8.36 kB for Regression, 58.83 kB / 10.62 kB for Quality, and
  70.01 kB / 16.26 kB for DOE. A post-fix frontend lint/typecheck/Vitest run
  also passed after correcting the Bayesian factor-input event handling.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-bayesian-gp-ei-final`. It retained
  upload/parser recovery, stored analyses, prediction/export, attribute chart,
  Factorial, RSM/Optimizer, and lazy-route/error-boundary coverage, and added a
  real bounded Matern-5/2 GP/Expected Improvement flow whose candidate remains
  a pending recommendation until the user records an objective observation.
- These are local Windows 10 Home build 19045 results before commit/push, not
  Windows 11 release evidence or remote GitHub Actions verification. By product
  owner direction, actual Windows 11 x64/CPython 3.10/CPU-only validation is a
  mandatory release gate rather than a development blocker. The `gh` CLI is
  unavailable in this environment, so the current remote workflow state was
  not independently verified.
- The scikit-learn production-pin and Windows Python hash-lock slice was
  validated locally on 2026-07-15 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. The product owner explicitly
  moved actual Windows 11 client validation to the release gate. The measured
  host remains Windows 10 Home build 19045, so no Windows 11 release evidence
  is claimed. `scikit-learn==1.7.2` is now an exact production pin; the 45-wheel
  CPython 3.10 Windows AMD64 lock includes reviewed joblib 1.5.2 and
  threadpoolctl 3.6.0 constraints plus runtime/dev/build dependencies with
  SHA-256 hashes. A fresh external TEMP venv installed only from the retained
  wheelhouse using `--no-index --require-hashes`, built the editable backend,
  passed `pip check`, imported the exact scientific versions, and imported
  `app.main` with `sklearn_loaded=False`.
- Full `scripts\check.ps1` then passed in one continuous run: Ruff and format
  passed over 140 Python files, mypy passed over 93 source files, backend
  pytest passed 618 tests, frontend lint/typecheck passed, frontend Vitest
  passed 93 tests, and the production build passed. The OpenAPI/frontend
  contract suite contains 104 tests. The main asset remains 464.68 kB / 109.49
  kB gzip. Browser E2E passed with diagnostics root
  `.tmp\e2e-diagnostics-sklearn-lock-promotion`, retaining upload/parser
  recovery, stored analyses, prediction/export, attribute chart, Factorial,
  RSM/Optimizer, and lazy-route/error-boundary coverage. No GP, EI,
  recommendation, objective execution, method/config/result schema, or fake
  result was added.
- The standard bootstrap's Python hash-lock install, editable install, and
  `pip check` passed. Its subsequent `npm ci` was not a clean pass because the
  intentionally retained Vite process on port 5173 held the Rolldown native
  module open and Windows returned `EPERM`; a non-destructive `npm install`
  restored the partially removed local node_modules without changing
  `package.json` or `package-lock.json`, after which the complete check passed.
  This local file-lock event is not represented as a dependency-contract
  failure or as a successful bootstrap run.
- Historical pre-promotion record: the conditional scikit-learn dependency
  spike was validated locally on
  2026-07-15 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. The TEMP-only isolated runner
  passed exact Windows AMD64 wheel download, offline `--no-index` install,
  `pip check`, current NumPy/SciPy compatibility, invalid-proxy runtime,
  single-thread CPU inspection, and matching deterministic GP fingerprints
  for scikit-learn 1.7.2/joblib 1.5.2/threadpoolctl 3.6.0. The measured host is
  Windows 10 Home build 19045, so the Windows 11 gate and product pin remain
  explicitly unapproved. Evidence schema 2 records OS caption/build/ProductType,
  excludes Windows Server hosted runners, and binds candidate wheel metadata
  to the downloaded manifest. Full `scripts\check.ps1` passed with backend
  Ruff/format, mypy over 93 source files, backend pytest 612, frontend
  lint/typecheck, frontend Vitest 93, and the production build. The
  OpenAPI/frontend contract suite contains 104 tests. The production main
  asset is 464.68 kB / 109.49 kB gzip. No production dependency, lockfile,
  method/config/result schema, surrogate, EI, or recommendation was added.
  This is local validation before commit/push, not remote GitHub Actions
  verification.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-sklearn-os-gate`. The dependency
  evidence has no product UI, so the smoke retained the complete upload,
  stored analyses, prediction/export, attribute chart, Factorial, RSM/
  Optimizer, parser recovery, and lazy-route/error-boundary paths without
  presenting a fake Bayesian result.
- The Bayesian study/history foundation was validated locally on 2026-07-15
  from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 93 source
  files, backend pytest 603, frontend lint/typecheck, frontend Vitest 93, and
  the production build. The OpenAPI/frontend contract suite contains 104
  tests. SQLite schema 11, study/history asset schemas 1, dedicated routes,
  deterministic initial trials, terminal manual transitions, SHA relationship
  tamper rejection, and typed frontend client alignment are included. No
  surrogate, recommendation, objective execution, or dependency was added.
  The production build has a 464.68 kB / 109.49 kB gzip main asset,
  Regression 41.53 kB, DOE 57.26 kB, and Quality 58.83 kB on-demand chunks;
  no asset exceeds the 500 kB warning threshold.
  This is local validation before commit/push, not remote GitHub Actions
  verification.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-bayesian-foundation`. The foundation
  intentionally has no browser study editor or recommendation step, so the
  smoke retained the complete existing upload, analysis, prediction/export,
  attribute chart, Factorial, RSM/Optimizer, parser recovery, direct lazy
  route, and isolated chunk-failure path without presenting a fake Bayesian
  result.
- The frontend module lazy-loading slice was validated locally on 2026-07-15
  from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 89 source
  files, backend pytest 582, frontend lint/typecheck, frontend Vitest 93, and
  the production build. The OpenAPI/frontend contract suite contains 91 tests.
  The main JavaScript asset is 463.89 kB, with Regression 41.53 kB, Quality
  58.83 kB, and DOE 57.26 kB on-demand chunks; no asset exceeds the 500 kB
  warning threshold. This is local validation before commit/push, not remote
  GitHub Actions verification.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-lazy-panels-reset`. It retained the
  full analysis path, observed all three module resources, opened all three
  routes directly, and verified a sanitized error boundary by aborting one
  Regression import in an isolated page, then switched methods to verify error
  reset and recovery. Earlier attempts exposed synchronous
  selection without `startTransition` and a boundary placed around filters
  instead of the executable panel; both product issues were corrected before
  the complete passing run.
- The DOE immutable response revision/history foundation was validated locally
  on 2026-07-15 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 89 source
  files, backend pytest 582, frontend lint/typecheck, frontend Vitest 90, and
  the production build. The OpenAPI/frontend contract suite contains 91 tests.
  The final frontend rebuild emitted the expected chunk warning for the 618.10 kB main
  JavaScript asset. This is local validation before commit/push, not remote
  GitHub Actions verification.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-doe-revisions-final`. It verified
  response revision 1 analysis pinning, analyzed Factorial/RSM read-only state,
  explicit correction mode, RSM revision 2 creation with revision 1 retained
  in history, optimizer execution, prediction/export, and parser recovery. The
  first attempt created the correction before checking the optimizer warning;
  the correction correctly cleared the superseded source result, so the test
  order was fixed, then the response-name stream-identity assertion was added;
  the final complete rerun passed.
- The post-expansion DOE/RSM lifecycle stabilization was validated locally on
  2026-07-15 from a working tree based on main SHA
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 88 source
  files, backend pytest 572, frontend lint/typecheck, frontend Vitest 90, and
  the production build. The OpenAPI/frontend contract suite contains 87
  passing tests. The build emitted the expected chunk warning for the 612.20
  kB main JavaScript asset. This is local validation before commit/push, not
  remote GitHub Actions verification.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-doe-lifecycle-rerun`. It verified
  the Factorial/RSM pre-analysis lock warning, analyzed response input/save
  locks, valid RSM fit, eligibility-gated optimizer recommendation, prediction/
  export, and upload/parser recovery. The first attempt reached a successful
  optimizer result but a test-only non-exact warning locator matched both the
  warning and typed informational issue; the exact locator fix preceded the
  complete rerun.
- Baseline bootstrap initially found a stale Vite process holding a frontend
  dependency file and `npm ci` returned Windows `EPERM`; only that Vite process
  was stopped and the second bootstrap passed. The first baseline full check
  also exposed pre-existing Ruff formatting in
  `test_openapi_frontend_contract.py`; the final full check above includes the
  formatted contract file and passed. Baseline browser E2E passed independently.
- The Bayesian Optimization planning-contract slice was validated locally on
  2026-07-15 from a working tree based on main SHA
  `3e05a7c32f0fa48830ca22600cbf20f450280244`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 88 source
  files, backend pytest 564, frontend lint/typecheck, frontend Vitest 86, and
  the production build. The OpenAPI/frontend contract suite contains 85
  passing tests. The Vite chunk warning remains for the 608.26 kB main
  JavaScript asset. This is local validation before commit/push, not remote
  GitHub Actions verification.
- Browser E2E passed on 2026-07-15 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-bayesian-contract`. The
  planning-only catalog entry did not add an execution step or alter existing
  results; the full upload, stored analysis, prediction/export, attribute
  chart, factorial DOE, RSM, bounded optimizer, and parser-recovery path
  completed successfully.
- The bounded Response Optimizer slice was validated locally on 2026-07-14
  from a working tree based on main SHA
  `3e05a7c32f0fa48830ca22600cbf20f450280244`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 88 source
  files, backend pytest 558, frontend lint/typecheck, frontend Vitest 86, and
  the production build. The OpenAPI/frontend contract suite contains 85
  passing tests. The existing Vite chunk warning remains for the 606.10 kB
  main JavaScript asset. This is local validation of uncommitted changes, not
  remote GitHub Actions verification.
- Browser E2E passed on 2026-07-14 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-response-optimizer`. The smoke
  completed the verified RSM fit and bounded optimizer recommendation,
  individual/composite desirability, constraint/search status, explicit
  no-global-optimum statement, and confirmation-run warning before completing
  every remaining upload and parser-recovery stage. An initial attempt stopped
  before browser startup on an E2E marker indentation syntax error; correcting
  that test-only line and passing `py_compile` preceded the successful rerun.
- The DOE response-surface CCD/quadratic-model slice and the narrow
  `localhost:5173` CORS compatibility fix were validated locally on
  2026-07-14 from a working tree based on main SHA
  `3e05a7c32f0fa48830ca22600cbf20f450280244`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 86 source
  files, backend pytest 538, frontend lint/typecheck, frontend Vitest 85, and
  the production build. The OpenAPI/frontend contract suite contains 78
  passing tests. The existing Vite chunk warning remains for the 592.01 kB
  main JavaScript asset. This is local validation of uncommitted changes, not
  remote GitHub Actions verification.
- Browser E2E passed on 2026-07-14 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-rsm-rerun`. The first run reached
  the response-surface screen but stopped on a test-only ambiguous heading
  locator. After scoping that assertion to the RSM panel title, the complete
  rerun passed through 13-run CCD creation, response persistence, quadratic
  fit, coefficient/diagnostic rendering, and the two-factor contour, followed
  by every remaining upload and parser-recovery stage.
- The DOE factorial effects/OLS/ANOVA slice was validated locally on
  2026-07-14 from a working tree based on main SHA
  `3e05a7c32f0fa48830ca22600cbf20f450280244`. Full
  `scripts\check.ps1` passed with backend Ruff/format, mypy over 83 source
  files, backend pytest 517, frontend lint/typecheck, frontend Vitest 84, and
  the production build. The OpenAPI/frontend contract suite contains 68
  passing tests. The existing Vite warning remains for the 575.69 kB main
  JavaScript asset. This is local validation of uncommitted changes, not remote
  GitHub Actions verification.
- Browser E2E passed on 2026-07-14 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-doe-cors`. The first DOE run exposed
  a purpose-helper locator mismatch; the second exposed the existing missing
  CORS `PUT` allowlist entry. After using the catalog label and adding a narrow
  `PUT` allowance plus startup test, the complete rerun passed through DOE
  design creation, nine response values, analysis v0.2.0, two SVGs, ANOVA, and
  diagnostics while preserving every earlier critical-path stage.
- The attribute-control-chart P/NP/C/U slice and the preceding regression
  prediction stabilization were validated locally on 2026-07-14 from a
  working tree based on main SHA
  `3e05a7c32f0fa48830ca22600cbf20f450280244`. Full
  `scripts\check.ps1` passed with backend Ruff/format/mypy over 81 source
  files, backend pytest 500, frontend lint/typecheck, frontend Vitest 82, and
  the production build. The OpenAPI/frontend contract suite contains 62
  passing tests. The existing Vite chunk warning remains for the 563.92 kB
  main JavaScript asset. This is local validation of uncommitted changes, not
  remote GitHub Actions verification.
- Browser E2E passed on 2026-07-14 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
  -DiagnosticsRoot .\.tmp\e2e-diagnostics-attribute-chart`. The first run
  stopped at a test-only P/NP partial-name locator ambiguity. Exact P selection
  and the correct two-signal NIST expectation were applied, and the complete
  rerun passed through regression fit/cross-dataset prediction/CSV plus the new
  30-row P-chart execution and rendered-signal checks.
- The prediction performance baseline exercised 1,000, 10,000, and 100,000
  cross-dataset rows through the real API with full page checksum/count/schema
  verification and full CSV creation. It is a benchmark record, not a CI
  pass/fail gate.
- The latest recorded backend pytest count is 603. The latest recorded frontend Vitest count is 93. The latest OpenAPI/frontend contract count is 104.

## Historical Local Validation

- Full regression prediction CSV export passed locally on 2026-07-13. The
  1,005-row streaming export/tamper contract passed, the OpenAPI/frontend
  contract suite passed with 61 tests, full `scripts\check.ps1` passed with
  backend pytest 461 tests and frontend Vitest 63 tests, and browser E2E created
  and downloaded the cross-dataset prediction CSV. The production build retains
  the existing Vite chunk-size warning for the 548.61 kB main JavaScript asset.
- Cross-dataset regression prediction target selection passed locally on
  2026-07-13. The dataset-version catalog privacy/pagination test and
  cross-dataset prediction contract passed, the OpenAPI/frontend contract suite
  passed with 60 tests, full `scripts\check.ps1` passed with backend pytest 460
  tests and frontend Vitest 63 tests, and browser E2E selected a separate
  four-row target version for a real 12-row trained model. The production build
  retains the existing Vite chunk-size warning for the 546.32 kB main
  JavaScript asset.
- Regression prediction paging stabilization passed locally on 2026-07-13.
  Targeted regression prediction API tests passed with 9 selected tests, the
  OpenAPI/frontend contract suite passed with 59 tests, full
  `scripts\check.ps1` passed with backend pytest 458 tests and frontend Vitest
  63 tests, and browser E2E passed with
  `-DiagnosticsRoot .\.tmp\e2e-diagnostics`. The production build retains the
  existing Vite chunk-size warning for the 542.90 kB main JavaScript asset.
- Post-reboot baseline validation on 2026-07-12 passed from clean main commit
  `02d5d4e4fb2e1d8a0ec802177e2ecdf62116a3fa`: bootstrap completed, full
  `scripts\check.ps1` passed with backend pytest 445 tests and frontend Vitest
  59 tests, and browser E2E passed with
  `-DiagnosticsRoot .\.tmp\e2e-diagnostics`. After the Workbench async and prop
  contract changes plus the capability, Gage R&R, Gage Run Chart, DOE
  factorial, and linear-model statsmodels reference slices, targeted frontend
  lint/typecheck passed without warnings,
  frontend Vitest passed with 63 tests, and the frontend/backend contract pytest
  passed with 57 tests. The post-change full `scripts\check.ps1` rerun passed
  with backend pytest 455 tests and frontend Vitest 63 tests, and the
  post-change browser E2E rerun passed with the same diagnostics-root option.
- Full local Windows validation for the current E2E stabilization, Workbench
  state-ownership hook split, CI diagnostics hardening, frontend API facade/type
  split, OpenAPI frontend route/schema field contract guards, and analysis-run
  service boundary guard passed on 2026-07-09 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`.
- That 2026-07-09 run passed backend ruff check, backend ruff format check,
  backend mypy over 79 source files, backend pytest with 438 tests, frontend
  lint, frontend typecheck, frontend Vitest with 59 tests, and frontend
  production build.
- Remote-CI/E2E reliability hardening, CI artifact-scope regression guard,
  remote CI verification checklist and stale-validation wording guards,
  OpenAPI TypeScript generation planning guard, UX/reference documentation
  guard, analysis-run facade boundary guard, and Workbench grouped hook/state
  ownership validation record now includes:
  `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`,
  `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`
  with 56 tests,
  `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py -k "analysis_run_service_boundaries or analysis_runs_facade_keeps_create_dispatch_only"`
  with 2 selected tests, full `scripts\check.ps1` with backend pytest 445 tests and
  frontend Vitest 59 tests, and browser E2E smoke with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`.
- Workbench hook ownership guard expansion also passed on 2026-07-11:
  `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`
  with 56 tests and full `scripts\check.ps1` with backend pytest 445 tests and
  frontend Vitest 59 tests. This expanded the existing guard without changing
  frontend UI behavior.
- Targeted stability validation for CI status wording and run-chart datetime
  order redaction passed on 2026-07-10:
  `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py::test_analysis_run_executes_run_chart_with_datetime_order_column .\backend\tests\unit\test_openapi_frontend_contract.py`
  with 56 tests.
- Targeted validation also passed on 2026-07-09:
  `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`,
  `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py .\backend\tests\unit\test_api_contracts.py::test_analysis_run_service_boundaries_are_split_without_api_drift`,
  `npm --prefix .\frontend run lint`,
  `npm --prefix .\frontend run typecheck`, and
  `npm --prefix .\frontend run test -- --run`.
- Route contract hardening validation also passed on 2026-07-10:
  `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`
  passed with 49 tests, and the full `scripts\check.ps1` rerun passed with
  backend pytest 437 tests and frontend Vitest 59 tests.
- Full local Windows validation for the current Workbench/service
  decomposition, frontend API type split, and frontend API client facade split
  passed on 2026-07-07 with
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`.
- That 2026-07-07 run passed backend ruff check, backend ruff format check,
  backend mypy over 79 source files, backend pytest with 388 tests, frontend
  lint, frontend typecheck, frontend Vitest with 58 tests, and frontend
  production build.
- Full local Windows validation for the current Workbench component split, UX refinement, Playwright E2E smoke, XLSX browser upload coverage, CSV upload/error-recovery coverage, parser option editing coverage, named XLSX sheet selection coverage, CP949 text encoding selection coverage, parser error-recovery coverage, and GitHub Actions E2E job wiring working tree passed on 2026-07-07 with `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`.
- The run passed backend ruff check, backend ruff format check, backend mypy over 75 source files, backend pytest with 387 tests, frontend lint, frontend typecheck, frontend Vitest with 58 tests, and frontend production build.
- The previous documentation mismatch between historical test counts was
  resolved by the dated records below; current counts are maintained only in
  the Local Validation section.
- Opt-in browser E2E validation also passed on 2026-07-10 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`.
  The run printed stage markers and passed without producing failure
  screenshots or HTML snapshots.
- Opt-in browser E2E validation also passed on 2026-07-07 with `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"` after installing Chromium with `.\scripts\e2e.ps1 -InstallBrowsers`.
- The current E2E smoke covers pasted TSV intake, parsing confirmation, dataset version creation, `eda.descriptive`, `hypothesis.two_sample_t`, JSON/CSV/HTML export creation, JSON download, saved-result restore/comparison, schema no-op save without stale marking, actual schema display-name change with stale marking, synthetic `regression.linear_model` fit plus explicit cross-dataset target selection, stored-model prediction preflight/execution and interval rendering, browser XLSX file upload with parsing confirmation, browser CSV file upload, empty-file upload error recovery, parser option editing for header row, missing tokens, and delimiter selection, named XLSX sheet selection, CP949 text encoding selection, missing XLSX sheet recovery, and text decoding failure recovery.
- `scripts/check.ps1` still does not run the browser E2E smoke locally. GitHub Actions now runs the smoke in a separate `e2e` job after the Windows check job.
- Historical note: an earlier WSL-side syntax-only validation could not run
  native Windows commands because Windows interop failed before command
  execution with `UtilAcceptVsock: accept4 failed 110`. That limitation is
  superseded by the 2026-07-09 native Windows validations recorded above.

## Remote GitHub Actions Verification

- On 2026-07-15, `Get-Command gh` confirmed that GitHub CLI is not installed,
  so `gh auth status --hostname github.com` could not start. The requested `gh run
  list`, `gh run view`, and artifact download checks therefore remain
  unavailable.
- Therefore no current run ID/head SHA, Windows/e2e job result/order, or
  `e2e-logs` artifact contents were verified. No artifact download was
  attempted after the CLI prerequisite failed.
- Remote GitHub Actions execution has not been directly verified from this
  environment for the working tree validated from local base `main` commit
  `de72b82fcba02aa69ea9adfdbe198e12f86e9e78`. A successful Git push confirms
  only remote ref transfer; it does not verify the resulting Actions jobs.
- GitHub app checks against that commit returned no PR-filtered workflow runs
  and no legacy commit statuses on 2026-07-10. The available connector endpoint
  is PR-run oriented, so that result is not sufficient to confirm push-triggered
  Actions or the new `e2e` job.
- Unauthenticated GitHub REST access to
  `https://api.github.com/repos/kiwoju-git/Data-analysis-platform/actions/runs?branch=main&per_page=5`
  returned `404 Not Found` again on 2026-07-10, consistent with a private
  repository or unauthenticated access boundary.
- `gh`/`gh.exe` is not installed in the current environment, and no `GH*` or
  `GITHUB*` token environment variable is present, so authenticated run listing
  could not be performed here.
- Branch protection and repository settings were not changed in this PR.
- The remote `windows` job, remote `e2e` job, `needs: windows` execution order,
  `e2e-logs` artifact upload, and GitHub UI `workflow_dispatch` manual-run
  control have not been observed remotely yet from this environment. The
  workflow file contains `workflow_dispatch`; the UI control still needs
  authenticated GitHub UI or `gh` confirmation.

Authenticated GitHub CLI verification commands:

```powershell
gh auth status --hostname github.com
gh run list --repo kiwoju-git/Data-analysis-platform --branch main --workflow ci.yml --limit 5
gh run view <run-id> --repo kiwoju-git/Data-analysis-platform --json status,conclusion,headSha,workflowName,jobs
gh run download <run-id> --repo kiwoju-git/Data-analysis-platform --name e2e-logs --dir "$env:TEMP\datalab-e2e-logs"
```

When inspecting the `gh run view <run-id> --json ...` output or the GitHub run
graph, verify that the `windows` job reached `success`, the `e2e` job exists,
and the `e2e` job started only after `windows` completed successfully. The
workflow encodes that ordering through `needs: windows`; hosted Actions still
needs real-run confirmation.

Manual dispatch can be checked from the GitHub Actions UI by opening the `ci`
workflow and confirming the Run workflow button is available for `main`.
If intentionally testing the trigger from the CLI, use:

```powershell
gh workflow run ci.yml --repo kiwoju-git/Data-analysis-platform --ref main
```

Do not change repository settings, Actions settings, branch protection, or
required checks as part of this PR.

After push, verify these items in GitHub UI:

- The latest workflow run appears for the expected branch or PR.
- The `windows` job starts and completes the PowerShell `scripts/check.ps1` command.
- The `e2e` job starts only after the `windows` job succeeds. In the workflow file this is represented by `needs: windows`; the run graph should show that dependency.
- The `e2e` job installs or restores Chromium and runs `scripts/e2e.ps1`.
- The `e2e-logs` artifact is present even on failure and contains only `logs`, `screenshots`, and `html` diagnostics, not raw workspace data.
- The Actions page exposes a `workflow_dispatch` manual run button for the `ci` workflow.

## Follow-up

- After pushing this PR or main update, verify the latest Actions run in GitHub UI or with an authenticated `gh run list --repo kiwoju-git/Data-analysis-platform --branch main --limit 5`.
- If Actions still does not run on main push, debug repository-level Actions settings outside this code PR.
