# CI Status

Last updated: 2026-07-14

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
- The latest recorded backend pytest count is 564. The latest recorded frontend Vitest count is 86.

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

- On 2026-07-15, `gh --version` failed before any network request because
  GitHub CLI is not installed. The earlier requested `gh auth status` and
  `gh run list` checks therefore remain unavailable.
- Therefore no current run ID/head SHA, Windows/e2e job result/order, or
  `e2e-logs` artifact contents were verified. No artifact download was
  attempted after the CLI prerequisite failed.
- Remote GitHub Actions execution has not been directly verified from this
  environment for the working tree validated from local base `main` commit
  `3e05a7c32f0fa48830ca22600cbf20f450280244`. A successful Git push confirms
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
