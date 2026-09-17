# UI, GPR and report parity release

## Starting point and acceptance gates

- BASE_SHA: `740486e885492d56456aef99933d80e7422ba421` (fetched origin/main).
- Branch: `feat/gpr-reproducibility-and-report-parity`.
- Preserve the untracked user file `examples/image2.png`; never stage it.
- `data_prd.md` is absent. AGENTS, addendum, implementation guide and current
  method/navigation/report contracts govern this change.
- Installed `ui-ux-pro-max` instructions and local UX search were consulted.
  Apply compact operational-tool cards, semantic hierarchy, keyboard focus and
  restrained active-state emphasis, not marketing-page composition.

Acceptance: all existing methods remain reachable in canonical order; four family
landings use the same executable cards as flat landings; sidebar ancestry remains
distinct from the selected leaf. Preserve routes, expansion, drafts and locales.

GPR acceptance: explicit length bounds and real bounded BFGS work throughout CV,
comparison, refit, persistence, prediction and HTML. Preserve legacy numerical
settings and Bayesian calculations. Independent posterior/optimizer/CV references,
gradient checks and artifact round trips must pass.

Report acceptance: PLS tables and SVG diagnostics come from saved payloads only;
all registered method/export routes have an honest coverage entry. Unknown results
must not produce a falsely complete report. Export must not fit or read raw rows.

## Risks and containment

- Statistical: a larger length lower bound is a smoothness constraint, not a
  universal accuracy improvement. Keep sample SD (`ddof=1`), fold-local scaling,
  observation versus latent uncertainty and unchanged candidate split policies.
- Compatibility: old requests without new settings retain the legacy bounds;
  new UI requests explicitly send the new proposal. Never rewrite saved bytes.
- Numerical: logistic BFGS can saturate at boundaries; validate finite bounds and
  interior initialization, record both gradient coordinates and optimizer status.
- Privacy: use synthetic data, local assets and existing dependencies only.
- Migration: JSON options/results/manifests suffice; no SQLite migration planned.
- Performance: preserve row/predictor/LOO limits, 256 optimizer starts, global
  deadline and single-thread numerical work. No hidden search reduction.

## Validation record

Results, exact commands, screenshots, release commits and limitations are recorded
below as checks finish. Historical counts are not new execution evidence.

Initial command discovery: the suggested `test_analysis_result_exports.py` does
not exist; that pytest invocation exited 4 without running tests. Actual export
coverage is in `test_api_contracts.py` and export retention/API tests.

Baseline focused backend (GPR, kernel comparison, PLS calculation/API): 50 passed.
Baseline frontend `npm --prefix frontend test -- --run`: 44 files, 335 passed.
Baseline E2E exited 1 during the curvature workflow when edits caused Vite HMR;
this contaminated run is neither a passing baseline nor evidence of a pre-existing
failure. Earlier synthetic screenshots remain under
`.tmp/e2e-baseline-gpr-report-parity/screenshots`. Final E2E runs without
application edits or Vite HMR.
UI focused tests: 3 files, 21 passed (domain/sidebar/model).

User Python code and comparison data were not provided. Synthetic independent
reference agreement does not reproduce or explain that specific user's discrepancy.

## Implemented changes

1. Presentation now flattens each domain's direct/family method list in canonical
   order without altering registration, routes or sidebar classification. All
   eight domains share `AnalysisDomainMethodCard`; family names are small labels.
   Planned/contextual entries remain distinct. Sidebar node kinds and depth drive
   typography, indentation and parent/selected-leaf emphasis.
2. Standalone GPR retains L-BFGS-B and sample-SD scaling. Explicit shared length
   bounds propagate through folds, candidates and final/detail refits. New scaled-X
   UI drafts propose 0.5/1/100; omitted legacy options still mean 0.01/1/100.
   Changing units requires confirmation and resets the draft visibly. BFGS uses
   a bounded log-theta transform with analytic chain-rule gradients, not clipping
   or a fallback optimizer. Result and manifest record actual settings and traces.
3. PLS was absent from report dispatch despite having a title. A dedicated
   schema-1 renderer now includes settings, all component-selection rows and
   selected marker, summary, both coefficient scales, training/OOF response
   plots, scores, every loading/weight/rotation component and residual diagnostics.
   HTML uses saved points only and labels their limit. Completed separate point
   predictions have an explicit JSON download, not an implicit report attachment.
4. An explicit 30-method inline-report contract is checked against the 37-method
   registry. Dedicated DOE/BO/prediction workflows are audited separately. Empty,
   unknown and unsupported results fail honestly; incomplete existing renderers
   are labelled summary reports. See `html_report_coverage_matrix.md` for each
   method's renderer, gaps and evidence, rather than treating registration as
   numerical or visual parity.

## Versions and compatibility

API 20 -> 21, standalone GPR method 0.2.0 -> 0.3.0, GPR result/manifest 2 -> 3.
Frontend, backend and PowerShell startup checks agree. Metadata stays 20: JSON
options and safe JSON/NPZ model artifacts need no relational migration. Readers
retain GPR schema 1/2; export adds coverage without rewriting any old bytes.
PLS calculation/result/manifest and Bayesian Optimization calculations are
unchanged. Code rollback does not remove generated assets, but pre-release code
cannot read the new GPR schema-3 models/results.

## UI evidence

The installed skill was queried with local UX searches for navigation hierarchy
and keyboard/focus accessibility. No marketing hero, external font, icon package
or new dependency was introduced. Baseline screenshots are partial evidence,
not a clean complete baseline run.

Before: `.tmp/e2e-baseline-gpr-report-parity/screenshots/`:
`hypothesis-family-cards.png`, `sidebar-analysis-method-hierarchy.png`.
After focused verification: `.tmp/e2e-gpr-report-focused/screenshots/`:
`unified-domain-{0..7}-{ko|en}-{1440|1280|1024|390}.png`,
`sidebar-expanded-hierarchy-{ko|en}.png`,
`gp-applied-settings-{ko|en}-{1440|1280|1024|390}.png`,
`pls-offline-report-{ko|en}.png`.
All use synthetic data and remain ignored, outside Git history.
The complete passing run is `.tmp/e2e-gpr-ui-report-final`; the additional
viewport/geometry checks are `.tmp/e2e-gpr-report-geometry`. A full-page screenshot
may place the fixed mobile header in the middle of the captured document; the
viewport-only captures confirm the real layout and readable labels.

## Corrected attempts

- PLS regression tests first demonstrated the missing renderer. After dispatch
  integration, stored-body/table/SVG tests pass, including no-fit/no-raw-read guards.
- BFGS initially exceeded a transformed upper bound by one ULP. The stable
  complementary-sigmoid expression avoids cancellation; no clipping was added.
- Legacy schema-2 restore fixtures must preserve their existing kernel-selection
  metadata. Tests were corrected rather than weakening the reader's SHA checks.
- Full E2E first stopped on the old family-card selector, then a relative file
  URI, then a report-navigation helper that only toggled the parent. These test
  assumptions were updated to the actual routes and absolute offline file URI.
- A focused E2E label lookup exposed an ambiguous optimizer select accessible
  name; it now has an explicit localized label. The focused flow then passed.
- ESLint rejected an untyped `JSON.parse` assignment in the new prediction
  snapshot test. An explicit result type fixed the test; no rule was disabled.
- Early full pytest/check attempts were stopped after finding the stale startup
  API-20 constant. They are not passes. The runtime contract follow-up passed
  224 tests. The next check stopped on Ruff format, corrected in that test only.

## Host and remaining limitations

Actual validation host: Windows 10 Home 19045, PowerShell 5.1, CPython 3.10.11,
Node 22.23.2, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2, CPU-only. A separate
Windows 11 host was not available; compatibility remains the product target.
No user Python code/data was supplied. Fixed-posterior, matched-optimizer and
fold-local CV comparisons are synthetic independent sklearn references.

Larger length bounds can underfit rapid variation, as the recorded benchmark
demonstrates. BFGS and L-BFGS-B need not reach the same local optimum. No per-column
ARD bounds or physical-to-fold-unit conversion is offered; shared ARD bounds and
RQ's scalar length are explicit. Nonconvergence remains visible.

Some pre-existing hypothesis/quality/OLS HTML exports remain summary-only; GPR's
surface is a stored table rather than a heatmap. Every historical schema/option
combination has not been visually checked. PLS point-prediction JSON is a separate
client download, not a managed Report Center artifact. Offline report checks use
a browser context with network disabled and a local file URI, not a machine-wide
network shutdown. No original analysis/model is refit during report generation.

## Executed commands and evidence

PowerShell 5.1 commands use the repository Python environment and Node 22.23.2 on
PATH. Native process exit codes are captured with `Start-Process -Wait -PassThru`
and separate stdout/stderr logs, then propagated as the wrapper exit code.

| Command | Observed outcome | Evidence |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_gaussian_process_regression_api.py backend/tests/unit/test_report_coverage.py backend/tests/unit/test_pls_report.py -q` | 47 passed, 66.65s | `.tmp/gp-report-followup.log` |
| `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_dev_startup_contract.py backend/tests/unit/test_openapi_frontend_contract.py -q` | 224 passed, 35.34s | `.tmp/runtime-contract-followup.log` |
| `npm --prefix frontend test -- --run` | 46 files / 342 passed, 23.72s | `.tmp/frontend-current.log` |
| `npm --prefix frontend run typecheck` | passed | strict TypeScript |
| `npm --prefix frontend run build` | native exit 0, 4.79s | `.tmp/build-current.log` |
| `node scripts/check_frontend_localization.mjs` | 2,964 sources / 3,835 keys passed | no new hard-coded UI Korean |
| `.\.venv\Scripts\python.exe scripts/benchmark_gpr_length_bounds.py` | completed all nine synthetic cases | `.tmp/gpr-length-sensitivity.json`; contract table |
| `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -GprReportOnly -DiagnosticsRoot .\.tmp\e2e-gpr-report-focused` | passed, native exit 0 | focused diagnostics |
| `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-gpr-ui-report-final` | complete critical path passed, native exit 0 | `.tmp/e2e-gpr-full-final.stdout.log` |
| `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -GprReportOnly -DiagnosticsRoot .\.tmp\e2e-gpr-report-geometry` | passed, native exit 0; mobile controls/labels within container | viewport screenshots and numeric geometry log |
| `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -GprReportOnly -DiagnosticsRoot .\.tmp\e2e-gpr-report-units` | passed, native exit 0; unit-change cancel preserves draft, accept resets explicit coordinates | `.tmp/e2e-gpr-units.stdout.log` |
| `git diff --check` | passed | no whitespace errors |

Final full gate:
`powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` returned **native
exit 0** (`.tmp/check-gpr-report-final2.stdout.log` / `.stderr.log`). Backend:
**1,224 passed, 1,576.48s**. Frontend: **46 files / 342 passed, 27.80s**. Ruff
lint/format (260 files), mypy (158 source files), 18 tutorial blocks, strict
TypeScript, localization (2,964 sources / 3,835 keys), ESLint and production build
(4.67s) passed. Lint: zero errors, nine Fast Refresh warnings (seven existing,
two new helper-export warnings). Vite also reports large chunks and localization
plugin timing. These warnings were not suppressed or counted as failures.

The complete E2E includes existing regularized/OLS/PLS/GP/PCA/DOE/BO workflows,
assets, reports, uploads, lazy-route recovery and preserved UI drafts. The focused
geometry follow-up added assertions only, not application changes.
The units follow-up also changes assertions only; all application sources stayed
identical to the complete passing E2E.

`scripts/test.ps1` is not separately rerun: `scripts/check.ps1` runs the same full
backend/frontend suites plus lint, format, typing, localization and production
build. A full backend baseline before edits was not completed. This is explicitly
different from the final full-suite validation.

## Logical release commits

- `70daa76`: domain cards/sidebar, their unit/browser tests and navigation docs.
- `ac77345`: GPR settings, BFGS, reproducibility, schema compatibility, safe model
  round trips, report evidence and synthetic sensitivity contract.
- `7d82882`: PLS renderer, separate prediction snapshot, report dispatch guard,
  method-level coverage and API/body/SHA tests.
- Integration verification/documentation commit: identified in the final release
  report (the document cannot contain its own commit hash).

UI-only rollback, without resetting history:

```powershell
git revert 70daa76
```

Application changes in reverse order:

```powershell
git revert 7d82882
git revert ac77345
git revert 70daa76
```

The final release report also lists the verification-only commit for a complete
rollback. Do not use a SHA range that could include someone else's changes.
Run checks and use an ordinary push after reverting. No rollback was performed.

## Source inventory

| Area | Changed implementation and focused tests |
| --- | --- |
| Domain/sidebar | `AnalysisDomainLanding.tsx`, `AnalysisDomainMethodCard.tsx`, `analysisDomainMapping.ts`, `SidebarNavigation.tsx`, `sidebarNavigationModel.ts`, `dashboardNavigation.css`; domain/sidebar/App tests |
| GPR backend | `statistics/gaussian_process_regression.py`, `gaussian_process_kernel_selection.py`, `services/analysis_runner_gaussian_process.py`, `gaussian_process_predictions.py`, `api/v1/schemas/analyses.py`, registry/runtime contracts; GP API/kernel/reproducibility/health/startup tests |
| GPR frontend | `GaussianProcessRegressionPanel.tsx`, `GpOptimizationSettings.tsx` and tests, `App.tsx`, `api/types/analysisResultsRegression.ts`, runtime compatibility/tests and i18n/error catalog |
| Reports | `analysis_run_exports.py`, `gaussian_process_report.py`, `pls_regression_report.py`, `stored_report_primitives.py`, `report_coverage.py`; PLS/coverage tests; `AnalysisResultExportPanel.tsx`, `PlsRegressionPanel.tsx`, `plsPredictionSnapshot.ts` and tests |
| Tools/browser | `dev_runtime_helpers.ps1`, `benchmark_gpr_length_bounds.py`, `e2e.ps1`; `critical_path.py`, `dashboard_navigation.py`, `refined_ui.py`, `gpr_report_parity.py` |
| Documentation | README, this record, GPR optimizer/method/kernel contracts, PLS/report-center/report coverage, navigation, assets, method/runtime versions, statistical audit, E2E and CI status |

Exact release paths can be reproduced without including untracked user files:
`git diff --name-only 740486e885492d56456aef99933d80e7422ba421 HEAD`.
