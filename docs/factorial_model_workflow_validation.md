# Factorial Final-Model Workflow Validation

Status: implementation and local release gates passed, including explicit
process exit code 0 for `test.ps1`, `check.ps1` and the full Chromium E2E.
The immutable publication SHA and observed remote CI state are recorded in the
delivery report rather than as a self-referencing SHA inside this commit.

## Acceptance and Risk Gates

Full and General Full selection must preserve strong hierarchy and immutable
history. Saturated pooling must use adjusted SS without invented p-values.
Fractional/PB automatic selection is rejected. All displayed diagnostics,
predictions and fitted plots must use the final stored model. Paste is draft-only.
Reports are escaped, script-free, bounded, checksum-verified managed assets.
EN/KO and desktop/mobile workflows must pass before a non-force main push.

Statistical risks: exploratory post-selection inference, aliased contrasts,
multi-DF blocks, zero residual DF and curvature domains. Privacy risks: pasted
values in logs, HTML injection and workspace-path disclosure. Compatibility
risks: response locks, legacy result readers and version contracts. Migration
risk: analysis-owned dependencies; metadata 20 adds a transactional BLOB table
without rewriting old JSON. Performance: 256 runs, 60-second selection deadline,
one numerical thread, 15 pair plots, 100 assets per analysis and 16 MiB per asset.

## Outcome Record (Requested Order)

1. Base main: `7e9a8147c8fa963e497179192177fc62ed081194`.
2. Official Minitab/NIST findings and direct sources are in
   `factorial_model_reduction_prediction_plots_audit.md`. No claim of executing
   Minitab or matching every Minitab option is made.
3. Existing two-level calculations already supplied coefficient inference,
   ANOVA, residual/influence and data-mean payloads; selection/prediction were absent.
4. New UI exposes those calculations and adds a final-model basis. Legacy design
   HTML actually includes the latest stored analysis when present, without refit;
   the old storage description was incorrect and has been corrected.
5. Automatic selection: two-level Full and General Full only; `none` stays default.
6. Fractional/PB backward selection is blocked because contrasts may be aliased.
7. A neutral deterministic term-block engine serves DOE only. OLS was not refactored.
8. Every retained interaction retains all lower-order terms; structural columns stay.
9. Saturated pooling targets one quarter of initial nonstructural blocks, rounded
   half-up, at least one and at most nine. Smallest hierarchy-eligible adjusted SS
   leaves first; pooling uses no p-value and does not prove an effect is zero.
10. Subsequent backward steps remove the largest partial-F p-value above alpha.
    Deterministic ties prefer higher order and later initial order. No re-entry.
11. Trace persists initial, pooled, removed and final IDs, fit metrics and optional
    detailed active coefficients. Same-data inference is explicitly exploratory.
12. Shared strict paste accepts one response column or explicit run_order/response
    TSV/CSV, previews all rows, rejects malformed/nonfinite/missing/duplicate rows.
13. Apply changes only the draft. Save creates one atomic revision; analyzed
    revisions remain read-only and require a correction revision.
14. Equation is coded for two-level designs, treatment-coded for General Full.
    Full-precision copy is available; no invented natural-unit equation.
15. Final coefficients expose Effect/Coef/SE/T/P/VIF; intercept has no effect/VIF.
    General Full VIF is per dummy coefficient, not term-level GVIF.
16. Final summary adds PRESS and untruncated predicted R-squared; leverage near
    one gives null PRESS and a warning. All observations enter PRESS/histograms.
17. Final ANOVA includes joint drop-group and term SS, residual/pure error/LOF;
    nonadditive partial SS are not forced to sum to model SS.
18. Interactive raw/standardized Q-Q, histogram, residual-fit and residual-run
    plots use final-model residuals. Existing influence summaries remain.
19. Immutable prediction assets bind design, response revision, analysis and
    preflight hashes. Point prediction and conditional t-based mean CI/PI are saved.
20. Curvature models accept corners or actual stored center/pseudo-center settings.
    Arbitrary interiors are rejected. Without curvature, in-bound numeric
    interpolation is allowed; General Full accepts known levels only.
21. Saved cell means support fitted/data main effects, up to 15 interaction pairs,
    and two-/three-factor cubes with other factors fixed. No General Full cube.
22. Legacy design/response report remains. New analysis report is bound to a
    specific immutable analysis and includes selection, equation, inference,
    diagnostics and fitted SVG plots plus the latest saved prediction snapshot.
23. Analysis, prediction and HTML appear in the asset catalog. Ownership hashes,
    deletion preflight, stale-snapshot rejection and transactional cascade are tested.
24. `차 -> tea` came from translating an ordinal fragment without context.
    Whole semantic interaction-order keys replace fragment concatenation.
25. All catalog/source keys receive automated coverage/placeholder checks; 47
    targeted statistical/context errors were manually corrected. See
    `english_ui_translation_audit.md` for the exact scope and remaining review.
26. API 19; Factorial 0.8.0/config 3/result 2/envelope 2; General Full
    0.3.0/config 2/result 2/envelope 1; prediction/report schema 1.
27. Metadata 20 adds analysis-owned prediction/report storage because existing
    generic artifacts reference analysis runs, not experiment-design analyses.
28. Design manifest and response revision versions remain unchanged. Legacy
    config/result readers and bytes/SHA are preserved. Tutorial numeric values
    and input hashes are unchanged; only the current Factorial version label changes.
29. Changed-file inventory: the feature branch diff against the base SHA above.
    Production changes are scoped to DOE workflow, its asset lifecycle, contracts,
    localization and tests. No regression/PLS/GP/Bayesian computation is replaced.
30. Exact validation commands are listed below.
31. Backend: baseline 1,076 passed. Latest focused gate: 316 passed in 220.13s.
    Final `check.ps1`: 1,137 passed in 1,747.34s. Final `test.ps1`: 1,137 passed
    in 1,774.06s. Both complete processes returned exit code 0.
32. Frontend: final 43 files / 328 tests passed in both full scripts
    (`check.ps1`: 19.95s; `test.ps1`: 24.72s).
33. Strict TypeScript, mypy (152 source files), Ruff lint/format (249 files),
    ESLint and production build passed. Build: 3.29s. Two pre-existing Fast
    Refresh warnings and Vite chunk/plugin-timing warnings remain non-failing.
34. Localization passed: 2,969 source strings / 3,734 keys.
35. Expanded Factorial Chromium workflow and post-rebase full critical path passed.
    The subsequent startup-boundary release run also passed with process exit 0.
36. Screenshots and bounding checks are described below.
37. Minitab binary/reference execution was not run; independent statsmodels static
    reference is used instead. Fetch/rebase found origin/main unchanged at the
    base SHA before the final complete checks; no rebase conflict was present.
    The actual local host reports Windows 10 Home build 19045, not Windows 11.
    A separate Windows 11 client execution was not available on this machine;
    Windows-compatible PowerShell/Python code and Windows CI remain required.
38. Limits: no aliased-design automatic selection, Lenth PSE, studentized-deleted
    residuals, GVIF, arbitrary-interior curvature prediction or natural-unit
    equation. No claim of complete Minitab parity or causal effects.
    Legacy schema 1 analyses remain readable/reportable; prediction needs a new
    analysis with the explicit final-model basis. Old results are not retrofitted.
39. Initial commits: `81214ad` (contracts), `8208180` (selection engine),
    `f76d2a6` (final-model backend/contracts), `0a97adf` (UI and translations).
    `69c7ddc` (workflow coverage/docs), `8cabcbb` (legacy migration assertions).
    `6cd9f39` aligns the startup helper's metadata minimum with the frontend and
    adds schema 19 rejection / schema 20 acceptance tests (10 startup tests passed).
    `8e86877` records the validation follow-up. The final validation/documentation
    commit includes only this record, CI notes and a test-string formatting fix.
40. Feature branch: `feat/factorial-model-selection-prediction-plots`.
41. Final local main SHA: supplied in the delivery report after publication.
42. Final origin/main SHA: independently fetched and compared in that report.
43. Publication policy: fast-forward main only after the gates above; no force.
44. Immutable GitHub commit URL: supplied with the final publication SHA.
45. GitHub CI: observed separately after publication; local checks are not
    represented as a completed remote Actions run.

## Commands and Evidence

Actual host: Windows 10 Home 10.0.19045, Windows PowerShell 5.1,
CPython 3.10.11, Node 22.23.2, CPU-only. Windows 11 remains the product target,
not a falsely claimed local test environment. This host's Node binary is local:

```powershell
$env:PATH = "$PWD\.tmp\node22\node-v22.23.2-win-x64;$env:PATH"
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_factorial_analysis.py backend/tests/unit/test_factorial_design_api.py backend/tests/unit/test_general_factorial_design.py backend/tests/unit/test_doe_response_revisions.py backend/tests/unit/test_factorial_model_selection_api.py backend/tests/unit/test_term_block_model_selection.py backend/tests/unit/test_factorial_model_workflow.py backend/tests/unit/test_factorial_selection_reference.py backend/tests/unit/test_factorial_prediction.py backend/tests/unit/test_factorial_analysis_exports.py backend/tests/unit/test_workspace_asset_retention_api.py backend/tests/unit/test_workspace_assets_api.py backend/tests/unit/test_openapi_frontend_contract.py backend/tests/unit/test_dev_startup_contract.py
npm --prefix frontend test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run build
node scripts/check_frontend_localization.mjs
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 18011 -FrontendPort 18599 -DiagnosticsRoot .tmp/e2e-diagnostics-factorial-model-workflow-release
```

The combined focused command above completed after fetch/rebase: 316 passed.
During implementation, subsets of these files were also run repeatedly.
No Python localization checker exists here;
the repository's actual checker is JavaScript. No DOE-specific retention test
file exists under the requested illustrative name; workspace retention tests apply.

Baseline logs: `.tmp/factorial-workflow-baseline-{backend,frontend,build,e2e}.log`.
Baseline: backend 1,076 passed in 1,424.83s, frontend 303 tests/41 files,
typecheck/build and full Chromium critical path passed.
Focused independent reference: statsmodels 0.14.5, NumPy 2.2.6, SciPy 1.15.3;
absolute tolerance 1e-9 and relative tolerance 1e-8. Generator imports no app
helper and is not a production/runtime dependency.

Corrected intermediate failures: an earlier full check had 13 failures and
1,122 passes. Those failures were outdated tutorial/API/runtime version assertions
and explicit legacy migration-table expectations; each corrected group was
rerun successfully before the current complete reruns. Other corrections included
exact accessible names for cube/paste selects; a test's center-policy
wording; screenshot timing during the mobile drawer close transition. Earlier
live-edit E2E attempts are not counted as successful checks. Ports 5199 and 8613
were refused by Windows; isolated verification uses available 18011/18599.

The startup-helper audit found an old minimum metadata value of 19 while the
frontend requires 20. It now shares that boundary explicitly, with executable
PowerShell tests. The previous complete test stages passed, but the wrapper's
exit status is not claimed successful. A subsequent rerun was deliberately
stopped before applying this correction and is not counted as a pass.
Final successful process logging separates stdout/stderr using `Start-Process -WindowStyle
Hidden -RedirectStandardOutput ... -RedirectStandardError ... -PassThru -Wait`,
then checks the returned process `ExitCode`; Vite warnings remain in stderr.
The new startup-test fixture also needed a line-length/line-ending-only Ruff
correction. Its PowerShell command and assertions are unchanged by that formatting.

Exact final check-process invocation (the test and E2E invocations use the same
process pattern and the script arguments listed above):

```powershell
$process = Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1' -WorkingDirectory $PWD -WindowStyle Hidden -RedirectStandardOutput "$PWD\.tmp\factorial-workflow-release-check-final.stdout.log" -RedirectStandardError "$PWD\.tmp\factorial-workflow-release-check-final.stderr.log" -PassThru -Wait
Write-Output "check.ps1 process exit code: $($process.ExitCode)"
exit $process.ExitCode
```

Release rerun evidence uses `.tmp/factorial-workflow-release-focused.log`,
`.tmp/factorial-workflow-release-test.{stdout,stderr}.log`,
`.tmp/factorial-workflow-release-check-final.{stdout,stderr}.log` and
`.tmp/factorial-workflow-release-e2e.{stdout,stderr}.log`.
The local 8000/8600 preview was restarted with API 19 / metadata 20 and matching
source identity. Chromium confirmed a rendered DOE landing without runtime
mismatch or page errors. A SQLite API backup was made before migration;
all pre-existing table contents compared equal afterwards. Workspace-specific
backup details and user data are deliberately excluded from Git.

## Screenshot Diagnostics

Expanded focused run: `.tmp/e2e-diagnostics-factorial-model-workflow-focused/`.
Full run: `.tmp/e2e-diagnostics-factorial-model-workflow/`.
Post-rebase full run: `.tmp/e2e-diagnostics-factorial-model-workflow-final/`.
Startup-boundary release run: `.tmp/e2e-diagnostics-factorial-model-workflow-release/`.
These local synthetic diagnostics are excluded from Git.

- factorial-backward-settings.png
- factorial-model-selection-steps.png
- factorial-saturated-pooling.png
- factorial-coded-equation.png
- factorial-coded-coefficients.png
- factorial-four-in-one-residuals.png
- factorial-response-paste.png
- factorial-prediction.png
- factorial-main-effects.png
- factorial-interaction-plot.png
- factorial-cube-plot.png
- factorial-report-html.png
- factorial-english-interaction-order.png
- factorial-mobile.png

Viewports: 1440x900, 1280x800, 390x844. Assertions include 2x2 residual layout,
keyboard point movement, internal table scrolling, bounded mobile controls,
no page-level horizontal overflow, no unresolved Korean in the English DOE
panel and no ordinal tea fragments. Mobile and residual screenshots were
visually inspected; the closed drawer no longer obscures controls.

## Changed Files

Implementation inventory relative to the base main commit (88 files).
The unrelated, pre-existing `examples/image2.png` is not part of this change.

```text
README.md
backend/app/analyses/registry.py
backend/app/api/v1/doe_designs.py
backend/app/api/v1/factorial_model_workflow.py
backend/app/api/v1/schemas/assets.py
backend/app/api/v1/schemas/doe.py
backend/app/api/v1/schemas/doe_model_workflow.py
backend/app/core/runtime_contract.py
backend/app/services/doe_design_retention.py
backend/app/services/doe_factorial_analysis.py
backend/app/services/factorial_analysis_assets.py
backend/app/services/factorial_analysis_report.py
backend/app/services/factorial_prediction.py
backend/app/services/general_factorial_designs.py
backend/app/services/workspace_assets.py
backend/app/statistics/factorial_analysis.py
backend/app/statistics/factorial_model_workflow.py
backend/app/statistics/general_factorial_analysis.py
backend/app/statistics/term_block_model_selection.py
backend/app/storage/factorial_analysis_assets.py
backend/app/storage/metadata.py
backend/tests/reference/fixtures/factorial_selection_statsmodels.json
backend/tests/reference/generate_factorial_selection_reference.py
backend/tests/unit/test_api_contracts.py
backend/tests/unit/test_asset_management_api.py
backend/tests/unit/test_dev_startup_contract.py
backend/tests/unit/test_factorial_analysis_exports.py
backend/tests/unit/test_factorial_design_api.py
backend/tests/unit/test_factorial_model_selection_api.py
backend/tests/unit/test_factorial_model_workflow.py
backend/tests/unit/test_factorial_prediction.py
backend/tests/unit/test_factorial_selection_reference.py
backend/tests/unit/test_health.py
backend/tests/unit/test_metadata_store.py
backend/tests/unit/test_openapi_frontend_contract.py
backend/tests/unit/test_term_block_model_selection.py
docs/asset_management_contract.md
docs/ci_status.md
docs/e2e_coverage.md
docs/english_ui_translation_audit.md
docs/factorial_design_extension_audit.md
docs/factorial_design_method_contract.md
docs/factorial_doe_parity_audit.md
docs/factorial_model_reduction_prediction_plots_audit.md
docs/factorial_model_selection_contract.md
docs/factorial_model_workflow_validation.md
docs/factorial_prediction_and_plots_contract.md
docs/interactive_chart_contract.md
docs/localization_coverage_audit.md
docs/localization_glossary.md
docs/method_versioning.md
docs/runtime_compatibility_contract.md
docs/statistical_method_audit_matrix.md
docs/statistical_twin_end_to_end_tutorial_ko.md
docs/storage.md
examples/tutorial/tutorial_expected_results.json
frontend/src/App.css
frontend/src/FactorialAnalysisAssetsPanel.tsx
frontend/src/FactorialDesignPanel.tsx
frontend/src/FactorialModelSelectionResults.tsx
frontend/src/FactorialModelWorkflow.test.tsx
frontend/src/FactorialPlotsPanel.tsx
frontend/src/FactorialPredictionPanel.tsx
frontend/src/FactorialResidualPlots.tsx
frontend/src/FactorialStoredModelWorkflow.tsx
frontend/src/GeneralFactorialDesignPanel.tsx
frontend/src/UnifiedAssetCatalogPanel.tsx
frontend/src/api/doe.ts
frontend/src/api/factorialWorkflow.ts
frontend/src/api/routes.ts
frontend/src/api/types/assets.ts
frontend/src/api/types/doe.ts
frontend/src/api/types/doeModelWorkflow.ts
frontend/src/asyncHookState.test.ts
frontend/src/doe/DoeModelSelectionSettings.tsx
frontend/src/doe/DoeResponsePasteDialog.tsx
frontend/src/doe/doeResponsePaste.test.ts
frontend/src/doe/doeResponsePaste.ts
frontend/src/doe/factorialView.ts
frontend/src/doe/factorialWorkflowPresentation.ts
frontend/src/i18n/catalog.generated.json
frontend/src/runtimeCompatibility.test.tsx
frontend/src/runtimeCompatibility.ts
scripts/check_frontend_localization.mjs
scripts/dev_runtime_helpers.ps1
scripts/e2e.ps1
tests/e2e/critical_path.py
tests/e2e/factorial_model_workflow.py
```
