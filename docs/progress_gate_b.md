# Gate B Progress

Last updated: 2026-07-19

## Current Bayesian P0 Release Closure Slice

- The supported scope is the bounded continuous, single-objective, sequential P0 recorded in
  `docs/bayesian_p0_release_checklist.md`; advanced Bayesian variants remain explicit non-goals.
- Catalog, Study restore, and recommendation restore now participate in one action lock. Study
  and recommendation output render only when their `study_id` matches the selected catalog ID,
  and direct lifecycle/recommendation/retention hook tests prove stale responses cannot revive
  prior actions.
- Help Center and Report Center now load through independent route chunks with accessible loading
  and sanitized failure boundaries. Main JavaScript decreased from 532.53 kB to 496.98 kB on
  the recorded Windows 10/Node 24 development host.
- Full graph validation remains enabled for every catalog item. The 20/100/500-Study benchmark,
  including one real 100-trial Study, is recorded in
  `docs/bayesian_catalog_performance.md`; lightweight summary/index work remains separate.
- Bayesian calculations, request/result/storage schemas, SQLite schema 14, and method `0.2.2`
  are unchanged. Windows 11/Node 22 and hosted Actions evidence remain release gates.
- Local development validation passed with backend 784, frontend 152,
  OpenAPI/frontend 155, 18 tutorial smoke sections, and Chromium E2E. The host is Windows 10
  build 19045/Python 3.10.11/Node 24.17.0, so this is not release-target evidence.

## Completed Bayesian Frontend And Repository Onboarding Slice

- The 1,400-line Bayesian panel is now a thin compatibility export over
  `features/bayesian/BayesianOptimizationWorkspace`. Study builder, factor and
  constraint tables, catalog, summary, trial table, recommendation, close,
  deletion, and confirmation views are lifecycle-scoped components.
- Draft, catalog, lifecycle, recommendation, and retention state use separate
  hooks and separate latest-request guards. The catalog pages 20 metadata-only
  summaries at a time, retains an exact off-page selection, and no longer
  relies on a fixed `fetchBayesianStudies(0, 50)` call.
- The Bayesian route stores only validated UUID `study_id` and
  `recommendation_id` query fields. Reload restores both through existing
  checksum/dependency-validating GET routes; mismatched or missing assets are
  explicit errors. A new Study clears the old recommendation query.
- Successor preparation keeps the predecessor seed only by explicit user
  choice, always warns that it can reproduce the same initial conditions, and
  offers an explicit random-seed command. Observation/history/recommendation
  data is still not copied.
- Root `README.md` now provides GitHub onboarding, while `backend/README.md` is
  a current schema-14 backend developer guide. No Bayesian calculation,
  persisted schema, API meaning, method ID, or method version changed.

## Current Help, Report, And Tutorial Truth Slice

- `examples/tutorial/tutorial_expected_results.json` is the numeric source of
  truth for 18 API-derived tutorial sections. Marked numeric blocks in the
  Korean tutorial are rendered by `scripts/render_tutorial_results.py`; its
  `--check` mode is part of `scripts/check.ps1` and reports method/field paths
  on drift. The API-vs-JSON tutorial smoke remains a separate gate.
- App routing now includes `/help` and `/reports`. Global question-based method
  guidance and the role dictionary live in Help Center, while the analysis
  page begins with module/method selection and keeps required preflight/warning
  content visible. A closed-by-default selected-method drawer supports ESC,
  focus return, ARIA state, and a tutorial link.
- Report Center reuses paged analysis-run history, checksum-validated stored
  result restore, and existing JSON/CSV/HTML export list/create/download/delete
  APIs. It exposes method/status/stale/result/dataset filters and never renders
  arbitrary result bodies.
- Dedicated capability is explicit: Predict full CSV and Factorial design HTML
  stay in their owning workflows; Predict, Optimizer, RSM, and Bayesian HTML
  reports are not supported in P0. No generic fallback or fake report is used.
- This is a frontend/documentation/test contract change. The 30 method IDs,
  statistical calculations, request/result schemas, and method versions are
  unchanged.

## Summary

Gate B has completed the upload/version, paste-as-dataset intake, canonical JSONL artifact materialization, canonical row reader adoption for preview/profile/current executable methods, schema/preview, profile/preflight with duplicate-row and memory estimates, persisted profile summary artifacts, conservative date/time preflight, analysis catalog, storage/run foundation, selected-method six-module Workbench shell, shared Workbench component split, route-level selected-analysis restore, route-selected dataset/analysis page rendering, filter snapshot row freezing, a narrow filter expression engine and Workbench-level frontend filter controls, basic XLSX parsing confirmation, the first four real exploration-method slices, the first eight real Gate B2 hypothesis slices, the first three categorical slices, the first three Gate C1 correlation/regression slices, the current Gate D quality-control slices, and the first two Gate C3 measurement-system slices in the working tree. The app can accept a local multipart dataset upload or pasted spreadsheet text, validate the file/text envelope, preserve raw bytes unchanged, store SHA-256 provenance in SQLite metadata, return parsing-option candidates, revalidate raw upload integrity before parsing confirmation, confirm delimited-text and basic XLSX parsing, create immutable dataset version `v1`, materialize canonical rows plus a manifest under the workspace, store dataset columns and artifact metadata, retrieve version metadata, update confirmed column metadata while marking dependent analysis runs stale, return paginated row preview from canonical rows, return aggregate profile/preflight counts and warnings from validated canonical rows, summarize date/time format candidates and timezone-awareness risks without raw samples, persist and reuse raw-value-free `profile_summary` artifacts tied to schema/canonical hashes, expose the 6-module analysis method catalog, show planned/disabled methods in a route-restorable Workbench shell with legacy hash fallback, initialize analysis run/artifact/job/regression-model metadata tables with status/cancel API skeletons, execute `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.attribute_control_chart`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart` with real calculations from validated canonical rows, persist an `analysis_row_snapshot` artifact for each executed row selection, persist a safe JSON model manifest for `regression.linear_model`, run backend OLS predictions from app-created manifests through `regression.predict`, store all valid prediction rows in checksum-recorded NDJSON, retrieve them through a paged API, list confirmed target versions without raw rows or storage metadata, and re-read stored analysis results and regression model manifests after checksum validation. The frontend app chrome is split into `AppChrome` for sidebar/topbar/context layout, dataset workflow state and API handlers are split into `useDatasetWorkflow`, and the frontend dataset preparation area is split into `DatasetPreparationPage`, `DatasetParsingPanel`, `DatasetVersionPanel`, `DatasetProfileSection`, `DatasetSchemaSection`, `DatasetPreviewSection`, and shared `datasetDisplay` helpers. The frontend analysis area is split into `AnalysisPage`, `AnalysisShell`, `AnalysisWorkbench`, `DescriptiveAnalysisPanel`, `GraphicalSummaryPanel`, `NormalityAnalysisPanel`, `EqualVariancesPanel`, `OneSampleTPanel`, `PairedTPanel`, `EquivalenceTostPanel`, `OneSampleWilcoxonPanel`, `TwoSampleTPanel`, `MannWhitneyPanel`, `KruskalWallisPanel`, `OneWayAnovaPanel`, `OneProportionPanel`, `TwoProportionPanel`, `ChiSquareAssociationPanel`, `PearsonCorrelationPanel`, `XyCorrelationPanel`, `LinearModelPanel`, `AttributeControlChartPanel`, `IndividualsChartPanel`, `SubgroupChartPanel`, `RunChartPanel`, `CapabilityPanel`, `GageRrPreflightPanel`, and `GageRunChartPanel`, with route selection state handled by `useAnalysisSelection` and app page routing handled by `appRoute` plus `WorkspaceRouter`, so the app chrome, dataset workflow, dataset page, analysis page, method shell, common filter surface, and executable panels have separate component boundaries. LinearModelPanel now supports stored-model preflight followed by explicit target-version prediction execution and a paged raw-value-free prediction result table. GageRrPreflightPanel now supports balanced crossed design preflight followed by Gage R&R ANOVA execution and result rendering. GageRunChartPanel now supports balanced crossed diagnostic chart execution and indexed redacted result rendering. Delimited-text parsing also handles leading preamble plus headerless tabular data through explicit `has_header=false` and `data_start_row` confirmation. The schema UI includes a guarded 34-column Bayesian sample role preset for headerless generated columns. It does not yet provide cell-level data edits, generated chart artifacts, formula recalculation/display-format restoration for XLSX, paired/two-sample TOST, event/trial summary-count categorical input, Fisher exact association p-values, chi-square aggregate-count input, categorical/interaction regression modeling, Gage R&R component/interaction plots, or Gage Run Chart export artifacts.

Gate D1 now includes the dedicated DOE design, immutable response revision/history, and 2-level full factorial analysis slices. `doe.factorial_design` v0.3.0 uses response revision schema 1 and analysis envelope/config schema 2 through current/history/correction routes plus `POST /api/v1/doe-designs/{design_id}/analyses`, `GET /api/v1/doe-designs/{design_id}/analyses/{analysis_id}`, and the HTML report route. SQLite schema 10 stores immutable ordered response values, current heads, and the exact analysis-revision relationship; legacy current responses are deterministically backfilled without rewriting stored analysis artifacts. The calculation uses -1/+1 coding, enforced hierarchy through selected interaction order, center curvature, block fixed effects, OLS effects/inference, partial drop-one ANOVA, pure error/lack-of-fit, residual/influence diagnostics, and capped plot payloads. `FactorialDesignPanel` distinguishes current/history revisions, requires explicit correction, and restores analyzed revisions read-only. Fractional alias analysis, optimization, and chart image export remain out of scope.

Gate D2 now includes the dedicated response-surface and bounded response-optimizer slices. `doe.response_surface` v0.2.0 uses response revision schema 1 and analysis envelope/config schema 2; new design schema-2 assets use family `central_composite`, `alpha_mode` distinguishes rotatable and face-centered CCD, and legacy schema-1 family/mode/SHA restore remains verbatim. It fits a hierarchy-fixed full quadratic OLS model with inference, partial drop-one ANOVA, pure error/lack-of-fit, residual/influence diagnostics, a Hessian-classified stationary point, design-region checks, and a 21x21 contour grid. `regression.response_optimizer` v0.3.0 keeps config/result schema 2 and uses source-bundle schema 2 to pin the exact source RSM analysis and response revision; a newer current correction does not change old optimizer restore. It is available both from the embedded RSM panel and a top-level dedicated Workbench that selects paged metadata-only stored RSM sources and revalidates the full source bundle before execution. Invalid rank, saturated/unusable residual inference, significant lack of fit, and dependency failures block, while advisory diagnostics require exact persisted acknowledgment codes. Automatic term selection, uncertainty-aware desirability, Box-Behnken, orthogonal blocking, nonlinear/integer constraints, report/image export, and a global-optimum claim remain out of scope.

Current stabilization update:

- Current catalog count: 30 stable catalog IDs, 30 available IDs, and 25
  generic `MethodExecutionHandler` entries. The remaining five are dedicated
  workflows and are rejected by generic analysis-run.

- `regression.predict` preflight now rejects missing, wrong-method,
  method-version-mismatched, stale, or source-schema-drifted model analyses and
  requires refitting before execution. Source freshness issues remain distinct
  from target compatibility issues; source schema no-op updates remain valid.
- Prediction provenance now records source analysis/source dataset/target
  dataset/model dependencies plus common runtime/build/package fields. Restore,
  page, CSV, export-list, and export-download paths validate config/result/rows/
  model IDs, versions, hashes, and counts as one relationship contract.
- `METHOD_VERSIONS` is also the sole source for dedicated prediction. The
  persisted contract change bumps only `regression.predict` to `0.2.0` with
  result schema 2, config schema 3, rows schema 2, and unchanged CSV schema 1.
- Actual Workbench and regression prediction hooks are exercised with delayed
  response inversion/reset races; obsolete responses cannot overwrite current
  data or loading state. `regression.predict` is now catalog-available with a
  top-level dedicated Workbench. Its paged metadata-only model catalog is
  followed by the existing checksum/freshness validation, and the top-level and
  Linear Model entries share `RegressionPredictionPanel`. ID-only query fields
  restore the selected model and target after reload.
- `regression.response_optimizer` is also catalog-available and dedicated. Its
  metadata-only RSM catalog reports eligibility counts without run values; a
  selected source is fully restored and checksum-validated before the shared
  `ResponseOptimizerPanel` renders. The embedded RSM entry remains available.
- High-risk statistical QA coverage was strengthened without adding new executable methods. New tests pin one-way ANOVA significant-only posthoc behavior, non-significant posthoc skip, negative omega-squared handling, group-size imbalance warnings, TOST one-sided decision logic, non-significance-not-equivalence behavior, two-proportion zero-cell/all-event handling, sparse chi-square diagnostics, and capability stability-warning visibility.
- Method versions now have a shared `METHOD_VERSIONS` map covering all 30 stable method IDs. The catalog descriptors and generic `MethodExecutionHandler` specs read from the same source, and API contract tests assert catalog/handler version alignment.
- `hypothesis.equivalence_tost` now validates its runner-boundary options through typed `EquivalenceTostOptions`, rejecting invalid numeric types, missing required bounds, and unknown option fields with `invalid_equivalence_tost_options` before row snapshot or result artifacts are written.
- `hypothesis.one_sample_t`, `hypothesis.paired_t`, and `hypothesis.two_sample_t` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_one_sample_t_options`, `invalid_paired_t_options`, or `invalid_two_sample_t_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- `hypothesis.one_sample_wilcoxon`, `hypothesis.mann_whitney`, and `categorical.one_proportion` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_one_sample_wilcoxon_options`, `invalid_mann_whitney_options`, or `invalid_one_proportion_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- `eda.graphical_summary`, `eda.normality`, and `eda.equal_variances` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_graphical_summary_options`, `invalid_normality_options`, or `invalid_equal_variances_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- `regression.linear_model` and `quality.gage_rr` now also validate runner-boundary options through typed contracts. Linear model rejects invalid numeric option types, missing predictor IDs, unknown top-level fields, and unknown nested interaction fields with `invalid_linear_model_options`; Gage R&R rejects invalid column ID types, missing required IDs, and unknown fields with `invalid_gage_rr_options`. Frontend analysis error guidance now explains both codes.
- `categorical.two_proportion`, `categorical.chi_square_association`, and `quality.capability` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_two_proportion_options`, `invalid_chi_square_options`, or `invalid_capability_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- `hypothesis.one_way_anova`, `hypothesis.kruskal_wallis`, and `quality.run_chart` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_one_way_anova_options`, `invalid_kruskal_wallis_options`, or `invalid_run_chart_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- `quality.individuals_chart`, `quality.subgroup_chart`, and `quality.gage_run_chart` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_individuals_chart_options`, `invalid_subgroup_chart_options`, or `invalid_gage_run_chart_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- `eda.descriptive`, `regression.pearson`, and `regression.xy_correlation` now validate runner-boundary options through typed contracts. They reject malformed payloads with `invalid_descriptive_options`, `invalid_pearson_options`, or `invalid_xy_correlation_options` before row snapshot/result artifacts are written, and frontend analysis error guidance now explains these codes.
- Quality/DOE partial reference coverage was strengthened without adding new executable methods. `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`, and `doe.factorial_design` now have fixture-backed regression tests for existing formulas, warnings, redaction behavior, design SHA-256, and deterministic run ordering; independent industrial package fixtures for capability and Gage R&R remain future work.
- The first report/export stabilization slice is available for stored analysis results. `POST /api/v1/analysis-runs/{analysis_id}/exports/json` revalidates the stored result checksum, writes an atomic `analysis_result_json_export` artifact, records it in `analysis_artifacts`, returns a typed frontend-synchronized response, and does not expose internal workspace paths.
- Stored analysis history is available through `GET /api/v1/analysis-runs?dataset_version_id={id}&limit=50&offset=0`. The response is metadata-only, paginated, newest-first, includes stale/result/artifact counts plus `has_more`, and does not expose result payloads, raw cell values, or internal paths. The endpoint supports metadata-only `method_id`, `status`, `stale`, and `result_available` filters. The frontend Workbench now has a saved-analysis section that refreshes history, filters by method/status/stale/result availability, pages through stored runs, marks stale runs, and restores a stored result through the checksum-validated result API.
- Stored analysis comparison is available through `GET /api/v1/analysis-runs/comparison?left_analysis_id={left_id}&right_analysis_id={right_id}`. The endpoint checksum-validates both stored result envelopes and returns metadata-only compatibility/difference output without exposing result payloads, raw cell values, or internal paths. The Workbench history panel now lets users select left/right saved runs and view method/version/dataset/summary compatibility plus provenance/result-hash differences.
- Compatible stored `eda.descriptive` comparisons now include method-specific saved-summary deltas for common columns. The comparison uses only the already persisted descriptive result payloads, reports left/right/delta for N and numeric summary metrics, and does not reread canonical rows or recompute statistics.
- Compatible stored `hypothesis.one_sample_t` comparisons now include method-specific saved-result deltas for response identity, run settings, sample summary metrics, contrast statistic/p-value/CI, and effect-size fields. The comparison uses only checksum-validated stored result envelopes and does not reread canonical rows or recompute t-tests.
- Compatible stored `hypothesis.two_sample_t` comparisons now include method-specific saved-result deltas for response/group identity, group set/order compatibility, run settings, group summary metrics by stored group index, contrast statistic/p-value/CI, and effect-size fields. The comparison does not expose group-label values, reread canonical rows, or recompute t-tests.
- Compatible stored `hypothesis.paired_t` comparisons now include method-specific saved-result deltas for before/after identity, run settings, complete-pair exclusion counts, paired-sample summaries, contrast statistic/p-value/CI, and effect-size fields. The comparison uses only stored result envelopes and does not reread canonical rows or recompute t-tests.
- Compatible stored `hypothesis.equivalence_tost` comparisons now include method-specific saved-result deltas for response identity, equivalence bounds/reference settings, lower/upper one-sided tests, TOST decision/p-value, confidence interval, and effect-size fields. The comparison uses only stored result envelopes and does not reread canonical rows or recompute TOST statistics.
- Created JSON/CSV/HTML analysis result exports can be listed through `GET /api/v1/analysis-runs/{analysis_id}/exports`. The response exposes export IDs, kind, media type, SHA-256, creation time, and a download endpoint only. The Workbench export panel now shows recent exports with download actions. Export security tests cover HTML escaping/CSP, CSV formula-injection sanitization, nosniff download headers, ETag SHA-256 metadata, checksum mismatch recovery, and no internal path exposure.
- The Workbench now includes beginner-facing statistical role guidance, purpose-based method helper cards, and a common preflight explanation panel. These sections explain Response/Group/Predictor/Event/Order/Subgroup/Gage/spec roles, show what can go wrong if a role is misassigned, map user questions to candidate method IDs, and clarify N/exclusions/missingness/assumptions before execution. Helper cards only select a method for review; they do not auto-run analyses, and planned/disabled methods remain visually non-executable.
- Dedicated DOE design reports are available through `GET /api/v1/doe-designs/{design_id}/report.html`. The response is a self-contained static HTML download built from verified design metadata plus stored response series, with escaped text and no internal path exposure; it does not create or imply DOE effects, OLS, ANOVA, diagnostics, or chart results.
- `docs/method_versioning.md` now defines the method-version operating policy for patch/minor/major bumps, frontend-only changes, reference fixture updates, and no-silent-migration behavior. `docs/statistical_method_audit_matrix.md` records the independent reference backlog for partial-coverage methods including `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`, `doe.factorial_design`, and `regression.linear_model`.
- Analysis provenance now builds `build_commit` consistently by preferring `Settings.git_commit` and falling back to `DATALAB_GIT_COMMIT`; provenance tests continue to assert that raw paths, original filenames, and raw cell values are not exposed.
- `docs/statistical_method_audit_matrix.md` now includes method-by-method verification depth for reference fixtures, hand tests, API contract coverage, edge/failure tests, effect/CI definitions, and known limitation visibility. Partial coverage for `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`, and `doe.factorial_design` is recorded explicitly.
- Rows preview remains intentionally conservative: each paginated preview verifies the full canonical JSONL artifact before returning a page. `docs/datasets.md` and `docs/storage.md` now record the large-dataset cost and future cache/index/hash improvement candidates.
- Paginated row preview now verifies the full canonical JSONL artifact before returning any preview page, so a small `limit` cannot bypass final row count, byte size, SHA-256, row-index, column-count, or value-type checks.
- Schema PATCH now treats unchanged display name, measurement level, role, and unit payloads as no-ops. No-op PATCH keeps the same `schema_hash` and does not mark existing analysis runs stale; real schema changes still mark existing runs stale.
- Generic analysis-run result envelopes now carry runtime/build provenance fields for Python version, platform, `Settings.git_commit` with `DATALAB_GIT_COMMIT` fallback, and NumPy/SciPy package versions without exposing raw paths or raw cell values.
- Common analysis-run execution helpers for row snapshot artifacts, filter row freezing, provenance construction, canonical result/config JSON, result paths, successful result persistence, and compensating file cleanup now live in `services/analysis_run_execution.py` so method-family runner modules can be split without circular imports.
- `analysis_runs.py` dispatches 25 generic methods through the shared `MethodExecutionHandler` registry. The five `execution_mode=dedicated` methods (`regression.predict`, `regression.response_optimizer`, Factorial, RSM, and Bayesian) remain on typed source/design APIs; sending any of them to the generic endpoint returns `analysis_method_uses_dedicated_api` without creating a run or fake result.
- `docs/statistical_method_audit_matrix.md` records the current registry, execution path, method-level tests, effect/provenance coverage, and known limitations for all 30 stable method IDs.
- `docs/ci_status.md` records the Windows workflow trigger configuration and the current limitation that authenticated remote GitHub Actions run listing was not available from this environment.
- Latest local Windows validation after the beginner role guidance and purpose-helper slice: `scripts/check.ps1` passed with backend pytest 387 tests, frontend Vitest 54 tests, frontend lint/typecheck, and frontend build.
- EDA, categorical, hypothesis, quality, and simple generic regression runner modules now use the shared `store_succeeded_analysis_result` helper for result JSON writing, checksum calculation, analysis run/artifact metadata insertion, and result-file cleanup on metadata insert failure. `regression.linear_model` uses a regression-specific manifest-aware persistence wrapper that preserves `regression_model_manifest` artifact registration and cleanup.
- Backend API contract tests now assert the persistence boundary explicitly: result-only runner modules must not import low-level metadata insert or file-write primitives, while `regression.linear_model` keeps the manifest-aware regression-model insert path.

## Checklist

| Area | Status | Evidence |
| --- | --- | --- |
| Safe upload API | Done for initial slice | `POST /api/v1/datasets` |
| Paste dataset API | Done for current slice | `POST /api/v1/datasets/paste` stores pasted spreadsheet text with raw SHA-256 provenance and reuses parsing confirmation |
| Raw preservation | Done | UUID workspace path plus SHA-256 metadata |
| File validation | Done for envelope | extension/type mismatch, empty, size limit, binary text rejection, XLSX container checks |
| Parser options | Done for initial slice | text encoding/delimiter/header/data-start suggestions, default `N/T` missing-token support, XLSX sheet-selection warning |
| Parsing confirmation | Done for delimited text and basic XLSX | `POST /api/v1/datasets/{dataset_id}/confirm-parsing`, including headerless data after preamble and first/named XLSX sheet parsing |
| Raw upload integrity recheck | Done | confirm-parsing streams the preserved raw file and rejects SHA-256/size mismatch with a stable 409 error before canonical artifact creation |
| Immutable dataset version | Done for initial slice | `dataset_versions`, version `v1`, schema hash |
| Dataset columns | Done for initial slice | `dataset_columns`, original names plus unique display names |
| Dataset version lookup | Done | `GET /api/v1/datasets/{dataset_id}/versions`, `GET /api/v1/dataset-versions/{version_id}` |
| Dataset schema API | Done | `GET/PATCH /api/v1/dataset-versions/{version_id}/schema` |
| Rows preview API | Done for canonical versions | `GET /api/v1/dataset-versions/{version_id}/rows?offset=0&limit=25`, `limit <= 100`, reads canonical JSONL rows |
| Basic profile/preflight API | Done for canonical versions | `GET /api/v1/dataset-versions/{version_id}/profile`, aggregate counts/warnings, canonical artifact metadata, duplicate-row count, memory estimate, no raw value samples |
| Profile summary artifact | Done for delimited text | profile scans persist raw-value-free `profile_summary` JSON artifacts, include schema/canonical hashes, and reuse matching artifacts without churn |
| Date/time preflight | Done for delimited text | column-level parse counts, min/max, format candidates, timezone-aware/naive counts, mixed-format and mixed-timezone warnings without coercion |
| Dataset UI | Done for B0/profile/paste staging slices | upload, text/plain paste staging grid/raw mode, parsing confirmation with header/no-header comparison, Context Bar, schema controls, Bayesian sample role preset, 10/25/50/100-row canonical paging/jump/inspector, profile/preflight table, rendered through `AppChrome`, `useDatasetWorkflow`, `usePastedDatasetDraft`, and split dataset-preparation components |
| Analysis method registry | Done for current methods | `GET /api/v1/analysis-methods`, 6 modules, 30 stable available method IDs: 25 generic and five dedicated. Dedicated cards show `사용 가능 · 전용 워크플로`; no fake result is returned from the generic route. |
| Analysis run request guard | Done for current methods | `POST /api/v1/analysis-runs` executes the 25 generic methods. Predict, Response Optimizer, Factorial, RSM, and Bayesian return `analysis_method_uses_dedicated_api` with their typed route. |
| Analysis run status/cancel API | Done for B0 storage/run slice | `GET/DELETE /api/v1/analysis-runs/{analysis_id}` skeleton |
| Analysis result retrieval API | Done for available inline methods | `GET /api/v1/analysis-runs/{analysis_id}/result` validates stored result path and SHA-256 before returning the envelope |
| Filter snapshot row freezing | Done for available inline methods | creates `analysis_row_snapshot` artifacts with filter hash, canonical artifact hash, included row counts, and row ranges for supported filters |
| Frontend filter controls | Done for Workbench shell; execution binding for available inline methods | common Workbench slot renders supported AND filter controls for dataset-backed methods; current API payload serialization covers the current twenty-four analysis-run methods; DOE design generation is dataset-independent |
| Basic XLSX parser | Done for current slice | stdlib ZIP/XML reader confirms first or named sheet, writes canonical JSONL rows, and keeps formula recalculation/display formatting out of scope |
| Job status/cancel API | Done for B0 storage/run slice | `GET/DELETE /api/v1/jobs/{job_id}` skeleton |
| Six-module navigation shell | Done for B0 third slice | frontend catalog fetch, module selector, planned/disabled method cards |
| Six-module Workbench shell | Done for current slice | selected method details, `/analysis/{module_id}/{method_id}` restore with legacy hash fallback, route-selected analysis page rendering through `appRoute` and `WorkspaceRouter`, split `AnalysisPage`/`AnalysisShell`/`AnalysisWorkbench`/`DescriptiveAnalysisPanel` components, `useAnalysisSelection` route state, common data/role/option/preflight/run/result step rail, method-specific role/option/preflight/result guidance for all 30 methods, no analysis-run execution controls for planned/disabled methods; `quality.gage_rr` has balanced crossed preflight plus executable ANOVA result UI and `quality.gage_run_chart` has executable diagnostic chart UI |
| Common analysis schemas | Started | request, filter snapshot, warning, provenance, result envelope, run status, and job status schemas exist |
| `eda.descriptive` | Done for first B1 slice | pure calculation module, dataset-version streaming reader, inline API execution, result JSON persistence, minimal UI result table |
| `eda.graphical_summary` | Done for current B1 slice plus frontend chart renderer | pure stdlib calculation module for histogram, boxplot, Q-Q, and ECDF chart-data payloads; dataset-version streaming reader; inline API execution; result JSON persistence; inline SVG histogram, box plot, Q-Q plot, ECDF, and summary table UI |
| `eda.normality` | Done for first B1 slice plus frontend Q-Q renderer | SciPy-backed Shapiro-Wilk, Anderson-Darling, and deterministic Q-Q point payloads; canonical row reader; persisted result JSON; row snapshot provenance; inline SVG Q-Q plot UI plus result table; grouped normality remains unsupported with stable error |
| `eda.equal_variances` | Done for current B1 slice | SciPy-backed Brown-Forsythe and Levene(mean) tests; grouped response design; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result tables; no automatic downstream method switching |
| `hypothesis.one_sample_t` | Done for current B2 slice | SciPy-backed one-sample t-test; explicit reference mean; CI, p-value, df, Cohen dz, Hedges-corrected effect; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result table; no automatic method switching from diagnostics |
| `hypothesis.paired_t` | Done for current B2 slice | SciPy-backed paired t-test for wide before/after numeric measurement columns; complete-pair exclusion counts; mean difference, CI, p-value, df, Cohen dz, Hedges-corrected effect; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result table; long format remains out of scope |
| `hypothesis.one_sample_wilcoxon` | Done for current B2 slice | SciPy-backed one-sample signed-rank test; explicit reference location; exact/asymptotic method records; zero/tie handling; W statistic, p-value, signed-rank sums, rank-biserial; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result table; not described as a median-only test |
| `hypothesis.two_sample_t` | Done for first B2 slice | SciPy-backed Welch default and explicit pooled Student t-test; exact two-group response design; CI, p-value, df, Hedges g; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result tables; no automatic method switching from diagnostics |
| `hypothesis.mann_whitney` | Done for current B2 slice | SciPy-backed Mann-Whitney U; exact/asymptotic p-value handling; tie exact request rejection; rank summaries, U, p-value, rank-biserial, common-language probability; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result tables; not described as a median-only test |
| `hypothesis.kruskal_wallis` | Done for current B2 slice | SciPy-backed Kruskal-Wallis for independent 3-or-more-group response designs; tie-corrected H, df, p-value, epsilon-squared; Dunn/Holm post-hoc only after significant overall test; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result tables; not described as a median-only test |
| `hypothesis.one_way_anova` | Done for current B2 slice | SciPy-backed standard one-way ANOVA for independent grouped numeric responses; ANOVA table, F statistic, p-value, eta squared, omega squared; Tukey-Kramer post-hoc only after significant overall test; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result tables; Welch ANOVA and Games-Howell remain out of scope |
| `hypothesis.equivalence_tost` | Done for current B2 slice | SciPy-backed one-sample mean TOST; explicit reference mean and user-defined raw-unit lower/upper equivalence bounds; lower/upper one-sided tests, TOST p-value, `1 - 2 * alpha` CI, Cohen dz; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result table; paired/two-sample TOST remain out of scope |
| `categorical.one_proportion` | Done for current B2 slice | SciPy-backed exact binomial 1-proportion test for one binary response column plus explicit event level; Wilson or Clopper-Pearson CI; event/non-event counts, p-value, Cohen h; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result table; event/trial summary input remains out of scope |
| `categorical.two_proportion` | Done for current B2 slice | SciPy-backed Fisher exact 2-proportion test for one binary response column grouped by exactly two usable groups plus explicit event level; Newcombe-Wilson CI for proportion difference; risk ratio and odds ratio where finite; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; minimal UI result tables; summary-count input remains out of scope |
| `categorical.chi_square_association` | Done for current B2 slice plus frontend residual heatmap | SciPy-backed Pearson chi-square independence test for two categorical columns; observed/expected counts, row/column/total percentages, standardized residuals, p-value, Cramer's V, expected-count diagnostics, sparse 2x2 Fisher recommendation without automatic fallback; canonical row reader; persisted result JSON; row snapshot provenance; reference fixture; inline standardized residual heatmap UI plus result tables; summary-count input and Fisher exact p-value remain out of scope |
| `regression.pearson` | Done for first C1 slice plus frontend scatter renderer | SciPy-backed Pearson product-moment correlation for two numeric columns; complete-case exclusions, sample summaries, covariance, r, r-squared, p-value, Fisher z CI, capped raw-string-free scatterplot point payload, non-causation/linearity/outlier warnings, canonical row reader, persisted result JSON, row snapshot provenance, reference fixture, inline SVG scatter plot UI, and result table; Spearman/Kendall, generated scatterplot artifact export, model fitting, and prediction remain out of scope |
| `regression.xy_correlation` | Done for second C1 slice plus frontend heatmap renderer | SciPy-backed pairwise Pearson X-Y correlation matrix for numeric X/Y column sets; pair-level N/exclusions, covariance, r, r-squared, p-value, Fisher z CI, failed-cell error codes, non-causation/linearity/outlier warnings, canonical row reader, persisted result JSON, row snapshot provenance, reference fixture, inline correlation heatmap UI, and result table; Spearman/Kendall, p-value adjustment, scatterplot artifact, model fitting, and prediction remain out of scope |
| `regression.linear_model` | Done for third C1 slice plus safe model-manifest/preflight/backend-prediction/frontend-prediction/chart hardening | NumPy/SciPy-backed OLS for one numeric response and numeric/categorical main-effect predictors plus selected numeric quadratic and numeric-by-numeric interaction terms; categorical predictors use deterministic treatment coding with reference levels; complete-case exclusions, coefficient SE/t/p/CI, R², adjusted R², residual standard error, F test, VIF/condition diagnostics, residual/leverage/Cook's distance diagnostics, capped diagnostic points, non-causation and assumption warnings, canonical row reader, persisted result JSON, row snapshot provenance, safe JSON `regression_model_manifest` storage with prediction basis, checksum-validated `GET /api/v1/regression-models/{model_id}`, `POST /api/v1/regression-models/{model_id}/prediction-preflight` for schema/column/range/category checks, `POST /api/v1/regression-models/{model_id}/predictions` for backend predicted means plus mean-response and individual prediction intervals, checksum-recorded NDJSON storage, paged prediction row retrieval, full checksum-validated prediction CSV export, paged confirmed-version target catalog and explicit target selection, frontend preflight/paged-result display, inline residual/fitted and leverage/Cook diagnostic charts, inline prediction interval chart, reference fixture, and result tables; categorical interactions, robust covariance, and exported diagnostic chart artifacts remain out of scope |
| `quality.individuals_chart` | Done for D1 I-MR slice plus numeric/datetime order-column and explicit I-chart rules | stdlib I-MR chart for one numeric measurement column using canonical row order by default or an optional numeric/datetime order column sorted ascending with canonical row position tie-breaks; timezone-aware datetime order values compare in UTC and mixed timezone awareness is rejected; complete-case exclusions for value/order columns, arithmetic mean center line, moving-range sigma estimate with `MRbar / d2`, I chart 3-sigma limits, MR chart `D3/D4` limits, I/MR limit signals, I chart same-side centerline signal, I chart strict trend signal, I chart alternating signal, I chart 2-of-3 beyond 2-sigma zone signal, I chart 4-of-5 beyond 1-sigma zone signal, I chart 15-within-1-sigma signal, I chart 8-outside-1-sigma signal, zero moving-range rejection, canonical row reader, persisted result JSON, row snapshot provenance, unit/API tests, and inline SVG I/MR chart UI; full Nelson/Western Electric rules, subgroup charts, capability analysis, and chart export artifacts remain out of scope |
| `quality.subgroup_chart` | Done for D1 Xbar-R/Xbar-S fixed-subgroup slice | stdlib Xbar-R/Xbar-S chart for one numeric measurement column and one subgroup ID column using canonical first-seen subgroup order; fixed subgroup size 2-10 only; complete-case exclusions for value/subgroup columns; Xbar center as mean of subgroup means, R center as average subgroup range, S center as average subgroup sample standard deviation, standard `A2/D3/D4` and `A3/B3/B4` constants, Xbar/R/S control limits, Xbar/R/S single-point limit signals, zero average range/stddev rejection, varying subgroup-size rejection, canonical row reader, persisted result JSON, row snapshot provenance, unit/API tests, and inline SVG Xbar/R/S chart UI with Xbar-R/Xbar-S selector; varying-size limits, full Nelson/Western Electric rules, capability analysis, Gage R&R, and chart export artifacts remain out of scope |
| `quality.run_chart` | Done for D1 slice plus numeric/datetime order-column, oscillation, and exact run-count signals | stdlib median run chart for one numeric measurement column using canonical row order by default or an optional numeric/datetime order column sorted ascending with canonical row position tie-breaks; timezone-aware datetime order values compare in UTC and mixed timezone awareness is rejected; complete-case exclusions for value/order columns, median center line, above/below median run count, tie-to-median exclusion policy, strict 6-point trend signal, strict 14-point oscillation signal, exact conditional run-count clustering/mixture signals, no control limits, canonical row reader, persisted result JSON, row snapshot provenance, unit/API tests, inline SVG run chart UI, and run/signal tables; control chart rules and chart export artifacts remain out of scope |
| `quality.capability` | Done for D1 normal capability first slice | stdlib normal capability for one numeric measurement column with LSL and/or USL plus optional target; complete-case exclusions; overall sample SD, within sigma from canonical adjacent `MRbar/d2`; Cp/Cpk and Pp/Ppk side indices, one-sided spec handling, observed nonconformance counts/ppm, expected normal-model nonconformance probabilities/ppm, histogram/fitted-normal/spec-line payload, canonical row reader, persisted result JSON, row snapshot provenance, unit/API tests, and inline SVG histogram UI; Cpm, confidence intervals, non-normal capability, transformations, subgroup pooled sigma, automatic stability approval, and chart export artifacts remain out of scope |
| `quality.gage_rr` | Done for C3 balanced crossed ANOVA first slice | SciPy-backed balanced crossed ANOVA Gage R&R for one numeric measurement column plus part/operator/replicate columns; complete-case exclusions; strict balanced crossed design validation; ANOVA table; raw and final variance components; repeatability, reproducibility, total Gage R&R, part-to-part, total variation; % contribution; % study variation; ndc; negative raw variance component reporting with final variance clamped to zero; no part/operator/replicate raw labels; canonical row reader; persisted result JSON; row snapshot provenance; unit/API tests; minimal frontend preflight/run/result table UI. Nested, unbalanced, expanded Gage R&R, tolerance/process variation, pooling selection, component/interaction plots, and chart export artifacts remain out of scope. |
| `quality.gage_run_chart` | Done for C3 diagnostic chart first slice | stdlib balanced crossed Gage Run Chart for one numeric measurement column plus part/operator/replicate columns and optional numeric/datetime order column; complete-case exclusions; strict balanced crossed design validation; capped indexed chart points; overall, part-index, and operator-index summaries; diagnostic-only warnings; no part/operator/replicate raw labels; canonical row reader; persisted result JSON; row snapshot provenance; unit/API tests; minimal inline SVG frontend chart UI. Component/interaction plots, faceting, exported chart artifacts, variance components, and paged chart payloads remain out of scope. |
| `doe.factorial_design` | Done for D1 design-asset plus response-entry/report slices | stdlib 2-level full factorial design generation for 2-6 factors with low/high/unit, replicates, center points, optional blocks, randomization on/off and seed, preserved standard/run order, deterministic design SHA-256, schema v7 design/version/run metadata, schema v8 run response metadata, dedicated create/read/response/report API, generic analysis-run guard, unit/API/migration tests, and minimal Workbench run-table preview/response-entry UI. Effects, OLS/ANOVA, diagnostics, alias structure, DOE charts, and stored export artifacts remain out of scope. |
| Analysis stale handling | Done for schema edits | schema PATCH marks existing runs for the same dataset version `stale=true` in the same SQLite transaction |
| Metadata migration | Done | schema version `8`, `datasets`, `dataset_versions`, `dataset_columns`, `dataset_artifacts`, `analysis_runs`, `analysis_artifacts`, `jobs`, `regression_models`, `experiment_designs`, `experiment_design_versions`, `experiment_runs`, `experiment_run_responses`, upgrade tests from versions 1, 2, 3, 4, 5, 6, and 7 |
| Canonical parsed artifact | Done for stdlib delimited-text slice | UTF-8 JSONL canonical rows plus JSON manifest are materialized with SHA-256 metadata; Parquet remains candidate after `pyarrow` review |
| Canonical row reader | Done for profile/current dataset-backed methods | profile and the current twenty-four analysis-run methods read validated canonical rows; corrupt/missing artifact metadata returns explicit recovery errors without raw fallback |
| Full profile | Started | aggregate profile/preflight, duplicate-row analysis, memory estimate, persisted profile artifacts, and conservative date/time preflight exist; richer distribution/outlier profiling remains |
| Statistical analysis | Started | `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart`; `doe.factorial_design` is design generation only; no fake charts or mock results |
| Statistical dependency smoke | Done for current SciPy-backed methods | `scripts/install-stat-deps-spike.ps1`, `scripts/check-stat-deps.ps1`, `scripts/stat_dependency_smoke.py`, `scripts/validate_stat_dependency_smoke.py`, `scripts/render_stat_dependency_record.py`, `scripts/generate_normality_reference.py`, `scripts/validate_normality_reference.py`, and `docs/stat_dependency_spike.md` provide opt-in Windows `.venv` install/smoke/result-record/reference-generation flow for NumPy/SciPy Shapiro-Wilk, Anderson-Darling, Levene, and Brown-Forsythe; NumPy 2.2.6/SciPy 1.15.3 are production-pinned and reused for `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, and `regression.linear_model` |

## Latest Validation

Current development validation on 2026-07-19:

- Worktree based on clean pushed SHA
  `695caf2fcfb6a8336ddd29afc77d4ed22911dc63`: full `scripts/check.ps1`
  passed in 841.8 seconds with backend 784, frontend 152, direct
  OpenAPI/frontend contract 155, tutorial Markdown 18-block verification, and
  all lint/type/build gates. The 18-section real-API tutorial smoke passed in
  19.0 seconds and Chromium E2E passed in 78.0 seconds through lazy Help/Report
  plus all retained critical paths. Main measured 496.98 kB / 118.70 kB gzip
  without the 500 kB warning. This Windows 10/Node 24 host result is development
  evidence, not the Windows 11/Node 22 release gate. This evidence was captured
  before the slice's commit/push, and remote Actions were not checked because
  `gh` is unavailable.

Historical validation begins below. Last validated on 2026-07-06:

- Current beginner role guidance and purpose-helper slice: the Workbench now
  renders always-visible statistical role guidance, purpose-based method helper
  cards, and a common preflight explanation panel. The helper maps beginner
  questions to existing method IDs without adding calculations or auto-running
  analyses, and planned/disabled methods are shown as non-executable. WSL
  frontend typecheck, lint, and Vitest passed with 54 tests. Full Windows
  `scripts/check.ps1` passed with backend pytest 387 tests, frontend Vitest 54
  tests, frontend lint/typecheck, and frontend build.
- Current linear model runner split: `regression.linear_model` now uses a
  module-owned runner function in
  `backend/app/services/analysis_runners_regression.py` alongside
  `regression.pearson` and `regression.xy_correlation`. Linear-model-specific
  safe JSON model-manifest payload construction, diagnostics redaction, and
  manifest path helpers moved with the runner. The dedicated stored-model
  prediction API path is unchanged. Statistical calculations, result schemas,
  availability, storage paths, migrations, and frontend behavior were
  unchanged. Targeted Windows pytest for regression-owned handler registry
  coverage, representative linear-model executions, and manifest cleanup passed
  with 7 selected tests. Backend ruff format, ruff check, and mypy passed.
  Full Windows `scripts/check.ps1` passed with backend pytest 270 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.
- Current regression correlation runner split: `regression.pearson` and
  `regression.xy_correlation` now use module-owned runner functions in
  `backend/app/services/analysis_runners_regression.py`; `analysis_runs.py`
  only wires those method IDs through the shared `MethodExecutionHandler`
  registry. This intermediate state was superseded by the current linear model
  runner split. Statistical calculations, result schemas, availability, storage
  paths, migrations, and frontend behavior were unchanged. Targeted Windows
  pytest for regression-owned handler registry coverage and representative
  Pearson/X-Y executions passed with 3 selected tests. Backend ruff format,
  ruff check, and mypy passed. Full Windows `scripts/check.ps1` passed with
  backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck,
  and frontend build.
- Current hypothesis runner split: `hypothesis.one_sample_t`,
  `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`,
  `hypothesis.two_sample_t`, `hypothesis.mann_whitney`,
  `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, and
  `hypothesis.equivalence_tost` now use module-owned runner functions in
  `backend/app/services/analysis_runners_hypothesis.py`; `analysis_runs.py`
  only wires those method IDs through the shared `MethodExecutionHandler`
  registry. Statistical calculations, result schemas, availability, storage
  paths, migrations, and frontend behavior were unchanged. Targeted Windows
  pytest for hypothesis-owned handler registry coverage and representative
  hypothesis executions passed with 9 selected tests. Backend ruff format,
  ruff check, and mypy passed. Full Windows `scripts/check.ps1` passed with
  backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck,
  and frontend build.
- Current categorical runner split: `categorical.one_proportion`,
  `categorical.two_proportion`, and `categorical.chi_square_association` now
  use module-owned runner functions in
  `backend/app/services/analysis_runners_categorical.py`; `analysis_runs.py`
  only wires those method IDs through the shared `MethodExecutionHandler`
  registry. Statistical calculations, result schemas, availability, storage
  paths, migrations, and frontend behavior were unchanged. Targeted Windows
  pytest for categorical-owned handler registry coverage and representative
  categorical executions passed with 4 selected tests. Backend ruff format,
  ruff check, and mypy passed. Full Windows `scripts/check.ps1` passed with
  backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck,
  and frontend build.
- Current `quality.gage_run_chart` slice: balanced crossed Gage Run Chart is available for one numeric measurement column plus part/operator/replicate columns and an optional order column. The method reads canonical rows, persists row snapshot provenance and result JSON, supports checksum-validated result retrieval, and returns diagnostic-only warning metadata, balanced design counts, overall summary, per-part-index and per-operator-index summaries, capped indexed chart points, canonical row positions, and order-source metadata. It rejects unbalanced or underspecified Gage designs instead of downgrading to a simple run chart, and it redacts raw part/operator/replicate labels from result payloads. Frontend renders `GageRunChartPanel` with role selectors, optional order selector, inline SVG indexed diagnostic chart, and part/operator summary tables. Targeted backend pytest for `test_gage_run_chart.py` and selected Gage/API/catalog contracts passed with 7 selected tests. Backend ruff and mypy passed. Frontend lint, typecheck, and Vitest passed with 39 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 252 tests, frontend Vitest 39 tests, frontend lint/typecheck, and frontend build.
- Current `doe.factorial_design` slice: 2-level full factorial design generation, response entry, and a checksum-verified static HTML design report are available through dedicated DOE design routes, not through the generic analysis-run endpoint. The generator preserves standard order and run order, supports deterministic randomization seed, replicates, center points, optional blocks, factor low/high/unit metadata, explicit run-count rejection, and `design_sha256`. Schema v7 stores design/version/run records, schema v8 stores numeric run response records, and readback/report rendering verifies the design checksum before returning payloads. Response saving requires exactly one finite numeric value for every current run_order and does not mutate factor/run metadata. Frontend renders `FactorialDesignPanel` with inputs, actual run-table preview, and response name/unit/value entry. Effects, OLS/ANOVA, diagnostics, alias structure, DOE charts, and stored export artifacts remain out of scope. WSL temporary backend targeted pytest for `test_metadata_store.py` and `test_api_contracts.py` passed with 95 tests; WSL temporary backend full ruff/mypy/pytest passed with 263 backend tests; WSL frontend lint, typecheck, Vitest with 40 tests, and build passed; Windows `scripts/check.ps1` passed with backend pytest 263 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

- Current `quality.gage_rr` slice: balanced crossed ANOVA Gage R&R is available for one numeric measurement column plus part/operator/replicate columns. The preflight API still reports design readiness without raw identifier labels, and `POST /api/v1/analysis-runs` now executes the validated design from canonical rows, persists row snapshot provenance and result JSON, and supports checksum-validated result retrieval. The method returns an ANOVA table, raw/final variance components, repeatability, reproducibility, total Gage R&R, part-to-part, total variation, % contribution, % study variation, ndc, negative variance component clamp policy, interaction no-pooling policy, and persistent design/independence/redaction warnings. It rejects unbalanced designs and zero total variation instead of fabricating output. Frontend renders `GageRrPreflightPanel` with role selectors, readiness summary, execution control, ANOVA table, variance component table, and headline %Study/NDC values. Targeted backend pytest for `test_gage_rr.py`, `test_gage_rr_preflight.py`, and selected Gage/API/catalog contracts passed with 12 selected tests. Frontend typecheck and Vitest passed with 38 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 247 tests, frontend Vitest 38 tests, frontend lint/typecheck, and frontend build.
- Current `quality.capability` slice: normal capability analysis is available for one numeric measurement column with LSL and/or USL plus optional target. The method reads canonical rows, applies complete-case exclusions, computes overall sample SD, within sigma from canonical adjacent `MRbar/d2`, Cp/Cpk and Pp/Ppk side indices, observed below/above/total nonconformance counts and ppm, expected normal-model nonconformance probabilities and ppm, row snapshot provenance, and histogram/fitted-normal/spec-line payloads. It rejects missing spec limits, invalid spec ordering, target outside spec, too-small N, and zero sigma instead of fabricating indices. Frontend renders LSL/USL/target controls, inline SVG histogram with fitted normal curve and spec lines, capability index table, and observed/expected nonconformance table. Targeted backend pytest for `test_capability.py` and selected capability API/catalog contracts passed with 6 selected tests. Frontend typecheck and Vitest passed with 37 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 237 tests, frontend Vitest 37 tests, frontend lint/typecheck, and frontend build.
- Current `quality.subgroup_chart` slice: Xbar-R and Xbar-S charts are available for one numeric measurement column and one subgroup ID column. Subgroups are ordered by first appearance in canonical rows, fixed subgroup size 2-10 is required, varying subgroup size is rejected with `subgroup_chart_varying_subgroup_size_unsupported`, all-zero average subgroup range is rejected with `subgroup_chart_zero_average_range`, and all-zero average subgroup sample standard deviation is rejected with `subgroup_chart_zero_average_stddev` instead of fabricating limits. The method computes complete-case exclusions, Xbar center line, R/S center line, standard `A2/D3/D4` and `A3/B3/B4` constants, Xbar/R/S control limits, Xbar/R/S single-point limit signals, row snapshot provenance, and capped chart payloads. Frontend renders inline SVG Xbar/R/S charts with value/subgroup selectors, Xbar-R/Xbar-S selector, control limit lines, and signal tables. Targeted backend pytest for `test_subgroup_chart.py` and selected subgroup-chart API contracts passed with 10 selected tests. Frontend typecheck and Vitest passed with 36 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 232 tests, frontend Vitest 36 tests, frontend lint/typecheck, and frontend build.
- Current `quality.individuals_chart` slice: I-MR chart is available for one numeric measurement column using canonical row order by default or an optional numeric/datetime order column. Numeric and datetime order columns sort ascending, use canonical row position as the stable tie-breaker, record order exclusions/tie counts, and do not expose raw order or datetime values in chart payloads. Timezone-aware datetime values compare in UTC; mixed aware/naive datetime order values are rejected with a stable error. The method computes complete-case exclusions, arithmetic mean center line, adjacent moving ranges, `MRbar / d2` sigma estimate, I chart 3-sigma limits, MR chart `D3/D4` limits, I/MR single-point limit signals, I chart same-side centerline signals, I chart strict increasing/decreasing trend signals, I chart alternating signals, I chart 2-of-3 beyond 2-sigma zone signals, I chart 4-of-5 beyond 1-sigma zone signals, I chart 15-within-1-sigma signals, I chart 8-outside-1-sigma signals, row snapshot provenance, and capped chart payloads without fake signals. Constant all-equal series are rejected with `individuals_chart_zero_moving_range` instead of fabricating limits. Frontend renders inline SVG I and MR charts with value/order selectors, control limit lines, and signal tables. Targeted backend pytest for `test_individuals_chart.py` and selected individuals-chart API contracts passed with 26 selected tests. Frontend typecheck and Vitest passed with 35 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 222 tests, frontend Vitest 35 tests, frontend lint/typecheck, and frontend build.
- Current `quality.run_chart` slice: median run chart is available for one numeric measurement column using canonical row order by default or an optional numeric/datetime order column. Numeric and datetime order columns sort ascending, use canonical row position as the stable tie-breaker, record order exclusions/tie counts, and do not expose raw order or datetime values in chart payloads. Timezone-aware datetime values compare in UTC; mixed aware/naive datetime order values are rejected with a stable error. The method computes complete-case exclusions, median center line, above/below median run count, tie-to-median exclusion policy, strict 6-point trend signals, strict 14-point oscillation signals, and exact conditional run-count clustering/mixture signals, with row snapshot provenance and a capped chart payload without control limits or fake signals. Frontend renders the run chart as inline SVG with value/order selectors, trend/oscillation/clustering/mixture signal counts, and run/signal tables. Targeted backend pytest for `test_run_chart.py` and selected run-chart API contracts passed with 22 selected tests. Frontend typecheck and Vitest passed with 34 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 196 tests, frontend Vitest 34 tests, frontend lint/typecheck, and frontend build.
- Current chi-square/regression chart renderer slice: `categorical.chi_square_association` renders existing observed/expected/standardized residual payloads as a standardized residual heatmap. `regression.linear_model` renders existing diagnostic points as residual/fitted and leverage/Cook charts, and existing prediction rows as a predicted mean/CI/prediction interval chart. No new statistical calculations, fake chart values, chart dependencies, CDN calls, or exported chart artifacts were added. Frontend `typecheck`, `lint`, Vitest, and build passed. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 174 tests, frontend Vitest 33 tests, and frontend build.
- Current visualization renderer slice: `eda.normality` now renders its real Q-Q point payload as inline SVG Q-Q plots, `regression.pearson` now returns a capped deterministic scatterplot point payload and renders it as an inline SVG scatter plot, and `regression.xy_correlation` now renders existing pairwise Pearson r values as a heatmap. Pearson scatter payloads omit row indices, raw strings, and source paths; no fake chart values or new statistical methods were added. Targeted backend pytest for `test_pearson.py` and `test_api_contracts.py -k "pearson"` passed with 6 selected tests. Frontend `typecheck`, `lint`, Vitest, and build passed. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 174 tests, frontend Vitest 33 tests, and frontend build.
- Current `regression.linear_model` slice: OLS linear model fitting is available for one numeric response and numeric/categorical main-effect predictors with complete-case handling, treatment-coded categorical reference levels, selected numeric quadratic terms, selected numeric-by-numeric interaction terms, coefficient standard errors, t statistics, p-values, confidence intervals, R², adjusted R², residual standard error, F test, VIF/condition diagnostics, residual/leverage/Cook's distance diagnostics, capped diagnostic points, safe JSON model manifest storage with OLS prediction basis, checksum-validated model manifest retrieval, stored-model prediction preflight, backend `regression.predict` prediction values and intervals, frontend target selection plus preflight and paged prediction result display, and persistent warnings for non-causation and OLS assumptions. Prediction preflight validates manifest checksum, source row snapshot, target canonical rows, schema hash mismatch, display-name fallback mapping, missing/non-numeric values, numeric extrapolation, and unseen categorical levels. Prediction execution reuses that preflight path, rejects error-severity issues, reconstructs the design matrix from the stored manifest, keeps the first 1,000 predicted rows in the compatible POST response, and atomically stores all valid rows in a checksum-recorded NDJSON artifact without raw predictor values. The paged row endpoint validates checksum, row schema, and expected count before returning up to 200 rows; the dedicated streaming wide CSV export includes every verified prediction row without raw predictors. A paged confirmed-version catalog returns display metadata without raw rows, paths, or hashes; the UI defaults to the active version, permits explicit cross-dataset target selection, invalidates stale prediction state on changes, and renders 25-row result pages. Backend API/browser coverage includes cross-dataset execution, the 1,005-row boundary, artifact tampering, metadata-failure cleanup, stored result checksum mismatch, categorical treatment-coded reconstruction, numeric quadratic/interaction reconstruction, and missing prediction-basis recovery. Categorical interactions, factor-by-numeric interactions, robust covariance, and diagnostic chart artifacts remain out of scope. Earlier validation counts in this historical section are superseded by the latest CI status and Progress Update entries below.
- Current `regression.pearson` slice: Pearson product-moment correlation is available for two numeric columns with complete-case handling, sample summaries, covariance, r, r-squared, p-value, Fisher z confidence interval, and persistent warnings that correlation is not causation, Pearson summarizes linear association, and outliers can dominate the result. Spearman/Kendall, scatterplot artifacts, expanded OLS modeling, model manifests, and prediction remain out of scope. Targeted backend pytest for `test_pearson.py` and `test_api_contracts.py` passed with 38 tests. Backend ruff for touched Pearson backend files passed. Frontend typecheck, lint, and Vitest passed with 31 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 149 tests, frontend Vitest 31 tests, and frontend build.
- Current `regression.xy_correlation` and analysis error-placement slice: X-Y pairwise Pearson correlation is available for numeric X/Y column sets with pair-level N/exclusions, covariance, r, r-squared, p-value, Fisher z confidence interval, cell-level failure codes instead of fake statistics, persistent correlation warnings, and stored result retrieval from canonical rows. Analysis execution errors no longer route through the dataset-preparation top error box on analysis pages, and `two_sample_t_requires_exactly_two_groups` has a readable action message. Spearman/Kendall, p-value adjustment, scatterplot artifacts, expanded OLS modeling, model manifests, and prediction remain out of scope. Targeted backend pytest for `test_xy_correlation.py` and `test_api_contracts.py` passed with 39 tests. Backend ruff and mypy passed. Frontend typecheck, lint, and Vitest passed with 32 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 154 tests, frontend Vitest 32 tests, and frontend build.
- Current `hypothesis.equivalence_tost` slice: one-sample mean TOST is available for one numeric response column with an explicit reference mean and user-defined raw-unit lower/upper equivalence bounds. The method computes complete-case exclusions, sample summary, lower/upper one-sided tests, TOST p-value, `1 - 2 * alpha` CI, Cohen dz, Hedges-corrected effect, equivalence-bound warnings, and provenance from validated canonical rows. Paired/two-sample TOST, standardized-margin input, automatic bound suggestions, and automatic method switching remain out of scope. Targeted backend pytest for `test_equivalence_tost.py` and `test_api_contracts.py` passed with 37 tests. Backend ruff for touched TOST files passed. Frontend lint, typecheck, and Vitest passed with 29 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 144 tests, frontend Vitest 29 tests, and frontend build.
- Current `categorical.chi_square_association` slice: Pearson chi-square association testing is available for two categorical columns with complete-case handling, observed/expected counts, row/column/total percentages, standardized residuals, expected-count diagnostics, p-value, and Cramer's V. Sparse 2x2 tables record a Fisher exact recommendation without calculating or fabricating a Fisher p-value. Summary-count contingency input and automatic method switching remain out of scope. Targeted backend pytest for `test_chi_square_association.py` and `test_api_contracts.py` passed with 36 tests. Frontend lint, typecheck, and Vitest passed with 28 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 139 tests, frontend Vitest 28 tests, and frontend build.
- Current `hypothesis.one_way_anova` slice: standard one-way ANOVA is available for independent grouped numeric responses with complete-case handling, group summaries, ANOVA table, F statistic, p-value, eta squared, omega squared, design/assumption warnings, and Tukey-Kramer post-hoc comparisons only when the omnibus test is significant. Welch ANOVA, Games-Howell, summary-statistic input, and automatic diagnostic-based switching remain out of scope. Targeted backend pytest for `test_one_way_anova.py` and `test_api_contracts.py` passed with 35 tests. Frontend lint, typecheck, and Vitest passed with 27 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 134 tests, frontend Vitest 27 tests, and frontend build.
- Current `categorical.two_proportion` slice: binary-response-by-two-group 2-proportion testing is available with an explicit event level, Fisher exact p-value, Newcombe-Wilson CI for the proportion difference, risk ratio and odds ratio where finite, design/sparse-cell warnings, and provenance from validated canonical rows. Summary event/trial input remains out of scope. Targeted backend pytest for `test_two_proportion.py` and `test_api_contracts.py` passed with 34 tests. Frontend lint, typecheck, and Vitest passed with 26 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 129 tests, frontend Vitest 26 tests, and frontend build.
- Current `categorical.one_proportion` slice: binary-column 1-proportion testing is available with an explicit event level, exact binomial p-value, Wilson or Clopper-Pearson CI, event/non-event counts, sample proportion, Cohen h, design warnings, and provenance from validated canonical rows. Event/trial summary-count input remains out of scope. Targeted backend pytest for `test_one_proportion.py` and `test_api_contracts.py` passed with 33 tests. Frontend lint, typecheck, and Vitest passed with 25 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 124 tests, frontend Vitest 25 tests, and frontend build.
- Current `hypothesis.kruskal_wallis` slice: independent 3-or-more-group rank testing is available with tie-corrected H, df, p-value, epsilon-squared, group rank summaries, and Dunn/Holm post-hoc comparisons only when the overall test is significant. The method computes N/exclusions, tie correction, post-hoc skip reason, design warnings, and provenance from validated canonical rows. Targeted backend pytest for `test_kruskal_wallis.py` and `test_api_contracts.py` passed with 32 tests. Frontend typecheck and Vitest passed with 24 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 119 tests, frontend Vitest 24 tests, and frontend build.
- Current `eda.equal_variances` slice: NumPy 2.2.6 and SciPy 1.15.3 are reused from the production-pinned normality slice; `eda.equal_variances` is available and computes real Brown-Forsythe and Levene(mean) results from validated canonical rows. Output includes group N/mean/median/variance/std summaries and a persistent warning that the result must not automatically switch downstream pooled/Welch or ANOVA choices. Targeted backend pytest for `test_equal_variances.py` and `test_api_contracts.py` passed with 26 tests. Frontend typecheck, lint, and Vitest passed with 18 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 89 tests, frontend Vitest 18 tests, and frontend build.
- Current `hypothesis.one_sample_t` slice: the method compares one numeric response with an explicit reference mean and computes N/exclusions, sample summary, mean difference, CI, t statistic, df, p-value, Cohen dz, Hedges-corrected effect, and provenance from validated canonical rows. Targeted backend pytest for `test_one_sample_t.py` and `test_api_contracts.py` passed with 28 tests. Frontend typecheck passed. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 99 tests, frontend Vitest 20 tests, and frontend build.
- Current `hypothesis.paired_t` slice: wide paired testing is available for two numeric before/after measurement columns, with pair difference defined as `after - before`. The method computes complete-pair exclusions, before/after means, difference summary, CI, t statistic, df, p-value, Cohen dz, Hedges-corrected effect, design warnings, and provenance from validated canonical rows. Targeted backend pytest for `test_paired_t.py` and `test_api_contracts.py` passed with 31 tests. Frontend typecheck, lint, and Vitest passed with 23 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 114 tests, frontend Vitest 23 tests, and frontend build.
- Current `hypothesis.two_sample_t` slice: Welch is the default and pooled Student is available only through explicit user selection. The method computes N/exclusions, group summaries, mean difference, CI, t statistic, df, p-value, Cohen's d, Hedges g, and provenance from validated canonical rows. Targeted backend pytest for `test_two_sample_t.py` and `test_api_contracts.py` passed with 27 tests. Frontend typecheck, lint, and Vitest passed with 19 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 94 tests, frontend Vitest 19 tests, and frontend build.
- Current `hypothesis.one_sample_wilcoxon` slice: one-sample signed-rank testing is available for one numeric response and an explicit reference location. The method computes N/exclusions, zero/tie counts, signed-rank W statistic, p-value, exact/asymptotic method records, signed-rank sums, rank-biserial effect size, symmetry/interpretation warnings, and provenance from validated canonical rows. Targeted backend pytest for `test_one_sample_wilcoxon.py` and `test_api_contracts.py` passed with 30 tests. Frontend typecheck and Vitest passed with 22 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 109 tests, frontend Vitest 22 tests, and frontend build.
- Current `hypothesis.mann_whitney` slice: exact/asymptotic Mann-Whitney U is available for independent exactly two-group response designs. The method computes N/exclusions, group rank summaries, U statistic, p-value, rank-biserial, common-language probability, tie/exact warnings, and provenance from validated canonical rows. Targeted backend pytest for `test_mann_whitney.py` and `test_api_contracts.py` passed with 29 tests. Frontend typecheck and Vitest passed with 21 tests. Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1` passed with backend pytest 104 tests, frontend Vitest 21 tests, and frontend build.
- Current Windows statistical dependency spike: native Windows `.venv` smoke passed with Python 3.10.11, NumPy 2.2.6, and SciPy 1.15.3. `scripts/install-stat-deps-spike.ps1` installed wheel-only candidate packages, `scripts/check-stat-deps.ps1` produced `logs/stat-dependency-smoke.json`, `scripts/validate_stat_dependency_smoke.py` passed, `scripts/render_stat_dependency_record.py` rendered the record, `scripts/generate_normality_reference.py` created `backend/tests/reference/fixtures/normality_scipy_reference.json`, and `scripts/validate_normality_reference.py` passed. A first smoke-only check before install failed with `stat_dependency_missing` for `numpy`, as expected. Full `scripts/check.ps1` passed with backend pytest 78 tests and frontend Vitest 16 tests. NumPy/SciPy are now production-pinned for the current SciPy-backed EDA methods.
- Current `eda.normality` slice: NumPy 2.2.6 and SciPy 1.15.3 are production-pinned in `backend/pyproject.toml`; `eda.normality` is available and computes real Shapiro-Wilk, Anderson-Darling, and deterministic Q-Q point payloads from validated canonical rows. Grouped normality rejects with `normality_grouping_not_supported`; normality output includes a persistent warning that it must not be used as an automatic downstream method switch. Full `scripts/check.ps1` passed with backend pytest 84 tests and frontend Vitest 17 tests.
- Current `eda.graphical_summary` slice: histogram, boxplot, Q-Q, and ECDF chart-data payloads are computed from canonical rows and rendered in the frontend as inline SVG charts with a summary table. `npm --prefix ./frontend run typecheck`, `npm --prefix ./frontend run lint`, `npm --prefix ./frontend run test -- --run` with 33 Vitest tests, `npm --prefix ./frontend run build`, and full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 173 tests, frontend Vitest 33 tests, and frontend build.
- Historical normality dependency-gate slice: before production pinning, WSL `python3` had no SciPy installed and `eda.normality` remained `planned`; no p-values, test statistics, or fake result payloads were added in that gate-hardening slice.
- Current statistical dependency smoke slice: added opt-in Windows PowerShell install/smoke/result-record/validation/reference-generation flow for NumPy/SciPy import and Shapiro-Wilk, Anderson-Darling, Levene, and Brown-Forsythe calculations. It is not part of base `scripts/check.ps1` yet. `git diff --check`, `python3 -m compileall -q scripts/stat_dependency_smoke.py scripts/validate_stat_dependency_smoke.py scripts/render_stat_dependency_record.py scripts/generate_normality_reference.py scripts/validate_normality_reference.py backend/tests/unit/test_stat_dependency_smoke_tools.py backend/tests/unit/test_normality_reference_fixture.py backend/tests/unit/test_normality_reference_validator.py`, and touched-script line-length scan passed under WSL. The normality input fixture load smoke passed with 3 cases. Direct WSL `python3 scripts/stat_dependency_smoke.py` and `python3 scripts/generate_normality_reference.py` returned the expected `python_version_unsupported` JSON because WSL Python is 3.12.3, while this project requires Python 3.10.
- Current `useDatasetWorkflow` slice: `git diff --check`, WSL Node `v24.14.0` `npm --prefix ./frontend run typecheck`, WSL `npm --prefix ./frontend run lint`, WSL `npm --prefix ./frontend run test -- --run` with 15 Vitest tests, and WSL `npm --prefix ./frontend run build` passed after delegating dataset upload/paste/parsing/schema/preview/profile workflow state and handlers from `App.tsx` to `useDatasetWorkflow`. `powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion"` still fails from WSL before command execution with a WSL socket/vsock error, so full `scripts/check.ps1` still needs to be re-run from native Windows PowerShell.
- Current `AppChrome` slice: `git diff --check`, WSL Node `v24.14.0` `npm --prefix ./frontend run typecheck`, WSL `npm --prefix ./frontend run lint`, WSL `npm --prefix ./frontend run test -- --run` with 14 Vitest tests, and WSL `npm --prefix ./frontend run build` passed after delegating sidebar/topbar/dataset context rendering from `App.tsx` to `AppChrome`. `powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion"` still fails from WSL before command execution with a WSL socket/vsock error, so full `scripts/check.ps1` still needs to be re-run from native Windows PowerShell.
- Current `WorkspaceRouter` slice: `git diff --check`, WSL Node `v24.14.0` `npm --prefix ./frontend run typecheck`, WSL `npm --prefix ./frontend run lint`, WSL `npm --prefix ./frontend run test -- --run` with 13 Vitest tests, and WSL `npm --prefix ./frontend run build` passed after delegating dataset-vs-analysis page rendering from `App.tsx` to `WorkspaceRouter`. `powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion"` still fails from WSL before command execution with a WSL socket/vsock error, so full `scripts/check.ps1` still needs to be re-run from native Windows PowerShell.
- Current route-selected page slice: `git diff --check`, WSL `npm --prefix ./frontend run typecheck`, WSL `npm --prefix ./frontend run lint`, WSL `npm --prefix ./frontend run test -- --run`, and WSL `npm --prefix ./frontend run build` passed after adding `appRoute` and rendering dataset/analysis pages conditionally by path. Windows PowerShell commands from WSL still fail before command execution with a WSL socket/vsock error, so full `scripts/check.ps1` still needs to be re-run from native Windows PowerShell.
- Current dataset-preparation component decomposition slice: `git diff --check`, WSL `npm --prefix ./frontend run typecheck`, WSL `npm --prefix ./frontend run lint`, WSL `npm --prefix ./frontend run test -- --run`, and WSL `npm --prefix ./frontend run build` passed after restoring the missing Linux native optional bindings in the local mixed Windows/WSL `node_modules`. Windows PowerShell commands from WSL still fail before command execution with a WSL socket/vsock error, so full `scripts/check.ps1` still needs to be re-run from native Windows PowerShell.
- Current Workbench component decomposition slice: `git diff --check`, WSL `npm --prefix ./frontend run typecheck`, WSL `npm --prefix ./frontend run lint`, WSL `npm --prefix ./frontend run test -- --run`, and WSL `npm --prefix ./frontend run build` passed after splitting `AnalysisPage`, `AnalysisShell`, `DescriptiveAnalysisPanel`, and `useAnalysisSelection`. Windows PowerShell commands from WSL still fail before command execution with a WSL socket/vsock error, so full `scripts/check.ps1` still needs to be re-run from native Windows PowerShell.
- Current Workbench-level filter UI slice: `git diff --check`, WSL `npm --prefix ./frontend run typecheck`, and WSL `npm --prefix ./frontend run lint` passed. WSL Vitest could not start because the Windows-installed `node_modules` lacks `@rolldown/binding-linux-x64-gnu`. Windows PowerShell commands from WSL are currently failing before command execution with a WSL vsock/socket error, so Windows Vitest and full `scripts/check.ps1` still need to be re-run once the WSL/Windows bridge recovers.
- Paste dataset intake slice: targeted backend dataset upload pytest passed with 28 tests. Backend ruff passed and mypy passed over 36 source files. Windows frontend `typecheck`, `lint`, and Vitest passed with 9 tests. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed, including backend pytest with 65 tests, frontend lint, frontend typecheck, Vitest with 9 tests, and frontend build.
- Basic XLSX parsing-confirmation slice: targeted backend dataset upload pytest passed with 27 tests. Backend ruff passed and mypy passed over 36 source files. Windows frontend `typecheck`, `lint`, and Vitest passed with 9 tests. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed, including backend pytest with 64 tests, frontend lint, frontend typecheck, Vitest with 9 tests, and frontend build.
- Frontend filter controls slice: Windows frontend `typecheck`, `lint`, and Vitest passed with 9 tests. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed, including backend ruff/format/mypy over 35 source files, backend pytest with 63 tests, frontend lint, frontend typecheck, Vitest with 9 tests, and frontend build.
- Route-level selected-analysis restore slice: Windows frontend `typecheck`, `lint`, and Vitest passed with 7 tests. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed, including backend ruff/format/mypy over 35 source files, backend pytest with 63 tests, frontend lint, frontend typecheck, Vitest with 7 tests, and frontend build.
- Current data integrity/reproducibility PR: targeted backend pytest passed with 42 tests (`test_dataset_upload.py`, `test_api_contracts.py`) on Windows Python 3.10.11. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed, including formatting check, mypy over 35 source files, backend pytest with 61 tests, frontend lint, frontend typecheck, Vitest with 6 tests, and frontend build.
- Filter snapshot row-freezing slice: targeted backend pytest passed with 52 tests (`test_api_contracts.py`, `test_dataset_upload.py`, `test_metadata_store.py`) on Windows Python 3.10.11. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed after formatting, including backend ruff, mypy over 35 source files, backend pytest with 62 tests, frontend lint, frontend typecheck, Vitest with 6 tests, and frontend build.
- Non-empty filter expression slice: targeted backend pytest passed with 53 tests (`test_api_contracts.py`, `test_dataset_upload.py`, `test_metadata_store.py`) on Windows Python 3.10.11. Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` passed, including backend ruff, mypy over 35 source files, backend pytest with 63 tests, frontend lint, frontend typecheck, Vitest with 6 tests, and frontend build.
- Targeted persisted-profile-artifact validation: backend dataset upload/profile plus metadata pytest passed with 32 tests; backend API contract pytest passed with 13 tests; backend ruff passed; backend mypy passed with 35 source files; frontend typecheck and lint passed.
- Targeted date/time preflight validation: backend dataset upload/profile pytest passed with 24 tests; backend ruff passed; backend mypy passed with 35 source files; frontend typecheck and lint passed.
- Full `scripts/check.ps1`: passed after the date/time preflight slice; backend pytest 56 tests, frontend lint/typecheck/Vitest 6 tests/build passed.
- Full `scripts/check.ps1`: passed after the persisted profile artifact slice; backend pytest 55 tests, frontend lint/typecheck/Vitest 6 tests/build passed.
- Targeted backend pytest: passed, 19 dataset upload/parsing/profile tests including preamble-plus-headerless TXT and basic profile warnings.
- Targeted backend pytest: passed, 15 descriptive/API contract tests including hand-checkable descriptive statistics and `eda.descriptive` API execution.
- Backend ruff check: passed.
- Backend mypy: passed, 33 source files.
- Frontend typecheck and lint: passed after adding profile/preflight UI.
- Frontend unit tests: passed, 4 Vitest tests total including Bayesian role preset and analysis hash selection.
- Manual HTTP smoke with `input_example/example data for Bayesian optimization.txt`: upload suggestion returned tab delimiter, `has_header=False`, `data_start_row=10`; parsing confirmation returned `row_count=64`, `column_count=34`; default missing tokens included `N/T`; first preview page treated an `N/T` value as missing; `eda.descriptive` succeeded for 3 selected numeric columns, with first selected column `column_3`, `n_used=64`, `mean=35.9953125`.
- Full `scripts/check.ps1`: passed after the canonical reader adoption slice; backend pytest 53 tests, frontend lint/typecheck/Vitest 6 tests/build passed.
- Targeted canonical reader validation after the reader-adoption slice: backend dataset upload/profile plus API contract pytest passed with 35 tests; backend ruff passed; backend mypy passed with 35 source files.
- Targeted frontend validation after the shared Workbench component split: `npm --prefix ./frontend run typecheck` passed and `npm --prefix ./frontend run lint` passed.
- Targeted canonical/profile validation after the canonical JSONL slice: backend dataset upload/profile and metadata pytest passed with 28 tests; backend ruff passed; backend mypy passed with 34 source files; frontend typecheck and lint passed.
- Targeted frontend validation after the six-module Workbench guidance slice: `npm --prefix ./frontend run typecheck` passed, `npm --prefix ./frontend run lint` passed, Windows `npm --prefix .\frontend run test -- --run` passed with 5 Vitest tests. WSL Vitest remains unsupported with the current Windows-installed `node_modules` because the Linux Rolldown optional native binding is absent.
- Manual HTTP smoke before profile/preflight: backend `http://127.0.0.1:8000/api/v1/analysis-methods` returned the latest catalog with `eda.descriptive` available; frontend `http://127.0.0.1:5179/` returned 200.
- Manual HTTP smoke with `input_example/example data for Bayesian optimization.txt` after profile/preflight: upload and parsing confirmation returned `row_count=64`, `column_count=34`; `GET /api/v1/dataset-versions/{version_id}/profile` returned 34 column profiles and flagged `column_1` as `possible_identifier`.
- Windows Node: `v24.17.0`
- Windows `npm --prefix .\frontend ci`: passed, 0 vulnerabilities
- Earlier WSL `npm --prefix ./frontend run test -- --run` failed because the Windows-installed native `node_modules` lacked Linux native optional bindings. The current local WSL workspace has the needed Rolldown and Lightning CSS native binaries restored for validation, while PowerShell/Windows Node remains the supported repository workflow.
- `pyarrow` local availability check: `pyarrow_available=False`; no dependency was added.

## Risks And Notes

- Statistical: `eda.descriptive` produces descriptive statistics. `eda.graphical_summary` produces histogram, boxplot, Q-Q, and ECDF chart-data payloads and now renders them as inline SVG charts in the frontend. `eda.normality` produces SciPy-backed Shapiro-Wilk p-values, Anderson-Darling critical-value decisions, and Q-Q point payloads rendered as inline SVG Q-Q plots. `eda.equal_variances` produces SciPy-backed Brown-Forsythe and Levene(mean) results. `hypothesis.one_sample_t` produces one-sample mean comparisons with CI and Cohen dz. `hypothesis.paired_t` produces wide paired before/after mean-difference comparisons with complete-pair exclusions, CI, and Cohen dz. `hypothesis.one_sample_wilcoxon` produces one-sample signed-rank comparisons with W, p-value, signed-rank sums, rank-biserial, exact/asymptotic method records, zero/tie handling, and a warning not to describe it as a median-only test. `hypothesis.two_sample_t` produces Welch or explicit pooled independent two-group mean comparisons with CI and Hedges g. `hypothesis.mann_whitney` produces independent two-group rank comparisons with U, p-value, rank-biserial, common-language probability, exact/asymptotic method records, and a warning not to describe it as a median-only test. `hypothesis.kruskal_wallis` produces independent 3-or-more-group rank comparisons with tie-corrected H, df, p-value, epsilon-squared, Dunn/Holm post-hoc comparisons after significant overall tests, and a warning not to describe it as a median-only test. `hypothesis.one_way_anova` produces standard one-way ANOVA comparisons with ANOVA table, F statistic, p-value, eta squared, omega squared, and Tukey-Kramer post-hoc comparisons after significant overall tests. `hypothesis.equivalence_tost` produces one-sample mean TOST with user-defined raw-unit equivalence bounds, two one-sided p-values, TOST p-value, `1 - 2 * alpha` CI, and Cohen dz. `categorical.one_proportion` produces binary-column exact binomial 1-proportion comparisons with event/non-event counts, Wilson or Clopper-Pearson CI, p-value, and Cohen h. `categorical.two_proportion` produces binary-response-by-two-group Fisher exact comparisons with Newcombe-Wilson CI for proportion difference plus risk ratio and odds ratio where finite. `categorical.chi_square_association` produces Pearson chi-square association comparisons with observed/expected counts, residuals, p-value, expected-count diagnostics, and Cramer's V rendered as a standardized residual heatmap; sparse 2x2 tables only recommend Fisher exact. `regression.pearson` produces real Pearson correlation plus a capped scatterplot point payload rendered as an inline SVG scatter plot, `regression.xy_correlation` renders pairwise r values as a heatmap, and `regression.linear_model` produces real regression outputs plus residual/fitted, leverage/Cook, and prediction interval charts with non-causation warnings. `quality.run_chart` produces a median run chart from canonical/numeric/datetime order with explicit no-control-limit interpretation, strict trend/oscillation definitions, exact conditional run-count clustering/mixture definitions, canonical row provenance, and no fake signal fallback. `quality.gage_run_chart` produces a measurement-system diagnostic chart payload with balanced crossed design validation, indexed part/operator/replicate context, raw-label redaction, and no variance-component fallback. `doe.factorial_design` creates a design asset/run table and stores numeric response values only; it does not calculate DOE effects, ANOVA, diagnostics, or fake response results. Diagnostic outputs explicitly warn that they must not automatically switch downstream methods. No fake charts or mock results are added.
- Privacy/security: committed tests use synthetic bytes only. The local `input_example/` file was used only for manual HTTP smoke and was not copied into fixtures or committed.
- Compatibility: upload, parsing-confirmation, schema update, and rows preview logic use Python 3.10-compatible stdlib streaming, `pathlib`, SQLite, and FastAPI `UploadFile`.
- Migration/storage: schema version advanced to `8`; upgrades from schema versions `1`, `2`, `3`, `4`, `5`, `6`, and `7` are tested.
- Performance: upload reads in 1 MB chunks and enforces `DATALAB_MAX_UPLOAD_BYTES`; confirm-parsing streams delimited text or XLSX worksheet XML for header, row count, column type candidates, and canonical JSONL materialization; rows preview streams only until the requested page is filled; profile streams the dataset once, caps per-column unique tracking at 1,000 values, caps duplicate-row signature tracking at 100,000 signatures, uses conservative stdlib date/time candidate parsing, and returns a memory estimate.
- Dependency: `python-multipart==0.0.32` was added for FastAPI multipart uploads and recorded in `docs/dependency_review.md`.
- XLSX: basic stdlib parsing confirmation exists for worksheet cached values. Formula recalculation, merged-cell expansion, hidden row/column handling, and Excel display-format/date serial restoration remain out of scope.

## Historical Gate B Planning Note

This early planning note is superseded by the numbered progress updates below
and is retained only as change history.

The next slice should stay narrow and avoid mock statistics:

1. Implement the next real method only after its statistical dependency, reference fixtures, warning metadata, and provenance contract are ready.
2. Keep methods non-executable until they have real code, references, and tests.
3. Follow the latest numbered update for the current allowed slice.

## Progress Update 94 - Analysis Result JSON Export UI

Completed in current working tree:

- Added a minimal frontend JSON export action for succeeded saved analysis
  results.
- The Workbench now shows the export action directly under the selected
  method's execution panel and keeps export failures in the same local analysis
  area.
- The UI calls the existing checksum-validating
  `POST /api/v1/analysis-runs/{analysis_id}/exports/json` API and displays
  matching export size, short SHA-256, and stale status metadata.
- Export status is matched by `analysis_id` so a previous method's export is
  not shown for the newly selected result.
- Added frontend render tests for the JSON export action and matching export
  metadata.
- Kept CSV, HTML, PDF, chart image export, report composition, file download
  response, and code export out of scope for this slice.

Validation:

- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 42 tests after
  stabilizing the SSR hash assertion.
- WSL `npm --prefix ./frontend run lint`: passed.
- `git diff --check`: passed.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 363 tests, frontend lint/typecheck, frontend Vitest 42 tests,
  and frontend build.

Remaining limitations:

- The UI creates a JSON export artifact and shows its metadata, but does not yet
  download the file.
- CSV/HTML/PDF/report/code exports remain unimplemented.
- Export retention/deletion policy is still inherited from generic analysis
  artifact storage.

Next PR:

- Define CSV table export and HTML report contracts, including formula
  injection protection and path-exposure tests, before adding broader report
  UI.

## Progress Update 95 - Analysis Result CSV Export Contract

Completed in current working tree:

- Added `POST /api/v1/analysis-runs/{analysis_id}/exports/csv`.
- The CSV export service reloads the stored analysis result through the same
  checksum-validated path as result retrieval and JSON export.
- The first CSV artifact contract is a generic long-form `section,path,value`
  table over the stored result envelope, so it adds no new statistics and works
  across current methods.
- CSV cells are escaped for spreadsheet formula injection when they start, after
  leading whitespace, with `=`, `+`, `-`, or `@`, or begin with tab/newline
  control characters.
- The API response exposes export ID, media type, SHA-256, size, source result
  SHA-256, stale flag, row count, columns, and preview rows without exposing
  internal artifact paths.
- Added frontend API type/client wiring and a minimal CSV action/status next to
  the existing JSON export action.
- Kept HTML/PDF report composition, file download responses, method-specific
  CSV report tables, chart image export, and code export out of scope.

Validation:

- Targeted Windows pytest for JSON/CSV export contract tests passed with 4
  selected tests.
- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 43 tests after
  stabilizing the SSR row-count assertion.
- WSL `npm --prefix ./frontend run lint`: passed.
- Targeted backend ruff check and backend mypy passed.
- `git diff --check`: passed.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 365 tests, frontend lint/typecheck, frontend Vitest 43 tests,
  and frontend build.

Remaining limitations:

- CSV export is a generic envelope table, not a polished method-specific report
  table.
- The UI creates JSON/CSV export artifacts and shows metadata, but does not yet
  download the files.
- HTML report composition remains unimplemented.

Next PR:

- Add artifact download responses for created JSON/CSV exports, or define the
  first HTML report envelope with path-exposure and formula-injection tests.

## Progress Update 96 - Analysis Result Export Download

Completed in current working tree:

- Added `GET /api/v1/analysis-runs/{analysis_id}/exports/{export_id}/download`
  for stored JSON/CSV analysis-result exports.
- Download lookup uses `analysis_artifacts` by `analysis_id` and `export_id`,
  accepts only `analysis_result_json_export` and `analysis_result_csv_export`,
  validates the stored relative path, file existence, and SHA-256 before
  returning bytes, and does not expose internal workspace paths.
- Download responses use attachment filenames derived only from analysis/export
  IDs and set `X-Content-Type-Options: nosniff`.
- Added stable recovery errors for download failures:
  `analysis_export_not_found`, `analysis_export_path_invalid`,
  `analysis_export_file_missing`, and `analysis_export_checksum_mismatch`.
- Added frontend download wiring for the existing JSON/CSV export metadata cards,
  with download failures shown inside the export panel instead of the global page
  header.
- Kept HTML/PDF report composition, method-specific CSV report tables, chart
  image export, and code export out of scope.

Validation:

- Targeted Windows pytest for the export download route passed with 2 selected
  tests.
- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 44 tests.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 367 tests, frontend lint/typecheck, frontend Vitest 44 tests,
  and frontend build.

Remaining limitations:

- CSV export remains a generic envelope table, not a method-specific report
  table.
- HTML/PDF report composition and chart artifact export remain unimplemented.
- Export retention/deletion policy is still inherited from generic analysis
  artifact storage.

Next PR:

- Define the first HTML report envelope or method-specific CSV/table export
  contract with path-exposure, checksum, and formula-injection tests.

## Progress Update 97 - Analysis Result HTML Report Export

Completed in current working tree:

- Added `POST /api/v1/analysis-runs/{analysis_id}/exports/html` for the first
  stored analysis-result HTML report artifact.
- The HTML report export reloads the stored result through the existing
  checksum-validated result path before writing any artifact.
- The report artifact is recorded as `analysis_result_html_report` with media
  type `text/html`, SHA-256, size, stale flag, source result SHA-256, and a
  minimal section count response.
- The first report is a static self-contained HTML envelope over the stored
  result, with escaped text values, no scripts, no external resources, no
  external services, and no internal workspace path exposure.
- Existing export download now supports JSON, CSV, and HTML report artifacts
  through the same metadata/path/checksum validation path.
- The Workbench export panel now offers `HTML 생성` and `HTML 다운로드` beside
  the JSON/CSV export actions.
- No new statistical calculation, fake statistic, or chart artifact was added.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  passed with 2 selected tests on Python 3.10.11 / win32.
- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 45 tests.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 369 tests, frontend lint/typecheck, frontend Vitest 45 tests,
  and frontend build.

Remaining limitations:

- The HTML report is a generic result-envelope report, not a polished
  method-specific statistical narrative or branded report template.
- PDF, chart image export, report composition across multiple analyses, and
  reproducible Python code export remain unimplemented.
- Export retention/deletion policy is still inherited from generic analysis
  artifact storage.

Next PR:

- Add method-specific report sections for one narrow method family, or define
  reproducible Python code export with path-exposure and provenance tests.

## Progress Update 98 - Descriptive HTML Report Section

Completed in current working tree:

- Added the first method-specific HTML report section for stored
  `eda.descriptive` results.
- The report now renders a dedicated "기술통계 요약" table with stored column
  names, N totals, N used, missing/non-numeric counts, mean, standard
  deviation, min, quartiles, median, max, and warning codes.
- The method-specific section reads only the persisted analysis result envelope;
  it does not recalculate statistics, read raw rows, or change analysis result
  schemas.
- The generic result-envelope table remains as fallback for all methods and as
  the full-detail section for descriptive reports.
- HTML escaping, no-script/no-external-resource behavior, export artifact
  checksum recording, and download checksum validation remain unchanged.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  passed with 2 selected tests on Python 3.10.11 / win32.
- Targeted backend ruff check and backend mypy passed.
- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 45 tests.
- WSL `npm --prefix ./frontend run lint`: passed.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 369 tests, frontend lint/typecheck, frontend Vitest 45 tests,
  and frontend build.

Remaining limitations:

- Only `eda.descriptive` has a method-specific HTML section.
- HTML report styling is still basic and local/static; PDF, chart image export,
  multi-analysis report composition, and Python code export remain out of
  scope.

Next PR:

- Add method-specific report sections for one more narrow family, or begin the
  reproducible Python code export contract.

## Progress Update 99 - EDA HTML Report Sections

Completed in current working tree:

- Expanded the stored-result HTML report from `eda.descriptive` only to the
  first EDA method family slice:
  - `eda.graphical_summary`;
  - `eda.normality`;
  - `eda.equal_variances`.
- Added a `그래프 요약` section with stored N, missing/non-numeric counts,
  quartiles, histogram bin count, boxplot outlier count, Q-Q point count, and
  ECDF point count.
- Added a `정규성 검정 요약` section with stored shape statistics,
  Shapiro-Wilk values, Anderson-Darling values, Q-Q point count, and warning
  codes.
- Added `등분산 검정 요약` and `등분산 그룹 요약` sections with stored Levene /
  Brown-Forsythe results and group summary statistics.
- These sections read only the persisted analysis result envelope. They do not
  re-read canonical rows, regenerate charts, recalculate statistics, or add new
  method availability.
- Generic result-envelope fallback, HTML escaping, checksum validation, static
  no-script/no-external-resource behavior, and internal path hiding remain
  unchanged.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  passed with 3 selected tests on Python 3.10.11 / win32.
- Targeted backend ruff check passed for `analysis_runs.py` and
  `test_api_contracts.py`.
- Targeted backend mypy passed for `analysis_runs.py`.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed after applying
  ruff formatting, with backend ruff check, backend ruff format check, backend
  mypy over 75 source files, backend pytest 370 tests, frontend lint/typecheck,
  frontend Vitest 45 tests, and frontend build.

Remaining limitations:

- HTML report sections are summary tables over stored JSON payloads, not
  generated chart images or a polished narrative report.
- Only EDA descriptive/graphical/normality/equal-variances methods have
  method-specific HTML sections.
- PDF, chart image export, multi-analysis report composition, and reproducible
  Python code export remain out of scope.

Next PR:

- Continue method-specific HTML sections for one narrow method family, or start
  the reproducible Python code export contract with provenance/checksum tests.

## Progress Update 100 - Hypothesis HTML Report Sections

Completed in current working tree:

- Added stored-result-only HTML report sections for the current generic
  `hypothesis.*` analysis-run methods:
  - `hypothesis.one_sample_t`;
  - `hypothesis.paired_t`;
  - `hypothesis.one_sample_wilcoxon`;
  - `hypothesis.two_sample_t`;
  - `hypothesis.mann_whitney`;
  - `hypothesis.kruskal_wallis`;
  - `hypothesis.one_way_anova`;
  - `hypothesis.equivalence_tost`.
- The report now renders a `가설 검정 요약` table with stored method, N,
  alpha, confidence level, alternative, missing policy, estimate, statistic,
  p-value, confidence interval, effect size, and equivalence-specific TOST
  fields when present.
- Added optional stored-result group and post-hoc comparison tables for methods
  whose payload includes `groups` or `posthoc.comparisons`.
- The renderer reads only the persisted result envelope. It does not re-read
  canonical rows, recalculate statistics, reinterpret hypotheses, add chart
  artifacts, or change method availability.
- Generic result-envelope fallback, HTML escaping, checksum validation, static
  no-script/no-external-resource behavior, and internal path hiding remain
  unchanged.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  passed with 4 selected tests on Python 3.10.11 / win32.
- Targeted backend ruff check passed for `analysis_runs.py` and
  `test_api_contracts.py`.
- Targeted backend mypy passed for `analysis_runs.py`.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 371 tests, frontend lint/typecheck, frontend Vitest 45 tests,
  and frontend build.

Remaining limitations:

- Hypothesis HTML sections are summary tables over stored JSON payloads, not
  a polished statistical narrative.
- Post-hoc tables are generic across ANOVA/Kruskal payloads and intentionally
  do not recalculate or reshape method-specific multiple-comparison statistics.
- PDF, chart image export, multi-analysis report composition, and reproducible
  Python code export remain out of scope.

Next PR:

- Add method-specific HTML sections for categorical or regression methods, or
  start reproducible Python code export with provenance/checksum tests.

## Progress Update 101 - Categorical And Regression HTML Report Sections

Completed in current working tree:

- Added stored-result-only HTML report sections for categorical methods:
  - `categorical.one_proportion`;
  - `categorical.two_proportion`;
  - `categorical.chi_square_association`.
- Added stored-result-only HTML report sections for correlation/regression
  methods:
  - `regression.pearson`;
  - `regression.xy_correlation`;
  - `regression.linear_model`.
- The categorical section renders N, alpha, confidence level, event level,
  event/non-event counts, sample proportion, difference estimate/CI, test
  p-value, effect size, expected-count diagnostics, group summaries, and
  aggregate contingency table counts when present.
- The regression section renders correlation metrics, pairwise X/Y correlation
  summaries, linear-model fit metrics, model ID, and coefficient estimates,
  standard errors, p-values, confidence intervals, and VIF values when present.
- These sections read only the persisted analysis result envelope. They do not
  re-read canonical rows, expose internal paths, regenerate scatter points,
  recalculate statistics, add chart artifacts, or change method availability.
- Generic result-envelope fallback, HTML escaping, checksum validation, static
  no-script/no-external-resource behavior, and internal path hiding remain
  unchanged.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  passed with 6 selected tests on Python 3.10.11 / win32.
- Targeted backend ruff check passed for `analysis_runs.py` and
  `test_api_contracts.py`.
- Targeted backend mypy passed for `analysis_runs.py`.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 373 tests, frontend lint/typecheck, frontend Vitest 45 tests,
  and frontend build.

Remaining limitations:

- Categorical and regression HTML sections are summary tables over stored JSON
  payloads, not polished statistical narratives.
- The regression section intentionally does not render raw scatterplot point
  rows or diagnostic point rows in the method-specific section.
- PDF, chart image export, multi-analysis report composition, and reproducible
  Python code export remain out of scope.

Next PR:

- Add method-specific HTML sections for quality-control methods, or start
  reproducible Python code export with provenance/checksum tests.

## Progress Update 102 - Quality HTML Report Sections

Completed in current working tree:

- Added stored-result-only HTML report sections for quality-control methods:
  - `quality.individuals_chart`;
  - `quality.subgroup_chart`;
  - `quality.run_chart`;
  - `quality.capability`;
  - `quality.gage_rr`;
  - `quality.gage_run_chart`.
- The quality section renders N, missing policy, order source, chart type,
  subgroup size/count, centerline, sigma/MR-bar, run counts, process capability
  spec/nonconformance summaries, Gage design counts, measurement summary, chart
  point counts, signal counts, and control-rule counts when present.
- Added optional quality chart, signal, capability, and Gage R&R variance
  tables over the persisted payload.
- These sections read only the persisted analysis result envelope. They do not
  re-read canonical rows, regenerate chart images, recalculate control limits,
  expose redacted Gage labels, add fake chart artifacts, or change method
  availability.
- Generic result-envelope fallback, HTML escaping, checksum validation, static
  no-script/no-external-resource behavior, and internal path hiding remain
  unchanged.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  passed with 8 selected tests on Python 3.10.11 / win32.
- Targeted backend ruff check passed for `analysis_runs.py` and
  `test_api_contracts.py`.
- Targeted backend mypy passed for `analysis_runs.py`.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 375 tests, frontend lint/typecheck, frontend Vitest 45 tests,
  and frontend build.

Remaining limitations:

- Quality HTML sections are summary tables over stored JSON payloads, not
  polished statistical narratives or image-based chart reports.
- The method-specific section intentionally avoids rendering full chart points
  and diagnostic point rows.
- PDF, chart image export, multi-analysis report composition, DOE report
  sections, and reproducible Python code export remain out of scope.

Next PR:

- Add a DOE design HTML report section, or start reproducible Python code
  export with provenance/checksum tests.

## Progress Update 103 - DOE Design HTML Report Download

Completed in current working tree:

- Added `GET /api/v1/doe-designs/{design_id}/report.html` for dedicated
  factorial DOE design reports.
- The report reuses the existing DOE design checksum verification path before
  rendering, then includes stored design metadata, factor levels, run order,
  options, and entered response series.
- The HTML is static and self-contained, escapes all text values, includes no
  scripts or external resources, and does not expose internal workspace paths.
- Kept DOE effects, OLS, ANOVA, diagnostics, alias structure, chart payloads,
  analysis-run result artifacts, fake statistics, and mock charts out of scope.
- Added API contract coverage for successful report download, escaped factor
  and response labels, path non-exposure, and checksum mismatch rejection.

Validation:

- Targeted pytest:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "factorial_design"`:
  passed with 7 selected tests on Python 3.10.11 / win32.
- Targeted backend ruff check passed for `doe_designs.py`,
  `api/v1/doe_designs.py`, and `test_api_contracts.py`.
- Targeted backend mypy passed for `doe_designs.py` and
  `api/v1/doe_designs.py`.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 377 tests, frontend lint/typecheck, frontend Vitest 45 tests,
  and frontend build.

Remaining limitations:

- DOE report is a design/response report only, not an effects or analysis
  report.
- The report is generated dynamically from verified metadata and is not yet a
  persisted export artifact.
- Frontend DOE report download wiring is not added in this slice.

Next PR:

- Add a small frontend DOE report download action, or start reproducible Python
  code export for stored analysis results.

## Progress Update 112 - One-Way ANOVA Stored-Result Comparison

Completed in current working tree:

- Extended the stored analysis comparison method-specific payload with
  `one_way_anova`.
- Added stored-result-only comparison for compatible
  `hypothesis.one_way_anova` runs.
- The comparison reports response/group column identity, group set/order
  compatibility without exposing raw group-label values, saved ANOVA settings,
  group summary deltas by stored group index, ANOVA table/test/effect-size
  deltas, and post-hoc comparison count metadata.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, recompute ANOVA statistics, or expose
  post-hoc `group_1_label`/`group_2_label` values.
- The Workbench comparison panel now renders an `일원분산분석 비교` section when
  the comparison payload contains one-way ANOVA metrics.
- Kept Welch ANOVA, Games-Howell, two-way/repeated/ANCOVA, new statistical
  calculations, method-version bumps, chart export artifacts, PDF export, and
  reproducible code export out of scope.

Validation:

- Targeted backend ruff check for the touched analysis schema/service/test
  files passed.
- Targeted frontend typecheck passed.
- Targeted backend pytest for stored comparison API contracts passed with
  6 selected tests.
- Frontend Vitest passed with 52 tests.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 386 tests, frontend lint/typecheck, frontend Vitest 52 tests,
  and frontend build.

Remaining limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, `hypothesis.two_sample_t`,
  `hypothesis.paired_t`, `hypothesis.equivalence_tost`, and
  `hypothesis.one_way_anova`.
- The one-way ANOVA comparison reports stored-result deltas only; it does not
  infer whether two saved ANOVA decisions differ in practical or statistical
  meaning beyond the recorded settings/results.
- Group comparisons are index based and deliberately avoid raw group labels;
  clearer redacted group handles can be added later if users need a more
  readable comparison table.

Next PR:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.kruskal_wallis`, or start reproducible Python code export with
  explicit data-version, provenance, checksum, and path-exposure tests.

## Progress Update 113 - Kruskal-Wallis Stored-Result Comparison

Completed in current working tree:

- Extended the stored analysis comparison method-specific payload with
  `kruskal_wallis`.
- Added stored-result-only comparison for compatible
  `hypothesis.kruskal_wallis` runs.
- The comparison reports response/group column identity, group set/order
  compatibility without exposing raw group-label values, saved rank-test
  settings, group rank-summary deltas by stored group index, H-test/effect-size
  deltas, tie-correction deltas, and post-hoc comparison count metadata.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, recompute Kruskal-Wallis statistics,
  or expose Dunn post-hoc `group_1_label`/`group_2_label` values.
- The Workbench comparison panel now renders a `Kruskal-Wallis 비교` section
  when the comparison payload contains Kruskal-Wallis metrics.
- Kept new statistical calculations, Mann-Whitney comparison, Wilcoxon
  comparison, method-version bumps, chart export artifacts, PDF export, and
  reproducible code export out of scope.

Validation:

- Targeted backend ruff check for the touched analysis schema/service/test
  files passed.
- Targeted frontend typecheck passed.
- Targeted backend pytest for stored comparison API contracts passed with
  7 selected tests.
- Frontend Vitest passed with 53 tests.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 53 tests,
  and frontend build.

Remaining limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, `hypothesis.two_sample_t`,
  `hypothesis.paired_t`, `hypothesis.equivalence_tost`,
  `hypothesis.one_way_anova`, and `hypothesis.kruskal_wallis`.
- The Kruskal-Wallis comparison reports stored-result deltas only; it does not
  infer whether two saved rank-test decisions differ in practical or
  statistical meaning beyond the recorded settings/results.
- Group and post-hoc comparisons are index/count based and deliberately avoid
  raw group labels.

Next PR:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.mann_whitney` or start reproducible Python code export with
  explicit data-version, provenance, checksum, and path-exposure tests.

## Progress Update 114 - Workbench Component Split And UX Refinement

Completed in current working tree:

- Split the growing `AnalysisWorkbench.tsx` into focused frontend components:
  `StatisticalRoleGuide.tsx`, `MethodPurposeHelper.tsx`,
  `PreflightExplanationPanel.tsx`, `AnalysisHistoryPanel.tsx`,
  `AnalysisComparisonPanel.tsx`, and `AnalysisResultExportPanel.tsx`.
- Added shared Workbench type and formatting helpers in
  `analysisWorkbenchTypes.ts` and `analysisWorkbenchUtils.ts`.
- Refined beginner guidance so selected methods surface more relevant always
  visible role guidance:
  - `hypothesis.two_sample_t` highlights Response/Group and independence
    caveats.
  - `hypothesis.paired_t` highlights Before/After and warns that it is not an
    independent two-sample design.
  - `quality.capability` highlights Response and LSL/USL/Target, with a spec
    limit versus control limit warning.
  - `quality.gage_rr` highlights Part/Operator/Replicate and balanced crossed
    design.
  - `doe.factorial_design` highlights factor/level/run-order/seed provenance.
- Refined the purpose helper so cards lead with the user question, easy Korean
  explanation, Korean method name, small method ID, required roles, and a
  caution. Planned/disabled/catalog-missing methods remain disabled and are not
  presented as executable.
- Refined saved analysis history UX with clearer current-dataset context,
  filter-state summary, stale badge copy, disabled restore action for
  unavailable results, pagination status, and restore summary.
- Refined export UX with JSON/CSV/HTML purpose descriptions, stale export
  warning, clearer download recovery message, and shorter SHA display with the
  full hash retained as metadata.
- Refined comparison UX with a plain-language compatibility note, same/different
  badges, version and dataset mismatch explanations, delta semantics, and a
  p-value delta caveat.
- Kept backend APIs, statistical calculations, method availability, method
  versions, fake results, new methods, and large redesigns out of scope.

E2E-like integration test plan:

1. Upload a delimited or XLSX file, or create a pasted dataset.
2. Confirm parsing and verify a dataset version is created.
3. Update schema roles and confirm no-op schema edits do not stale existing
   analyses.
4. Run `eda.descriptive` and verify result, provenance, history entry, and
   export availability.
5. Run `hypothesis.two_sample_t` on a valid two-group fixture and verify
   preflight copy, result warnings, and saved history.
6. Restore a saved result through the history panel.
7. Compare two saved results and verify compatible and incompatible comparison
   explanations.
8. Create and download JSON, CSV, and HTML exports.
9. Reload the app and restore the saved result again without rerunning the
   analysis.

Validation:

- `npm --prefix ./frontend run test -- --run`: passed with 58 tests.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run lint`: passed.
- `npm --prefix ./frontend run build`: passed. Vite reported the existing
  post-minification chunk-size warning.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 58 tests,
  and frontend build.

Remaining limitations:

- The E2E critical path is documented but not yet implemented in Playwright.
- The purpose helper is still guidance-only. It does not inspect selected
  columns or execute a method.
- Comparison details remain limited to the methods already supported by the
  stored-result comparison API.
- The frontend bundle still emits Vite's chunk-size warning; this PR did not add
  code splitting.

Next PR:

- Add the documented Playwright critical-path test, or continue with a narrow
  stored-result/export polish slice such as reproducible code export.

## Progress Update 115 - Playwright Critical-Path Smoke

Completed in current working tree:

- Added Python Playwright as a backend dev dependency for local browser E2E
  smoke tests only.
- Added `scripts/e2e.ps1`, an opt-in PowerShell entry point that can install the
  Chromium browser and run the E2E smoke on loopback-only test ports.
- Added `tests/e2e/critical_path.py`, which starts isolated backend/frontend
  servers, uses a temporary `DATALAB_WORKSPACE_ROOT`, and removes the workspace
  after the run unless `-KeepWorkspace` is requested.
- Automated the documented critical path:
  - create a pasted TSV dataset;
  - confirm parsing and create dataset version v1;
  - verify dataset context;
  - run `eda.descriptive`;
  - run `hypothesis.two_sample_t`;
  - create JSON, CSV, and HTML exports;
  - download the JSON export;
  - restore a saved result from analysis history;
  - compare two saved results and verify the comparison explanation is visible.
- Updated setup and dependency review docs for Playwright installation and
  browser-install behavior.
- Kept new statistical calculations, new analysis methods, fake results, CI
  browser execution, and Playwright-heavy full-suite coverage out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"`: passed and
  installed `playwright==1.61.0` with its pinned transitive dependencies.
- `.\.venv\Scripts\python.exe -m playwright install chromium`: passed and
  installed the local Chromium browser bundle.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 58 tests,
  and frontend build.

Remaining limitations:

- The E2E smoke is opt-in and is not yet part of `scripts/check.ps1` or GitHub
  Actions because browser installation and server lifecycle add runtime cost.
- The E2E flow uses a small synthetic pasted TSV fixture. File upload and XLSX
  browser upload are still covered by lower-level tests, not this browser smoke.
- The schema role update/no-op stale branch is still documented in the broader
  plan but is not exercised by this first browser smoke.

Next PR:

- Add a second browser E2E for schema role update/no-op stale behavior, or wire
  the opt-in E2E into CI with an explicit Playwright browser cache/install step.

## Progress Update 116 - Schema No-Op And Stale Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover schema-save stale behavior in
  the browser flow.
- After creating stored `eda.descriptive` and `hypothesis.two_sample_t` results,
  the E2E returns to the dataset page and clicks `스키마 저장` without changing
  schema values.
- The test refreshes saved analysis history and verifies that no stale badge is
  shown after the no-op schema save.
- The test then changes the `Value` display name to `Measurement Value`, saves
  schema, refreshes saved analysis history, and verifies both existing analysis
  runs are marked `stale · 재검토 필요`.
- Tightened navigation selectors to exact-match the sidebar `데이터셋` and `분석`
  buttons so method-card labels cannot trip Playwright strict mode.
- Kept backend stale logic, statistical calculations, method availability,
  method versions, new methods, and fake results out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 58 tests,
  and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- The browser smoke still uses pasted TSV data; file upload and XLSX browser
  flows remain future E2E slices.
- The test verifies stale badges in the UI, not direct API stale payload fields;
  backend API-level stale tests remain the lower-level source of truth.

Next PR:

- Add browser E2E coverage for file upload or XLSX upload, or wire this opt-in
  E2E into CI with explicit Playwright browser installation and caching.

## Progress Update 117 - XLSX Browser Upload E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover browser file upload with a
  synthetic `.xlsx` workbook.
- The E2E now verifies the actual file input path, upload request, parsing
  options screen, parsing confirmation, dataset version creation, row/column
  counts, and XLSX column headers.
- The XLSX fixture is generated in the test with the standard library
  `zipfile` module, so no new runtime dependency or external test file is
  required.
- Kept new statistical methods, parser feature expansion, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 58 tests,
  and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- The browser smoke now covers pasted TSV and XLSX upload. CSV upload through
  the browser remains covered by lower-level parser/API tests rather than this
  E2E.
- The E2E confirms a basic XLSX workbook shape. Multi-sheet selection and
  larger XLSX limits remain backend/parser-level coverage.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  installation/cache handling, or add a narrow browser coverage slice for CSV
  file upload and parser error recovery.

## Progress Update 118 - CSV Upload And Error-Recovery Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover browser CSV file upload after
  the XLSX upload smoke.
- Added an upload recovery check: the browser first uploads an empty `.csv`,
  verifies the stable `empty_file` error code is shown in the page alert, then
  selects a valid CSV and confirms parsing successfully.
- Used a Korean CSV filename, `브라우저-csv-upload.csv`, to keep the browser
  smoke aligned with Windows/Unicode filename expectations.
- Verified CSV parsing confirmation creates a dataset version with expected
  row/column counts and visible preview column headers.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 58 tests,
  and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- CSV and XLSX happy paths are covered in the browser, but parser option edits,
  multi-sheet XLSX selection, and malformed-row recovery remain lower-level or
  future E2E coverage.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  install/cache handling, or add a narrow browser coverage slice for parser
  option editing.

## Progress Update 119 - Parser Option Editing Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover user-edited parsing options in
  the browser.
- Added a CSV fixture where the first row is preamble metadata and the real
  header starts on row 2.
- The E2E uploads the file, enables `첫 데이터 행을 헤더로 사용`, sets `헤더 행`
  to `2`, adds `MISSING` to the missing-token list, then confirms parsing.
- Verified the created dataset version uses the edited header row by checking
  preview headers `Alpha` and `Beta`.
- Verified the edited missing-token list is reflected in canonical preview by
  checking that `MISSING` renders as `(missing)`.
- Tightened row/column count checks to the `데이터셋 컨텍스트` region so repeated
  metadata-grid text cannot trip Playwright strict mode.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 387 tests, frontend lint/typecheck, frontend Vitest 58 tests,
  and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- Header-row and missing-token editing are covered. Delimiter changes,
  encoding changes, malformed-row recovery, and multi-sheet XLSX selection
  remain lower-level or future E2E coverage.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  install/cache handling, or add a narrow browser coverage slice for delimiter
  editing.

## Progress Update 120 - Delimiter Editing Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover user-edited delimiter
  selection in the browser.
- Added a `.csv` fixture whose content is semicolon-delimited. Because CSV
  uploads default to comma, the test must change `구분자` to `semicolon` before
  confirmation.
- Verified the created dataset version uses the edited delimiter by checking
  the dataset context count and preview headers `Category` and `Value`.
- Verified representative preview cells `Left` and `20` using table-cell scoped
  selectors so UUID text cannot trip Playwright strict mode.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- Full Windows `scripts/check.ps1`: passed after delimiter browser coverage with
  backend pytest 387 tests, frontend Vitest 58 tests, frontend lint/typecheck,
  and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- Header-row, missing-token, and delimiter editing are covered. Encoding
  changes, malformed-row recovery, and multi-sheet XLSX selection remain
  lower-level or future E2E coverage.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  install/cache handling, or add a narrow browser coverage slice for
  multi-sheet XLSX selection.

## Progress Update 121 - Multi-Sheet XLSX Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover selecting a named sheet from a
  multi-sheet XLSX file in the browser.
- Added a synthetic workbook with `Summary` and `Measurements` sheets. The test
  uploads the file, fills `시트명` with `Measurements`, confirms parsing, and
  verifies that the preview comes from that selected sheet rather than the first
  sheet.
- Verified the resulting dataset version has `2행` / `2컬럼`, headers
  `Station` and `Reading`, and representative cells `S2` and `43`.
- Kept parser expansion, new statistical methods, fake results, and CI browser
  execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- Full Windows `scripts/check.ps1`: passed after multi-sheet XLSX browser
  coverage with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- Header-row, missing-token, delimiter editing, empty-file recovery, CSV upload,
  single-sheet XLSX upload, and named XLSX sheet selection are covered. Encoding
  changes and malformed-row recovery remain lower-level or future E2E coverage.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  install/cache handling, or add browser coverage for malformed-row and encoding
  option behavior.

## Progress Update 122 - Text Encoding Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover selecting a text encoding in
  the browser before parsing confirmation.
- Added a CP949-encoded CSV fixture with Korean headers and values. The test
  uploads the file, selects `cp949` from `인코딩`, confirms parsing, and verifies
  the decoded preview headers and representative Korean cells.
- Fixed strict Playwright selectors in this slice by checking Korean headers
  with exact matching and avoiding duplicate numeric cell text.
- Kept parser expansion, new statistical methods, fake results, and CI browser
  execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- First browser E2E attempt failed on a duplicate numeric cell selector. Second
  attempt failed on partial header matching. Both were test-selector issues, not
  backend parsing failures.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed after selector
  fixes.
- Full Windows `scripts/check.ps1`: passed after text encoding browser coverage
  with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- Header-row, missing-token, delimiter editing, text encoding selection,
  empty-file recovery, CSV upload, single-sheet XLSX upload, and named XLSX
  sheet selection are covered. Malformed-row recovery remains lower-level or
  future E2E coverage.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  install/cache handling, or add browser coverage for malformed-row behavior.

## Progress Update 123 - Parser Error-Recovery Browser E2E

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` to cover parser option error recovery
  without leaving the browser parsing screen.
- The multi-sheet XLSX test now first enters a missing sheet name, verifies the
  stable `xlsx_sheet_not_found` error, then changes `시트명` to `Measurements`
  and confirms successfully.
- The text encoding test now uses a CP949 fixture whose first 8192 bytes are
  ASCII so both `utf-8` and `cp949` appear as UI candidates. It first confirms
  with `utf-8`, verifies `text_decoding_failed`, then switches to `cp949`,
  confirms successfully, and verifies decoded Korean preview headers and cells.
- Kept parser semantics, new statistical methods, fake results, and CI browser
  execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- First attempt failed because the CP949 fixture started with Korean text, so
  `utf-8` was correctly absent from detected encoding candidates. The fixture
  was changed to use an ASCII sniffing prefix and CP949 data after that prefix.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- Full Windows `scripts/check.ps1`: passed after parser error-recovery browser
  coverage with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Remaining limitations:

- Browser E2E is still opt-in and not part of `scripts/check.ps1` or GitHub
  Actions.
- Error recovery is now covered for missing XLSX sheet names and text decoding
  failure. General malformed-row behavior remains lower-level/parser coverage
  because the canonical row reader intentionally pads short rows.

Next PR:

- Either wire the opt-in Playwright smoke into CI with explicit browser
  install/cache handling or add targeted browser coverage for another
  recoverable parser validation error.

## Progress Update 124 - Browser E2E GitHub Actions Job

Completed in current working tree:

- Added a separate `e2e` job to `.github/workflows/ci.yml`.
- The existing `windows` job remains the main ruff/format/mypy/pytest/frontend
  lint/typecheck/test/build gate.
- The new `e2e` job runs after `windows` succeeds, bootstraps the same Python
  3.10 and Node 22 environment, installs Playwright Chromium, and runs
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1`.
- Set `PLAYWRIGHT_BROWSERS_PATH` to `${{ runner.temp }}\ms-playwright` and added
  `actions/cache@v4` for that path so repeated Windows E2E runs can reuse the
  browser bundle when the Playwright dependency hash is unchanged.
- Kept local `scripts/check.ps1` browser-free so routine local checks do not
  require a browser install.

Validation:

- This change modifies only GitHub Actions workflow wiring and documentation.
  Remote Actions execution cannot be observed from this environment until the
  change is pushed or opened as a PR.
- `git diff --check`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`: passed.
- Full Windows `scripts/check.ps1`: passed after the GitHub Actions E2E job
  wiring with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Remaining limitations:

- The remote `e2e` job still needs to be verified in GitHub Actions after push.
- The E2E job installs Chromium explicitly in CI, so it is expected to add
  runtime compared with the `windows` check job.

Next PR:

- Push and verify the new `e2e` job in GitHub Actions, then decide whether to
  keep it required or leave it as an informational job while the browser smoke
  is still growing.

## Progress Update 125 - Browser E2E CI Diagnostics

Completed in current working tree:

- Added `workflow_dispatch` to `.github/workflows/ci.yml` so the Windows CI and
  browser E2E jobs can be triggered manually from GitHub Actions.
- Added timeouts to the `windows` and `e2e` jobs to prevent stuck hosted-runner
  sessions.
- Added `-WorkspaceRoot` support to `scripts/e2e.ps1` and
  `tests/e2e/critical_path.py`. The Python runner now creates a unique
  per-run directory under the supplied parent path.
- Updated the CI `e2e` job to run with a known `${{ runner.temp }}\datalab-e2e`
  parent and `-KeepWorkspace`, then upload only `logs\*.log` files as an
  `e2e-logs` artifact with `if: always()`.
- Kept local `scripts/check.ps1` browser-free and avoided uploading temporary
  workspace data or raw dataset artifacts.

Validation:

- `python3 -m py_compile tests/e2e/critical_path.py`: passed under WSL as a
  syntax check for the updated Python runner.
- `git diff --check`: passed.
- Native Windows `.venv\Scripts\python.exe`, `powershell.exe`, `cmd.exe`,
  `scripts\e2e.ps1`, and full `scripts\check.ps1` could not be rerun from this
  WSL session after the diagnostics update because WSL Windows interop failed
  before command execution with `UtilAcceptVsock: accept4 failed 110`.
- The last successful native Windows `scripts\e2e.ps1` and `scripts\check.ps1`
  runs were before this diagnostics wiring update, after the initial GitHub
  Actions E2E job wiring.

Remaining limitations:

- The remote artifact upload path still needs to be verified in GitHub Actions
  after push.
- Native Windows local rerun is still needed once the WSL/Windows interop issue
  clears.
- The uploaded artifact intentionally contains only backend/frontend server
  logs; screenshots and full temporary workspaces remain out of scope.

Next PR:

- Rerun native Windows `scripts\e2e.ps1` and `scripts\check.ps1`, then verify
  the remote `e2e-logs` artifact behavior on the first hosted Windows run and
  adjust retention/path handling if needed.

## Progress Update 127 - Workbench/Service Decomposition And Type Drift Guard

Completed in current working tree:

- Kept the already-split frontend Workbench component boundary in place:
  `StatisticalRoleGuide`, `MethodPurposeHelper`, `PreflightExplanationPanel`,
  `AnalysisHistoryPanel`, `AnalysisComparisonPanel`, and
  `AnalysisResultExportPanel` remain separate from `AnalysisWorkbench`.
- Split the large backend analysis-run service by responsibility:
  - `analysis_run_results.py`: stored result loading and SHA-256 validation.
  - `analysis_run_history.py`: status, list, pagination metadata, and cancel.
  - `analysis_run_exports.py`: JSON/CSV/HTML export creation, export listing,
    download validation, CSV formula sanitization, and static HTML rendering.
  - `analysis_run_comparisons.py`: stored-result comparison and method-specific
    comparison helpers.
- Reduced `analysis_runs.py` to the create/run dispatcher plus compatibility
  re-exports for existing callers and tests.
- Updated the API route module to import history/result/export/comparison
  behavior from the new service modules directly.
- Split frontend API types out of the large `api.ts` client into
  `frontend/src/api/types/common.ts`, `datasets.ts`, `analyses.ts`, `doe.ts`,
  `regression.ts`, and `index.ts`; `api.ts` remains the public typed client and
  re-exports those types so existing imports from `./api` keep working.
- Preserved beginner UX behavior from the previous slice: selected-method role
  emphasis still covers 2-sample t, paired t, capability, Gage R&R, and DOE
  factorial design; purpose-helper cards still show the question/easy
  explanation/Korean method name before the method ID and do not auto-run.
- Added a backend service-boundary test to guard that the public analysis-run
  facade still points at the split result/history/export/comparison modules.
- Added no statistical method, fake result, or mock chart.

Validation:

- `.venv/Scripts/python.exe -m py_compile backend/app/services/analysis_runs.py backend/app/services/analysis_run_results.py backend/app/services/analysis_run_history.py backend/app/services/analysis_run_exports.py backend/app/services/analysis_run_comparisons.py tests/e2e/critical_path.py`: passed.
- `git diff --check`: passed.
- Targeted backend ruff check for the split analysis-run modules, route, and
  API contract test: passed after formatting `analysis_run_history.py`.
- Targeted backend pytest for service boundary, handler registry, export,
  comparison, and export-list contracts: 5 passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 58 tests.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  388 tests, frontend lint, frontend typecheck, frontend Vitest with 58 tests,
  and frontend production build.

Remaining limitations:

- Frontend/backend API schema alignment is still manually maintained. The new
  `frontend/src/api/types/*` layout reduces the drift surface but does not yet
  generate types from OpenAPI.
- The remote GitHub Actions run/status still needs to be checked in GitHub UI
  or through authenticated `gh` after pushing.
- Vite production build reports the existing single-chunk size warning; no
  code-splitting change was made in this PR.

Next PR:

- Add an OpenAPI type-generation spike or schema drift check that compares the
  FastAPI schema to `frontend/src/api/types/*` without adding heavy runtime
  dependencies.
- Verify the latest remote `windows` and `e2e` GitHub Actions jobs after push.

## Progress Update 128 - Frontend API Client Facade Split

Completed in current working tree:

- Reduced `frontend/src/api.ts` to a public facade that re-exports client
  functions and API types.
- Split frontend API client implementation by backend domain:
  - `frontend/src/api/client.ts`: base URL, fetch wrapper, error-code parsing,
    content-disposition filename parsing, and browser download helper.
  - `frontend/src/api/health.ts`: health check response validation and fetch.
  - `frontend/src/api/datasets.ts`: upload, paste, parsing confirmation,
    schema update, rows preview, and profile fetch.
  - `frontend/src/api/analyses.ts`: method catalog, analysis history, restore,
    comparison, analysis run creation, export create/list/download.
  - `frontend/src/api/doe.ts`: factorial design and response entry client calls.
  - `frontend/src/api/regression.ts`: regression model prediction preflight and
    prediction calls.
  - `frontend/src/api/quality.ts`: Gage R&R preflight client call.
- Kept all existing component imports from `./api` working through the facade.
- Kept the previously split `frontend/src/api/types/*` as the manual schema
  boundary. No new dependency or OpenAPI generator was added.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 58 tests.
- `npm --prefix ./frontend run lint`: passed.
- Targeted backend ruff/mypy/pytest for the analysis-run service split remained
  green after the frontend client split:
  - ruff check: passed.
  - mypy over 6 backend source files: passed.
  - selected API contract pytest: 5 passed.

Remaining limitations:

- `frontend/src/api/types/*` is still manually maintained. The client split
  reduces file size and review conflicts, but does not yet prove schema parity
  against FastAPI OpenAPI.
- Components still intentionally import from `./api`; migrating component-level
  imports directly to domain clients is optional and not needed for behavior.

Next PR:

- Add a lightweight OpenAPI schema drift check or type-generation spike.
- Consider splitting method-specific result types within
  `frontend/src/api/types/analyses.ts` only if that file becomes a review
  bottleneck.

## Progress Update 129 - Frontend API Route Drift Guard

Completed in current working tree:

- Added `frontend/src/api/routes.ts` as the centralized route map for frontend
  API calls.
- Moved `/api/v1` endpoint construction, path-ID encoding, analysis-run create
  base path, and analysis history query-key ordering into the route map.
- Updated domain clients (`health`, `datasets`, `analyses`, `doe`,
  `regression`, and `quality`) to call `apiRoutes` instead of building endpoint
  strings inline.
- Removed a stray runtime `getApiBaseUrl` implementation from
  `frontend/src/api/types/analyses.ts` so type files stay type-only.
- Added a frontend test that verifies encoded path IDs and preserves the
  history query-string order expected by the existing API wrapper tests.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  388 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- Frontend request/response types are still manually maintained; this route map
  reduces endpoint drift but does not replace an OpenAPI schema drift check.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- In the next PR, add an OpenAPI schema drift check or type-generation spike
  without adding runtime dependencies.

## Progress Update 130 - OpenAPI Frontend Route Contract Guard

Completed in current working tree:

- Added `backend/tests/unit/test_openapi_frontend_contract.py`.
- The new test instantiates the FastAPI app, reads the generated OpenAPI schema,
  and verifies the route surface used by `frontend/src/api/routes.ts`.
- The checked contract covers frontend-used path, HTTP method, path/query
  parameters, request media types, success statuses, and response schema
  component refs.
- The check is included in normal backend pytest, so `scripts/check.ps1` runs it
  without a new script, dependency, or generator.
- No API behavior, statistical method, fake result, or frontend UI behavior was
  added.

Validation:

- `.venv/Scripts/python.exe -m ruff check backend/tests/unit/test_openapi_frontend_contract.py`:
  passed.
- `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_openapi_frontend_contract.py`:
  24 passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  412 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- This is a route/schema-component drift guard, not full TypeScript generation.
  It does not deeply compare every Pydantic field to every frontend TypeScript
  interface field.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Consider a deeper OpenAPI field-shape diff or generated frontend types in a
  later bounded PR.

## Progress Update 131 - OpenAPI Frontend Schema Field Guard

Completed in current working tree:

- Extended `backend/tests/unit/test_openapi_frontend_contract.py` with
  frontend schema component contracts.
- The test now guards high-value frontend-used schema fields in addition to
  route/method contracts.
- Covered schema surfaces include health, dataset upload/version/rows preview,
  dataset columns/artifacts, analysis method catalog, analysis history, stored
  result envelope, analysis provenance, warnings, and export list metadata.
- The guard verifies field presence, required field subsets, enum values,
  const values, direct schema refs, and array item refs.
- The check remains dependency-free and runs as part of backend pytest.
- No API behavior, frontend UI, statistical method, fake result, or generated
  type pipeline was added.

Validation:

- `.venv/Scripts/python.exe -m ruff check backend/tests/unit/test_openapi_frontend_contract.py`:
  passed.
- `.venv/Scripts/python.exe -m ruff format --check backend/tests/unit/test_openapi_frontend_contract.py`:
  passed.
- `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_openapi_frontend_contract.py`:
  41 passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- This is still a curated subset guard, not full Pydantic-to-TypeScript field
  parity. It intentionally allows additive backend schema fields.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Consider generated frontend types or a deeper OpenAPI field-shape diff in a
  later bounded PR.

## Progress Update 132 - Frontend Analysis API Type Split

Completed in current working tree:

- Split saved analysis history and comparison types out of
  `frontend/src/api/types/analyses.ts` into
  `frontend/src/api/types/analysisRuns.ts`.
- Split analysis result export response/list types into
  `frontend/src/api/types/analysisExports.ts`.
- Updated `frontend/src/api/types/index.ts` so the public `./api` type import
  surface remains unchanged for components and tests.
- Kept `AnalysisResultEnvelope` in `analyses.ts` because it depends on the
  large method-result union.
- Reduced `analyses.ts` from 2562 lines to 2227 lines without changing runtime
  API behavior, UI behavior, statistical methods, fake results, or generated
  type tooling.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- Method-specific result types still live in `analyses.ts`; splitting them by
  analysis family remains optional and should be done only if review bottlenecks
  continue.

Next:

- Consider a later generated type spike or family-level method-result type
  split.

## Progress Update 133 - Frontend Exploration Result Type Split

Completed in current working tree:

- Added `frontend/src/api/types/analysisResultsExploration.ts`.
- Moved exploratory analysis result types for `eda.descriptive`,
  `eda.graphical_summary`, `eda.normality`, and `eda.equal_variances` out of
  `frontend/src/api/types/analyses.ts`.
- Updated `AnalysisResultEnvelope` in `analyses.ts` to import those result
  types from the new exploration type module.
- Updated `frontend/src/api/types/index.ts` so the public `./api` type import
  surface remains unchanged.
- Reduced `analyses.ts` from 2227 lines to 2005 lines without changing runtime
  API behavior, UI behavior, statistical methods, fake results, or generated
  type tooling.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- Hypothesis, categorical, regression, and quality method-result types still
  live in `analyses.ts`.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Continue family-level result type splitting only if it keeps reducing review
  risk without obscuring the result envelope contract.

## Progress Update 134 - Frontend Categorical Result Type Split

Completed in current working tree:

- Added `frontend/src/api/types/analysisResultsCategorical.ts`.
- Moved categorical analysis result types for `categorical.one_proportion`,
  `categorical.two_proportion`, and `categorical.chi_square_association` out of
  `frontend/src/api/types/analyses.ts`.
- Updated `AnalysisResultEnvelope` in `analyses.ts` to import those result
  types from the new categorical type module.
- Updated `frontend/src/api/types/index.ts` so the public `./api` type import
  surface remains unchanged.
- Reduced `analyses.ts` from 2005 lines to 1738 lines without changing runtime
  API behavior, UI behavior, statistical methods, fake results, or generated
  type tooling.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- Hypothesis, regression, and quality method-result types still live in
  `analyses.ts`.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Continue family-level result type splitting in bounded slices only.

## Progress Update 135 - Frontend Regression Result Type Split

Completed in current working tree:

- Added `frontend/src/api/types/analysisResultsRegression.ts`.
- Moved correlation/regression result types for `regression.pearson`,
  `regression.xy_correlation`, and `regression.linear_model` out of
  `frontend/src/api/types/analyses.ts`.
- Updated `AnalysisResultEnvelope` in `analyses.ts` to import those result
  types from the new regression type module.
- Updated `frontend/src/api/types/index.ts` so the public `./api` type import
  surface remains unchanged.
- Reduced `analyses.ts` from 1738 lines to 1449 lines without changing runtime
  API behavior, UI behavior, statistical methods, fake results, or generated
  type tooling.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- Hypothesis and quality method-result types still live in `analyses.ts`.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Continue family-level result type splitting in bounded slices only.

## Progress Update 136 - Frontend Quality Result Type Split

Completed in current working tree:

- Added `frontend/src/api/types/analysisResultsQuality.ts`.
- Moved quality result and preflight types for `quality.individuals_chart`,
  `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`,
  `quality.gage_rr`, and `quality.gage_run_chart` out of
  `frontend/src/api/types/analyses.ts`.
- Updated `AnalysisResultEnvelope` in `analyses.ts` to import quality result
  types from the new quality type module.
- Updated `frontend/src/api/types/index.ts` so the public `./api` type import
  surface remains unchanged.
- Reduced `analyses.ts` from 1449 lines to 817 lines without changing runtime
  API behavior, UI behavior, statistical methods, fake results, or generated
  type tooling.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- Hypothesis method-result types still live in `analyses.ts`.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Split hypothesis result types only if the next bounded slice keeps the result
  envelope easier to review.

## Progress Update 137 - Frontend Hypothesis Result Type Split

Completed in current working tree:

- Added `frontend/src/api/types/analysisResultsHypothesis.ts`.
- Moved hypothesis-test result types for `hypothesis.one_sample_t`,
  `hypothesis.paired_t`, `hypothesis.two_sample_t`,
  `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`,
  `hypothesis.one_sample_wilcoxon`, `hypothesis.mann_whitney`, and
  `hypothesis.kruskal_wallis` out of `frontend/src/api/types/analyses.ts`.
- Updated `AnalysisResultEnvelope` in `analyses.ts` to import hypothesis
  result types from the new hypothesis type module.
- Updated `frontend/src/api/types/index.ts` so the public `./api` type import
  surface remains unchanged.
- Reduced `analyses.ts` from 817 lines to 160 lines without changing runtime
  API behavior, UI behavior, statistical methods, fake results, or generated
  type tooling.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining limitations:

- API types are still manually maintained; OpenAPI type generation remains a
  later hardening task.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this maintenance step.

Next:

- Continue with schema drift hardening or OpenAPI type-generation planning
  rather than further result-type splitting.

## Progress Update 138 - Frontend Result Summary-Type Drift Guard

Completed in current working tree:

- Corrected `MethodExecutionHandlerSpec.result_summary_type` for
  `eda.normality` from `normality` to `normality_test`.
- Corrected `MethodExecutionHandlerSpec.result_summary_type` for
  `eda.equal_variances` from `equal_variances` to `equal_variances_test`.
- Added frontend result type file ownership checks to
  `backend/tests/unit/test_openapi_frontend_contract.py`.
- Added a backend/frontend summary-type drift guard that compares every
  frontend `analysisResults*.ts` `summary_type` literal with backend generic
  analysis-run handler specs, plus the non-analysis-run Gage R&R preflight
  summary type.
- Updated method versioning documentation to explain the summary-type guard and
  the current non-analysis-run exception.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 47 tests.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py::test_analysis_execution_handler_registry_covers_core_methods`:
  passed.
- Full Windows `scripts/check.ps1`: passed on 2026-07-09 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 435 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- The guard checks summary-type literal alignment and file ownership, not full
  field-level TypeScript/Pydantic parity.
- Full OpenAPI type generation remains a later task.

Next:

- Consider a deeper schema diff or generated type spike once this manual guard
  proves stable.

## Progress Update 139 - E2E, CI, Workbench Ownership Stabilization

Completed in current working tree:

- Added failure diagnostics to `tests/e2e/critical_path.py`: step markers,
  current URL and page title reporting, failure screenshots, and failure HTML
  snapshots.
- Added `-DiagnosticsRoot` to `scripts/e2e.ps1` so local and CI runs can keep
  diagnostic logs/screenshots/html separate from the temporary workspace.
- Limited the GitHub Actions `e2e-logs` artifact to E2E logs, screenshots, and
  HTML snapshots.
- Split Workbench history, export, comparison, and restored-result state into
  dedicated frontend hooks while preserving existing UI behavior and prop names
  consumed by the Workbench shell.
- Added `docs/e2e_coverage.md` to describe the current browser smoke coverage,
  non-covered flows, known flake risks, local execution, browser install,
  diagnostics inspection, and workspace retention.
- Added `docs/beginner_usability_walkthrough.md` as a UX QA checklist for
  beginner-facing role guide, purpose helper, preflight, and result-reading
  flows.
- Clarified OpenAPI/frontend contract guard scope: this is a high-value route
  and field guard, not full TypeScript generation.
- Documented the intended `analysis_runs.py` facade boundary so stored result,
  history, export, and comparison behavior remain owned by sibling service
  modules.

Validation:

- `npm --prefix .\frontend run lint`: passed.
- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py .\backend\tests\unit\test_api_contracts.py::test_analysis_run_service_boundaries_are_split_without_api_drift`:
  passed with 48 tests.
- `npm --prefix .\frontend run typecheck`: passed.
- `npm --prefix .\frontend run test -- --run`: passed with 59 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-09 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 435 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed.

Remaining limitations:

- Remote GitHub Actions status for this working-tree change was not observed in
  this environment.
- OpenAPI/frontend parity is still guarded manually for high-value routes and
  fields only; generated TypeScript clients remain a later task.
- The existing Vite production chunk-size warning remains; no code-splitting
  change was made in this stabilization step.

Next:

- After the change is pushed, verify the `windows` and `e2e` jobs, dependency
  order, `e2e-logs` artifact, and `workflow_dispatch` button in GitHub UI.
- Consider generated OpenAPI TypeScript types or a broader schema-diff guard in
  a separate hardening PR.

## Progress Update 140 - Frontend Route Contract Coverage Guard

Completed in current working tree:

- Extended `OperationContract` in
  `backend/tests/unit/test_openapi_frontend_contract.py` with the owning
  `frontend/src/api/routes.ts` route helper name.
- Added a contract test that extracts the frontend `apiRoutes` helper names and
  requires an exact match with `FRONTEND_ROUTE_CONTRACTS`, so adding a frontend
  API route now requires adding the matching backend OpenAPI contract entry.
- Added a boundary guard that fails if frontend API domain modules embed direct
  `/api/v1` endpoint literals outside the centralized route map.
- Updated `docs/method_versioning.md` to describe the route-name coverage guard
  and route-map bypass guard.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 49 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 437 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.
- Browser E2E smoke
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed on 2026-07-10.

Remaining limitations:

- This still is not full OpenAPI TypeScript generation and does not prove every
  nested TypeScript field exactly matches Pydantic.
- The guard is route-map and high-value schema focused; broader request/response
  shape diffing remains a later hardening task.

Next:

- Consider full OpenAPI TypeScript generation or a deeper request/response
  field-shape diff in a separate hardening PR.

## Progress Update 141 - Remote CI Verification And Reference QA Planning

Completed in current working tree:

- Rechecked remote CI visibility for pushed `main` commit
  `49266a365bbfffcecdf32a008bdb4c02739f2742` using the available GitHub app
  checks and unauthenticated GitHub REST.
- Updated `.github/workflows/ci.yml` so the browser E2E job uses a separate
  diagnostics root and uploads only diagnostics-root logs, screenshots, and HTML
  snapshots as `e2e-logs`.
- Added `logs/e2e-diagnostics.log` output to `tests/e2e/critical_path.py` so CI
  artifacts include timestamped step markers, step-slugged failure screenshot
  and HTML names, URL/title on Playwright timeouts, and recent backend/frontend
  log tails when a readiness dependency exits early.
- Added a Workbench state ownership guard to
  `backend/tests/unit/test_openapi_frontend_contract.py` so saved history,
  export, comparison, and restored-result API ownership stays in dedicated
  frontend hooks rather than drifting back into `App.tsx`.
- Grouped the Workbench saved-history, export, comparison, and restored-result
  state/handler props through `AnalysisShell`/`AnalysisWorkbench` so the actual
  app path passes four state ownership objects instead of broad hook spreads.
- Expanded `docs/statistical_method_audit_matrix.md` with first fixture file
  names, expected output sources, tolerances, fields to verify, and
  license/source checks for independent reference QA planning.
- Expanded `docs/beginner_usability_walkthrough.md` into a QA checklist with
  pass criteria, fail examples, copy visibility checks, UI element checks, and
  recovery paths for wrong roles.
- Added an OpenAPI TypeScript generation review plan to `to_do_list.md` without
  adding a generator dependency.
- Updated CI/E2E operations docs.

Validation so far:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 50 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 438 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.
- Browser E2E smoke
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed on 2026-07-10 and produced `logs/e2e-diagnostics.log`.

Remote CI status:

- GitHub app checks against the pushed commit returned no PR-filtered workflow
  runs and no legacy commit statuses.
- Unauthenticated GitHub REST Actions run listing returned `404 Not Found`.
- `gh` is not installed in this environment and no `GH*` or `GITHUB*` token
  environment variable is present, so authenticated Actions run listing is still
  unavailable here.

Remaining limitations:

- The remote `windows` and `e2e` jobs, dependency order, and `e2e-logs` artifact
  still need confirmation in the GitHub UI or with an authenticated `gh` setup.
- Reference QA planning is documentation only; no new independent fixtures were
  added in this slice.
- The GitHub UI `workflow_dispatch` control has not been observed here even
  though the workflow file contains the trigger.

## Progress Update 142 - CI/E2E Diagnostics Contract Guard

Completed in current working tree:

- Added a regression guard in
  `backend/tests/unit/test_openapi_frontend_contract.py` for the CI/E2E
  diagnostics contract. The guard checks that the workflow keeps
  `workflow_dispatch`, runs `e2e` after `windows`, passes separate workspace and
  diagnostics roots to `scripts/e2e.ps1`, uploads only diagnostics-root
  `logs`, `screenshots`, and `html` paths as `e2e-logs`, and preserves the E2E
  runner's step-slugged failure artifacts, URL/title timeout context, and
  backend/frontend readiness log tails.
- Added an E2E maintenance checklist to `docs/e2e_coverage.md` for future smoke
  extensions, including required `diagnostics.step(...)` markers, synthetic
  data, diagnostics-only CI artifacts, and timeout/log-tail diagnostics.
- Updated `docs/ci_status.md` so the latest local validation counts match the
  current tree.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 51 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 439 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- The remote `windows` and `e2e` jobs, dependency order, `e2e-logs` artifact,
  and GitHub UI `workflow_dispatch` control still need authenticated GitHub UI
  or `gh` confirmation after push.
- This guard verifies workflow/script wiring and diagnostic artifact scope. It
  is not a substitute for observing a real remote Actions run.
- The latest guard-only slice did not rerun browser E2E because no E2E runtime
  code changed after the previous passing run.

## Progress Update 143 - E2E Step Marker Documentation Guard

Completed in current working tree:

- Reran the browser E2E smoke after the CI/E2E diagnostics guard changes. The
  run passed and produced only diagnostics logs, with no failure screenshots or
  HTML snapshots.
- Added a `Current Step Markers` section to `docs/e2e_coverage.md` listing the
  exact `diagnostics.step(...)` markers from `tests/e2e/critical_path.py`.
- Added a regression guard in
  `backend/tests/unit/test_openapi_frontend_contract.py` that parses
  `tests/e2e/critical_path.py` and `docs/e2e_coverage.md` so the documented E2E
  step marker list must stay in the same order as the smoke runner.
- Updated `docs/ci_status.md` so the latest local validation counts match the
  current tree.

Validation:

- Browser E2E smoke
  `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed on 2026-07-10.
- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 52 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 440 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- The remote `windows` and `e2e` jobs, dependency order, `e2e-logs` artifact,
  and GitHub UI `workflow_dispatch` control still need authenticated GitHub UI
  or `gh` confirmation after push.
- No new statistical method, reference fixture, method version bump, or fake
  result was added in this stabilization slice.

## Progress Update 144 - UX And Reference QA Documentation Guards

Completed in current working tree:

- Added a beginner usability walkthrough guard in
  `backend/tests/unit/test_openapi_frontend_contract.py`. It verifies that
  `docs/beginner_usability_walkthrough.md` keeps the five required beginner QA
  scenarios and that each scenario includes the required question, purpose
  helper card, role guidance, easy wrong roles, preflight checks, result-reading
  guidance, non-claims, pass criteria, fail examples, visible UX copy, UI
  inspection target, and wrong-role recovery notes.
- Added an independent reference backlog guard in
  `backend/tests/unit/test_openapi_frontend_contract.py`. It verifies that
  `docs/statistical_method_audit_matrix.md` keeps actionable fixture plans for
  `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`,
  `doe.factorial_design`, and `regression.linear_model`, including fixture file
  names, expected output source, tolerances, fields to verify, and license/source
  checks.
- Updated `docs/ci_status.md` so the latest local validation counts match the
  current tree.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 54 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 442 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- The remote `windows` and `e2e` jobs, dependency order, `e2e-logs` artifact,
  and GitHub UI `workflow_dispatch` control still need authenticated GitHub UI
  or `gh` confirmation after push.
- These guards keep QA plans actionable but do not add the independent reference
  fixtures themselves.

## Progress Update 145 - Analysis Run Facade Boundary Guard

Completed in current working tree:

- Strengthened `backend/tests/unit/test_api_contracts.py` with an AST-based
  guard for `backend/app/services/analysis_runs.py`. The guard does not enforce
  a line count; it asserts that the facade has only `create_analysis_run` as a
  top-level function, defines no classes, imports the split
  result/history/export/comparison service modules, and does not regain direct
  storage metadata or result-execution persistence imports.
- Updated `docs/storage.md` to state that `analysis_runs.py` is the create/run
  dispatcher plus compatibility facade, while stored-result loading, history,
  exports, and comparison ownership stay in sibling modules.
- Updated `docs/ci_status.md` so the latest local validation counts match the
  current tree.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py -k "analysis_run_service_boundaries or analysis_runs_facade_keeps_create_dispatch_only"`:
  passed with 2 selected tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 443 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- This is a boundary ownership guard, not a functional expansion. No analysis
  result schema, method version, statistical formula, or export format changed.
- The remote `windows` and `e2e` jobs, dependency order, `e2e-logs` artifact,
  and GitHub UI `workflow_dispatch` control still need authenticated GitHub UI
  or `gh` confirmation after push.

## Progress Update 146 - Remote CI Verification Checklist Guard

Completed in current working tree:

- Expanded `docs/ci_status.md` with authenticated GitHub CLI verification
  commands for remote Actions inspection:
  `gh auth status`, `gh run list`, `gh run view`, `gh run download`, and
  optional `gh workflow run` for manual dispatch testing.
- Kept the remote CI state honest: the `windows` job, `e2e` job, dependency
  order, `e2e-logs` artifact, and GitHub UI `workflow_dispatch` control are
  still not observed from this environment.
- Added a documentation consistency guard in
  `backend/tests/unit/test_openapi_frontend_contract.py` so
  `docs/ci_status.md` must continue to document the workflow triggers, Windows
  runner, Python/Node versions, local check command, browser E2E command,
  `e2e-logs` artifact, authenticated `gh` verification commands, manual dispatch
  check, and repository-settings non-change rule.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 55 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 444 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- Remote GitHub Actions status is still unverified here because authenticated
  GitHub UI or `gh` access is required after push.

- No repository settings, branch protection, workflow requirements, statistical
  methods, method versions, or generated types changed in this slice.

## Progress Update 147 - CI Status Wording And Datetime-Order Test Stabilization

Completed in current working tree:

- Clarified `docs/ci_status.md` so older 2026-07-07 and 2026-07-09 validation
  rows no longer describe themselves as "latest" runs. The current latest local
  validation remains the 2026-07-10 record with backend pytest 444 tests and
  frontend Vitest 59 tests.
- Strengthened the CI status documentation guard in
  `backend/tests/unit/test_openapi_frontend_contract.py` so stale "latest run"
  wording does not return to the Local Validation section.
- Stabilized
  `test_analysis_run_executes_run_chart_with_datetime_order_column` so it checks
  that raw input datetime strings are not exposed instead of rejecting every
  occurrence of `2024` in the full result JSON, which can appear by chance in a
  generated UUID.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py::test_analysis_run_executes_run_chart_with_datetime_order_column .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 56 tests.
- Full Windows `scripts/check.ps1`: first exposed the UUID-sensitive assertion,
  then passed after the stabilization fix with backend pytest 444 tests,
  frontend lint, frontend typecheck, frontend Vitest with 59 tests, and frontend
  production build.

Remaining limitations:

- Remote GitHub Actions status is still unverified here because authenticated
  GitHub UI or `gh` access is required after push.
- The Vite production build still reports the existing large-chunk warning.

## Progress Update 148 - OpenAPI TypeScript Generation Planning Guard

Completed in current working tree:

- Added a planning-scope guard in
  `backend/tests/unit/test_openapi_frontend_contract.py` for the OpenAPI
  TypeScript generation review note in `to_do_list.md`.
- The guard verifies that the review remains explicit about current high-value
  route/field guard coverage, non-coverage, candidate tools, Windows/Node
  compatibility, lockfile and CI-time impact, generated-file commit policy,
  schema naming stability, curated domain type migration, and the fact that no
  generator dependency is added in this PR.
- The same guard checks `frontend/package.json` and `frontend/package-lock.json`
  to make sure candidate generator packages such as `openapi-typescript`,
  `openapi-fetch`, `orval`, and `@openapitools/openapi-generator-cli` were not
  introduced.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 56 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-10 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 445 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- OpenAPI TypeScript generation remains a later spike; no generator dependency,
  generated client, generated types, or package lockfile change was added.
- Remote GitHub Actions status is still unverified here because authenticated
  GitHub UI or `gh` access is required after push.

## Progress Update 149 - Workbench Hook Ownership Guard Expansion

Completed in current working tree:

- Expanded the Workbench saved-result state ownership guard in
  `backend/tests/unit/test_openapi_frontend_contract.py`.
- The guard now verifies that each dedicated hook keeps its own saved-result API
  ownership and does not import sibling saved-result API calls:
  `useAnalysisHistoryState` owns history fetch, `useAnalysisExportState` owns
  export creation/list/download, `useAnalysisComparisonState` owns comparison,
  and `useRestoredAnalysisResultState` owns stored-result restore.
- The guard also checks hook-level reset/effect markers such as `resetKey`,
  reset functions, refresh handlers, comparison validation, export-error
  clearing, method selection during restore, and export-list refresh after
  restore.
- No frontend UI behavior, route, result schema, statistical method, or API
  payload changed.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 56 tests.
- Full Windows `scripts/check.ps1`: passed on 2026-07-11 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 445 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining limitations:

- This is still a guard for grouped hook ownership, not a broader Workbench
  redesign.
- Remote GitHub Actions status is still unverified here because authenticated
  GitHub UI or `gh` access is required after push.

## Progress Update 150 - Post-Reboot Workbench Async Stabilization

Completed in current working tree:

- Revalidated the clean repository at
  `02d5d4e4fb2e1d8a0ec802177e2ecdf62116a3fa` after the reboot before
  changing code.
- Added a shared latest-request guard for Workbench saved-result history,
  export list/create/download, comparison, and restore flows.
- Reset, selection, and component unmount paths now invalidate in-flight
  requests. Reset paths clear their loading states, and only the latest request
  may write response/error state or clear its loading flag.
- Removed the duplicate field-by-field saved-result prop fallback from
  `AnalysisShell` and `AnalysisWorkbench`. The four grouped history, export,
  comparison, and restored-result state props are now the only contract.
- Confirmed the registry boundary against code: 29 stable catalog IDs, 25
  available IDs, 24 generic `MethodExecutionHandler` entries, dedicated
  `doe.factorial_design` routes, and a dedicated stored-model prediction path
  while `regression.predict` remains disabled in the generic catalog path.
- Updated setup guidance to use a separate E2E diagnostics root and to describe
  the actual CI `e2e-logs` scope: logs, failure screenshots, and failure HTML,
  never the temporary data workspace.
- No statistical calculation, request/result schema, method version,
  dependency, migration, or availability changed.

Targeted validation:

- `npm --prefix .\frontend run typecheck`: passed.
- `npm --prefix .\frontend run lint`: passed with no warnings.
- `npm --prefix .\frontend run test -- --run`: passed with 63 tests.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py -q`:
  passed with 57 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 446 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed after the Workbench prop and async-state changes.

Remaining limitations:

- The browser E2E smoke covers saved-result restore/comparison and export flows,
  but does not deliberately delay two HTTP responses to exercise a race in a
  real browser. The latest-request token behavior is covered by focused
  frontend tests and the hook integration is protected by the ownership guard.
- Remote GitHub Actions status still requires authenticated verification after
  push.

## Progress Update 151 - Capability Independent NIST Reference Slice

Completed in current working tree:

- Added
  `backend/tests/reference/fixtures/quality_capability_normal_reference.json`
  with source URL, access date, license/source review, estimator mapping,
  tolerances, synthetic summary-matching rows, expected metadata, and explicit
  interpretation limits.
- Cross-checked the application's overall sample-SD capability indices against
  the official NIST/SEMATECH section 6.1.6 example: LSL 8, USL 20, mean 16,
  sample SD 2, Cp 1.0, Cpk/Cpu 0.6667, and Cpl 1.3333.
- Kept the application-specific adjacent-moving-range `MRbar/d2` within sigma
  as a separate hand-check instead of attributing it to the NIST example.
- Added assertions for source metadata, convention disclosure, tolerances,
  N/exclusions, sample sigma, overall and within indices, and persistent warning
  codes.
- Updated the capability method contract and statistical audit matrix. No
  runtime formula, result schema, method version, API, dependency, migration,
  or frontend behavior changed.

Targeted validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_capability.py -q`:
  passed with 5 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 447 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed after the reference-only changes.

Remaining limitations:

- NIST publishes summary statistics rather than raw rows for this example. The
  fixture's `[14, 16, 18]` rows are synthetic and only reproduce mean 16 and
  sample SD 2 for formula verification.
- Independent raw-data coverage for expected nonconformance/ppm and an
  industrial-software within-sigma convention remains backlog.
- NIST notes that capability estimates require substantially larger samples;
  this three-row formula fixture cannot support a process capability decision.

## Progress Update 152 - Gage R&R Independent Minitab Summary Slice

Completed in current working tree:

- Added
  `backend/tests/reference/fixtures/quality_gage_rr_crossed_reference.json`
  with official Minitab example/formula URLs, access date, license review,
  balanced design counts, published full-model ANOVA summary, published
  reduced-model results, tolerances, and explicit policy mapping.
- Cross-checked the published 10-part, 3-operator, 3-replicate interaction ANOVA
  summary. The interaction row calculated from published rounded mean squares
  matches Minitab's rounded `F=0.434` and `p=0.974`.
- Derived repeatability, operator, part-operator, reproducibility, total Gage
  R&R, part-to-part, total variation, contribution, study variation, and ndc
  under the application's explicit no-pooling policy.
- Preserved the negative raw interaction component and verified its visible
  clamp-to-zero warning policy.
- Documented that Minitab removes the nonsignificant interaction and therefore
  its reduced-model final variance table is not a direct parity target for this
  application.
- Updated the Gage R&R method contract and statistical audit matrix. No runtime
  formula, result schema, method version, API, dependency, migration, or
  frontend behavior changed.

Targeted validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_gage_rr.py -q`:
  passed with 5 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 448 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed after the reference-only changes.

Remaining limitations:

- A redistributable raw-row crossed study with the same no-pooling interaction
  policy remains needed for end-to-end independent ANOVA parity.
- Minitab's worksheet, screenshots, and raw measurements are not copied into
  the repository; the fixture records only the small published summary needed
  for convention-aware validation.

## Progress Update 153 - Gage Run Chart Ordering Reference Slice

Completed in current working tree:

- Added
  `backend/tests/reference/fixtures/quality_gage_run_chart_ordering_reference.json`
  as a fully synthetic, internally hand-reviewed diagnostic fixture with source
  classification, license review, conventions, tolerances, and interpretation
  limits.
- Fixed numeric order-column sorting, canonical row position as the stable tie
  breaker, and every displayed point's value and redacted
  part/operator/replicate index.
- Verified that the inline five-point cap does not change the eight-observation
  design, sample, or measurement summaries.
- Added exact missing measurement, nonnumeric measurement, missing identifier,
  missing order, and invalid order exclusion counts and warning assertions.
- Checked every synthetic raw label against the complete serialized result and
  added a duplicate-replicate failure case that returns no fake chart payload.
- Updated the Gage Run Chart method contract and statistical audit matrix. No
  runtime calculation, result schema, method version, API, dependency,
  migration, or frontend behavior changed.

Targeted validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_gage_run_chart.py -q`:
  passed with 6 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 450 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed after the reference-only changes.

Remaining limitations:

- The fixture validates deterministic chart payload construction, not browser
  chart rendering or an exported chart artifact.
- It does not calculate variance components or establish measurement-system
  acceptability; `quality.gage_rr` remains the relevant inferential workflow.

## Progress Update 154 - DOE Factorial NIST Standard-Order Reference Slice

Completed in current working tree:

- Added
  `backend/tests/reference/fixtures/doe_factorial_design_reference.json` with
  official NIST/SEMATECH source URLs, access date, license review, convention
  boundaries, tolerances, and design-asset interpretation limits.
- Cross-checked the published three-factor `2^3` Yates coded order and the
  actual Speed/Feed/Depth low/high settings for all eight combinations.
- Verified the published two-replicate sequence as 16 immutable runs with the
  same eight standard-order combinations per replicate.
- Recorded the application-derived canonical design SHA-256 while explicitly
  noting that NIST does not publish that checksum or the application's seeded
  shuffle/block conventions.
- Added an invalid low/high range failure case with no fallback design.
- Updated the DOE method contract and statistical audit matrix. No runtime
  generator, API schema, storage migration, method version, dependency, or
  frontend behavior changed.

Targeted validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_factorial_design.py -q`:
  passed with 6 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 452 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed after the reference-only changes.

Remaining limitations:

- The fixture validates the current immutable design-asset slice only; it has
  no response measurements or downstream DOE statistics.
- Effects, OLS/ANOVA, alias analysis, diagnostics, response surfaces, and
  optimization remain unimplemented rather than represented by placeholders.

## Progress Update 155 - Linear Model Independent Statsmodels Reference Slice

Completed in current working tree:

- Added a compact synthetic
  `regression_linear_model_reference.csv` with a recorded SHA-256 and
  `regression_linear_model_reference.json` with statsmodels 0.14.6 source,
  generator versions/options, license review, tolerances, and interpretation
  limits.
- Generated the independent reference in a temporary Python 3.10 environment
  outside the repository; statsmodels and its dependencies were not added to
  the product or test environment.
- Cross-checked treatment coding with reference level `A`, mapped term names,
  coefficients, SE/t/p/CI, residual sigma, R-squared/adjusted R-squared, model
  F test, VIF, condition number, and persistent warning codes.
- Cross-checked three predicted means, mean-response confidence intervals, and
  individual prediction intervals against statsmodels `get_prediction` output.
- Added a single-level categorical failure case without fallback statistics.
- Kept manifest SHA-256 validation in existing API tests because generated IDs
  and provenance make a fixed fixture hash inappropriate; metadata equality,
  retrieval, tamper recovery, and row-snapshot provenance remain covered.
- Updated linear-model/prediction contracts and the statistical audit matrix.
  No runtime calculation, API/schema, manifest version, dependency, migration,
  or frontend behavior changed.

Targeted validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_linear_model.py -q`:
  passed with 8 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 454 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build after the temporary reference environment was removed.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed after the reference-only changes.

Remaining limitations:

- The reference validates standard OLS arithmetic and treatment coding only;
  robust covariance, categorical interactions, and arbitrary formulas remain
  unsupported.
- Interactive browser E2E does not yet cover the complete upload-fit-preflight-
  predict workflow, and prediction results remain inline-capped.

## Progress Update 156 - Linear Model Browser Fit And Prediction Slice

Completed in current working tree:

- Extended `tests/e2e/critical_path.py` with a second fully synthetic 12-row
  `y`/`x`/`group` TSV workflow after the saved-result stale checks and before
  the existing upload/parser matrix.
- Verified dataset creation and the `12행`/`3컬럼` active-version context, then
  navigated through the regression module/method grid to
  `regression.linear_model`.
- Explicitly selected response `y` and predictors `x` plus categorical `group`
  before executing a real treatment-coded OLS fit and checking Model ID and
  manifest presence.
- Executed same-version prediction preflight and verified all 12 rows were
  usable, the schema hash matched, and prediction was ready.
- Executed real backend prediction and verified the 12-row result summary,
  Prediction ID, mean-CI/prediction-interval table, a reference predicted value,
  and all 12 SVG interval-line elements.
- Added a static contract guard for the critical selectors/assertions and
  synchronized E2E and regression method/prediction documentation.
- Kept runtime calculations, APIs, schemas, method/manifest versions,
  dependencies, migrations, and production frontend behavior unchanged.

Targeted validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed with the new `verify linear model fit and prediction` step.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 455 tests, frontend Vitest 63 tests, lint, typecheck, and the
  production build.
- The browser E2E passed again after the full check and documentation/guard
  synchronization.

Remaining limitations:

- Prediction output is still inline-capped and has no paged retrieval endpoint.
- The browser smoke uses the active training dataset for prediction; selecting
  a different target dataset version remains outside the current UI.

## Progress Update 158 - Cross-Dataset Regression Prediction Target Selection

Completed in current working tree:

- Added paged confirmed dataset-version catalog retrieval without raw rows,
  storage paths, or hashes.
- Added a typed target catalog client and dedicated target-selection state hook.
- Added explicit Linear Model target selection with active-version default and
  stale preflight/prediction/page invalidation on target changes.
- Verified a real 12-row OLS fit predicting a separately registered four-row
  target dataset in backend contracts and browser E2E.
- Preserved the `regression.predict` calculation/method version, existing
  preflight gate, local-only behavior, and raw-value-free result contract.

Validation:

- OpenAPI/frontend contract tests passed with 60 tests.
- Full `scripts\check.ps1` passed with backend pytest 460 tests and frontend
  Vitest 63 tests.
- Browser E2E passed with explicit cross-dataset target selection.

Remaining limitations:

- Manual single-row prediction input and stored prediction export remain out of
  scope.
- The production build retains the existing Vite main-chunk size warning.

## Progress Update 159 - Full Regression Prediction CSV Export

Completed in current working tree:

- Added checksum/schema/count-verified streaming of every stored prediction row
  into a dedicated wide CSV export artifact.
- Preserved full prediction/model/source-target/interval provenance without raw
  predictor columns or target cell values.
- Added grouped frontend creation/download state with stale-response guards and
  browser coverage for cross-dataset prediction CSV download.
- Kept generic analysis CSV semantics, prediction calculations, method version,
  dependencies, and migrations unchanged.

Validation:

- Targeted backend/OpenAPI tests passed with 62 tests.
- Full `scripts\check.ps1` passed with backend pytest 461 tests and frontend
  Vitest 63 tests.
- Browser E2E passed through prediction CSV generation and `.csv` download.

Remaining limitations:

- Manual single-row prediction input remains out of scope.
- The production build retains the existing Vite main-chunk size warning.

## Progress Update 160 - Regression Prediction Dependency Stabilization

Completed in current working tree:

- Added source analysis freshness, method-version, fit/current schema, canonical
  artifact, model metadata, and manifest checksum gates to prediction preflight
  and execution. Stale source models require an explicit refit.
- Added complete source/target/model dependency provenance using the shared
  runtime/build helper, without raw paths, filenames, or predictor values.
- Bumped `regression.predict` to `0.2.0` from the registry-only version source;
  result/config/rows schemas are 2/3/2 and CSV schema remains 1.
- Added a shared cross-artifact consistency validator used by restore, paging,
  full CSV, export listing, and download, with tamper coverage for config,
  result, rows, model, IDs, versions, hashes, and counts.
- Extracted preflight/prediction and prediction-page state into guarded hooks
  and added nine actual hook-level delayed-response/reset race tests across the
  Workbench and regression prediction flows.
- Reconciled registry/guidance/UI text with the implemented dedicated Linear
  Model prediction path while keeping generic `regression.predict` unavailable.
- Measured full-verification page/CSV performance at 1,000, 10,000, and 100,000
  rows. The 100,000-row page baseline is about 7.9 seconds at every page
  position; verification remains enabled and cache/index work remains backlog.

Validation:

- Backend pytest passed with 475 tests.
- Frontend Vitest passed with 72 tests, including nine hook race tests.
- OpenAPI/frontend contract pytest passed with 62 tests.
- Full `scripts\check.ps1` passed with backend Ruff/format/mypy, backend pytest
  475, frontend lint/typecheck, frontend Vitest 72, and production build. The
  existing Vite main-chunk warning remains at 550.39 kB.
- Browser E2E passed after anchoring the regression method locator to avoid the
  new disabled Predict guidance text; the complete cross-dataset prediction
  and full CSV flow passed.

Next allowed PR:

- `quality.attribute_control_chart`: define the common method contract, then
  implement P/NP/C/U formulas, denominator/opportunity validation, independent
  fixtures, frontend chart/result UI, warnings, provenance, and export.

## Progress Update 161 - Attribute Control Chart P/NP/C/U Slice

Completed in the current working tree:

- Made `quality.attribute_control_chart` available at method version `0.1.0`
  with result schema `1`. The registry now contains 29 stable catalog IDs, 26
  available IDs, and 25 generic `MethodExecutionHandler` entries.
- Added explicit P/NP defective-unit and C/U defect-count contracts. P/NP
  require positive integer sample size, NP rejects varying sample size, C
  requires recorded equal-opportunity confirmation, and U accepts positive
  finite opportunity/area/exposure.
- Added Phase I weighted centers, point-specific P/U limits, fixed NP/C limits,
  natural-bound truncation metadata, strict one-point 3-sigma signals, Pearson
  dispersion diagnostics, and approximation/baseline warnings without silent
  chart switching or limit correction.
- Added stable invalid-count/denominator/definition/zero-variance errors and
  raw-value/path-free API responses. Common analysis provenance, row snapshot,
  stored-result restore, JSON/CSV/HTML export, and stale behavior are reused.
- Added a NIST reference fixture covering the published C and P examples,
  fixed-n NP parity, and independently evaluated U formulas, plus hand and
  failure tests.
- Added P/NP/C/U segmented UI, conditional count/denominator roles, explicit C
  confirmation, varying-limit SVG, result table, persistent warnings, and two
  frontend rendering tests.
- Added `docs/attribute_control_chart_method_contract.md` and synchronized the
  implementation guide, versioning policy, audit matrix, CI/progress, and
  to-do source-of-truth documents.

Validation in progress for this update:

- Attribute-control-chart statistics tests passed with 15 tests.
- Attribute chart unit/reference tests passed with 17 tests; targeted
  API/registry/handler coverage passed with 12 selected tests.
- OpenAPI/frontend contract tests passed with 62 tests.
- Full `scripts\check.ps1` passed: Ruff and format checks, mypy over 81 source
  files, backend pytest 500, frontend lint/typecheck, frontend Vitest 82, and
  the production build. The existing Vite chunk warning remains at 563.92 kB.
- Browser E2E passed through the existing regression fit/cross-dataset
  prediction/full CSV flow and the new 30-row P-chart execution, accessible
  SVG, two strict 3-sigma signals, and first-25-point table assertions.

Next allowed PR after this slice:

- DOE factorial analysis: factor coding, effects, hierarchy, OLS/ANOVA,
  main/interaction plots, residual diagnostics, pure error/lack-of-fit, and
  report integration.

## Progress Update - DOE Factorial Analysis

Implemented in the current working tree:

- `doe.factorial_design` v0.2.0 with config/result schema 1 and SQLite schema v9
  analysis records tied to immutable design version and response SHA-256.
- Enforced-hierarchy -1/+1 main/interaction effects, OLS inference, center
  curvature, block fixed effects, partial drop-one ANOVA, pure error/lack-of-fit,
  residual/influence diagnostics, and capped chart payloads.
- NIST saturated 2^3 coefficient reference, hand/failure fixtures, dedicated
  create/restore API, dependency/checksum tamper rejection, common runtime/build
  provenance, Workbench result UI, and verified HTML report integration.
- Targeted validation passed for statistics/storage (22), DOE API (9),
  OpenAPI/frontend contracts (68), frontend lint/typecheck, and targeted Vitest
  (63). Full `scripts/check.ps1` passed with backend pytest 517 and frontend
  Vitest 84. Browser E2E passed through the complete DOE design/response/
  analysis UI after adding the required local-origin CORS `PUT` allowance.

Next allowed PR after this slice:

- DOE/RSM: Central Composite Design, axial/center points, quadratic model,
  contour/surface plot payloads, residual diagnostics, and design-region
  validation.

## Progress Update 162 - DOE Response Surface CCD And Quadratic Model

Implemented in the current working tree:

- Made `doe.response_surface` available at method version `0.1.0`, with design,
  analysis config, and analysis result schema `1`. The registry now contains 29
  stable catalog IDs, 27 available IDs, and 25 generic
  `MethodExecutionHandler` entries; both DOE methods use dedicated APIs.
- Added two-to-five-factor rotatable CCI and face-centered CCD generation with
  deterministic standard order, seeded run randomization, factorial/axial/
  center point labels, and actual low/high bounds fixed at the axial points.
- Added hierarchy-fixed full quadratic OLS, coefficient inference, partial
  drop-one ANOVA, pure error/lack-of-fit, residual/leverage/Cook diagnostics,
  stationary-point/Hessian classification, axial-bound and factorial-cube
  checks, and a capped 21x21 contour payload without automatic model switching.
- Reused schema-v9 DOE design/run/response/analysis storage. Design, response,
  config, result, method, and dependency checksums/IDs are verified on restore;
  common runtime/build/package provenance is reused and internal paths are not
  exposed.
- Added the official NIST/SEMATECH 11-run CCI Uniformity full-quadratic fixture,
  hand-checkable stationary-point tests, rank/constant failures, API restore/
  tamper tests, typed OpenAPI/frontend contracts, and the Workbench RSM panel.
- Fixed local startup CORS so the loopback Vite UI works at both
  `127.0.0.1:5173` and `localhost:5173`, while the backend remains bound to
  `127.0.0.1` and no wildcard or LAN origin is allowed.

Validation for this update:

- Response-surface statistics/reference tests: 6 passed.
- Response-surface API/persistence/tamper tests: 3 passed before the generic
  dedicated-route rejection assertion was added.
- Frontend lint and strict typecheck passed; frontend Vitest passed with 85
  tests before the final full-check count update.
- Full project check and browser E2E are pending the final validation pass below.

Next allowed PR after this slice:

- Response Optimizer: maximize/minimize/target/range objectives, bounded factor
  region, constraints, individual/composite desirability, deterministic CPU/
  time budgets, and auditable recommendation provenance.

## Progress Update 164 - Bounded Response Optimizer

Implemented in the current working tree:

- Added `regression.response_optimizer` v0.1.0 through dedicated RSM create and
  restore APIs while keeping its generic analysis-run page disabled with
  accurate guidance. Config and result schemas start at 1 and reuse schema-v9
  DOE analysis storage without a migration.
- Added maximize, minimize, target, and in-range Derringer-Suich objectives,
  importance-weighted geometric composite desirability, narrower factor bounds,
  actual-unit linear inequality constraints, seeded candidates, bounded SLSQP
  multi-start refinement, and explicit iteration/evaluation/time budgets.
- Required checksum-validated `doe.response_surface` source results with an
  identical design and factor space. Restore revalidates design, response,
  source bundle, config, result, dependency, and method-version relationships.
- Added a dedicated RSM-panel UI for one current response objective, factor
  bounds, an optional linear constraint, budgets, recommended actual/coded
  settings, point prediction, individual/composite desirability, constraint
  status, search diagnostics, and persistent limitations.
- Added the published NIST/SEMATECH tire-tread multiresponse fixture plus
  hand-checkable quadratic/constraint tests, typed API/OpenAPI/frontend
  contracts, tamper/error-redaction tests, and browser critical-path coverage.
- Results do not claim global optimality, do not include prediction intervals,
  and require source-model review plus a confirmation experiment. There is no
  silent algorithm switch or fabricated statistic.
- Local full validation passed with backend pytest 558, frontend Vitest 86,
  OpenAPI/frontend contracts 85, mypy over 88 source files, frontend lint/
  typecheck/build, and the complete browser E2E including optimizer execution.

Next allowed PR after this slice:

- Bayesian Optimization planning and contract for
  `doe.bayesian_optimization`: bounded factor space, objective/constraint,
  surrogate/acquisition, sequential-history, deterministic budget, provenance,
  audit trail, and explicit no-guaranteed-global-optimum policy. Do not add an
  executable method until the contract and reference strategy are approved.

## Progress Update 165 - Bayesian Optimization Planning Contract

Implemented in the current working tree:

- Added the stable `doe.bayesian_optimization` v0.1.0 catalog ID as the only
  planned method. The catalog now has 30 stable catalog IDs, 27 available IDs,
  two disabled IDs, one planned ID, and 25 generic
  `MethodExecutionHandler` entries.
- Fixed the first executable contract to one deterministic scalar objective,
  one to six bounded continuous factors, explicit completed-trial history,
  actual-unit linear inequalities, Matérn-5/2 Gaussian Process, Expected
  Improvement, one pending recommendation, and bounded seeded CPU/time/trial
  search budgets.
- Explicitly prohibited objective/Python/shell/equipment execution, fake
  observations, automatic recommendation completion, silent surrogate/
  acquisition fallback, raw path logging, and global-optimum claims.
- Added a machine-readable planning fixture with hand EI values, a known 1-D
  quadratic, and independently documented Branin minima plus source metadata.
  Contract tests reproduce those analytic values and assert there is no runtime
  handler or result expectation.
- Added Korean catalog, purpose-helper, role-guide, and method guidance copy.
  Generic `POST /analysis-runs` still returns
  `analysis_method_not_available` without a recommendation or fake statistic.
- No executable API, result/config/history schema, SQLite migration, new
  dependency, surrogate artifact, recommendation UI, or E2E execution step was
  added in this planning slice.
- Full local validation passed with backend pytest 564, frontend Vitest 86,
  OpenAPI/frontend contracts 85, mypy over 88 source files, frontend lint/
  typecheck/build, and the existing browser critical path.

Next allowed PR after this slice:

- Bayesian Optimization study/history foundation: immutable study version,
  bounded continuous factor schema, deterministic initial-design policy,
  completed/pending/abandoned trial state machine, observation-history SHA,
  relationship validation, typed API/storage tests, and no surrogate or next-
  point recommendation until that foundation is verified.

## Progress Update 166 - DOE/RSM/Optimizer Lifecycle Stabilization

Implemented in the current working tree:

- New RSM designs use design schema 2 and family `central_composite`, with
  rotatable/face-centered meaning carried by `alpha_mode`. Method v0.1.0 and
  analysis schemas remain unchanged. Legacy schema-1
  `central_composite_inscribed` assets retain their original payload and SHA.
- Factorial and RSM panels show the response-lock warning before analysis and
  disable response name/unit/run values/save after analysis. Direct backend
  writes to analyzed designs still return 409.
- `regression.response_optimizer` is v0.2.0 with config/result schema 2.
  Source eligibility blocks invalid rank, saturated/no inference, unusable
  residual variance, significant lack of fit, and invalid dependencies.
  Residual-df/influence/leverage/normality advisories require exact warning-code
  acknowledgment stored in config, result, envelope, and restore validation.
- Added `docs/doe_response_revision_contract.md` for immutable response
  revision IDs/SHA, current/history UI/API, correction flow, migration,
  analysis/optimizer dependency, multi-response, and tamper acceptance tests.
- Bayesian remains planning-only and has no scikit-learn dependency. Its future
  study/history foundation uses stdlib/Pydantic/SQLite; GP work requires a
  separate Windows/Python 3.10/CPU/offline/license/size dependency spike.
- The pre-slice approximately 608 kB and latest 612.20 kB main bundle warning is
  a separate backlog for DOE,
  Quality, and Regression dynamic imports, loading/error boundaries, route E2E,
  and before/after measurement.

Next allowed PR after this slice:

- Frontend module lazy loading for DOE/Quality/Regression panels, with explicit
  loading/error boundaries, route-level E2E coverage, and before/after bundle
  measurement. Do not mix it with DOE storage or method changes.

## Progress Update 167 - DOE Immutable Response Revision/History Foundation

Implemented in the current working tree:

- Added SQLite schema 10 immutable response revision, ordered-value, current-
  head, and analysis-revision relationship tables. Consistent schema-v9 current
  responses are deterministically backfilled as revision 1 without rewriting
  existing result artifacts or manufacturing unavailable overwrite history.
- Added response revision schema 1 create/current/paged-history/get/abandon
  contracts. Corrections require the exact current `supersedes_revision_id`,
  create a new revision, and never overwrite prior ordered values.
- Bumped `doe.factorial_design` to v0.3.0 and `doe.response_surface` to v0.2.0.
  Their analysis envelope/config schemas are 2 and pin revision ID/number/SHA;
  calculation result schemas remain 1. Stored analyses restore against their
  original revision after a newer correction becomes current.
- Bumped `regression.response_optimizer` to v0.3.0 with source-bundle schema 2;
  config/result schemas remain 2. Optimizer restore validates the exact source
  RSM analysis and response revision rather than the mutable current head.
- Added Factorial/RSM current/history displays and explicit correction mode.
  Analyzed revisions remain read-only, multi-response names retain independent
  revision streams, and stale history requests cannot overwrite newer panel
  state.
- Added migration, old-analysis restore, multi-response, paging, abandon,
  relation/checksum tamper, path-redaction, typed OpenAPI/frontend contract,
  optimizer dependency, component, and browser correction-flow coverage.
- Full local validation passed with backend pytest 582, frontend Vitest 90,
  OpenAPI/frontend contracts 91, mypy over 89 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E. The final main
  bundle is 618.10 kB and retains the expected code-splitting warning.

Next allowed PR after this slice:

- Frontend module lazy loading for DOE, Quality, and Regression panels. Add
  loading/error boundaries and route E2E coverage, measure the main bundle
  before/after, and leave Bayesian/storage/method behavior unchanged.

## Progress Update 168 - Frontend Module Lazy Loading

Implemented in the current working tree:

- Split Regression, Quality, and DOE execution panels into three module-level
  dynamic imports without changing method IDs, APIs, statistics, persistence,
  or dependencies. Response Optimizer remains nested in the DOE chunk.
- Added a stable execution-panel Suspense boundary, accessible loading state,
  sanitized import-failure state, reload command, and method-key error reset.
- Routed module, method-list, and purpose-helper selections through React 18
  `startTransition` so lazy suspension cannot replace the Workbench during a
  synchronous selection.
- Preserved the existing panel-content tests with a test-only direct loader and
  added focused loading/error/module-group tests.
- Extended browser E2E to observe all three module requests, open all three
  routes directly, and abort one isolated Regression import to verify the error
  boundary without exposing exception text.
- Reduced main JavaScript from 618.10 kB to 463.89 kB (24.95%). Regression is
  41.53 kB, Quality 58.83 kB, and DOE 57.26 kB. Total JS is 621.51 kB, so the
  result is an initial-payload improvement rather than total-code reduction.
- Full local validation passed with backend pytest 582, frontend Vitest 93,
  OpenAPI/frontend contracts 91, mypy over 89 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E including direct
  routes and isolated import-failure recovery.

Next allowed PR after this slice:

- Bayesian Optimization study/history foundation only: immutable study
  version, bounded factor/objective metadata, trial state machine, observation
  history SHA, storage/API relationship checks, and typed tests. Do not add a
  surrogate, recommendation, scikit-learn, or executable objective.

## Progress Update 169 - Bayesian Study/History Foundation

Implemented in the current working tree:

- Added SQLite schema 11 tables for study identity, immutable versioned
  definition, initial-design trials, immutable observation-history revisions,
  and the current history head. Migration from schema 10 creates no fabricated
  study or observation and leaves existing DOE assets unchanged.
- Added study payload schema 1 for one to six bounded continuous factors, one
  explicit manual objective, up to 16 actual-unit linear inequalities, method
  version, generator policy/budget, and canonical definition SHA-256.
- Added deterministic `sha256_counter_uniform_feasible_v1` initial trials.
  Generation is seed-stable across Python patch runtimes, bounded by 1,000
  attempts per requested point, constraint checked, and fails explicitly when
  it cannot fill the requested feasible set.
- Added only `origin=initial_design` pending trials. Users can explicitly enter
  one finite observation or abandon a trial; both transitions are terminal,
  and neither endpoint executes an objective or creates a recommendation.
- Added observation-history schema 1. Each completion requires the expected
  current revision ID and appends a SHA chain over definition SHA and completed
  trial ID/number/coordinate SHA/value ordered by trial number. Abandonment does
  not alter the observation history.
- Added create/list/restore, paged trial/history, immutable history-revision,
  observation, and abandon routes plus a synchronized typed frontend client.
  Restore rejects definition, coordinate, state, count, head, chain, or SHA
  relationship mismatches with stable redacted errors.
- `doe.bayesian_optimization` remains catalog version 0.1.0 and planned. Study
  schema 1/history schema 1 are asset schemas; no method config/result schema,
  generic execution, surrogate, EI, recommendation, fake value, scikit-learn,
  or objective execution was added.
- Full local validation passed with backend pytest 603, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, Ruff/format,
  frontend lint/typecheck/build, and browser E2E. The main bundle is 464.68 kB
  and all assets remain below the 500 kB warning threshold.

Next allowed PR after this slice:

- Perform the separate scikit-learn dependency spike only: Windows 11/Python
  3.10/CPU wheel, pinned NumPy/SciPy compatibility, license, offline behavior,
  import/startup/memory cost, and deterministic GP smoke. Do not add a
  production pin or executable GP/EI/recommendation API until review.

## Progress Update 170 - Conditional Scikit-learn Dependency Spike

Implemented in the current working tree:

- Selected scikit-learn 1.7.2 as the newest stable CPython 3.10 candidate.
  PyPI's current 1.9.0 release requires Python 3.11 and is outside the fixed
  product runtime.
- Added `scripts/run-scikit-learn-spike.ps1`, a synthetic fixed-kernel GP
  probe, an initial evidence validator, and focused backend contract tests.
  Output is restricted to a new external TEMP path and no product environment,
  dependency, or lockfile is modified.
- Downloaded exact Windows AMD64 wheels for NumPy 2.2.6, SciPy 1.15.3,
  scikit-learn 1.7.2, joblib 1.5.2, and threadpoolctl 3.6.0. The 60.442 MiB
  wheel set installed with `--no-index`; `pip check`, imports, invalid-proxy
  offline runtime, and single-threaded CPU execution passed.
- Two isolated fixed-kernel GP processes produced the same SHA-256 fingerprint
  `a0a6c5ab5d4aebb74a4a42bd988b427e3d991ad58db97977d1bc3c818909cfed`.
  Five-run timing and CPython process-tree peak working-set measurements are
  recorded in `docs/scikit_learn_dependency_spike.md`.
- The actual host identifies as Windows 10 Home build 19045. The evidence is
  therefore conditionally compatible but explicitly not approved for a
  production pin; the Windows 11 acceptance item remains open.
- `doe.bayesian_optimization` stays planning-only at 0.1.0, study/history
  schemas stay 1, and no config/result schema, surrogate, EI, recommendation,
  objective execution, or fake value was added.
- Full local validation passed with backend pytest 609, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E. The main bundle
  remains 464.68 kB and all assets remain below the 500 kB warning threshold.

Next allowed PR after this slice:

- Re-run the evidence-schema-2 dependency spike on Windows 11, CPython 3.10, CPU-only.
  Do not add a production pin or executable GP/EI until that result reports an
  approved Windows 11 gate.

## Progress Update 171 - Windows 11 Approval Gate Hardening

Implemented in the current working tree:

- Four independent local OS probes identify Windows 10 Home build 19045. The
  required Windows 11 client run remains an external-environment gate and was
  not inferred from package compatibility.
- Replaced the build-number-only evidence rule with evidence schema 2. It
  records `Win32_OperatingSystem` caption, build, and ProductType and approves
  only ProductType 1 workstations at build 22000 or newer.
- Added an explicit Windows Server 2025 build-26100 negative case. The current
  GitHub-hosted `windows-latest` server image cannot satisfy the Windows 11
  product requirement despite its newer build number.
- Pinned the evidence validator to the reviewed five exact package versions
  and cross-checks the candidate scikit-learn wheel name, byte size, and
  SHA-256 against the downloaded wheel manifest. Schema-1 evidence is not
  silently reinterpreted.
- Expanded the focused validator suite from six to nine tests for Windows 11
  workstation approval, Windows Server exclusion, false approval, wheel
  metadata tamper, manifest composition, nondeterminism, source archive,
  TEMP-only output, and the no-product-dependency contract.
- Re-ran the schema-2 wheel/offline/GP spike on the current host. It passed all
  technical checks and retained the deterministic fingerprint while correctly
  returning `candidate_approved_for_future_pin=false` for Windows 10 build
  19045/ProductType 1.
- No product dependency, lockfile, method/config/result schema, surrogate, EI,
  recommendation, objective execution, or UI behavior changed.
- Full local validation passed with backend pytest 612, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E. The main bundle
  remains 464.68 kB and all assets remain below the 500 kB warning threshold.

Next allowed PR after this slice:

- Run the evidence-schema-2 spike on an actual Windows 11 x64 workstation,
  CPython 3.10, CPU-only. Do not advance to a production pin or executable
  GP/EI until the validator returns an approved Windows 11 gate.

## Progress Update 172 - Scikit-learn Pin And Windows Hash Lock

Implemented in the current working tree:

- By explicit product-owner decision, actual Windows 11 client validation is
  now a mandatory release gate rather than a dependency-development gate. The
  current Windows 10 result is not relabeled as Windows 11 evidence.
- Added the exact `scikit-learn==1.7.2` production dependency. Bayesian remains
  planning-only at method version 0.1.0 with study/history schemas 1; no
  method/config/result version changed because no executable calculation or
  persisted recommendation was added.
- Added a 45-wheel CPython 3.10 Windows AMD64 SHA-256 lock covering backend
  runtime, dev, and build requirements. The reviewed joblib 1.5.2 and
  threadpoolctl 3.6.0 versions are resolver constraints, not direct project
  dependencies. Source archives, URLs, editable lock entries, missing hashes,
  duplicate packages, and reviewed-version drift are rejected.
- Updated bootstrap to install the wheel-only hash lock, install the backend
  editable with no dependency resolution/build isolation, and run `pip check`.
  Lock generation uses an external TEMP wheelhouse and rejects a repository
  output path.
- A clean external TEMP venv passed `--no-index --require-hashes` install,
  editable backend build, `pip check`, exact package imports, and API startup
  import with `sklearn_loaded=False`. This caught and then explicitly locked
  the `editables==0.5` build requirement.
- Added six lock/generator/bootstrap/startup contract tests and updated the
  nine spike-policy tests for the approved exact pin. Full local validation
  passed with backend pytest 618, frontend Vitest 93, OpenAPI/frontend
  contracts 104, mypy over 93 source files, Ruff/format, frontend
  lint/typecheck/build, and the complete browser E2E. The main bundle remains
  464.68 kB.
- `gh` is unavailable, so remote GitHub Actions and artifacts remain
  unverified. The repository settings and branch protection were unchanged.

Next allowed PR after this slice:

- Implement the first bounded Bayesian GP/EI executable vertical slice with
  explicit method/config/result versioning, independent posterior and EI
  parity, typed numerical failures, deterministic budgets, immutable
  recommendation persistence, relationship tamper coverage, and browser E2E.
  Do not execute arbitrary objectives or silently change kernels/acquisition
  policies. Actual Windows 11 x64 workstation validation is required before
  release.

## Progress Update 173 - Bounded Bayesian GP/EI Executable Slice

Status: implemented in the current working tree; final local validation is
recorded in `docs/ci_status.md`.

Completed:

- Moved `doe.bayesian_optimization` from planning `0.1.0` to dedicated API/UI
  method `0.2.0`. The catalog now contains 30 stable catalog IDs, 28 available
  IDs, two disabled generic pages, and 25 generic `MethodExecutionHandler`
  entries. Factorial, RSM, and Bayesian use dedicated APIs.
- Preserved study/history schemas 1 and legacy `0.1.0` restore. SQLite schema
  12 adds immutable recommendation records and `origin=recommendation` trials;
  recommendation config/result/model schemas each start at 1.
- Added spawn-worker Matérn-5/2 ARD GP fitting, analytic Expected Improvement,
  actual-unit linear constraint filtering, deterministic candidate/local search,
  bounded fit/search/time budgets, and explicit no-fallback errors.
- Persisted source history, config/result/model checksums, full runtime/package
  provenance, pending trial snapshots, confirmation-run warnings, and explicit
  no-global-optimum limitations. A shared validator checks recommendation,
  history, trial, config, result, model, and provenance relationships on study,
  list, and restore paths.
- Added the dedicated `BayesianOptimizationPanel`, typed client/OpenAPI guards,
  hand EI and direct Matérn posterior parity, migration/legacy/tamper/API tests,
  and a browser flow that records observations before requesting a candidate.
- The app still does not execute objectives or load pickle/joblib. Actual
  Windows 11 x64 validation remains a release gate and is not claimed from the
  measured Windows 10 host.

Next allowed PR:

- Stabilize the sequential Bayesian lifecycle by broadening relationship-tamper
  coverage, characterizing multi-seed Branin regret under declared budgets,
  exposing existing linear constraints in the UI, and measuring worker startup,
  fit, and search cost. Do not add a new acquisition algorithm or objective
  execution in that PR.

## Progress Update 174 - Bayesian Sequential Lifecycle Stabilization

Status: implemented in the current working tree; final local validation is
recorded in `docs/ci_status.md`.

Completed:

- Extended recommendation restore validation to cross-check result/trial
  coordinates, factor scaling, source-history observations and incumbent,
  request/result budgets, model counts, constraint evaluations, required
  warnings, finite values, and package provenance after checksum validation.
- Added checksum-recomputed relationship tamper for nine independent fields and
  verified rejection through study, recommendation-list, and single-restore
  endpoints without internal path disclosure.
- Added a five-seed, 20-trial Branin sequential reference with maximum simple
  regret `0.20` and median simple regret `0.15` gates under declared GP/EI
  budgets. This is a reference harness, not product objective execution.
- Exposed the existing actual-unit linear-inequality contract in the dedicated
  UI, including pre-submit validation, stored equations, and recommendation
  feasibility output. Browser coverage uses a constrained one-factor study.
- Added a repeatable Windows/CPython 3.10 CPU-only benchmark for empty spawn,
  worker round trip, child calculation, GP fit, non-fit calculation, and
  bootstrap/IPC overhead. The measured Windows 10 values are descriptive and
  are not relabeled as Windows 11 release evidence.
- Kept method `0.2.0`, all recommendation schemas at 1, SQLite schema 12, the
  Matern-5/2/analytic-EI calculation, and no-objective-execution policy
  unchanged.
- Full `scripts/check.ps1` passed with backend pytest 635, frontend Vitest 95,
  OpenAPI/frontend contracts 110, mypy over 96 source files, Ruff/format,
  frontend lint/typecheck, and production build. Browser E2E passed with
  diagnostics root
  `.tmp\e2e-diagnostics-bayesian-lifecycle-stabilization`.

Next allowed PR:

- Define the Phase II attribute-control-chart limits contract/reference
  foundation with immutable baseline provenance and explicit Phase I/Phase II
  semantics before changing executable chart behavior.

## Progress Update 175 - Phase II Attribute Chart Contract Foundation

Status: implemented in the current working tree; final local validation is
recorded in `docs/ci_status.md`.

Completed:

- Kept current `quality.attribute_control_chart` execution at method `0.1.0`,
  result schema `1`, and Phase I-only behavior. Production options/calculation,
  registry availability, formulas, and persisted output were not changed.
- Added `docs/attribute_control_chart_phase_2_contract.md` with an immutable
  app-created limit-set schema `1`, baseline/target provenance, canonical SHA,
  restore/tamper gates, P/NP/C/U frozen-limit semantics, reserved typed errors,
  and implementation acceptance criteria.
- Reserved method `0.2.0` and result schema `2` for the first executable Phase
  II slice because request dependencies, limit source, and result meaning will
  change. Existing `0.1.0` results must remain Phase I without migration or
  silent reinterpretation.
- Added a synthetic policy-adjusted reference fixture that independently
  evaluates frozen P/NP/C/U centers, varying/fixed limits, natural bounds, and
  strict signal behavior. Contract tests also prove that current options reject
  `phase` and `limit_set_id` and the production result remains Phase I.
- Updated the panel and critical-path expectations to state that current
  execution estimates Phase I limits from all filtered valid observations and
  does not apply stored Phase II limits. Results identify the phase and limit
  source explicitly.
- Kept WECO/Nelson rules, Laney correction, exact probability limits,
  user-entered naked limits, Phase II execution, new chart families, and all
  production statistical calculations out of this foundation.
- Full `scripts/check.ps1` passed with backend pytest 640, frontend Vitest 95,
  OpenAPI/frontend contracts 110, mypy over 96 source files, Ruff/format,
  frontend lint/typecheck, and production build. Browser E2E passed with
  diagnostics root `.tmp\e2e-diagnostics-attribute-phase2-contract`.
- The measured host remains Windows 10 Home build 19045. Windows 11 validation
  remains a mandatory release gate, and remote Actions remain unverified
  because `gh` is unavailable.

Next allowed PR:

- Implement immutable control-limit-set storage and dedicated create/get/list
  APIs with a SQLite migration, Phase I baseline promotion eligibility,
  canonical asset checksum, dependency/current-history/tamper/upgrade tests,
  and typed frontend/OpenAPI contracts. Do not execute monitoring data against
  frozen limits in that storage/API foundation.

## Progress Update 176 - Immutable Attribute Limit-Set Storage/API

Status: implemented and validated in the current working tree.

Completed:

- Raised SQLite metadata to schema 13 with immutable
  `attribute_control_limit_sets`. Schema 12 upgrades add an empty table without
  rewriting Bayesian, DOE, analysis, dataset, or existing result records.
- Persisted app-created limit-set schema 1 JSON atomically and pinned source
  analysis/dataset/config/result/schema/canonical/filter/row-snapshot hashes,
  P/NP/C/U meaning, frozen center, eligibility, asset SHA, and close time.
- Added idempotent POST plus checksum/relation/source-validated GET and filtered
  paged list routes under `/api/v1/quality/attribute-control-limit-sets`. No
  PUT/PATCH/DELETE or monitoring endpoint exists.
- Required 20 or more complete untruncated points, no existing Phase I signal,
  usable expected counts, and Pearson dispersion no greater than 2. The service
  independently recomputes center, point limits, strict signals, dispersion,
  totals, and NP fixed sample size before promotion.
- Added controlled frontend routes/client/types and OpenAPI guards, but no
  Phase II mode, selector, or execution UI.
- Added migration/metadata tests and P/NP/C/U API coverage for idempotence,
  ineligibility/stale source, checksum/path/DB relationship tamper, rehashed
  asset/source result, row-snapshot/canonical/schema tamper, redaction, and
  immutability.
- Full `scripts/check.ps1` passed with backend pytest 663, frontend Vitest 95,
  OpenAPI/frontend contracts 116, mypy over 98 source files, Ruff/format over
  150 Python files, frontend lint/typecheck, and production build. The
  successful run used an explicit D-drive pytest basetemp because the host C
  drive lacked temp space.
- Browser E2E passed on ports `8025`/`5225` with diagnostics root
  `.tmp\e2e-diagnostics-attribute-limit-set-storage`. It retains the Phase I
  P-chart and all prior critical flows without claiming an unimplemented Phase
  II browser path.
- The measured host remains Windows 10 Home build 19045. Windows 11 validation
  remains a mandatory release gate, and remote Actions remain unverified
  because `gh` is unavailable.

Next allowed PR:

- Implement the first Phase II frozen-limit monitoring vertical slice at
  method `0.2.0`/result schema `2`, using only verified app-created limit sets
  with target compatibility preflight, stored provenance, restore/export
  consistency, typed UI selection, and browser E2E. Keep WECO/Nelson, Laney,
  exact limits, naked user limits, and automatic baseline refit out of scope.

## Progress Update 177 - Bayesian Lifecycle Correctness Stabilization

Status: implemented in the current working tree; final full validation is
recorded in `docs/ci_status.md`.

Completed:

- Bumped `doe.bayesian_optimization` to patch version `0.2.1` while retaining
  study/history and recommendation config/result/model schemas 1, SQLite schema
  13, and restore of valid stored `0.2.0` recommendations without relabeling.
- Enforced `max(2, factor_count + 1)` initial trials in the backend and UI,
  centralized the 200-trial/200-completed/201-history limits, and covered exact
  upper-bound restore plus over-limit rejection.
- Prevented an initial-trial abandonment that would leave too few possible
  completed observations, while retaining surplus-initial and recommendation
  abandonment. Completed, pending, and abandoned coordinates are all excluded
  from later candidates within the declared duplicate tolerance.
- Added the actual latest-recommendation endpoint and transient current-trial
  reconciliation without changing the immutable checksummed snapshot. The UI
  distinguishes pending, completed with actual observation, abandoned, and
  historical recommendations.
- Exposed the effective request-level total-trial budget, aligned frontend
  blockers with the backend hard limit, and mapped fit/acquisition/worker time
  exhaustion to `bayesian_optimization_budget_exhausted` rather than a
  surrogate-fit error.
- Added accessible inline confirmation for irreversible observation and
  abandonment transitions, transition locking, error input retention, and
  refresh of study/latest state after success.
- Added `docs/bayesian_study_lifecycle_contract.md` for the still-unimplemented
  study close/abandon API, optimistic close transition, read-only restore,
  retention, migration, audit, and acceptance criteria.
- The initial targeted Bayesian/OpenAPI backend run passed 155 tests, the
  follow-up recommendation compatibility suite passed 36 tests, frontend Vitest
  passed 98 tests, and the lifecycle-expanded browser E2E passed on ports
  `8027`/`5227`. The final full critical-path rerun also passed in 57.9 seconds
  on ports `8028`/`5228`; after the restore-boundary review it passed again in
  56.8 seconds on ports `8029`/`5229`.
- Full `scripts/check.ps1` passed with Ruff/format over 150 Python files, mypy
  over 98 source files, backend pytest 687, frontend lint/typecheck, frontend
  Vitest 98, and production build. The direct OpenAPI/frontend contract suite
  passed 117 tests. Main JavaScript is 467.18 kB / 110.05 kB gzip and the DOE
  chunk is 79.80 kB / 18.32 kB gzip.
- The measured host remains Windows 10 Home build 19045 with CPython 3.10.11
  and Node 24.17.0. Windows 11/Node 22 remains a mandatory release gate and is
  not inferred from this development validation.

Next development order:

1. Implement Phase II frozen-limit monitoring only from verified app-created
   limit sets.
2. Run clean Windows 11/Python 3.10/Node 22 release validation.
3. Implement Bayesian study close/abandon and retention from the new contract.
4. Continue the advanced quality/statistics backlog.

## Progress Update 178 - Phase II Frozen-Limit Monitoring

Status: implemented and validated in the current working tree.

Completed:

- Bumped `quality.attribute_control_chart` to method `0.2.0` and result schema
  `2`. New Phase I results explicitly record `phase_1`; stored method `0.1.0` /
  schema-1 results remain restorable and promotable without relabeling or
  migration. Limit-set asset schema 1, common config schema 2, and SQLite
  schema 13 remain unchanged.
- Added explicit Phase II options and a typed monitoring preflight. The target
  must match chart/count meaning and compatible column semantics; NP requires
  the frozen sample size and C requires current-target equal-opportunity
  confirmation. Phase II accepts only a verified app-created `limit_set_id`.
- Added production P/NP/C/U frozen-limit calculations with natural bounds and
  strict outside-only signals. Monitoring never refits the center or limits,
  switches chart type, or falls back to Phase I.
- Persisted limit-set source identity and SHA, source analysis/dataset/result,
  close time, target dataset/schema/canonical/filter/row snapshot, selected
  target columns, row counts, and fixed-limit policy. Restore and common
  JSON/CSV/HTML export reject result/config/asset/target relationship or
  checksum mismatches with a redacted stable dependency error.
- Added an explicit Phase I/Phase II panel, deliberate verified-limit selector,
  target preflight, latest-request stale-response protection, run blockers, and
  Phase II source/close-time result labels.
- Added formula/reference, cross-dataset API, schema mismatch, NP/C gate,
  legacy promotion, tamper, restore/export, frontend race/rendering, and
  OpenAPI contract tests. Full `scripts/check.ps1` passed with Ruff/format over
  152 Python files, mypy over 99 source files, backend pytest 702, frontend
  Vitest 100, OpenAPI/frontend contracts 120, lint/typecheck, and production
  build.
- Chromium E2E passed in 58.1 seconds on ports `8030`/`5230`, including real
  Phase I baseline promotion and Phase II monitoring on a separate dataset.
  The measured host is Windows 10 Home build 19045 with CPython 3.10.11 and
  Node 24.17.0; Windows 11/Python 3.10/Node 22 remains a mandatory release
  gate. Remote Actions remain unverified because `gh` is not installed.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22/CPU-only release validation.
2. Implement Bayesian study close/abandon and retention from the lifecycle
   contract.
3. Continue Phase II rules/limits and advanced quality/statistics only through
   separately approved contracts.

## Progress Update 179 - Bayesian Study Close And Read-Only Lifecycle

Status: implemented and validated in the current working tree.

Completed:

- Bumped `doe.bayesian_optimization` to patch `0.2.2` without changing the GP,
  EI, duplicate policy, study/history schema 1, or recommendation config/result/
  model schemas 1. Valid `0.2.0`/`0.2.1` artifacts retain their recorded
  versions.
- Advanced SQLite metadata from schema 13 to 14 with immutable lifecycle-event
  schema 1 and nullable `predecessor_study_id`. Schema-13 active studies upgrade
  without invented close status, reason, or timestamp.
- Added optimistic `active -> completed|abandoned` close, exact idempotent retry,
  pending/completion requirement gates, stable redacted errors, canonical event
  SHA, and final history/count/definition/latest-recommendation relationships.
- Added explicit `close_study` abandon intent so a user can terminate below the
  recommendation minimum without silently abandoning pending trials. After
  close, recommendation, observation, and abandon storage transactions reject
  mutation under a write lock while all restore endpoints remain available.
- Added typed frontend/OpenAPI fields and route, inline close confirmation,
  completed/abandoned reason selection, read-only restore, and successor draft
  creation that copies only the immutable definition inputs and records lineage.
  Close is not deletion; retention remains separate.
- Full `scripts/check.ps1` passed in 734.4 seconds with Ruff/format over 153
  Python files, mypy over 99 source files, backend pytest 712, frontend Vitest
  101, lint/typecheck, and production build. OpenAPI/frontend contracts remain
  120; the targeted lifecycle/Bayesian/OpenAPI suite passed 189 tests.
- Chromium E2E passed in 58.6 seconds on ports `8031`/`5231`, including final
  Bayesian observation, completed close, read-only controls, reload restore,
  and the successor command. Main is 473.59 kB and DOE is 87.24 kB.
- Validation used Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0 from an uncommitted tree based on
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Windows 11/Python 3.10/Node 22
  remains the release gate. Remote Actions remain unverified because `gh` is
  not installed.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22/CPU-only release validation.
2. Implement retention/deletion and workspace management with inbound-reference
   checks and explicit ownership-graph confirmation. Do not equate close with
   deletion.
3. Continue advanced quality/statistics only through an approved contract.

## Progress Update 180 - Closed Bayesian Study Metadata Deletion

Status: implemented and validated in the current working tree.

Completed:

- Added typed deletion preflight and confirmed delete routes for a closed
  Bayesian study. Preflight validates the complete immutable graph, reports
  exact metadata/file counts, and hashes status, version, current history,
  lifecycle event, successor references, and counts into a canonical manifest.
- Active studies and referenced predecessors return stable blockers. Delete
  requires the exact study ID and latest manifest, reacquires a SQLite write
  lock, compares the graph, and removes all owned metadata in one transaction
  without cascade into a successor.
- Added frontend impact review and separate irreversible confirmation, stale
  response guards, catalog refresh, stable Korean error guidance, OpenAPI/type
  guards, API/tamper/redaction tests, and browser removal verification.
- Added `docs/workspace_retention_contract.md`. The implemented Bayesian graph
  is metadata-only (`file_count=0`); dataset, analysis/export, DOE, model, and
  limit-set files require later trusted-path, quarantine, Windows-lock, and
  crash-recovery work.
- Kept Bayesian method `0.2.2`, SQLite schema 14, and existing study/history/
  recommendation/lifecycle schemas unchanged. Preflight and delete-response
  operational schemas start at 1.
- Full `scripts/check.ps1` passed in 764.9 seconds: 721 backend tests, 102
  frontend tests, 131 OpenAPI/frontend contract tests, Ruff/format over 153
  files, mypy over 99 source files, lint/typecheck, and production build. Main
  is 474.80 kB / 111.96 kB gzip and DOE is 90.79 kB / 20.76 kB gzip.
- Chromium E2E passed in 62.2 seconds on `8031`/`5231`. Two preliminary runs
  were blocked before app execution by Windows socket-bind `EACCES` on alternate
  ports; the final isolated workspace run passed every existing flow.
- The host remains Windows 10 Home build 19045, Python 3.10.11, and Node
  24.17.0 on base SHA `0cbce01d2fa2914459c5be69f070e1703cb631dd`.
  Windows 11/Node 22 remains release evidence, and remote Actions are unverified
  because `gh` is unavailable.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22 release validation.
2. Implement analysis/export file-owning deletion as the next bounded retention
   slice with quarantine and recovery tests.
3. Expand ownership graphs to datasets, DOE, models, and limit sets only after
   that file lifecycle is proven.

## Progress Update 181 - Individual Analysis Export File Deletion

Status: implemented and validated in the current working tree.

Completed:

- Added typed preflight and exact-confirmation DELETE APIs for one app-created
  JSON/CSV/HTML analysis export or regression-prediction CSV export. The
  operation preserves the parent analysis result, row snapshots, model,
  prediction, and every other export.
- Bound deletion to the exact analysis/export ownership row, approved artifact
  kind/media type, kind-specific relative path, non-symlink regular file,
  SHA-256, byte size, parent method/version/update/stale/result state, and a
  canonical manifest. Responses expose no internal path or raw result value.
- Added same-directory quarantine rename, post-rename SHA/size recheck,
  conditional `BEGIN IMMEDIATE` metadata deletion, compensating restore on DB
  conflict, pending-cleanup status, and startup recovery. Recovery removes a
  committed orphan, restores a metadata-owned file only when SHA matches, and
  leaves tampered quarantine pending.
- Added export-list impact review, separate irreversible confirmation, exact
  file/metadata counts, parent-result preservation copy, list refresh, and
  latest-request guards for late preflight/delete responses after reset.
- Kept all statistical method versions, existing export/result schemas, and
  SQLite schema 14 unchanged. Operational deletion preflight/response schemas
  start at 1.
- Full `scripts/check.ps1` passed in 746.7 seconds: backend pytest 731,
  frontend Vitest 105, OpenAPI/frontend contracts 137, Ruff/format over 154
  Python files, mypy over 99 source files, lint/typecheck, and production
  build. Main is 480.68 kB / 112.99 kB gzip.
- Chromium E2E passed in 59.9 seconds on `8031`/`5231`, including three export
  creations, JSON download, one export impact/confirmation/deletion, list
  reduction, and parent analysis-result preservation.
- Validation used Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0 on base SHA `0cbce01d2fa2914459c5be69f070e1703cb631dd`.
  Windows 11/Python 3.10/Node 22 remains release evidence. Remote Actions are
  unverified because `gh` is unavailable.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22 release validation.
2. Implement analysis-run root deletion as a separate ownership-graph slice:
   include its result, row snapshots, and exports, but block model, prediction,
   limit-set, or other inbound dependencies instead of cascading silently.
3. Extend reviewed root-graph deletion to datasets, DOE, models, and limit sets.

## Progress Update 182 - Analysis-Run Root Deletion

Completed:

- Added deletion preflight and exact analysis-ID/manifest confirmation for one
  succeeded stored analysis run. Preflight verifies the result envelope,
  config-to-row-snapshot relation, every approved artifact kind/path/media type,
  SHA-256, byte size, and prediction cross-artifact relationships.
- Added independent blockers for app-created regression models, dependent
  regression predictions, attribute-control limit sets, and job audit records.
  The operation never silently cascades or severs those relationships.
- Added Windows-safe short same-directory quarantine names, post-move integrity
  checks, exact run/artifact revalidation under `BEGIN IMMEDIATE`, reverse-order
  restoration after partial move or DB failure, and startup recovery for
  committed, metadata-owned, and tampered quarantines.
- Added typed API/OpenAPI/frontend contracts, impact counts, separate
  irreversible confirmation, history refresh, and clearing of deleted current,
  restored, comparison, and export state. Independent latest-request guards
  prevent late preflight/delete responses from reviving reset state.
- Kept all statistical method versions, result/config meanings, artifact
  checksum payloads, and SQLite schema 14 unchanged. Operational deletion
  preflight/response schemas start at 1.
- Backend retention tests cover exact deletion, unrelated-run preservation,
  stale confirmation, path/checksum tamper, model/prediction/limit-set/job
  blockers, partial quarantine failure, DB rollback restoration, pending
  cleanup, and next-start restore/removal.
- Final `scripts/check.ps1` passed in 792.7 seconds with backend pytest 738,
  frontend Vitest 109, OpenAPI/frontend contracts 139, Ruff/format over 156
  Python files, mypy over 100 source files, lint/typecheck, and production
  build. Main JavaScript is 487.56 kB / 114.21 kB gzip.
- Chromium E2E passed in 66.5 seconds on `8031`/`5231` with workspace
  `.tmp/e2e-workspace-analysis-run-retention-final`. It verifies two-to-one
  history reduction and clears deleted restore/comparison state while retaining
  all existing prediction, Phase II, DOE, Bayesian, parser, and lazy-panel paths.

Next development order:

1. Add explicit regression-model and attribute-control-limit-set deletion
   foundations so their dependent source analyses can later become eligible.
2. Run clean Windows 11/Python 3.10/Node 22/CPU-only release validation.
3. Extend the reviewed ownership graph to datasets and DOE designs before any
   bulk, age-based, or automatic cleanup.
4. Continue advanced quality/statistics only through an approved contract.

## Progress Update 183 - Regression Model And Limit-Set Deletion

Completed:

- Added checksum-validated deletion preflight and exact manifest confirmation
  for app-created regression models and attribute-control limit sets. Neither
  response exposes an internal path, source filename, predictor value, or
  control-chart observation.
- Regression-model deletion preserves the source linear-model analysis and is
  blocked by every stored prediction that references the model or source
  analysis. Attribute-control-limit-set deletion preserves its Phase I source
  analysis and is blocked by every Phase II analysis that references the
  `limit_set_id`; a stale Phase I source does not by itself prevent explicit
  deletion of an otherwise valid immutable limit set.
- Added short same-directory quarantine names, post-move SHA/size validation,
  conditional `BEGIN IMMEDIATE` metadata deletion, compensating restoration,
  pending cleanup, and startup recovery for both asset kinds.
- Added typed API/OpenAPI/frontend contracts, impact counts, separate exact
  confirmation, read-only dependency blockers, and latest-request guards for
  late model/limit-set preflight or delete responses.
- Statistical method versions, persisted result/config meanings, regression
  model manifest schema 2, limit-set asset schema 1, and SQLite schema 14 remain
  unchanged. The two operational deletion contracts start at schema 1.
- Final `scripts/check.ps1` passed in 781.8 seconds with backend pytest 750,
  frontend Vitest 111, OpenAPI/frontend contracts 150, Ruff/format over 158
  Python files, mypy over 101 source files, lint/typecheck, and production
  build. Main JavaScript is 490.15 kB / 114.58 kB gzip.
- Chromium E2E passed in 99.3 seconds on `8031`/`5231` with workspace
  `.tmp/e2e-workspace-asset-retention-final-3`, including the prediction and
  Phase II dependency blockers while retaining all earlier critical paths.
- Validation used Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0 from base SHA `0cbce01d2fa2914459c5be69f070e1703cb631dd`.
  Windows 11/Python 3.10/Node 22 remains release evidence; remote Actions are
  unverified because `gh` is unavailable.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22/CPU-only release validation.
2. Define and implement dataset-root deletion with explicit inbound-reference
   blockers and no silent cascade.
3. Extend reviewed retention to DOE designs and immutable response revisions.
4. Add bulk, age-based, or automatic cleanup only after those ownership graphs
   and recovery behavior are validated.
5. Continue advanced quality/statistics only through an approved contract.

## Progress Update 184 - Phase II Boundary And Model Availability Stabilization

Completed:

- Bumped `quality.attribute_control_chart` to method `0.3.0` and result schema
  3. Phase I still requires two usable points and limit-set promotion still
  requires 20, while Phase II accepts one valid monitoring point without
  refitting the baseline.
- One-point Phase II results preserve frozen center/LCL/UCL and strict outside-
  limit signals, but store dispersion as unavailable with degrees of freedom 0,
  ratio null, and
  `attribute_control_chart_dispersion_insufficient_points`. At n>=2 the prior
  Pearson calculation is unchanged. Zero usable points return
  `attribute_control_chart_phase_2_no_usable_points`.
- Kept immutable limit-set asset schema 1, analysis config schema 2, and SQLite
  schema 14 unchanged. Stored v0.1/schema-1 and v0.2/schema-2 results restore and
  export under their original versions without rewriting.
- Bumped monitoring preflight to schema 2 and added typed
  `validation_scope=schema_and_dependency_only` plus
  `row_data_validated=false`. The UI states that row values and filter results
  are revalidated during execution; NP/count/denominator and usable-row checks
  remain mandatory at execution.
- Added checksum-validated regression-model availability checks for current and
  restored linear-model results. Missing models map to
  `unavailable_or_deleted`; manifest/path/checksum failures map separately to
  `integrity_error`. Both states preserve the fit result while disabling
  prediction preflight, execution, and CSV actions.
- The current dataset version UUID, and no raw rows or filename, is kept in
  session storage so a reload can restore version/profile/preview through
  validated backend APIs. This makes model deletion and restored-fit
  availability consistent before and after reload.
- Backend tests cover one-point P/NP/C/U, n=1/n=2 dispersion, zero usable rows,
  strict signal equality/outside boundaries, schema-ready NP row mismatch,
  old-result restore, all common exports, availability error distinction, and
  OpenAPI/frontend alignment. Frontend tests cover one-point rendering,
  preflight wording, availability states, deletion, stale response handling,
  and retained fit output.
- `scripts/check.ps1` passed in 771.5 seconds: backend pytest 763, frontend
  Vitest 114, direct OpenAPI/frontend contract collection 148, Ruff/format,
  mypy, lint, typecheck, and production build. Main JavaScript is 491.75 kB /
  114.96 kB gzip.
- Final Chromium E2E passed in 69.2 seconds with diagnostics at
  `.tmp/e2e-diagnostics`, including one-point Phase II result/export/restore
  and model deletion/reload/stored-fit restore. The host
  was Windows 10 build 19045, CPython 3.10.11, and Node 24.17.0, so this remains
  development evidence rather than the Windows 11/Node 22 release gate.
- Remote Actions remain unverified because `gh` is not installed.

Next development order:

1. Run the clean Windows 11/Python 3.10/Node 22/CPU-only release gate.
2. Verify the resulting main run and required Windows/E2E checks in GitHub.
3. Improve Bayesian catalog/successor UX without changing GP/EI behavior.
4. Implement dataset-root and then DOE-root retention through separate reviewed
   dependency graphs with no silent cascade.
5. Continue advanced quality/statistics only through an approved contract.

## Progress Update 185 - Safe Paste Staging And Canonical Preview UX

Status: implemented and validated in the current working tree.

Completed:

- Split pasted-data intake into `PasteDatasetPanel`, `PastePreviewGrid`, a pure
  preview parser, and `usePastedDatasetDraft`. The exact clipboard string stays
  in a ref/fallback textarea and is sent unchanged to the existing paste API;
  parser cells are never serialized back into the request.
- Added a focusable `text/plain` paste surface, raw/grid modes, spreadsheet
  row/column headers, empty and ragged-row cues, selected-cell inspector,
  keyboard movement, presentation-only header toggle, and explicit comparison
  with the authoritative server header suggestion.
- Materialization is capped at 200 rows, 100 columns, and 20,000 cells. Browser
  structure scanning is capped at 2,000,000 characters and labels counts as
  lower bounds when reached. Formula-like/HTML-looking values remain inert text.
- Successful registration clears raw ref/textarea/preview/selection. Failure
  keeps the in-session draft, while reload restores only a confirmed dataset
  version ID and never raw paste text from browser storage.
- Canonical preview remains checksum-validated and server-paged, with 10/25/50/
  100 page sizes, bounded row jump, sticky headers, horizontal scroll, explicit
  missing/empty labels, and one full-value inspector.
- A generic regression-model availability request failure now remains visible
  as a transient error with explicit retry; it is not conflated with missing or
  integrity-error states.
- The backend paste/OpenAPI/result contracts, SQLite schema, dataset/version
  meaning, and every statistical method/result version remain unchanged. A
  probabilistic raw-value-redaction assertion was narrowed to error message and
  developer-detail fields so random correlation UUID digits cannot cause a
  false failure.
- Full `scripts/check.ps1` passed in 769.0 seconds with backend pytest 763,
  frontend Vitest 131, OpenAPI/frontend contracts 148, Ruff/format over 158
  Python files, mypy over 101 source files, lint/typecheck, and production
  build. The final expanded Chromium E2E passed in 70.8 seconds with diagnostics
  at `.tmp/e2e-diagnostics` and retained every prior critical path.
- Production assets are 508.32 kB / 120.48 kB gzip for main, 46.75 kB / 9.69
  kB for Regression, 64.25 kB / 11.97 kB for Quality, and 90.79 kB / 20.77 kB
  for DOE. Main now emits the Vite 500 kB warning; a measured first-screen
  loading/code-splitting follow-up is required rather than hiding the warning.
- Validation used Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0 from pushed base SHA
  `702e20f0ed1a377d411cb8d7d3a6faa2c4fcbd6f`. It is development evidence, not
  the Windows 11/Node 22 release gate. Remote Actions remain unverified because
  `gh` is not installed.

Next development order:

1. Run the clean Windows 11/Python 3.10/Node 22 release gate.
2. Verify remote GitHub Actions and required Windows/E2E checks.
3. Improve Bayesian catalog/successor UX without changing GP/EI behavior.
4. Implement dataset-root and then DOE-root retention through separately
   reviewed dependency graphs with explicit blockers and quarantine recovery.
5. Continue advanced quality/statistics only through approved contracts.

## Progress Update 186 - Dedicated Predict And Optimizer Workflows

- All 30 stable IDs are catalog-available: 25 generic handlers and five
  dedicated workflows. Dedicated requests sent to generic analysis-run return
  `analysis_method_uses_dedicated_api` without creating a result.
- Predict now has a metadata-only regression-model catalog and top-level route;
  Optimizer has a metadata-only RSM analysis catalog and top-level route.
  Selection uses ID-only query state and then full checksum/dependency GETs.
- Linear Model/top-level Predict share `RegressionPredictionPanel`; RSM and
  top-level Optimizer share `ResponseOptimizerPanel`. Calculation and stored
  schemas are unchanged, so versions remain Predict `0.2.0` and Optimizer
  `0.3.0`.
- Full local development validation passed with backend 773, frontend 133,
  OpenAPI/frontend contracts 155, and Chromium E2E 76.9 seconds. Main measured
  511.60 kB / 121.24 kB gzip and retains the 500 kB warning.
- The completed entrypoint slice is pushed at
  `b12c3b26235089fa28e5b48b1faa2cf627e3bec0`. A clean checkout of that SHA
  passed bootstrap, full check (backend 773, frontend 133, OpenAPI/frontend
  155), and Chromium E2E in 78.6 seconds. Windows 10/Python 3.10/Node 24 is
  development evidence; Windows 11/Node 22 and remote Actions remain
  unverified (`gh` unavailable).

## Progress Update 187 - Tutorial Data And Dedicated Result Restore

Current bounded worktree:

- Predict writes `prediction_id` to its ID-only query after execution and
  reloads the checksum-validated stored result and first row page, then keeps
  CSV creation/download available without recalculation. A deleted model still blocks new prediction
  but no longer erases access to its immutable stored prediction.
- Response Optimizer writes `optimization_id` to its query and restores the
  existing verified optimization only when design version and exact source RSM
  analysis match. Both parent-embedded workflows still use the same reusable
  panels.
- Dedicated routes no longer render dataset-scoped generic analysis history or
  generic result export. Prediction paging/CSV and stored optimizer restore
  remain inside the relevant dedicated workflow.
- The Bayesian purpose helper now describes the executable Matérn-5/2 GP and
  Expected Improvement recommendation while stating that it is neither an
  observation nor a global-optimum guarantee.
- `examples/tutorial/` contains eight deterministic synthetic data files,
  manifest, expected API results, generator, and usage README. Seed 20260718
  produces 240 training rows, 48 valid prediction-target rows, and separate
  paste, invalid-target, Gage, factorial, RSM, and Bayesian inputs.
- `scripts/tutorial_smoke.ps1` runs 18 actual Studio API result sections and
  compares only normalized, ID-free results with explicit tolerances. The
  Korean end-to-end guide is `docs/studio_end_to_end_tutorial_ko.md`.
- Prediction remains method `0.2.0` with result/config/rows schemas 2/3/2;
  optimizer remains method `0.3.0` with config/result/source-bundle schemas
  2/2/2. No statistical formula, method version, SQLite schema, or stored
  artifact meaning changes.
- Final local development validation passed: `scripts/check.ps1` completed in
  825.1 seconds with backend 777, frontend 137, OpenAPI/frontend 155, and a
  production build. Chromium E2E passed in 74.6 seconds, and the 18-section
  tutorial smoke passed in 18.6 seconds. Main is 512.33 kB / 121.39 kB gzip and
  retains the explicit 500 kB warning.
- The host is Windows 10 Home build 19045, Python 3.10.11, and Node 24.17.0.
  This is development evidence, not the Windows 11/Python 3.10/Node 22 release
  gate. Remote Actions remain unverified because `gh` is unavailable.

Next development order:

1. Clean Windows 11/Python 3.10/Node 22 release gate.
2. Remote Actions, required checks, and repository protection review.
3. Measured main-bundle optimization.
4. Regression/RSM source catalog search and large-catalog benchmark.
5. Bayesian catalog/successor UX, then dataset/DOE root retention.

## Progress Update 188 - Tutorial Truth, Help Center, And Report Center P0

- `tutorial_expected_results.json` remains the numeric source of truth. The
  Korean tutorial now contains 18 generated marker blocks and
  `scripts/render_tutorial_results.py --check` is part of the full check.
- Analysis starts with module/method selection. Global purpose and role guidance
  moved to reload-safe `/help`; selected-method help is closed by default and
  supports keyboard open/close, ESC, focus return, and ARIA state.
- Reload-safe `/reports` pages checksum-validated generic analysis results and
  reuses existing JSON/CSV/HTML create/list/download/delete APIs. Dedicated
  capability rows explicitly state unsupported HTML formats instead of using a
  generic fallback.
- Local development validation on the Windows 10/Python 3.10/Node 24 host:
  full check 836.0 seconds (backend 782, frontend 139, OpenAPI/frontend 155),
  tutorial smoke 18 sections in 19.7 seconds, and Chromium E2E in 77.3 seconds.
  Main is 532.53 kB / 127.56 kB gzip and retains the measured warning.
- Statistical calculations, method versions, persisted result schemas, and
  SQLite schema are unchanged. Remote Actions remain unverified because `gh`
  is unavailable; this is not Windows 11/Node 22 release evidence.

Next development order:

1. Clean Windows 11/Python 3.10/Node 22 release gate.
2. Remote Actions, required checks, and repository protection review.
3. Separately contracted Predict/RSM/Bayesian dedicated HTML reports.
4. Measured main-bundle optimization.
5. Source catalog performance, then dataset/DOE retention and advanced backlog.

## Progress Update 189 - Bayesian P0 Release Closure And Route Loading

- Published the bounded-continuous, single-objective, sequential P0 audit in
  `docs/bayesian_p0_release_checklist.md`; advanced Bayesian variants and objective automation
  remain explicit non-goals.
- Study/recommendation rendering now requires the current catalog Study ID, and catalog/restore
  loading participates in the common action lock. Direct hook tests cover stale restore,
  observation, close, recommendation, deletion-preflight, deletion, reset, and unmount paths.
- Help and Report Center now load through independent route chunks with accessible loading and
  sanitized failure states. Main decreased from 532.53 kB to 496.98 kB on the development host.
- The new production-transition benchmark builds 20/100/500 Study catalogs plus real medium and
  100-trial large graphs. It keeps full validation and records the measured follow-up boundary in
  `docs/bayesian_catalog_performance.md`.
- Full local development validation passed in 841.8 seconds with backend 784, frontend 152,
  OpenAPI/frontend 155, and 18 tutorial Markdown blocks. Tutorial smoke passed 18 sections in
  19.0 seconds and Chromium E2E passed in 78.0 seconds.
- The host is Windows 10 build 19045, Python 3.10.11, and Node 24.17.0. This is not the clean
  Windows 11/Node 22 release gate. Hosted Actions remain unverified because `gh` is unavailable.
- Bayesian method `0.2.2`, GP/Matérn/EI behavior, budgets, API/storage schemas, and SQLite schema
  14 are unchanged.

Next development order:

1. Clean Windows 11/Python 3.10/Node 22 release gate.
2. Remote Actions and required-check/branch-protection review with separate approval.
3. Separately contracted dedicated HTML reports.
4. Verified catalog summary/index and search with exact-selection full validation.
5. Dataset/DOE retention roots, then advanced quality/statistics.
