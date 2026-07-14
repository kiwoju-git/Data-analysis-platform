# Browser E2E Coverage

This document describes what the current Playwright smoke covers, how to run it,
and how to inspect failures. It is an operations and coverage note, not a
statistical-method expansion plan.

## Covered Flows

The current smoke test is `tests/e2e/critical_path.py`.

- Starts the FastAPI backend on `127.0.0.1` and the Vite frontend on
  `127.0.0.1`.
- Uses a synthetic pasted TSV dataset with `Group` and `Value` columns.
- Confirms parsing options and creates dataset version `v1`.
- Verifies the dataset context bar row/column counts.
- Runs `eda.descriptive` and waits for the result table.
- Switches to `hypothesis.two_sample_t`, runs it, and waits for the Hedges g
  result row.
- Creates JSON, CSV, and HTML stored-result exports.
- Downloads the JSON export and verifies the suggested filename is `.json`.
- Opens saved analysis history, restores a stored result, selects left/right
  saved runs, and renders comparison output.
- Saves schema metadata with no actual change and verifies saved runs are not
  marked stale.
- Changes a display name and verifies saved runs become stale.
- Registers a second synthetic `y`/`x`/`group` TSV dataset, selects
  `regression.linear_model`, explicitly assigns response/predictor roles, and
  fits a real treatment-coded OLS model.
- Registers a separate compatible four-row target dataset version, selects it
  from the prediction target catalog, and verifies `prediction_ready` with all
  four target rows usable despite a different schema hash.
- Executes real cross-dataset backend prediction, retrieves the first stored-result
  page, and verifies the four-row summary, predicted mean/mean-CI/prediction-interval
  table, and four rendered interval lines.
- Generates a full stored prediction CSV and verifies the browser starts a
  `.csv` download through the checksum-validated analysis export route.
- Registers the published NIST 30-point defectives/sample-size fixture, opens
  `quality.attribute_control_chart`, executes a P chart, and verifies the
  30-row summary, two strict 3-sigma signals, accessible SVG chart, and first
  25 displayed point rows.
- Creates a deterministic replicated 2-factor DOE with one center point, saves
  all nine response values, runs the dedicated factorial analysis, and verifies
  method v0.2.0, effect and main-effect SVGs, ANOVA table, and diagnostics.
- Creates a deterministic 13-run rotatable CCI, saves every response, fits the
  dedicated full quadratic response-surface model, and verifies the contour
  SVG, coefficient table, fit summary, and diagnostics.
- Runs the bounded Response Optimizer from that verified RSM result and checks
  the recommended factor settings, point prediction, individual/composite
  desirability, constraint status, search termination, confirmation-run
  warning, and explicit absence of a global-optimum guarantee.
- Uploads a synthetic XLSX file in the browser and confirms parsing.
- Uploads an empty CSV to verify upload error recovery, then uploads a valid
  synthetic CSV.
- Edits parser options for header row and missing tokens.
- Edits delimiter selection for a semicolon-delimited file.
- Selects a named XLSX worksheet after first verifying missing-sheet recovery.
- Selects CP949 encoding after first verifying UTF-8 decoding failure recovery.

## Current Step Markers

`tests/e2e/critical_path.py` currently prints these major step markers in order:

- `wait for backend health`
- `wait for frontend dev server`
- `open Workbench`
- `paste synthetic TSV and confirm schema`
- `run descriptive statistics`
- `run two-sample t test`
- `create and download exports`
- `restore and compare saved results`
- `verify schema stale behavior`
- `verify linear model fit and prediction`
- `verify attribute control chart`
- `verify DOE factorial analysis`
- `verify DOE response surface analysis and optimization`
- `verify XLSX browser upload`
- `verify CSV upload and upload error recovery`
- `verify parser option editing`
- `verify delimiter option editing`
- `verify XLSX sheet selection recovery`
- `verify CP949 encoding selection recovery`

## Not Covered

- Remote GitHub Actions status or branch protection settings.
- Full OpenAPI-to-TypeScript generation.
- Every available statistical method panel.
- Bayesian optimization, non-normal capability, advanced Gage R&R, or
  fractional-factorial alias analysis.
- Chart export artifacts.
- Browser matrix coverage beyond Chromium.
- Large dataset performance or memory budget E2E.
- Network-disconnected runtime validation after dependencies are installed.
- Accessibility audits beyond the assertions embedded in current component
  tests.

## Known Flake Risks

- Vite startup and backend startup can race with the browser if the host runner
  is slow.
- Playwright browser install/cache behavior may vary on first CI run.
- Text labels are currently matched through existing UI copy; copy changes can
  break the smoke even when behavior is intact.
- The smoke performs many sequential flows in one browser session, so an early
  state leak can affect later assertions.
- Windows file locking can delay cleanup of temporary browser upload files.
- A failed assertion late in the flow can be hard to locate without step-aware
  diagnostics, so screenshots and HTML snapshots include the current step slug
  in their filenames.
- Backend or frontend startup failures can otherwise look like generic readiness
  timeouts, so the runner prints the exited process name and recent log tail
  when a process exits early, and prints recent backend/frontend log tails when
  a readiness URL times out while processes are still running.

## Run Locally

Install dependencies first:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

Install Chromium for Playwright:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -InstallBrowsers
```

Run the smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1
```

Run on custom ports:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -BackendPort 8012 -FrontendPort 5200
```

Keep the workspace and diagnostics:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -WorkspaceRoot "$env:TEMP\datalab-e2e" -KeepWorkspace
```

Write diagnostics to a separate directory:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -WorkspaceRoot "$env:TEMP\datalab-e2e" -DiagnosticsRoot "$env:TEMP\datalab-e2e-diagnostics" -KeepWorkspace
```

## Inspect Logs

Each run writes:

- `logs/e2e-diagnostics.log`
- `logs/backend.log`
- `logs/frontend.log`
- `screenshots/failure-{step}-{timestamp}.png` on browser-flow failure
- `html/failure-{step}-{timestamp}.html` on browser-flow failure

The diagnostics log records UTC timestamps and the same step markers printed to
the console, such as `[e2e] run descriptive statistics`, to make CI failures
easier to scan even when stdout is noisy. Failure artifact paths in this log are
relative to the diagnostics root. Playwright wait timeouts include the current
step, current URL, and page title before the screenshot/HTML capture path is
printed. If the backend or frontend process exits during readiness waits, the
runner prints that process name, exit code, and recent log tail. If readiness
times out while the processes are still running, the runner records the timed-out
URL and prints recent backend/frontend log tails.

CI uses separate workspace and diagnostics roots. It uploads only diagnostics
under `logs`, `screenshots`, and `html` as the `e2e-logs` artifact. It does not
upload raw workspace files or generated dataset artifacts. The current smoke
uses synthetic data only; do not point this smoke at private user data.

## Maintenance Checklist

When extending `tests/e2e/critical_path.py`:

- Add a `diagnostics.step(...)` marker before each major browser action or
  process wait so failure screenshots and HTML snapshots include a meaningful
  step slug.
- Keep fixture data synthetic and small enough to inspect in logs without
  exposing private records.
- Keep workspace output and diagnostics output separate. CI artifacts must stay
  limited to diagnostics-root `logs`, `screenshots`, and `html` paths.
- Preserve URL/title reporting on Playwright wait timeouts and process log-tail
  printing for backend/frontend early exits and readiness timeouts.
- Prefer stable user-visible labels already asserted by component tests. If UI
  copy changes intentionally, update the E2E step name and the relevant
  usability checklist in the same change.
