# CI Status

Last updated: 2026-07-24

## Local Validation

- The dataset-cleanup/project-overview feature branch is based on pushed main
  `fd7612c028e7a1067003f8fc686c3704cc2ed1dd`; feature commits
  `c0df903` and `5a79322` contain schema-16 archive visibility, operational
  schema-3 dependency/cascade retention, `/project`, and `Statistical Twin`.
  Final development validation on 2026-07-24 passed tutorial Markdown block
  verification 18, Ruff/format over 167 Python files, mypy over 104 source
  files, backend pytest 838, frontend lint/typecheck and Vitest 187,
  OpenAPI/frontend contracts 171, and production build. `scripts/check.ps1`
  completed in 988.8 seconds.
- The real-API tutorial smoke passed all 18 sections in 18.7 seconds. The final
  Chromium critical-path E2E passed in 90.0 seconds on isolated ports. It
  verifies `Statistical Twin`, `/project` navigation, active state, lazy chunk,
  ID-only query preservation, reload, and the single-workspace explanation,
  while retaining the existing upload, saved-result, export, Predict,
  Optimizer, quality, DOE, Bayesian, management, and lazy-route paths.
- The build measured main at 505.70 kB / 124.30 kB gzip, Project at
  6.23/1.89 kB, Manage at 25.67/6.75 kB, Report at 38.97/8.67 kB, Regression
  at 59.62/13.33 kB, Quality at 67.05/12.82 kB, DOE at 111.15/26.25 kB, and
  Help at 18.40/6.47 kB. Main remains above Vite's 500 kB warning threshold;
  no unsafe split or dependency was added to conceal it.
- `scripts/bootstrap.ps1` completed its locked Python install but its `npm ci`
  step could not replace the Rolldown native binding because a user-owned Vite
  process was still using the frontend dependency tree. That process was not
  terminated. The same lockfile was restored without source or lockfile
  changes, and the complete check/build then passed. This bootstrap run is
  recorded as failed, not passed.
- The first full check collected 838 backend tests and stopped at one stale
  exact-dictionary fixture after 837 passed; the fixture was updated for the
  schema-16 `archived` fields and its 30-test file passed before the complete
  838-test rerun above.
- The measured host remains Windows 10 Home build 19045, CPython 3.10.11, and
  Node 24.17.0. Any passing result from this host is development evidence, not
  the Windows 11/Python 3.10/Node 22 release gate.
- Current-main hosted Actions status is not inferred from local results. The
  branch must be pushed before a matching main run can exist; the most recent
  previously recorded hosted status remains in the history below.

- The usability/retention/run-chart/ZIP feature branch based on pushed main
  `e6f74f031daaa5208eac77f8beba35b427d44d9d` passed the final development
  validation on 2026-07-23. `scripts/check.ps1` took 945.9 seconds: tutorial
  Markdown blocks 18, Ruff/format over 166 Python files, mypy over 103 source
  files, backend pytest 829, frontend lint/typecheck and Vitest 185, direct
  OpenAPI/frontend contracts 168, and production build.
- The real-API tutorial smoke passed all 18 sections in 18.7 seconds. The final
  Chromium critical path passed in 88.3 seconds and includes descriptive quick
  histogram/boxplot, five persistent boxplot labels, Run Chart four-card
  approximate randomness output, dataset creation time, Report inline actions,
  Help method focus, and all retained Predict/Optimizer/Bayesian/retention/
  upload/lazy-route paths.
- The production build measured main at 503.51 kB / 123.84 kB gzip, Report at
  39.01/8.67 kB, Regression at 59.65/13.36 kB, Manage at 20.35/5.38 kB,
  Quality at 67.05/12.82 kB, DOE at 111.16/26.24 kB, and Help at 18.40/6.47
  kB. Main remains above Vite's 500 kB warning threshold; no unsafe split or
  dependency was added to hide it.
- The measured host is Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0. This is development evidence, not Windows 11/Python 3.10/Node 22
  release evidence.
- Hosted PR run `29995284572` for feature head
  `5268797d295d538062f1d3407965e652c707cb04` passed the `windows` job and its
  dependent `e2e` job. The `e2e-logs` artifact exists with size 5,302 bytes
  and digest
  `sha256:1beca9635146c31daea4662d730caa803a540803c5066046d2e1bedc7c30a16a`.
  The connector confirmed artifact metadata but did not download the archive,
  so its internal file list/content is not claimed as independently inspected.

- The runtime-compatibility and compact-history worktree based on pushed main
  `6cc097a6f3d2983feab1fd7e4ccc2c5ab16f765d` passed `scripts/check.ps1` on
  2026-07-23. The final rerun after hosted-Windows fixture stabilization took
  917.7 seconds: tutorial Markdown blocks 18, Ruff/format over
  166 Python files, mypy over 103 source files, backend pytest 818, frontend
  lint/typecheck and Vitest 175, direct OpenAPI/frontend contracts 167, and
  production build. The real-API tutorial smoke passed all 18 sections in
  19.2 seconds. Chromium critical-path E2E passed in 84.9 seconds after the
  runtime request was kept CORS-safelisted and obsolete full-history test
  selectors were moved to the compact/Report Center flow.
- The build measured main at 498.08 kB / 122.23 kB gzip, Report at 35.60/7.87
  kB, Regression at 59.66/13.35 kB, Manage at 15.61/4.30 kB, Quality at
  64.25/11.97 kB, DOE at 111.16/26.24 kB, and Help at 18.01/6.28 kB. Main is
  below Vite's 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0. This is development worktree evidence, not Windows 11/Python
  3.10/Node 22 release evidence. `bootstrap.ps1` was not rerun because the
  reproduced user-owned old Vite process still uses this checkout's
  `node_modules`; reinstalling under that live process would violate the
  no-interference boundary. Locked dependencies were exercised by every
  passing check above.
- `gh` is not installed, so no installation was attempted and the new main
  push's remote run cannot be recorded until after push. Hosted status is not
  inferred from local validation.

- The normality/interactivity/asset-management revision based on pushed main
  `7d30ad0899ba11c14dbd0c4053041ddc7dcf2a15` contains `eda.normality`
  `0.2.0`/schema 2, interactive EDA charts, SQLite schema 15 user metadata,
  route-lazy `/manage`, dependency-safe dataset-version deletion, and compact
  method-help placement. `scripts/check.ps1` passed in 849.1 seconds on
  2026-07-22: Ruff/format over 164 Python files, mypy over 102 source files,
  backend pytest 810, frontend lint/typecheck and Vitest 163, direct
  OpenAPI/frontend contracts 164, 18 tutorial Markdown blocks, and production
  build. The separate real-API tutorial smoke passed all 18 sections in 17.5
  seconds, and Chromium E2E passed in 77.7 seconds after one test-selector
  correction. This is pre-commit development worktree evidence; clean pushed
  SHA evidence is the hosted run recorded in the remote section.
- The production build measured main at 513.58 kB / 124.25 kB gzip,
  Regression at 59.66/13.35 kB, Manage at 15.14/4.15 kB, Quality at
  64.25/11.97 kB, DOE at 111.15/26.22 kB, Help at 18.01/6.28 kB, and Report at
  12.03/3.42 kB. Exploration remains in main rather than a separate route
  chunk. Vite's main-chunk warning is open; no dependency or unsafe split was
  introduced to conceal it.
- The measured host is Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0. This is not Windows 11/Python 3.10/Node 22 release evidence.

- The active-dataset and interactive-regression worktree based on pushed main
  `baf3372975c115cfb2c64566e727b31c58623b4d` passed
  `scripts/check.ps1` in 878.7 seconds on 2026-07-21: Ruff/format over 160
  Python files, mypy over 101 source files, backend pytest 784, frontend
  lint/typecheck and Vitest 158, OpenAPI/frontend contracts 155, 18 tutorial
  Markdown blocks, and production build. The real-API tutorial smoke separately
  passed all 18 sections in 17.8 seconds. This is pre-commit development
  evidence for the current revision, not a clean pushed-SHA claim.
- The production build measured main at 503.55 kB / 120.70 kB gzip and
  Regression at 64.59 kB / 14.84 kB gzip. Quality is 64.25/11.97 kB, DOE is
  111.16/26.23 kB, Help is 18.01/6.29 kB, and Report is 12.04/3.42 kB. The
  global dataset selector and regression interaction foundation caused main to
  cross Vite's 500 kB warning threshold again; measured module extraction is a
  follow-up, not a reason to remove the workflow.
- A final isolated Chromium critical path passed in 79.8 seconds with
  diagnostics under `.tmp/e2e-diagnostics`. It covers ID-only active dataset
  switching/reload, grouped Predict mapping and training-range warnings,
  Observed vs Fitted, pointer/keyboard diagnostic details, and all retained
  Help/Report/Paste/quality/DOE/Bayesian/retention paths.
- The measured host remains Windows 10 Home build 19045, CPython 3.10.11, and
  Node 24.17.0. These results are development evidence, not Windows 11/Python
  3.10/Node 22 release evidence.
- Clean pushed-main closure: local `main`, `origin/main`, and the remote main
  ref resolved to `7e11d08e91b664417b3eb4eb4d2a980fae8ec8b1` with an empty
  working tree on 2026-07-20. `scripts/bootstrap.ps1` passed in 26.1 seconds;
  the locked Python environment was consistent and `npm ci` reported zero
  vulnerabilities.
- On that clean pushed commit, `scripts/check.ps1` passed in 834.6 seconds:
  Ruff/format over 160 Python files, mypy over 101 source files, backend pytest
  784, frontend lint/typecheck and Vitest 152, OpenAPI/frontend contracts 155,
  18 tutorial Markdown blocks, and production build. The separate real-API
  tutorial smoke passed all 18 sections in 18.7 seconds.
- The latest recorded backend pytest count is 818.
- The latest recorded frontend Vitest count is 175.
- The latest OpenAPI/frontend contract count is 167.
  These counts describe the current fully collected validation suites; the
  final command result and commit SHA are stated in the first entry above.
- The clean pushed commit results are local development evidence, not
  remote Actions or Windows 11/Node 22 release evidence.
- Route splitting reduced main from 532.53 kB / 127.56 kB gzip to 496.98 kB /
  118.70 kB. Current assets are Help 18.01/6.29 kB, Report 12.04/3.42 kB,
  shared latest-request 7.36/1.81 kB, Regression 55.14/12.01 kB, Quality
  64.25/11.97 kB, DOE 111.16/26.23 kB, and dedicated-result restore
  0.71/0.32 kB. The main asset no longer emits the 500 kB warning.
- Current Chromium E2E passed in 78.1 seconds with diagnostics at
  `.tmp/e2e-diagnostics-bayesian-p0-final-sha`. It covers Predict `prediction_id` and Optimizer
  `optimization_id` stored-result reload, dedicated generic-history/export
  scoping, Report Center HTML generation/download, Help Center route/reload,
  separate Help/Report resource loading, selected-method context help, plus all
  existing paste, prediction/export, quality, DOE, Bayesian, and retention
  paths. The Bayesian path records and reloads exact study/recommendation IDs.
- The catalog benchmark used full graph validation and page size 20. Three-run
  medians for 20/100/500 Study catalogs are recorded in
  `docs/bayesian_catalog_performance.md`; this is descriptive development
  evidence, not a cache or release threshold.
- The measured host is Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0. These are development results, not Windows 11/Python 3.10/Node 22
  release evidence. The Windows 11/Node 22 clean release gate remains open.
- `gh auth status --hostname github.com` and the requested `gh run list` could
  not run because `gh` is not installed. No installation was attempted.
  No latest run ID/head SHA, hosted Windows/E2E job result/order, artifact
  contents, or workflow-dispatch UI was independently verified.

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

## Recent Local Validation History

- The paste staging/canonical preview slice was validated on 2026-07-17 from
  an uncommitted worktree based on pushed main SHA
  `702e20f0ed1a377d411cb8d7d3a6faa2c4fcbd6f`. Full `scripts/check.ps1`
  passed in 769.0 seconds with backend pytest 763, frontend Vitest 131,
  OpenAPI/frontend contracts 148, Ruff/format, mypy, lint/typecheck, and build.
  Final Chromium E2E passed in 70.8 seconds on `8030`/`5230` with diagnostics
  at `.tmp/e2e-diagnostics`.
- The final assets were 508.32 kB / 120.48 kB gzip for main, 46.75 kB / 9.69
  kB for Regression, 64.25 kB / 11.97 kB for Quality, and 90.79 kB / 20.77 kB
  for DOE. Main emitted the 500 kB Vite warning. The measured host was Windows
  10 Home build 19045, CPython 3.10.11, and Node 24.17.0, so this is development
  evidence and not the Windows 11/Node 22 release gate.
- The first final-E2E attempt on defaults stopped before application flow due
  to an existing port-8000 listener; port 5242 was separately denied by Windows
  bind permissions. The stable-port run above is the passing application result.

- The regression-model and attribute-control-limit-set deletion slice was
  validated locally on 2026-07-17 from an uncommitted working tree based on
  main SHA `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Final
  `scripts\check.ps1` passed in 781.8 seconds with Ruff/format over 158 Python
  files, mypy over 101 source files, backend pytest 750, frontend
  lint/typecheck, frontend Vitest 111, and production build. The direct
  OpenAPI/frontend contract suite contains 150 tests and passed.
- The clean final Chromium E2E passed in 99.3 seconds on `8031`/`5231` with
  workspace `.tmp\e2e-workspace-asset-retention-final-3` and diagnostics root
  `.tmp\e2e-diagnostics-asset-retention-final-3`. It verifies regression-model
  deletion is blocked by one stored prediction and attribute-control-limit-set
  deletion is blocked by one Phase II run, while retaining every earlier
  upload, prediction/export, Phase I/II, DOE, Bayesian, and retention path.
  Two preliminary browser runs reached these new controls but failed only
  ambiguous/partial Playwright selectors; both selectors were scoped exactly
  before the clean passing run.
- Final production assets are 490.15 kB / 114.58 kB gzip for main, 44.86 kB /
  9.23 kB for Regression, 63.97 kB / 11.88 kB for Quality, and 90.79 kB /
  20.77 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This is development evidence, not the required Windows 11 /
  Python 3.10 / Node 22 release evidence. Remote Actions verification is
  recorded separately and is not inferred from local checks or a Git push.

- The analysis-run root deletion slice was validated locally on 2026-07-17
  from an uncommitted working tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Final
  `scripts\check.ps1` passed in 792.7 seconds with Ruff/format over 156 Python
  files, mypy over 100 source files, backend pytest 738, frontend
  lint/typecheck, frontend Vitest 109, and production build. The direct
  OpenAPI/frontend contract suite contains 139 tests.
- The first full run completed 737 of 738 backend tests and failed only the
  documentation guard because the newly added E2E step marker was not yet in
  `docs/e2e_coverage.md`. After synchronizing the marker and adding the final
  prediction-dependency blocker, the complete final run above passed.
- The first browser run successfully deleted the run and cleared restore/
  comparison state, then failed an incorrect assertion that expected the
  previously selected t-test table while the restored method selection was
  descriptive. That assertion was removed. The clean final Chromium E2E passed
  in 66.5 seconds on `8031`/`5231` with workspace
  `.tmp\e2e-workspace-analysis-run-retention-final` and diagnostics root
  `.tmp\e2e-diagnostics-analysis-run-retention-final`.
- Final production assets are 487.56 kB / 114.21 kB gzip for main, 41.53 kB /
  8.37 kB for Regression, 62.14 kB / 11.48 kB for Quality, and 90.79 kB /
  20.76 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This is development evidence, not the required Windows 11 /
  Python 3.10 / Node 22 release evidence. Remote Actions verification is
  recorded separately and is not inferred from local checks.

- The individual analysis-export file-retention slice was validated locally on
  2026-07-16 from an uncommitted working tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Full
  `scripts\check.ps1` passed in 746.7 seconds with Ruff/format over 154 Python
  files, mypy over 99 source files, backend pytest 731 tests, frontend
  lint/typecheck, frontend Vitest 105 tests, and production build. The direct
  OpenAPI/frontend contract suite passed 137 tests.
- The complete Chromium E2E passed in 59.9 seconds on ports `8031`/`5231` with
  workspace `.tmp\e2e-workspace-analysis-export-retention` and diagnostics root
  `.tmp\e2e-diagnostics-analysis-export-retention`. It creates three stored
  result exports, downloads JSON, reviews and confirms deletion of one export,
  verifies the list shrinks while the parent analysis result remains, and
  retains every prior prediction, Phase I/II, DOE, Bayesian, parser-recovery,
  and lazy-panel path.
- Production assets are 480.68 kB / 112.99 kB gzip for main, 41.53 kB /
  8.36 kB for Regression, 62.14 kB / 11.48 kB for Quality, and 90.79 kB /
  20.76 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This is development evidence, not Windows 11/Python 3.10/Node
  22 release evidence. `gh auth status` and `gh run list` could not run because
  `gh` is not installed, so remote Actions and artifacts remain independently
  unverified.

- The closed Bayesian study metadata-deletion slice was validated locally on
  2026-07-16 from an uncommitted working tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Full
  `scripts\check.ps1` passed in 764.9 seconds with Ruff/format over 153 Python
  files, mypy over 99 source files, backend pytest 721 tests, frontend
  lint/typecheck, frontend Vitest 102 tests, and production build. The direct
  OpenAPI/frontend contract suite passed 131 tests.
- The complete Chromium E2E passed in 62.2 seconds on ports `8031`/`5231` with
  workspace `.tmp\e2e-workspace-bayesian-retention-final` and diagnostics root
  `.tmp\e2e-diagnostics-bayesian-retention-final`. It retains every prior flow
  and adds closed-study deletion impact review, exact confirmation, and catalog
  removal. Preliminary launches on `5232` and `8040` were denied by Windows
  socket-bind permissions before application/browser execution; they are not
  test failures and the clean final run passed.
- Production assets are 474.80 kB / 111.96 kB gzip for main, 41.53 kB /
  8.37 kB for Regression, 62.14 kB / 11.48 kB for Quality, and 90.79 kB /
  20.76 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This remains development evidence, not Windows 11/Python 3.10/
  Node 22 release evidence. `gh auth status` and `gh run list` could not run
  because `gh` is not installed, so remote Actions remain independently
  unverified.

- The Bayesian study close/abandon lifecycle slice was validated locally on
  2026-07-16 from an uncommitted working tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Full
  `scripts\check.ps1` passed in 734.4 seconds with Ruff/format over 153 Python
  files, mypy over 99 source files, backend pytest 712 tests, frontend
  lint/typecheck, frontend Vitest 101 tests, and the production build. The
  direct OpenAPI/frontend contract suite remains 120 tests and passed within
  the full backend run; a lifecycle/Bayesian/OpenAPI targeted run passed 189
  tests.
- The complete Chromium E2E passed in 58.6 seconds on ports `8031`/`5231` with
  workspace `.tmp\e2e-workspace-bayesian-study-close` and diagnostics root
  `.tmp\e2e-diagnostics-bayesian-study-close`. The Bayesian path now records
  the final recommendation observation, closes the study as completed through
  inline confirmation, verifies read-only controls, and restores the lifecycle
  event after reload while retaining all previous critical paths.
- Production assets are 473.59 kB / 111.64 kB gzip for main, 41.53 kB /
  8.36 kB for Regression, 62.14 kB / 11.48 kB for Quality, and 87.24 kB /
  20.00 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This remains development evidence, not the required Windows
  11/Python 3.10/Node 22 release evidence. `gh auth status` and `gh run list`
  could not run because the `gh` executable is not installed, so remote Actions
  and artifacts remain independently unverified.

- The Phase II frozen-limit attribute-control-chart vertical slice was
  validated locally on 2026-07-16 from an uncommitted working tree based on
  main SHA `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Full
  `scripts\check.ps1` passed with Ruff/format over 152 Python files, mypy over
  99 source files, backend pytest 702 tests, frontend lint/typecheck, frontend
  Vitest 100 tests, and the production build. The direct OpenAPI/frontend
  contract suite contains 120 tests and passed.
- The complete browser E2E passed in 58.1 seconds on ports `8030`/`5230` with
  workspace `.tmp\e2e-workspace-attribute-phase2` and diagnostics root
  `.tmp\e2e-diagnostics-attribute-phase2`. It creates a stable Phase I P-chart
  baseline, promotes the verified app-created limit set, uploads a separate
  monitoring dataset, passes the Phase II compatibility preflight, executes
  frozen-limit monitoring, and verifies the immutable source identity in the
  result while retaining every prior critical path.
- Production assets are 472.13 kB / 111.23 kB gzip for main, 41.53 kB /
  8.37 kB for Regression, 62.14 kB / 11.48 kB for Quality, and 79.80 kB /
  18.32 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This is development evidence, not Windows 11/Python 3.10/Node
  22 release evidence; that clean environment remains a mandatory release
  gate. The `gh` command is not installed in this environment, so remote
  GitHub Actions jobs and artifacts were not independently verified.

- The Bayesian lifecycle-correctness stabilization was validated locally on
  2026-07-16 from an uncommitted working tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Full
  `scripts\check.ps1` passed with Ruff/format over 150 Python files, mypy over
  98 source files, backend pytest 687 tests, frontend lint/typecheck, frontend
  Vitest 98 tests, and production build. The OpenAPI/frontend contract suite is
  117 tests and passed in a separate direct run.
- Production assets are 467.18 kB / 110.05 kB gzip for main, 41.53 kB /
  8.36 kB for Regression, 59.29 kB / 10.79 kB for Quality, and 79.80 kB /
  18.32 kB for DOE. No JavaScript asset exceeds the 500 kB warning threshold.
- The first full run completed 685 tests and failed one stale contract assertion
  that still expected Bayesian method `0.2.0`. After changing that method-source
  assertion to `0.2.1`, its targeted file passed 5 tests and the complete second
  run passed all 686 backend tests. A final restore-boundary review then limited
  recommendation versions to executable `0.2.0/0.2.1`; its 36-test compatibility
  suite and the final full run passed all 687 backend tests. These were not
  disk-space failures.
- The initial targeted Bayesian/OpenAPI backend run passed 155 tests, and the
  follow-up restore-boundary suite passed 36 tests. Frontend
  lint/typecheck and all 98 Vitest tests passed. The lifecycle-expanded browser
  E2E first passed on ports `8027`/`5227`, then the final full critical path
  passed in 57.9 seconds on ports `8028`/`5228`. After the final recommendation
  restore-boundary review, the complete path passed again in 56.8 seconds on
  ports `8029`/`5229` with workspace
  `.tmp\e2e-workspace-bayesian-lifecycle-final` and diagnostics root
  `.tmp\e2e-diagnostics-bayesian-lifecycle-final`.
- The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0. This is development evidence, not Windows 11/Python 3.10/Node
  22 release evidence. That clean environment remains a mandatory release gate.
  Remote GitHub Actions verification is recorded separately below.
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
- The latest recorded backend pytest count is 750. The latest recorded frontend Vitest count is 111. The latest OpenAPI/frontend contract count is 150.

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

- Push run `29945533976` verified exact main SHA
  `8002d6dcff43573301b596a1888acf69f3da570b`. Hosted `windows` completed
  successfully, and the dependent `e2e` job then completed successfully; every
  bootstrap, check, browser smoke, and upload step reported success.
- The non-expired `e2e-logs` artifact is ID `8540492802`, 5,136 bytes, with
  digest `sha256:325f9380482101a94f7aa4c412a4c4c42edee406234c73658974cad6d3edab4f`.
  Authenticated connector inspection found only `logs/backend.log`,
  `logs/e2e-diagnostics.log`, and `logs/frontend.log`. No workspace/data file,
  absolute path, canonical JSONL, prediction-row JSONL, or metadata SQLite
  marker was present.
- Push run `29942544577` checked exact main SHA
  `b4cd7115660d66097994ba039a9462c73fdd2a4a` on hosted Windows Server 2025,
  CPython 3.10.11, and Node 22.23.1. Bootstrap succeeded; `Check` failed with
  815/818 backend tests passed, so the dependent E2E job correctly did not run.
- The three failures were test-boundary issues, not production calculation
  changes: a rollback test used a platform-sensitive perfect linear fit, a
  large reference sum used only `1e-12` absolute tolerance, and the CI document
  guard still expected the previous 810/163/164 counts. The cleanup fixture is
  now non-perfect, the reference comparison uses explicit relative plus
  absolute tolerance, and the guard tracks 818/175/167. The three targeted
  tests passed locally, followed by the complete 818-test check above.

- Public GitHub Actions REST inspection on 2026-07-22 verified push run
  `29909222867` for main SHA
  `fe1b7c36de0354e319d10038ccc939a612f3ed2e`. The run completed with
  conclusion `success`.
- The hosted `windows` job ran from `2026-07-22T09:45:22Z` through
  `10:00:39Z` and completed successfully. The dependent `e2e` job started at
  `10:00:42Z`, after Windows success, and completed successfully at
  `10:02:52Z`. This directly verifies the configured `needs: windows` order.
- Run artifact metadata reports one non-expired `e2e-logs` artifact,
  ID `8525607052`, size 5,502 bytes. The public metadata endpoint was
  accessible, but archive download returned `401 Unauthorized`; therefore its
  internal entry list and raw-workspace absence were not independently
  inspected in this environment.
- `gh auth status --hostname github.com` and the requested `gh run list` still
  could not be performed here because GitHub CLI is not installed. No install
  was attempted. Public REST metadata was sufficient for run/job/artifact
  existence, but not authenticated artifact download or the GitHub UI
  `workflow_dispatch` button.
- Branch protection and repository settings were not changed in this PR.

### Historical Hosted Runs

- Public GitHub Actions REST/UI inspection on 2026-07-21 verified push run
  `29834082053` for head SHA
  `413dba3e641522ac3238c3d23d54952791aee580`. It failed before creating any
  jobs or artifacts because the workflow used the `runner` context in
  job-level `env` at lines 36-38, where that context is unavailable. This was
  a workflow parse failure, not a Windows check or E2E test result.
- The subsequent workflow revision moved those values to step-level `env`/`with`
  fields while retaining runner-temp browser, workspace, and diagnostics
  paths. The successful run above now supersedes this earlier pending state.
- Follow-up run `29834322001` for `c1e393525e106225de4b194d3cc93fccf29c27d3`
  created the expected `windows` and dependent `e2e` jobs, proving the workflow
  parse fix. `windows` then failed after 782/784 backend tests passed: hosted
  checkout converted the tutorial generator to CRLF and changed its manifest
  SHA, and the E2E artifact guard still expected the previous env-based path
  spelling. The current revision pins that generator to LF in `.gitattributes`
  and updates the guard to require the same runner-temp `logs/screenshots/html`
  scope. `e2e` was correctly skipped because `needs: windows` did not succeed.
- Run `29837897049` for `9112c4e5f9ae988d6117df289d73b8b5a9b24d75`
  passed 783/784 backend tests, including the generator SHA and corrected
  artifact guard. The remaining failure showed that the eight manifest-listed
  tutorial CSV/TSV files also require their declared LF policy during hosted
  Windows checkout. The current `.gitattributes` revision pins those generated
  data files to LF as well; no sample data bytes, formulas, expected results, or
  manifest hashes were changed. `e2e` was again correctly skipped after the
  failed Windows dependency.
- On 2026-07-19, invoking `gh auth status --hostname github.com` and the
  requested `gh run list` command returned
  PowerShell command-not-found error, confirming that GitHub CLI is not
  installed. The requested `gh run list`, `gh run view`, and artifact download
  checks therefore remain unavailable.
- That failed run provided a run ID/head SHA but no Windows/e2e job
  result/order and no `e2e-logs` artifact. Artifact inspection therefore
  remains pending a workflow run that reaches its jobs.
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
- The current remote `windows` job, remote `e2e` job, `needs: windows`
  execution order, and `e2e-logs` artifact existence have now been observed.
  Artifact contents and the GitHub UI `workflow_dispatch` manual-run control
  still need authenticated download/UI confirmation.

Authenticated GitHub CLI verification commands:

```powershell
gh auth status --hostname github.com
gh run list --repo kiwoju-git/Data-analysis-platform --branch main --workflow ci.yml --limit 5
gh run view <run-id> --repo kiwoju-git/Data-analysis-platform --json status,conclusion,headSha,workflowName,jobs
gh run download <run-id> --repo kiwoju-git/Data-analysis-platform --name e2e-logs --dir "$env:TEMP\datalab-e2e-logs"
```

When inspecting the `gh run view <run-id> --json ...` output or the GitHub run
graph, verify that the `windows` job reached `success`, the `e2e` job exists,
and the `e2e` job started only after `windows` completed successfully. Run
`29909222867` provides that hosted confirmation for this push.

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
