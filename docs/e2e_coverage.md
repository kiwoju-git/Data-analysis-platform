# Browser E2E Coverage

This document describes what the current Playwright smoke covers, how to run it,
and how to inspect failures. It is an operations and coverage note, not a
statistical-method expansion plan.

## Latest Local Run

The 2026-07-19 tutorial-truth/Help/Report worktree run passed in 77.3 seconds
with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 `
  -DiagnosticsRoot .\.tmp\e2e-diagnostics
```

The run first dispatches a real `text/plain` spreadsheet paste while providing
ignored clipboard HTML. It reviews empty/ragged cells, uses keyboard cell
navigation and the inspector, captures exact CRLF-preserving API content on an
intentional failure, verifies the failed draft remains in the current page,
reloads to prove it was not persisted, registers the real dataset, and verifies
successful raw clearing. After parsing it changes canonical page size, selects
a full-value cell, and reloads the confirmed version. It then verifies that a
stored prediction blocks deletion of its
regression model. It then deletes the prediction through its reviewed analysis
ownership graph, deletes the now-unreferenced model, reloads the app, restores
the preserved fit result, and verifies that model availability remains
unavailable and all prediction actions stay disabled. It also runs a one-point
Phase II chart, displays unavailable dispersion, creates JSON/CSV/HTML exports,
restores the saved result, and confirms the limit-set dependency blocker. Both
impact panels remain path/raw-value free. The run also retains
individual export deletion, then restores and compares two
analysis runs, reviews and separately confirms deletion of the dependency-free
run, verifies history shrinks from two to one, and verifies deleted restore and
comparison state are cleared. It then verifies no-op and real schema changes
against the remaining run. It also verifies
explicit initial-observation confirmations, a pending GP/EI
recommendation, actual-observation completion and completed status, an
abandoned recommendation that is not repeated, effective trial-budget blocking,
latest recommendation restore, completed close, read-only state, lifecycle
restore after reload, deletion impact counts, separate irreversible
confirmation, and catalog removal. It also retains the existing
Phase I/II attribute charts, prediction/export, Factorial, RSM/Optimizer,
parser-recovery, and lazy-panel paths. The current run additionally opens and
reloads the Help and Report Center routes, creates and downloads an HTML report
through the existing generic export API, verifies unsupported dedicated report
formats, and opens/closes selected-method context help. The final run above was
a single application run on the E2E script's isolated default ports.

## Covered Flows

The current smoke test is `tests/e2e/critical_path.py`.

- Starts the FastAPI backend on `127.0.0.1` and the Vite frontend on
  `127.0.0.1`.
- Dispatches a real browser `ClipboardEvent` with a synthetic `text/plain` TSV
  plus ignored clipboard HTML. Before registration it verifies the capped grid,
  row/column headers, empty/ragged summaries, full-value inspector, and keyboard
  cell movement.
- Forces one paste API failure and verifies the exact raw draft remains in the
  fallback textarea, then reloads and verifies the draft was not restored from
  browser storage.
- Registers a synthetic pasted TSV dataset with `Group` and `Value` columns and
  verifies successful registration clears the raw textarea.
- Confirms parsing options and creates dataset version `v1`.
- Changes the canonical preview page size to 25, selects a canonical cell,
  verifies the full-value inspector, reloads the app, and restores only the
  confirmed dataset version through backend APIs.
- Verifies the dataset context bar row/column counts.
- Runs `eda.descriptive` and waits for the result table.
- Switches to `hypothesis.two_sample_t`, runs it, and waits for the Hedges g
  result row.
- Creates JSON and CSV stored-result exports in the analysis Workbench.
- Downloads the JSON export and verifies the suggested filename is `.json`.
- Reviews the exact one-file/one-metadata-row deletion impact for the newest
  export, uses the separate irreversible confirmation, verifies the export
  list shrinks from two to one, and confirms the stored analysis result stays
  rendered.
- Opens `/reports`, selects the checksum-validated stored result, creates and
  downloads its HTML report, verifies unsupported dedicated HTML formats remain
  explicitly unsupported, and reloads the route. It then opens and reloads
  `/help`, verifies the purpose helper and role dictionary, returns to analysis,
  and opens/closes the selected-method context help dialog.
- Opens saved analysis history, restores a stored result, selects left/right
  saved runs, and renders comparison output.
- Restores the dependency-free run, reviews its exact two-file/two-metadata-row
  deletion impact, uses a separate irreversible confirmation, verifies history
  shrinks from two runs to one, and verifies deleted restore/comparison state
  is cleared while the unrelated run remains.
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
- Opens the top-level `regression.predict` route, verifies the available
  dedicated badge, selects the stored model and target through their catalogs,
  runs preflight/prediction/CSV creation, records `prediction_id`, and reloads
  the ID-only deep link to verify source selection, stored result rows, and CSV
  restore without recalculation. The extra prediction is removed through the
  reviewed analysis-run deletion contract before model-retention assertions.
- Loads regression-model deletion impact after the prediction exists, verifies
  the dependent-prediction count, and verifies confirmed deletion is disabled.
  It deletes the prediction through exact analysis-run preflight, deletes the
  model, verifies the fit remains rendered while prediction/preflight/CSV are
  disabled, reloads the app, restores the selected dataset version and stored
  fit through validated APIs, and verifies the same unavailable state.
- Creates a stable 20-point P-chart Phase I baseline, closes it through the
  app-created immutable limit-set API, registers a separate one-point monitoring
  dataset, selects the verified asset in the Phase II UI, verifies the
  schema/dependency-only preflight notice, and verifies frozen-limit execution,
  source/close metadata, one-row summary, unavailable dispersion, accessible
  SVG chart, JSON/CSV/HTML exports, and stored-result restore.
- Loads limit-set deletion impact after the Phase II result exists, verifies
  the dependent Phase II count, and verifies confirmed deletion is disabled.
- Creates a deterministic replicated 2-factor DOE with one center point, saves
  all nine response values as response revision 1, runs the dedicated factorial
  analysis, and verifies method v0.3.0, effect and main-effect SVGs, ANOVA table,
  diagnostics, analyzed-response input/save lock, and explicit correction mode.
- Creates a deterministic 13-run rotatable CCI, saves every response, fits the
  dedicated full quadratic response-surface model, and verifies the contour
  SVG, coefficient table, fit summary, diagnostics, and the analyzed-response
  name/unit/value/save lock. Both DOE flows also assert the pre-analysis lock
  warning.
- Runs the bounded Response Optimizer from that verified RSM result and checks
  the recommended factor settings, point prediction, individual/composite
  desirability, constraint status, search termination, confirmation-run
  warning, and explicit absence of a global-optimum guarantee.
- Opens the top-level `regression.response_optimizer` route, selects the stored
  RSM analysis, runs the shared optimizer panel, records `optimization_id`, and
  reloads the ID-only deep link to verify source, eligibility, and stored
  recommendation/desirability restore. Both dedicated routes assert that
  unrelated generic analysis history/export headings are absent.
- Creates RSM response revision 2 through the explicit correction flow after
  analysis and verifies that newest-first revision history retains revision 1.
- Creates a one-factor Bayesian study with an actual-unit upper-bound linear
  constraint and an effective total-trial budget of five, then records two
  explicit synthetic initial observations through immutable-action
  confirmations. It runs the bounded Matérn-5/2 GP/Expected Improvement worker,
  verifies the first candidate is pending, records its actual observation, and
  verifies completed state plus separation of actual and predicted values. It
  creates and abandons a second recommendation through confirmation, verifies a
  third candidate does not repeat the abandoned coordinates, verifies the
  budget-reached blocker, reloads the page, and restores the actual latest
  pending recommendation and its request budget. It then records the final
  confirmation observation, closes the study as completed through the inline
  immutable-action confirmation, verifies recommendation/budget controls are
  read-only, reloads, and restores the lifecycle reason plus successor command.
  It then loads the deletion preflight, verifies zero owned files and three
  recommendation records, uses the separate irreversible confirmation, and
  verifies the study disappears from the refreshed catalog. Confirmation-run
  and no-global-optimum warnings remain visible before deletion.
- Observes the actual Regression, Quality, and DOE dynamic module resources
  during their existing workflows and verifies no loading state remains after
  each panel is ready.
- Opens Linear Model, Attribute Control Chart, and Factorial DOE routes directly
  and verifies their lazy panels render.
- Aborts the Regression module request in a separate browser page and verifies
  the sanitized panel error boundary and reload command without exposing the
  dynamic-import exception in the page.
- Uploads a synthetic XLSX file in the browser and confirms parsing.
- Uploads an empty CSV to verify upload error recovery, then uploads a valid
  synthetic CSV.
- Edits parser options for header row and missing tokens.
- Edits delimiter selection for a semicolon-delimited file.
- Selects a named XLSX worksheet after first verifying missing-sheet recovery.

## Tutorial API Smoke

`scripts/tutorial_smoke.ps1` uses a temporary local workspace and the real
FastAPI application to upload and confirm the committed synthetic training,
prediction, and Gage files. It runs 18 normalized result sections spanning
EDA, inference, categorical analysis, regression/Predict, quality, Factorial,
RSM/Optimizer, and Bayesian GP/EI. It then compares current Studio responses to
`examples/tutorial/tutorial_expected_results.json` with explicit absolute and
relative tolerances. Dynamic IDs, timestamps, paths, and raw source rows are
not stored in that expected-results file.

Generator tests run the data generator twice, verify identical manifests and
file SHAs, dimensions, schema compatibility, and the intentionally invalid
prediction target. This API smoke supplements rather than replaces the
browser critical path.
- Selects CP949 encoding after first verifying UTF-8 decoding failure recovery.

## Current Step Markers

`tests/e2e/critical_path.py` currently prints these major step markers in order:

- `wait for backend health`
- `wait for frontend dev server`
- `open Workbench`
- `paste synthetic TSV and confirm schema`
- `run descriptive statistics`
- `run two-sample t test`
- `create, download, and delete one export`
- `verify Help Center and Report Center routes`
- `restore and compare saved results`
- `delete one stored analysis run`
- `verify schema stale behavior`
- `verify linear model fit and prediction`
- `verify attribute control chart`
- `verify DOE factorial analysis`
- `verify DOE response surface analysis and optimization`
- `verify Bayesian study observations and recommendation`
- `verify XLSX browser upload`
- `verify CSV upload and upload error recovery`
- `verify parser option editing`
- `verify delimiter option editing`
- `verify XLSX sheet selection recovery`
- `verify CP949 encoding selection recovery`
- `verify lazy panel direct routes`
- `verify lazy panel error boundary`

## Not Covered

- Remote GitHub Actions status or branch protection settings.
- Full OpenAPI-to-TypeScript generation.
- Every available statistical method panel.
- Limit-set tamper and every P/NP/C/U Phase II mismatch branch; backend unit,
  reference, API, and OpenAPI tests cover those cases while E2E covers the P
  vertical path.
- Bayesian abandoned-study close and successor creation submission, additional
  Bayesian benchmark families/budgets, non-normal capability,
  advanced Gage R&R, or fractional-factorial alias analysis.
- Root-graph retention for datasets and DOE designs. Individual export and
  analysis-run deletion are covered in E2E. Model/limit-set dependency blockers
  are covered in E2E and their successful deletion is covered by API tests;
  Windows locked-file,
  rollback restoration, cleanup retry, and tampered-quarantine branches are
  covered by backend API tests rather than browser automation.
- Chart export artifacts.
- Browser matrix coverage beyond Chromium.
- Large dataset performance or memory budget E2E. The paste staging parser is
  unit-tested at its materialization/scan boundaries rather than with a 100 MB
  browser fixture.
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

## Historical Bayesian Foundation Regression

The schema-11 Bayesian study/history foundation has no browser study editor,
surrogate, recommendation, or executable method in this slice. Its dedicated
asset API is covered by backend create/restore/paging/state/history/tamper tests
rather than a fake browser result. The full browser smoke was rerun with
`-DiagnosticsRoot .\.tmp\e2e-diagnostics-bayesian-foundation` and retained all
existing critical paths, including lazy direct routes and isolated import
failure recovery.

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
