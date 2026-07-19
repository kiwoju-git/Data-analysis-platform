# DataLab Studio To-Do List

Last updated: 2026-07-19

## 1. Required Reading And Priority

Before any implementation PR, read these in order:

1. `AGENTS.md`
2. `docs/six_module_implementation_guide.md`
3. `to_do_list.md`
4. `data_prd_addendum.md`
5. `data_prd.md` if present
6. nearest nested `AGENTS.md` or `AGENTS.override.md` if present

Current source-of-truth note:

- `docs/six_module_implementation_guide.md` defines the 6-module product structure and Gate B0/B1/B2/C1/C2/C3/D1/D2/E order.
- `data_prd_addendum.md` remains authoritative for security, privacy, statistical correctness, reproducibility, Windows/Python 3.10, CPU-only, and local-only constraints.
- `to_do_list.md` tracks the current implementation state and the next allowed PR slice.

Current and next development order:

Predict/Response Optimizer entrypoints, tutorial truth sync, Help/Report Center,
Bayesian frontend modularization, catalog paging/deep-link restore, successor seed guidance, and
repository onboarding README are complete on pushed main through
`695caf2fcfb6a8336ddd29afc77d4ed22911dc63`. The current approved closure slice
adds Study-selection action isolation and direct lifecycle/recommendation/retention race tests,
route-level Help/Report loading, a bounded P0 release checklist, and measured 20/100/500-Study
catalog evidence. Bayesian math, request/result/storage schemas, SQLite schema 14, and method
`0.2.2` remain unchanged. After this slice:

1. Run the clean Windows 11 x64/Python 3.10/Node 22/CPU-only release gate.
2. Verify the resulting main push in remote GitHub Actions and review required Windows/E2E checks
   and repository protection outside this code PR.
3. Add separately contracted Predict/RSM/Optimizer/Bayesian dedicated HTML reports.
4. Specify a lightweight immutable catalog summary/index and search contract while retaining
   exact selected-Study full validation and a measured latency threshold.
5. Add dataset-root and then DOE-root retention only through separate reviewed ownership graphs
   with explicit inbound-reference blockers.
6. Continue the advanced quality/statistics backlog through a separately approved contract.

The current Phase II slice retains explicit target compatibility, P/NP/C/U
frozen formulas, dependency provenance, restore/export consistency, typed UI
selection, and browser E2E. Method `0.3.0`/result schema `3` permits one valid
monitoring point and records dispersion as unavailable rather than inventing a
numeric ratio. Phase I still requires two usable points and limit-set promotion
still requires 20. Any later chart expansion requires a separate approved
contract. Do not add WECO/Nelson rules, Laney correction, exact probability
limits, naked user-entered limits, automatic baseline refit, or a new chart
family, and never reinterpret stored `0.1.0` or `0.2.0` results.

## 2. Current Code State

Already implemented:

- FastAPI app factory, root route `GET /`, health route `GET /api/v1/health`
- Structured API errors with `correlation_id`
- Local-only default host `127.0.0.1` and narrow CORS
- React 18 + Vite + TypeScript shell with API health display
- PowerShell workflow scripts: `bootstrap.ps1`, `dev.ps1`, `test.ps1`, `check.ps1`
- SQLite migration skeleton through schema version `14`
- `datasets` metadata table for raw upload provenance
- `dataset_versions` metadata table for immutable parsing-confirmed versions
- `dataset_columns` metadata table preserving original names and unique display names
- `dataset_artifacts` metadata table for app-owned dataset artifact paths and hashes
- Atomic file write helper for small app-owned artifacts, with short temporary filename prefixes for deep Windows workspace paths
- `POST /api/v1/datasets` multipart upload
- `POST /api/v1/datasets/paste` for pasted spreadsheet text
- `POST /api/v1/datasets/{dataset_id}/confirm-parsing` for delimited text files and basic XLSX worksheets
- `GET /api/v1/datasets/{dataset_id}/versions`
- `GET /api/v1/dataset-versions/{version_id}`
- `GET /api/v1/dataset-versions/{version_id}/schema`
- `PATCH /api/v1/dataset-versions/{version_id}/schema`
- `GET /api/v1/dataset-versions/{version_id}/rows`
- `GET /api/v1/dataset-versions/{version_id}/profile`
- `GET /api/v1/analysis-methods`
- `POST /api/v1/analysis-runs` unavailable-method guard
- `GET /api/v1/analysis-runs/{analysis_id}`
- `DELETE /api/v1/analysis-runs/{analysis_id}`
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`
- CSV, TSV, TXT-as-delimited-text, XLSX envelope validation
- Clipboard/paste text intake stores raw pasted bytes with SHA-256 provenance and reuses parsing confirmation
- Upload size limit through `DATALAB_MAX_UPLOAD_BYTES`
- Sanitized filename handling and UUID-based raw workspace paths
- Raw upload preservation with SHA-256 and byte size metadata
- Confirm-parsing raw upload integrity recheck against stored SHA-256 and byte size before canonical artifact creation
- Parsing suggestions for encoding, delimiter, quote, decimal, thousands, header presence, header row, and data start row
- Explicit parsing confirmation records encoding, delimiter, quote, decimal/thousands, header presence, header row, data start row, missing tokens, and XLSX sheet name where applicable
- Delimited TXT files with leading preamble and no header can be confirmed with generated `column_1...column_n` names
- Default parsing-confirmation missing tokens include `N/T` for local no-test/not-tested style entries, while still remaining user-editable before confirmation
- Immutable dataset version `v1` creation for confirmed delimited text and basic XLSX uploads
- Streamed header and row-count scan for delimited text without browser full-data loading
- Dataset schema lookup/update for display name, measurement level, role, and unit
- Paginated canonical row preview with `limit <= 100`
- Canonical UTF-8 JSONL rows and JSON manifest materialization for confirmed delimited text and basic XLSX dataset versions
- Basic profile/preflight API with aggregate missing, unique-count, numeric, date/time, constant-column, possible-ID, non-numeric-in-numeric, non-datetime-in-datetime, duplicate-row, canonical-artifact, persisted profile-artifact, and memory-estimate warnings
- Minimal React UI for upload, parsing confirmation, dataset Context Bar, schema update, and row preview
- View-only React paste staging grid with exact raw-ref submission, raw/grid
  modes, capped cells, structural warnings, and no browser-storage persistence
- Minimal React UI for profile/preflight warnings, canonical/profile artifact summary, preflight summary, and column-level aggregate/numeric/date-time profile table
- Minimal React schema UI includes a guarded 34-column headerless Bayesian sample role preset: `column_1` as ID, `column_2`-`column_25` as X/features, and `column_26`-`column_34` as Y/responses
- App chrome rendering is split into `frontend/src/AppChrome.tsx`, while `App.tsx` keeps API bootstrap and analysis state ownership
- App routes include reload-safe dataset, analysis, Report Center (`/reports`),
  and Help Center (`/help`) pages. The analysis page starts with module/method
  selection and keeps global purpose/role guidance in Help Center; selected
  method guidance opens in an accessible context drawer.
- Report Center pages existing generic analysis-run JSON/CSV/HTML exports and
  explicitly marks unsupported dedicated HTML formats as unavailable.
- Dataset workflow state and handlers are split into `frontend/src/useDatasetWorkflow.ts`
- Dataset preparation rendering is split into `frontend/src/DatasetPreparationPage.tsx`, `frontend/src/DatasetParsingPanel.tsx`, `frontend/src/DatasetVersionPanel.tsx`, `frontend/src/DatasetProfileSection.tsx`, and `frontend/src/DatasetPreviewSection.tsx`, while `WorkspaceRouter` chooses the active dataset/analysis page
- Dataset formatting, labels, and profile summary helpers are centralized in `frontend/src/datasetDisplay.ts`
- Analysis method registry with 6 modules and 30 stable available method IDs:
  25 generic analysis-run methods and 5 dedicated workflow methods
- Common analysis request, filter snapshot, warning, provenance, and result envelope schemas
- Common analysis run status and job status schemas
- `analysis_runs`, `analysis_artifacts`, and `jobs` metadata tables
- `experiment_designs`, `experiment_design_versions`, `experiment_runs`, `experiment_run_responses`, `experiment_design_analyses`, immutable response revision/value/head, and analysis-revision relationship tables for DOE assets
- Analysis run and job status/cancel API skeletons
- Six-module planned/disabled navigation shell in the React UI
- Six-module selected-method Workbench shell in the React UI:
  - module and method selection comes from the backend catalog
  - selected module/method is restorable through `/analysis/{module_id}/{method_id}` with legacy hash fallback
  - route selection state is centralized in `frontend/src/analysisSelection.ts`
  - app page route parsing is centralized in `frontend/src/appRoute.ts`
  - workspace route boundary is split into `frontend/src/WorkspaceRouter.tsx`
  - analysis page boundary is split into `frontend/src/AnalysisPage.tsx`
  - common shell rendering is split into `frontend/src/AnalysisWorkbench.tsx`
  - analysis area rendering is further split into method panels, including dedicated `RegressionPredictionWorkspace`, `ResponseOptimizerWorkspace`, `FactorialDesignPanel`, `ResponseSurfacePanel`, and `ResponseOptimizerPanel`; the legacy `BayesianOptimizationPanel` export is a thin wrapper over `features/bayesian/BayesianOptimizationWorkspace`
  - Bayesian study builder/catalog/summary/trials/recommendation/close/deletion UI and draft/catalog/lifecycle/recommendation/retention state are separated under `frontend/src/features/bayesian`; each async concern has an independent latest-request guard
  - root/dataset routes render the dataset preparation page and `/analysis/{module_id}/{method_id}` routes render the analysis page
  - Regression, Quality, and DOE execution panels load through three module-level dynamic imports with accessible loading/error boundaries and transition-safe method selection
  - supported filter controls render through a common Workbench slot for dataset-backed methods
  - Workbench steps show data, roles, options, preflight, execution, and results
  - all 30 documented methods show UI guidance for required roles, options, preflight checks, and result focus
  - `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.attribute_control_chart`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart` expose analysis execution controls
  - `doe.factorial_design` exposes dedicated design, response-entry, effects/ANOVA, diagnostic, and report controls; it remains outside the generic analysis-run API
  - `regression.predict` and `regression.response_optimizer` expose top-level source catalogs and ID-only deep links while reusing the embedded prediction/optimizer components; both remain outside the generic analysis-run API
  - `doe.response_surface` exposes dedicated CCD design, response-entry, full-quadratic model, contour, stationary-point, diagnostic, and embedded bounded Response Optimizer controls
  - `doe.bayesian_optimization` exposes dedicated bounded study, manual observation, immutable history, and GP/EI recommendation controls; it remains outside the generic analysis-run API
- Analysis run API guard that directs dedicated methods to their typed APIs and rejects disabled methods without returning fake results
- `eda.descriptive` is the first executable method and computes real descriptive statistics from confirmed dataset versions
- `eda.graphical_summary` is the second executable method and computes real histogram, boxplot, Q-Q, and ECDF chart-data payloads from confirmed dataset versions, with frontend inline SVG rendering for histogram, box plot, Q-Q plot, and ECDF
- `eda.normality` is the third executable method and computes real SciPy-backed Shapiro-Wilk, Anderson-Darling, and Q-Q point payloads from confirmed dataset versions
- `eda.equal_variances` is the fourth executable method and computes real SciPy-backed Brown-Forsythe and Levene(mean) results from confirmed dataset versions
- `hypothesis.one_sample_t` is the first single-sample Gate B2 executable method and computes real SciPy-backed one-sample t-test results from confirmed dataset versions
- `hypothesis.paired_t` is the first paired-design Gate B2 executable method and computes real SciPy-backed paired t-test results from confirmed wide before/after measurement columns
- `hypothesis.one_sample_wilcoxon` is the first single-sample rank-based Gate B2 executable method and computes real SciPy-backed signed-rank results from confirmed dataset versions
- `hypothesis.two_sample_t` is the first two-group Gate B2 executable method and computes real SciPy-backed Welch-default or explicit pooled independent two-sample t-test results from confirmed dataset versions
- `hypothesis.mann_whitney` is the first rank-based Gate B2 executable method and computes real SciPy-backed Mann-Whitney U results from confirmed dataset versions
- `hypothesis.kruskal_wallis` is the first 3-or-more-group rank-based Gate B2 executable method and computes real SciPy-backed Kruskal-Wallis plus Dunn/Holm results from confirmed dataset versions
- `hypothesis.one_way_anova` is the first ANOVA Gate B2 executable method and computes real SciPy-backed standard one-way ANOVA plus Tukey-Kramer post-hoc results from confirmed dataset versions
- `hypothesis.equivalence_tost` is the first equivalence Gate B2 executable method and computes real SciPy-backed one-sample mean TOST results from one numeric response column, an explicit reference mean, and user-defined raw-unit equivalence bounds
- `categorical.one_proportion` is the first categorical Gate B2 executable method and computes real SciPy-backed exact binomial 1-proportion results from one binary response column plus an explicit event level on confirmed dataset versions
- `categorical.two_proportion` is the second categorical Gate B2 executable method and computes real SciPy-backed Fisher exact 2-proportion results from one binary response column, exactly two usable groups, and an explicit event level on confirmed dataset versions
- `categorical.chi_square_association` is the third categorical Gate B2 executable method and computes real SciPy-backed Pearson chi-square association results from two categorical columns on confirmed dataset versions
- `regression.pearson` is the first Gate C1 executable method and computes real SciPy-backed Pearson product-moment correlation results from two numeric columns on confirmed dataset versions
- `regression.xy_correlation` is the second Gate C1 executable method and computes real SciPy-backed pairwise Pearson X-Y correlation matrix results from numeric X/Y column sets on confirmed dataset versions
- `regression.linear_model` is the third Gate C1 executable method and computes real NumPy/SciPy-backed OLS linear model results from one numeric response and one or more numeric/categorical predictors on confirmed dataset versions, with safe JSON model manifest persistence, checksum-validated manifest retrieval, source-freshness-gated same/cross-dataset prediction, paged rows, full prediction CSV export, and frontend execution/result display
- `quality.gage_run_chart` is the second Gate C3 executable method and computes real stdlib measurement-system diagnostic chart payloads from balanced crossed Gage rows with raw part/operator/replicate label redaction
- `doe.factorial_design` is the Gate D1 2-level full factorial method at version `0.3.0`; analysis envelope/config schema 2 pins immutable response revision schema 1 in SQLite schema 10 while result calculation schema remains 1. Dedicated APIs provide current/history/correction, analysis restore, -1/+1 effects, hierarchy-fixed OLS/ANOVA, diagnostics, charts, and HTML report. Fractional alias analysis and optimization remain out of scope
- `doe.response_surface` is the Gate D2 CCD/full-quadratic method at version `0.2.0`; analysis envelope/config schema 2 pins immutable response revision schema 1, design payload schema 2 uses generic `central_composite` family plus `alpha_mode`, legacy schema-1 family/SHA restore is preserved, and analyzed revisions remain read-only while corrections create new revisions
- `regression.response_optimizer` is an available dedicated catalog method at version `0.3.0`; its top-level workspace selects checksum-validated stored RSM analyses while the existing embedded RSM entry remains available. Config/result schema 2 and source-bundle schema 2 are unchanged
- `doe.bayesian_optimization` is available through dedicated APIs/UI at version `0.2.2`; study/history and recommendation config/result/model schemas remain 1, lifecycle-event schema 1 and SQLite schema 14 add immutable close metadata and successor lineage, backend/UI enforce initial-design and 200/201 boundaries, stranded-study abandonment protection, all-trial duplicate exclusion, latest/current reconciliation, explicit trial budgets, terminal confirmations, typed time-budget errors, and read-only closed restore while preserving legacy `0.1.0` studies and valid `0.2.0`/`0.2.1` recommendations
- scikit-learn 1.7.2 is production-pinned after the isolated CPython 3.10 wheel-only, current NumPy/SciPy, offline, CPU/thread, and deterministic fixed-kernel GP checks; joblib 1.5.2/threadpoolctl 3.6.0 and the full Windows backend environment are protected by a 45-wheel SHA-256 lock. Windows 11 client validation remains a release gate
- NumPy 2.2.6/SciPy 1.15.3 are production-pinned after the native Windows Python 3.10.11 dependency spike, and a SciPy-backed normality reference fixture was generated and validated
- Descriptive statistics result persistence stores app-owned JSON under the workspace and records result SHA-256 in `analysis_runs`
- Available inline analysis runs persist an `analysis_row_snapshot` artifact with filter snapshot hash, source canonical artifact hash, included row counts, and row ranges for supported filters
- XLSX container checks, sheet-selection warning, and basic stdlib parsing confirmation for the first or named worksheet
- XLSX formula recalculation, merged-cell expansion, hidden row/column handling, and display-format/date serial restoration remain out of scope
- Synthetic upload tests, parsing confirmation tests, canonical artifact tests, and migration upgrade tests through schema version `13`, including deterministic legacy DOE response backfill, schema-11 Bayesian trial preservation, legacy `0.1.0` study restore, and schema-12-to-13 immutable attribute limit-set table creation
- Schema update validation tests and rows preview pagination/bounds tests
- Synthetic tests for preamble-plus-headerless delimited text upload, parsing confirmation, generated columns, and row preview
- Canonical row reader adoption tests proving profile and `eda.descriptive` read canonical rows after raw upload mutation
- Corrupt canonical artifact tests proving profile returns an explicit recovery error without raw fallback
- Profile artifact persistence tests proving profile scans write raw-value-free JSON artifacts, update `dataset_artifacts`, and do not echo raw values
- Date/time preflight tests proving profile reports parse counts, format candidates, timezone-aware/naive counts, and profile artifact payloads without raw value samples
- Data integrity/reproducibility hardening:
  - rows preview, profile, and `eda.descriptive` use the same canonical JSONL source after parsing confirmation
  - schema PATCH marks existing analysis runs for the same dataset version `stale=true`
  - stored `eda.descriptive` result envelopes are retrievable through checksum-validated `GET /api/v1/analysis-runs/{analysis_id}/result`
  - profile artifacts are reused only when schema hash and source canonical artifact hash still match
  - descriptive result files are removed if metadata insert fails after file write
- Regression model reproducibility hardening:
  - `regression.linear_model` writes a safe JSON `regression_model_manifest` artifact tied to dataset version, schema hash, canonical artifact hash, row snapshot hash, coefficients, fit summary, diagnostic summary, and package versions
  - `regression_models` SQLite metadata stores model ID, analysis ID, dataset version ID, schema hash, manifest path, and manifest SHA-256 for app-created regression models only
  - `GET /api/v1/regression-models/{model_id}` validates manifest path and SHA-256 before returning the manifest without exposing absolute paths
  - `POST /api/v1/regression-models/{model_id}/prediction-preflight` validates source analysis existence/method/version/freshness, fit/current source schema, model/manifest metadata and checksum, then validates target mapping, extrapolation, missing/non-numeric values, and unseen categorical levels
  - `POST /api/v1/regression-models/{model_id}/predictions` runs the same preflight path, rejects error-severity preflight failures, reconstructs the OLS design matrix from the stored manifest, returns capped predicted means plus mean-response confidence intervals and individual prediction intervals, and stores a checksum-validated `regression.predict` result envelope without raw cell values
  - all valid prediction rows are atomically stored in a checksum-recorded `regression_prediction_rows` NDJSON artifact; `GET /api/v1/regression-models/predictions/{prediction_id}/rows` validates the artifact and returns pages of up to 200 rows
  - the Linear Model UI retrieves 25-row pages through one grouped prediction-row state contract and invalidates stale page requests when the model or dataset version changes
  - `GET /api/v1/dataset-versions` returns a paged catalog of confirmed local versions without raw rows, storage paths, or hashes; the prediction UI defaults to the active version and can explicitly select another catalog version
  - target selection state is isolated in `useRegressionPredictionTargetState`; changing target invalidates preflight, prediction, and prediction-row requests/results before a new run
  - full stored prediction rows can be streamed into a checksum-recorded, raw-predictor-free wide CSV through `POST /api/v1/regression-models/predictions/{prediction_id}/exports/csv` and downloaded through the existing analysis export route
  - prediction provenance records source analysis/source dataset/target dataset/model dependencies plus shared runtime/build/package metadata without paths, filenames, or raw predictor values
  - restore, page, CSV, export-list, and download paths share result/config/rows/model relationship validation for IDs, method version, hashes, target/source linkage, and expected counts
  - `METHOD_VERSIONS` is the only prediction version source; `regression.predict` is `0.2.0`, prediction result/config/rows schemas are `2`/`3`/`2`, and CSV schema remains `1`
  - result, row snapshot, model manifest, and prediction result files are removed if metadata insert fails after file writes
- Filter snapshot row freezing:
  - `eda.descriptive` filter snapshots are frozen into `analysis_row_snapshot` artifacts
  - analysis provenance records filter snapshot hash, row snapshot hash, total row count, and included row count
  - supported non-empty filters select canonical row-index ranges before calculation
- Workbench-level frontend controls for supported filters:
  - users can add/remove AND filter conditions in the selected-method Workbench before running supported analyses
  - numeric columns expose `gt`/`gte`/`lt`/`lte`; all columns expose missing and equality conditions
  - filter drafts are validated in the shared UI slot
  - current executable payload serialization into `filter_snapshot.conditions` covers `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.attribute_control_chart`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart`
  - `quality.attribute_control_chart` v0.3.0/result schema 3 implements Phase I P/NP/C/U estimation plus Phase II frozen-limit monitoring from verified immutable limit-set assets; Phase II accepts one valid point with typed unavailable dispersion, preflight declares schema/dependency-only scope, execution revalidates rows, and old v0.1/schema-1 and v0.2/schema-2 results restore without rewriting
  - `quality.individuals_chart` uses canonical row order by default or an optional numeric/datetime order column sorted ascending with canonical row position tie-breaks, complete-case exclusions, arithmetic mean center line, `MRbar / d2` sigma estimate, I chart 3-sigma limits, MR chart `D3/D4` limits, I/MR single-point limit signals, I chart same-side centerline signals, I chart strict trend signals, I chart alternating signals, and explicit I chart zone/pattern signals
  - `quality.subgroup_chart` uses canonical first-seen subgroup order, fixed subgroup size 2-10, complete-case exclusions, Xbar-R/Xbar-S standard constants, Xbar/R/S control limits, and Xbar/R/S single-point limit signals
  - `quality.run_chart` uses canonical row order by default or an optional numeric/datetime order column sorted ascending with canonical row position tie-breaks, median center line, complete-case exclusions, above/below median run counts, tie-to-median exclusion policy, strict 6-point trend signal, strict 14-point oscillation signal, and exact conditional run-count clustering/mixture signals without control limits
  - `quality.capability` uses one numeric measurement column, LSL and/or USL, optional target, complete-case exclusions, overall sample SD, within `MRbar/d2` sigma, Cp/Cpk/Pp/Ppk side indices, observed/expected nonconformance, and histogram/fitted-normal/spec-line payloads
  - `quality.gage_rr` uses one numeric measurement column plus part/operator/replicate columns, complete-case exclusions, strict balanced crossed design validation, ANOVA table, raw/final variance components, % contribution, % study variation, ndc, and raw-label redaction
  - `quality.gage_run_chart` uses one numeric measurement column plus part/operator/replicate columns, optional numeric/datetime order, strict balanced crossed design validation, capped indexed chart points, part/operator summaries, and raw-label redaction
- Gate B2 first inferential slice:
  - `hypothesis.one_sample_t` validates an explicit response role and reference mean from schema metadata and request options
  - returns N/exclusion counts, sample summary, mean difference, confidence interval, t statistic, df, p-value, Cohen dz, Hedges-corrected effect, warning codes, and provenance
  - `hypothesis.paired_t` validates explicit before/after wide measurement columns from schema metadata and request options
  - records pair difference as `after - before`, complete-pair exclusion counts, before/after means, difference summary, confidence interval, t statistic, df, p-value, Cohen dz, Hedges-corrected effect, warning codes, and provenance
  - long format subject/condition/response paired data remains out of scope for the current paired t slice
  - `hypothesis.two_sample_t` validates explicit response and group roles from schema metadata and request options
  - Welch unequal-variance is the default; pooled Student t-test is available only through explicit `variance_assumption="pooled"`
  - returns N/exclusion counts, group summaries, mean difference, confidence interval, t statistic, df, p-value, Cohen's d, Hedges g, warning codes, and provenance
  - `hypothesis.mann_whitney` validates explicit response and group roles from schema metadata and request options
  - records exact/asymptotic p-value handling, rejects exact requests when ties are present, and never describes the result as a median-only test
  - returns N/exclusion counts, group rank summaries, U statistic, p-value, rank-biserial, common-language probability, warning codes, and provenance
  - `hypothesis.kruskal_wallis` validates explicit response and group roles from schema metadata and request options
  - requires at least three usable groups, records tie correction, and never describes the result as a median-only test
  - returns N/exclusion counts, group rank summaries, H statistic, df, p-value, epsilon-squared, optional Dunn/Holm comparisons after significant overall tests, warning codes, and provenance
  - `hypothesis.one_way_anova` validates explicit response and group roles from schema metadata and request options
  - supports standard one-way ANOVA only, computes ANOVA table, F statistic, p-value, eta squared, omega squared, and Tukey-Kramer post-hoc comparisons only after a significant omnibus test
  - Welch ANOVA, Games-Howell, repeated/two-way/ANCOVA, summary-statistic input, and automatic diagnostic-based method switching remain out of scope for this slice
  - `hypothesis.equivalence_tost` validates one explicit numeric response role, design `one_sample_mean`, explicit reference mean, alpha, complete-case missing handling, and user-defined lower/upper equivalence bounds from request options
  - computes lower/upper one-sided TOST p-values, TOST p-value, `1 - 2 * alpha` CI, Cohen dz, Hedges-corrected effect, warning codes, and provenance
  - paired mean-difference TOST, independent two-sample TOST, standardized-margin input, and automatic equivalence-bound suggestions remain out of scope for this slice
  - `categorical.one_proportion` validates one explicit binary response role, explicit `event_level`, `null_proportion`, alpha, confidence level, and CI method from request options
  - computes exact binomial p-values, Wilson or Clopper-Pearson CI, event/non-event counts, sample proportion, Cohen h, warning codes, and provenance
  - `categorical.two_proportion` validates one explicit binary response role, one explicit group role with exactly two usable groups, explicit `event_level`, alpha, confidence level, alternative, and complete-case missing handling
  - computes Fisher exact p-values, Newcombe-Wilson CI for the proportion difference, event/non-event counts by group, risk ratio and odds ratio where finite, warning codes, and provenance
  - `categorical.chi_square_association` validates two explicit non-ID categorical roles, alpha, and complete-case missing handling
  - computes Pearson chi-square p-values, expected-count diagnostics, observed/expected counts, standardized residuals, Cramer's V, warning codes, and provenance; sparse 2x2 tables record a Fisher exact recommendation without automatic fallback
  - `hypothesis.one_sample_wilcoxon` validates an explicit response role and reference location from schema metadata and request options
  - records exact/asymptotic p-value handling, `zero_method`, zero differences, ties, and symmetry/interpretation warnings
  - rejects exact requests when zero differences or absolute-difference ties are present and never describes the result as a median-only test without the symmetry caveat
  - returns N/exclusion counts, sample summary, signed-rank W statistic, p-value, signed-rank sums, rank-biserial, warning codes, and provenance
  - persists result JSON plus row snapshot provenance through the existing analysis run/result API

Not implemented yet:

- Full profile API beyond the current aggregate/duplicate/memory/date-time preflight slice
- Router-mounted Analysis Workbench page decomposition and additional shared feature components
- Binding the common filter UI state into future dataset-backed executable methods beyond the current twenty-five analysis-run methods
- Full XLSX workbook semantics beyond cached worksheet values
- Cell-level data editing or transformations that create a new immutable dataset version
- Executable generic analysis method dispatch beyond the current twenty-five analysis-run methods and the dedicated DOE/RSM/optimizer endpoints
- Any production statistical calculation beyond `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.attribute_control_chart`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart`
- Bayesian Optimization, fractional alias analysis, Box-Behnken, uncertainty-aware desirability, nonlinear/integer optimizer constraints, broader quality-control methods, or additional hypothesis/categorical calculations
- Any mock/fake statistical result

Strict rule:

- Do not add statistical calculation mock results, fake charts, fake tables, or placeholder numeric outputs.
- Unimplemented methods may be shown only as `planned` or `disabled`; they must not look executable or complete.

Near-term visualization plan:

- Current completed renderer: `eda.graphical_summary` renders backend-calculated histogram, box plot, Q-Q plot, and ECDF payloads as inline SVG without adding external chart dependencies.
- Next visualization candidates should reuse real result payloads only: `eda.normality` Q-Q plots, `regression.pearson` scatter plot plus confidence annotation, `regression.xy_correlation` matrix heatmap, `categorical.chi_square_association` observed/expected or residual heatmap, and `regression.linear_model` residual/fitted/leverage/Cook diagnostic charts.
- Do not create fake or decorative chart images. If a method does not yet return sufficient chart data, first add the real result payload and tests, then render it.
- Keep chart exports/artifact images, grouped/small-multiple graphical summary, KDE/density rendering, and high-volume canvas/WebGL rendering as later slices.

## 3. Historical Gate B0 Implementation Record

This section preserves the original Gate B0 implementation record. It is not
the current next-work source of truth; use the ordered list at the top of this
document.

Completed in this slice:

- Parsing confirmation request/response schema
- `POST /api/v1/datasets/{dataset_id}/confirm-parsing`
- Immutable `dataset_version` creation for delimited text uploads
- `dataset_columns` migration
- Dataset version 조회 API:
  - `GET /api/v1/datasets/{dataset_id}/versions`
  - `GET /api/v1/dataset-versions/{version_id}`
- Minimal UI path for uploaded dataset parsing confirmation and dataset version status
- Tests for migration, parsing confirmation, version creation, and minimal UI behavior
- Preamble-plus-headerless delimited text parsing support:
  - upload suggestion detects consistent tabular data after leading notes
  - confirmation supports `has_header=false` and `data_start_row`
  - generated column names preserve immutable schema without fabricating source headers
- Headerless Bayesian sample schema helper:
  - UI-only guarded preset for 34 generated columns
  - assigns first column as ID, B-Y as feature roles, Z-AH as response roles
  - treats E/F/W day columns as count measurement level
- Dataset schema lookup/update API and UI
- Paginated rows preview API and UI
- Dataset Context Bar using real dataset version metadata
- Basic profile/preflight API and UI:
  - `GET /api/v1/dataset-versions/{version_id}/profile`
  - streams confirmed delimited-text versions without returning raw value samples
  - reports missing rate, capped unique count, numeric parse summary, date/time parse summary, date/time format/timezone warnings, constants, possible identifiers, numeric parse warnings, duplicate rows, memory estimate, and canonical/profile artifact state
  - persists raw-value-free `profile_summary` JSON artifacts and upserts latest profile artifact metadata in `dataset_artifacts`
  - UI displays aggregate profile rows and preflight summary after version creation and schema save
- Tests for schema update validation and row pagination bounds
- Analysis method registry:
  - `GET /api/v1/analysis-methods`
  - 6 module IDs in the documented order
  - 30 stable method IDs with explicit `available`, `planned`, or `disabled`
- Common analysis request/result/warning/provenance schemas
- `POST /api/v1/analysis-runs` executes the current available methods and rejects planned/disabled methods without result payloads
- Minimal six-module navigation shell using the backend catalog
- Hash-restorable selected-method Workbench shell:
  - selected method details are shown for all 30 method IDs
  - method-specific guidance describes required roles, options, preflight checks, and result focus for all 30 method IDs
  - route selection state is centralized in `frontend/src/analysisSelection.ts`
  - page boundary rendering is split into `frontend/src/AnalysisPage.tsx`
  - common module, method, guidance, and status rendering is split into `frontend/src/AnalysisWorkbench.tsx`
  - analysis shell and executable panel rendering are split into `frontend/src/AnalysisShell.tsx`, `frontend/src/DescriptiveAnalysisPanel.tsx`, `frontend/src/GraphicalSummaryPanel.tsx`, `frontend/src/NormalityAnalysisPanel.tsx`, `frontend/src/EqualVariancesPanel.tsx`, `frontend/src/OneSampleTPanel.tsx`, `frontend/src/OneSampleWilcoxonPanel.tsx`, `frontend/src/TwoSampleTPanel.tsx`, `frontend/src/MannWhitneyPanel.tsx`, `frontend/src/KruskalWallisPanel.tsx`, `frontend/src/OneProportionPanel.tsx`, and `frontend/src/TwoProportionPanel.tsx`
  - planned/disabled methods show availability state without execution controls
  - `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.paired_t`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` are executable Workbench methods
- Dataset-preparation component split:
  - sidebar, topbar, and dataset context layout are split into `frontend/src/AppChrome.tsx`
  - dataset upload, pasted text, parsing confirmation, schema, preview, and profile workflow state/handlers are split into `frontend/src/useDatasetWorkflow.ts`
  - upload and pasted text intake are composed by `DatasetPreparationPage`,
    `PasteDatasetPanel`, `PastePreviewGrid`, and `usePastedDatasetDraft`
  - parsing confirmation is split into `frontend/src/DatasetParsingPanel.tsx`
  - dataset version context is split into `frontend/src/DatasetVersionPanel.tsx`
  - profile/preflight, schema, and preview rendering are split into `frontend/src/DatasetProfileSection.tsx`, `frontend/src/DatasetSchemaSection.tsx`, and `frontend/src/DatasetPreviewSection.tsx`
  - dataset display labels, byte/number/percent formatting, hash shortening, and profile/date-time summaries are split into `frontend/src/datasetDisplay.ts`
  - `App.tsx` still owns API bootstrap, route state, and analysis state to avoid behavior changes during the component split
- Route-selected page rendering:
  - `frontend/src/appRoute.ts` maps root/dataset URLs to the dataset page and `/analysis/{module_id}/{method_id}` URLs to the analysis page
  - `WorkspaceRouter` renders either `DatasetPreparationPage` or `AnalysisPage` for the current page route instead of showing both at once
  - `useAnalysisSelection` no longer rewrites the root/dataset route to the default analysis route when the method catalog loads
- Tests for method ID stability, disabled method behavior, and no mock results
- `eda.descriptive` first real method:
  - pure calculation module independent of FastAPI/UI
  - hand-checkable descriptive fixture and edge tests
  - API integration test through dataset version abstraction
  - minimal UI column selector and result table
  - result JSON persisted under workspace with SHA-256 in `analysis_runs`
- `eda.graphical_summary` second real method:
  - pure stdlib calculation module independent of FastAPI/UI
  - hand-checkable histogram, boxplot, Q-Q, ECDF fixture and edge tests
  - API integration test through dataset version abstraction
  - minimal UI column selector and result table
  - result JSON persisted under workspace with SHA-256 in `analysis_runs`
- `eda.normality` third real method:
  - SciPy-backed calculation module independent of FastAPI/UI
  - hand-checkable and generated SciPy reference fixture tests
  - API integration test through dataset version abstraction and canonical raw-mutation guard
  - minimal UI column selector, alpha input, warnings, and result table
  - result JSON persisted under workspace with SHA-256 in `analysis_runs`
  - grouped execution is explicitly rejected with `normality_grouping_not_supported`
- SQLite schema v4:
  - `analysis_runs`
  - `analysis_artifacts`
  - `jobs`
- SQLite schema v5:
  - `dataset_artifacts`
- SQLite schema v6:
  - `regression_models`
- SQLite schema v8:
  - `experiment_designs`
  - `experiment_design_versions`
  - `experiment_runs`
  - `experiment_run_responses`
- Analysis run status/cancel API skeleton:
  - `GET /api/v1/analysis-runs/{analysis_id}`
  - `DELETE /api/v1/analysis-runs/{analysis_id}`
- Job status/cancel API skeleton:
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`
- `POST /api/v1/doe-designs/factorial`
- `GET /api/v1/doe-designs/{design_id}`
- Tests for v3 to v4 migration, v4 to v5 migration, v5 to v6 migration, v6 to v7 migration, v7 to v8 migration, analysis/job/regression model metadata round trip, dataset artifact metadata round trip, DOE design/response metadata round trip, status lookup, cancellation request, and no fake results
- Canonical parsed artifact implementation:
  - UTF-8 JSONL rows and JSON manifest are written under the local workspace
  - artifact metadata stores relative paths, SHA-256, media type, and byte size in `dataset_artifacts`
  - profile response exposes canonical artifact metadata without returning raw values
- Canonical row reader adoption:
  - profile and `eda.descriptive` execution read validated canonical rows
  - canonical artifact path, media type, row index, row width, byte size, and SHA-256 are checked
  - corrupt or missing canonical artifacts return explicit recovery errors without raw fallback
- Persisted profile artifact implementation:
  - profile scans write raw-value-free `profile_summary` JSON under the local workspace
  - `dataset_artifacts` stores the latest profile artifact relative path, SHA-256, media type, byte size, and timestamp
  - profile responses and the React summary UI expose profile artifact hash/size metadata
  - atomic writes use short temporary filename prefixes to avoid Windows path-length failures in deep workspace paths
- Date/time preflight implementation:
  - profile schema version `4` adds column-level `datetime_profile`
  - reports date/time parse count, non-date/time count, min/max ISO values, format candidates, timezone-aware count, timezone-naive count, and mixed timezone status
  - warnings cover possible date/time columns, non-date/time values in datetime/time columns, mixed date/time formats, and mixed timezone awareness
  - frontend profile summary displays date/time aggregate info without raw value samples
- Data integrity/reproducibility hardening PR:
  - confirm-parsing streams the preserved raw upload and rejects SHA-256/size mismatch before canonical artifact or dataset version creation
  - rows preview reads canonical JSONL rows, matching profile and `eda.descriptive`
  - schema PATCH marks existing analysis runs stale in the same SQLite transaction as schema metadata updates
  - `GET /api/v1/analysis-runs/{analysis_id}/result` returns persisted result envelopes only after path and SHA-256 validation
  - profile artifact payloads include schema hash, profile schema version, and source canonical artifact hash, and matching artifacts are reused
  - descriptive result file writes compensate by deleting the file if `analysis_runs` insert fails
  - runtime workspaces, SQLite DBs, logs, exports, temp directories, and test caches are ignored by Git
- Filter snapshot row-freezing slice:
  - `analysis_runs.config_json` schema version `2` includes `filter_snapshot_sha256` and row snapshot metadata
  - `analysis_artifacts` records one `analysis_row_snapshot` artifact per succeeded inline `eda.descriptive` run
  - row snapshot files contain no raw cell values and link the executed row selection to the canonical artifact hash
- Non-empty filter expression slice:
  - supports conjunctions of `is_missing`, `is_not_missing`, `eq`, `ne`, and numeric `gt`/`gte`/`lt`/`lte` conditions
  - stores selected canonical rows as `row_ranges` in the row snapshot artifact
  - rejects unsupported operators, unknown columns, invalid values, and excessive condition counts before writing artifacts
- Canonical parsed artifact decision record:
  - Parquet remains candidate
  - `pyarrow_available=False` in current Windows Python 3.10 venv
  - no `pyarrow`, pickle, or joblib canonical data dependency added

The next implementation PR should remain narrow and must still avoid fake statistics.

Allowed next scope:

- Implement the next real executable method only after its statistical dependency, reference fixtures, warning metadata, and provenance contract are ready.
- Keep every method except the current twenty-four analysis-run methods and the dedicated `doe.factorial_design` design/response API unavailable until real code and tests exist.
- Keep analysis run status/job storage as infrastructure unless a later method requires worker execution.

Still explicitly out of scope:

- Statistical method calculations beyond the current twenty-four analysis-run methods
- Analysis mock results
- Full profile implementation beyond the current aggregate/duplicate/memory/date-time/profile-artifact preflight slice
- Router-mounted Analysis Workbench pages beyond the current path-restorable shared component shell
- Bayesian optimization, Response Optimizer, DOE effects/ANOVA analysis beyond the factorial design/response asset slices, broader quality-control methods, or additional hypothesis testing
- PyCaret, Optuna, SHAP, LIME, PyTorch, or GPU dependency

## 4. Gate Roadmap

### Gate B0: Analysis Platform Contract

Purpose:

- Build the shared dataset-version, schema, analysis-contract, navigation, and storage foundation required before any statistical method is implemented.

Implementation scope:

- Parsing confirmation from existing raw uploads
- Immutable dataset versions and column metadata
- Bounded row preview and dataset context
- Shared analysis method registry and result envelope
- Six-module navigation with unavailable methods clearly marked as planned
- Dependency compatibility spike for pandas/NumPy/SciPy/statsmodels/XLSX parsing before production adoption

Backend work:

- Add parsing confirmation API for uploaded datasets.
- Materialize immutable dataset version `v1` from confirmed parsing options.
- Add typed dataset version and dataset column response schemas.
- Add dataset version 조회 APIs.
- Add bounded row preview API after version creation.
- Add method registry skeleton only after dataset version APIs exist.
- Add common analysis request/result/warning/provenance contracts without fake results.
- Add analysis run, artifact, and job metadata contracts without executable analysis.
- Update stale `backend/README.md` to mention current dataset upload and version APIs.

Frontend work:

- Add minimal upload-result to parsing-confirmation flow.
- Show confirmed parsing options, dataset version ID, row/column counts, and schema status.
- Add dataset context bar based on real dataset version metadata.
- Show six module entries only when they can be marked as planned/disabled without mock results.
- Keep Korean UI default and machine-readable IDs in English.

DB/migration work:

- Advance SQLite schema from `2` to `3`.
- Add `dataset_versions`.
- Add `dataset_columns`.
- Advance SQLite schema from `3` to `4`.
- Add `analysis_runs`.
- Add `analysis_artifacts`.
- Add `jobs`.
- Advance SQLite schema from `4` to `5`.
- Add `dataset_artifacts`.
- Add only the minimum additional metadata needed for parsing confirmation.
- Include JSON fields only with explicit `schema_version`.
- Test upgrade from schema versions `1`, `2`, `3`, and `4`.

Tests:

- Migration upgrade through v5.
- UTF-8, UTF-8-SIG, CP949, Korean path/name, duplicate headers, empty header, and long filename fixtures.
- Parsing confirmation rejects unsupported or inconsistent options.
- Dataset version is immutable after creation.
- Dataset columns preserve original names and safe display names separately.
- Frontend smoke test for upload result to parsing confirmation UI.
- Assert no raw cell values appear in client errors or logs.

Completion criteria:

- Uploaded file can become immutable dataset version `v1`.
- Restarting the app can reopen the same dataset version metadata and schema hash.
- Dataset version 조회 APIs return stable typed responses.
- UI shows dataset version context without loading the entire dataset into browser state.
- Gate B0 does not introduce statistical calculations or mock results; the later Gate B1 `eda.descriptive` slice is the first real calculation.
- Relevant backend/frontend checks pass or skipped checks are explicitly justified.

Current status:

- First and second vertical slices are implemented in the working tree: safe upload, delimited-text parsing confirmation, immutable `dataset_version` v1, `dataset_columns`, version lookup APIs, schema update API/UI, paginated rows preview, and minimal Dataset Context Bar.
- The catalog/navigation part of the third vertical slice is implemented: analysis method registry, six-module planned/disabled navigation shell, common analysis request/result envelope, and unavailable-method API guard.
- The storage/run foundation slice is implemented: schema v4, persisted analysis run/artifact/job tables, status/cancel skeleton APIs, and no-result tests.
- The canonical/profile preflight slice is implemented: schema v5 `dataset_artifacts`, canonical JSONL rows/manifest materialization, duplicate-row count, memory estimate, and minimal UI summary.
- The canonical reader adoption slice is implemented: profile and `eda.descriptive` read validated canonical rows and reject corrupt artifacts without raw fallback.
- The persisted profile artifact slice is implemented: profile scans write raw-value-free `profile_summary` JSON artifacts and expose latest hash/size metadata.
- The date/time preflight slice is implemented: profile reports conservative format/timezone aggregate checks without coercing values.
- Still missing in Gate B0/B1 transition: router-mounted Analysis Workbench page decomposition, binding common filter state into additional executable methods, and additional reference-backed methods.
- Basic XLSX parsing confirmation is implemented with a stdlib ZIP/XML reader; full workbook semantics remain out of scope.

### Gate B1: Exploratory Analysis

Purpose:

- Implement the first real statistical module using the shared Gate B0 contracts.

Implementation scope:

- `eda.descriptive`
- `eda.graphical_summary`
- `eda.normality`
- `eda.equal_variances`
- Shared chart/table/result components

Backend work:

- Add method descriptors for the four exploration methods.
- Implement pure domain calculations independent of FastAPI and SQLite.
- Return N, missing counts, estimates, confidence intervals where applicable, assumptions, warnings, and provenance.
- Avoid dtype-only method decisions.

Frontend work:

- Add exploration module route and method picker.
- Add variable selection and preflight display.
- Render result tables, warnings, provenance, and charts from typed backend data.
- Keep unimplemented methods visibly planned/disabled.

DB/migration work:

- Add or finalize analysis run/artifact storage only as required by the common contract.
- Store large chart/table artifacts as workspace files with hashes, not SQLite blobs.

Tests:

- Hand-checkable descriptive fixture.
- Reference fixtures for normality/equal variance methods.
- Edge cases: empty column, constant column, all missing, non-finite values, small N.
- API and frontend smoke tests for one complete exploration method.

Completion criteria:

- Four exploration methods have reference, edge, API, and frontend coverage.
- Results include persistent warnings and provenance.
- No fake result or placeholder numeric output remains.

Current status:

- Completed for the current planned B1 set. `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, and `eda.equal_variances` are available with real calculations, persisted results, and minimal UI.
- `eda.normality` uses pinned NumPy 2.2.6/SciPy 1.15.3, generated SciPy reference fixtures, Shapiro-Wilk, Anderson-Darling, deterministic Q-Q point payloads, and a persistent no-automatic-method-switch warning.
- `eda.equal_variances` uses pinned NumPy 2.2.6/SciPy 1.15.3, reference fixtures, Brown-Forsythe, Levene(mean), group-level variance summaries, complete-case exclusion counts, persisted result envelopes, row snapshot provenance, and a persistent no-automatic-method-switch warning.

### Gate B2: Hypothesis And Categorical Analysis

Purpose:

- Implement core inferential tests with strict design metadata and transparent assumptions.

Implementation scope:

- 1-sample t, paired t, 2-sample t/Welch
- One-way ANOVA/Welch ANOVA with compatible post-hoc direction
- TOST equivalence test
- 1-sample Wilcoxon, Mann-Whitney U, Kruskal-Wallis
- 1-proportion, 2-proportion, chi-square association, Fisher exact where appropriate

Backend work:

- Add typed requests with explicit roles, measurement levels, alpha, alternative, missing policy, and multiplicity policy.
- Validate pairing keys and group structure before calculation.
- Use Holm as default suggested family-wise correction when multiple comparisons apply.
- Return effect sizes and 95% confidence intervals whenever supported.

Frontend work:

- Add hypothesis and categorical modules.
- Show design assumptions, N/exclusions, alpha, alternative, missing policy, and correction before execution.
- Emphasize estimate, CI, and effect size before p-value.

DB/migration work:

- Store analysis config snapshots and result artifact manifests through common analysis tables.
- Preserve raw and adjusted p-values.

Tests:

- Hand-checkable small fixtures.
- Independent reference fixtures with explicit tolerances.
- Failure tests for empty groups, constant variables, incomplete pairs, sparse cells, invalid equivalence bounds.
- Assertions for warnings and metadata, not only numeric values.

Completion criteria:

- Design misuse is blocked in preflight.
- Every inferential result includes N, exclusions, assumptions, warnings, CI/effect size where supported, and provenance.

Current status:

- Started. `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` are available as narrow B2 slices with real calculations, complete-case/complete-pair exclusion counts, p-value/effect size metadata, row snapshot provenance, persisted result retrieval, backend reference tests, API tests, and minimal frontend panels.
- Remaining B2 methods are still planned/disabled until each has real calculation code, reference fixtures, warning metadata, and UI/API coverage.

### Gate C1: Correlation, Regression, And Predict

Purpose:

- Implement correlation, safe regression modeling, diagnostics, model assets, and app-created regression prediction.

Implementation scope:

- Pearson correlation
- X-set by Y-set correlation matrix
- Safe OLS term builder
- Linear regression diagnostics
- Safe app-created model manifest
- Predict from app-created regression model

Backend work:

- Add safe formula/term builder without Python `eval`.
- Detect singular design matrices, non-finite values, zero variance, and extrapolation.
- Store regression model manifests with schema hash and provenance.
- Reject external pickle/joblib uploads.

Frontend work:

- Add regression module forms and diagnostics views.
- Warn on extrapolation and schema drift.
- Show prediction inputs and outputs without implying causation.

DB/migration work:

- Complete prediction-facing `regression_models` storage only after schema-drift and extrapolation checks are designed.
- Store model manifest and schema hash, not unsafe arbitrary deserialization payloads.

Tests:

- Reference correlation and OLS fixtures.
- Multicollinearity, singular matrix, non-finite, extrapolation, schema drift tests.
- Prediction reproducibility tests.

Completion criteria:

- Stored regression model predictions are reproducible only while the source
  analysis is fresh and its current schema still matches the fit-time schema.
- Model explanation text avoids causal claims.

Current status:

- Started. `regression.pearson` is available as the first narrow C1 slice with real SciPy-backed Pearson product-moment correlation, complete-case exclusion counts, covariance, r, r-squared, p-value, Fisher z CI, non-causation/linearity/outlier warnings, row snapshot provenance, persisted result retrieval, backend reference tests, API tests, and a minimal frontend panel.
- `regression.xy_correlation` is available as the second narrow C1 slice with real SciPy-backed pairwise Pearson X-Y correlation matrices, pair-level N/exclusions, covariance, r, r-squared, p-value, Fisher z CI, failed-cell error codes, row snapshot provenance, persisted result retrieval, backend reference tests, API tests, and a minimal frontend panel.
- `regression.linear_model` is available as the third narrow Gate C1 slice with real NumPy/SciPy-backed OLS for one numeric response and numeric/categorical main-effect predictors, selected numeric quadratic terms, selected numeric-by-numeric interactions, deterministic treatment coding for categorical factors, complete-case exclusions, coefficient SE/t/p/CI, R²/adjusted R², F test, VIF/condition diagnostics, residual/leverage/Cook's distance diagnostics, capped diagnostic points, row snapshot provenance, persisted result retrieval, safe JSON model manifest storage, checksum-validated manifest retrieval, prediction preflight for stored app-created manifests, backend prediction means/intervals from the stored manifest, backend reference tests, API tests, and a minimal frontend panel.
- Spearman/Kendall, adjusted p-values, scatterplot artifacts, categorical interactions, factor-by-numeric interactions, robust covariance, manual single-row prediction, response optimizer, and diagnostic chart artifacts remain planned/disabled until each has real calculation code, reference fixtures, warning metadata, and UI/API coverage.

### Gate C2: Basic Quality Control

Purpose:

- Implement basic SPC and capability tools while separating control limits from specification limits.

Implementation scope:

- Attribute P/NP/C/U charts
- I-MR chart
- X-bar/R and X-bar/S charts
- Run chart
- Normal capability analysis
- Common rule engine

Backend work:

- Validate order/timestamp/subgroup/sample size roles.
- Compute reference control limits and rule violations.
- Keep spec limits and control limits semantically separate.
- Return violation indices with non-color cues.

Frontend work:

- Add quality module forms.
- Render control charts with accessible violation labels.
- Show process assumptions and instability warnings persistently.

DB/migration work:

- Store chart result artifacts and rule-set metadata through common analysis artifact tables.

Tests:

- Reference control-limit fixtures.
- Rule violation index fixtures.
- Invalid subgroup and missing order tests.
- Capability tests for missing/invalid LSL/USL/target.

Completion criteria:

- Reference control limits and violation indices match tolerance.
- UI clearly separates specification limits from control limits.

Current status:

- Started. `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart` now provide real quality/measurement-system slices. `quality.subgroup_chart` is available as a fixed subgroup-size Xbar-R/Xbar-S slice with canonical row reader, persisted result JSON, Xbar/R/S control limits, single-point limit signals, varying subgroup-size rejection, zero-average-range/stddev rejection, backend unit/API tests, and a minimal inline SVG frontend panel with Xbar-R/Xbar-S selector. `quality.capability` is available as a normal capability first slice with LSL/USL/target inputs, Cp/Cpk/Pp/Ppk side indices, observed/expected nonconformance, histogram/fitted-normal/spec-line payload, backend unit/API tests, and minimal inline SVG frontend panel. `quality.gage_rr` is available as a balanced crossed ANOVA first slice with canonical row reader, persisted result JSON, ANOVA table, raw/final variance components, % contribution, % study variation, ndc, backend unit/API tests, and minimal frontend preflight/run/result table UI. `quality.gage_run_chart` is available as a balanced crossed diagnostic chart first slice with canonical row reader, optional order column, capped indexed point payload, part/operator summaries, raw-label redaction, backend unit/API tests, and minimal inline SVG frontend panel. Attribute charts, varying subgroup-size limits, non-normal capability, nested/unbalanced/expanded Gage R&R, full Nelson/Western Electric rules, component/interaction plots, and chart export artifacts remain planned until each has reference fixtures and UI/API coverage.

### Gate C3: Measurement System Analysis

Purpose:

- Implement balanced crossed Gage R&R calculation and Gage Run Chart with design validation.

Implementation scope:

- Balanced crossed Gage R&R
- Variance components
- NDC and contribution outputs where supported
- Gage Run Chart

Backend work:

- Validate part, operator, replicate, and response roles.
- Detect unbalanced, nested, missing cell, and non-numeric response cases.
- Return exact error or planned status for unsupported designs.

Frontend work:

- Add measurement-system forms under quality flow.
- Show design balance preflight and persistent warnings.
- Render Gage Run Chart with part/operator/replicate context.

DB/migration work:

- Use common analysis storage; no separate model artifact unless required.

Tests:

- Balanced crossed reference fixture.
- Unbalanced/nested rejection tests.
- Missing replicate and constant response edge cases.

Completion criteria:

- Reference variance components and NDC pass tolerance.
- Unsupported Gage designs are not silently coerced.

Current status:

- Started. Balanced crossed Gage R&R first slice is available through `quality.gage_rr`. It validates measurement, part, operator, and replicate roles; rejects unbalanced/missing-cell/duplicate-replicate/too-small/zero-total-variation cases with stable errors; returns ANOVA table, raw/final variance components, % contribution, % study variation, and ndc; and persists the result through the common analysis run/result API.
- `quality.gage_run_chart` is available as a separate diagnostic chart first slice. It validates the same balanced crossed role design, accepts an optional order column, returns capped indexed chart points plus part/operator summaries, redacts raw part/operator/replicate labels, and persists the result through the common analysis run/result API. Nested Gage R&R, unbalanced designs, tolerance/process variation, pooling choices, component/interaction plots, high-volume paged chart payloads, and chart export artifacts remain out of scope.
- Gate D1 DOE has started with design-asset and response-entry slices: `doe.factorial_design` is available through `POST /api/v1/doe-designs/factorial`, `GET /api/v1/doe-designs/{design_id}`, `PUT /api/v1/doe-designs/{design_id}/responses`, and `GET /api/v1/doe-designs/{design_id}/responses`. It creates a persisted 2-level full factorial design/run table with deterministic seed handling and `design_sha256`, then stores numeric response series against the immutable design version/run IDs. Effects, OLS/ANOVA, diagnostics, alias structure, and DOE charts remain out of scope.

### Gate D1: Factorial DOE

Purpose:

- Create immutable factorial design assets and analyze completed design responses.

Implementation scope:

- Done in first slice: 2-level full factorial design asset/version/run metadata
- Done in first slice: randomization, block, replicate, center-point metadata
- Done in first slice: deterministic run order from explicit seed and design SHA-256
- Done in first slice: dedicated create/read API and minimal Workbench preview
- Done in second slice: response import/storage API and minimal response-entry UI
- Remaining: effects, OLS, ANOVA, diagnostics

Backend work:

- Done: generate deterministic design/run order from explicit seed.
- Done: persist design, version, and run metadata in schema v7.
- Done: persist numeric run response metadata in schema v8 without mutating design run order.
- Done: checksum-verify stored design metadata before returning it.
- Done: preserve design after response entry by storing response rows separately from factor/run metadata.
- Add design analysis only after response data is present and validated.

Frontend work:

- Done: add DOE design creation flow for factors, randomization seed, block, replicate, and center points.
- Done: show factor settings, randomization seed, run order, and design SHA summary.
- Done: add response name/unit/value entry table keyed by run order and save status.
- Prevent accidental rerandomization after responses are recorded.

DB/migration work:

- Done: add `experiment_designs`, `experiment_design_versions`, and `experiment_runs`.
- Done: store factor definitions and run order as versioned design assets.
- Done: add `experiment_run_responses` for response metadata by design version/run ID.

Tests:

- Done: same seed produces same run order.
- Done: metadata migration v6 to v7, v7 to v8, and DOE design/response record round trip.
- Done: create/read API, duplicate factor rejection, response save/read, and incomplete response run-set rejection.
- Done: design immutability after response entry at the factor/run metadata level.
- Reference effect and ANOVA fixtures.

Completion criteria:

- Factorial design creation and analysis are reproducible and auditable.

Current status:

- Complete for the current 2-level full-factorial design, response, effects,
  OLS/ANOVA, diagnostics, persistence, report, and UI slice. Fractional alias
  analysis remains a later extension.

### Gate D2: RSM And Optimization

Purpose:

- Implement response surface design/modeling and bounded response optimization.

Implementation scope:

- Central composite design
- Quadratic response surface model
- Contour/surface chart data
- Response optimizer
- Box-Behnken as P1 candidate

Backend work:

- Validate factor ranges and design region.
- Fit quadratic models with diagnostics and warnings.
- Optimize only within declared design region and constraints.
- Record optimizer parameters, seed if applicable, and package versions.

Frontend work:

- Add RSM design and contour/surface result views.
- Show design-region limits and optimizer constraints.
- Avoid presenting optimization as Bayesian or causal unless explicitly implemented and validated later.

DB/migration work:

- Extend DOE design/model artifacts only as required.
- Store optimizer result manifests with hashes and constraints.

Tests:

- Known quadratic surface optimum fixtures.
- Boundary optimum tests.
- Invalid constraints and extrapolation tests.

Completion criteria:

- Optimizer respects design region and reproduces known reference surfaces.

Current status:

- Partially complete: CCD generation, full quadratic modeling, contour payload,
  stationary-point/design-region checks, persistence, reference tests, and UI
  are implemented. Bounded response optimization and Box-Behnken remain.

### Gate E: Deferred ML And Advanced Statistics

Purpose:

- Add advanced ML/statistical features only after Gates B-D are stable.

Implementation scope:

- General classification/regression ML
- AutoML/tuning
- SHAP/LIME
- Advanced ANOVA/mixed models
- Non-normal capability
- Extended Gage/DOE
- Bayesian adaptive experimentation only with separate design, validation, and threat model

Backend work:

- Use sklearn `Pipeline`/`ColumnTransformer` for ML.
- Split before any learned preprocessing.
- Keep holdout/nested CV discipline.
- Add explicit time, memory, trial, and failure budgets.

Frontend work:

- Show leakage warnings, model cards, evaluation limits, and non-causal explanation warnings.
- Keep optional heavy features out of the base workflow unless approved.

DB/migration work:

- Store safe app-created artifacts only with manifest version and hash.
- Reject untrusted external pickle/joblib uploads.

Tests:

- Leakage-prevention tests.
- Holdout/nested CV reproducibility tests.
- Schema drift and unseen category tests.
- Optional dependency compatibility/license review tests where applicable.

Completion criteria:

- Gate E does not weaken B-D quality gates.
- No heavy optional dependency enters the base install without approval.

Current status:

- Not started.

## 5. Validation Policy

For code implementation PRs:

- Run narrow backend/frontend checks first.
- Run `scripts/check.ps1` or the documented equivalent before completion.
- Report every command actually run and any command that could not run.

Current Gate B0 implementation validation notes:

- Windows Node `v24.17.0` is active in PowerShell.
- `npm --prefix .\frontend ci` was rerun in PowerShell and reported 0 vulnerabilities.
- `scripts/check.ps1` passed end-to-end after the shared Workbench component split.
- Backend ruff check, ruff format check, mypy, and 48 pytest tests passed through `scripts/check.ps1`.
- Frontend lint, typecheck, 6 Vitest tests, and build passed through `scripts/check.ps1`.

## 6. PR Description Draft For Gate B0 Second Slice

Summary:

- Added Gate B0 second vertical slice: dataset schema lookup/update API, paginated rows preview API, dataset Context Bar, and frontend schema/preview UI.
- Kept dataset raw bytes, original column names, data types, and source SHA immutable; schema update changes only display name, measurement level, role, unit, and schema hash.
- Added tests for schema update validation, duplicate display names, unknown column updates, rows preview pagination, missing-token display, and `limit <= 100`.
- Revalidated full Windows PowerShell check after moving to Node 24.

Changed files:

- Backend API/schema/service/storage/tests
- Frontend API client/App/UI test/styles
- `scripts/check.ps1`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/setup.md`
- `docs/progress_gate_b.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md`
- nearest nested instruction file

Next PR:

- This second-slice follow-up has been partially implemented by the Gate B0 third slice: analysis method registry, six-module planned/disabled navigation shell, and common analysis request/result envelope are present.
- The storage/run foundation follow-up is tracked in section 8 and has been implemented in the working tree.

Validation:

- `npm --prefix .\frontend ci`: passed, 0 vulnerabilities.
- `scripts/check.ps1`: passed end-to-end.

Known limitations:

- No statistical method calculation or mock result is introduced.
- Superseded by the basic XLSX parsing-confirmation slice: XLSX cached worksheet values can now be confirmed into canonical JSONL rows.
- Full profile beyond the current aggregate/duplicate/memory/profile-artifact preflight slice is not implemented yet.

## 7. PR Description Draft For Gate B0 Third Slice

Summary:

- Added Gate B0 analysis method registry with the documented 6 modules and 29 stable method IDs.
- Added `GET /api/v1/analysis-methods` and a guarded `POST /api/v1/analysis-runs` that rejects every planned/disabled method without returning a fake result.
- Added common analysis request, filter snapshot, warning, provenance, and result envelope schemas.
- Added frontend catalog fetch and six-module planned/disabled navigation shell with no execute controls and no statistical result display.
- Added backend and frontend tests covering method ID stability, unavailable-method behavior, no mock output, and shell rendering.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/api/v1/analysis_methods.py`
- `backend/app/api/v1/analysis_runs.py`
- `backend/app/api/v1/schemas/analyses.py`
- `backend/app/main.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `backend/README.md`
- `docs/progress_gate_b.md`
- `docs/linear_model_method_contract.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Superseded by section 8 and the first Gate B1 slice: storage/run foundation and `eda.descriptive` are implemented in the working tree.
- Keep every method except `eda.descriptive` non-executable until a reference-backed calculation slice starts.

Validation:

- Targeted backend API contract pytest: passed.
- Backend ruff check: passed.
- Backend mypy: passed.
- Frontend lint/typecheck/Vitest: passed in PowerShell.
- Full `scripts/check.ps1`: passed after final code changes; only smoke-result documentation notes were added afterward.
- Manual HTTP smoke: backend health ready, 6 modules/29 methods, planned analysis run rejected with 409, frontend dev server returned 200.
- Browser automation smoke: skipped because Playwright is not installed; no new dependency was added.

Known limitations:

- No statistical method calculation, fake chart, fake table, mock p-value, or mock result is introduced.
- Canonical parsed artifact materialization was not part of this older slice; it is now tracked as implemented in section 9.
- Analysis run, artifact, and job persistence is implemented as metadata infrastructure only.
- Frontend navigation is still a shell; selected analyses now have path-level restore and a page boundary, but the Workbench has not been mounted as a separate routed page.

## 8. PR Description Draft For Gate B0 Storage/Run Foundation

Summary:

- Advanced SQLite metadata schema to version `4`.
- Added `analysis_runs`, `analysis_artifacts`, and `jobs` tables with status, artifact hash/path, progress, cancellation, and timestamp fields.
- Added storage helpers for analysis run, artifact, and job metadata without storing raw data or result blobs in SQLite.
- Added `GET/DELETE /api/v1/analysis-runs/{analysis_id}` and `GET/DELETE /api/v1/jobs/{job_id}` status/cancel skeletons.
- Kept `POST /api/v1/analysis-runs` non-executable for every planned/disabled method.
- Recorded canonical parsed artifact decision: Parquet remains candidate, `pyarrow` is not currently installed/reviewed, and pickle/joblib remain prohibited.

Changed files:

- `backend/app/storage/metadata.py`
- `backend/app/api/v1/analysis_runs.py`
- `backend/app/api/v1/jobs.py`
- `backend/app/api/v1/schemas/analyses.py`
- `backend/app/api/v1/schemas/common.py`
- `backend/app/main.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/services/jobs.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_metadata_store.py`
- `backend/README.md`
- `docs/storage.md`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Superseded by the first Gate B1 slice: `eda.descriptive` is implemented through the dataset-version abstraction.
- Do not make any additional planned method executable without real calculation code, reference tests, provenance, warnings, and no-mock API/UI behavior.

Validation:

- Targeted metadata/API contract pytest: passed.
- Backend ruff check: passed.
- Backend mypy: passed.
- Full `scripts/check.ps1`: passed; backend pytest 42 tests, frontend lint/typecheck/Vitest/build passed.
- Manual HTTP smoke: backend health ready, 6 modules/29 methods, planned analysis run rejected with 409, missing analysis/job status returned 404, frontend dev server returned 200.

Known limitations:

- This storage/run slice introduced no statistical method calculation, fake chart, fake table, mock p-value, or mock result.
- Canonical parsed artifact materialization is now implemented by the later section 9 slice.
- Job cancellation is a persisted request state only; no worker process exists yet.
- Analysis artifact rows are metadata only; no result generator writes artifacts yet.

## 9. PR Description Draft For Canonical/Profile Preflight Slice

Summary:

- Advanced SQLite metadata schema to version `5`.
- Added `dataset_artifacts` metadata for app-owned dataset artifact relative paths, SHA-256 hashes, media type, byte size, and timestamps.
- Materialized confirmed delimited-text dataset versions as canonical UTF-8 JSONL rows plus JSON manifest under the local workspace.
- Added canonical artifact metadata to dataset version/profile responses.
- Added profile preflight fields for estimated memory bytes, duplicate row count, duplicate row check cap, and cap status.
- Added minimal frontend display for canonical artifact hash/size, memory estimate, and duplicate row count.
- Kept every method except `eda.descriptive` non-executable and added no mock statistics.

Changed files:

- `backend/app/storage/metadata.py`
- `backend/app/api/v1/schemas/datasets.py`
- `backend/app/services/canonical_artifacts.py`
- `backend/app/services/dataset_rows.py`
- `backend/app/services/dataset_versions.py`
- `backend/app/services/dataset_profiles.py`
- `backend/tests/unit/test_dataset_upload.py`
- `backend/tests/unit/test_metadata_store.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `backend/README.md`
- `docs/storage.md`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Superseded by section 11: profile artifacts with hashes are implemented.
- Superseded by section 12: richer date/time preflight is implemented.
- Next narrow slice should move the split Workbench into router-mounted page components or bind the common filter state into the next real executable method.
- Keep additional executable filter binding and deeper Workbench decomposition as separate narrow slices unless one is explicitly selected.
- Do not add Parquet/`pyarrow` until dependency review is complete.

Validation:

- Targeted backend pytest for dataset upload/profile plus metadata: passed, 28 tests.
- Backend ruff check: passed.
- Backend mypy: passed, 34 source files.
- Frontend typecheck: passed.
- Frontend lint: passed.
- Full `scripts/check.ps1`: passed; backend pytest 51 tests, frontend lint/typecheck/Vitest 6 tests/build passed.

Known limitations:

- JSONL canonical rows are a stdlib local format; Parquet remains a future candidate after `pyarrow` review.
- Profile artifacts are now persisted by the later section 11 slice.
- Superseded by the basic XLSX parsing-confirmation slice: XLSX cached worksheet values can now be confirmed into canonical JSONL rows.

## 10. PR Description Draft For Canonical Reader Adoption Slice

Summary:

- Split raw delimited text row parsing into `backend/app/services/row_readers.py` for canonical materialization.
- Switched `iter_dataset_rows()` to read validated `canonical_rows` artifacts instead of reparsing the raw upload.
- Validates canonical artifact kind, media type, relative path, file existence, row index sequence, row width, byte size, and SHA-256 before profile/analysis can complete.
- Added tests proving profile and `eda.descriptive` keep using canonical values after the raw upload is mutated.
- Added a corrupt canonical artifact test proving profile returns an explicit recovery error without leaking raw values or falling back to raw upload.
- Kept rows preview as bounded raw-upload preview and added no mock statistics.

Changed files:

- `backend/app/services/row_readers.py`
- `backend/app/services/canonical_artifacts.py`
- `backend/app/services/dataset_rows.py`
- `backend/tests/unit/test_dataset_upload.py`
- `backend/tests/unit/test_api_contracts.py`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Superseded by section 11: profile result artifacts with hash metadata are implemented.
- Superseded by section 12: richer date/time preflight is implemented.
- Next narrow slice should bind the common filter state into the next real executable method or move Workbench into router-mounted page components.
- Keep additional executable filter binding and deeper Workbench decomposition as separate narrow slices.
- Do not add Parquet/`pyarrow` until dependency review is complete.

Validation:

- Targeted backend pytest for dataset upload/profile plus API contracts: passed, 35 tests.
- Backend ruff check: passed.
- Backend mypy: passed, 35 source files.
- Full `scripts/check.ps1`: passed; backend pytest 53 tests, frontend lint/typecheck/Vitest 6 tests/build passed.

Known limitations:

- Superseded by data integrity/reproducibility hardening: rows preview now reads canonical JSONL rows.
- Profile artifacts are now persisted by the later section 11 slice.
- JSONL canonical rows are a stdlib local format; Parquet remains a future candidate after `pyarrow` review.

## 11. PR Description Draft For Persisted Profile Artifact Slice

Summary:

- Added persisted `profile_summary` dataset artifacts for `GET /api/v1/dataset-versions/{version_id}/profile`.
- Profile artifact payloads contain aggregate profile/preflight data and metadata only; raw cell values and value samples remain excluded.
- Added `profile_artifact` metadata to the profile API response and frontend profile summary.
- Added `upsert_dataset_artifact_record()` so repeated profile scans replace the latest `profile_summary` metadata for a dataset version.
- Shortened profile artifact paths to avoid Windows path-length failures in deep workspace directories while using the existing short-prefix atomic writer.
- Kept every method except `eda.descriptive` non-executable and added no mock statistics.

Changed files:

- `backend/app/storage/metadata.py`
- `backend/app/api/v1/schemas/datasets.py`
- `backend/app/services/dataset_profiles.py`
- `backend/tests/unit/test_dataset_upload.py`
- `backend/tests/unit/test_metadata_store.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Superseded by section 12: richer date/time preflight is implemented.
- Next narrow slice should move the shared Workbench into router-mounted analysis pages or bind common filter state into the next real executable method.
- Keep additional executable filter binding as a separate narrow slice unless the selected next slice needs it.
- Do not add Parquet/`pyarrow` until dependency review is complete.
- Do not make planned methods executable without real calculation code, reference tests, provenance, and no-mock API/UI behavior.

Validation:

- Targeted backend pytest for dataset upload/profile plus metadata: passed, 32 tests.
- Backend API contract pytest: passed, 13 tests.
- Backend ruff check: passed.
- Backend mypy: passed, 35 source files.
- Frontend typecheck: passed.
- Frontend lint: passed.
- Full `scripts/check.ps1`: passed; backend pytest 55 tests, frontend lint/typecheck/Vitest 6 tests/build passed.

Known limitations:

- Profile artifacts store the latest aggregate profile result; date/time preflight is now implemented by the later section 12 slice.
- Superseded by data integrity/reproducibility hardening: rows preview now reads canonical JSONL rows.
- JSONL canonical rows are a stdlib local format; Parquet remains a future candidate after `pyarrow` review.

## 12. PR Description Draft For Date/Time Profile Preflight Slice

Summary:

- Added column-level `datetime_profile` to `GET /api/v1/dataset-versions/{version_id}/profile` and bumped `profile_schema_version` to `4`.
- Reports date/time parse counts, non-date/time counts, ISO min/max, format candidates, timezone-aware counts, timezone-naive counts, and mixed timezone status.
- Added warnings for possible date/time columns, non-date/time values in datetime/time columns, mixed date/time formats, and mixed timezone awareness.
- Kept date/time detection as conservative preflight only; it does not coerce cell values, infer study design, or create dataset transformations.
- Persisted profile artifacts include the new date/time profile fields without raw value samples.
- Updated the React profile table summary to display date/time aggregate information next to numeric summaries.
- Kept every method except `eda.descriptive` non-executable and added no mock statistics.

Changed files:

- `backend/app/api/v1/schemas/datasets.py`
- `backend/app/services/dataset_profiles.py`
- `backend/tests/unit/test_dataset_upload.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `backend/README.md`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Move the split Workbench into router-mounted analysis pages, or bind common filter state into the next real executable method.
- Keep cell editing/transformation versioning as a separate slice unless explicitly selected.
- Do not add Parquet/`pyarrow` until dependency review is complete.
- Do not make planned methods executable without real calculation code, reference tests, provenance, and no-mock API/UI behavior.

Validation:

- Targeted backend pytest for dataset upload/profile: passed, 24 tests.
- Backend API contract pytest: passed, 13 tests.
- Backend ruff check: passed.
- Backend mypy: passed, 35 source files.
- Frontend typecheck: passed.
- Frontend lint: passed.
- Full `scripts/check.ps1`: passed; backend pytest 56 tests, frontend lint/typecheck/Vitest 6 tests/build passed.

Known limitations:

- Date/time detection is a preflight summary only; it does not perform confirmed type conversion or timezone normalization.
- Superseded by data integrity/reproducibility hardening: rows preview now reads canonical JSONL rows.
- JSONL canonical rows are a stdlib local format; Parquet remains a future candidate after `pyarrow` review.

## 13. PR Description Draft For Workbench-Level Filter UI Slice

Summary:

- Moved supported analysis filter controls out of the `eda.descriptive` execution panel and into a common `AnalysisWorkbench` render slot for dataset-backed methods.
- Kept `eda.descriptive` as the only executable method and the only method that serializes filter drafts into `filter_snapshot.conditions`.
- Added a frontend test assertion that the shared Workbench renders the common filter slot while planned methods remain non-executable.
- Added `*.tsbuildinfo` to `.gitignore` so TypeScript incremental build metadata does not enter Git.
- Added no new statistical method, no fake result, and no new backend API.

Changed files:

- `.gitignore`
- `frontend/src/AnalysisWorkbench.tsx`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Move the split Workbench into router-mounted analysis pages, or implement the next reference-backed method and bind the common filter state into that real calculation.
- Keep every method except `eda.descriptive` unavailable until calculation code, reference tests, provenance, and no-mock API/UI behavior exist.
- Do not add Bayesian optimization, DOE, regression, quality control, inferential tests, or chart rendering as part of this UI-only slice.

Validation:

- `git diff --check`: passed.
- `npm --prefix ./frontend run typecheck`: passed under WSL Node 24.14.0.
- `npm --prefix ./frontend run lint`: passed under WSL Node 24.14.0.
- `npm --prefix ./frontend run test -- --run`: passed with 13 Vitest tests under WSL Node 24.14.0 after restoring missing Linux native optional bindings in the local mixed Windows/WSL `node_modules`.
- `npm --prefix ./frontend run build`: passed under WSL Node 24.14.0 after restoring missing Linux native optional bindings in the local mixed Windows/WSL `node_modules`.
- Windows PowerShell validation and full `scripts/check.ps1`: not run in this session because `powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion"` still fails from WSL before command execution with a WSL socket/vsock error.

Known limitations:

- The common filter UI state is bound to executable analysis requests for `eda.descriptive` and `eda.graphical_summary`.
- Planned/disabled methods remain non-executable and must not return mock results.

## 14. PR Description Draft For Frontend Component Split

Summary:

- Split the dataset preparation UI out of `App.tsx` into `frontend/src/DatasetPreparationPage.tsx`.
- Split parsing confirmation, dataset version summary, profile/preflight, schema, and preview rendering into dedicated dataset-preparation components.
- Moved dataset display labels, hash/byte/number formatting, and profile/date-time summary helpers into `frontend/src/datasetDisplay.ts`.
- Split the analysis area out of `App.tsx` into `frontend/src/AnalysisShell.tsx`.
- Added `frontend/src/AnalysisPage.tsx` as the analysis page boundary for the current single-screen app.
- Split the first executable `eda.descriptive` panel into `frontend/src/DescriptiveAnalysisPanel.tsx`.
- Moved route selection parsing, catalog validation, popstate/hashchange handling, and route replacement into `frontend/src/analysisSelection.ts`.
- Added `frontend/src/appRoute.ts` so root/dataset URLs render the dataset preparation page and `/analysis/{module_id}/{method_id}` URLs render the analysis page.
- Added `frontend/src/WorkspaceRouter.tsx` so `App.tsx` delegates dataset-vs-analysis page rendering while keeping state/API ownership.
- Added `frontend/src/AppChrome.tsx` so `App.tsx` delegates sidebar, topbar, and dataset context layout while keeping state/API ownership.
- Added `frontend/src/useDatasetWorkflow.ts` so `App.tsx` delegates dataset upload/paste/parsing/schema/preview/profile workflow state and handlers while keeping analysis orchestration.
- Prevented catalog loading from automatically replacing the root/dataset route with the default analysis route.
- Kept analysis state ownership and API bootstrap in `App.tsx` to avoid changing behavior while reducing rendering boundaries.
- Added frontend SSR/pure tests for `AppChrome`, `DatasetPreparationPage`, `WorkspaceRouter`, `AnalysisPage`, catalog-backed route selection resolution, dataset workflow parsing helpers, the common filter UI, and the `eda.descriptive` execution panel.
- Added no backend API, no statistical calculation, no fake result, and no execution path for planned/disabled methods.

Changed files:

- `frontend/src/DatasetPreparationPage.tsx`
- `frontend/src/DatasetParsingPanel.tsx`
- `frontend/src/DatasetVersionPanel.tsx`
- `frontend/src/DatasetProfileSection.tsx`
- `frontend/src/DatasetSchemaSection.tsx`
- `frontend/src/DatasetPreviewSection.tsx`
- `frontend/src/datasetPreparationTypes.ts`
- `frontend/src/datasetDisplay.ts`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/AnalysisPage.tsx`
- `frontend/src/DescriptiveAnalysisPanel.tsx`
- `frontend/src/WorkspaceRouter.tsx`
- `frontend/src/AppChrome.tsx`
- `frontend/src/useDatasetWorkflow.ts`
- `frontend/src/analysisSelection.ts`
- `frontend/src/appRoute.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Continue small component decomposition only where behavior stays stable, or implement the next reference-backed method and bind the common filter state into that real calculation.
- Keep every method except `eda.descriptive` unavailable until calculation code, reference tests, provenance, and no-mock API/UI behavior exist.
- Do not add Bayesian optimization, DOE, regression, quality control, inferential tests, or chart rendering as part of this component-split slice.

Validation:

- `git diff --check`: passed.
- `npm --prefix ./frontend run typecheck`: passed under WSL Node 24.14.0.
- `npm --prefix ./frontend run lint`: passed under WSL Node 24.14.0.
- `npm --prefix ./frontend run test -- --run`: passed with 15 Vitest tests under WSL Node 24.14.0 after restoring missing Linux native optional bindings in the local mixed Windows/WSL `node_modules`.
- `npm --prefix ./frontend run build`: passed under WSL Node 24.14.0 after restoring missing Linux native optional bindings in the local mixed Windows/WSL `node_modules`.
- Windows PowerShell validation and full `scripts/check.ps1`: not run in this session because `powershell.exe -NoProfile -Command "$PSVersionTable.PSVersion"` still fails from WSL before command execution with a WSL socket/vsock error.

Known limitations:

- This is a component-boundary split and route-selection cleanup, not a full router-mounted page implementation or a data editing implementation.
- The common filter UI state is still bound to an executable analysis request only for `eda.descriptive`.
- Planned/disabled methods remain non-executable and must not return mock results.

## 15. PR Description Draft For Graphical Summary Calculation Slice

Summary:

- Added `eda.graphical_summary` as the second real executable method after `eda.descriptive`.
- Implemented stdlib-backed histogram, boxplot, Q-Q, and ECDF chart-data calculation from validated canonical rows.
- Reused immutable dataset version lookup, canonical row streaming, filter snapshot row freezing, result JSON persistence, result SHA-256 validation, and no-raw-value artifact metadata.
- Initially added a minimal Workbench execution panel for `eda.graphical_summary` without fake chart images; chart rendering is now superseded by the inline SVG renderer in Progress Update 43.
- Kept all remaining methods planned/disabled until real calculation code and tests exist.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/graphical_summary.py`
- `backend/tests/unit/test_graphical_summary.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/README.md`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/GraphicalSummaryPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Document priority:

- `AGENTS.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `data_prd_addendum.md`
- `data_prd.md` if present
- nearest nested instruction file

Next PR:

- Choose the next real statistical method only after dependency review and reference fixtures are ready.
- Likely candidates are `eda.normality` or `eda.equal_variances`, but both require a validated SciPy/statsmodels compatibility plan before being marked executable.
- Keep Bayesian optimization, DOE, regression, quality control, ML, and chart renderer work out of the next narrow stats slice unless the gate changes.

Validation:

- `python3 -m compileall -q backend/app/statistics/graphical_summary.py backend/app/services/analysis_runs.py backend/app/analyses/registry.py backend/tests/unit/test_graphical_summary.py backend/tests/unit/test_api_contracts.py`: passed under WSL Python 3.12 syntax check only.
- `npm --prefix ./frontend run typecheck`: passed under WSL Node.
- `git diff --check`: passed.
- `npm --prefix ./frontend run lint`: passed under WSL Node.
- `npm --prefix ./frontend run test -- --run`: passed with 16 Vitest tests under WSL Node.
- `npm --prefix ./frontend run build`: passed under WSL Node.
- Backend pytest: not run in this WSL Python environment because `python3 -m pytest ...` fails with `No module named pytest`.
- Full `scripts/check.ps1` and Windows `.venv` backend pytest: not run because `cmd.exe`/`powershell.exe` from this WSL session fail before command execution with the known WSL socket/vsock error.

Known limitations:

- Superseded by Progress Update 43: `eda.graphical_summary` now renders inline SVG charts from the existing chart-data payload.
- Grouped graphical summaries, KDE, density rendering, chart exports, and small-multiple UI are not implemented.
- This method has no p-values, inferential decision logic, confidence intervals, or effect sizes.

## 16. PR Description Draft For Normality Dependency Gate

Summary:

- Kept `eda.normality` and `eda.equal_variances` in `planned` state because SciPy is not yet part of backend production dependencies.
- Added registry disabled reasons that explicitly require SciPy-based compatibility validation and reference fixtures before either method can become executable.
- Updated frontend method guidance so planned normality/equal-variance methods show the SciPy validation preflight requirement.
- Updated dependency review and progress docs with the exact gate for future p-value/statistic methods.
- Added no p-values, no test statistics, no inferential decision logic, and no mock result payloads.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/analysisMethodGuidance.ts`
- `docs/dependency_review.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Next PR:

- Validate SciPy/NumPy on native Windows Python 3.10.
- Add exact pinned dependencies only after wheel/license/offline/runtime checks.
- Implement `eda.normality` with Shapiro-Wilk, Anderson-Darling, Q-Q metadata, N/exclusion/warning metadata, reference fixtures, and no automatic downstream test switching.

Validation:

- WSL `python3` check showed SciPy is not installed: `ModuleNotFoundError No module named 'scipy'`.
- Focused syntax check for the changed backend registry and API contract test passed under WSL Python.
- `git diff --check`: passed.
- Touched backend Python line-length scan: passed after wrapping one API contract assertion.
- `npm --prefix ./frontend run typecheck`: passed under WSL Node.
- `npm --prefix ./frontend run lint`: passed under WSL Node.
- `npm --prefix ./frontend run test -- --run`: passed with 16 Vitest tests under WSL Node.
- `npm --prefix ./frontend run build`: passed under WSL Node.
- Backend pytest was not run because WSL `python3` has no pytest and Windows `.venv` execution fails from this WSL session with the known WSL socket/vsock error.

Known limitations:

- This is a gate-hardening slice, not a new executable statistical method.
- Backend pytest and full Windows check still require native Windows PowerShell in the current environment.

## 17. PR Description Draft For Statistical Dependency Smoke

Summary:

- Added an opt-in Windows PowerShell install/smoke flow for future statistical dependencies.
- Added a Python smoke helper that checks Python 3.10, imports NumPy/SciPy, and runs Shapiro-Wilk, Anderson-Darling, Levene, and Brown-Forsythe calculations.
- Added smoke output capture and validation so native Windows results can be recorded before dependency pins change.
- Added a markdown record renderer and unit tests for the smoke JSON validator/renderer.
- Added synthetic normality reference input fixture and a SciPy-backed reference generator for the next implementation PR.
- Added a generated normality reference validator and tests to check case alignment, Python version, dependency metadata, and p-value/statistic ranges.
- Added a result-record template for native Windows dependency spike evidence.
- Kept SciPy/NumPy out of the production dependency list and lockfiles in that slice.
- Kept `eda.normality` and `eda.equal_variances` planned in that dependency-gate slice; no p-values, test statistics, or fake result payloads were added.

Changed files:

- `scripts/check-stat-deps.ps1`
- `scripts/install-stat-deps-spike.ps1`
- `scripts/stat_dependency_smoke.py`
- `scripts/validate_stat_dependency_smoke.py`
- `scripts/render_stat_dependency_record.py`
- `scripts/generate_normality_reference.py`
- `scripts/validate_normality_reference.py`
- `backend/tests/reference/fixtures/normality_input.json`
- `backend/tests/reference/fixtures/normality_scipy_reference.json`
- `backend/tests/unit/test_stat_dependency_smoke_tools.py`
- `backend/tests/unit/test_normality_reference_fixture.py`
- `backend/tests/unit/test_normality_reference_validator.py`
- `docs/normality_method_contract.md`
- `docs/stat_dependency_spike.md`
- `docs/setup.md`
- `docs/dependency_review.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

How to run on native Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-stat-deps-spike.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\check-stat-deps.ps1
.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json
.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json
.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py
.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py
```

Next PR:

- Decide whether to production-pin NumPy 2.2.6 and SciPy 1.15.3 after the recorded candidate spike.
- If approved, update backend dependency metadata and run full Windows checks.
- Implement `eda.normality` according to `docs/normality_method_contract.md` using `backend/tests/reference/fixtures/normality_scipy_reference.json`; do not add downstream automatic method switching.

Validation:

- `git diff --check`: passed.
- `python3 -m compileall -q scripts/stat_dependency_smoke.py scripts/validate_stat_dependency_smoke.py scripts/render_stat_dependency_record.py scripts/generate_normality_reference.py scripts/validate_normality_reference.py backend/tests/unit/test_stat_dependency_smoke_tools.py backend/tests/unit/test_normality_reference_fixture.py backend/tests/unit/test_normality_reference_validator.py`: passed under WSL.
- Touched script line-length scan: passed.
- Direct renderer smoke with a synthetic passed payload: passed.
- Direct normality input fixture load smoke: passed with 3 cases.
- Direct normality reference validator smoke with a synthetic generated-reference payload: passed.
- Direct WSL `python3 scripts/generate_normality_reference.py`: returned the expected `python_version_unsupported` JSON because WSL Python is 3.12.3.
- Direct WSL `python3 scripts/stat_dependency_smoke.py`: returned the expected `python_version_unsupported` JSON because WSL Python is 3.12.3.
- Native Windows Python 3.10.11 smoke passed after installing candidate NumPy 2.2.6 and SciPy 1.15.3 into `.venv`.
- `.\.venv\Scripts\python.exe .\scripts\validate_stat_dependency_smoke.py .\logs\stat-dependency-smoke.json`: passed.
- `.\.venv\Scripts\python.exe .\scripts\render_stat_dependency_record.py .\logs\stat-dependency-smoke.json`: passed.
- `.\.venv\Scripts\python.exe .\scripts\generate_normality_reference.py`: passed and generated `backend\tests\reference\fixtures\normality_scipy_reference.json`; SciPy emitted the expected Shapiro-Wilk `N > 5000` accuracy warning for the large synthetic case.
- `.\.venv\Scripts\python.exe .\scripts\validate_normality_reference.py`: passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_stat_dependency_smoke_tools.py .\backend\tests\unit\test_normality_reference_fixture.py .\backend\tests\unit\test_normality_reference_validator.py`: passed with 9 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed after formatting one backend file and fixing ruff findings; backend pytest 78 tests, frontend Vitest 16 tests, frontend build passed.

Known limitations:

- `check-stat-deps.ps1` does not install dependencies; `install-stat-deps-spike.ps1` installs candidate wheels only into local `.venv`.
- Passing smoke checks is necessary but not sufficient for marking `eda.normality` or `eda.equal_variances` available.
- This section is historical. NumPy/SciPy are now production-pinned for the later `eda.normality` implementation slice.

## 18. PR Description Draft For Normality Implementation

Summary:

- Added production pins for NumPy 2.2.6 and SciPy 1.15.3 after the recorded Windows Python 3.10 dependency spike.
- Made `eda.normality` available with real Shapiro-Wilk, Anderson-Darling, and deterministic Q-Q point payloads from canonical rows.
- Added warnings for non-numeric exclusions, no numeric values, insufficient observations, constant columns, Shapiro large-N p-value limitations, Q-Q truncation, and the no-automatic-method-switch rule.
- Added persisted result envelope support through the existing analysis run/result API and row snapshot provenance.
- Added a minimal frontend execution panel with numeric column selection, alpha input, warnings, and result table.
- Added `instruction.md` with Windows PowerShell install, run, check, and basic usage flow.
- Kept grouped normality unsupported with stable error `normality_grouping_not_supported`.
- Kept `eda.equal_variances` and all later methods planned/disabled; no fake results were added.

Changed files:

- `backend/pyproject.toml`
- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/normality.py`
- `backend/tests/unit/test_normality.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/NormalityAnalysisPanel.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/dependency_review.md`
- `docs/normality_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/setup.md`
- `docs/six_module_implementation_guide.md`
- `docs/stat_dependency_spike.md`
- `docs/storage.md`
- `to_do_list.md`

Next PR:

- Implement `eda.equal_variances` only after adding reference fixtures and API/UI tests for Levene and Brown-Forsythe.
- Keep hypothesis tests, regression, quality control, DOE, Bayesian optimization, chart rendering, and heavy optional dependencies out of the next narrow slice unless explicitly requested.

Validation:

- Targeted backend pytest for `test_normality.py` and `test_api_contracts.py`: passed with 25 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 17 tests.
- Full `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed; backend pytest 84 tests, frontend Vitest 17 tests, frontend build passed.

## Progress Update 20 - Equal Variances Executable Slice

Completed in current working tree:

- Made `eda.equal_variances` available in the analysis method registry.
- Added `backend/app/statistics/equal_variances.py` with real SciPy-backed Brown-Forsythe and Levene(mean) calculations.
- Added complete-case exclusion counts, group summaries, stable warnings, and no-automatic-method-switch messaging.
- Added equal-variance reference fixtures:
  - `backend/tests/reference/fixtures/equal_variances_input.json`
  - `backend/tests/reference/fixtures/equal_variances_scipy_reference.json`
- Added backend domain and API tests for hand-checkable summaries, SciPy reference matching, missing/non-numeric/small-group handling, constant-response handling, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `EqualVariancesPanel` with response/group/alpha controls, warnings, test result table, and group summary table.
- Updated docs with `docs/equal_variances_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/equal_variances.py`
- `backend/tests/reference/fixtures/equal_variances_input.json`
- `backend/tests/reference/fixtures/equal_variances_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_equal_variances.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/EqualVariancesPanel.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `docs/equal_variances_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_equal_variances.py` and `test_api_contracts.py`: passed with 26 tests.
- Backend ruff check on touched backend files: passed.
- Backend mypy over `backend/app`: passed with 39 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 18 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed; backend pytest 89 tests, frontend Vitest 18 tests, frontend build passed.

Next PR:

- Move to Gate B2 only after full project check passes.
- First Gate B2 candidate should be a narrow inferential slice, likely `hypothesis.one_sample_t` or `hypothesis.two_sample_t`, with explicit design metadata, reference fixtures, effect size/CI, and no automatic method switching from normality/equal-variance diagnostics.
- Keep regression, quality, DOE, Bayesian optimization, chart rendering, and optional heavy dependencies out of the next narrow PR unless explicitly requested.

## Progress Update 21 - Two-Sample T-Test Executable Slice

Completed in current working tree:

- Made `hypothesis.two_sample_t` available in the analysis method registry as the first Gate B2 inferential slice.
- Added `backend/app/statistics/two_sample_t.py` with real SciPy-backed Welch default and explicit pooled Student independent two-sample t-test calculations.
- Added validation for response/group roles, exactly two groups, complete-case missing handling, alpha, confidence level, alternative hypothesis, null difference, and variance assumption.
- Added result fields for N/exclusions, group summaries, mean difference, confidence interval, t statistic, df, p-value, Cohen's d, Hedges g, warning codes, and provenance.
- Added two-sample reference fixtures:
  - `backend/tests/reference/fixtures/two_sample_t_input.json`
  - `backend/tests/reference/fixtures/two_sample_t_scipy_reference.json`
- Added backend domain and API tests for hand-checkable group summaries, SciPy reference matching, exclusion handling, invalid group structures, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `TwoSampleTPanel` with response/group selectors, Welch/pooled choice, alternative, alpha, confidence level, warnings, contrast table, and group summary table.
- Updated docs with `docs/two_sample_t_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/two_sample_t.py`
- `backend/tests/reference/fixtures/two_sample_t_input.json`
- `backend/tests/reference/fixtures/two_sample_t_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_two_sample_t.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/TwoSampleTPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/two_sample_t_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`

Validation:

- Targeted backend pytest for `test_two_sample_t.py` and `test_api_contracts.py`: passed with 27 tests.
- Backend ruff check on touched backend files: passed.
- Backend mypy over `backend/app`: passed with 40 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 19 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed; backend pytest 94 tests, frontend Vitest 19 tests, and frontend build passed.

Next PR:

- Keep remaining B2 hypothesis/categorical methods planned until each has explicit design metadata, reference fixtures, effect size/CI policy, and no automatic diagnostic-based method switching.
- Good next candidates are a narrow one-sample t-test or Mann-Whitney U slice; do not start ANOVA, regression, quality, DOE, Bayesian optimization, chart rendering, or optional heavy dependency work unless the gate changes.

## Progress Update 22 - One-Sample T-Test Executable Slice

Completed in current working tree:

- Made `hypothesis.one_sample_t` available in the analysis method registry as the next narrow Gate B2 inferential slice.
- Added `backend/app/statistics/one_sample_t.py` with real SciPy-backed one-sample t-test calculations.
- Added validation for response role, explicit finite reference mean, complete-case missing handling, alpha, confidence level, and alternative hypothesis.
- Added result fields for N/exclusions, sample summary, mean difference, confidence interval, t statistic, df, p-value, Cohen dz, Hedges-corrected effect, warning codes, and provenance.
- Added one-sample reference fixtures:
  - `backend/tests/reference/fixtures/one_sample_t_input.json`
  - `backend/tests/reference/fixtures/one_sample_t_scipy_reference.json`
- Added backend domain and API tests for hand-checkable summaries, SciPy reference matching, exclusion handling, invalid input handling, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `OneSampleTPanel` with response selector, reference mean, alternative, alpha, confidence level, warnings, and result table.
- Updated docs with `docs/one_sample_t_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/one_sample_t.py`
- `backend/tests/reference/fixtures/one_sample_t_input.json`
- `backend/tests/reference/fixtures/one_sample_t_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_one_sample_t.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/OneSampleTPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/one_sample_t_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation:

- Targeted backend pytest for `test_one_sample_t.py` and `test_api_contracts.py`: passed with 28 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Backend ruff format check, ruff check, and mypy over `backend/app`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 20 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed; backend pytest 99 tests, frontend Vitest 20 tests, and frontend build passed.

Next PR:

- Keep remaining B2 hypothesis/categorical methods planned until each has explicit design metadata, reference fixtures, effect size/CI policy, and no automatic diagnostic-based method switching.
- Good next candidates are a narrow Mann-Whitney U or one-sample Wilcoxon slice; do not start ANOVA, regression, quality, DOE, Bayesian optimization, chart rendering, or optional heavy dependency work unless the gate changes.

## Progress Update 23 - Mann-Whitney U Executable Slice

Completed in current working tree:

- Made `hypothesis.mann_whitney` available in the analysis method registry as the next narrow Gate B2 inferential slice.
- Added `backend/app/statistics/mann_whitney.py` with real SciPy-backed Mann-Whitney U calculations.
- Added validation for response/group roles, exactly two usable groups, complete-case missing handling, alpha, alternative hypothesis, and p-value method.
- Added exact/asymptotic method recording, tie detection, explicit rejection of exact p-value requests when ties are present, and a warning not to describe the result as a median-only test.
- Added result fields for N/exclusions, group rank summaries, U statistic, p-value, rank-biserial, common-language probability, warning codes, and provenance.
- Added Mann-Whitney reference fixtures:
  - `backend/tests/reference/fixtures/mann_whitney_input.json`
  - `backend/tests/reference/fixtures/mann_whitney_scipy_reference.json`
- Added backend domain and API tests for hand-checkable U/effect size values, SciPy reference matching, exclusion handling, tie/asymptotic behavior, invalid group structures, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `MannWhitneyPanel` with response/group selectors, exact/auto/asymptotic choice, alternative, alpha, warnings, U/effect table, and rank summary table.
- Updated docs with `docs/mann_whitney_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/mann_whitney.py`
- `backend/tests/reference/fixtures/mann_whitney_input.json`
- `backend/tests/reference/fixtures/mann_whitney_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_mann_whitney.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/MannWhitneyPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/mann_whitney_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_mann_whitney.py` and `test_api_contracts.py`: passed with 29 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 21 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed; backend pytest 104 tests, frontend Vitest 21 tests, and frontend build passed.

Next PR:

- Keep remaining B2 hypothesis/categorical methods planned until each has explicit design metadata, reference fixtures, effect size/CI policy, and no automatic diagnostic-based method switching.
- Good next candidates are a narrow one-sample Wilcoxon or paired t-test slice; do not start ANOVA, regression, quality, DOE, Bayesian optimization, chart rendering, or optional heavy dependency work unless the gate changes.

## Progress Update 24 - One-Sample Wilcoxon Executable Slice

Completed in current working tree:

- Made `hypothesis.one_sample_wilcoxon` available in the analysis method registry as the next narrow Gate B2 inferential slice.
- Added `backend/app/statistics/one_sample_wilcoxon.py` with real SciPy-backed one-sample signed-rank calculations.
- Added validation for response role, complete-case missing handling, alpha, alternative hypothesis, reference location, p-value method, and `zero_method`.
- Added exact/asymptotic method recording, zero-difference and absolute-difference tie detection, explicit rejection of exact p-value requests when zero differences or ties are present, and warnings that the result depends on the signed-difference symmetry assumption and must not be reduced to a simple median-only test.
- Added result fields for N/exclusions, sample summary, signed-rank W statistic, p-value, positive/negative rank sums, rank-biserial effect size, warning codes, and provenance.
- Added one-sample Wilcoxon reference fixtures:
  - `backend/tests/reference/fixtures/one_sample_wilcoxon_input.json`
  - `backend/tests/reference/fixtures/one_sample_wilcoxon_scipy_reference.json`
- Added backend domain and API tests for hand-checkable signed-rank/effect size values, SciPy reference matching, exclusion handling, zero/tie asymptotic behavior, invalid exact requests, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `OneSampleWilcoxonPanel` with response selector, reference location, exact/auto/asymptotic choice, zero handling, alternative, alpha, warnings, W/effect table, and sample summary table.
- Updated docs with `docs/one_sample_wilcoxon_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/one_sample_wilcoxon.py`
- `backend/tests/reference/fixtures/one_sample_wilcoxon_input.json`
- `backend/tests/reference/fixtures/one_sample_wilcoxon_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_one_sample_wilcoxon.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/OneSampleWilcoxonPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/one_sample_wilcoxon_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_one_sample_wilcoxon.py` and `test_api_contracts.py`: passed with 30 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 22 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed; backend pytest 109 tests, frontend Vitest 22 tests, and frontend build passed.

Next PR:

- Keep remaining B2 hypothesis/categorical methods planned until each has explicit design metadata, reference fixtures, effect size/CI policy, and no automatic diagnostic-based method switching.
- Good next candidates are a narrow paired t-test or Kruskal-Wallis slice; do not start ANOVA, regression, quality, DOE, Bayesian optimization, chart rendering, or optional heavy dependency work unless the gate changes.

## Progress Update 25 - Paired t-Test Executable Slice

Completed in current working tree:

- Made `hypothesis.paired_t` available in the analysis method registry as the next narrow Gate B2 inferential slice.
- Added `backend/app/statistics/paired_t.py` with real SciPy-backed paired t-test calculations for wide before/after measurement columns.
- Added validation for before/after numeric non-ID columns, distinct measurement columns, complete-pair missing handling, alpha, confidence level, alternative hypothesis, and reference difference.
- Defined pair difference as `after - before`; long format subject/condition/response paired data remains out of scope for this slice.
- Added result fields for N/exclusions, incomplete pair counts, non-numeric pair counts, before/after means, difference summary, CI, t statistic, df, p-value, Cohen dz, Hedges-corrected effect, warning codes, and provenance.
- Added paired t-test reference fixtures:
  - `backend/tests/reference/fixtures/paired_t_input.json`
  - `backend/tests/reference/fixtures/paired_t_scipy_reference.json`
- Added backend domain and API tests for hand-checkable difference values, SciPy reference matching, complete-pair exclusion handling, invalid inputs, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `PairedTPanel` with before/after selectors, reference difference, alternative, alpha, confidence level, warnings, t/effect table, and paired summary table.
- Updated docs with `docs/paired_t_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/paired_t.py`
- `backend/tests/reference/fixtures/paired_t_input.json`
- `backend/tests/reference/fixtures/paired_t_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_paired_t.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/PairedTPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/paired_t_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_paired_t.py` and `test_api_contracts.py`: passed with 31 tests.
- Backend ruff and mypy over `backend/app`: passed with 44 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 23 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 114 tests, frontend Vitest 23 tests, and frontend build.

Next PR:

- Keep remaining B2 hypothesis/categorical methods planned until each has explicit design metadata, reference fixtures, effect size/CI policy, and no automatic diagnostic-based method switching.
- Good next candidates are a narrow Kruskal-Wallis or one-way ANOVA setup slice; do not start regression, quality, DOE, Bayesian optimization, chart rendering, or optional heavy dependency work unless the gate changes.

## Progress Update 26 - Kruskal-Wallis Executable Slice

Completed in current working tree:

- Made `hypothesis.kruskal_wallis` available in the analysis method registry as the next narrow Gate B2 inferential slice.
- Added `backend/app/statistics/kruskal_wallis.py` with real SciPy-backed Kruskal-Wallis calculations for independent 3-or-more-group response designs.
- Added validation for response/group columns, complete-case missing handling, alpha, post-hoc method, and post-hoc policy.
- Added result fields for N/exclusions, group rank summaries, tie correction, H statistic, df, p-value, epsilon-squared, warning codes, provenance, and Dunn/Holm post-hoc comparisons only when the overall test is significant.
- Added Kruskal-Wallis reference fixtures:
  - `backend/tests/reference/fixtures/kruskal_wallis_input.json`
  - `backend/tests/reference/fixtures/kruskal_wallis_scipy_reference.json`
- Added backend domain and API tests for hand-checkable rank sums, reference matching, tie/exclusion handling, invalid designs, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `KruskalWallisPanel` with response/group selectors, alpha input, warnings, H/effect table, group rank summary table, and Dunn/Holm comparison table.
- Updated docs with `docs/kruskal_wallis_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/kruskal_wallis.py`
- `backend/tests/reference/fixtures/kruskal_wallis_input.json`
- `backend/tests/reference/fixtures/kruskal_wallis_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_kruskal_wallis.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/KruskalWallisPanel.tsx`
- `frontend/src/App.test.tsx`
- `docs/kruskal_wallis_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_kruskal_wallis.py` and `test_api_contracts.py`: passed with 32 tests.
- Backend ruff check for touched backend files: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 24 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 119 tests, frontend Vitest 24 tests, and frontend build.

Next PR:

- Keep remaining B2 hypothesis/categorical methods planned until each has explicit design metadata, reference fixtures, effect size/CI policy, and no automatic diagnostic-based method switching.
- Good next candidates are a narrow one-way ANOVA setup slice or the next categorical method slice; do not start regression, quality, DOE, Bayesian optimization, chart rendering, or optional heavy dependency work unless the gate changes.

## Progress Update 27 - 1-Proportion Executable Slice

Completed in current working tree:

- Made `categorical.one_proportion` available in the analysis method registry as the first narrow Gate B2 categorical slice.
- Added `backend/app/statistics/one_proportion.py` with real SciPy-backed exact binomial calculations for one binary response column plus explicit event level.
- Added validation for response column, event level, `null_proportion`, alpha, confidence level, CI method, and complete-case missing handling.
- Added result fields for N/exclusions, event/non-event counts, observed levels, sample proportion, `p - p0`, odds where finite, exact binomial p-value, Wilson or Clopper-Pearson CI, Cohen h, warning codes, and provenance.
- Added one-proportion reference fixtures:
  - `backend/tests/reference/fixtures/one_proportion_input.json`
  - `backend/tests/reference/fixtures/one_proportion_reference.json`
- Added backend domain and API tests for hand-checkable exact binomial values, reference matching, warning behavior, invalid inputs, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `OneProportionPanel` with binary response selector, event level input, p0, alternative, CI method, alpha, confidence level, warnings, result summary table, and observed-level table.
- Updated docs with `docs/one_proportion_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/one_proportion.py`
- `backend/tests/reference/fixtures/one_proportion_input.json`
- `backend/tests/reference/fixtures/one_proportion_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_one_proportion.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/OneProportionPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/App.test.tsx`
- `docs/one_proportion_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_one_proportion.py` and `test_api_contracts.py`: passed with 33 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 25 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 124 tests, frontend Vitest 25 tests, and frontend build.

Next PR:

- Superseded by Progress Update 28 for `categorical.two_proportion`.
- Keep summary-count categorical input, Fisher association p-values, ANOVA, regression, quality, DOE, Bayesian optimization, chart rendering, and optional heavy dependency work out of scope until each receives its own explicit contract, reference fixtures, and validation.

## Progress Update 28 - 2-Proportion Executable Slice

Completed in current working tree:

- Made `categorical.two_proportion` available in the analysis method registry as the second narrow Gate B2 categorical slice.
- Added `backend/app/statistics/two_proportion.py` with real SciPy-backed Fisher exact calculations for one binary response column, exactly two usable groups, and an explicit event level.
- Added validation for response column, group column, event level, alpha, confidence level, alternative, and complete-case missing handling.
- Added result fields for N/exclusions, group event/non-event counts, sample proportions, expected counts, proportion difference, Newcombe-Wilson CI, Fisher exact p-value, risk ratio, odds ratio, warning codes, and provenance.
- Added two-proportion reference fixtures:
  - `backend/tests/reference/fixtures/two_proportion_input.json`
  - `backend/tests/reference/fixtures/two_proportion_reference.json`
- Added backend domain and API tests for hand-checkable 2x2 counts, reference matching, missing/sparse/zero-cell warnings, invalid inputs, canonical-row execution after raw mutation, result persistence, and no fake output.
- Added minimal frontend API types and `TwoProportionPanel` with binary response selector, group selector, event level input, alternative, alpha, confidence level, warnings, result summary table, and group event/non-event table.
- Updated docs with `docs/two_proportion_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/two_proportion.py`
- `backend/tests/reference/fixtures/two_proportion_input.json`
- `backend/tests/reference/fixtures/two_proportion_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_two_proportion.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/TwoProportionPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/App.test.tsx`
- `docs/two_proportion_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_two_proportion.py` and `test_api_contracts.py`: passed with 34 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 26 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 129 tests, frontend Vitest 26 tests, and frontend build.

Next PR:

- Keep summary-count categorical input, Fisher association p-values, regression, quality, DOE, Bayesian optimization, chart rendering, and optional heavy dependency work out of scope until each receives its own explicit contract, reference fixtures, and validation.
- Good next candidates are either a narrow categorical follow-up slice or the next Gate B2 cleanup slice.

## Progress Update 29 - One-Way ANOVA Executable Slice

Completed in current working tree:

- Made `hypothesis.one_way_anova` available in the analysis method registry as the first narrow Gate B2 ANOVA slice.
- Added `backend/app/statistics/one_way_anova.py` with real standard one-way ANOVA calculations, group summaries, ANOVA table, eta squared, omega squared, and Tukey-Kramer post-hoc comparisons after a significant omnibus test.
- Added validation for response column, group column, alpha, confidence level, ANOVA type, post-hoc method, post-hoc policy, and complete-case missing handling.
- Added stable failure paths for unsupported ANOVA/post-hoc options, invalid alpha/confidence, too few groups, too-small groups, all-identical response, zero residual variance, and non-finite statistics without falling back to another method.
- Added one-way ANOVA reference fixtures:
  - `backend/tests/reference/fixtures/one_way_anova_input.json`
  - `backend/tests/reference/fixtures/one_way_anova_scipy_reference.json`
- Added backend domain and API tests for a hand-checkable balanced ANOVA table, SciPy `f_oneway` reference matching, Tukey-Kramer adjusted p-values/CI, missing/non-numeric exclusions, invalid inputs, canonical-row execution after raw mutation, stored result retrieval, row snapshot provenance, and no fake output.
- Added minimal frontend API types and `OneWayAnovaPanel` with response/group selectors, alpha, confidence level, standard-ANOVA/Tukey-Kramer policy display, warnings, ANOVA table, group summaries, and post-hoc table.
- Updated docs with `docs/one_way_anova_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/one_way_anova.py`
- `backend/tests/reference/fixtures/one_way_anova_input.json`
- `backend/tests/reference/fixtures/one_way_anova_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_one_way_anova.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/OneWayAnovaPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/App.test.tsx`
- `docs/one_way_anova_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_one_way_anova.py` and `test_api_contracts.py`: passed with 35 tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 27 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 134 tests, frontend Vitest 27 tests, and frontend build.

Next PR:

- Keep Welch ANOVA, Games-Howell, two-way/repeated/ANCOVA, summary-statistic ANOVA input, Fisher association p-values, regression, quality, DOE, Bayesian optimization, chart rendering, and optional heavy dependency work out of scope until each receives its own explicit contract, reference fixtures, and validation.
- Good next candidates are a narrow categorical follow-up slice or the next Gate B2 cleanup slice; keep all still-planned methods non-executable until they have real calculation code and tests.

## Progress Update 30 - Chi-square Association Executable Slice

Completed in current working tree:

- Made `categorical.chi_square_association` available in the analysis method registry as the third narrow Gate B2 categorical slice.
- Added `backend/app/statistics/chi_square_association.py` with real SciPy-backed Pearson chi-square independence calculations for two categorical columns.
- Added observed/expected counts, row/column/total percentages, standardized residuals, expected-count diagnostics, p-value, Cramer's V, warning codes, and provenance.
- Added stable failure paths for invalid alpha, same row/column selection, missing columns, ID roles, too few row/column levels, excessive levels, and non-finite statistics without falling back to another method.
- Added sparse 2x2 Fisher exact recommendation metadata without computing or fabricating a Fisher exact p-value.
- Added chi-square association reference fixtures:
  - `backend/tests/reference/fixtures/chi_square_association_input.json`
  - `backend/tests/reference/fixtures/chi_square_association_scipy_reference.json`
- Added backend domain and API tests for a hand-checkable 2x2 table, SciPy reference matching, missing exclusions, sparse 2x2 recommendation, invalid inputs, canonical-row execution after raw mutation, stored result retrieval, row snapshot provenance, and no fake output.
- Added minimal frontend API types and `ChiSquareAssociationPanel` with row/column selectors, alpha, Pearson-only policy display, warnings, test summary, and observed/expected contingency table.
- Updated docs with `docs/chi_square_association_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/chi_square_association.py`
- `backend/tests/reference/fixtures/chi_square_association_input.json`
- `backend/tests/reference/fixtures/chi_square_association_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_chi_square_association.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/ChiSquareAssociationPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/chi_square_association_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation so far:

- Targeted backend pytest for `test_chi_square_association.py` and `test_api_contracts.py`: passed with 36 tests.
- Backend ruff for the touched chi-square backend files: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 28 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 139 tests, frontend Vitest 28 tests, and frontend build.

Next PR:

- Keep summary-count contingency input, Fisher exact association p-values, regression, quality, DOE, Bayesian optimization, chart rendering, and optional heavy dependency work out of scope until each receives its own explicit contract, reference fixtures, and validation.
- Good next candidates are either the next categorical follow-up slice, a Gate B2 cleanup slice, or a regression planning slice; keep all still-planned methods non-executable until they have real calculation code and tests.

## Progress Update 31 - One-Sample Equivalence TOST Executable Slice

Completed in current working tree:

- Made `hypothesis.equivalence_tost` available in the analysis method registry as the first narrow Gate B2 equivalence slice.
- Added `backend/app/statistics/equivalence_tost.py` with real SciPy-backed one-sample mean TOST calculations for one numeric response column.
- Added explicit reference mean, user-defined raw-unit lower/upper equivalence bounds, `alpha`, `1 - 2 * alpha` CI, lower/upper one-sided tests, TOST p-value, Cohen dz, Hedges-corrected effect, warning codes, and provenance.
- Added stable failure paths for unsupported design, missing response, invalid reference mean, invalid or reversed bounds, invalid alpha, unsupported missing policy, too few usable rows, and zero standard error without falling back to another method.
- Kept paired mean-difference TOST, independent two-sample TOST, standardized-margin input, automatic equivalence-bound suggestions, nonparametric equivalence tests, and automatic method switching out of scope.
- Added equivalence TOST reference fixtures:
  - `backend/tests/reference/fixtures/equivalence_tost_input.json`
  - `backend/tests/reference/fixtures/equivalence_tost_scipy_reference.json`
- Added backend domain and API tests for a hand-checkable one-sample case, SciPy reference matching, missing/non-numeric exclusions, invalid inputs, canonical-row execution after raw mutation, stored result retrieval, row snapshot provenance, and no fake output.
- Added minimal frontend API types and `EquivalenceTostPanel` with response selector, reference mean, lower/upper bounds, alpha, computed TOST CI level, warnings, one-sided test table, and result summary.
- Updated docs with `docs/equivalence_tost_method_contract.md` and Gate B progress notes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/equivalence_tost.py`
- `backend/tests/reference/fixtures/equivalence_tost_input.json`
- `backend/tests/reference/fixtures/equivalence_tost_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_equivalence_tost.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/EquivalenceTostPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/equivalence_tost_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`
- `instruction.md`
- `backend/README.md`
- `docs/datasets.md`
- `docs/storage.md`
- `docs/dependency_review.md`
- `docs/stat_dependency_spike.md`

Validation:

- Targeted backend pytest for `test_equivalence_tost.py` and `test_api_contracts.py`: passed with 37 tests.
- Backend ruff for the touched TOST backend files: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 29 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 144 tests, frontend Vitest 29 tests, and frontend build.

Next PR:

- Keep paired/two-sample TOST, regression, quality, DOE, Bayesian optimization, generated chart rendering, and optional heavy dependency work out of scope until each receives its own explicit contract, reference fixtures, and validation.
- Good next candidates are a Gate B2 cleanup/documentation pass, regression planning, or the next explicitly scoped statistical method; keep all still-planned methods non-executable until they have real calculation code and tests.

## Progress Update 32 - Analysis UX Error/Guidance Improvement

Completed in current working tree:

- Moved analysis execution errors from the top of the analysis workspace into the selected method Workbench, directly below the execution panel.
- Added frontend error-code explanations with a short title, likely cause, and user action while keeping stable machine-readable error codes visible.
- Added beginner-oriented "쉽게 말하면" explanations and common error causes for the current hypothesis and categorical methods.
- Kept backend calculation behavior unchanged; this is a frontend usability slice, not a new statistical method.

Changed files:

- `frontend/src/AnalysisWorkbench.tsx`
- `frontend/src/WorkspaceRouter.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/analysisRunErrors.ts`
- `to_do_list.md`

Validation:

- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 30 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 144 tests, frontend Vitest 30 tests, and frontend build.
- `git diff --check`: passed.

## Progress Update 33 - Pearson Correlation Executable Slice

Completed in current working tree:

- Made `regression.pearson` available in the analysis method registry as the first narrow Gate C1 executable slice.
- Added `backend/app/statistics/pearson.py` with real SciPy-backed Pearson product-moment correlation for two numeric columns.
- Added complete-case exclusion counts, X/Y sample summaries, covariance, r, r-squared, p-value, Fisher z confidence interval, stable warning codes, and provenance.
- Added stable failure paths for missing X/Y columns, same X/Y column, non-numeric or ID columns, invalid alpha/confidence level, unsupported missing policy, too few complete numeric pairs, constant X/Y columns, and non-finite results without falling back to another method.
- Added Pearson reference fixtures:
  - `backend/tests/reference/fixtures/pearson_input.json`
  - `backend/tests/reference/fixtures/pearson_scipy_reference.json`
- Added backend domain and API tests for hand-checkable summaries, SciPy reference matching, missing/non-numeric exclusions, invalid inputs, canonical-row execution after raw mutation, stored result retrieval, row snapshot provenance, and no fake output.
- Added frontend API types and `PearsonCorrelationPanel` with X/Y selectors, alpha, confidence level, warnings, correlation summary, and sample summary tables.
- Added beginner-oriented guidance/error explanations for Pearson-specific mistakes such as same-column selection, too-small N, and constant columns.
- Added `docs/pearson_method_contract.md` and updated Gate progress docs.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/pearson.py`
- `backend/tests/reference/fixtures/pearson_input.json`
- `backend/tests/reference/fixtures/pearson_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_pearson.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/PearsonCorrelationPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/analysisRunErrors.ts`
- `frontend/src/App.test.tsx`
- `docs/pearson_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_pearson.py` and `test_api_contracts.py`: passed with 38 tests.
- Backend ruff for touched Pearson backend files: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 31 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 149 tests, frontend Vitest 31 tests, and frontend build.

Next PR:

- Good next candidates are X-Y correlation matrix planning/implementation, a safe OLS term-builder planning slice, or a Gate C1 UI/results cleanup pass.
- Keep Spearman/Kendall, generated scatterplot artifacts, OLS model fitting, model manifest storage, prediction, response optimizer, quality control, DOE, and Bayesian optimization out of scope until each receives an explicit contract, reference fixtures, and validation.

## Progress Update 34 - X-Y Correlation And Analysis Error Placement Slice

Completed in current working tree:

- Hardened analysis-page error placement by removing the extra `flowError` prop from `WorkspaceRouter`; dataset-preparation top error boxes no longer render on the analysis route.
- Added readable frontend error details for `two_sample_t_requires_exactly_two_groups`, including the likely cause and action while preserving the stable machine-readable code.
- Made `regression.xy_correlation` available as the second narrow Gate C1 executable slice.
- Added `backend/app/statistics/xy_correlation.py` with real SciPy-backed pairwise Pearson X-Y correlation matrix calculations from canonical rows.
- Added pair-level N/exclusion counts, covariance, r, r-squared, p-value, Fisher z confidence interval, pairwise complete-case warning, non-causation/linearity/outlier warnings, and cell-level failure codes for too-small N, constant X/Y, and non-finite results without fake statistics.
- Added X-Y reference fixtures:
  - `backend/tests/reference/fixtures/xy_correlation_input.json`
  - `backend/tests/reference/fixtures/xy_correlation_scipy_reference.json`
- Added backend domain and API tests for hand-checkable matrix shape/counts, SciPy reference matching, pairwise exclusions, cell-level failures, invalid inputs, canonical-row execution after raw mutation, stored result retrieval, and row snapshot provenance.
- Added frontend API types and `XyCorrelationPanel` with X/Y checkbox sets, alpha, confidence level, warnings, pair-level result table, and failed-cell error display.
- Added beginner-oriented guidance for X-Y correlation and a regression test proving analysis errors do not render through the dataset-preparation top error box on analysis routes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/xy_correlation.py`
- `backend/tests/reference/fixtures/xy_correlation_input.json`
- `backend/tests/reference/fixtures/xy_correlation_scipy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_xy_correlation.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/WorkspaceRouter.tsx`
- `frontend/src/XyCorrelationPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/analysisRunErrors.ts`
- `frontend/src/App.test.tsx`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_xy_correlation.py` and `test_api_contracts.py`: passed with 39 tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 52 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 32 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 154 tests, frontend Vitest 32 tests, and frontend build.

Remaining limitations:

- X-Y correlation currently supports Pearson only.
- Holm/BH adjusted p-values, Spearman/Kendall, scatterplot artifacts, and generated chart rendering remain out of scope.
- OLS model fitting, model manifests, prediction, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.
- Browser automation was not run in this slice; coverage is from unit/API/Vitest/full script checks.

Next PR:

- Start a safe OLS model-fitting contract slice, or add X-Y correlation p-value adjustment and scatterplot artifact contracts before implementation.
- Keep every new statistical method tied to a method contract, reference fixture, canonical row source, persisted result retrieval, and no mock result policy.

## Progress Update 35 - Linear Model OLS Executable Slice

Completed in current working tree:

- Made `regression.linear_model` available as the third narrow Gate C1 executable slice.
- Added `backend/app/statistics/linear_model.py` with real NumPy/SciPy-backed OLS for one numeric response and one or more numeric main-effect predictors from canonical rows.
- Added complete-case exclusion counts, coefficient estimates, standard errors, t statistics, p-values, t-based confidence intervals, R², adjusted R², residual standard error, F test, VIF, condition number, residual/leverage/Cook's distance diagnostics, capped diagnostic points, and persistent assumption/non-causation warnings.
- Added stable backend errors for invalid alpha/confidence level, missing predictors, insufficient residual degrees of freedom, constant response/predictor columns, rank-deficient design, zero residual variance, and non-finite standard errors.
- Added OLS reference fixtures:
  - `backend/tests/reference/fixtures/linear_model_input.json`
  - `backend/tests/reference/fixtures/linear_model_numpy_reference.json`
- Added backend domain and API tests for hand-checkable fit shape, NumPy reference matching, residual/leverage/Cook's distance diagnostics, complete-case exclusions, invalid inputs, canonical-row execution after raw mutation, stored result retrieval, and row snapshot provenance.
- Added frontend API types and `LinearModelPanel` with response selection, predictor checkbox set, alpha, confidence level, explanatory copy, warnings, fit summary, coefficient table, diagnostic summary, and top diagnostic-point table.
- Updated analysis guidance and error details so common regression setup failures explain the cause and next action without hiding stable error codes.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/linear_model.py`
- `backend/tests/reference/fixtures/linear_model_input.json`
- `backend/tests/reference/fixtures/linear_model_numpy_reference.json`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_linear_model.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/analysisRunErrors.ts`
- `frontend/src/App.test.tsx`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Targeted backend pytest for `test_linear_model.py` and `test_api_contracts.py`: passed with 40 tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 53 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 159 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Linear model currently supports numeric main-effect OLS only.
- Categorical factors, interactions, polynomial terms, no-intercept models, HC3 robust covariance, diagnostic chart artifacts, model manifest storage, prediction, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.
- The current OLS result is persisted as an analysis result envelope, not as a reusable model asset.

Next PR:

- Add a safe OLS term-builder/model-contract slice for categorical factors and interaction planning, or continue Gate C1 with diagnostic chart artifact contracts before implementing prediction.
- Keep model manifest and prediction disabled until app-created model artifacts are designed, hashed, tested, and schema-drift checked.

## Progress Update 36 - Linear Model Diagnostic Payload Slice

Completed in current working tree:

- Extended `regression.linear_model` result schema to version `2`.
- Added residual summary, leverage summary, Cook's distance summary, large-residual/high-leverage/high-Cook warning codes, and capped row-level diagnostic points with only row index plus derived fitted/residual/leverage/Cook values.
- Kept raw input cell values out of diagnostic point payloads and capped UI payload size while computing diagnostic summaries over all complete-case rows.
- Updated the stored NumPy reference fixture, backend domain/API assertions, frontend API type, and `LinearModelPanel` diagnostic display.
- Updated `docs/linear_model_method_contract.md`, six-module guidance, Gate progress, and this task list to clarify that diagnostic payloads exist while diagnostic chart artifacts, model manifests, and prediction remain out of scope.

Changed files:

- `backend/app/statistics/linear_model.py`
- `backend/app/services/analysis_runs.py`
- `backend/tests/reference/fixtures/linear_model_numpy_reference.json`
- `backend/tests/unit/test_linear_model.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/App.test.tsx`
- `docs/linear_model_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_linear_model.py` and `test_api_contracts.py`: passed with 40 tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 53 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 159 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Linear model still supports numeric main-effect OLS only.
- Categorical factors, interactions, polynomial terms, no-intercept models, HC3 robust covariance, diagnostic chart artifacts, model manifest storage, prediction, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.

Next PR:

- Continue Gate C1 with a safe OLS term-builder/model-contract slice for categorical factors/interactions, or add diagnostic chart artifact contracts before prediction.
- Keep model manifest and prediction disabled until app-created model artifacts are designed, hashed, tested, and schema-drift checked.

## Progress Update 37 - Linear Model Safe Factor Main-Effects Slice

Completed in current working tree:

- Extended `regression.linear_model` result schema to version `3`.
- Added a safe OLS design matrix/term builder that preserves existing numeric main-effect behavior and supports categorical main-effect predictors through deterministic treatment coding.
- Categorical predictors use the first sorted observed complete-case level as the reference, emit `categorical_main_effect` model specification metadata, and return coefficient-level `level`, `reference_level`, and `coding` fields.
- Added stable failures for unsupported predictor types, single-level factors, and excessive factor levels rather than returning fake coefficients.
- Updated API validation so response columns remain numeric while predictor columns may be numeric or categorical factor candidates.
- Updated the frontend linear model panel, typed API contract, method guidance, and error explanations for categorical factor predictors.

Changed files:

- `backend/app/statistics/linear_model.py`
- `backend/app/services/analysis_runs.py`
- `backend/tests/unit/test_linear_model.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/analysisRunErrors.ts`
- `frontend/src/App.test.tsx`
- `docs/linear_model_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_linear_model.py` and `test_api_contracts.py`: passed with 42 tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 53 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 161 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Linear model still supports main effects only.
- Interactions, polynomial terms, no-intercept models, HC3 robust covariance, diagnostic chart artifacts, model manifest storage, prediction, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.

Next PR:

- Continue Gate C1 with interaction/polynomial term-builder contracts or safe app-created model manifest storage.
- Keep prediction disabled until model artifacts are designed, hashed, tested, and schema-drift/extrapolation checks exist.

## Progress Update 38 - Linear Model Numeric Extra-Term Slice

Completed in current working tree:

- Extended `regression.linear_model` result schema to version `4`.
- Added explicit `quadratic_terms` and `interaction_terms` analysis options for selected numeric predictors.
- Added safe numeric 2차항 and numeric-by-numeric interaction columns to the existing OLS term builder without using formulas, `eval`, or arbitrary Python.
- Added `source_column_ids` to coefficient and model term payloads so generated terms remain reproducible.
- Added stable failures for invalid/duplicate extra-term requests, unselected term predictors, non-numeric term predictors, constant quadratic terms, and constant interaction terms.
- Added API and frontend controls for selecting numeric 2차항 and numeric interactions from currently selected numeric predictors.
- Kept categorical interactions, factor-by-numeric interactions, arbitrary formulas, no-intercept, robust covariance, model manifest storage, and prediction out of scope.

Changed files:

- `backend/app/statistics/linear_model.py`
- `backend/app/services/analysis_runs.py`
- `backend/tests/unit/test_linear_model.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/analysisRunErrors.ts`
- `frontend/src/App.test.tsx`
- `docs/linear_model_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_linear_model.py` and `test_api_contracts.py`: passed with 44 tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 53 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 163 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Linear model still does not support categorical interactions, factor-by-numeric interactions, arbitrary formulas, no-intercept models, HC3 robust covariance, diagnostic chart artifacts, model manifest storage, prediction, response optimizer, quality control, DOE, or Bayesian optimization.

Next PR:

- Continue Gate C1 with safe app-created model manifest storage.
- Keep prediction disabled until model artifacts are designed, hashed, tested, and schema-drift/extrapolation checks exist.

## Progress Update 39 - Linear Model Prediction Preflight Slice

Completed in current working tree:

- Added stored app-created OLS model prediction preflight through `POST /api/v1/regression-models/{model_id}/prediction-preflight`.
- The preflight validates the stored manifest checksum, source dataset version, source row snapshot, target dataset version, and target canonical rows before returning readiness.
- Required predictor columns map by exact `column_id` first, then by a one-to-one `display_name` fallback with a warning.
- Numeric predictors report missing, non-numeric, below-training-range, and above-training-range counts.
- Categorical predictors report training level count, missing count, and unseen-level count.
- The endpoint returns structured warning/error issues and `row_count_usable` but does not calculate prediction values, intervals, or prediction artifacts.
- Added frontend API types and a typed client function for the preflight endpoint; no large prediction UI was added in this slice.
- Updated linear-model, storage, six-module, and progress documentation to distinguish preflight from actual prediction.

Changed files:

- `backend/app/api/v1/schemas/analyses.py`
- `backend/app/api/v1/regression_models.py`
- `backend/app/services/regression_models.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `docs/linear_model_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `docs/storage.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_api_contracts.py -k regression_prediction_preflight`: passed with 2 tests.
- Backend ruff for touched regression-model files and `test_api_contracts.py`: passed.
- Backend mypy for `backend/app`: passed with 55 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 168 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Actual prediction values, mean response confidence intervals, individual prediction intervals, prediction result artifacts, and prediction UI are still not implemented.
- Categorical interactions, factor-by-numeric interactions, arbitrary formulas, no-intercept models, HC3 robust covariance, diagnostic chart artifacts, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.

Next PR:

- Superseded by Progress Update 40 for the frontend preflight UI and prediction contract.
- Surface the prediction-preflight result in the UI near the stored model result.
- Write the actual prediction result contract before implementing design-matrix reconstruction, prediction intervals, and prediction artifact persistence.

## Progress Update 40 - Linear Model Prediction Preflight UI And Contract Slice

Completed in current working tree:

- Added a Linear Model result-panel action for running stored-model prediction preflight against the current dataset version.
- Rendered prediction preflight readiness, usable/total row counts, schema-hash match state, warning/error counts, required predictor mapping, numeric missing/non-numeric/extrapolation counts, and categorical unseen-level counts.
- Kept preflight failures local to the Linear Model result panel instead of routing them through the dataset-preparation top error.
- Reset preflight display automatically when the active model ID or dataset version changes.
- Added `docs/regression_prediction_contract.md` to define the next actual prediction endpoint, validation, interval, storage, and test requirements before prediction values are enabled.
- Kept prediction values, prediction intervals, prediction artifacts, and prediction execution UI disabled.

Changed files:

- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/regression_prediction_contract.md`
- `docs/linear_model_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/check.ps1`: passed with backend pytest 168 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Actual prediction values, confidence intervals, prediction intervals, prediction artifact persistence, and paged prediction result retrieval are still not implemented.
- The preflight UI currently targets the active dataset version; selecting a different prediction target dataset version is a later UI step.
- Categorical interactions, factor-by-numeric interactions, robust covariance, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.

Next PR:

- Add backend prediction manifest metadata required for valid intervals, or explicitly gate interval-less prediction with a stable recovery error if the manifest is insufficient.
- Implement actual prediction only after `docs/regression_prediction_contract.md` requirements have backend reference fixtures and API tests.

## Progress Update 41 - Linear Model Backend Prediction Slice

Completed in current working tree:

- Extended app-created OLS model manifests to `manifest_schema_version=2` with a `prediction_basis` containing coefficient order, inverse cross-product matrix, residual variance, and residual degrees of freedom.
- Kept the large prediction basis out of the user-facing `regression.linear_model` result envelope; the result still exposes only the model-manifest pointer and checksum.
- Added `POST /api/v1/regression-models/{model_id}/predictions` for backend batch predictions from app-created OLS manifests.
- The prediction endpoint reuses the preflight validation path and rejects error-severity preflight issues with `regression_prediction_preflight_failed`.
- Prediction reconstructs the stored design matrix for numeric main effects, categorical treatment-coded factors, numeric quadratic terms, and numeric-by-numeric interactions.
- Prediction returns capped rows with target row index, predicted mean, mean-response confidence interval, individual prediction interval, row warning codes, exclusion counts, warning metadata, and provenance without raw input cell values.
- Stored prediction results are persisted as `regression.predict` analysis result envelopes with SHA-256 validation compatibility through the existing analysis-run result API.
- Prediction result files are removed if metadata insert fails after the file write.

Changed files:

- `backend/app/statistics/linear_model.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/services/regression_models.py`
- `backend/app/api/v1/regression_models.py`
- `backend/app/api/v1/schemas/analyses.py`
- `backend/tests/unit/test_api_contracts.py`
- `docs/regression_prediction_contract.md`
- `docs/linear_model_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `docs/storage.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_api_contracts.py -k "linear_model or regression_prediction"`: passed with 8 tests.
- Backend ruff format/check for touched backend files and `test_api_contracts.py`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 170 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- The frontend still shows prediction preflight only; it does not yet execute or render prediction rows.
- Prediction response rows are capped at 1,000 inline rows; separate paged result retrieval is not implemented.
- Dedicated prediction reference fixtures for categorical, quadratic, interaction, artifact checksum mismatch, and insufficient uncertainty metadata are still pending.
- Spearman/Kendall, categorical interactions, factor-by-numeric interactions, robust covariance, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.

Next PR:

- Add the minimal frontend prediction execution/result display for app-created OLS models, or add the remaining backend prediction reference/recovery tests before exposing the UI button.

## Progress Update 42 - Linear Model Prediction UI Slice

Completed in current working tree:

- Added frontend API types and `fetchRegressionPredictions` for `POST /api/v1/regression-models/{model_id}/predictions`.
- Added Linear Model prediction execution state, local error state, and reset behavior in `App.tsx`.
- Wired prediction execution through `AnalysisShell` into `LinearModelPanel`.
- The Linear Model panel now enables `예측 실행` only after the stored-model preflight is ready for the active dataset version and model ID.
- Rendered prediction warnings, prediction ID, predicted/total/excluded/omitted counts, confidence level, inline row cap, and a capped row table with row index, predicted mean, mean-response CI, individual prediction interval, and row warning codes.
- Kept raw target cell values out of the prediction UI and kept the warning text explicit that predictions are model-based estimates, not causal effects.
- Extended the frontend SSR test fixture to cover prediction execution UI rendering and manifest schema version `2`.
- Added backend API coverage for prediction result checksum mismatch, categorical treatment-coded prediction reconstruction, numeric quadratic/interaction prediction reconstruction, and missing prediction-basis recovery.

Changed files:

- `frontend/src/api.ts`
- `frontend/src/App.tsx`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/App.test.tsx`
- `backend/tests/unit/test_api_contracts.py`
- `docs/regression_prediction_contract.md`
- `docs/linear_model_method_contract.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 173 tests, frontend Vitest 33 tests, and frontend build.
- Targeted backend `test_api_contracts.py -k "regression_prediction"`: passed with 7 tests.
- `git diff --check`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 173 tests, frontend Vitest 33 tests, and frontend build.

Remaining limitations:

- Prediction UI currently targets the active dataset version only; selecting another confirmed dataset version as the target is not implemented.
- Prediction table displays only the first 25 inline rows; backend inline response is capped at 1,000 rows and paged retrieval is not implemented.
- Dedicated independent reference fixtures for prediction intervals and broader schema/unseen/missing/extrapolation recovery matrix are still pending.
- Spearman/Kendall, categorical interactions, factor-by-numeric interactions, robust covariance, response optimizer, quality control, DOE, and Bayesian optimization remain out of scope.

Next PR:

- Add prediction target dataset selection plus paged result retrieval, or first add the remaining backend prediction reference/recovery tests.

## Progress Update 43 - Graphical Summary Inline Chart Renderer Slice

Completed in current working tree:

- Confirmed `eda.graphical_summary` already computes real histogram, boxplot, Q-Q, and ECDF chart-data payloads; the missing part was frontend chart rendering.
- Added inline SVG rendering in `GraphicalSummaryPanel` for histogram, box plot, Q-Q plot, and ECDF from the existing backend result payload.
- Kept the numeric summary table under the charts so exact values remain inspectable.
- Added responsive chart layout CSS without adding a chart dependency or CDN.
- Extended the frontend SSR test fixture so the graphical summary result renders the chart section and chart titles.
- Added a near-term visualization plan for other result payloads that can be safely visualized without fake charts.

Changed files:

- `frontend/src/GraphicalSummaryPanel.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Frontend `npm --prefix ./frontend run lint`: passed.

Remaining limitations:

- Grouped graphical summaries, KDE, density rendering, chart exports, and small-multiple UI are still not implemented.
- Other analysis panels remain mostly table/text based until their real chart payloads are rendered in separate slices.
- This slice does not add new statistical calculations.

Next PR:

- Add visualization for `eda.normality` Q-Q plot or `regression.pearson` scatter plot from existing result payloads.
- For methods that do not yet return chart-ready data, add tested result payloads before rendering charts.

## Progress Update 44 - Normality, Pearson, And X-Y Visualization Slice

Completed in current working tree:

- Added inline SVG Q-Q plot rendering to `NormalityAnalysisPanel` from the existing `eda.normality` Q-Q point payload.
- Added a capped, deterministic, raw-string-free Pearson scatterplot payload to `regression.pearson` results.
- Added inline SVG scatter plot rendering to `PearsonCorrelationPanel` from the new capped scatter payload.
- Added an X-Y Pearson correlation heatmap to `XyCorrelationPanel` from existing pairwise r values.
- Kept exact numeric result tables under the visual sections so values remain inspectable.
- Added frontend SSR fixtures and assertions for the new Q-Q, scatter, and heatmap result sections.
- Added backend Pearson tests for scatter payload shape, cap behavior, and no row identity.
- Updated the Pearson method contract and Gate/6-module progress docs.

Changed files:

- `backend/app/statistics/pearson.py`
- `backend/tests/unit/test_pearson.py`
- `backend/tests/unit/test_api_contracts.py`
- `frontend/src/api.ts`
- `frontend/src/NormalityAnalysisPanel.tsx`
- `frontend/src/PearsonCorrelationPanel.tsx`
- `frontend/src/XyCorrelationPanel.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/pearson_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Targeted backend pytest for `test_pearson.py` and `test_api_contracts.py -k "pearson"`: passed with 6 selected tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Frontend `npm --prefix ./frontend run build`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 174 tests, frontend Vitest 33 tests, frontend lint/typecheck, and frontend build.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 174 tests, frontend Vitest 33 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- The Pearson scatter payload is capped at 500 points and is for result visualization, not a separate chart artifact/export.
- Normality grouped plots, graphical summary grouping/small multiples, and downloadable chart artifacts remain out of scope.
- X-Y heatmap uses pairwise Pearson r only; Spearman/Kendall and p-value adjustment remain out of scope.
- No new statistical method was added in this slice.

Next PR:

- Add chart renderers for linear-model diagnostics/residuals or chi-square residual heatmap from existing real payloads, then continue with the next planned Gate C/D method only after reference tests and result contracts are ready.

## Progress Update 45 - Chi-Square, Linear Model, And Prediction Chart Slice

Completed in current working tree:

- Added a standardized residual heatmap to `ChiSquareAssociationPanel` using existing observed, expected, and standardized residual payload fields.
- Added linear-model diagnostic charts to `LinearModelPanel`:
  - residuals vs fitted
  - leverage vs Cook's D with existing threshold metadata
- Added a prediction interval chart to `LinearModelPanel` using existing predicted mean, mean CI, and prediction interval rows.
- Reused the local inline SVG chart style without adding chart dependencies, CDN calls, or generated fake chart values.
- Extended frontend SSR fixtures/assertions for chi-square heatmap, regression diagnostic charts, and prediction interval chart rendering.

Changed files:

- `frontend/src/ChiSquareAssociationPanel.tsx`
- `frontend/src/LinearModelPanel.tsx`
- `frontend/src/App.css`
- `frontend/src/App.test.tsx`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 33 tests.
- Frontend `npm --prefix ./frontend run build`: passed.

Remaining limitations:

- These are inline UI renderers only; static chart artifact export is still out of scope.
- Chi-square Fisher exact p-value, residual export, and aggregate-count contingency input remain out of scope.
- Linear-model robust covariance, categorical interactions, and additional diagnostic exports remain out of scope.
- Prediction target dataset selection and paged prediction result retrieval remain out of scope.

Next PR:

- After committing this accumulated vertical-slice work, choose either a small chart-export/reporting contract or the first Gate D quality-control method with real reference tests.

## Progress Update 46 - Run Chart Executable Quality Slice

Completed in current working tree:

- Made `quality.run_chart` available in the analysis method registry as the first narrow Gate D quality-control slice.
- Added `backend/app/statistics/run_chart.py` with a real stdlib median run chart calculation for one numeric measurement column.
- The backend reads canonical rows through the existing row snapshot path, persists result JSON, and stores row snapshot provenance.
- Result payload includes complete-case exclusion counts, median center line, above/below median run count, tie-to-median exclusion policy, strict 6-point trend signal metadata, and capped chart points.
- The method explicitly does not compute control limits and does not represent trend signals as control-chart out-of-control violations.
- Added frontend API types and `RunChartPanel` with measurement selector, canonical row order policy display, inline SVG run chart, run count summary, and signal table.
- Updated method guidance and docs with the current contract and limitations.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/run_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_run_chart.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/RunChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/run_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation:

- Backend targeted pytest for `test_run_chart.py` and selected run-chart/catalog API contracts: passed with 7 selected tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for touched backend files: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 34 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 178 tests, frontend Vitest 34 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Run chart supports canonical row order and optional numeric order columns only; datetime order parsing remains out of scope.
- Strict monotonic trend and strict alternating oscillation signals are implemented; clustering and mixture signal definitions remain out of scope.
- Control limits, I-MR, Xbar charts, capability analysis, and Gage methods remain planned.
- Inline chart rendering is not a chart export artifact.

Next PR:

- Define the next run-chart signal contract or implement the next small quality method only after its result contract and reference fixtures are ready.

## Progress Update 47 - Run Chart Numeric Order Column Slice

Completed in current working tree:

- Extended `quality.run_chart` to accept an optional numeric `order_column_id`.
- Numeric order columns are sorted ascending, with canonical row position as the deterministic tie-breaker.
- Result payload now records order column metadata, order-source policy, order tie-breaker, order missing/non-numeric exclusions, and order duplicate count.
- Chart payload uses `order_rank` when an order column is selected and does not expose raw order values or source paths.
- Frontend `RunChartPanel` now exposes an order selector, displays the chosen order policy, and shows order exclusion/tie counts.
- No control limits, fake signals, or new statistical methods were added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/run_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_run_chart.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/RunChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/run_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_run_chart.py` and selected run-chart API contracts: passed with 8 selected tests.
- Backend ruff for touched backend files: passed.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run lint`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 34 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 182 tests, frontend Vitest 34 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Strict monotonic trend and strict alternating oscillation signals are implemented; clustering and mixture signal definitions remain out of scope.
- Control limits, I-MR, Xbar charts, capability analysis, and Gage methods remain planned.
- Inline chart rendering is not a chart export artifact.

Next PR:

- Define the next run-chart signal contract or implement the next small quality-control slice only after its method contract and reference fixtures are ready.

## Progress Update 48 - Run Chart Oscillation Signal Slice

Completed in current working tree:

- Added a real `run_chart_oscillation` signal to `quality.run_chart`.
- The oscillation signal is strictly defined as consecutive point-to-point directions alternating between increasing and decreasing for at least the configured minimum number of points.
- Default oscillation rule length is 14 points; API accepts `oscillation_min_length` from 4 to 30.
- Equal adjacent values break the oscillation sequence; no fallback or fake signal is emitted.
- Result payload now includes `oscillation_rule`, and chart points can carry `run_chart_oscillation` signal codes.
- Frontend Run Chart UI now shows the oscillation rule, separate trend/oscillation signal counts, and signal-code-aware chart tooltips.
- No control limits, Nelson/Western Electric rules, clustering/mixture signals, or new quality method were added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/run_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_run_chart.py`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/RunChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/run_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_run_chart.py` and selected run-chart API contracts: passed with 12 selected tests.
- Backend ruff for touched backend files: passed.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 34 tests.
- Frontend `npm --prefix frontend run lint`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 186 tests, frontend Vitest 34 tests, frontend lint/typecheck, and frontend build. The first full-check attempt stopped on backend ruff format for `backend/app/services/analysis_runs.py`; after running ruff format, the full check passed.

Remaining limitations:

- Clustering and mixture signal definitions remain out of scope.
- Control limits, Nelson/Western Electric control-chart rules, I-MR, Xbar charts, capability analysis, and Gage methods remain planned.
- Inline chart rendering is not a chart export artifact.

Next PR:

- Define the next run-chart signal contract or implement the next small quality-control method only after its result contract and reference fixtures are ready.

## Progress Update 49 - Run Chart Datetime Order Column Slice

Completed in current working tree:

- Extended `quality.run_chart` order-column support from numeric-only to numeric or datetime order columns.
- Datetime order columns are sorted ascending with canonical row position as the deterministic tie-breaker.
- Supported datetime parsing follows the dataset profile preflight slice: ISO 8601 plus common date/time formats such as `YYYY-MM-DD`, slash/dot dates, and minute/second timestamps.
- Timezone-aware datetime values are normalized to UTC for ordering.
- Mixed timezone-aware and timezone-naive order values are rejected with `run_chart_order_mixed_timezone_awareness` instead of imposing an ambiguous order.
- Invalid datetime order values are excluded under complete-case handling and emit `run_chart_order_invalid_datetime_excluded`.
- Result payload now records `order_source: datetime_order_column_ascending` and `order_timezone`, while chart payloads continue to expose only order rank plus canonical position and not raw datetime values.
- Frontend order-column selection now includes datetime columns and labels datetime order results.
- No control limits, fake signals, clustering/mixture signals, or new quality method were added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/run_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_run_chart.py`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/RunChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/run_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_run_chart.py` and selected run-chart API contracts: passed with 17 selected tests.
- Backend ruff for touched backend files: passed.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 34 tests.
- Frontend `npm --prefix frontend run lint`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 191 tests, frontend Vitest 34 tests, frontend lint/typecheck, and frontend build. The first full-check attempt stopped on backend mypy for datetime duplicate-count typing in `backend/app/statistics/run_chart.py`; after widening the helper type and rerunning targeted mypy/pytest, the full check passed.

Remaining limitations:

- Clustering and mixture signal definitions remain out of scope.
- Control limits, Nelson/Western Electric control-chart rules, I-MR, Xbar charts, capability analysis, and Gage methods remain planned.
- Inline chart rendering is not a chart export artifact.

Next PR:

- Define the next run-chart signal contract or implement the next small quality-control method only after its result contract and reference fixtures are ready.

## Progress Update 50 - Run Chart Exact Run-Count Signal Slice

Completed in current working tree:

- Added exact conditional run-count testing to `quality.run_chart` for clustering and mixture signals.
- `run_chart_clustering` is emitted when the observed above/below median run count is in the low exact tail at `runs_test_alpha`.
- `run_chart_mixture` is emitted when the observed above/below median run count is in the high exact tail at `runs_test_alpha`.
- Default `runs_test_alpha` is `0.05`; API rejects non-finite values and values outside `0 < alpha < 0.5` with `invalid_run_chart_runs_test_alpha`.
- Result payload now includes `runs_test` with observed run count, above/below/tie counts, expected run count, variance, low/high tail p-values, interpretation, skip reason, and max exact calculation limit.
- Exact run-count testing excludes values tied to the median; if one side is absent or the non-tie count exceeds 5000, the result records `available=false` and does not create a fallback signal.
- Frontend Run Chart UI now displays the exact runs-test policy, low/high tail p-values, and separate clustering/mixture signal counts.
- No control limits, Nelson/Western Electric rules, normal approximation fallback, fake signals, or new quality method were added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/run_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_run_chart.py`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/RunChartPanel.tsx`
- `frontend/src/api.ts`
- `docs/run_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_run_chart.py` and selected run-chart API contracts: passed with 22 selected tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 56 source files.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run lint`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 34 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 196 tests, frontend Vitest 34 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Exact clustering/mixture signals are capped at 5000 non-tie points; larger inputs record an explicit unavailable result rather than using an approximation.
- Run Chart still does not compute control limits or control-chart out-of-control rules.
- I-MR, Xbar charts, capability analysis, Gage methods, chart export artifacts, and paged chart payloads remain planned.

Next PR:

- Start the next small quality-control slice only after choosing between I-MR/control-chart rule foundation and capability-analysis contract work, with reference fixtures ready first.

## Progress Update 51 - Individuals Chart First I-MR Slice

Completed in current working tree:

- Made `quality.individuals_chart` available as the first Gate D I-MR slice.
- Added stdlib I-MR calculation for one numeric measurement column from canonical rows.
- Uses canonical row order, complete-case exclusions, arithmetic mean center line, adjacent moving ranges of length 2, `MRbar / d2` sigma estimate, I chart 3-sigma limits, and MR chart `D3/D4` limits.
- Emits `individuals_chart_i_beyond_3_sigma` and `individuals_chart_mr_beyond_ucl` for the first P0 single-point limit signals.
- Rejects all-zero moving ranges with `individuals_chart_zero_moving_range` instead of fabricating limits.
- Persists the result envelope and row snapshot through the existing analysis run path.
- Added frontend `IndividualsChartPanel` with value selector, inline SVG I/MR charts, limit table, and signal table.
- No fake limits/signals, full Nelson/Western Electric rules, subgroup charts, capability analysis, Gage R&R, or export artifacts were added.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/individuals_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_individuals_chart.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/IndividualsChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/individuals_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_individuals_chart.py` and selected individuals-chart API contracts: passed with 8 selected tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 57 source files.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run lint`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 35 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 203 tests, frontend Vitest 35 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Current execution order is canonical row order only in this slice; numeric/datetime order-column support is added in Progress Update 52.
- In this slice, control rules only covered first single-point I/MR limit checks; same-side/trend rules are added in Progress Update 53.
- Subgroup charts, capability analysis, Gage R&R, paged chart payloads, and chart export artifacts remain planned.

Next PR:

- Superseded by Progress Update 52 for order-column support; the next remaining path is a tested control-rule slice after its statistical contract and fixtures are ready.

## Progress Update 52 - Individuals Chart Order Column Slice

Completed in current working tree:

- Extended `quality.individuals_chart` from canonical-only order to optional numeric or datetime order columns.
- Numeric and datetime order columns sort ascending and use canonical row position as the deterministic tie-breaker.
- Datetime order parsing follows the Run Chart/profile preflight policy: ISO 8601 plus common date/time formats, timezone-aware values normalized to UTC for comparison, and mixed timezone-aware/timezone-naive values rejected with `individuals_chart_order_mixed_timezone_awareness`.
- Result payload now records order column metadata, `order_source`, `order_tie_breaker`, `order_timezone`, order missing/non-numeric exclusions, and duplicate order count without exposing raw order values.
- I chart and MR chart payloads now include `x_axis` and use `order_rank` when an order column is selected.
- Frontend `IndividualsChartPanel` now includes an order-column selector and displays the selected order policy in the result summary.
- No Nelson/Western Electric rules, subgroup charts, capability analysis, Gage R&R, chart export artifact, or fake signal fallback was added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/individuals_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_individuals_chart.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/IndividualsChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/individuals_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_individuals_chart.py` and selected individuals-chart API contracts: passed with 15 selected tests.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 211 tests, frontend Vitest 35 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- In this slice, control rules only covered first single-point I/MR limit checks; same-side/trend rules are added in Progress Update 53.
- Subgroup charts, capability analysis, Gage R&R, paged chart payloads, and chart export artifacts remain planned.

Next PR:

- Implement the next tested control-rule slice for `quality.individuals_chart`, or start a narrow subgroup/capability contract only after reference fixtures are ready.

## Progress Update 53 - Individuals Chart Centerline And Trend Rule Slice

Completed in current working tree:

- Added two explicit I chart rule signals to `quality.individuals_chart`.
- `individuals_chart_i_same_side_centerline` is emitted for at least `same_side_min_length` consecutive I-chart points strictly above or strictly below the center line.
- `individuals_chart_i_trend` is emitted for at least `trend_min_length` consecutive I-chart points that are strictly increasing or strictly decreasing.
- Defaults are `same_side_min_length=9` and `trend_min_length=6`; API rejects invalid lengths with stable error codes.
- Center-line ties break the same-side run; equal adjacent values break trend runs.
- Range signals are attached to every chart point in the detected range through `signal_codes`.
- Frontend signal tables now display point ranges plus direction/length for range-based signals.
- No full Nelson/Western Electric rule set, subgroup charts, capability analysis, Gage R&R, chart export artifact, or fake signal fallback was added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/individuals_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_individuals_chart.py`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/IndividualsChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/individuals_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_individuals_chart.py` and selected individuals-chart API contracts: passed with 19 selected tests.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 35 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 215 tests, frontend Vitest 35 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Full Nelson/Western Electric rule sets remain out of scope; only the explicitly listed same-side/trend I-chart rules are implemented.
- Subgroup charts, capability analysis, Gage R&R, paged chart payloads, and chart export artifacts remain planned.

Next PR:

- Add the next explicitly specified control-rule slice or start a narrow subgroup/capability contract with reference fixtures.

## Progress Update 54 - Individuals Chart Zone Rule Slice

Completed in current working tree:

- Added two explicit I chart zone rule signals to `quality.individuals_chart`.
- `individuals_chart_i_two_of_three_beyond_2_sigma` is emitted for at least two of three consecutive I-chart points beyond 2 sigma on the same side of the center line.
- `individuals_chart_i_four_of_five_beyond_1_sigma` is emitted for at least four of five consecutive I-chart points beyond 1 sigma on the same side of the center line.
- Zone-rule signal payloads record window start/end, qualifying point positions, qualifying canonical positions, count, window length, direction, and sigma multiple.
- Chart point `signal_codes` mark only qualifying threshold-crossing points inside the evaluated window, not every point in the window.
- Frontend signal tables now display zone-rule direction, count/window length, and sigma multiple.
- No full Nelson/Western Electric rule set, subgroup charts, capability analysis, Gage R&R, chart export artifact, or fake signal fallback was added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/individuals_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_individuals_chart.py`
- `frontend/src/App.test.tsx`
- `frontend/src/IndividualsChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/individuals_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_individuals_chart.py` and selected individuals-chart API contracts: passed with 22 selected tests.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 35 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 218 tests, frontend Vitest 35 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Full Nelson/Western Electric rule sets remain out of scope; only explicitly listed I chart limit, same-side, trend, and zone rules are implemented.
- Subgroup charts, capability analysis, Gage R&R, paged chart payloads, and chart export artifacts remain planned.

Next PR:

- Either add the next explicitly specified control-rule slice or start a narrow subgroup/capability contract with reference fixtures.

## Progress Update 55 - Individuals Chart Extended Pattern Rule Slice

Completed in current working tree:

- Added three explicit I chart pattern signals to `quality.individuals_chart`.
- `individuals_chart_i_alternating` is emitted for 14 consecutive I-chart points with strictly alternating adjacent directions.
- `individuals_chart_i_fifteen_within_1_sigma` is emitted for 15 consecutive I-chart points within 1 sigma of the center line.
- `individuals_chart_i_eight_outside_1_sigma` is emitted for 8 consecutive I-chart points outside 1 sigma of the center line on either side.
- Pattern signal payloads record window start/end, point positions, canonical positions, count, window length, direction, and sigma multiple where applicable.
- Chart point `signal_codes` mark every point in the alternating/within/outside qualifying pattern window.
- Frontend signal tables accept and display `alternating`, `within`, and `outside` directions.
- No new statistical method, full Nelson/Western Electric rule claim, subgroup chart, capability analysis, Gage R&R, chart export artifact, or fake signal fallback was added.

Changed files:

- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/individuals_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_individuals_chart.py`
- `frontend/src/App.test.tsx`
- `frontend/src/IndividualsChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/individuals_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_individuals_chart.py` and selected individuals-chart API contracts: passed with 26 selected tests.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 35 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 222 tests, frontend Vitest 35 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Full Nelson/Western Electric rule sets remain out of scope; only explicitly listed I chart limit, same-side, trend, alternating, and zone/pattern rules are implemented.
- Subgroup charts, capability analysis, Gage R&R, paged chart payloads, and chart export artifacts remain planned.

Next PR:

- Start the next narrow Gate D quality method slice, likely subgroup chart contract/preflight, or add capability-analysis requirements only after reference fixtures are ready.

## Progress Update 56 - Subgroup Chart Xbar-R/Xbar-S Fixed-Subgroup Slice

Completed in current working tree:

- Made `quality.subgroup_chart` available as the Gate D fixed-subgroup chart slice.
- Added stdlib Xbar-R and Xbar-S calculation for one numeric measurement column and one subgroup ID column.
- Uses canonical row first-seen subgroup order, complete-case exclusions, fixed subgroup size 2-10, standard `A2/D3/D4` Xbar-R constants, standard `A3/B3/B4` Xbar-S constants, Xbar center, R/S center, and Xbar/R/S control limits.
- Emits `subgroup_chart_xbar_beyond_control_limits`, `subgroup_chart_r_beyond_control_limits`, and `subgroup_chart_s_beyond_control_limits` for first-slice single-point limit signals.
- Rejects varying subgroup sizes with `subgroup_chart_varying_subgroup_size_unsupported`.
- Rejects all-zero average subgroup range with `subgroup_chart_zero_average_range` instead of fabricating limits.
- Rejects all-zero average subgroup sample standard deviation with `subgroup_chart_zero_average_stddev` instead of fabricating limits.
- Added frontend `SubgroupChartPanel` with value/subgroup selectors, Xbar-R/Xbar-S selector, inline SVG Xbar/R/S charts, limit table, and signal table.
- No varying-size limits, full Nelson/Western Electric rule set, capability analysis, Gage R&R, chart export artifact, or fake signal fallback was added.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/subgroup_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_subgroup_chart.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/SubgroupChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `docs/subgroup_chart_method_contract.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_subgroup_chart.py` and selected subgroup-chart API contracts: passed with 10 selected tests.
- Frontend `npm --prefix frontend run typecheck`: passed.
- Frontend `npm --prefix frontend run test -- --run`: passed with 36 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"` passed with backend pytest 232 tests, frontend Vitest 36 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Varying subgroup-size Xbar-R/Xbar-S limits remain out of scope.
- Full Nelson/Western Electric rule sets, attribute charts, capability analysis, Gage R&R, paged chart payloads, and chart export artifacts remain planned.

Next PR:

- Add the next narrow Gate D quality slice: either varying-size subgroup chart contract work or the first capability-analysis preflight slice, only after reference fixtures are ready.

## Progress Update 57 - Capability Normal First Slice

Completed in current working tree:

- Made `quality.capability` available as the first Gate D normal capability slice.
- Added stdlib normal capability calculation for one numeric measurement column.
- Requires LSL and/or USL, accepts optional target, and rejects invalid spec ordering or target outside spec.
- Uses complete-case exclusions, overall sample standard deviation, and within sigma from canonical adjacent moving range `MRbar / d2` with `d2=1.128`.
- Computes Cp/Cpk-style within side indices and Pp/Ppk-style overall side indices.
- Handles one-sided specs by returning `null` for two-sided Cp/Pp while preserving the available side index.
- Computes observed below/above/total nonconformance counts/proportions/ppm and expected normal-model nonconformance probability/ppm.
- Returns histogram bins with fitted normal density for inline frontend rendering.
- Persists the result envelope and row snapshot through the existing analysis run path.
- Added frontend `CapabilityPanel` with measurement selector, LSL/USL/target inputs, inline SVG histogram/fitted normal/spec lines, capability index table, and observed/expected nonconformance table.
- No Cpm, confidence intervals, non-normal capability, Box-Cox/Johnson transform, subgroup pooled sigma, automatic stability approval, chart export artifact, or fake index fallback was added.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/capability.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_capability.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/CapabilityPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/capability_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_capability.py` and selected capability API/catalog contracts: passed with 6 selected tests.
- Backend ruff for touched backend files: passed.
- Backend mypy for `backend/app`: passed with 59 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 37 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 237 tests, frontend Vitest 37 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Capability indices are point estimates only; confidence intervals remain out of scope.
- Within sigma uses canonical row adjacent moving ranges, not subgroup-pooled sigma.
- Normal-model expected nonconformance is provided with warnings; normality and stability are not automatically approved.
- Non-normal capability, transformations, Cpm, capability report export, and chart export artifacts remain planned.

Next PR:

- Either add subgroup-pooled sigma and capability CI contract work, or continue Gate D with Gage R&R preflight only after reference fixtures are ready.

## Progress Update 58 - Gage R&R Preflight Shell

Completed in current working tree:

- At that earlier preflight-only slice, `quality.gage_rr` was not executable through `POST /api/v1/analysis-runs`.
- Added `POST /api/v1/quality/gage-rr/preflight` for balanced crossed design readiness only.
- The preflight reads canonical rows for one numeric measurement column plus part, operator, and replicate columns.
- The preflight returns schema hash, role-column metadata, usable/excluded row counts, part/operator/replicate counts, expected/observed part-operator cells, missing cells, min/max replicates per cell, replicate-count distribution, `ready_for_anova`, issues, and next step.
- Raw part/operator/replicate labels are not returned.
- No ANOVA table, variance components, %GRR, ndc, component plots, analysis run, result artifact, or fake statistical result was added.
- Added frontend `GageRrPreflightPanel` for the planned method with role selectors, readiness summary, replicate distribution table, and issues list.

Changed files:

- `backend/app/api/v1/quality.py`
- `backend/app/api/v1/schemas/analyses.py`
- `backend/app/main.py`
- `backend/app/services/gage_rr.py`
- `backend/app/statistics/gage_rr_preflight.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_gage_rr_preflight.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/AnalysisWorkbench.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/GageRrPreflightPanel.tsx`
- `frontend/src/api.ts`
- `docs/gage_rr_preflight_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_gage_rr_preflight.py` and selected Gage/API/catalog contracts: passed with 7 selected tests.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 38 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 242 tests, frontend Vitest 38 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- This earlier limitation is superseded by Progress Update 59, which adds the executable balanced crossed ANOVA slice.
- Nested, unbalanced, expanded Gage R&R remain out of scope.
- The preflight does not apply Workbench filter snapshots; it checks the full canonical dataset version.
- Tolerance/process variation, negative variance component policy, pooling policy, ndc, plots, and report output remain planned.

Next PR:

- Implement balanced crossed ANOVA Gage R&R only after adding independent reference fixtures and explicit negative-component/pooling/reporting policy.

## Progress Update 59 - Gage R&R Balanced Crossed ANOVA First Slice

Completed in current working tree:

- Made `quality.gage_rr` available in the analysis method registry.
- Added executable balanced crossed ANOVA Gage R&R through `POST /api/v1/analysis-runs`.
- Reused the canonical row reader and common row-snapshot artifact path before calculation.
- Added strict role validation for measurement, part, operator, and replicate columns.
- Added complete-case handling for missing measurement and identifier values.
- Rejects unbalanced crossed designs, missing part-operator cells, duplicate replicate IDs per cell, too few parts/operators/replicates, zero total variation, and unsupported missing policies with stable errors.
- Returns ANOVA table, raw/final variance components, repeatability, reproducibility, total Gage R&R, part-to-part, total variation, % contribution, % study variation, ndc, negative component policy, and interaction no-pooling policy.
- Preserves negative raw variance estimates while clamping final variance to zero and recording a warning.
- Redacts raw part/operator/replicate labels from preflight and result payloads.
- Added frontend Gage R&R execution control and result tables to the existing preflight panel.
- Added `docs/gage_rr_method_contract.md` and updated the six-module guide, preflight contract, and progress documents.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/services/gage_rr.py`
- `backend/app/statistics/gage_rr.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_gage_rr.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/GageRrPreflightPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/gage_rr_method_contract.md`
- `docs/gage_rr_preflight_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_gage_rr.py`, `test_gage_rr_preflight.py`, and selected Gage/API/catalog contracts: passed with 12 selected tests.
- Backend ruff format check, ruff check, and mypy passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 38 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 247 tests, frontend Vitest 38 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Only balanced crossed ANOVA is supported.
- Nested, unbalanced, expanded Gage R&R remain out of scope.
- Tolerance/process variation, pooling selection, component/interaction plots, chart artifacts, and report export remain planned.
- The preflight endpoint checks the full canonical dataset version; execution can still use the common analysis filter snapshot and then validates balance on the included rows.

Next PR:

- Continue with Gage Run Chart shell/calculation or the next DOE/quality slice only after adding reference fixtures and UI/result contracts; do not add mock statistical output.

## Progress Update 60 - Gage Run Chart Diagnostic First Slice

Completed in current working tree:

- Made `quality.gage_run_chart` available in the analysis method registry.
- Added stdlib Gage Run Chart calculation for balanced crossed measurement-system data.
- Reused canonical rows, the common filter snapshot, and `analysis_row_snapshot` provenance before calculation.
- Added role validation for measurement, part, operator, replicate, and optional order columns.
- Rejects unsupported missing policy, too few parts/operators/replicates, missing part/operator cells, unbalanced replicate sets, duplicate replicate IDs, invalid point limits, and no-usable-measurement cases with stable errors.
- Returns diagnostic-only warning metadata, design counts, overall summary, per-part-index and per-operator-index summaries, capped indexed chart points, canonical row positions, and order-source metadata.
- Redacts raw part/operator/replicate labels from the result payload.
- Added frontend `GageRunChartPanel` with role selectors, optional order selector, warning display, inline SVG indexed chart, and part/operator summary tables.
- Added `docs/gage_run_chart_method_contract.md` and updated progress and six-module planning docs.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/statistics/gage_run_chart.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_gage_run_chart.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/GageRunChartPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/gage_run_chart_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- Backend targeted pytest for `test_gage_run_chart.py` and selected Gage/API/catalog contracts: passed with 7 selected tests.
- Backend ruff check for touched backend files: passed.
- Backend mypy for `backend/app`: passed.
- Frontend `npm --prefix ./frontend run lint`: passed.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Frontend `npm --prefix ./frontend run test -- --run`: passed with 39 tests.
- Full `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 252 tests, frontend Vitest 39 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- This is a diagnostic chart payload, not variance component analysis.
- Component/interaction plots, faceting, chart export artifacts, and paged chart result retrieval remain out of scope.
- Datetime order columns are currently sorted by canonical string representation in the calculation slice.
- The UI displays indexed part/operator/replicate context only; raw labels stay redacted.

Next PR:

- Either harden Gage Run Chart ordering/faceting/export contracts or begin the first narrow Gate D1 DOE design-asset slice after adding fixtures and explicit result contracts.

## Progress Update 61 - Factorial DOE Design Asset First Slice

Completed in current working tree:

- Made `doe.factorial_design` available in the analysis method registry as a dedicated design-asset method with `requires_dataset=false`.
- Added a pure stdlib 2-level full factorial generator with deterministic randomization seed, standard order, run order, replicate index, center points, optional block assignment, explicit factor/run-count limits, and canonical `design_sha256`.
- Added SQLite schema v7 tables: `experiment_designs`, `experiment_design_versions`, and `experiment_runs`.
- Added `POST /api/v1/doe-designs/factorial` and `GET /api/v1/doe-designs/{design_id}` for persisted design creation/readback.
- Added checksum verification on stored DOE metadata before returning design payloads.
- Added `analysis_method_uses_dedicated_api` guard so `POST /api/v1/analysis-runs` does not create a fake DOE analysis result.
- Added frontend `FactorialDesignPanel` for factors, low/high/unit, replicates, center points, randomization seed, block count, and actual returned run-table preview.
- Added `docs/factorial_design_method_contract.md` and updated the six-module guide/progress docs.

Changed files:

- `backend/app/analyses/registry.py`
- `backend/app/api/v1/doe_designs.py`
- `backend/app/api/v1/schemas/doe.py`
- `backend/app/main.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/services/doe_designs.py`
- `backend/app/statistics/factorial_design.py`
- `backend/app/storage/metadata.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_factorial_design.py`
- `backend/tests/unit/test_metadata_store.py`
- `frontend/src/AnalysisShell.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/FactorialDesignPanel.tsx`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/factorial_design_method_contract.md`
- `docs/progress_gate_b.md`
- `docs/six_module_implementation_guide.md`
- `to_do_list.md`

Validation so far:

- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL temporary Python 3.12 validation venv with `--ignore-requires-python` was used because Windows executables currently fail from this WSL session with `UtilAcceptVsock: accept4 failed 110`.
- WSL temporary backend ruff format check for `backend`: passed, 103 files already formatted.
- WSL temporary backend ruff check for `backend`: passed.
- WSL temporary backend mypy for `backend/app`: passed with 68 source files.
- WSL temporary backend targeted pytest for `test_factorial_design.py`, `test_metadata_store.py`, and `test_api_contracts.py`: passed with 95 tests.
- WSL temporary backend full pytest for `backend/tests`: passed with 260 tests.
- WSL `npm --prefix ./frontend run lint`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 40 Vitest tests.
- WSL `npm --prefix ./frontend run build`: passed.
- `git diff --check`: passed.

Remaining limitations:

- This slice creates and stores design assets only.
- Response import is completed in Progress Update 62; effects, OLS/ANOVA, diagnostics, alias structure, DOE charts, design export, and report output remain out of scope.
- Native Windows Python 3.10 `scripts/check.ps1` still needs to be rerun from Windows PowerShell because this WSL session cannot launch Windows executables.

Next PR:

- Add response-entry/import for the persisted DOE design without regenerating factor levels or run order, then add effects/OLS/ANOVA only after reference fixtures and result contracts are ready.

## Progress Update 62 - Factorial DOE Response Entry Slice

Completed in current working tree:

- Added SQLite schema v8 table `experiment_run_responses` for numeric DOE response values keyed by immutable design version and run ID.
- Added metadata helpers to replace one response series and update DOE design status in the same transaction without mutating `experiment_runs`.
- Added `PUT /api/v1/doe-designs/{design_id}/responses` and `GET /api/v1/doe-designs/{design_id}/responses`.
- Added service validation that response entry must include exactly one finite numeric value for every persisted run_order, with duplicate/missing/extra run_order rejected.
- Kept `doe.factorial_design` blocked on the generic analysis-run API; no DOE effects, OLS, ANOVA, p-values, or fake result envelope was added.
- Added minimal frontend response entry in `FactorialDesignPanel` with response name/unit and run-order keyed numeric inputs.
- Updated `docs/factorial_design_method_contract.md`, `docs/six_module_implementation_guide.md`, `docs/progress_gate_b.md`, and `docs/storage.md`.

Validation so far:

- WSL temporary backend ruff format/check for touched backend files: passed.
- WSL temporary backend targeted pytest for `test_metadata_store.py` and `test_api_contracts.py`: passed with 95 tests.
- WSL temporary backend full ruff/mypy/pytest: passed with 263 backend tests.
- WSL `npm --prefix ./frontend run lint`: passed.
- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 40 Vitest tests.
- WSL `npm --prefix ./frontend run build`: passed.
- Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend pytest 263 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Response entry currently supports one numeric response series at a time through the UI, although the API can store named series.
- DOE effects, OLS/ANOVA, residual diagnostics, alias structure, DOE charts, design export, and report output remain out of scope.
- No Windows validation gap remains for this slice.

Next PR:

- Add the DOE effects/OLS/ANOVA contract and reference fixtures first, then implement calculation only after the contract has stable result fields and failure cases.

## Progress Update 63 - Statistical QA and Execution Hardening

Completed in current working tree:

- Added full canonical rows artifact verification before paginated row preview returns any row values.
- Added schema PATCH no-op detection so unchanged display name, measurement level, role, and unit values keep the existing `schema_hash` and do not mark analysis runs stale.
- Added runtime/build provenance fields to generic analysis-run envelopes: Python version, platform, optional `DATALAB_GIT_COMMIT`, and NumPy/SciPy package versions.
- Added the first `MethodExecutionHandler` registry slice for `eda.descriptive` and `eda.graphical_summary` while keeping other methods on the existing guarded path.
- Added a TOST regression audit for the rule that both one-sided tests must reject before equivalence is reported.
- Documented the 29-method audit matrix, regression prediction vs generic registry boundary, DOE dedicated API boundary, canonical preview verification policy, schema no-op stale policy, and CI status.
- Kept planned/disabled methods non-executable and did not add new statistical methods or fake results.

Changed files:

- `backend/app/api/v1/schemas/analyses.py`
- `backend/app/core/config.py`
- `backend/app/services/analysis_runs.py`
- `backend/app/services/dataset_rows.py`
- `backend/app/services/dataset_versions.py`
- `backend/tests/unit/test_api_contracts.py`
- `backend/tests/unit/test_dataset_upload.py`
- `backend/tests/unit/test_equivalence_tost.py`
- `frontend/src/analysisMethodGuidance.ts`
- `frontend/src/api.ts`
- `docs/ci_status.md`
- `docs/datasets.md`
- `docs/progress_gate_b.md`
- `docs/statistical_method_audit_matrix.md`
- `docs/storage.md`
- `to_do_list.md`

Validation:

- Targeted Windows pytest for `test_dataset_upload.py`: passed with 29 tests.
- Targeted Windows pytest for `test_equivalence_tost.py`: passed with 5 tests.
- Targeted Windows pytest for selected API contract stabilization tests: passed with 5 selected tests.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Row preview now performs an extra full canonical JSONL pass before page extraction; this is intentionally conservative for the stabilization PR and may need cached artifact verification metadata later.
- Only `eda.descriptive` and `eda.graphical_summary` have moved to the handler registry so far.
- `regression.predict` remains disabled in the generic method registry and runs only through the dedicated stored-model prediction API.
- `doe.factorial_design` remains available only through dedicated DOE design routes; effects, OLS/ANOVA, diagnostics, alias structure, and DOE charts remain out of scope.
- Remote GitHub Actions run status could not be verified from this environment because public Actions access was not inspectable and `gh` was unavailable.

Next PR:

- Continue moving available methods into `MethodExecutionHandler` one module at a time, starting with EDA methods, without changing result contracts.
- Add cached canonical artifact verification metadata or a more efficient verified-reader strategy if preview performance becomes an issue.
- Add DOE effects/OLS/ANOVA contracts and reference fixtures before implementing any DOE calculation.

## Progress Update 64 - EDA Handler Registry and Provenance Helper Follow-up

Completed in current working tree:

- Centralized generic analysis-run provenance construction in `_analysis_provenance` so runtime/build fields are applied consistently across current methods.
- Replaced repeated `AnalysisProvenance(...)` blocks in `analysis_runs.py` with the shared helper.
- Moved all four EDA methods into the `MethodExecutionHandler` registry: `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, and `eda.equal_variances`.
- Removed the remaining EDA branches from the large `create_analysis_run` method-id chain without changing method availability or result contracts.
- Updated the handler registry contract test and audit/progress docs.

Validation:

- Targeted Windows pytest for EDA method execution, handler registry, and provenance helper coverage: passed with 6 selected tests.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted after formatting `analysis_runs.py`.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Hypothesis, categorical, regression, quality, and dedicated DOE methods still use the existing guarded dispatch path.
- No new statistical method, result schema version, DB migration, or fake result was added.

Next PR:

- Move the hypothesis module methods into handler registry in smaller batches, or add an explicit handler interface file if `analysis_runs.py` becomes harder to navigate.

## Progress Update 65 - First Hypothesis Handler Registry Batch

Completed in current working tree:

- Moved the first hypothesis batch into the `MethodExecutionHandler` registry:
  `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, and `hypothesis.equivalence_tost`.
- Removed those four method branches from the large `create_analysis_run` if-chain.
- Kept `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, and `hypothesis.one_way_anova` on the existing guarded path for the next batch.
- Updated the handler registry contract test and audit/progress docs.
- Did not change statistical calculations, result schemas, availability, migrations, or frontend behavior.

Validation:

- Targeted Windows pytest for handler registry plus the four migrated hypothesis methods: passed with 5 selected tests.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- The remaining hypothesis methods, categorical methods, regression methods, quality methods, and dedicated DOE flow still use the existing dispatch path.
- No new statistical method or fake result was added.

Next PR:

- Move the remaining hypothesis methods into the handler registry after targeted execution tests pass.

## Progress Update 66 - Complete Hypothesis Handler Registry Migration

Completed in current working tree:

- Moved the remaining hypothesis methods into the `MethodExecutionHandler` registry:
  `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, and `hypothesis.one_way_anova`.
- Removed the last hypothesis method branches from the large `create_analysis_run` if-chain.
- Updated the handler registry contract test so it covers all EDA and hypothesis methods now handled by the registry.
- Updated the audit/progress docs to reflect that all eight hypothesis methods are on the handler path.
- Did not change statistical calculations, result schemas, availability, migrations, or frontend behavior.

Validation:

- Targeted Windows pytest for handler registry plus the four newly migrated hypothesis methods: passed with 5 selected tests.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Categorical, regression, quality, and dedicated DOE flows still use the existing dispatch path.
- No new statistical method or fake result was added.

Next PR:

- Move categorical methods into the handler registry as the next small batch, then repeat targeted API execution tests.

## Progress Update 67 - Categorical Handler Registry Migration

Completed in current working tree:

- Moved all categorical methods into the `MethodExecutionHandler` registry:
  `categorical.one_proportion`, `categorical.two_proportion`, and
  `categorical.chi_square_association`.
- Removed categorical method branches from the large `create_analysis_run` if-chain.
- Updated the handler registry contract test so it covers EDA, hypothesis, and categorical methods handled by the registry.
- Updated the audit/progress docs to reflect categorical handler coverage.
- Did not change statistical calculations, result schemas, availability, migrations, or frontend behavior.

Validation:

- Targeted Windows pytest for handler registry plus the three migrated categorical methods: passed with 4 selected tests.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Regression, quality, and dedicated DOE flows still use the existing dispatch path.
- No new statistical method or fake result was added.

Next PR:

- Move regression analysis-run methods into the handler registry as the next small batch, keeping `regression.predict` on the dedicated stored-model API path.

## Progress Update 68 - Regression Handler Registry Migration

Completed in current working tree:

- Moved the generic regression analysis-run methods into the `MethodExecutionHandler` registry:
  `regression.pearson`, `regression.xy_correlation`, and `regression.linear_model`.
- Removed regression analysis-run method branches from the large `create_analysis_run` if-chain.
- Kept `regression.predict` out of the generic handler registry because it uses the dedicated stored-model prediction API and remains disabled in the generic method registry.
- Updated the handler registry contract test so it covers EDA, hypothesis, categorical, and generic regression methods handled by the registry.
- Updated the audit/progress docs to reflect generic regression handler coverage.
- Did not change statistical calculations, result schemas, availability, migrations, or frontend behavior.

Validation:

- Targeted Windows pytest for handler registry plus the three migrated generic regression methods: passed with 4 selected tests.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Frontend `npm --prefix ./frontend run typecheck`: passed.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Quality and dedicated DOE flows still use the existing dispatch path.
- No new statistical method or fake result was added.

Next PR:

- Move quality methods into the handler registry in small batches, starting with chart-style methods.

## Progress Update 69 - Quality Handler Registry Migration

Completed in current working tree:

- Moved all current quality analysis-run methods into the `MethodExecutionHandler` registry:
  `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`,
  `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart`.
- Removed quality method branches from the large `create_analysis_run` if-chain.
- Kept `doe.factorial_design` out of the generic handler registry because it uses dedicated DOE design routes.
- Updated the handler registry contract test so it covers EDA, hypothesis, categorical, generic regression, and quality methods handled by the registry, and fails if an available generic analysis-run method is missing a handler.
- Updated the audit/progress docs to reflect quality handler coverage.
- Did not change statistical calculations, result schemas, availability, migrations, or frontend behavior.

Validation:

- Targeted Windows pytest for handler registry plus the six migrated quality methods: passed with 8 selected tests.
- Additional Windows pytest for the no-gap handler registry contract: passed with 1 selected test.
- Windows backend ruff format check for `backend`: passed, 103 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 68 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 267 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- `doe.factorial_design` still uses dedicated DOE design routes and returns `analysis_method_uses_dedicated_api` from the generic analysis-run endpoint.
- `regression.predict` remains disabled in the generic registry and uses the dedicated stored-model prediction API.
- No new statistical method or fake result was added.

Next PR:

- Split `analysis_runs.py` handlers into smaller module-owned files if the registry keeps growing, or start the next documented Gate slice only with reference-backed calculations.

## Progress Update 70 - Handler Spec Module Split

Completed in current working tree:

- Added `backend/app/services/analysis_method_handlers.py` for the shared
  `MethodExecutionHandler` dataclass, method handler specs, and missing-runner
  validation builder.
- Changed `analysis_runs.py` so it supplies only the method runner functions to
  `build_method_execution_handlers`, while handler metadata lives outside the
  large execution service.
- Kept all current generic analysis-run methods on the same execution behavior:
  four EDA, eight hypothesis, three categorical, three generic regression, and
  six quality methods.
- Kept `regression.predict` on the dedicated stored-model prediction API and
  `doe.factorial_design` on dedicated DOE design routes.
- Strengthened the handler contract tests so the spec order matches the runtime
  registry and the builder fails loudly if a runner is missing.
- Did not change statistical calculations, result schemas, availability,
  migrations, or frontend behavior.

Validation:

- Targeted Windows pytest for handler registry, builder guard, and representative EDA executions: passed with 5 selected tests.
- Additional Windows pytest for the focused handler registry and builder guard: passed with 2 selected tests.
- Windows backend ruff format check for `backend`: passed, 104 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 69 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 268 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- The handler runner functions still live in `analysis_runs.py`; moving each
  method family into module-owned runner files should be a separate refactor.
- No new statistical method or fake result was added.

Next PR:

- Split one low-risk method family, likely EDA, into a module-owned runner file
  only after the current spec/builder contract remains green.

## Progress Update 71 - Analysis Run Execution Support Split

Completed in current working tree:

- Added `backend/app/services/analysis_run_execution.py` for common inline
  analysis-run execution helpers:
  - runtime/build provenance construction
  - row snapshot artifact creation
  - filter snapshot row freezing
  - canonical result/config JSON bytes
  - result and row-snapshot workspace paths
  - compensating file cleanup helper
- Updated `analysis_runs.py` to import these common helpers instead of owning
  duplicate row snapshot/filter/provenance infrastructure inline.
- Added direct unit tests for deterministic canonical JSON bytes and contiguous
  row-range compression in the new execution-support module.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for execution-support helpers, handler registry, and representative EDA executions: passed with 8 selected tests.
- Windows backend ruff format check for `backend`: passed, 106 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 70 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Method runner functions still live in `analysis_runs.py`.
- EDA runner extraction is now lower risk because execution-support helpers no
  longer create a circular import boundary.
- No new statistical method or fake result was added.

Next PR:

- Move the four EDA runner functions and EDA-specific selection/warning helpers
  into an EDA-owned runner module while keeping the same handler registry
  method IDs and result envelopes.

## Progress Update 72 - EDA Runner Module Split

Completed in current working tree:

- Added `backend/app/services/analysis_runners_eda.py` for the four EDA runner
  functions:
  - `eda.descriptive`
  - `eda.graphical_summary`
  - `eda.normality`
  - `eda.equal_variances`
- Moved EDA-specific column selection, option validation, and warning mapping
  helpers out of `analysis_runs.py` into the EDA runner module.
- Kept shared result persistence, row snapshot, filter snapshot, provenance,
  and cleanup behavior delegated to `analysis_run_execution.py`.
- Updated the method execution registry so the four EDA method IDs now point to
  the EDA-owned runner functions.
- Strengthened the handler contract test to assert the EDA handlers use the
  module-owned runner functions.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for EDA-owned handler registry coverage, cleanup failure behavior, and representative EDA executions: passed with 5 selected tests.
- Windows backend ruff format check for `backend`: passed, 107 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 71 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Hypothesis, categorical, regression, and quality runner functions still live
  in `analysis_runs.py`.
- The EDA runner module still has a local result-persistence wrapper around the
  common execution helpers; a later refactor can generalize that wrapper after
  one more method family is split.
- No new statistical method or fake result was added.

Next PR:

- Split the next low-risk method family, likely categorical or a small
  hypothesis batch, into a module-owned runner file using the same
  execution-support helpers.

## Progress Update 73 - Categorical Runner Module Split

Completed in current working tree:

- Added `backend/app/services/analysis_runners_categorical.py` for the three
  categorical runner functions:
  - `categorical.one_proportion`
  - `categorical.two_proportion`
  - `categorical.chi_square_association`
- Moved categorical-specific column selection, option validation, API error
  mapping, and warning mapping helpers out of `analysis_runs.py` into the
  categorical runner module.
- Kept shared result persistence, row snapshot, filter snapshot, provenance,
  and cleanup behavior delegated to `analysis_run_execution.py`.
- Updated the method execution registry so the three categorical method IDs now
  point to the categorical-owned runner functions.
- Strengthened the handler contract test to assert the categorical handlers use
  the module-owned runner functions.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for categorical-owned handler registry coverage and representative categorical executions: passed with 4 selected tests.
- Windows backend ruff format check for `backend`: passed, 108 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 72 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Hypothesis, regression, and quality runner functions still live in
  `analysis_runs.py`.
- The categorical runner module still has a local result-persistence wrapper
  around the common execution helpers; a later refactor can generalize that
  wrapper after another method family is split.
- No new statistical method or fake result was added.

Next PR:

- Split the next method family, likely hypothesis or quality, into a
  module-owned runner file only after the categorical split remains green.

## Progress Update 74 - Hypothesis Runner Module Split

Completed in current working tree:

- Added `backend/app/services/analysis_runners_hypothesis.py` for the eight
  hypothesis runner functions:
  - `hypothesis.one_sample_t`
  - `hypothesis.paired_t`
  - `hypothesis.one_sample_wilcoxon`
  - `hypothesis.two_sample_t`
  - `hypothesis.mann_whitney`
  - `hypothesis.kruskal_wallis`
  - `hypothesis.one_way_anova`
  - `hypothesis.equivalence_tost`
- Moved hypothesis-specific column selection, option validation, API error
  mapping, and warning mapping helpers out of `analysis_runs.py` into the
  hypothesis runner module.
- Kept row snapshot, filter snapshot, provenance, result persistence, and
  cleanup behavior on the same shared `analysis_run_execution.py` helper path.
- Updated the method execution registry so the eight hypothesis method IDs now
  point to the hypothesis-owned runner functions.
- Strengthened the handler contract test to assert the hypothesis handlers use
  the module-owned runner functions.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for hypothesis-owned handler registry coverage and representative hypothesis executions: passed with 9 selected tests.
- Windows backend ruff format check for `backend`: passed, 109 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 73 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Generic regression and quality runner functions still live in
  `analysis_runs.py`.
- The hypothesis runner module preserves the current inline result-persistence
  pattern; a later refactor can generalize that wrapper after the remaining
  method families are split.
- No new statistical method or fake result was added.

Next PR:

- Split the generic regression runners or quality runners into module-owned
  files, then consider a shared result-persistence wrapper once at least three
  method-family modules use the same pattern.

## Progress Update 75 - Regression Correlation Runner Module Split

Completed in current working tree:

- Added `backend/app/services/analysis_runners_regression.py` for the first two
  generic regression runner functions:
  - `regression.pearson`
  - `regression.xy_correlation`
- Moved Pearson and X-Y correlation column selection, option validation, API
  error mapping, and warning mapping helpers out of `analysis_runs.py` into the
  regression runner module.
- Updated the method execution registry so `regression.pearson` and
  `regression.xy_correlation` now point to regression-owned runner functions.
- Strengthened the handler contract test to assert the Pearson and X-Y
  correlation handlers use module-owned runner functions.
- Kept `regression.linear_model` in `analysis_runs.py` for this slice because
  it owns safe JSON model-manifest persistence and the dedicated stored-model
  prediction boundary; this limitation is superseded by Progress Update 76.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for regression-owned handler registry coverage and representative Pearson/X-Y executions: passed with 3 selected tests.
- Windows backend ruff format check for `backend`: passed, 110 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 74 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Superseded by Progress Update 76 for `regression.linear_model`.
- Quality runner functions still live in `analysis_runs.py`.
- No new statistical method or fake result was added.

Next PR:

- Superseded by Progress Update 76; the remaining runner-family split is quality.

## Progress Update 76 - Linear Model Runner And Manifest Split

Completed in current working tree:

- Moved `regression.linear_model` into
  `backend/app/services/analysis_runners_regression.py` alongside the Pearson
  and X-Y correlation runners.
- Moved linear-model-specific column selection, option validation, API error
  mapping, warning mapping, safe JSON model-manifest payload construction,
  diagnostics redaction, and model-manifest relative path helpers out of
  `analysis_runs.py`.
- Updated the method execution registry so all three generic regression method
  IDs now point to regression-owned runner functions.
- Updated the linear-model metadata-insert-failure cleanup test so it patches
  the regression runner module boundary.
- Strengthened the handler contract test to assert `regression.linear_model`
  uses the module-owned runner function.
- Kept the dedicated stored-model prediction API path unchanged; only the
  generic analysis-run execution owner moved.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for regression-owned handler registry coverage, representative linear-model executions, and manifest cleanup: passed with 7 selected tests.
- Windows backend ruff format check for `backend`: passed, 110 files already formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 74 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests, frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Quality runner functions still live in `analysis_runs.py`.
- Regression runner module still preserves the current inline result-persistence
  pattern; a later refactor can generalize that wrapper after quality runners
  are split.
- No new statistical method or fake result was added.

Next PR:

- Split quality runners into a module-owned runner file or first extract the
  duplicated succeeded-result persistence wrapper shared by runner modules.

## Progress Update 77 - Quality Runner Module Split

Completed in current working tree:

- Added `backend/app/services/analysis_runners_quality.py` for the six current
  quality runner functions:
  - `quality.individuals_chart`
  - `quality.subgroup_chart`
  - `quality.run_chart`
  - `quality.capability`
  - `quality.gage_rr`
  - `quality.gage_run_chart`
- Moved quality-specific column selection, option validation, API error
  mapping, warning mapping, Gage R&R column preflight reuse, and result
  persistence cleanup paths out of `analysis_runs.py` into the quality runner
  module.
- Updated the method execution registry so all six current quality method IDs
  now point to quality-owned runner functions.
- Strengthened the handler contract test to assert all six quality handlers use
  the module-owned runner functions.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for quality-owned handler registry coverage and
  representative quality executions: passed with 8 selected tests.
- Windows backend ruff format check for `backend`: passed, 111 files already
  formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 75 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 270 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Quality runner module still preserves the current inline result-persistence
  pattern; a later refactor can generalize the duplicated succeeded-result
  wrapper shared by runner modules.
- No new statistical method or fake result was added.

Next PR:

- Either extract the duplicated successful analysis-result persistence wrapper
  shared by runner modules, or start the next documented Gate slice only with
  reference-backed statistical fixtures.

## Progress Update 78 - Shared Result Persistence Helper First Slice

Completed in current working tree:

- Added `store_succeeded_analysis_result` to
  `backend/app/services/analysis_run_execution.py`.
- Centralized successful analysis result envelope construction, canonical JSON
  serialization, result path generation, SHA-256 calculation, metadata insert,
  and result-file cleanup on metadata insert failure.
- Migrated EDA runner methods to the shared helper:
  - `eda.descriptive`
  - `eda.graphical_summary`
  - `eda.normality`
  - `eda.equal_variances`
- Migrated categorical runner methods to the shared helper:
  - `categorical.one_proportion`
  - `categorical.two_proportion`
  - `categorical.chi_square_association`
- Updated cleanup tests so metadata insert failures are injected at the shared
  helper boundary, and added categorical cleanup coverage through
  `categorical.one_proportion`.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for shared helper cleanup, representative EDA and
  categorical execution, handler registry, and analysis-run helper tests:
  passed with 7 selected tests.
- Windows backend ruff format check for `backend`: passed, 111 files already
  formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 75 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 271 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Hypothesis, quality, and simple generic regression runners still use local
  inline result-persistence blocks; `regression.linear_model` also has
  model-manifest persistence that needs a narrower follow-up.
- No new statistical method or fake result was added.

Next PR:

- Migrate hypothesis and quality runner methods to
  `store_succeeded_analysis_result` in one or two small batches, keeping
  `regression.linear_model` manifest persistence separate until its cleanup
  behavior has dedicated coverage.

## Progress Update 79 - Shared Result Persistence Helper Expansion

Completed in current working tree:

- Migrated all hypothesis runner methods to `store_succeeded_analysis_result`:
  - `hypothesis.one_sample_t`
  - `hypothesis.paired_t`
  - `hypothesis.one_sample_wilcoxon`
  - `hypothesis.two_sample_t`
  - `hypothesis.mann_whitney`
  - `hypothesis.kruskal_wallis`
  - `hypothesis.one_way_anova`
  - `hypothesis.equivalence_tost`
- Migrated all current quality runner methods to
  `store_succeeded_analysis_result`:
  - `quality.individuals_chart`
  - `quality.subgroup_chart`
  - `quality.run_chart`
  - `quality.capability`
  - `quality.gage_rr`
  - `quality.gage_run_chart`
- Preserved the existing outer row-snapshot cleanup block in each runner while
  delegating result JSON cleanup to the shared helper.
- Added cleanup regression coverage for `hypothesis.one_sample_t` and
  `quality.individuals_chart` metadata insert failures.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for shared helper cleanup, representative hypothesis
  and quality execution, and handler registry coverage: passed with 5 selected
  tests.
- Windows backend ruff format check for `backend`: passed, 111 files already
  formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 75 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 273 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- `regression.pearson` and `regression.xy_correlation` still use local inline
  result-persistence blocks.
- `regression.linear_model` still has custom result plus model-manifest
  persistence and cleanup behavior that should remain separate until the
  regression model manifest path has focused coverage.
- No new statistical method or fake result was added.

Next PR:

- Migrate simple generic regression result persistence for `regression.pearson`
  and `regression.xy_correlation` to the shared helper, then evaluate a narrow
  helper or wrapper for `regression.linear_model` manifest persistence.

## Progress Update 80 - Simple Regression Result Persistence Helper Migration

Completed in current working tree:

- Migrated `regression.pearson` to `store_succeeded_analysis_result`.
- Migrated `regression.xy_correlation` to `store_succeeded_analysis_result`.
- Preserved the existing outer row-snapshot cleanup block in both simple
  regression runners while delegating result JSON cleanup to the shared helper.
- Added cleanup regression coverage for metadata insert failures:
  - `regression.pearson`
  - `regression.xy_correlation`
- Kept `regression.linear_model` on its custom result plus model-manifest
  persistence path because it writes and registers an additional
  `regression_model_manifest` artifact.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for shared helper cleanup, representative Pearson and
  X-Y execution, and handler registry coverage: passed with 5 selected tests.
- Windows backend ruff format check for `backend`: passed, 111 files already
  formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 75 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 275 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- `regression.linear_model` still has custom result plus model-manifest
  persistence and cleanup behavior.
- No new statistical method or fake result was added.

Next PR:

- Evaluate a narrow helper or wrapper for `regression.linear_model` that can
  preserve manifest artifact registration and cleanup without weakening the
  stored-model prediction boundary.

## Progress Update 81 - Linear Model Manifest-Aware Persistence Wrapper

Completed in current working tree:

- Extracted `regression.linear_model` result and model-manifest persistence into
  a dedicated `_store_succeeded_linear_model_result` wrapper inside
  `backend/app/services/analysis_runners_regression.py`.
- Kept `regression.linear_model` separate from the generic
  `store_succeeded_analysis_result` helper because it writes both:
  - the analysis `result.json`
  - the app-created `regression_model_manifest` artifact and regression model
    metadata record
- Preserved result envelope behavior:
  - `prediction_basis` stays out of the analysis result envelope
  - `model_manifest` metadata remains in the result envelope
  - the full prediction basis remains in the checksum-validated manifest
- Preserved row-snapshot cleanup in the runner and moved result/manifest cleanup
  into the manifest-aware wrapper.
- Added focused cleanup coverage for the case where manifest writing succeeds
  but `result.json` writing fails.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, prediction endpoints, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for linear-model execution, manifest cleanup,
  result-write cleanup, manifest-backed prediction, and handler registry
  coverage: passed with 5 selected tests.
- Windows backend ruff format check for `backend`: passed, 111 files already
  formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 75 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 276 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- The regression-specific wrapper is intentionally local to
  `analysis_runners_regression.py`; a more generic multi-artifact persistence
  helper is not added yet.
- No new statistical method or fake result was added.

Next PR:

- With method runner persistence mostly stabilized, move to either a small
  documentation/contract cleanup pass or the next reference-backed statistical
  Gate slice.

## Progress Update 82 - Persistence Boundary Contract Test

Completed in current working tree:

- Added an explicit API contract test for analysis runner persistence
  boundaries.
- The test now verifies result-only runner modules delegate successful result
  persistence to `store_succeeded_analysis_result` and do not directly import
  low-level metadata insert or file-write primitives.
- The test also verifies `regression.pearson` and `regression.xy_correlation`
  use the shared result helper, while `regression.linear_model` keeps the
  manifest-aware regression-model persistence boundary.
- Updated Gate B progress and statistical audit docs to record the persistence
  boundary contract coverage.
- Kept statistical calculations, result schemas, method availability, storage
  paths, migrations, prediction endpoints, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for handler registry, handler builder guard, and
  persistence boundary contract coverage: passed with 3 selected tests.
- Windows backend ruff format check for `backend`: passed, 111 files already
  formatted.
- Windows backend ruff check for `backend`: passed.
- Windows backend mypy for `backend/app`: passed with 75 source files.
- Full Windows `scripts/check.ps1`: passed with backend pytest 277 tests,
  frontend Vitest 40 tests, frontend lint/typecheck, and frontend build.

Remaining limitations:

- Persistence boundary checks are intentionally internal contract tests; they
  complement but do not replace API execution and cleanup tests.
- No new statistical method or fake result was added.

Next PR:

- Continue with a small documentation/contract cleanup pass, or start the next
  reference-backed statistical Gate slice.

## Progress Update 83 - High-Risk Statistical QA and Method Contract Stabilization

Completed in current working tree:

- Added a shared `METHOD_VERSIONS` map for all 29 stable method IDs and wired
  the analysis catalog plus generic execution handler specs to that same
  source.
- Added API contract coverage that asserts method version mapping completeness
  and catalog/handler version alignment.
- Added typed runner-boundary option validation for
  `hypothesis.equivalence_tost` through `EquivalenceTostOptions`.
- Added API contract coverage for invalid TOST option type, missing required
  bound, and unknown option field rejection with
  `invalid_equivalence_tost_options`.
- Consolidated analysis provenance commit metadata so the shared provenance
  helper prefers `Settings.git_commit` and falls back to
  `DATALAB_GIT_COMMIT`.
- Added or strengthened high-risk statistical QA tests:
  - `hypothesis.one_way_anova`: significant-only Tukey-Kramer posthoc,
    non-significant posthoc skip, negative omega squared retained from the
    documented formula, and group-size imbalance warning.
  - `hypothesis.equivalence_tost`: one-sided TOST decision logic and
    non-significant difference not being treated as equivalence.
  - `categorical.two_proportion`: all-event/no-event zero-cell RR/OR handling
    without fake effect CIs.
  - `categorical.chi_square_association`: sparse 2x2 Fisher recommendation
    without automatic fallback and finite standardized residuals.
  - `quality.capability`: one-sided spec still carries the process-stability
    warning.
- Updated `docs/statistical_method_audit_matrix.md` with method-level
  verification depth, including honest partial coverage notes for capability,
  Gage R&R, Gage Run Chart, and DOE factorial design.
- Updated CI and Gate B progress docs to record the latest local validation
  count and the current GitHub Actions inspection limitation.
- Added dataset/storage performance notes for full canonical preview
  verification before paging.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and frontend behavior unchanged.

Validation:

- Targeted Windows pytest for API contracts plus high-risk statistical QA files:
  passed with 124 tests.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 284
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- `hypothesis.equivalence_tost` received the first typed options adapter in this
  slice; other high-risk methods still need the same runner-boundary contract
  treatment.
- `quality.capability` still lacks an independent external reference fixture and
  index confidence intervals.
- `quality.gage_rr` and `quality.gage_run_chart` still rely on hand fixtures,
  not independent external reference fixtures.
- `doe.factorial_design` remains a design-asset API only; effects, OLS, ANOVA,
  diagnostics, and DOE charts remain out of scope.

Next PR:

- Add typed option adapters for `regression.linear_model` and/or
  `quality.gage_rr`.
- Add independent reference fixtures for capability and Gage R&R where feasible.
- Continue auditing high-risk statistical formulas before adding any new
  available method.

## Progress Update 84 - Linear Model and Gage R&R Option Contract Expansion

Completed in current working tree:

- Added `LinearModelOptions` and nested `LinearModelInteractionTermOption` typed
  request adapters for `regression.linear_model`.
- Added `GageRrOptions` typed request adapter for `quality.gage_rr`.
- Wired both adapters at runner entry before row snapshot or result artifact
  creation.
- Added stable sanitized error codes:
  - `invalid_linear_model_options`
  - `invalid_gage_rr_options`
- Added API contract tests that malformed option payloads fail without echoing
  invalid raw option values or unknown field names in the response.
- Added frontend analysis error guidance for the two new error codes so users
  see actionable Korean guidance instead of only machine-readable codes.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation so far:

- Targeted Windows pytest for method-version/provenance/typed-option contracts:
  passed with 11 selected tests.
- Frontend typecheck passed.
- Frontend lint passed.
- Frontend Vitest passed with 40 tests.
- Targeted backend ruff format/check for touched backend files passed after
  formatting `test_api_contracts.py`.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 291
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Other high-risk methods still use generic `options` dictionaries plus
  method-local validators.
- Capability and Gage R&R still need independent external reference fixtures
  where feasible.
- No new statistical method or fake result was added.

Next PR:

- Continue typed adapter coverage for capability, chi-square, and two-proportion
  payloads, or add independent reference fixtures for capability/Gage R&R before
  expanding new methods.

## Progress Update 85 - Categorical and Capability Option Contract Expansion

Completed in current working tree:

- Added `TwoProportionOptions` typed request adapter for
  `categorical.two_proportion`.
- Added `ChiSquareAssociationOptions` typed request adapter for
  `categorical.chi_square_association`.
- Added `CapabilityOptions` typed request adapter for `quality.capability`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_two_proportion_options`
  - `invalid_chi_square_options`
  - `invalid_capability_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix and Gate B progress notes to
  record typed contract coverage.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation so far:

- Targeted Windows pytest for typed-option contracts across TOST, categorical,
  linear model, capability, and Gage R&R: passed with 20 selected tests.
- Targeted backend ruff format/check for touched backend files passed.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 301
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Several other methods still use generic `options` dictionaries plus
  method-local validators.
- Capability and Gage R&R still need independent external reference fixtures
  where feasible.
- No new statistical method or fake result was added.

Next PR:

- Continue typed adapter coverage for remaining high-risk request payloads, or
  switch to independent reference fixture work for capability/Gage R&R.

## Progress Update 86 - ANOVA, Kruskal-Wallis, and Run Chart Option Contract Expansion

Completed in current working tree:

- Added `OneWayAnovaOptions` typed request adapter for
  `hypothesis.one_way_anova`.
- Added `KruskalWallisOptions` typed request adapter for
  `hypothesis.kruskal_wallis`.
- Added `RunChartOptions` typed request adapter for `quality.run_chart`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_one_way_anova_options`
  - `invalid_kruskal_wallis_options`
  - `invalid_run_chart_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix, Gate B progress notes, and CI
  status to record typed contract coverage and the latest validation count.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation:

- Targeted Windows pytest for the three new typed-option contracts: passed with
  10 selected tests.
- Targeted backend ruff format/check for touched backend files passed.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 311
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Several other methods still use generic `options` dictionaries plus
  method-local validators.
- Capability, Gage R&R, Gage Run Chart, and DOE factorial design still need
  stronger independent reference fixture coverage where feasible.
- No new statistical method or fake result was added.

Next PR:

- Continue typed adapter coverage for remaining request payloads, especially
  EDA chart/normality/equal-variance and remaining hypothesis methods, or add
  independent reference fixtures for the currently partial quality methods.

## Progress Update 87 - Core t-Test Option Contract Expansion

Completed in current working tree:

- Added `OneSampleTOptions` typed request adapter for
  `hypothesis.one_sample_t`.
- Added `PairedTOptions` typed request adapter for `hypothesis.paired_t`.
- Added `TwoSampleTOptions` typed request adapter for
  `hypothesis.two_sample_t`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_one_sample_t_options`
  - `invalid_paired_t_options`
  - `invalid_two_sample_t_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix, Gate B progress notes, and CI
  status to record typed contract coverage.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation:

- Targeted Windows pytest for the three new typed-option contracts: passed with
  9 selected tests.
- Targeted backend ruff format/check for touched backend files passed.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 320
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Several other methods still use generic `options` dictionaries plus
  method-local validators.
- Capability, Gage R&R, Gage Run Chart, and DOE factorial design still need
  stronger independent reference fixture coverage where feasible.
- No new statistical method or fake result was added.

Next PR:

- Continue typed adapter coverage for remaining request payloads, especially
  EDA chart/normality/equal-variance, one-sample Wilcoxon, and Mann-Whitney, or
  add independent reference fixtures for the currently partial quality methods.

## Progress Update 88 - Rank and One-Proportion Option Contract Expansion

Completed in current working tree:

- Added `OneSampleWilcoxonOptions` typed request adapter for
  `hypothesis.one_sample_wilcoxon`.
- Added `MannWhitneyOptions` typed request adapter for
  `hypothesis.mann_whitney`.
- Added `OneProportionOptions` typed request adapter for
  `categorical.one_proportion`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_one_sample_wilcoxon_options`
  - `invalid_mann_whitney_options`
  - `invalid_one_proportion_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix, Gate B progress notes, and CI
  status to record typed contract coverage.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation:

- Targeted Windows pytest for the three new typed-option contracts: passed with
  9 selected tests.
- Targeted backend ruff format/check for touched backend files passed.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 329
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Capability, Gage R&R, Gage Run Chart, and DOE factorial design still need
  stronger independent reference fixture coverage where feasible.
- No new statistical method or fake result was added.

Next PR:

- Add independent reference fixtures for the currently partial quality/DOE
  methods, or continue contract hardening for remaining regression correlation
  payloads.

## Progress Update 90 - Quality Chart Option Contract Expansion

Completed in current working tree:

- Added `IndividualsChartOptions` typed request adapter for
  `quality.individuals_chart`.
- Added `SubgroupChartOptions` typed request adapter for
  `quality.subgroup_chart`.
- Added `GageRunChartOptions` typed request adapter for
  `quality.gage_run_chart`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_individuals_chart_options`
  - `invalid_subgroup_chart_options`
  - `invalid_gage_run_chart_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix, Gate B progress notes, and CI
  status to record typed contract coverage.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation:

- Targeted Windows pytest for the three new typed-option contracts: passed with
  10 selected tests.
- Targeted backend ruff format/check for touched backend files passed after
  import sorting.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 348
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Capability, Gage R&R, Gage Run Chart, and DOE factorial design still need
  stronger independent reference fixture coverage where feasible.
- Pearson and X-Y correlation still rely on generic option dictionaries plus
  method-local validators.
- No new statistical method or fake result was added.

Next PR:

- Add independent reference fixtures for partial quality/DOE methods, or add
  typed adapters for `regression.pearson` and `regression.xy_correlation`.

## Progress Update 89 - EDA Option Contract Expansion

Completed in current working tree:

- Added `GraphicalSummaryOptions` typed request adapter for
  `eda.graphical_summary`.
- Added `NormalityOptions` typed request adapter for `eda.normality`.
- Added `EqualVariancesOptions` typed request adapter for
  `eda.equal_variances`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_graphical_summary_options`
  - `invalid_normality_options`
  - `invalid_equal_variances_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix, Gate B progress notes, and CI
  status to record typed contract coverage.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation:

- Targeted Windows pytest for the three new typed-option contracts: passed with
  9 selected tests.
- Targeted backend ruff format/check for touched backend files passed.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 338
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Several quality chart methods still use generic `options` dictionaries plus
  method-local validators.
- Capability, Gage R&R, Gage Run Chart, and DOE factorial design still need
  stronger independent reference fixture coverage where feasible.
- No new statistical method or fake result was added.

Next PR:

- Continue typed adapter coverage for remaining quality chart payloads, or add
  independent reference fixtures for the currently partial quality methods.

## Progress Update 91 - Descriptive and Correlation Option Contract Expansion

Completed in current working tree:

- Added `DescriptiveOptions` typed request adapter for `eda.descriptive`.
- Added `PearsonOptions` typed request adapter for `regression.pearson`.
- Added `XyCorrelationOptions` typed request adapter for
  `regression.xy_correlation`.
- Wired all three adapters at runner entry before row snapshot or result
  artifact creation.
- Added stable sanitized error codes:
  - `invalid_descriptive_options`
  - `invalid_pearson_options`
  - `invalid_xy_correlation_options`
- Added API contract tests that invalid option types, missing required options,
  and unknown option fields fail without echoing raw invalid values or unknown
  field names in the response.
- Added frontend analysis error guidance for all three new error codes.
- Updated the statistical method audit matrix, Gate B progress notes, and CI
  status to record typed contract coverage.
- Kept statistical calculations, method availability, result schemas,
  migrations, storage paths, and normal frontend payloads unchanged.

Validation:

- Targeted Windows pytest for the three new typed-option contracts: passed with
  9 selected tests.
- Targeted backend ruff format/check for touched backend files passed.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 357
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Capability, Gage R&R, Gage Run Chart, and DOE factorial design still need
  stronger independent reference fixture coverage where feasible.
- DOE design/response routes use dedicated request schemas rather than generic
  analysis-run option adapters.
- No new statistical method or fake result was added.

Next PR:

- Add independent reference fixtures for partial quality/DOE methods, or start
  stabilizing report/export contracts.

## Progress Update 92 - Quality and DOE Fixture Coverage Expansion

Completed in current working tree:

- Added fixture-backed regression coverage for `quality.capability`.
  - Covers two-sided target and one-sided/exclusion cases.
  - Pins hand-calculated sample SD, moving-range within sigma, capability
    indices, observed/expected nonconformance, and warnings.
- Added fixture-backed regression coverage for `quality.gage_rr`.
  - Covers balanced crossed ANOVA with positive interaction variance.
  - Covers additive data where raw part-operator variance is negative and final
    variance is clamped to zero.
  - Pins ANOVA SS/MS/F/p fields, variance components, ndc, warnings, and label
    redaction behavior.
- Added fixture-backed regression coverage for `quality.gage_run_chart`.
  - Pins balanced diagnostic summaries, order-column sorting, first chart point
    indexes, warnings, and raw label redaction.
- Added fixture-backed regression coverage for `doe.factorial_design`.
  - Pins 2-factor standard order plus center point levels.
  - Pins design SHA-256 and seeded randomized/block run ordering for a
    3-factor design.
- Updated the statistical method audit matrix and Gate B progress notes to
  record the stronger-but-still-partial quality/DOE fixture coverage.
- Kept all method availability, calculation formulas, result schemas, API
  routes, migrations, and frontend behavior unchanged.
- Added no new statistical method, DOE effects, fake result, fake chart, or mock
  statistic.

Validation:

- Targeted Windows pytest for `test_capability.py`, `test_gage_rr.py`,
  `test_gage_run_chart.py`, and `test_factorial_design.py`: passed with 16
  tests.
- Targeted backend ruff check passed for the four touched test files.
- Targeted backend ruff format check passed after formatting
  `test_capability.py`.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 361
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- Capability and Gage R&R still lack independent industrial software reference
  fixture comparison.
- `doe.factorial_design` fixture covers design assets only; DOE effects,
  OLS/ANOVA, diagnostics, alias structure, and DOE charts remain out of scope.
- Gage Run Chart remains a diagnostic chart payload and does not replace Gage
  R&R variance components.

Next PR:

- Start report/export contract stabilization, or continue quality reference
  hardening with an approved independent benchmark source for capability and
  Gage R&R.

## Progress Update 93 - Analysis Result JSON Export Contract

Completed in current working tree:

- Added a typed `AnalysisResultJsonExportResponse` API schema.
- Added `POST /api/v1/analysis-runs/{analysis_id}/exports/json`.
- The export service:
  - reloads and checksum-validates the stored analysis result before exporting;
  - writes an atomic JSON export artifact under the analysis workspace;
  - records the artifact as `analysis_result_json_export` in
    `analysis_artifacts`;
  - returns export ID, media type, SHA-256, byte size, source result SHA-256,
    stale flag, created time, and the exported result envelope;
  - omits internal relative paths, absolute paths, and raw workspace locations
    from the API response.
- Added frontend API type and typed client function
  `createAnalysisResultJsonExport` without adding UI surface yet.
- Added API contract tests for successful JSON export artifact creation and
  checksum-mismatch rejection without creating an export artifact.
- Kept CSV, HTML, PDF, chart image export, report composition, and code export
  out of scope for this slice.

Validation:

- Targeted Windows pytest for the new export route: passed with 2 selected
  tests.
- Targeted backend ruff format/check for touched backend files passed after
  import sorting.
- Frontend typecheck passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 75 source files, backend pytest 363
  tests, frontend lint/typecheck, frontend Vitest 40 tests, and frontend build.

Remaining limitations:

- The route creates JSON export artifacts but does not yet provide a browser UI
  button or file download response.
- CSV/HTML/PDF/report/code exports are still unimplemented.
- Export retention/deletion policy is still inherited from generic analysis
  artifact storage and needs a dedicated report/export lifecycle slice.

Next PR:

- Add a minimal frontend export action for saved result JSON, then define CSV
  table export and HTML report contracts with formula-injection and path
  exposure tests.

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
  for created JSON/CSV result export artifacts.
- Added metadata lookup for a single `analysis_artifacts` record by
  `analysis_id` and `artifact_id`.
- The download service accepts only JSON/CSV result export artifact kinds,
  validates relative path safety, file existence, and SHA-256 before returning
  bytes, and keeps internal relative/absolute workspace paths out of responses.
- Added stable recovery errors:
  - `analysis_export_not_found`
  - `analysis_export_path_invalid`
  - `analysis_export_file_missing`
  - `analysis_export_checksum_mismatch`
- Added frontend download buttons to matching JSON/CSV export metadata cards and
  displays download failures inside the export panel.
- No new statistical method, fake statistic, fake chart, HTML/PDF report, or
  chart export artifact was added.

Validation:

- Targeted pytest through the Windows Python venv from WSL:
  `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_result_export"`:
  passed with 2 selected tests on Python 3.10.11 / win32.
- WSL `npm --prefix ./frontend run typecheck`: passed.
- WSL `npm --prefix ./frontend run test -- --run`: passed with 44 tests.
- Full Windows `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command
  "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`: passed with backend
  ruff check, backend ruff format check, backend mypy over 75 source files,
  backend pytest 367 tests, frontend lint/typecheck, frontend Vitest 44 tests,
  and frontend build.

Remaining limitations:

- CSV export is still a generic result-envelope table, not a method-specific
  statistical report table.
- HTML/PDF report composition, code export, and chart artifact export remain out
  of scope.
- Export retention/deletion policy still uses the generic analysis artifact
  lifecycle.

Next PR:

- Define the first HTML report envelope or method-specific CSV/table export
  contract with checksum validation, no path exposure, and spreadsheet
  formula-injection tests.

## Progress Update 97 - Analysis Result HTML Report Export

Completed in current working tree:

- Added `POST /api/v1/analysis-runs/{analysis_id}/exports/html`.
- The service reloads and checksum-validates the stored result envelope before
  writing the HTML report artifact.
- The report is stored as `analysis_result_html_report` with `text/html`
  metadata, SHA-256, size, stale flag, source result SHA-256, and section count.
- The generated report is static and self-contained:
  - all result text is HTML-escaped;
  - no script tag or external resource is required;
  - no relative/absolute workspace path is exposed;
  - no new statistical calculation is performed.
- Existing export download now supports JSON, CSV, and HTML report artifacts
  through the same analysis artifact lookup, relative path validation, file
  existence check, and SHA-256 verification path.
- Added frontend API type/client wiring plus `HTML 생성` and `HTML 다운로드`
  controls in the Workbench export panel.
- Added API contract tests for escaped HTML report creation/download and stored
  result checksum mismatch rejection without creating an HTML artifact.
- Added frontend render coverage for HTML report action/metadata.

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

- HTML report is a generic result-envelope report, not a method-specific
  narrative/report template.
- PDF, multi-analysis report composition, chart image export, and reproducible
  Python code export remain out of scope.
- Export retention/deletion policy still uses the generic analysis artifact
  lifecycle.

Next PR:

- Add method-specific report sections for one narrow method family, or define
  reproducible Python code export with provenance, checksum, and path-exposure
  tests.

## Progress Update 98 - Descriptive HTML Report Section

Completed in current working tree:

- Added the first method-specific HTML report section for `eda.descriptive`.
- The HTML report now includes a dedicated `기술통계 요약` table before the
  generic result-envelope table.
- The section displays stored result values only:
  - display name;
  - N total / N used;
  - missing and non-numeric counts;
  - mean, sample standard deviation, min, Q1, median, Q3, max;
  - warning codes.
- The section does not read canonical rows, re-run descriptive statistics, or
  alter the analysis result schema.
- Generic envelope fallback remains for every method, including descriptive.
- Existing XSS/path-exposure protections stay in place by HTML-escaping every
  rendered value and keeping internal workspace paths out of the report.

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
- Report styling remains basic and local/static.
- PDF, chart image export, multi-analysis report composition, and reproducible
  Python code export remain out of scope.

Next PR:

- Add method-specific report sections for one more narrow method family, or
  start the reproducible Python code export contract with provenance and
  checksum tests.

## Progress Update 99 - EDA HTML Report Sections

Completed:

- Added method-specific HTML report sections for stored `eda.graphical_summary`,
  `eda.normality`, and `eda.equal_variances` results.
- Kept all report sections stored-result-only: no canonical row reads, no
  statistical recalculation, no fake chart artifact, and no new available
  methods.
- Added API contract coverage that creates each EDA result through
  `/api/v1/analysis-runs`, exports HTML through
  `/api/v1/analysis-runs/{analysis_id}/exports/html`, and verifies the rendered
  section text/key values from the checksum-recorded artifact.
- Updated storage documentation to list the supported method-specific HTML
  report sections.

Validation:

- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  3 passed, 173 deselected.
- `./.venv/Scripts/python.exe -m ruff check ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/services/analysis_runs.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed after applying ruff formatting; backend pytest 370 passed, frontend
  Vitest 45 passed, frontend build passed.

Next:

- Add method-specific HTML sections for the next narrow family, likely
  hypothesis tests, or begin reproducible Python code export.

## Progress Update 100 - Hypothesis HTML Report Sections

Completed:

- Added method-specific HTML report sections for stored generic
  `hypothesis.*` analysis-run results.
- Covered the current available hypothesis summary types:
  - `one_sample_t_test`;
  - `paired_t_test`;
  - `one_sample_wilcoxon_signed_rank_test`;
  - `two_sample_t_test`;
  - `mann_whitney_u_test`;
  - `kruskal_wallis_test`;
  - `one_way_anova`;
  - `equivalence_tost`.
- The sections render stored result values only: N, alpha, confidence level,
  estimate, statistic, p-value, confidence interval, effect size, equivalence
  bounds/TOST p-values, group summaries, and post-hoc comparisons when present.
- Added API contract coverage for representative contrast, post-hoc, and TOST
  payload paths through the existing HTML export endpoint.
- Updated storage documentation to include hypothesis method-specific HTML
  report sections.

Validation so far:

- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  4 passed, 173 deselected.
- `./.venv/Scripts/python.exe -m ruff check ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/services/analysis_runs.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 371 passed, frontend Vitest 45 passed, frontend
  build passed.

Next:

- Continue with categorical/regression HTML sections or reproducible Python code
  export.

## Progress Update 101 - Categorical And Regression HTML Report Sections

Completed:

- Added method-specific HTML report sections for stored categorical results:
  `one_proportion_test`, `two_proportion_test`, and
  `chi_square_association`.
- Added method-specific HTML report sections for stored regression/correlation
  results: `pearson_correlation`, `xy_correlation_matrix`, and `linear_model`.
- Added aggregate categorical tables for group/event counts and contingency
  table observed counts.
- Added regression tables for pairwise correlations and linear-model
  coefficients.
- Kept all sections stored-result-only: no canonical row reads, no statistical
  recalculation, no fake chart artifact, and no new available methods.
- Added API contract coverage for representative categorical and regression
  payloads through `/api/v1/analysis-runs/{analysis_id}/exports/html`.
- Updated storage documentation to list the new method-specific HTML report
  sections.

Validation:

- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  6 passed, 173 deselected.
- `./.venv/Scripts/python.exe -m ruff check ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/services/analysis_runs.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 373 passed, frontend Vitest 45 passed, frontend
  build passed.

Next:

- Continue with quality-control HTML sections or reproducible Python code
  export.

## Progress Update 102 - Quality HTML Report Sections

Completed:

- Added method-specific HTML report sections for stored quality-control
  results: `individuals_chart`, `subgroup_chart`, `run_chart`,
  `capability_analysis`, `gage_rr`, and `gage_run_chart`.
- Added aggregate quality tables for chart summaries, control/run signals,
  process capability indices, and Gage R&R variance components.
- Kept all sections stored-result-only: no canonical row reads, no control-limit
  recalculation, no fake chart artifact, no raw Gage label exposure, and no new
  available methods.
- Added API contract coverage for representative quality chart, capability,
  Gage R&R, and Gage run-chart payloads through
  `/api/v1/analysis-runs/{analysis_id}/exports/html`.
- Updated storage documentation to list quality method-specific HTML report
  sections.

Validation:

- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "html_report_export"`:
  8 passed, 173 deselected.
- `./.venv/Scripts/python.exe -m ruff check ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/services/analysis_runs.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 375 passed, frontend Vitest 45 passed, frontend
  build passed.

Next:

- Add a DOE design HTML report section or start reproducible Python code
  export.

## Progress Update 103 - DOE Design HTML Report Download

Completed:

- Added `GET /api/v1/doe-designs/{design_id}/report.html` for dedicated
  DOE factorial design reports.
- The report reads the stored DOE design metadata and response series only
  after existing `design_sha256` verification succeeds.
- The generated HTML is static and self-contained:
  - text content is HTML-escaped;
  - no scripts or external resources are referenced;
  - internal workspace paths are not exposed;
  - attachment filename is derived from the design ID only.
- Kept DOE effects, OLS, ANOVA, diagnostics, alias structure, chart payloads,
  analysis-run artifacts, fake statistics, and mock charts out of scope.
- Added API contract coverage for normal report download, response rendering,
  escaping/path non-exposure, and checksum mismatch rejection.
- Updated storage/progress documentation to distinguish DOE design reports from
  generic analysis-run result exports.

Validation:

- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "factorial_design"`:
  7 passed, 176 deselected.
- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/doe_designs.py ./backend/app/services/doe_designs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/doe_designs.py ./backend/app/services/doe_designs.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 377 passed, frontend Vitest 45 passed, frontend
  build passed.

Limitations:

- DOE report is a design/response report only; it is not an effects or
  analysis report.
- The report is generated dynamically from verified metadata and is not yet
  persisted as an export artifact.
- Frontend download wiring is not added in this slice.

Next:

- Add a small frontend button for DOE report download, or start reproducible
  Python code export for stored analysis results.

## Progress Update 104 - Analysis History, Export Listing, And Method Version Policy

Completed:

- Added a metadata-only saved analysis history API:
  `GET /api/v1/analysis-runs?dataset_version_id={id}&limit=50&offset=0`.
  The response is paginated, newest-first, includes stale/result/artifact
  status, and excludes raw result payloads, raw cell values, and internal
  workspace paths.
- Added `GET /api/v1/analysis-runs/{analysis_id}/exports` for listing created
  JSON/CSV/HTML export artifacts with export ID, kind, media type, SHA-256,
  created time, and download URL only.
- Added a minimal Workbench saved-analysis section that refreshes stored runs,
  shows stale badges, restores a stored result through the checksum-validated
  result API, and shows recent export artifacts with download buttons.
- Added `docs/method_versioning.md` to document patch/minor/major bump rules,
  frontend-only change handling, reference fixture update expectations, and
  no-silent-migration behavior for stored result envelopes.
- Updated `docs/statistical_method_audit_matrix.md` with an independent
  reference backlog for partial-coverage high-risk methods:
  `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`,
  `doe.factorial_design`, and `regression.linear_model`.
- Strengthened export/report security tests for CSV formula-injection
  sanitization, HTML escaping/CSP, download `nosniff`, SHA-256 ETag metadata,
  checksum mismatch recovery, and internal-path non-exposure.
- Kept new statistical methods, method-version bumps, fake statistics, DOE
  effects/ANOVA, PDF/code exports, and chart export artifacts out of scope.

Validation:

- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_list or export_list or formula_like or export_downloads or html_report_export_creates"`:
  5 passed, 181 deselected.
- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/analysis_runs.py ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/app/storage/metadata.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/analysis_runs.py ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/app/storage/metadata.py`:
  passed.
- `npm --prefix ./frontend run lint`: passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 47 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 380 tests, frontend lint/typecheck, frontend
  Vitest 47 tests, and frontend build.

Limitations:

- Saved-analysis history is intentionally metadata-only and has no search,
  grouping, comparison, or bulk deletion UI yet.
- Export listing covers created JSON/CSV/HTML analysis-run exports only; DOE
  design reports remain dedicated dynamic downloads, not stored analysis export
  artifacts.
- CSV export remains a generic result-envelope table. Method-specific CSV
  tables, PDF reports, reproducible code export, and chart artifact exports are
  still planned.
- Method-version policy is documented, but current stable method versions
  remain `0.1.0`.
- Remote GitHub Actions run/status is still not verified from this environment.

Next:

- Add user-facing comparison/filtering for saved analysis history, or start a
  reproducible Python code export contract with provenance, checksum, and
  path-exposure tests.

## Progress Update 105 - Saved Analysis History Filtering And Paging

Completed:

- Extended `GET /api/v1/analysis-runs` with metadata-only filters for
  `method_id`, `status`, `stale`, and `result_available`.
- Added `has_more` to the analysis history response so the frontend can page
  without requiring a total count query.
- Kept filtering limited to analysis-run metadata. The endpoint still excludes
  raw result payloads, raw cell values, `result_path`, and internal workspace
  paths.
- Added Workbench history controls for method, status, stale state, and result
  availability, plus previous/next page buttons.
- Kept browser state bounded to the current page of history and the selected
  restored result; no full analysis history or raw dataset is loaded into the
  browser.
- Updated frontend API wrappers and render tests for the filtered history query
  contract.
- Kept new statistical methods, method-version bumps, report composition, PDF
  export, reproducible code export, and chart export artifacts out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/analysis_runs.py ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/app/storage/metadata.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/analysis_runs.py ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/app/storage/metadata.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_list or export_list or formula_like or export_downloads or html_report_export_creates"`:
  5 passed, 181 deselected.
- `npm --prefix ./frontend run lint`: passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 47 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 380 tests, frontend lint/typecheck, frontend
  Vitest 47 tests, and frontend build.

Limitations:

- History still has no text search, method-family grouping, result comparison,
  favorite/pin state, bulk deletion, or export bundle generation.
- The response does not return a total count; `has_more` is enough for current
  previous/next paging but not for numbered pages.
- Reproducible Python code export remains planned and should be designed
  separately so it does not imply statistical recomputation without the exact
  dataset/version contract.

Next:

- Add saved-result comparison for two compatible history entries, or begin the
  reproducible Python code export contract with explicit data-version,
  provenance, checksum, and path-exposure tests.

## Progress Update 106 - Saved Analysis Result Comparison

Completed:

- Added `GET /api/v1/analysis-runs/comparison` for comparing two stored
  analysis results by `left_analysis_id` and `right_analysis_id`.
- The comparison service uses the same checksum-validated stored result loading
  path as result restore/export. It does not recalculate statistics.
- The response is metadata-only: method/version/dataset/summary compatibility,
  stale flags, result SHA-256, warning counts, row-count provenance,
  schema/filter/row snapshot hashes, and field-level metadata differences.
- The comparison response excludes raw result payloads, raw cell values,
  `result_path`, and internal workspace paths.
- Same-analysis comparison is rejected with
  `analysis_comparison_requires_two_runs`.
- Different method/summary comparisons return `comparable=false` instead of
  fabricating a cross-method result comparison.
- Added Workbench controls to choose left/right saved runs from the current
  history page and display comparison compatibility plus metadata differences.
- Updated frontend API wrappers, types, and render/API tests for the comparison
  route.
- Kept new statistical methods, method-version bumps, result recomputation,
  PDF export, reproducible code export, and chart export artifacts out of
  scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/analysis_runs.py ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/analysis_runs.py ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_comparison or analysis_run_list or export_list"`:
  3 passed, 184 deselected.
- `npm --prefix ./frontend run lint`: passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 47 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 381 tests, frontend lint/typecheck, frontend
  Vitest 47 tests, and frontend build.

Limitations:

- Comparison is metadata/provenance/result-hash comparison only. It does not
  compute method-specific numeric deltas yet.
- The UI compares runs on the current history page only; search and pinned
  comparison selections across pages are still planned.
- Cross-method comparisons are intentionally marked incompatible rather than
  interpreted.

Next:

- Add method-specific safe comparison renderers for a narrow method such as
  `eda.descriptive`, or start the reproducible Python code export contract with
  explicit data-version, provenance, checksum, and path-exposure tests.

## Progress Update 107 - Descriptive Stored-Result Comparison

Completed:

- Extended the stored analysis comparison response with optional
  method-specific comparison payloads.
- Added the first method-specific comparison for compatible `eda.descriptive`
  stored results.
- The descriptive comparison matches common columns by `column_id` and returns
  left/right/delta for saved summary metrics: `n_total`, `n_used`,
  `n_missing`, `n_non_numeric`, `mean`, `std`, `min`, `q1`, `median`, `q3`,
  and `max`.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, or recompute descriptive statistics.
- The response records left-only and right-only column IDs for column-set drift.
- The Workbench comparison panel now renders a 기술통계 비교 table when the
  comparison payload contains descriptive metrics.
- Updated backend API contract tests and frontend render/API fixtures for the
  descriptive comparison payload.
- Kept new statistical methods, method-version bumps, cross-method numeric
  interpretation, PDF export, reproducible code export, and chart export
  artifacts out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed after import sorting.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_comparison"`:
  1 passed, 186 deselected.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 47 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 381 tests, frontend lint/typecheck, frontend
  Vitest 47 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented only for
  `eda.descriptive`.
- The descriptive comparison reports simple stored-summary deltas; it does not
  perform statistical tests on differences or infer practical significance.
- Column matching uses `column_id`; renamed display labels do not create a new
  match key.

Next:

- Add a similarly stored-result-only comparison for a narrow inferential method
  such as `hypothesis.one_sample_t`, or begin the reproducible Python code
  export contract with explicit data-version, provenance, checksum, and
  path-exposure tests.

## Progress Update 108 - One-Sample T Stored-Result Comparison

Completed:

- Extended the stored analysis comparison method-specific payload with
  `one_sample_t_test`.
- Added stored-result-only comparison for compatible `hypothesis.one_sample_t`
  runs.
- The one-sample t comparison reports response-column identity, saved setting
  differences (`alternative`, `alpha`, `confidence_level`, `null_mean`,
  `missing_policy`), and left/right/delta for saved sample and contrast
  metrics.
- The compared metrics include N/exclusion counts, sample mean/std/min/max,
  contrast estimate, standard error, degrees of freedom, statistic, p-value,
  confidence interval bounds, and effect-size fields.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, or recompute t-tests.
- The Workbench comparison panel now renders a `1-표본 t-검정 비교` table when
  the comparison payload contains one-sample t metrics.
- Updated backend API contract tests and frontend render fixtures for the
  one-sample t comparison payload.
- Kept new statistical methods, method-version bumps, cross-method numeric
  interpretation, PDF export, reproducible code export, chart export artifacts,
  and new t-test calculations out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_comparison"`:
  2 passed, 186 deselected.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 48 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 382 tests, frontend lint/typecheck, frontend
  Vitest 48 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented only for
  `eda.descriptive` and `hypothesis.one_sample_t`.
- The one-sample t comparison reports stored-result deltas only; it does not
  test whether two estimates differ from each other or infer practical
  significance.
- The UI compares runs on the current history page only; search and pinned
  comparison selections across pages are still planned.

Next:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.two_sample_t` or start the reproducible Python code export
  contract with explicit data-version, provenance, checksum, and path-exposure
  tests.

## Progress Update 109 - Two-Sample T Stored-Result Comparison

Completed:

- Extended the stored analysis comparison method-specific payload with
  `two_sample_t_test`.
- Added stored-result-only comparison for compatible `hypothesis.two_sample_t`
  runs.
- The two-sample t comparison reports response/group column identity, group
  set/order compatibility, saved setting differences (`alternative`, `alpha`,
  `confidence_level`, `variance_assumption`, `null_difference`,
  `missing_policy`), and left/right/delta for saved group summary and contrast
  metrics.
- The compared metrics include N/exclusion counts, stored group-index
  mean/std/N summaries, contrast estimate, standard error, degrees of freedom,
  statistic, p-value, confidence interval bounds, and effect-size fields.
- The comparison intentionally does not expose group-label values because they
  can be raw dataset cell values; it only reports group-set/order compatibility.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, or recompute t-tests.
- The Workbench comparison panel now renders a `2-표본 t-검정 비교` table when
  the comparison payload contains two-sample t metrics.
- Updated backend API contract tests and frontend render fixtures for the
  two-sample t comparison payload.
- Kept new statistical methods, method-version bumps, cross-method numeric
  interpretation, PDF export, reproducible code export, chart export artifacts,
  and new t-test calculations out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_comparison"`:
  3 passed, 186 deselected.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 49 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 383 tests, frontend lint/typecheck, frontend
  Vitest 49 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, and `hypothesis.two_sample_t`.
- The two-sample t comparison reports stored-result deltas only; it does not
  test whether two saved contrasts differ from each other or infer practical
  significance.
- Group summary metrics are keyed by stored group order. The response reports
  whether group-label order is identical but does not expose the label values.
- The UI compares runs on the current history page only; search and pinned
  comparison selections across pages are still planned.

Next:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.paired_t`, or start the reproducible Python code export contract
  with explicit data-version, provenance, checksum, and path-exposure tests.

## Progress Update 110 - Paired T Stored-Result Comparison

Completed:

- Extended the stored analysis comparison method-specific payload with
  `paired_t_test`.
- Added stored-result-only comparison for compatible `hypothesis.paired_t`
  runs.
- The paired t comparison reports before/after column identity, saved setting
  differences (`alternative`, `alpha`, `confidence_level`, `null_difference`,
  `missing_policy`, `difference_definition`), and left/right/delta for saved
  complete-pair, paired-sample, contrast, and effect-size metrics.
- The compared metrics include total/used N, incomplete and non-numeric pair
  exclusions, before/after means, mean/median/std/min/max pair differences,
  signed difference counts, contrast statistic/p-value/CI, and effect-size
  fields.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, or recompute t-tests.
- The Workbench comparison panel now renders a `대응표본 t-검정 비교` table when
  the comparison payload contains paired t metrics.
- Updated backend API contract tests and frontend render fixtures for the
  paired t comparison payload.
- Kept new statistical methods, method-version bumps, cross-method numeric
  interpretation, PDF export, reproducible code export, chart export artifacts,
  and new t-test calculations out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_comparison"`:
  4 passed, 186 deselected.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 50 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 384 tests, frontend lint/typecheck, frontend
  Vitest 50 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, `hypothesis.two_sample_t`, and
  `hypothesis.paired_t`.
- The paired t comparison reports stored-result deltas only; it does not test
  whether two saved paired contrasts differ from each other or infer practical
  significance.
- The UI compares runs on the current history page only; search and pinned
  comparison selections across pages are still planned.

Next:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.equivalence_tost`, or start the reproducible Python code export
  contract with explicit data-version, provenance, checksum, and path-exposure
  tests.

## Progress Update 111 - Equivalence TOST Stored-Result Comparison

Completed:

- Extended the stored analysis comparison method-specific payload with
  `equivalence_tost`.
- Added stored-result-only comparison for compatible
  `hypothesis.equivalence_tost` runs.
- The TOST comparison reports response-column identity, saved equivalence
  bounds/reference/alpha settings, lower/upper one-sided test decisions, TOST
  decision fields, and left/right/delta for saved sample, estimate, one-sided
  p-value, TOST p-value, confidence interval, and effect-size metrics.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, or recompute TOST statistics.
- The Workbench comparison panel now renders a `동등성 TOST 비교` table when
  the comparison payload contains TOST metrics.
- Updated backend API contract tests and frontend render fixtures for the
  TOST comparison payload.
- Kept new statistical methods, method-version bumps, cross-method numeric
  interpretation, PDF export, reproducible code export, chart export artifacts,
  and new TOST calculations out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `./.venv/Scripts/python.exe -m mypy ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py`:
  passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "analysis_run_comparison"`:
  5 passed, 186 deselected.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 51 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 385 tests, frontend lint/typecheck, frontend
  Vitest 51 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, `hypothesis.two_sample_t`,
  `hypothesis.paired_t`, and `hypothesis.equivalence_tost`.
- The TOST comparison reports stored-result deltas only; it does not infer
  whether two saved equivalence decisions differ in a practically meaningful
  way beyond the recorded settings/results.
- The UI compares runs on the current history page only; search and pinned
  comparison selections across pages are still planned.

Next:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.one_way_anova`, or start the reproducible Python code export
  contract with explicit data-version, provenance, checksum, and path-exposure
  tests.

## Progress Update 112 - One-Way ANOVA Stored-Result Comparison

Completed:

- Extended the stored analysis comparison method-specific payload with
  `one_way_anova`.
- Added stored-result-only comparison for compatible
  `hypothesis.one_way_anova` runs.
- The ANOVA comparison reports response/group column identity, group-set/order
  compatibility without raw group-label values, saved method/alpha/posthoc
  settings, group summary deltas by stored group index, ANOVA table/test/effect
  deltas, and post-hoc comparison-count metadata.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, recompute ANOVA statistics, or expose
  stored result payloads/internal paths.
- The Workbench comparison panel now renders an `일원분산분석 비교` table when the
  comparison payload contains ANOVA metrics.
- Updated backend API contract tests and frontend render fixtures for the ANOVA
  comparison payload.
- Kept Welch ANOVA, Games-Howell, two-way/repeated/ANCOVA, method-version
  bumps, new statistical calculations, PDF export, reproducible code export,
  and chart export artifacts out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "comparison_api_returns_one_way_anova or analysis_run_comparison"`:
  6 passed, 186 deselected.
- `npm --prefix ./frontend run test -- --run`: passed with 52 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 386 tests, frontend lint/typecheck, frontend
  Vitest 52 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, `hypothesis.two_sample_t`,
  `hypothesis.paired_t`, `hypothesis.equivalence_tost`, and
  `hypothesis.one_way_anova`.
- The ANOVA comparison reports stored-result deltas only; it does not infer
  practical significance or compare post-hoc group labels by name.
- Group summaries are compared by stored group index to avoid raw group-label
  exposure.

Next:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.kruskal_wallis`, or start the reproducible Python code export
  contract with explicit data-version, provenance, checksum, and path-exposure
  tests.

## Progress Update 113 - Kruskal-Wallis Stored-Result Comparison

Completed:

- Extended the stored analysis comparison method-specific payload with
  `kruskal_wallis`.
- Added stored-result-only comparison for compatible
  `hypothesis.kruskal_wallis` runs.
- The Kruskal-Wallis comparison reports response/group column identity,
  group-set/order compatibility without raw group-label values, saved
  method/alpha/posthoc/tie settings, group rank-summary deltas by stored group
  index, H-test/effect deltas, and post-hoc comparison-count metadata.
- The service uses only checksum-validated stored result envelopes. It does not
  reread canonical rows, reparse uploads, recompute Kruskal-Wallis statistics,
  or expose stored result payloads/internal paths.
- The Workbench comparison panel now renders a `Kruskal-Wallis 비교` table when
  the comparison payload contains Kruskal-Wallis metrics.
- Updated backend API contract tests and frontend render fixtures for the
  Kruskal-Wallis comparison payload.
- Kept new statistical calculations, Mann-Whitney comparison, Wilcoxon
  comparison, method-version bumps, PDF export, reproducible code export, and
  chart export artifacts out of scope.

Validation:

- `./.venv/Scripts/python.exe -m ruff check ./backend/app/api/v1/schemas/analyses.py ./backend/app/services/analysis_runs.py ./backend/tests/unit/test_api_contracts.py`:
  passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `./.venv/Scripts/python.exe -m pytest ./backend/tests/unit/test_api_contracts.py -k "comparison_api_returns_kruskal_wallis or analysis_run_comparison"`:
  7 passed, 186 deselected.
- `npm --prefix ./frontend run test -- --run`: passed with 53 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 53 tests, and frontend build.

Limitations:

- Method-specific numeric comparison is currently implemented for
  `eda.descriptive`, `hypothesis.one_sample_t`, `hypothesis.two_sample_t`,
  `hypothesis.paired_t`, `hypothesis.equivalence_tost`,
  `hypothesis.one_way_anova`, and `hypothesis.kruskal_wallis`.
- The Kruskal-Wallis comparison reports stored-result deltas only; it does not
  infer practical significance or compare post-hoc group labels by name.
- Group summaries are compared by stored group index to avoid raw group-label
  exposure.

Next:

- Add another stored-result-only comparison for a narrow method such as
  `hypothesis.mann_whitney`, or start the reproducible Python code export
  contract with explicit data-version, provenance, checksum, and path-exposure
  tests.

## Progress Update 114 - Beginner Role Guidance And Purpose Helper

Completed:

- Added always-visible beginner role guidance to the Workbench for
  Response/Y, Group, Predictor/X, Event level, Order, Subgroup, Part,
  Operator, Replicate, and LSL/USL/Target.
- Each role guide entry includes what the role means, common examples, and a
  one-line risk explaining how the analysis can go wrong if the role is
  misassigned.
- Added a purpose-based helper section, `무엇을 알고 싶나요?`, that maps common
  beginner questions to existing method IDs such as `eda.graphical_summary`,
  `hypothesis.two_sample_t`, `regression.pearson`, `quality.capability`,
  `quality.gage_rr`, and `doe.factorial_design`.
- Helper cards only move the user to a method for review. They do not auto-run
  analyses, and planned/disabled/catalog-missing methods are not shown as
  executable actions.
- Added a common preflight explanation panel that clarifies use-row counts,
  exclusions, complete-case missingness, selected role requirements, selected
  method/version, independence assumptions, what the analysis can support, and
  what it cannot conclude from p-values alone.
- Kept backend API behavior, method availability, statistical formulas, method
  versions, fake results, new methods, and large UI redesigns out of scope.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run lint`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 54 tests.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 54 tests, and frontend build.

Limitations:

- The helper is guidance-only. It does not inspect the currently selected
  column controls or infer the correct method automatically.
- Preflight explanation is common copy plus method role requirements; detailed
  method-specific N/exclusion numbers still come from each actual result or
  preflight payload.
- Chart export artifacts, reproducible code export, and additional stored
  result comparisons remain out of scope.

Next:

- Add a lightweight method-choice wizard that can read selected column roles
  and suggest candidate methods without executing them, or continue stored
  result comparison coverage for one more existing method.

## Progress Update 115 - Workbench Maintainability And Saved-Result UX Refinement

Completed:

- Split the large Workbench UI into focused components:
  `StatisticalRoleGuide.tsx`, `MethodPurposeHelper.tsx`,
  `PreflightExplanationPanel.tsx`, `AnalysisHistoryPanel.tsx`,
  `AnalysisComparisonPanel.tsx`, and `AnalysisResultExportPanel.tsx`.
- Added shared Workbench types and formatting utilities for history filters,
  availability labels, short hashes, dates, bytes, and comparison values.
- Improved selected-method beginner guidance for two-sample t, paired t,
  capability, Gage R&R, and DOE factorial design without adding new statistical
  methods or fake results.
- Reworked the purpose helper card order so user questions and Korean method
  names come before method IDs; planned/disabled/catalog-missing methods remain
  non-executable.
- Refined saved analysis history copy and states for current dataset context,
  filter status, stale badges, unavailable result restore disabling,
  pagination, and restore summaries.
- Refined export copy and states for JSON/CSV/HTML use cases, stale export
  warnings, download recovery, and SHA display.
- Refined saved-result comparison copy for same/different compatibility,
  method-version mismatch, dataset-version mismatch, delta meaning, and p-value
  caveats.
- Documented the upload/paste -> confirm parsing -> schema role update -> run
  `eda.descriptive` -> run `hypothesis.two_sample_t` -> restore -> compare ->
  export JSON/CSV/HTML -> reload/restore E2E-like plan in
  `docs/progress_gate_b.md`.

Validation:

- `npm --prefix ./frontend run test -- --run`: passed with 58 tests.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run lint`: passed.
- `npm --prefix ./frontend run build`: passed with Vite's existing chunk-size
  warning.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 58 tests, and frontend build.

Limitations:

- Playwright E2E is still a documented next step, not implemented in this PR.
- The purpose helper does not infer the right method from selected columns.
- Frontend bundle code splitting is still future work; Vite reports the
  existing large chunk warning.

Next:

- Implement the documented Playwright critical path, or add the next narrow
  saved-result/export hardening slice such as reproducible code export.

## Progress Update 116 - Playwright Browser Critical Path

Completed:

- Added `playwright==1.61.0` to backend dev dependencies for local-only browser
  E2E smoke testing.
- Added `scripts/e2e.ps1` with opt-in Chromium installation and loopback-only
  E2E execution on separate test ports.
- Added `tests/e2e/critical_path.py`, which starts isolated backend/frontend
  servers, uses a temporary workspace, and drives Chromium through the critical
  workflow.
- Covered the first browser critical path:
  pasted TSV intake, parsing confirmation, dataset version creation,
  `eda.descriptive`, `hypothesis.two_sample_t`, JSON/CSV/HTML export creation,
  JSON download, saved-result restore, and saved-result comparison messaging.
- Updated `docs/setup.md`, `docs/dependency_review.md`,
  `docs/progress_gate_b.md`, and `docs/ci_status.md`.
- Kept new statistical methods, fake results, full Playwright suite expansion,
  and CI browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"`: passed.
- `.\.venv\Scripts\python.exe -m playwright install chromium`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 58 tests, and frontend build.

Limitations:

- Browser E2E is opt-in and not yet included in `scripts/check.ps1` or GitHub
  Actions.
- The browser smoke uses pasted TSV data. Browser file upload/XLSX and schema
  no-op stale behavior remain future E2E slices.
- Vite still reports the existing production chunk-size warning.

Next:

- Add a schema-update/no-op-stale browser E2E, or wire Playwright into CI with a
  controlled browser cache/install step.

## Progress Update 117 - Schema No-Op Stale Browser Coverage

Completed:

- Extended the Playwright critical path to cover schema stale behavior after
  stored analyses exist.
- Verified no-op `스키마 저장` does not show stale badges in saved analysis
  history.
- Verified changing the `Value` display name to `Measurement Value` and saving
  schema marks both stored analysis runs as `stale · 재검토 필요`.
- Tightened sidebar navigation selectors to exact-match `데이터셋` and `분석`.
- Kept backend stale logic, new statistical methods, fake results, method
  version changes, and CI browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend ruff check, backend ruff format check, backend mypy over
  75 source files, backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 58 tests, and frontend build.

Limitations:

- E2E remains opt-in and is not yet included in `scripts/check.ps1`.
- File upload and XLSX browser E2E are still future work.
- The browser test asserts UI stale badges; API stale payload coverage remains
  in backend tests.

Next:

- Add file upload/XLSX browser coverage, or add a CI workflow step for opt-in
  Playwright with browser caching.

## Progress Update 118 - XLSX File Upload Browser Coverage

Completed:

- Added browser E2E coverage for the actual file upload path using a synthetic
  `.xlsx` workbook.
- Verified the upload form, parsing options screen, parsing confirmation,
  dataset version creation, `2행` / `3컬럼` context, and preview column headers.
- Reused the existing opt-in Playwright script and temporary workspace
  isolation.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend ruff check, backend ruff format check, backend mypy over
  75 source files, backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 58 tests, and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- Browser CSV upload and multi-sheet XLSX selection are not part of this E2E
  slice.

Next:

- Add browser CSV upload/error recovery coverage or prepare the opt-in E2E for
  CI execution with browser caching.

## Progress Update 119 - CSV Upload And Empty-File Recovery Browser Coverage

Completed:

- Added browser E2E coverage for CSV file upload through the actual file input.
- Added upload failure recovery coverage: an empty `.csv` upload shows the
  stable `empty_file` code, then a valid CSV can be selected and confirmed
  without reloading the app.
- Used a Korean CSV filename to keep Unicode filename handling inside the
  browser smoke.
- Verified valid CSV parsing creates a dataset version with `3행`, `2컬럼`, and
  preview headers for `Batch` and `Measurement`.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend ruff check, backend ruff format check, backend mypy over
  75 source files, backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 58 tests, and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- Parser option editing, malformed-row recovery, and multi-sheet XLSX selection
  are not part of this E2E slice.

Next:

- Prepare the opt-in E2E for CI execution with browser caching or add
  parser-option editing coverage.

## Progress Update 120 - Parser Option Editing Browser Coverage

Completed:

- Added browser E2E coverage for editing parsing options before confirmation.
- The test uploads a CSV with a preamble row, turns on header-row parsing, sets
  `헤더 행` to `2`, and adds `MISSING` to the missing-token list.
- Verified the resulting dataset version uses `Alpha` and `Beta` as headers,
  has `2행` / `2컬럼` in the dataset context, and renders `MISSING` as
  `(missing)` in preview.
- Tightened E2E row/column count assertions to the dataset context bar instead
  of page-wide text, avoiding strict-mode collisions with metadata grids.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\check.ps1"`:
  passed with backend ruff check, backend ruff format check, backend mypy over
  75 source files, backend pytest 387 tests, frontend lint/typecheck, frontend
  Vitest 58 tests, and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- Delimiter editing, encoding changes, malformed-row recovery, and multi-sheet
  XLSX selection are not part of this E2E slice.

Next:

- Prepare the opt-in E2E for CI execution with browser caching or add
  delimiter-editing coverage.

## Progress Update 121 - Delimiter Editing Browser Coverage

Completed:

- Added browser E2E coverage for editing the delimiter before parsing
  confirmation.
- The test uploads a `.csv` file whose content is semicolon-delimited, then
  changes `구분자` to `semicolon` before confirming.
- Verified the resulting dataset version has `2행` / `2컬럼` in the dataset
  context and preview headers for `Category` and `Value`.
- Verified representative preview cells with table-cell scoped selectors to
  avoid UUID/text collisions.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- Full Windows `scripts/check.ps1`: passed after delimiter browser coverage with
  backend pytest 387 tests, frontend Vitest 58 tests, frontend lint/typecheck,
  and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- Encoding changes, malformed-row recovery, and multi-sheet XLSX selection are
  not part of this E2E slice.

Next:

- Prepare the opt-in E2E for CI execution with browser caching or add
  multi-sheet XLSX browser coverage.

## Progress Update 122 - Multi-Sheet XLSX Browser Coverage

Status: completed in the current working tree.

Completed:

- Added browser E2E coverage for uploading a multi-sheet XLSX workbook and
  selecting a named sheet before parsing confirmation.
- The synthetic workbook contains `Summary` and `Measurements` sheets. The test
  fills `시트명` with `Measurements` and verifies that canonical preview data
  comes from that sheet.
- Verified the resulting dataset version has `2행` / `2컬럼`, preview headers
  `Station` and `Reading`, and representative cells `S2` and `43`.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- Full Windows `scripts/check.ps1`: passed after multi-sheet XLSX browser
  coverage with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- Encoding changes and malformed-row recovery are not part of this E2E slice.

Next:

- Prepare the opt-in E2E for CI execution with browser caching or add
  malformed-row/encoding browser coverage.

## Progress Update 123 - Text Encoding Browser Coverage

Status: completed in the current working tree.

Completed:

- Added browser E2E coverage for selecting a text encoding before parsing
  confirmation.
- The test uploads a CP949-encoded CSV file with Korean headers and values,
  selects `cp949` from `인코딩`, confirms parsing, and verifies the decoded
  preview.
- Tightened Playwright selectors to use exact Korean header matching and
  representative text cells instead of duplicate numeric cells.
- Kept parser feature expansion, new statistical methods, fake results, and CI
  browser execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- First browser E2E attempt failed on duplicate numeric cell text; second failed
  on partial header matching. Both were selector issues and were fixed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- Full Windows `scripts/check.ps1`: passed after text encoding browser coverage
  with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- Malformed-row recovery is not part of this E2E slice.

Next:

- Prepare the opt-in E2E for CI execution with browser caching or add
  malformed-row browser coverage.

## Progress Update 124 - Parser Error-Recovery Browser Coverage

Status: completed in the current working tree.

Completed:

- Added browser E2E coverage for recovering from parser option errors on the
  same parsing screen.
- The XLSX sheet-selection test now enters a missing sheet name, verifies
  `xlsx_sheet_not_found`, then corrects the sheet to `Measurements` and confirms
  successfully.
- The text encoding test now uses a CP949 fixture with an ASCII sniffing prefix,
  verifies `text_decoding_failed` when the user confirms with `utf-8`, then
  switches to `cp949` and verifies decoded Korean preview headers and cells.
- Kept parser semantics, new statistical methods, fake results, and CI browser
  execution out of scope.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- First E2E attempt failed because the original CP949 fixture started with
  Korean text, so `utf-8` was correctly absent from detected encoding
  candidates. The fixture was changed to use an ASCII sniffing prefix.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- Full Windows `scripts/check.ps1`: passed after parser error-recovery browser
  coverage with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Limitations:

- E2E remains opt-in and is not included in `scripts/check.ps1`.
- General malformed-row behavior remains lower-level/parser coverage because
  the canonical row reader intentionally pads short rows.

Next:

- Prepare the opt-in E2E for CI execution with browser caching or add another
  parser validation recovery case.

## Progress Update 125 - Browser E2E GitHub Actions Job

Status: completed in the current working tree.

Completed:

- Added a separate `e2e` job to `.github/workflows/ci.yml`.
- Kept the existing `windows` job as the main local-equivalent quality gate.
- Configured the `e2e` job to run after `windows`, bootstrap Python 3.10 and
  Node 22 dependencies, install Playwright Chromium, and run
  `.\scripts\e2e.ps1`.
- Set `PLAYWRIGHT_BROWSERS_PATH` to `${{ runner.temp }}\ms-playwright` and added
  `actions/cache@v4` for that path.
- Kept local `scripts/check.ps1` browser-free.

Validation:

- Workflow syntax was reviewed as a text change. Remote Actions execution
  cannot be observed from this environment until the change is pushed or opened
  as a PR.
- `git diff --check`: passed.
- `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'D:\codex\data'; .\scripts\e2e.ps1"`:
  passed.
- Full Windows `scripts/check.ps1`: passed after GitHub Actions E2E job wiring
  with backend pytest 387 tests, frontend Vitest 58 tests, frontend
  lint/typecheck, and frontend build.

Limitations:

- The new remote `e2e` job still needs to be verified in GitHub Actions after
  push.
- Browser install/cache behavior may need adjustment after the first hosted
  Windows run.

Next:

- Push and verify the new `e2e` job in GitHub Actions, then decide whether it
  should become a required branch-protection check.

## Progress Update 126 - Browser E2E CI Diagnostics

Status: completed in the current working tree with local validation limitations noted.

Completed:

- Added `workflow_dispatch` to the CI workflow.
- Added job timeouts to the `windows` and `e2e` jobs.
- Added `-WorkspaceRoot` support to `scripts/e2e.ps1`.
- Added `--workspace-root` support to `tests/e2e/critical_path.py`; each run
  creates a unique child directory below the supplied parent path.
- Updated the GitHub Actions `e2e` job to keep the E2E workspace under
  `${{ runner.temp }}\datalab-e2e` and upload only `logs\*.log` files as an
  `e2e-logs` artifact.
- Kept temporary data workspaces and raw dataset artifacts out of CI artifacts.

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

Limitations:

- Remote artifact upload behavior still needs verification after push.
- Native Windows local rerun is still needed once the WSL/Windows interop issue
  clears.
- Screenshots and full browser traces are not collected yet.

Next:

- Rerun native Windows `scripts\e2e.ps1` and `scripts\check.ps1`, then verify
  `e2e-logs` on the first remote Actions run and consider adding
  screenshots/traces only if needed.

## Progress Update 127 - Workbench/Service Decomposition And Type Drift Guard

Status: completed in the current working tree.

Completed:

- Confirmed the previous frontend Workbench split remains active:
  - `StatisticalRoleGuide.tsx`
  - `MethodPurposeHelper.tsx`
  - `PreflightExplanationPanel.tsx`
  - `AnalysisHistoryPanel.tsx`
  - `AnalysisComparisonPanel.tsx`
  - `AnalysisResultExportPanel.tsx`
- Split backend analysis-run responsibilities out of
  `backend/app/services/analysis_runs.py`:
  - `analysis_run_results.py` for stored result checksum validation.
  - `analysis_run_history.py` for status/list/cancel.
  - `analysis_run_exports.py` for JSON/CSV/HTML export, list, download, CSV
    formula sanitization, and static HTML report rendering.
  - `analysis_run_comparisons.py` for stored-result comparison.
- Kept `analysis_runs.py` as the create/run dispatcher and compatibility
  facade, including `_METHOD_EXECUTION_HANDLERS` and `_sanitize_csv_cell`
  re-exports for existing tests.
- Updated `backend/app/api/v1/analysis_runs.py` to import split services
  directly for history/result/export/comparison routes.
- Split frontend API types out of `frontend/src/api.ts` into:
  - `frontend/src/api/types/common.ts`
  - `frontend/src/api/types/datasets.ts`
  - `frontend/src/api/types/analyses.ts`
  - `frontend/src/api/types/doe.ts`
  - `frontend/src/api/types/regression.ts`
  - `frontend/src/api/types/index.ts`
- Kept `frontend/src/api.ts` as the public client and type re-export surface so
  existing `./api` imports do not change.
- Added `test_analysis_run_service_boundaries_are_split_without_api_drift`.
- Preserved selected-method beginner guidance and purpose-helper UX; no new
  statistics, fake results, or mock charts were added.

Validation:

- `.venv/Scripts/python.exe -m py_compile backend/app/services/analysis_runs.py backend/app/services/analysis_run_results.py backend/app/services/analysis_run_history.py backend/app/services/analysis_run_exports.py backend/app/services/analysis_run_comparisons.py tests/e2e/critical_path.py`: passed.
- `git diff --check`: passed.
- Targeted backend ruff check for split modules/routes/tests: passed after
  formatting `analysis_run_history.py`.
- Targeted backend pytest:
  `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_api_contracts.py -k "analysis_run_service_boundaries or analysis_execution_handler_registry or analysis_result_csv_export_sanitizes_formula_like_values_explicitly or analysis_run_comparison_api_returns_metadata_only_comparison or analysis_result_export_list_returns_created_exports_without_internal_paths"`:
  5 passed.
- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 58 tests.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  388 tests, frontend lint, frontend typecheck, frontend Vitest with 58 tests,
  and frontend production build.

Remaining limitations:

- Frontend API types are now organized by domain, but still manually mirror
  backend Pydantic schemas.
- OpenAPI generation or schema drift checking remains a next PR task.
- Remote GitHub Actions run/status has not been verified from this environment.
- Vite still reports the existing production chunk-size warning.

Next:

- Add an OpenAPI type-generation or schema-drift spike for
  `frontend/src/api/types/*`.
- Verify remote `windows` and `e2e` GitHub Actions jobs after the next push.

## Progress Update 128 - Frontend API Client Facade Split

Status: completed in the current working tree.

Completed:

- Reduced `frontend/src/api.ts` to a compatibility facade that re-exports API
  client functions and `frontend/src/api/types/*`.
- Split API client implementation into domain files:
  - `frontend/src/api/client.ts`
  - `frontend/src/api/health.ts`
  - `frontend/src/api/datasets.ts`
  - `frontend/src/api/analyses.ts`
  - `frontend/src/api/doe.ts`
  - `frontend/src/api/regression.ts`
  - `frontend/src/api/quality.ts`
- Preserved all existing component imports from `./api`.
- Added no dependency, OpenAPI generator, statistical method, fake result, or
  fake chart.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 58 tests.
- `npm --prefix ./frontend run lint`: passed.
- Backend split regression checks remained green:
  - targeted ruff check: passed.
  - targeted mypy over 6 source files: passed.
  - selected API contract pytest: 5 passed.

Remaining limitations:

- Frontend API types are organized but still manually maintained.
- `frontend/src/api/types/analyses.ts` remains large because it still owns many
  method result interfaces.
- Remote GitHub Actions run/status still needs verification after push.

Next:

- Add a lightweight OpenAPI schema drift check or type-generation spike.
- Split method-specific frontend result types only if manual review becomes a
  bottleneck.

## Progress Update 129 - Frontend API Route Drift Guard

Status: completed in the current working tree.

Completed:

- Added `frontend/src/api/routes.ts` as the single frontend route map for
  `/api/v1` paths.
- Updated the split frontend API clients to use `apiRoutes` for health,
  dataset, analysis, DOE, regression, and quality endpoints.
- Centralized analysis-run create base path, analysis history query ordering,
  and path-ID encoding.
- Removed the accidental runtime `getApiBaseUrl` export from
  `frontend/src/api/types/analyses.ts`.
- Added route-map coverage to `frontend/src/App.test.tsx` while preserving
  existing wrapper URL assertions.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  388 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Keep OpenAPI schema drift/type generation as the next bounded hardening task.

## Progress Update 130 - OpenAPI Frontend Route Contract Guard

Status: completed in the current working tree.

Completed:

- Added `backend/tests/unit/test_openapi_frontend_contract.py`.
- The test checks the backend-generated OpenAPI contract for every route used
  by `frontend/src/api/routes.ts`.
- It verifies path, HTTP method, expected path/query parameters, request media
  type, success status, and response schema component ref.
- It runs as part of backend pytest, so `scripts/check.ps1` automatically
  includes it without a new dependency or standalone generator.

Validation:

- `.venv/Scripts/python.exe -m ruff check backend/tests/unit/test_openapi_frontend_contract.py`:
  passed.
- `.venv/Scripts/python.exe -m pytest backend/tests/unit/test_openapi_frontend_contract.py`:
  24 passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  412 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Full frontend TypeScript/Pydantic field parity still needs a later OpenAPI
  schema diff or type-generation spike.

## Progress Update 131 - OpenAPI Frontend Schema Field Guard

Status: completed in the current working tree.

Completed:

- Extended `backend/tests/unit/test_openapi_frontend_contract.py` beyond route
  checks into curated schema component checks.
- Guarded key frontend-used fields for health, dataset upload/version/preview,
  dataset columns/artifacts, method catalog, analysis history, result envelope,
  provenance, warnings, and export list metadata.
- The guard checks field presence, required field subsets, enum values, const
  values, direct schema refs, and array item refs.
- Added no dependency, generator, API behavior change, UI change, statistical
  method, fake result, or fake chart.

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

Remaining:

- Full generated frontend type parity remains a later bounded task.

## Progress Update 132 - Frontend Analysis API Type Split

Status: completed in the current working tree.

Completed:

- Moved saved analysis history and comparison types to
  `frontend/src/api/types/analysisRuns.ts`.
- Moved analysis export response/list types to
  `frontend/src/api/types/analysisExports.ts`.
- Updated `frontend/src/api/types/index.ts` to keep the existing public `./api`
  import surface stable.
- Kept method-result union types in `analyses.ts`; `AnalysisResultEnvelope`
  remains there because it depends on that union.
- Reduced `analyses.ts` from 2562 lines to 2227 lines with no runtime behavior
  change.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Consider generated frontend types or family-level result type splitting later.

## Progress Update 133 - Frontend Exploration Result Type Split

Status: completed in the current working tree.

Completed:

- Added `frontend/src/api/types/analysisResultsExploration.ts`.
- Moved exploratory analysis result types for descriptive statistics, graphical
  summary, normality, and equal variances out of `analyses.ts`.
- Updated `AnalysisResultEnvelope` to import the exploration result types from
  the new file.
- Updated `frontend/src/api/types/index.ts` so existing component imports from
  `./api` remain stable.
- Reduced `analyses.ts` from 2227 lines to 2005 lines with no runtime behavior
  change.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Consider splitting hypothesis/categorical/regression/quality result types only
  in bounded family-sized slices.

## Progress Update 134 - Frontend Categorical Result Type Split

Status: completed in the current working tree.

Completed:

- Added `frontend/src/api/types/analysisResultsCategorical.ts`.
- Moved one-proportion, two-proportion, and chi-square association result types
  out of `analyses.ts`.
- Updated `AnalysisResultEnvelope` to import categorical result types from the
  new file.
- Updated `frontend/src/api/types/index.ts` so existing component imports from
  `./api` remain stable.
- Reduced `analyses.ts` from 2005 lines to 1738 lines with no runtime behavior
  change.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Consider splitting hypothesis, regression, and quality result types in later
  bounded slices.

## Progress Update 135 - Frontend Regression Result Type Split

Status: completed in the current working tree.

Completed:

- Added `frontend/src/api/types/analysisResultsRegression.ts`.
- Moved Pearson correlation, XY correlation matrix, and linear model result
  types out of `analyses.ts`.
- Updated `AnalysisResultEnvelope` to import regression result types from the
  new file.
- Updated `frontend/src/api/types/index.ts` so existing component imports from
  `./api` remain stable.
- Reduced `analyses.ts` from 1738 lines to 1449 lines with no runtime behavior
  change.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Consider splitting hypothesis and quality result types in later bounded
  slices.

## Progress Update 136 - Frontend Quality Result Type Split

Status: completed in the current working tree.

Completed:

- Added `frontend/src/api/types/analysisResultsQuality.ts`.
- Moved individuals chart, subgroup chart, run chart, capability, Gage R&R,
  Gage run chart, and Gage R&R preflight contract types out of `analyses.ts`.
- Updated `AnalysisResultEnvelope` to import quality result types from the new
  file.
- Updated `frontend/src/api/types/index.ts` so existing component imports from
  `./api` remain stable.
- Reduced `analyses.ts` from 1449 lines to 817 lines with no runtime behavior
  change.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- Consider splitting hypothesis result types in one later bounded slice.

## Progress Update 137 - Frontend Hypothesis Result Type Split

Status: completed in the current working tree.

Completed:

- Added `frontend/src/api/types/analysisResultsHypothesis.ts`.
- Moved one-sample t, paired t, two-sample t, ANOVA, TOST, Wilcoxon,
  Mann-Whitney, and Kruskal-Wallis result types out of `analyses.ts`.
- Updated `AnalysisResultEnvelope` to import hypothesis result types from the
  new file.
- Updated `frontend/src/api/types/index.ts` so existing component imports from
  `./api` remain stable.
- Reduced `analyses.ts` from 817 lines to 160 lines with no runtime behavior
  change.

Validation:

- `npm --prefix ./frontend run typecheck`: passed.
- `npm --prefix ./frontend run test -- --run`: passed with 59 tests.
- `npm --prefix ./frontend run lint`: passed.
- Full Windows `scripts/check.ps1`: passed with backend ruff check, backend
  ruff format check, backend mypy over 79 source files, backend pytest with
  429 tests, frontend lint, frontend typecheck, frontend Vitest with 59 tests,
  and frontend production build.

Remaining:

- API types are still manual; keep OpenAPI type generation or deeper schema
  drift checks as a future task.

## Progress Update 138 - Frontend Result Summary-Type Drift Guard

Status: completed in the current working tree.

Completed:

- Fixed EDA handler summary metadata for `eda.normality` and
  `eda.equal_variances` so handler specs match actual result `summary_type`
  literals.
- Added file-owned frontend result `summary_type` literal checks for
  exploration, hypothesis, categorical, regression, and quality result type
  modules.
- Added a guard comparing frontend result summary literals with backend generic
  analysis-run handler specs, with `gage_rr_preflight` tracked as a quality
  preflight exception.
- Documented the new summary-type drift guard in `docs/method_versioning.md`.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 47 tests.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py::test_analysis_execution_handler_registry_covers_core_methods`:
  passed.
- Full Windows `scripts/check.ps1`: passed on 2026-07-09 with backend ruff
  check, backend ruff format check, backend mypy over 79 source files, backend
  pytest with 435 tests, frontend lint, frontend typecheck, frontend Vitest
  with 59 tests, and frontend production build.

Remaining:

- Full field-level TypeScript/Pydantic parity still needs OpenAPI generation or
  a deeper schema diff.

## Progress Update 139 - OpenAPI TypeScript Generation Review Plan

Status: planning only in the current working tree.

Current guard coverage:

- `backend/tests/unit/test_openapi_frontend_contract.py` instantiates the FastAPI
  app and checks `frontend/src/api/routes.ts` route names against
  `FRONTEND_ROUTE_CONTRACTS`.
- It verifies frontend-used route path, HTTP method, path/query parameters,
  request media type, success response status, and response schema component
  refs.
- It also checks curated high-value schema fields the UI relies on, including
  dataset/version/profile, method catalog, analysis-run history/result/export,
  provenance, warnings, and selected result-shape fields.
- The route-map exact-match guard means a new frontend route should require a
  matching contract entry instead of silently bypassing OpenAPI validation.

Not covered:

- This is not full OpenAPI-to-TypeScript generation.
- It does not prove every nested Pydantic field exactly matches every frontend
  TypeScript type.
- It permits additive backend response fields when they are outside the curated
  high-value guard list.
- It does not generate a typed fetch client, runtime validators, or schema-name
  stability checks.

Candidate tools for a later spike:

- `openapi-typescript` for lightweight TypeScript type generation.
- `openapi-fetch` if a generated typed fetch layer is wanted without a larger
  client framework.
- `orval` if generated request functions and React-query style integration are
  later desired.
- `@openapitools/openapi-generator-cli` only if the team accepts the larger Java
  based toolchain and generated-client footprint.

Review before adoption:

- Windows and current Node LTS compatibility.
- Whether adding the generator changes `package-lock.json` and CI install time.
- Generated file commit policy: checked-in generated types versus generated in
  CI and diff-checked.
- Schema naming stability for Pydantic/FastAPI component names.
- How to handle manually curated domain types during migration.
- Whether generated request types should replace or only cross-check the
  existing `frontend/src/api/*` facade.
- No generator dependency is added in this PR.

## Progress Update 140 - CI/E2E Diagnostics Contract Guard

Status: completed in the current working tree.

Completed:

- Added a CI/E2E wiring regression guard to
  `backend/tests/unit/test_openapi_frontend_contract.py`.
- The guard verifies that `.github/workflows/ci.yml` keeps manual
  `workflow_dispatch`, keeps `e2e` dependent on `windows`, passes separate
  workspace and diagnostics roots to `scripts/e2e.ps1`, and uploads only
  diagnostics-root `logs`, `screenshots`, and `html` paths as `e2e-logs`.
- The guard also checks that `tests/e2e/critical_path.py` retains the
  diagnostics root option, step-slugged failure artifacts, URL/title timeout
  context, and backend/frontend early-exit log-tail support.
- Added a maintenance checklist to `docs/e2e_coverage.md` for future smoke-test
  extensions.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 51 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 439 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 146 - OpenAPI TypeScript Generation Planning Guard

Status: completed in the current working tree.

Completed:

- Added a guard to `backend/tests/unit/test_openapi_frontend_contract.py` for
  the OpenAPI TypeScript generation review plan.
- The guard verifies the review still documents current guard coverage,
  non-coverage, candidate tools, Windows/Node compatibility, package-lock and
  CI install-time impact, generated-file commit policy, schema naming stability,
  curated domain type migration, and the no-generator-dependency PR scope.
- The guard also checks `frontend/package.json` and `frontend/package-lock.json`
  so `openapi-typescript`, `openapi-fetch`, `orval`, and
  `@openapitools/openapi-generator-cli` are not accidentally introduced in this
  stabilization PR.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 56 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 445 tests and frontend Vitest 59 tests.

Remaining:

- OpenAPI TypeScript generation remains a later spike; no dependency,
  generated client, generated type file, or lockfile change was added.
- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 147 - Workbench Hook Ownership Guard Expansion

Status: completed in the current working tree.

Completed:

- Expanded the Workbench saved-result state ownership guard in
  `backend/tests/unit/test_openapi_frontend_contract.py`.
- The guard now asserts that history, export, comparison, and restored-result
  hooks each own only their matching saved-result API calls and do not import
  sibling saved-result API calls.
- The guard also checks hook-level reset/effect markers, refresh handlers,
  comparison validation, export-error clearing, restore-driven method selection,
  and export-list refresh after restore.
- No frontend UI behavior, statistical method, API route, response schema,
  dependency, or method version changed.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 56 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 445 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 145 - CI Status Wording And Datetime-Order Test Stabilization

Status: completed in the current working tree.

Completed:

- Clarified `docs/ci_status.md` so older validation entries no longer call
  themselves "latest" runs.
- Extended the CI status documentation guard in
  `backend/tests/unit/test_openapi_frontend_contract.py` so the Local Validation
  section keeps the current latest 444/59 record and does not regress to stale
  "latest run" wording for older counts.
- Stabilized
  `test_analysis_run_executes_run_chart_with_datetime_order_column` by checking
  for the exact raw datetime input strings instead of rejecting every `2024`
  substring in the full JSON payload, which can be present in a generated UUID.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py::test_analysis_run_executes_run_chart_with_datetime_order_column .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 56 tests.
- First full `scripts/check.ps1` run exposed the UUID-sensitive assertion.
- Second `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1` run
  passed with backend pytest 444 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 144 - Remote CI Verification Checklist Guard

Status: completed in the current working tree.

Completed:

- Expanded `docs/ci_status.md` with authenticated GitHub CLI commands for
  checking remote Actions runs:
  `gh auth status`, `gh run list`, `gh run view`, `gh run download`, and
  optional `gh workflow run`.
- Added a documentation consistency guard to
  `backend/tests/unit/test_openapi_frontend_contract.py` so the CI status
  document keeps workflow triggers, Windows runner, Python/Node versions,
  `scripts/check.ps1`, `scripts/e2e.ps1`, `e2e-logs`, authenticated `gh`
  verification commands, manual dispatch guidance, and repository-settings
  non-change guidance.
- Kept the remote CI state as unverified from this environment.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 55 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 444 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 142 - UX And Reference QA Documentation Guards

Status: completed in the current working tree.

Completed:

- Added a beginner usability walkthrough regression guard to
  `backend/tests/unit/test_openapi_frontend_contract.py`.
- The guard verifies that `docs/beginner_usability_walkthrough.md` keeps the
  five required beginner QA scenarios and their required checklist fields:
  user question, purpose helper card, needed roles, easy wrong roles, preflight
  checks, first result-reading target, non-claims, pass criteria, fail examples,
  visible UX copy, UI element to inspect, and wrong-role recovery.
- Added an independent reference backlog regression guard for
  `quality.capability`, `quality.gage_rr`, `quality.gage_run_chart`,
  `doe.factorial_design`, and `regression.linear_model`.
- The reference backlog guard checks fixture filename, expected output source,
  tolerance, fields to verify, and license/source review content without adding
  fixtures or dependencies.

Validation:

- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 54 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 442 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.
- Independent reference fixtures remain a next PR implementation task.

## Progress Update 143 - Analysis Run Facade Boundary Guard

Status: completed in the current working tree.

Completed:

- Added an AST-based boundary guard to
  `backend/tests/unit/test_api_contracts.py` for
  `backend/app/services/analysis_runs.py`.
- The guard verifies that `analysis_runs.py` keeps only `create_analysis_run`
  as a top-level function, defines no classes, imports the split
  result/history/export/comparison service modules, and does not regain direct
  storage metadata or result-execution persistence imports.
- Updated `docs/storage.md` to document `analysis_runs.py` as the create/run
  dispatcher plus compatibility facade.
- Updated `docs/ci_status.md` and `docs/progress_gate_b.md` with the latest
  validation counts.

Validation:

- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_api_contracts.py -k "analysis_run_service_boundaries or analysis_runs_facade_keeps_create_dispatch_only"`:
  passed with 2 selected tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 443 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 141 - E2E Step Marker Documentation Guard

Status: completed in the current working tree.

Completed:

- Reran the browser E2E smoke with `-DiagnosticsRoot` after the diagnostics
  contract guard changes.
- Added `Current Step Markers` to `docs/e2e_coverage.md` so the documented E2E
  operation sequence is explicit.
- Added a regression guard to
  `backend/tests/unit/test_openapi_frontend_contract.py` that compares
  `diagnostics.step(...)` markers in `tests/e2e/critical_path.py` with the
  documented marker list.
- Updated `docs/ci_status.md` and `docs/progress_gate_b.md` with the latest
  local validation counts.

Validation:

- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 -DiagnosticsRoot .\.tmp\e2e-diagnostics`:
  passed.
- `.\.venv\Scripts\python.exe -m py_compile .\tests\e2e\critical_path.py`:
  passed.
- `.\.venv\Scripts\python.exe -m pytest .\backend\tests\unit\test_openapi_frontend_contract.py`:
  passed with 52 tests.
- `powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1`: passed with
  backend pytest 440 tests and frontend Vitest 59 tests.

Remaining:

- Remote GitHub Actions still needs authenticated confirmation after push for
  the `windows` job, `e2e` job, dependency order, `e2e-logs` artifact, and
  `workflow_dispatch` UI control.

## Progress Update 150 - Post-Reboot Workbench Async Stabilization

Status: completed in the current working tree.

Completed:

- Started from clean main commit
  `02d5d4e4fb2e1d8a0ec802177e2ecdf62116a3fa` and reran bootstrap, the full
  repository check, and browser E2E before editing.
- Added latest-request guards to all four Workbench saved-result hooks so stale
  history/export/comparison/restore responses and stale `finally` blocks cannot
  overwrite newer state or clear newer loading indicators.
- Reset and comparison-selection paths invalidate pending requests and clear
  their loading state immediately; unmount cleanup invalidates requests without
  writing React state.
- Removed duplicate individual saved-result props from `AnalysisShell` and
  `AnalysisWorkbench`; the four grouped state objects are the sole prop
  contract.
- Reconciled documentation with the registry implementation: 29 stable IDs,
  25 available catalog methods, 24 generic handlers, dedicated DOE design
  routes, and dedicated stored-model prediction while generic
  `regression.predict` remains disabled.
- Corrected setup documentation for separate E2E workspace/diagnostics roots
  and the diagnostics-only CI artifact scope.
- Kept statistical methods, formulas, result schemas, method versions,
  dependencies, migrations, and availability unchanged.

Targeted validation:

- Frontend lint and typecheck passed.
- Frontend Vitest passed with 63 tests.
- Frontend/backend contract pytest passed with 57 tests.
- Full `scripts\check.ps1` passed with backend pytest 446 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build.
- Browser E2E passed with
  `-DiagnosticsRoot .\.tmp\e2e-diagnostics` after the implementation changes.

Remaining:

- Remote GitHub Actions verification still requires authenticated access after
  push.
- Deliberately reordered browser HTTP responses are not part of the E2E smoke;
  focused request-token tests and static hook integration guards cover this
  stabilization contract.

## Progress Update 151 - Capability Independent NIST Reference Slice

Status: implemented in the current working tree.

Completed:

- Added an official NIST/SEMATECH summary-reference fixture for
  `quality.capability` with source, access date, convention mapping, tolerances,
  and interpretation limits.
- Used synthetic rows that reproduce the NIST example's mean 16 and sample SD 2
  to verify the published Cp/Cpk/Cpl/Cpu values against the application's
  overall sample-SD fields.
- Kept `MRbar/d2` within-sigma values as an application-specific hand-check and
  did not silently equate them with the NIST estimator.
- Added N/exclusion, warning, source-metadata, and numeric tolerance assertions.
- Updated the capability contract and audit matrix without changing runtime
  calculations, result schemas, method versions, dependencies, or migrations.

Targeted validation:

- Capability unit/reference tests passed with 5 tests.
- Full `scripts\check.ps1` passed with backend pytest 447 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build.
- Browser E2E passed with the separate diagnostics-root option.

Remaining:

- Add a compatible public raw-data industrial-software fixture for
  nonconformance/ppm and within-sigma comparison before changing capability
  formulas or versions.
- The synthetic three-row formula fixture is not an adequate capability-study
  sample and does not establish stability or normality.

## Progress Update 152 - Gage R&R Independent Minitab Summary Slice

Status: implemented in the current working tree.

Completed:

- Added an official Minitab Crossed Gage R&R summary fixture with source URLs,
  access date, design counts, full-model ANOVA values, reduced-model comparison
  values, tolerances, license review, and policy limits.
- Verified the published interaction `F=0.434` / `p=0.974` within its displayed
  precision and derived the application's no-pooling variance components from
  the published rounded mean squares.
- Asserted negative interaction variance preservation, final clamp, contribution,
  study variation, ndc, and persistent warnings.
- Kept Minitab's automatically pooled reduced-model values out of direct parity
  because the current application explicitly preserves the interaction.
- Updated the Gage R&R contract and audit matrix without changing runtime
  calculations, schemas, method versions, dependencies, or migrations.

Targeted validation:

- Gage R&R unit/reference tests passed with 5 tests.
- Full `scripts\check.ps1` passed with backend pytest 448 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build.
- Browser E2E passed with the separate diagnostics-root option.

Remaining:

- Add a redistributable raw-row crossed fixture with a matching no-pooling
  policy for full independent ANOVA parity.

## Progress Update 153 - Gage Run Chart Ordering Reference Slice

Status: implemented in the current working tree.

Completed:

- Added a fully synthetic, internally hand-reviewed ordering fixture for
  `quality.gage_run_chart` with explicit source/license review, conventions,
  tolerances, and diagnostic interpretation limits.
- Verified tied numeric order values use canonical row position as the stable
  tie breaker and asserted all displayed values, canonical positions, and
  redacted part/operator/replicate indexes.
- Verified inline point truncation preserves full valid-observation sample,
  design, and summary metadata.
- Added exact exclusion and warning assertions for missing/nonnumeric
  measurements, missing identifiers, and missing/invalid order values.
- Checked that no synthetic raw identifiers appear anywhere in the serialized
  result and added a duplicate-replicate failure fixture.
- Updated the method contract and audit matrix without changing runtime
  calculations, schemas, method versions, dependencies, or migrations.

Targeted validation:

- Gage Run Chart unit/reference tests passed with 6 tests.
- Full `scripts\check.ps1` passed with backend pytest 450 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build.
- Browser E2E passed with the separate diagnostics-root option.

Remaining:

- Browser chart rendering and exported chart artifacts are outside this
  fixture's deterministic payload scope.
- Gage Run Chart remains diagnostic only and does not replace variance-component
  Gage R&R or establish measurement-system acceptability.

## Progress Update 154 - DOE Factorial NIST Standard-Order Reference Slice

Status: implemented in the current working tree.

Completed:

- Added an official NIST/SEMATECH reference fixture for the three-factor `2^3`
  Yates standard order and the replicated Speed/Feed/Depth factor settings.
- Verified all coded and actual low/high combinations, replicate ordering,
  immutable run metadata, and the application-derived design SHA-256.
- Kept NIST standard-order parity separate from the application's seeded
  shuffle, center-point, round-robin block, and checksum conventions.
- Added a reversed factor-range failure case without a fallback design.
- Reconciled the DOE method contract and statistical audit matrix with existing
  dedicated create/read, response completeness, checksum, report, and generic
  analysis-run rejection tests.
- Kept runtime generation, APIs, schemas, migrations, versions, dependencies,
  and frontend behavior unchanged.

Targeted validation:

- DOE factorial unit/reference tests passed with 6 tests.
- Full `scripts\check.ps1` passed with backend pytest 452 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build.
- Browser E2E passed with the separate diagnostics-root option.

Remaining:

- The current DOE slice remains a design asset with numeric response storage;
  effects, OLS/ANOVA, alias analysis, diagnostics, RSM, and optimization are not
  implemented.

## Progress Update 155 - Linear Model Independent Statsmodels Reference Slice

Status: implemented in the current working tree.

Completed:

- Added a fully synthetic compact regression CSV and a statsmodels 0.14.6
  full-precision OLS reference with CSV SHA-256, package versions, formula,
  covariance/interval options, term mapping, license review, and limitations.
- Generated the independent values in a temporary Python 3.10 environment
  outside the repository without adding statsmodels to product/test dependencies.
- Verified categorical treatment reference `A`, coefficients, SE/t/p/CI, fit
  statistics, VIF/condition number, warnings, and a single-level failure case.
- Verified three mean predictions, mean-response confidence intervals, and
  individual prediction intervals from the stored OLS prediction basis.
- Linked the fixture to existing API coverage for method/version, safe JSON
  manifest checksum equality/tamper recovery, result persistence, and
  row-snapshot provenance rather than pinning generated IDs to a fake checksum.
- Updated the linear model and prediction contracts plus statistical audit
  matrix without changing runtime code, schemas, versions, dependencies, or
  frontend behavior.

Targeted validation:

- Linear model unit/reference tests passed with 8 tests.
- Full `scripts\check.ps1` passed with backend pytest 454 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build after removing the
  temporary statsmodels environment.
- Browser E2E passed with the separate diagnostics-root option.

Remaining:

- Robust covariance, categorical interactions, arbitrary formulas, paged
  prediction retrieval, and interactive upload-fit-predict E2E remain backlog.

## Progress Update 156 - Linear Model Browser Fit And Prediction Slice

Status: implemented in the current working tree.

Completed:

- Extended the Playwright critical path with a fully synthetic 12-row
  `y`/`x`/`group` paste-and-confirm workflow.
- Navigated through the regression module/method grid, explicitly selected
  response `y` and numeric/categorical predictors, and executed a real OLS fit.
- Verified generated Model ID/manifest UI, same-version prediction preflight,
  12/12 usable rows, matching schema, and prediction-ready status.
- Executed real stored-model prediction and verified the 12-row result summary,
  predicted mean/CI/PI table, one reference prediction, and all 12 interval
  lines.
- Added a regression browser-flow contract guard and synchronized
  `docs/e2e_coverage.md`, linear model/prediction contracts, and step markers.
- No mock response/statistic, runtime behavior change, schema/version bump,
  dependency, or migration was introduced.

Targeted validation:

- E2E Python syntax check passed.
- Browser E2E passed with the new regression fit/preflight/predict step.
- Full `scripts\check.ps1` passed with backend pytest 455 tests, frontend
  Vitest 63 tests, lint, typecheck, and production build.
- Browser E2E passed again after the full check and contract documentation
  synchronization.

Remaining:

- A UI for choosing a different target dataset version remains backlog.

## Progress Update 157 - Regression Prediction Paging Stabilization

Status: implemented in the current working tree.

Completed:

- Preserved the existing 1,000-row inline POST response while atomically
  storing every valid prediction row in a raw-predictor-free NDJSON artifact.
- Added checksum/schema/count-validated prediction row retrieval with
  `limit=1..200`, non-negative offsets, and stable pagination metadata.
- Inserted the prediction analysis run and artifact metadata in one SQLite
  transaction and removed both result files when persistence fails.
- Added a typed frontend client and 25-row previous/next controls, passed
  prediction paging as one grouped prop contract, and guarded page requests so
  stale responses cannot replace newer prediction state.
- Updated OpenAPI/frontend route drift coverage and the prediction, setup,
  versioning, E2E, implementation-guide, progress, and CI documents. No new
  dependency, migration, statistical calculation, or method-version bump was
  introduced.

Validation:

- Targeted regression prediction API tests passed with 9 tests.
- OpenAPI/frontend contract tests passed with 59 tests.
- Full `scripts\check.ps1` passed with backend pytest 458 tests, frontend
  Vitest 63 tests, Ruff, format, mypy, lint, typecheck, and production build.
- Browser E2E passed with the separate diagnostics-root option and exercised
  the real fit/preflight/predict plus first-page retrieval flow.

Remaining:

- Selecting a different target dataset version in the prediction UI remains
  backlog.
- The production build retains the existing Vite main-chunk size warning.

## Progress Update 159 - Full Regression Prediction CSV Export

Status: implemented in the current working tree.

Completed:

- Refactored prediction row retrieval around one checksum/schema/count-verified
  iterator shared by paging and export.
- Added a dedicated streaming UTF-8-SIG wide CSV export with prediction/model,
  source-target version, manifest/schema, interval, row-index, and warning
  provenance but no raw predictor columns or target cells.
- Registered `regression_prediction_csv_export` in the existing analysis export
  artifact list/checksum download path without changing generic long-form CSV.
- Added a latest-request-guarded prediction export hook and Linear Model
  generate/download controls that reset on prediction changes.
- Verified all 1,005 stored prediction rows export despite the 1,000-row inline
  limit and blocked export after row artifact tampering.
- Extended browser E2E through real cross-dataset prediction CSV generation and
  `.csv` download. No dependency, migration, calculation, or method-version
  bump was introduced.

Validation:

- Targeted backend/OpenAPI tests passed with 62 tests.
- Full `scripts\check.ps1` passed with backend pytest 461 tests and frontend
  Vitest 63 tests, including Ruff, format, mypy, lint, typecheck, and build.
- Browser E2E passed with prediction CSV generation and download.

Remaining:

- Manual single-row prediction input remains a later contract slice.
- The production build retains the existing Vite main-chunk size warning.

## Progress Update 158 - Cross-Dataset Regression Prediction Target Selection

Status: implemented in the current working tree.

Completed:

- Added paged `GET /api/v1/dataset-versions` discovery for confirmed local
  versions, returning only sanitized display name, IDs, version number,
  row/column counts, and creation time.
- Added a typed client and `useRegressionPredictionTargetState` so target
  catalog loading, paging, selection, and stale-response ownership remain
  outside the main App state surface.
- Defaulted prediction to the active version while allowing explicit selection
  of another confirmed version; target changes cancel and clear older
  preflight, prediction, and prediction-row request state.
- Kept the selector disabled while preflight or prediction is running and
  retained backend schema/range/category validation as the execution gate.
- Extended browser coverage to train on 12 rows, select a separate four-row
  dataset version, pass cross-dataset preflight, and render four real prediction
  intervals.
- Updated OpenAPI route guards and prediction, implementation, setup, E2E,
  progress, and CI documents. No new dependency, migration, calculation, or
  method-version bump was introduced.

Validation:

- Dataset-version catalog privacy/pagination and cross-dataset prediction tests
  passed.
- OpenAPI/frontend contract tests passed with 60 tests.
- Full `scripts\check.ps1` passed with backend pytest 460 tests and frontend
  Vitest 63 tests, including Ruff, format, mypy, lint, typecheck, and build.
- Browser E2E passed with explicit cross-dataset target selection.

Historical remaining at completion of Update 158 (prediction export was later
completed by Update 159):

- Manual single-row prediction input remains a later contract slice.
- The production build retains the existing Vite main-chunk size warning.

## Progress Update 160 - Regression Prediction Dependency Stabilization

Status: implemented in the current working tree.

Completed:

- Block stale, missing, wrong-method, method-version-mismatched, and
  source-schema-drifted source models before target prediction.
- Persist source analysis/source dataset/target dataset/model dependencies and
  shared runtime/build/package provenance without raw paths or values.
- Use registry `METHOD_VERSIONS` as the sole source and bump
  `regression.predict` to `0.2.0`; result/config/rows schemas are `2`/`3`/`2`.
- Validate result/config/rows/model IDs, versions, hashes, target/source links,
  and counts for restore, paging, CSV, list, and download paths.
- Add nine actual hook-level stale-response/reset tests and update registry/UI
  guidance to point to the implemented Linear Model prediction flow.
- Record 1,000/10,000/100,000-row full-verification page and CSV performance;
  keep verified cache/index/hash/session-cache work as a separate safety review.

Validation:

- Backend pytest: 475 passed.
- Frontend Vitest: 72 passed.
- OpenAPI/frontend contract pytest: 62 passed.
- Full `scripts\check.ps1` passed with backend Ruff/format/mypy, backend pytest
  475, frontend lint/typecheck, frontend Vitest 72, and production build. The
  existing Vite main-chunk warning remains at 550.39 kB.
- Browser E2E passed with the cross-dataset prediction page and full CSV flow
  after making the Fit Regression Model locator unambiguous.

Next allowed PR:

- `quality.attribute_control_chart`, starting with the common method contract
  and P/NP/C/U validation/reference/UI/provenance/export slice.

## Progress Update 161 - Attribute Control Chart P/NP/C/U Slice

Status: implemented and locally validated in the current working tree.

Completed:

- Added the available `quality.attribute_control_chart` generic analysis-run
  method at version `0.1.0` with result schema `1`.
- Implemented P/NP/C/U Phase I formulas, natural bounds, one-point 3-sigma
  signals, explicit defective/defect semantics, NP fixed-size and C equal-
  opportunity gates, exclusion accounting, approximation and dispersion
  warnings, and no silent fallback or automatic limit adjustment.
- Reused stored result, row snapshot, provenance, stale handling, and common
  JSON/CSV/HTML exports without adding a dependency or migration.
- Added NIST/formula reference coverage, stable failure/security contracts,
  P/NP/C/U frontend controls, varying-limit SVG and result table, and updated
  method/audit/progress documentation.

Validation:

- Attribute chart unit/reference tests: 17 passed.
- Targeted API/registry/handler tests: 12 passed.
- OpenAPI/frontend contract tests: 62 passed.
- Full `scripts\check.ps1`: passed with Ruff/format/mypy, backend pytest 500,
  frontend lint/typecheck, frontend Vitest 82, and production build. The
  existing Vite chunk warning remains at 563.92 kB.
- Browser E2E: passed with the new P-chart execution, accessible chart, two
  strict 3-sigma signals, and first-25-point table checks while preserving the
  existing regression prediction/export and upload/parser flows.

Next allowed PR:

- DOE factorial analysis: effect estimates, OLS/ANOVA, hierarchy, main and
  interaction effects, residual diagnostics, pure error/lack-of-fit, reference
  fixtures, and report integration.

## Progress Update 162 - DOE Factorial Effects, OLS/ANOVA, And Diagnostics

Status: implemented and locally validated in the current working tree.

Completed:

- Bumped `doe.factorial_design` to `0.2.0` from the shared registry source
  because a persisted analysis contract was added; analysis config/result
  schemas are `1` and SQLite metadata schema is `9`.
- Added -1/+1 coded main/interaction effects through order 3 with enforced
  hierarchy, center curvature, block fixed effects, OLS inference, partial
  drop-one ANOVA, pure error/lack-of-fit, residual/influence diagnostics, and
  capped main/interaction plot payloads without automatic term selection or
  fallback.
- Added a NIST saturated 2^3 coefficient reference and hand/failure tests for
  effect scaling, hierarchy, reduced-model lack of fit, point limits, constant
  response, and invalid center coding.
- Added dedicated create/restore APIs and schema-v9 checksum/dependency storage,
  response SHA verification, relationship-tamper rejection, runtime/build/
  NumPy/SciPy provenance, and internal-path-free errors.
- Extended the verified DOE HTML report with stored fit/effect/ANOVA/diagnostic
  sections and added typed frontend API routes/types plus Workbench analysis
  controls, effect/main-effect SVGs, term/ANOVA tables, diagnostics, and warnings.
- Added OpenAPI/frontend route/schema/summary-type guards and API, migration,
  report, tamper, and frontend SSR coverage.

Targeted validation completed:

- Factorial statistics plus metadata tests: 22 passed.
- Dedicated DOE API tests: 9 passed.
- OpenAPI/frontend contract suite: 68 passed.
- Frontend lint and strict typecheck passed; targeted Vitest: 63 passed.

Full validation:

- Full `scripts/check.ps1` passed with Ruff/format, mypy over 83 source files,
  backend pytest 517, frontend lint/typecheck, frontend Vitest 84, and build.
- Browser E2E passed through DOE design, nine response values, analysis v0.2.0,
  effect/main-effect SVGs, ANOVA, and diagnostics after adding the required
  local-origin CORS `PUT` allowance and its startup contract test.
- Fractional factorial alias analysis, RSM, optimization, and chart image export
  remain out of scope.

Next allowed PR after this slice:

- DOE/RSM: Central Composite Design, axial/center points, quadratic model,
  contour/surface plot payloads, residual diagnostics, and design-region
  validation.

## Progress Update 163 - DOE/RSM CCD And Full Quadratic Model

Status: implemented in the current working tree; final full validation recorded
in `docs/ci_status.md`.

Completed:

- Made `doe.response_surface` available at `0.1.0` through dedicated DOE APIs.
- Added bounded rotatable central composite inscribed and face-centered CCD
  generation for two to five factors with deterministic standard order,
  optional seeded randomization, factorial/axial/center labels, and design SHA.
- Added complete response storage and hierarchy-fixed full quadratic OLS with
  coefficient inference, partial drop-one ANOVA, pure error/lack-of-fit,
  residual/influence diagnostics, stationary-point/Hessian classification,
  design-region checks, and a 21x21 contour payload.
- Reused schema-v9 DOE storage plus common runtime/build provenance and added
  design/result/response/config relationship validation on restore.
- Added the NIST/SEMATECH 11-run CCI Uniformity reference, known quadratic
  stationary-point hand test, rank/constant/invalid-grid failures, API tamper
  coverage, typed OpenAPI/frontend contracts, and Workbench CCD/RSM controls.
- Added browser coverage for CCD creation, thirteen response values, response
  persistence, quadratic fit, contour rendering, term table, and diagnostics.
- Allowed only the two local Vite loopback origins, `127.0.0.1:5173` and
  `localhost:5173`, so either address reaches the loopback backend without a
  wildcard or LAN exposure.

Intentionally deferred:

- Response optimizer/desirability, objective constraints, Box-Behnken,
  orthogonal blocking, ridge analysis, surface perspective plot, report/image
  export, and recommended operating settings.

Next allowed PR:

- Response Optimizer: maximize/minimize/target/range objectives, bounded design
  region and constraints, individual/composite desirability, deterministic
  CPU/time budget, stored manifests, and auditable recommendation provenance.

## Progress Update 164 - Bounded Response Optimizer

Status: implemented and locally validated in the current working tree; the
exact full-check record is in `docs/ci_status.md`.

Completed:

- Added `regression.response_optimizer` v0.1.0 through dedicated response-
  surface optimization create/restore APIs. The generic catalog method remains
  disabled and points users to the fitted RSM screen.
- Added config/result schema 1 with checksum-validated source RSM analyses,
  source bundle SHA, design/response/config/result relationships, common
  runtime/build/package provenance, and schema-v9 DOE metadata reuse.
- Implemented maximize/minimize/target/range Derringer-Suich objectives,
  importance-weighted geometric composite desirability, narrower actual factor
  bounds, actual-unit linear `<=`/`>=` constraints, deterministic seeded
  candidates, bounded SLSQP multi-start search, and explicit CPU/time/
  iteration/evaluation budgets.
- Added a one-current-response `ResponseOptimizerPanel` under the verified RSM
  result. It renders recommendation coordinates, point prediction,
  individual/composite desirability, constraint slack/status, diagnostics, and
  persistent confirmation/global-optimum/uncertainty warnings.
- Added NIST/SEMATECH multiresponse reference coverage, hand-checkable known-
  optimum and constraint cases, source/config/result tamper coverage, stable
  public errors without internal paths, typed OpenAPI/frontend contracts, and
  browser critical-path coverage.
- Full local validation passed with backend pytest 558, frontend Vitest 86,
  OpenAPI/frontend contracts 85, mypy over 88 source files, lint/typecheck/
  production build, and the complete browser E2E optimizer flow.

Intentionally deferred:

- Multiresponse objective construction in the UI, prediction intervals and
  uncertainty-aware desirability, nonlinear/equality/integer/categorical
  constraints, global-optimum claims, confirmation experiments, ridge analysis,
  and an independent Response Optimizer page.

Next allowed PR:

- Plan and specify `doe.bayesian_optimization`: bounded factor space,
  objective/constraints, surrogate/acquisition policies, sequential experiment
  history, deterministic seed and CPU/time/trial budgets, recommendation
  provenance, audit trail, and no guaranteed-global-optimum claim. Keep it
  non-executable until its contract and independent reference policy exist.

## Progress Update 165 - Bayesian Optimization Planning Contract

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md` after the full pass.

Completed:

- Added stable method ID `doe.bayesian_optimization` at planning version
  `0.1.0`; it is catalog `planned`, requires no dataset, has no execution
  handler, and returns no result or recommendation.
- Defined a one-to-six continuous-factor, single deterministic objective,
  sequential completed-trial contract with Matérn-5/2 GP, Expected Improvement,
  actual-unit linear constraints, one pending recommendation, explicit seeds,
  and CPU/time/trial/candidate/local-search budgets.
- Prohibited arbitrary objective/Python/shell/equipment execution, fabricated
  observations, silent model/acquisition fallback, recommendation-to-observation
  promotion, path/raw-value logging, and global-optimum guarantees.
- Added `doe_bayesian_optimization_reference_policy.json` with hand EI cases,
  a hand quadratic, documented Branin minima, method sources, and explicit
  `planning_only`/`runtime_result_expected=false` metadata.
- Added registry/API no-fake tests and frontend catalog/guidance/role tests.
  No dependency, migration, persisted schema, executable API, or calculation
  was introduced.
- Full local validation passed with backend pytest 564, frontend Vitest 86,
  OpenAPI/frontend contracts 85, mypy over 88 source files, lint/typecheck/
  production build, and the existing browser critical path.

Next allowed PR:

- Build only the immutable Bayesian Optimization study/history foundation:
  study version, bounded factor/objective definition, initial design policy,
  trial state transitions, observation history SHA, storage/API relationship
  validation, and typed tests. Keep surrogate fitting and recommendation out
  until this foundation passes its own gate.

## Progress Update 166 - Post-Expansion DOE/RSM Lifecycle Stabilization

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md`.

Completed:

- Kept `doe.response_surface` at v0.1.0 and moved new design payloads to schema
  2 with family `central_composite`; `alpha_mode` distinguishes rotatable and
  face-centered geometry. Legacy schema-1
  `central_composite_inscribed` designs retain their original family, mode, and
  SHA on restore.
- Made Factorial and RSM response name/unit/value/save controls read-only after
  analysis and added the persistent pre-analysis lock warning. Backend direct
  response writes still reject analyzed designs with 409.
- Bumped `regression.response_optimizer` to v0.2.0 with config/result schema 2.
  Source RSM eligibility is classified as blocking, acknowledgment-required,
  or informational; blockers produce no recommendation and accepted advisory
  codes are stored in config/result/envelope provenance.
- Added saturated, unusable residual variance, significant lack-of-fit,
  checksum-dependency, acknowledgment, restore, and browser lock coverage.
- Added `docs/doe_response_revision_contract.md` as the immutable correction,
  history, migration, restore, and multi-response acceptance contract.
- Corrected the Bayesian dependency plan: study/history uses stdlib/Pydantic/
  SQLite and adds no scikit-learn. GP work requires a separate Windows/Python
  3.10/CPU/offline/license/size/determinism dependency spike and exact pin
  approval.
- Recorded the pre-slice approximately 608 kB and latest 612.20 kB bundle
  warning as a separate dynamic-import backlog rather than mixing a large
  frontend refactor into lifecycle work.

Next allowed PR:

- Frontend module lazy loading for DOE/Quality/Regression panels, with explicit
  loading/error boundaries, route-level E2E coverage, and before/after bundle
  measurement. Do not mix it with DOE storage, Bayesian execution, GP/EI, or
  scikit-learn.

## Progress Update 167 - DOE Immutable Response Revision/History Foundation

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md` after the full pass.

Completed:

- Added SQLite schema 10 immutable response revision, ordered-value, current-
  head, and analysis-revision relationship tables. Consistent legacy current
  responses receive deterministic revision 1 records without rewriting result
  artifacts or inventing missing historical versions.
- Added response revision schema 1 create/current/paged-history/get/abandon
  APIs and an explicit compare-and-supersede correction contract. In-place
  response overwrite remains prohibited.
- Bumped Factorial to v0.3.0 and RSM to v0.2.0 with analysis envelope/config
  schema 2. Each analysis pins revision ID/number/SHA while its statistical
  calculation result schema remains 1.
- Bumped Response Optimizer to v0.3.0 with source-bundle schema 2 while keeping
  config/result schema 2. Old analysis and optimizer restores remain fixed to
  the response revision they consumed after newer corrections are created.
- Added Factorial/RSM current/history UI, analyzed read-only state, explicit
  correction mode, multi-response separation, request-race guards, and browser
  coverage for correction/history.
- Added migration, pagination, abandon, checksum/relation tamper, redaction,
  old-analysis restore, optimizer dependency, OpenAPI/frontend contract, and
  component tests. Bayesian remains planning-only and no dependency was added.
- Full local validation passed with backend pytest 582, frontend Vitest 90,
  OpenAPI/frontend contracts 91, mypy over 89 source files, Ruff/format,
  frontend lint/typecheck/build, and browser E2E. The final main bundle is
  618.10 kB and remains the baseline for the next code-splitting slice.

Next allowed PR:

- Split DOE, Quality, and Regression panels into dynamic-imported chunks with
  loading/error boundaries and route E2E. Record before/after bundle sizes and
  keep DOE storage and statistical behavior unchanged.

## Progress Update 168 - Frontend Module Lazy Loading

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md` after the full pass.

Completed:

- Split Regression, Quality, and DOE execution panels into three on-demand
  module chunks with no new dependency and no API/statistical/storage change.
- Added transition-safe module/method selection, accessible stable-height
  loading UI, sanitized method-resettable error UI, and a local reload command.
- Kept existing detailed panel tests through a test-only direct loader and
  added focused loader/boundary tests.
- Added real resource timing, direct route, and isolated chunk-failure browser
  assertions while retaining the full analysis critical path.
- Reduced main JS from 618.10 kB to 463.89 kB. The three chunks are Regression
  41.53 kB, Quality 58.83 kB, and DOE 57.26 kB; total JS is 621.51 kB.
- Full local validation passed with backend pytest 582, frontend Vitest 93,
  OpenAPI/frontend contracts 91, mypy over 89 source files, Ruff/format,
  frontend lint/typecheck/build, and browser E2E with direct route and isolated
  import-failure coverage.

Next allowed PR:

- Implement only the Bayesian study/history foundation defined in
  `docs/bayesian_optimization_contract.md`: immutable study metadata, trial
  states, history SHA, relationship validation, and typed storage/API tests.
  Keep GP/EI, recommendations, objective execution, and scikit-learn out.

## Progress Update 169 - Bayesian Study/History Foundation

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md` after the full pass.

Completed:

- Added SQLite schema 11 study, immutable version, initial-design trial,
  immutable observation-history revision, and current-head tables. Schema-10
  DOE data is not rewritten and migration creates an empty Bayesian namespace.
- Added study schema 1 with one to six bounded continuous factors, one manual
  maximize/minimize objective, actual-unit linear inequalities, canonical
  definition SHA, and no definition mutation endpoint.
- Added reproducible `sha256_counter_uniform_feasible_v1` seeded initial points
  with an explicit attempt budget. Points are bounded and constraint-checked;
  infeasible generation fails without dropping constraints or shrinking size.
- Added pending to completed/abandoned terminal trial transitions. Completion
  requires the expected history revision, never updates an existing objective,
  and appends history schema 1 with ordered trial IDs and chained SHA-256.
- Added paged study/trial/history restore routes, typed frontend API client
  contracts, catalog/guidance copy, relationship/checksum validation, and
  stable redacted error codes. Generic Bayesian analysis execution remains
  unavailable and both surrogate/recommendation availability are false.
- Added deterministic seed, bounds, normalization, constraint, migration,
  terminal-state, stale-head, immutable history, hand SHA, paging, missing
  relation, metadata/trial/history tamper, redaction, and OpenAPI/frontend
  contract tests. No dependency was added.
- Full local validation passed with backend pytest 603, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E regression path.

Next allowed PR:

- Run the separate scikit-learn dependency spike only. Record Windows 11,
  Python 3.10, CPU wheel, NumPy/SciPy compatibility, license, offline behavior,
  startup/memory cost, and deterministic GP smoke results before deciding an
  exact production pin. Do not add GP/EI/recommendation APIs in that spike.

## Progress Update 170 - Conditional Scikit-learn Dependency Spike

Status: implemented in the current working tree; full local validation is
recorded in `docs/ci_status.md` after the final pass.

Completed:

- Selected scikit-learn 1.7.2 as the newest stable version exposed to CPython
  3.10; the overall current 1.9.0 release requires Python 3.11 and was rejected.
- Added a TEMP-only PowerShell runner, synthetic fixed-kernel GP probe, strict
  JSON result validator, and six contract tests. The runner rejects repository
  output, uses exact wheel-only downloads, performs an offline `--no-index`
  install, and never modifies the product `.venv` or dependencies.
- Validated NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2, joblib 1.5.2, and
  threadpoolctl 3.6.0 with `pip check`, invalid runtime proxies, single-threaded
  BLAS/OpenMP settings, and two matching isolated GP fingerprints.
- Recorded a 60.442 MiB wheelhouse, 217.908 MiB installed distribution total,
  five-run import/GP elapsed and process-tree peak-memory measurements, package
  licenses, wheel SHA-256, and the deterministic synthetic predictions in
  `docs/scikit_learn_dependency_spike.md`.
- Measured host detection returned Windows 10 Home build 19045. The runner and
  validator therefore set `candidate_approved_for_future_pin=false`; the
  required Windows 11 gate is not claimed or inferred.
- Kept `backend/pyproject.toml` and lockfiles unchanged. Bayesian remains
  planning-only at method version 0.1.0 with study/history schemas 1 and no
  config/result schema, surrogate, EI, recommendation, objective execution, or
  fake result.
- Full local validation passed with backend pytest 609, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E. The main bundle
  remains 464.68 kB.

Next allowed PR:

- Re-run the evidence-schema-2 spike on Windows 11/CPython 3.10/CPU-only and require an
  approved validator result before any product pin or executable GP/EI work.

## Progress Update 171 - Windows 11 Approval Gate Hardening

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md`.

Completed:

- Rechecked the host through registry, `Win32_OperatingSystem`,
  `Environment.OSVersion`, and `ver`; all independently identify Windows 10
  Home build 19045, so a real Windows 11 run cannot be claimed on this PC.
- Corrected the spike approval gate so build number alone is insufficient.
  Evidence schema 2 stores OS caption, build, and ProductType and approves only
  workstation ProductType 1 with build 22000 or newer.
- Added explicit Windows Server 2025 coverage. A build-26100 server remains
  unapproved, preventing GitHub-hosted `windows-latest` from being presented as
  Windows 11 client evidence.
- Pinned evidence schema 2 to the reviewed five-package candidate set and bound
  the scikit-learn PyPI candidate wheel name, size, and SHA-256 to the actual
  downloaded wheel manifest. Duplicate, missing, source-archive, version, and
  relationship mismatches fail validation.
- Added Windows 10, Windows 11 workstation, Windows Server 2025, approval-flag,
  wheel-SHA, nondeterminism, source archive, TEMP isolation, and no-product-pin
  tests; the focused suite now contains nine tests.
- Re-ran the full wheel/offline/GP spike. Evidence schema 2 passed while
  correctly returning `candidate_approved_for_future_pin=false` for caption
  `Microsoft Windows 10 Home`, build 19045, ProductType 1. The deterministic
  fingerprint remained unchanged.
- Kept production dependencies, method/study/history/config/result versions,
  Bayesian execution behavior, and frontend behavior unchanged.
- Full local validation passed with backend pytest 612, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, Ruff/format,
  frontend lint/typecheck/build, and the complete browser E2E. The main bundle
  remains 464.68 kB.

Next allowed PR:

- Run the evidence-schema-2 spike on an actual Windows 11 x64 workstation with
  CPython 3.10 and CPU-only. GP/EI and the production pin remain gated.

## Progress Update 172 - Scikit-learn Production Pin And Reproducible Lock

Status: implemented in the current working tree; local validation is recorded
in `docs/ci_status.md`.

Completed:

- Accepted actual Windows 11 client validation as a release gate by explicit
  product-owner direction. The measured Windows 10 Home build 19045 result
  remains labeled accurately and cannot approve a release.
- Added the exact `scikit-learn==1.7.2` production pin without adding GP, EI,
  recommendation, objective execution, or a fake Bayesian result.
- Added a 45-wheel CPython 3.10 Windows AMD64 SHA-256 lock, deterministic
  wheel-metadata generator, strict validator, and external-TEMP PowerShell
  generation entry point. joblib 1.5.2 and threadpoolctl 3.6.0 remain reviewed
  resolver constraints rather than direct project dependencies.
- Updated bootstrap to consume only hashed wheels before a no-dependency,
  no-build-isolation editable backend install and `pip check`. A clean offline
  TEMP venv proved the lock and API startup does not import scikit-learn.
- Added six dependency-lock tests and updated the nine spike-policy tests.
  Full checks passed with backend pytest 618, frontend Vitest 93,
  OpenAPI/frontend contracts 104, mypy over 93 source files, frontend build,
  and complete browser E2E. The main bundle remains 464.68 kB.
- Kept `doe.bayesian_optimization` planning-only at 0.1.0 with study/history
  schemas 1. No method/config/result version changed in this dependency-only
  slice. Remote Actions remain unverified because `gh` is unavailable.

Next allowed PR:

- Implement the first bounded Bayesian GP/EI executable vertical slice. It
  must define method/config/result versions, independent GP-posterior and EI
  references, deterministic candidate/time/trial budgets, typed numerical
  errors, immutable recommendation provenance/storage, relationship tamper
  rejection, and E2E coverage. It must not execute arbitrary objectives,
  silently change algorithms, or claim a guaranteed global optimum.
- Run the unchanged spike on an actual Windows 11 x64 workstation before any
  release containing this dependency or future GP/EI behavior.

## Progress Update 173 - Bounded Bayesian GP/EI Executable Slice

Status: implemented in the current working tree; local validation is recorded
in `docs/ci_status.md`.

Completed:

- Promoted `doe.bayesian_optimization` to dedicated API/UI method `0.2.0`
  while preserving study/history schema 1 and legacy `0.1.0` restore.
- Added SQLite schema 12 recommendation records, recommendation-origin pending
  trials, config/result/model schema 1, and checksum-validated immutable
  source-history/config/result/model/provenance relationships.
- Added a spawn-worker, single-numerical-thread Matérn-5/2 ARD Gaussian Process
  with analytic Expected Improvement, deterministic bounded search, actual-unit
  linear constraints, explicit budgets, and typed no-fallback failures.
- Added direct posterior/EI reference tests, migration/legacy/tamper/API tests,
  a dedicated frontend panel, controlled OpenAPI/frontend contracts, and a
  complete browser flow. The application still never executes the objective,
  accepts arbitrary code, or claims a guaranteed global optimum.
- Full checks passed with backend pytest 633, frontend Vitest 94,
  OpenAPI/frontend contracts 110, and mypy over 96 source files. The complete
  browser E2E passed with diagnostics root
  `.tmp\e2e-diagnostics-bayesian-gp-ei-final`.
- Actual Windows 11 x64/CPython 3.10/CPU-only validation remains a mandatory
  release gate, not a development blocker. The local host is Windows 10 Home
  build 19045, and remote Actions remain unverified because `gh` is unavailable.

Next allowed PR:

- Stabilize the sequential Bayesian lifecycle: broaden relationship-tamper
  coverage, characterize multi-seed Branin regret under declared budgets,
  expose linear constraints in the UI, and measure worker startup/fit/search
  cost. Do not add another acquisition function or objective execution.

## Progress Update 174 - Bayesian Sequential Lifecycle Stabilization

Status: implemented in the current working tree; final validation is recorded
in `docs/ci_status.md`.

Completed:

- Extended recommendation consistency checks from checksum integrity to
  result/trial coordinates, factor scaling, source-history observation count and
  incumbent, request/result budgets, model counts, constraint evaluations,
  required warnings, package provenance, and finite numerical relationships.
- Added checksum-recomputed tamper cases for coordinates, request/result budget,
  model observation count, incumbent, constraint evaluation, required warning,
  source history, and package provenance across study/list/single restore paths.
- Added a five-seed Branin reference with six initial points, 14 sequential
  recommendations, a 20-trial total budget, maximum simple regret `0.20`, and
  median simple regret `0.15` acceptance thresholds.
- Added the typed actual-unit linear-constraint editor and stored/recommendation
  feasibility tables to `BayesianOptimizationPanel`; zero-only, nonnumeric,
  duplicate-ID, and over-limit drafts are rejected before API submission.
- Added `scripts/benchmark-bayesian.ps1` and its static Python runner. The local
  three-repeat Windows 10/Python 3.10 measurement records empty spawn, worker
  round trip, child calculation, GP fit, non-fit calculation, and IPC/bootstrap
  overhead without changing persisted result schemas.
- Retained method `0.2.0`, study/history schemas 1, recommendation
  config/result/model schemas 1, SQLite schema 12, Matern-5/2 GP, analytic EI,
  and all safety/no-objective-execution policies.
- Full `scripts/check.ps1` passed with backend pytest 635, frontend Vitest 95,
  OpenAPI/frontend contracts 110, mypy over 96 source files, and production
  build. Browser E2E passed with diagnostics root
  `.tmp\e2e-diagnostics-bayesian-lifecycle-stabilization`.

## Progress Update 175 - Phase II Attribute Chart Contract Foundation

Completed:

- Kept executable `quality.attribute_control_chart` at method `0.1.0`, result
  schema `1`, and Phase I-only calculation. Current typed options continue to
  reject unimplemented `phase` and `limit_set_id` fields.
- Added an immutable app-created limit-set contract reserving asset schema `1`,
  future method `0.2.0`, and result schema `2` without reinterpreting existing
  Phase I artifacts or adding a migration/API/calculation placeholder.
- Added a policy-adjusted independent P/NP/C/U frozen-limit fixture and tests
  for formula, natural-bound, strict-signal, current-version, and closed-option
  behavior. This fixture is not presented as direct published-output parity.
- Added persistent Phase I-only/Phase-II-not-applied UI wording, result phase
  and limit-source labels, frontend assertions, and critical-path coverage.
- Full `scripts/check.ps1` passed with backend pytest 640, frontend Vitest 95,
  OpenAPI/frontend contracts 110, mypy over 96 source files, and production
  build. Browser E2E passed with diagnostics root
  `.tmp\e2e-diagnostics-attribute-phase2-contract`.
- The local host is Windows 10 Home build 19045; Windows 11 validation remains
  a mandatory release gate. Remote Actions are unverified because `gh` is
  unavailable.

Next allowed PR:

- Implement the Phase II frozen-limit monitoring vertical slice defined in
  `docs/attribute_control_chart_phase_2_contract.md`. Use only verified
  app-created limit sets and keep all non-Phase-II chart expansions out of
  scope. Actual Windows 11 validation remains a mandatory release gate rather
  than a development blocker.

## Progress Update 176 - Immutable Attribute Limit-Set Storage/API

Completed:

- Added SQLite schema 13 and immutable `attribute_control_limit_sets` metadata
  with source analysis/dataset/config/result/schema/canonical/row-snapshot
  hashes, P/NP/C/U semantics, eligibility, internal asset path/SHA, and close
  time. Schema-12 upgrade preserves prior data and creates an empty table.
- Added idempotent create, checksum/relation-validated get, and filtered paged
  list routes under `/api/v1/quality/attribute-control-limit-sets`. No update,
  delete, monitoring, or fallback route exists.
- Added conservative baseline eligibility: at least 20 complete points, no
  Phase I signals, usable expected counts, Pearson dispersion <= 2, and full
  untruncated points. Center, limits, dispersion, signals, totals, and NP fixed
  sample size are independently recomputed before promotion.
- Added controlled frontend route/client/types and OpenAPI field-level guards
  without exposing a Phase II execution control.
- Added P/NP/C/U promotion, idempotence, migration, file checksum, DB relation,
  rehashed asset/source result, row snapshot/canonical/schema tamper, path
  redaction, stale/small source, and no-overwrite/delete tests.

Validation:

- Full `scripts/check.ps1` passed with backend pytest 663, frontend Vitest 95,
  OpenAPI/frontend contracts 116, mypy over 98 source files, Ruff/format over
  150 Python files, frontend lint/typecheck, and production build. The final
  run used a D-drive pytest basetemp because the host C drive lacked temp space.
- Browser E2E passed on ports `8025`/`5225` with diagnostics root
  `.tmp\e2e-diagnostics-attribute-limit-set-storage` and retained every prior
  critical flow. It does not claim an unimplemented Phase II UI.
- Windows 11 remains a mandatory release gate. Remote Actions are unverified
  because `gh` is unavailable.

Next allowed PR:

- Implement the first Phase II frozen-limit monitoring vertical slice defined
  in `docs/attribute_control_chart_phase_2_contract.md`: method `0.2.0`, result
  schema `2`, verified app-created limit-set selection, target compatibility
  preflight, P/NP/C/U frozen-limit calculation, dependency provenance,
  restore/export consistency, typed UI, and browser E2E.
- Keep WECO/Nelson rules, Laney correction, exact probability limits,
  user-entered naked limits, automatic baseline refit, and new chart families
  out of that slice.

## Progress Update 177 - Bayesian Lifecycle Correctness Stabilization

Completed:

- Bumped `doe.bayesian_optimization` to patch `0.2.1`; study/history and
  recommendation config/result/model schemas remain 1, SQLite remains schema
  13, and valid stored `0.2.0` recommendations restore without relabeling.
- Enforced the shared `max(2, factor_count + 1)` initial-design rule in the
  backend and frontend. Shared limits now distinguish 200 total trials, 200
  completed observations, and 201 history revisions including the empty first
  revision.
- Prevented initial-trial abandonment that would strand the minimum observation
  requirement. Surplus initial trials and recommendation trials remain
  abandonable, and abandonment does not create a history revision.
- Excluded completed, pending, and abandoned coordinates from every later
  candidate within the existing duplicate tolerance. No random or duplicate
  fallback was added.
- Added a latest-recommendation API, current-trial reconciliation, pending/
  completed/abandoned/historical labels, and separation of stored predicted
  values from an actual completed observation.
- Displayed and enforced the effective request-level total-trial budget,
  retained the hard 200 limit, and unified fit/acquisition/worker time
  exhaustion under `bayesian_optimization_budget_exhausted`.
- Added accessible inline confirmations for immutable observation completion
  and abandonment, transition action locking, retained input after errors, and
  study/latest refresh after success.
- Added `docs/bayesian_study_lifecycle_contract.md`. Study-level completion and
  abandonment remain unimplemented until a later migration/API PR.

Validation:

- Initial targeted Bayesian/OpenAPI backend pytest: 155 passed; follow-up
  recommendation-version compatibility suite: 36 passed.
- Frontend lint/typecheck passed and Vitest: 98 passed.
- Browser E2E passed on ports `8027`/`5227` with diagnostics root
  `.tmp\e2e-diagnostics-bayesian-lifecycle-correctness`; the final full rerun
  also passed in 57.9 seconds on ports `8028`/`5228` with diagnostics root
  `.tmp\e2e-diagnostics-bayesian-lifecycle-correctness-final`. After the final
  restore-boundary review it passed again in 56.8 seconds on ports `8029`/
  `5229` with diagnostics root `.tmp\e2e-diagnostics-bayesian-lifecycle-final`.
- Full `scripts/check.ps1` passed with Ruff/format over 150 Python files, mypy
  over 98 source files, backend pytest 687, frontend lint/typecheck, frontend
  Vitest 98, and production build. The direct OpenAPI/frontend contract suite
  passed 117 tests. Main JavaScript is 467.18 kB and the DOE chunk is 79.80 kB;
  both remain below the 500 kB warning threshold.
- Final environment evidence is recorded in `docs/ci_status.md`; Windows 11/
  Node 22 remains a release gate.

Next development order:

1. Phase II frozen-limit monitoring.
2. Windows 11/Python 3.10/Node 22 clean release validation.
3. Bayesian study close/abandon and retention implementation.
4. Advanced quality/statistics backlog.

## Progress Update 178 - Phase II Frozen-Limit Monitoring

Completed:

- Promoted `quality.attribute_control_chart` to method `0.2.0` and result
  schema 2 for explicit Phase I/Phase II meaning while preserving verbatim
  restore and limit-set promotion of stored `0.1.0`/schema-1 Phase I results.
- Added verified app-created limit-set selection, target compatibility
  preflight, P/NP/C/U frozen-limit execution, NP fixed-sample-size and C current
  opportunity gates, and stable redacted errors. No target refit, naked limit,
  chart switch, or silent fallback exists.
- Added source-limit and target dependency provenance plus checksum/relation
  validation across result, config, asset, dataset schema/canonical artifact,
  filter, row snapshot, columns, and counts for restore and common exports.
- Added explicit Phase I/II UI, latest-request-guarded asset/preflight state,
  disabled run reasons, immutable source labels, cross-dataset API tests, legacy
  compatibility, tamper coverage, and a full browser path.
- Full `scripts/check.ps1` passed with backend pytest 702, frontend Vitest 100,
  OpenAPI/frontend contracts 120, Ruff/format over 152 Python files, mypy over
  99 source files, frontend lint/typecheck, and production build. Chromium E2E
  passed in 58.1 seconds on ports `8030`/`5230`.
- Validation ran on Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0 from an uncommitted working tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Windows 11/Python 3.10/Node 22
  remains a release gate. Remote Actions were not verified because `gh` is not
  installed.

Next development order:

1. Windows 11/Python 3.10/Node 22 clean release validation.
2. Bayesian study close/abandon and retention implementation.
3. Advanced quality/statistics backlog through separately approved contracts.

## Progress Update 179 - Bayesian Study Close And Read-Only Lifecycle

Completed:

- Bumped `doe.bayesian_optimization` to patch `0.2.2`; existing study/history
  and recommendation config/result/model schemas remain 1 and legacy executable
  recommendations are not relabeled.
- Added SQLite schema 14 immutable lifecycle-event schema 1, optimistic close,
  canonical event SHA, final trial/history/recommendation relationships, stable
  reason codes, exact idempotency, and successor `predecessor_study_id`.
- Added explicit close-intent trial abandonment, pending and completion gates,
  storage-level post-close mutation blocking, schema-13 upgrade coverage, and
  tamper/redaction tests. Close does not delete any artifact.
- Added typed API/OpenAPI/frontend lifecycle contracts, accessible inline
  confirmation, active/completed/abandoned labels, closed read-only restore,
  and successor definition preparation without copying observations or results.
- Full `scripts/check.ps1` passed with backend pytest 712, frontend Vitest 101,
  OpenAPI/frontend contracts 120, Ruff/format over 153 Python files, mypy over
  99 source files, lint/typecheck, and production build. Targeted lifecycle/
  Bayesian/OpenAPI tests passed 189.
- Chromium E2E passed in 58.6 seconds on ports `8031`/`5231`. Validation used
  Windows 10 Home build 19045, Python 3.10.11, and Node 24.17.0 from main base
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`; it is not Windows 11/Node 22
  release evidence. `gh` is not installed, so remote Actions remain unverified.

Next development order:

1. Windows 11/Python 3.10/Node 22 clean release validation.
2. Retention/deletion and workspace management with explicit reference-graph
   review and no dangling lifecycle/history/recommendation artifacts.
3. Advanced quality/statistics backlog through separately approved contracts.

## Progress Update 180 - Closed Bayesian Study Metadata Deletion

Completed:

- Added checksum-validated deletion preflight and exact study-ID/manifest
  confirmation for closed Bayesian studies. Active studies and predecessor
  studies referenced by successors are blocked; no cascade or lineage severing
  occurs.
- Added a `BEGIN IMMEDIATE` storage transaction that rechecks the complete
  graph, deletes lifecycle/recommendation/history-head rows in dependency order,
  and removes the owning study/version/trial/history graph atomically. Count or
  graph disagreement rolls back.
- Added typed API/OpenAPI/frontend schemas, exact metadata/file counts, stable
  redacted error codes, an impact-review step, and a separate irreversible
  confirmation. The current Bayesian graph owns no files and reports zero
  files/bytes.
- Kept `doe.bayesian_optimization` at `0.2.2`, SQLite at schema 14, and all
  existing Bayesian artifact schemas at 1. Deletion preflight/response schemas
  start at 1 and do not reinterpret stored recommendations.
- Added `docs/workspace_retention_contract.md` for later file-aware cleanup,
  including Windows locking, trusted relative paths, quarantine boundaries,
  crash recovery, and inbound-reference acceptance criteria.
- Full `scripts/check.ps1` passed in 764.9 seconds with backend pytest 721,
  frontend Vitest 102, OpenAPI/frontend contracts 131, Ruff/format over 153
  Python files, mypy over 99 source files, lint/typecheck, and production build.
- Chromium E2E passed in 62.2 seconds on ports `8031`/`5231`, including impact
  review, deletion confirmation, and catalog removal after reload. Two earlier
  launch attempts on other ports ended before browser execution because Windows
  denied one frontend/backend socket bind; the final isolated run passed.
- Validation used Windows 10 Home build 19045, CPython 3.10.11, and Node
  24.17.0 from an uncommitted tree based on main SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`. Windows 11/Python 3.10/Node 22
  remains the release gate. Remote Actions remain unverified because `gh` is
  not installed.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22/CPU-only release validation.
2. Implement one file-owning retention vertical slice, starting with analysis
   exports and their owning analysis graph, including quarantine/recovery tests.
3. Extend the same reviewed ownership model to datasets, DOE, models, and limit
   sets before adding bulk or automatic cleanup.
4. Continue advanced quality/statistics only through an approved contract.

## Progress Update 181 - Individual Analysis Export File Deletion

Completed:

- Added deletion preflight and exact analysis/export/manifest confirmation for
  one app-created JSON/CSV/HTML or regression-prediction CSV export.
- Validated ownership, approved kind/media type, exact relative path,
  non-symlink file, SHA-256, byte size, and parent analysis state without
  exposing paths or raw result values.
- Added same-directory quarantine, post-move integrity recheck, conditional
  metadata transaction, rollback restoration, pending cleanup, and startup
  recovery for committed, metadata-owned, and tampered quarantine cases.
- Added frontend impact review, separate irreversible confirmation, list
  refresh, parent-result preservation copy, and stale-response/reset guards.
- Kept statistical methods, existing export/result schemas, and SQLite schema
  14 unchanged; operational deletion schemas start at 1.
- Full `scripts/check.ps1` passed in 746.7 seconds with backend pytest 731,
  frontend Vitest 105, OpenAPI/frontend contracts 137, Ruff/format over 154
  Python files, mypy over 99 source files, lint/typecheck, and build.
- Chromium E2E passed in 59.9 seconds on `8031`/`5231`, including export
  deletion impact, exact confirmation, list reduction, and parent result
  preservation.
- Validation used Windows 10 build 19045, Python 3.10.11, Node 24.17.0, and
  base SHA `0cbce01d2fa2914459c5be69f070e1703cb631dd`. It is not Windows 11/Node
  22 release evidence; remote Actions remain unverified because `gh` is absent.

Next development order:

1. Run clean Windows 11/Python 3.10/Node 22/CPU-only release validation.
2. Implement analysis-run root deletion with complete owned-file preflight and
   blockers for model/prediction/limit-set/other inbound dependencies.
3. Extend reviewed ownership graphs to datasets, DOE, models, and limit sets
   before any bulk or automatic cleanup.

## Progress Update 182 - Analysis-Run Root Deletion

Completed:

- Added exact-manifest deletion preflight for a succeeded stored analysis run,
  covering its result, row snapshot, supported prediction rows, and all stored
  exports without returning paths or raw values.
- Added explicit model, prediction, limit-set, and job blockers. Deletion does
  not cascade into or silently detach these references.
- Added short Windows-safe quarantine names, full rollback restoration, an
  exact `BEGIN IMMEDIATE` run/artifact transaction, committed cleanup retry,
  and startup restore/removal with checksum validation.
- Added typed UI impact review and irreversible confirmation, history refresh,
  deleted restore/comparison/export clearing, and hook-level stale-response
  tests for both preflight and deletion.
- Method versions, statistical result/config schemas, checksums, and SQLite
  schema 14 remain unchanged. Deletion operational schemas start at 1.
- Browser E2E passed in 66.5 seconds on `8031`/`5231`, including analysis
  history reduction from two to one and clearing deleted result references.
- Final `scripts/check.ps1` passed in 792.7 seconds with backend pytest 738,
  frontend Vitest 109, OpenAPI/frontend contracts 139, Ruff/format over 156
  Python files, mypy over 100 source files, lint/typecheck, and build.

Next allowed work:

1. Implement regression-model deletion with dependent-prediction blockers and
   attribute-control-limit-set deletion with source/audit preservation.
2. Run the clean Windows 11/Python 3.10/Node 22 release gate.
3. Only then extend reviewed ownership graphs to datasets and DOE designs;
   bulk and automatic deletion remain prohibited.

## Progress Update 183 - Regression Model And Limit-Set Deletion

Completed:

- Added explicit, manifest-confirmed deletion for an app-created regression
  model and an immutable attribute-control limit set without deleting either
  source analysis.
- Model deletion is blocked by stored prediction dependencies. Limit-set
  deletion is blocked by Phase II dependencies. No relationship is silently
  detached and no dependent result is cascaded.
- Added exact artifact ownership/path/media/checksum/size validation,
  same-directory quarantine, transactional metadata rechecks, compensating
  restoration, pending cleanup, and startup recovery.
- Added typed backend/frontend contracts, impact review, separate irreversible
  confirmation, dependency guidance, and hook-level stale-response guards.
- Kept statistical method versions, result/config schemas, SQLite schema 14,
  regression model manifest schema 2, and limit-set asset schema 1 unchanged.
  Operational deletion request/response schemas start at 1.
- Final `scripts/check.ps1` passed in 781.8 seconds with backend pytest 750,
  frontend Vitest 111, OpenAPI/frontend contracts 150, Ruff/format over 158
  Python files, mypy over 101 source files, lint/typecheck, and build.
- Chromium E2E passed in 99.3 seconds on `8031`/`5231`, including the model-to-
  prediction and limit-set-to-Phase-II blockers. Validation used Windows 10
  build 19045, Python 3.10.11, Node 24.17.0, and base SHA
  `0cbce01d2fa2914459c5be69f070e1703cb631dd`; this is not Windows 11/Node 22
  release evidence. Remote Actions remain unverified because `gh` is absent.

Next allowed work:

1. Run the clean Windows 11/Python 3.10/Node 22/CPU-only release gate.
2. Implement dataset-root deletion only after documenting every inbound owner
   and using explicit blockers instead of cascade.
3. Extend the same reviewed lifecycle to DOE designs and immutable response
   revisions.
4. Keep bulk, age-based, and automatic cleanup out of scope until all root
   ownership graphs and recovery paths are validated.
5. Continue advanced methods only through a separately approved contract.

## Progress Update 184 - Phase II Boundary And Retained-Model Availability

Completed:

- `quality.attribute_control_chart` is now method `0.3.0` with result schema 3.
  Phase II accepts one valid P/NP/C/U monitoring point; Phase I still requires
  two points and immutable limit-set promotion still requires 20.
- One-point dispersion is explicitly unavailable with df 0 and null ratio.
  No zero, NaN, infinity, or fabricated statistic is stored. Existing
  v0.1/schema-1 and v0.2/schema-2 results retain their stored meaning.
- Phase II preflight schema 2 declares schema/dependency-only validation and
  the UI states that row/filter contracts are checked again at execution.
- Current and restored linear-model results verify the model manifest before
  enabling prediction. Missing/deleted and integrity-error states are separate;
  both preserve the fit result and disable all prediction actions.
- Reload restores only the current dataset version UUID from session storage,
  then refetches version/profile/preview through backend validation. Raw rows,
  filenames, and result payloads are not stored in browser storage.
- Full check passed with backend 763, frontend 114, and direct OpenAPI/frontend
  contract collection 148. Final Chromium E2E passed in 69.2 seconds with
  diagnostics at `.tmp/e2e-diagnostics` and one-point Phase II
  result/export/restore plus model delete/reload/fit restore coverage.
- Validation used Windows 10 build 19045, Python 3.10.11, and Node 24.17.0; it
  is not Windows 11/Node 22 release evidence. Remote Actions are unverified
  because `gh` is unavailable.

Next allowed work:

1. Run the clean Windows 11/Python 3.10/Node 22/CPU-only release gate.
2. Verify the resulting main run and repository required checks in GitHub.
3. Improve Bayesian catalog and successor UX without changing GP/EI behavior.
4. Add dataset-root and DOE-root retention only through separately reviewed
   ownership graphs with explicit blockers and quarantine recovery.
5. Continue advanced quality/statistics only through an approved contract.

## Progress Update 185 - Paste Staging Grid And Canonical Preview UX

Completed:

- Added a `text/plain`-only, view-only paste staging grid with exact raw-string
  submission, raw/grid modes, A1 coordinates, empty/ragged/truncation warnings,
  inert formula-like text, selected-cell inspection, and keyboard navigation.
- Capped materialized preview state at 200 rows, 100 columns, and 20,000 cells;
  a 2,000,000-character browser scan cap labels structural counts as lower
  bounds without changing the submitted full source.
- Added presentation-only first-row header review and explicit server-suggestion
  comparison while keeping parsing confirmation authoritative.
- Added canonical preview page sizes 10/25/50/100, bounded row jump, sticky
  headers, explicit missing/empty labels, and selected-cell inspection without
  loading all canonical rows.
- Kept the paste API, backend size enforcement, immutable dataset version,
  canonical artifact, SQLite schema, and all method/result versions unchanged.
  The P1/P2 edit/version requirements are frozen in
  `docs/pasted_data_grid_contract.md`; cell editing remains unimplemented.
- Added transient regression-model availability error/retry UX without merging
  not-found and integrity-error states.
- Full local development validation passed with backend 763, frontend 131, and
  OpenAPI/frontend contracts 148. The expanded Chromium critical path passed,
  including exact CRLF request preservation, failure retention, reload
  non-restoration, successful clearing, canonical inspection, and all prior
  workflows. Exact duration/evidence is maintained in `docs/ci_status.md`.
- Main production JavaScript is 508.32 kB / 120.48 kB gzip and emits the Vite
  500 kB warning. This is recorded for measured follow-up rather than hidden.
- The development host is Windows 10 build 19045, Python 3.10.11, and Node
  24.17.0 on pushed base SHA
  `702e20f0ed1a377d411cb8d7d3a6faa2c4fcbd6f`; this is not Windows 11/Node 22
  release evidence. Remote Actions are unverified because `gh` is unavailable.

Next allowed work:

1. Run the clean Windows 11/Python 3.10/Node 22 release gate.
2. Verify remote GitHub Actions and required Windows/E2E checks.
3. Improve Bayesian catalog/successor UX without changing GP/EI behavior.
4. Implement dataset-root and then DOE-root retention through separate reviewed
   ownership graphs with explicit inbound blockers and quarantine recovery.
5. Continue advanced quality/statistics only through approved contracts.

## Progress Update 186 - Dedicated Predict And Response Optimizer Entrypoints

Completed:

- Marked all 30 stable catalog IDs available while preserving 25 generic
  analysis-run handlers and five explicit dedicated workflows.
- Added paged, metadata-only regression-model and stored-RSM-analysis catalogs
  with redacted responses and full selected-source revalidation.
- Added top-level Predict and Response Optimizer routes with ID-only reload
  state. Embedded Linear Model/RSM entries remain and share
  `RegressionPredictionPanel`/`ResponseOptimizerPanel` rather than duplicating
  calculations or API contracts.
- Generic analysis-run requests for any dedicated method return
  `analysis_method_uses_dedicated_api` without storing a fake result.
- Kept prediction `0.2.0` and optimizer `0.3.0` plus all persisted schemas
  unchanged. Corrected paste delimiter scoring so Tab is a tie-break only.
- Full local development validation passed with backend 773, frontend 133, and
  OpenAPI/frontend contracts 155. Chromium E2E passed in 76.9 seconds through
  both top-level execution/reload paths and all retained critical paths.
- Main is 511.60 kB / 121.24 kB gzip and still emits the measured 500 kB
  warning. The completed slice is pushed at
  `b12c3b26235089fa28e5b48b1faa2cf627e3bec0`; a clean local checkout passed
  bootstrap, full check, and Chromium E2E. Validation used Windows 10 build
  19045, Python 3.10.11, and Node 24.17.0, so it is not release evidence.
  Remote Actions remain unverified because `gh` is unavailable.

Next allowed work:

1. Run the clean Windows 11/Python 3.10/Node 22 release gate.
2. Verify remote Actions and required Windows/E2E checks.
3. Measure and optimize the main bundle.
4. Improve Bayesian catalog/successor UX.
5. Add dataset-root and DOE-root retention through reviewed ownership graphs.
6. Continue advanced quality/statistics only through approved contracts.

## Progress Update 187 - Tutorial Pack And Dedicated Result Restore

Current approved worktree:

- Add `prediction_id` and `optimization_id` to ID-only workflow URLs and restore
  verified persisted results without recalculation.
- Keep immutable prediction results viewable after source-model deletion while
  continuing to block new prediction; preserve all other integrity failures.
- Hide unrelated generic history/export panels on dedicated workflows and keep
  the workflow-owned prediction paging/CSV and optimizer result restore.
- Correct Bayesian purpose-helper copy to describe current executable GP/EI
  behavior and its confirmation/global-optimum limitations.
- Publish deterministic seed-20260718 synthetic files, SHA manifest, API-derived
  expected results, Korean end-to-end tutorial, and 18-section tutorial smoke.
- Keep every statistical method version, calculation, persisted result schema,
  and SQLite schema unchanged.
- Final local development validation passed with backend 777, frontend 137,
  OpenAPI/frontend 155, and Chromium E2E 74.6 seconds. The host is Windows 10
  build 19045/Python 3.10.11/Node 24.17.0, not release-target evidence; remote
  Actions remain unverified because `gh` is not installed.

Next allowed work after completion:

1. Clean Windows 11/Python 3.10/Node 22 release gate.
2. Remote Actions, required checks, and repository protection review.
3. Measured main-bundle optimization.
4. Regression/RSM source catalog search and large-catalog performance.
5. Bayesian catalog/successor UX, dataset/DOE retention, then advanced backlog.

## Progress Update 188 - Tutorial Truth, Help Center, And Report Center P0

Implemented and validated before commit/push in a worktree based on pushed main
`ee9806a4e491f0d700fba6701ed5cc218d228c62`:

- Generated 18 tutorial numeric blocks from the checked expected-result JSON;
  `scripts/check.ps1` now rejects Markdown drift with method/field diagnostics.
- Moved purpose guidance and the role dictionary to `/help`, kept the analysis
  flow method-first, and added accessible selected-method context help.
- Activated `/reports` with paged generic analysis-run filters, verified result
  restore, and existing JSON/CSV/HTML export creation/list/download/deletion.
- Kept dedicated report capabilities explicit: unsupported Predict, Optimizer,
  RSM, and Bayesian HTML reports are not presented as available.
- Exposed only safe generated `Content-Disposition` and `ETag` download headers
  to the local frontend; no raw filename, value, or path is introduced.
- Final local development validation passed: backend 782, frontend 139,
  OpenAPI/frontend 155, 18 tutorial smoke sections, and Chromium E2E. The host
  remains Windows 10/Python 3.10/Node 24, so this is not release evidence;
  remote Actions remain unverified because `gh` is unavailable.

Next allowed work after completion:

1. Clean Windows 11/Python 3.10/Node 22 release gate.
2. Remote Actions, required checks, and repository protection review.
3. Predict/RSM/Bayesian dedicated HTML report contracts and implementations.
4. Measured main-bundle optimization.
5. Source catalog scale, retention roots, then advanced statistics backlog.
