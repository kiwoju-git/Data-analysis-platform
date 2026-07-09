# CI Status

Last updated: 2026-07-09

## Workflow Configuration

- Workflow file: `.github/workflows/ci.yml`
- Triggers: `workflow_dispatch`, `pull_request`, and `push` to `main`
- Required runner in file: `windows-latest`
- Runtime setup in file: Python `3.10`, Node `22`
- Main check job command in file: `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`
- Browser E2E job command in file: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1`
- Browser E2E job dependency: runs after the Windows check job succeeds
- Browser install/cache: the `e2e` job sets `PLAYWRIGHT_BROWSERS_PATH` to `${{ runner.temp }}\ms-playwright`, caches that path with `actions/cache@v4`, and installs Chromium with `.\.venv\Scripts\python.exe -m playwright install chromium`
- Browser E2E diagnostics: the `e2e` job runs with `-WorkspaceRoot "${{ runner.temp }}\datalab-e2e" -KeepWorkspace`. The E2E runner writes step markers, backend/frontend logs, and on browser-flow failure the current URL, page title, screenshot, and HTML snapshot. GitHub uploads only `logs\*.log`, `screenshots\*.png`, and `html\*.html` files as the `e2e-logs` artifact with `if: always()`.

This satisfies the current repository-side requirement that main pushes should start the Windows CI workflow and the browser E2E smoke workflow job.

## Local Validation

- Full local Windows validation for the current E2E stabilization, Workbench
  state-ownership hook split, CI diagnostics hardening, frontend API facade/type
  split, OpenAPI frontend route/schema field contract guards, and analysis-run
  service boundary guard passed on 2026-07-09 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`.
- The latest run passed backend ruff check, backend ruff format check, backend
  mypy over 79 source files, backend pytest with 437 tests, frontend lint,
  frontend typecheck, frontend Vitest with 59 tests, and frontend production
  build.
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
- The latest run passed backend ruff check, backend ruff format check, backend
  mypy over 79 source files, backend pytest with 388 tests, frontend lint,
  frontend typecheck, frontend Vitest with 58 tests, and frontend production
  build.
- Full local Windows validation for the current Workbench component split, UX refinement, Playwright E2E smoke, XLSX browser upload coverage, CSV upload/error-recovery coverage, parser option editing coverage, named XLSX sheet selection coverage, CP949 text encoding selection coverage, parser error-recovery coverage, and GitHub Actions E2E job wiring working tree passed on 2026-07-07 with `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`.
- The run passed backend ruff check, backend ruff format check, backend mypy over 75 source files, backend pytest with 387 tests, frontend lint, frontend typecheck, frontend Vitest with 58 tests, and frontend production build.
- The previous documentation mismatch between 267/277/301/311/320/329/338/348/357/361/363/375/377/380/381/382/383/384/385/386/387/388/412/429/435 backend tests is resolved; the latest recorded backend pytest count is 437 and the latest recorded frontend Vitest count is 59.
- Opt-in browser E2E validation also passed on 2026-07-10 with
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`.
  The run printed stage markers and passed without producing failure
  screenshots or HTML snapshots.
- Opt-in browser E2E validation also passed on 2026-07-07 with `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"` after installing Chromium with `.\scripts\e2e.ps1 -InstallBrowsers`.
- The current E2E smoke covers pasted TSV intake, parsing confirmation, dataset version creation, `eda.descriptive`, `hypothesis.two_sample_t`, JSON/CSV/HTML export creation, JSON download, saved-result restore/comparison, schema no-op save without stale marking, actual schema display-name change with stale marking, browser XLSX file upload with parsing confirmation, browser CSV file upload, empty-file upload error recovery, parser option editing for header row, missing tokens, and delimiter selection, named XLSX sheet selection, CP949 text encoding selection, missing XLSX sheet recovery, and text decoding failure recovery.
- `scripts/check.ps1` still does not run the browser E2E smoke locally. GitHub Actions now runs the smoke in a separate `e2e` job after the Windows check job.
- Historical note: an earlier WSL-side syntax-only validation could not run
  native Windows commands because Windows interop failed before command
  execution with `UtilAcceptVsock: accept4 failed 110`. That limitation is
  superseded by the 2026-07-09 native Windows validations recorded above.

## Remote GitHub Actions Verification

- Remote GitHub Actions execution has not been directly verified from this
  environment for this working-tree change because it has not been observed in a
  pushed workflow run here.
- GitHub app checks against the current `origin/main` commit
  `73770ad3cf54af756394301f9e14a2d9c7db7d24` returned no PR-filtered workflow
  runs and no legacy commit statuses. That result is not sufficient to confirm
  push-triggered Actions or the new `e2e` job.
- Public browser/API access to `https://github.com/kiwoju-git/Data-analysis-platform/actions` previously returned no inspectable workflow run here, consistent with a private repository or unauthenticated access boundary.
- `gh`/`gh.exe` is not installed in the current environment, so authenticated run listing could not be performed here.
- Branch protection and repository settings were not changed in this PR.
- The new `e2e` workflow job has not been observed remotely yet because it requires a push or pull request workflow run after this working-tree change.

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
