# Factorial Final-Model Workflow Validation

Status: implementation complete; full-suite and release gates are still running.
Do not interpret this working record as main-push approval.

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
31. Backend: baseline 1,076 passed. Final full-suite gate pending.
32. Frontend: 43 files / 328 tests passed during implementation; final rerun pending.
33. Strict TypeScript/build and mypy passed during implementation; final rerun pending.
34. Localization passed: 2,969 source strings / 3,734 keys.
35. Expanded Factorial Chromium workflow passed; full critical-path gate pending.
36. Screenshots and bounding checks are described below.
37. Minitab binary/reference execution was not run; independent statsmodels static
    reference is used instead. Main/rebase verification has not yet completed.
38. Limits: no aliased-design automatic selection, Lenth PSE, studentized-deleted
    residuals, GVIF, arbitrary-interior curvature prediction or natural-unit
    equation. No claim of complete Minitab parity or causal effects.
39. Initial commits: `81214ad` (contracts), `8208180` (selection engine),
    `f76d2a6` (final-model backend/contracts), `0a97adf` (UI and translations).
    Remaining logical commits and final release SHA will be recorded after gates.
40. Feature branch: `feat/factorial-model-selection-prediction-plots`.
41. Final local main SHA: pending.
42. Final origin/main SHA: pending.
43. Main push: pending; no force push permitted.
44. Commit URL: pending release.
45. GitHub CI: pending release.

## Commands and Evidence

Windows PowerShell, CPython 3.10, CPU-only. This host's Node 22 binary is local:

```powershell
$env:PATH = "$PWD\.tmp\node22\node-v22.23.2-win-x64;$env:PATH"
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_factorial_analysis.py backend/tests/unit/test_factorial_design_api.py backend/tests/unit/test_general_factorial_design.py backend/tests/unit/test_doe_response_revisions.py backend/tests/unit/test_factorial_model_selection_api.py backend/tests/unit/test_term_block_model_selection.py backend/tests/unit/test_factorial_model_workflow.py backend/tests/unit/test_factorial_selection_reference.py backend/tests/unit/test_factorial_prediction.py backend/tests/unit/test_factorial_analysis_exports.py backend/tests/unit/test_workspace_asset_retention_api.py backend/tests/unit/test_workspace_assets_api.py backend/tests/unit/test_openapi_frontend_contract.py backend/tests/unit/test_dev_startup_contract.py
npm --prefix frontend test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run build
node scripts/check_frontend_localization.mjs
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -ExecutionPolicy Bypass -File scripts/e2e.ps1 -BackendPort 18011 -FrontendPort 18599 -DiagnosticsRoot .tmp/e2e-diagnostics-factorial-model-workflow
```

The combined focused command above is the final intended gate, not yet a claim
that this exact invocation has completed. During implementation, subsets of
these files were run repeatedly. No Python localization checker exists here;
the repository's actual checker is JavaScript. No DOE-specific retention test
file exists under the requested illustrative name; workspace retention tests apply.

Baseline logs: `.tmp/factorial-workflow-baseline-{backend,frontend,build,e2e}.log`.
Baseline: backend 1,076 passed in 1,424.83s, frontend 303 tests/41 files,
typecheck/build and full Chromium critical path passed.
Focused independent reference: statsmodels 0.14.5, NumPy 2.2.6, SciPy 1.15.3;
absolute tolerance 1e-9 and relative tolerance 1e-8. Generator imports no app
helper and is not a production/runtime dependency.

Corrected intermediate failures: old version assertions in tutorial/API/runtime
tests; exact accessible names for cube/paste selects; a test's center-policy
wording; screenshot timing during the mobile drawer close transition. Earlier
live-edit E2E attempts are not counted as successful checks. Ports 5199 and 8613
were refused by Windows; isolated verification uses available 18011/18599.

## Screenshot Diagnostics

Expanded focused run: `.tmp/e2e-diagnostics-factorial-model-workflow-focused/`.
Full run: `.tmp/e2e-diagnostics-factorial-model-workflow/`.
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
