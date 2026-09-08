# Regularized Regression And Compact Domains

Validation record, 2026-09-08. Full tests, static/type/build checks and Chromium
have passed. Publication details and the matching local server are reported in
the completion response.

## Implementation Report

1. Base main: `019c73f66fc177cf5de303dedd920a45048739b1`. Work is on
   `feat/regularized-linear-models-and-compact-domains`, not directly on main.
2. Existing OLS: NumPy least squares, treatment coding, numeric quadratics and
   interactions, hierarchical backward elimination, SE/t/p/CI, ANOVA, PRESS,
   lack-of-fit, residual diagnostics, saved models, prediction and optimization
   remain. The arithmetic in `statistics/linear_model.py` is unchanged.
3. Official research: pinned scikit-learn 1.7 estimator/scaler/Pipeline/CV
   documentation and Minitab model-selection help are linked in
   [the statistical contract](regularized_linear_model_contract.md).
4. One method: a native-radio estimator selector lives inside
   `regression.linear_model`; each execution fits and saves exactly one model.
   There are no Ridge/Lasso/Elastic Net method IDs or duplicate sidebar cards.
5. Shared design: the validated OLS design builder is public and reused with
   the existing parsing, contrasts, feature order, row identities and domains.
   Penalized solvers do not inherit OLS rank/inference restrictions.
6. Scaling: every non-intercept design feature, including dummy/quadratic/
   interaction columns, uses training-fold `StandardScaler` (ddof 0). Response
   units are unchanged. Coefficients and intercept are back-transformed.
7. Leakage: each inner and outer fit constructs a new scaler/estimator pipeline.
   Prespecified, response-independent category contrasts are shared; validation
   responses never influence fitting, scaling or inner parameter selection.
8. Nested CV: outer OOF predictions evaluate tuning; independent full-data
   inner selection and refit produce the saved model. Limits: 10,000 solver
   fits, 10,000 usable rows, 100,000 scanned rows, 200 features, LOO at most 200
   rows, one numerical thread and one spawned worker. Default deadline 120 s,
   configurable up to 300 s, with a bounded parent-process startup allowance.
9. Ridge: deterministic dense SVD, unpenalized intercept and positive L2 alpha.
10. Lasso: cyclic coordinate descent, positive L1 alpha, exact-zero flags,
    iterations/dual gap and explicit convergence warnings.
11. Elastic Net: cyclic coordinate descent with strictly `0 < l1_ratio < 1`;
    fixed or tuned alpha/ratio. Endpoints require choosing Ridge or Lasso.
12. Defaults: Ridge 49 alphas from 1e-6 to 1e6; Lasso/EN 50 from 1e-6 to 10.
    EN ratios: .10/.50/.70/.90/.95/.99. Outer/inner folds 5/5, shuffled seed
    20260907. Fixed mode does not tune. Alpha magnitudes are not comparable
    across estimator objectives. Per-estimator drafts survive radio changes.
13. Results: OLS keeps its inference sections. Penalized results show training
    and OOF performance, original/standardized coefficients and zero flags,
    without OLS p-values, SE, CI, ANOVA, adjusted R-squared, VIF or Cook's D.
14. Charts: localized interactive inner-CV error curve with fold-SD bars,
    selected-alpha marker, selectable coefficient path and complete path table;
    fitted/OOF, residual-fit/order, histogram and Q-Q diagnostics. The path is
    descriptive, not an independent performance assessment.
15. Prediction: JSON coefficients use the existing numeric/category feature
    adapter. Penalized intervals are null with `point_only` and a reason;
    OLS intervals remain. Atomic manual-row validation, known-level checks,
    training-range warnings and checksum verification are preserved.
16. Optimization: existing original-scale coefficient/desirability/search
    calculations are reused within training bounds. Model kind and selected
    alpha/ratio are displayed; no new uncertainty calculation is invented.
17. Limits of interpretation: category dummies are penalized separately;
    Lasso/EN do not enforce strong hierarchy. No grouped or causal selection,
    classical penalized inference, bootstrap or conformal intervals are claimed.
18. Versions: API 18; linear-model method 0.3.0/result 6; linear manifest 4;
    prediction method 0.3.0/result 3/config 4/rows 2; pasted prediction method
    0.2.0/response 2; optimizer method 0.2.0/result 2/config 2. New manifest
    readers are discriminated by model kind. Existing PLS/GP/PCA/DOE/Bayesian
    versions are unchanged.
19. Metadata: schema 19 remains. Existing generic model records and JSON
    artifacts suffice; no SQLite migration or existing artifact rewrite.
20. Legacy parity: static OLS inference/backward/prediction/optimizer assertions
    are retained. Synthetic schema-2/3 manifests and schema-4/5 results restore
    without byte changes. Running all 18 tutorial methods changed only two
    expected method-version strings, not any expected statistic.
21. Historical UI: only the density of `fb07c68405e0038e2a694a35d806a1a191b2cfda`
    informed the layout. No reset, revert or historical source replacement.
22. Current capabilities: eight domains, their mapping/sidebar and all PCA,
    PLS, GP, DOE, Bayesian and stored-asset workflows remain.
23. Compact UI: root cards omit order badges/count clutter/repeated open text.
    Domain method/family grids precede a default-closed native disclosure.
    Method cards use names, availability and at most three guidance tags.
    Planned-only families are compact notices. Regression results use bounded
    grid tracks so manual prediction tables scroll internally on mobile.
24. Changed files: see the file inventory below and
    `git diff --name-only 019c73f..HEAD`. User `examples/image2.png`, workspaces,
    downloaded tools, diagnostics and model artifacts are not committed.
25. Exact commands: see the command ledger below. PowerShell wrappers are
    used; `npm.cmd` avoids the machine's restricted `npm.ps1` execution policy.
26. Backend: final `scripts/test.ps1` passed 1,076 tests in 1702.42 seconds.
    The final combined check repeated all 1,076 tests in 1515.96 seconds.
    Focused calculations: 43 passed; focused
    regularized/legacy/runtime/schema checks: 222 passed; final missing-basis
    error-code regression plus regularized API suite: 10 passed.
27. Frontend: `scripts/test.ps1` passed 298 tests/40 files in 26.88 seconds.
    The final combined gate passed 300 tests/40 files in 21.83 seconds,
    including the two subsequent edge-case/help tests;
    focused settings/result/locale/interval/guidance tests passed 15/15.
28. Typecheck/build: final Node-22 lint and strict TypeScript checks passed;
    production build passed in 3.30 seconds. Localization passed 2,976 sources
    and 3,579 keys. Existing chunk-size/plugin-timing warnings remain.
29. E2E: complete Chromium critical path passed with exit code 0 on ports
    18625/18713 after the final zero-equation/help changes. It covers
    three real penalized fits, model persistence, manual point predictions,
    saved-result restore and compact en/ko layouts at four viewport sizes,
    followed by the existing OLS/PLS/GP/PCA/DOE/Bayesian workflows. Intermediate
    failures are retained in diagnostics, not counted as passes.
30. Final diagnostics: `.tmp/e2e-diagnostics-regularized-regression-final-pass`;
    an earlier complete pass is in `.tmp/e2e-diagnostics-regularized-regression`,
    and baseline in
    `.tmp/e2e-diagnostics-regularized-baseline`. Viewports 1440x900, 1280x800,
    1024x768 and 390x844; English and Korean.
31. Not run: no R/glmnet/Minitab runtime was added. Independent static expected
    values use a separate sklearn GridSearchCV script without app imports,
    closed-form Ridge and hand-checkable orthogonal shrinkage. No additional
    browser engine is claimed; Chromium is the requested gate.
32. Known limitations: exact CPU-bound tuning can hit explicit limits; no
    silent candidate thinning, model substitution or sampling. Paths show one
    selectable feature at a time with a complete table. Existing legacy chart
    translations run through the production Vite transform, so full English
    DOM coverage is verified in browser tests, not raw Vitest SSR alone.
    ESLint reports two non-failing Fast Refresh export warnings; Vite reports
    the existing large-chunk warning. Neither is a type or calculation failure.
    The requested root `data_prd.md` is absent from this checkout; the available
    addendum, implementation guide and current method/runtime contracts govern
    this work. No missing document is claimed as read or recreated implicitly.
33. Commits: `6999551` contract; `0db2afb` shared matrix; `e517f81` solvers;
    `89f9670` UI/model/prediction/optimizer integration; `16298be` compact
    domains. The final `test(docs): validate regularized regression and compact
    domain workflows` commit contains this verification record; its SHA is
    reported in the completion response to avoid a self-referential commit hash.
34. Publication: branch `feat/regularized-linear-models-and-compact-domains`,
    target `main` by normal fast-forward as requested. The final remote tip and
    draft-PR outcome are recorded in the completion response after publishing.

## Benchmark

Windows CPython 3.10.11, NumPy 2.2.6, SciPy 1.15.3, sklearn 1.7.2; synthetic
static reference with 24 rows and three numeric features, all default tuning
settings, one numerical thread. Other validation processes were running;
these timings are observations, not guaranteed response times.

| Estimator | Fits | Elapsed seconds | Selected alpha | Selected ratio | Converged |
| --- | ---: | ---: | ---: | ---: | --- |
| Ridge | 1,525 | 6.956 | 0.05623413251903491 | N/A | Yes |
| Lasso | 1,556 | 6.991 | 0.01 | N/A | Yes |
| Elastic Net | 9,056 | 38.675 | 0.007196856730011514 | 0.7 | Yes |

## Command Ledger

The system Node was 24.17.0 during intermediate checks. Final requested Node
22 checks use an isolated official Node 22.23.2 Windows distribution; its ZIP
SHA-256 was checked against the official SHASUMS256 file:
`1177b4137ba5adaa56354ae40f1080c7450e8ae09cecb47da459d1c52ac99f97`.
No application dependency or system installation was changed.

```powershell
git fetch origin main
git switch -c feat/regularized-linear-models-and-compact-domains
git show fb07c68405e0038e2a694a35d806a1a191b2cfda:frontend/src/AnalysisWorkbench.tsx
git show fb07c68405e0038e2a694a35d806a1a191b2cfda:frontend/src/AnalysisShell.tsx
git show fb07c68405e0038e2a694a35d806a1a191b2cfda:frontend/src/App.css

.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_regularized_linear_model.py
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_api_contracts.py::test_regression_prediction_endpoint_rejects_manifest_without_prediction_basis backend/tests/unit/test_regularized_linear_model_api.py
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_regularized_linear_model_api.py backend/tests/unit/test_health.py backend/tests/tutorial backend/tests/unit/test_openapi_frontend_contract.py
.\.venv\Scripts\python.exe -m ruff check backend
.\.venv\Scripts\python.exe -m ruff format --check backend
.\.venv\Scripts\python.exe -m mypy backend/app
powershell -ExecutionPolicy Bypass -File .\scripts\tutorial_smoke.ps1 --write-expected
.\.venv\Scripts\python.exe scripts/render_tutorial_results.py --write
.\.venv\Scripts\python.exe .tmp/benchmark_regularized.py

$env:Path = (Resolve-Path .tmp/node22/node-v22.23.2-win-x64).Path + ';' + $env:Path
npm.cmd --prefix frontend test -- --run
npm.cmd --prefix frontend test -- --run src/RegularizedLinearModel.test.tsx
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
node scripts/check_frontend_localization.mjs
powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -BackendPort 18623 -FrontendPort 18711 -DiagnosticsRoot .\.tmp\e2e-diagnostics-regularized-regression
cmd.exe /d /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1 1> .tmp\regularized-verified-check.stdout.log 2> .tmp\regularized-verified-check.stderr.log"
cmd.exe /d /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check.ps1 1> .tmp\regularized-check-final-pass.stdout.log 2> .tmp\regularized-check-final-pass.stderr.log"
cmd.exe /d /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -BackendPort 18625 -FrontendPort 18713 -DiagnosticsRoot .\.tmp\e2e-diagnostics-regularized-regression-final-pass 1> .tmp\regularized-verified-e2e-final.stdout.log 2> .tmp\regularized-verified-e2e-final.stderr.log"
```

Commands above group completed and final in-progress checks; only the test
result entries marked passed certify success. Test servers bind only to 127.0.0.1.

## Baseline And Intermediate Failures

- Baseline frontend: 289 tests/39 files, typecheck and production build passed.
- Baseline backend: 1,047 passed, two failures. The E2E documentation marker
  parser missed a multiline step. A detached sklearn source file created while
  the long baseline ran also triggered the dependency-import allowlist; that
  second result is a contaminated baseline, not a pre-existing application bug.
- Baseline Chromium passed on backend 18611/frontend 18699 after Windows
  rejected the script's default frontend port 5199.
- Intermediate full test: 1,071 passed/three failed (old runtime/tutorial
  version expectations and the multiline E2E marker parser), then corrected.
- Intermediate full check: first stopped on formatting of touched files; next
  had 1,075 passed/one failed because strict manifest validation masked the
  established missing-prediction-basis error code. The original stable code is
  preserved and its focused test passes.
- Browser testing found and fixed dropped estimator arguments at the App
  callback and a manual-prediction grid mobile overflow. Test-only waits and
  selectors were corrected for asynchronous dataset correction completion,
  accessible language-button names, card markup and the suite's forced-locale
  initialization. Failed runs are not counted as successful E2E coverage.
- A later full check passed all individual gates (1,076 backend and 299
  frontend tests), but its outer PowerShell `*>` wrapper returned exit 1 when
  Vite wrote a warning to stderr. Separate native stdout/stderr capture is used
  for the final invocation so its actual exit code is preserved.
- One supplementary browser attempt was invalidated by a Vite restart while
  the guidance translation file was being edited. The complete final run uses
  frozen source and has exit code 0; its stderr log is empty.
- Replacing OLS-only help with estimator-specific translation tokens left seven
  unused legacy source mappings. The localization gate correctly failed after
  the backend suite passed 1,076 tests in 1554.44 seconds. Removing only those
  unused mappings restores the strict check: 2,976 sources and 3,579 en/ko keys.
- The last full check completed through production build. After a conversation
  interruption the process session was no longer available, so its final
  terminal exit-code item could not be recovered. Complete per-gate stdout and
  stderr logs show all tests/checks passed, with only the documented warnings.

## File Inventory

- Backend calculation/reference: `statistics/linear_model.py`, new
  `statistics/regularized_linear_model.py`, independent generator/static JSON,
  `test_regularized_linear_model.py`, dependency-import allowlist test.
- Backend API/lifecycle: `schemas/analyses.py`, new
  `schemas/linear_model_manifests.py`, registry/runtime contract,
  `analysis_runners_regression.py`, `regression_models.py`,
  `regression_pasted_predictions.py`, `regression_response_optimizer.py`,
  `analysis_run_exports.py`, new worker/report/message modules and API tests.
- Frontend: App/AnalysisShell/LinearModelPanel/LinearModelFitResults,
  new RegularizationSettingsPanel/RegularizedLinearModelResults and tests,
  prediction/manual/pasted/results-table/workspace/optimizer panels,
  regression API types/client, diagnostics type narrowing, runtime fixtures,
  typed i18n resources/messages, domain landing/method/family cards and CSS.
- Validation/docs: runtime helper, critical-path and regularized E2E scripts,
  tutorial expected versions/rendered document, README, regression/prediction/
  optimizer/asset/runtime/method/domain contracts, statistical audit,
  E2E coverage and CI status.

### Complete Changed-File List

- `README.md`
- `backend/app/analyses/registry.py`
- `backend/app/api/v1/schemas/analyses.py`
- `backend/app/api/v1/schemas/linear_model_manifests.py`
- `backend/app/core/runtime_contract.py`
- `backend/app/services/analysis_run_exports.py`
- `backend/app/services/analysis_runners_regression.py`
- `backend/app/services/regression_models.py`
- `backend/app/services/regression_pasted_predictions.py`
- `backend/app/services/regression_response_optimizer.py`
- `backend/app/services/regularized_model_messages.py`
- `backend/app/services/regularized_model_report.py`
- `backend/app/services/regularized_model_worker.py`
- `backend/app/statistics/linear_model.py`
- `backend/app/statistics/regularized_linear_model.py`
- `backend/tests/reference/fixtures/regularized_linear_model_reference.json`
- `backend/tests/reference/generate_regularized_reference.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_dev_startup_contract.py`
- `backend/tests/unit/test_health.py`
- `backend/tests/unit/test_openapi_frontend_contract.py`
- `backend/tests/unit/test_python_dependency_lock.py`
- `backend/tests/unit/test_regression_workflow_extensions_api.py`
- `backend/tests/unit/test_regularized_linear_model.py`
- `backend/tests/unit/test_regularized_linear_model_api.py`
- `docs/analysis_domain_menu_spec.md`
- `docs/analysis_domain_navigation_implementation.md`
- `docs/asset_management_contract.md`
- `docs/ci_status.md`
- `docs/e2e_coverage.md`
- `docs/linear_model_method_contract.md`
- `docs/method_versioning.md`
- `docs/regression_prediction_contract.md`
- `docs/regression_response_optimizer_contract.md`
- `docs/regularized_linear_model_contract.md`
- `docs/regularized_regression_implementation.md`
- `docs/runtime_compatibility_contract.md`
- `docs/statistical_method_audit_matrix.md`
- `docs/statistical_twin_end_to_end_tutorial_ko.md`
- `examples/tutorial/tutorial_expected_results.json`
- `frontend/src/AnalysisDomainFamilyCard.tsx`
- `frontend/src/AnalysisDomainLanding.tsx`
- `frontend/src/AnalysisDomainMethodCard.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/LinearModelFitResults.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/LinearModelWorkflow.test.tsx`
- `frontend/src/RegressionManualPredictionPanel.tsx`
- `frontend/src/RegressionPastedPredictionPanel.tsx`
- `frontend/src/RegressionPredictionPanel.tsx`
- `frontend/src/RegressionPredictionResultsTable.tsx`
- `frontend/src/RegressionPredictionWorkspace.tsx`
- `frontend/src/RegressionResponseOptimizerPanel.tsx`
- `frontend/src/RegularizationSettingsPanel.tsx`
- `frontend/src/RegularizedLinearModel.test.tsx`
- `frontend/src/RegularizedLinearModelResults.tsx`
- `frontend/src/analysisDomains.test.tsx`
- `frontend/src/analysisMethodGuidance.test.ts`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/types/analysisResultsRegression.ts`
- `frontend/src/api/types/regression.ts`
- `frontend/src/asyncHookState.test.ts`
- `frontend/src/i18n/catalog.generated.json`
- `frontend/src/i18n/errorMessages.ts`
- `frontend/src/i18n/regularizedMessages.ts`
- `frontend/src/linearModelDiagnosticPoints.ts`
- `frontend/src/runtimeCompatibility.test.tsx`
- `frontend/src/runtimeCompatibility.ts`
- `scripts/dev_runtime_helpers.ps1`
- `tests/e2e/critical_path.py`
- `tests/e2e/regularized_regression.py`
