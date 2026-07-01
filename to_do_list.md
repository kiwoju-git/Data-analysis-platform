# DataLab Studio To-Do List

Last updated: 2026-07-01

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

## 2. Current Code State

Already implemented:

- FastAPI app factory, root route `GET /`, health route `GET /api/v1/health`
- Structured API errors with `correlation_id`
- Local-only default host `127.0.0.1` and narrow CORS
- React 18 + Vite + TypeScript shell with API health display
- PowerShell workflow scripts: `bootstrap.ps1`, `dev.ps1`, `test.ps1`, `check.ps1`
- SQLite migration skeleton through schema version `6`
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
- Minimal React UI for pasted spreadsheet text intake without keeping successful paste contents in React state
- Minimal React UI for profile/preflight warnings, canonical/profile artifact summary, preflight summary, and column-level aggregate/numeric/date-time profile table
- Minimal React schema UI includes a guarded 34-column headerless Bayesian sample role preset: `column_1` as ID, `column_2`-`column_25` as X/features, and `column_26`-`column_34` as Y/responses
- App chrome rendering is split into `frontend/src/AppChrome.tsx`, while `App.tsx` keeps API bootstrap and analysis state ownership
- Dataset workflow state and handlers are split into `frontend/src/useDatasetWorkflow.ts`
- Dataset preparation rendering is split into `frontend/src/DatasetPreparationPage.tsx`, `frontend/src/DatasetParsingPanel.tsx`, `frontend/src/DatasetVersionPanel.tsx`, `frontend/src/DatasetProfileSection.tsx`, and `frontend/src/DatasetPreviewSection.tsx`, while `WorkspaceRouter` chooses the active dataset/analysis page
- Dataset formatting, labels, and profile summary helpers are centralized in `frontend/src/datasetDisplay.ts`
- Analysis method registry with 6 modules and 29 stable method IDs
- Common analysis request, filter snapshot, warning, provenance, and result envelope schemas
- Common analysis run status and job status schemas
- `analysis_runs`, `analysis_artifacts`, and `jobs` metadata tables
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
  - analysis area rendering is further split into `frontend/src/AnalysisShell.tsx`, `frontend/src/DescriptiveAnalysisPanel.tsx`, `frontend/src/GraphicalSummaryPanel.tsx`, `frontend/src/NormalityAnalysisPanel.tsx`, `frontend/src/EqualVariancesPanel.tsx`, `frontend/src/OneSampleTPanel.tsx`, `frontend/src/PairedTPanel.tsx`, `frontend/src/EquivalenceTostPanel.tsx`, `frontend/src/OneSampleWilcoxonPanel.tsx`, `frontend/src/TwoSampleTPanel.tsx`, `frontend/src/MannWhitneyPanel.tsx`, `frontend/src/KruskalWallisPanel.tsx`, `frontend/src/OneWayAnovaPanel.tsx`, `frontend/src/OneProportionPanel.tsx`, `frontend/src/TwoProportionPanel.tsx`, `frontend/src/ChiSquareAssociationPanel.tsx`, `frontend/src/PearsonCorrelationPanel.tsx`, `frontend/src/XyCorrelationPanel.tsx`, and `frontend/src/LinearModelPanel.tsx`
  - root/dataset routes render the dataset preparation page and `/analysis/{module_id}/{method_id}` routes render the analysis page
  - supported filter controls render through a common Workbench slot for dataset-backed methods
  - Workbench steps show data, roles, options, preflight, execution, and results
  - all 29 documented methods show UI guidance for required roles, options, preflight checks, and result focus
  - `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, and `regression.linear_model` expose execution controls
- Analysis run API guard that rejects planned/disabled methods without returning fake results
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
- `regression.linear_model` is the third Gate C1 executable method and computes real NumPy/SciPy-backed OLS linear model results from one numeric response and one or more numeric/categorical predictors on confirmed dataset versions, with safe JSON model manifest persistence, checksum-validated manifest retrieval, stored-model prediction preflight, backend prediction values/intervals from app-created manifests, and frontend preflight result display
- NumPy 2.2.6/SciPy 1.15.3 are production-pinned after the native Windows Python 3.10.11 dependency spike, and a SciPy-backed normality reference fixture was generated and validated
- Descriptive statistics result persistence stores app-owned JSON under the workspace and records result SHA-256 in `analysis_runs`
- Available inline analysis runs persist an `analysis_row_snapshot` artifact with filter snapshot hash, source canonical artifact hash, included row counts, and row ranges for supported filters
- XLSX container checks, sheet-selection warning, and basic stdlib parsing confirmation for the first or named worksheet
- XLSX formula recalculation, merged-cell expansion, hidden row/column handling, and display-format/date serial restoration remain out of scope
- Synthetic upload tests, parsing confirmation tests, canonical artifact tests, and migration upgrade tests from schema version `1`/`2`/`3`/`4`/`5` to `6`
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
  - `POST /api/v1/regression-models/{model_id}/prediction-preflight` validates the stored manifest and target canonical rows for schema drift, required predictor mapping, numeric extrapolation, missing/non-numeric values, and unseen categorical levels
  - `POST /api/v1/regression-models/{model_id}/predictions` runs the same preflight path, rejects error-severity preflight failures, reconstructs the OLS design matrix from the stored manifest, returns capped predicted means plus mean-response confidence intervals and individual prediction intervals, and stores a checksum-validated `regression.predict` result envelope without raw cell values
  - result, row snapshot, model manifest, and prediction result files are removed if metadata insert fails after file writes
- Filter snapshot row freezing:
  - `eda.descriptive` filter snapshots are frozen into `analysis_row_snapshot` artifacts
  - analysis provenance records filter snapshot hash, row snapshot hash, total row count, and included row count
  - supported non-empty filters select canonical row-index ranges before calculation
- Workbench-level frontend controls for supported filters:
  - users can add/remove AND filter conditions in the selected-method Workbench before running supported analyses
  - numeric columns expose `gt`/`gte`/`lt`/`lte`; all columns expose missing and equality conditions
  - filter drafts are validated in the shared UI slot
  - current executable payload serialization into `filter_snapshot.conditions` covers `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, and `regression.linear_model`
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
- Binding the common filter UI state into future executable methods beyond the current eighteen available methods
- Full XLSX workbook semantics beyond cached worksheet values
- Cell-level data editing or transformations that create a new immutable dataset version
- Executable analysis method dispatch beyond the current eighteen available methods
- Any production statistical calculation beyond `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, and `regression.linear_model`
- Any Bayesian, optimizer, DOE, quality, regression prediction target-dataset selection UI, paged prediction result retrieval, or additional hypothesis/categorical test calculation
- Any mock/fake statistical result

Strict rule:

- Do not add statistical calculation mock results, fake charts, fake tables, or placeholder numeric outputs.
- Unimplemented methods may be shown only as `planned` or `disabled`; they must not look executable or complete.

Near-term visualization plan:

- Current completed renderer: `eda.graphical_summary` renders backend-calculated histogram, box plot, Q-Q plot, and ECDF payloads as inline SVG without adding external chart dependencies.
- Next visualization candidates should reuse real result payloads only: `eda.normality` Q-Q plots, `regression.pearson` scatter plot plus confidence annotation, `regression.xy_correlation` matrix heatmap, `categorical.chi_square_association` observed/expected or residual heatmap, and `regression.linear_model` residual/fitted/leverage/Cook diagnostic charts.
- Do not create fake or decorative chart images. If a method does not yet return sufficient chart data, first add the real result payload and tests, then render it.
- Keep chart exports/artifact images, grouped/small-multiple graphical summary, KDE/density rendering, and high-volume canvas/WebGL rendering as later slices.

## 3. Next Actual Implementation PR

Gate B0 first, second, catalog/navigation, and storage/run foundation slices are now implemented in the working tree.

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
  - 29 stable method IDs marked only `planned` or `disabled`
- Common analysis request/result/warning/provenance schemas
- `POST /api/v1/analysis-runs` executes the current available methods and rejects planned/disabled methods without result payloads
- Minimal six-module navigation shell using the backend catalog
- Hash-restorable selected-method Workbench shell:
  - selected method details are shown for all 29 method IDs
  - method-specific guidance describes required roles, options, preflight checks, and result focus for all 29 method IDs
  - route selection state is centralized in `frontend/src/analysisSelection.ts`
  - page boundary rendering is split into `frontend/src/AnalysisPage.tsx`
  - common module, method, guidance, and status rendering is split into `frontend/src/AnalysisWorkbench.tsx`
  - analysis shell and executable panel rendering are split into `frontend/src/AnalysisShell.tsx`, `frontend/src/DescriptiveAnalysisPanel.tsx`, `frontend/src/GraphicalSummaryPanel.tsx`, `frontend/src/NormalityAnalysisPanel.tsx`, `frontend/src/EqualVariancesPanel.tsx`, `frontend/src/OneSampleTPanel.tsx`, `frontend/src/OneSampleWilcoxonPanel.tsx`, `frontend/src/TwoSampleTPanel.tsx`, `frontend/src/MannWhitneyPanel.tsx`, `frontend/src/KruskalWallisPanel.tsx`, `frontend/src/OneProportionPanel.tsx`, and `frontend/src/TwoProportionPanel.tsx`
  - planned/disabled methods show availability state without execution controls
  - `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.paired_t`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` are executable Workbench methods
- Dataset-preparation component split:
  - sidebar, topbar, and dataset context layout are split into `frontend/src/AppChrome.tsx`
  - dataset upload, pasted text, parsing confirmation, schema, preview, and profile workflow state/handlers are split into `frontend/src/useDatasetWorkflow.ts`
  - upload and pasted text intake are composed by `frontend/src/DatasetPreparationPage.tsx`
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
- Analysis run status/cancel API skeleton:
  - `GET /api/v1/analysis-runs/{analysis_id}`
  - `DELETE /api/v1/analysis-runs/{analysis_id}`
- Job status/cancel API skeleton:
  - `GET /api/v1/jobs/{job_id}`
  - `DELETE /api/v1/jobs/{job_id}`
- Tests for v3 to v4 migration, v4 to v5 migration, v5 to v6 migration, analysis/job/regression model metadata round trip, dataset artifact metadata round trip, status lookup, cancellation request, and no fake results
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
- Keep every method except the current eighteen available methods unavailable until real calculation code and tests exist.
- Keep analysis run status/job storage as infrastructure unless a later method requires worker execution.

Still explicitly out of scope:

- Statistical method calculations beyond the current eighteen available methods
- Analysis mock results
- Full profile implementation beyond the current aggregate/duplicate/memory/date-time/profile-artifact preflight slice
- Router-mounted Analysis Workbench pages beyond the current path-restorable shared component shell
- Bayesian optimization, Response Optimizer, DOE, regression, quality control, or hypothesis testing
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

- Stored regression model predictions are reproducible with the same dataset version and schema.
- Model explanation text avoids causal claims.

Current status:

- Started. `regression.pearson` is available as the first narrow C1 slice with real SciPy-backed Pearson product-moment correlation, complete-case exclusion counts, covariance, r, r-squared, p-value, Fisher z CI, non-causation/linearity/outlier warnings, row snapshot provenance, persisted result retrieval, backend reference tests, API tests, and a minimal frontend panel.
- `regression.xy_correlation` is available as the second narrow C1 slice with real SciPy-backed pairwise Pearson X-Y correlation matrices, pair-level N/exclusions, covariance, r, r-squared, p-value, Fisher z CI, failed-cell error codes, row snapshot provenance, persisted result retrieval, backend reference tests, API tests, and a minimal frontend panel.
- `regression.linear_model` is available as the third narrow Gate C1 slice with real NumPy/SciPy-backed OLS for one numeric response and numeric/categorical main-effect predictors, selected numeric quadratic terms, selected numeric-by-numeric interactions, deterministic treatment coding for categorical factors, complete-case exclusions, coefficient SE/t/p/CI, R²/adjusted R², F test, VIF/condition diagnostics, residual/leverage/Cook's distance diagnostics, capped diagnostic points, row snapshot provenance, persisted result retrieval, safe JSON model manifest storage, checksum-validated manifest retrieval, prediction preflight for stored app-created manifests, backend prediction means/intervals from the stored manifest, backend reference tests, API tests, and a minimal frontend panel.
- Spearman/Kendall, adjusted p-values, scatterplot artifacts, categorical interactions, factor-by-numeric interactions, robust covariance, prediction target-dataset selection UI, paged prediction result retrieval, response optimizer, and diagnostic chart artifacts remain planned/disabled until each has real calculation code, reference fixtures, warning metadata, and UI/API coverage.

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

- Not started.

### Gate C3: Measurement System Analysis

Purpose:

- Implement balanced crossed Gage R&R and Gage Run Chart with design validation.

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

- Not started.

### Gate D1: Factorial DOE

Purpose:

- Create immutable factorial design assets and analyze completed design responses.

Implementation scope:

- 2-level full factorial
- Design asset/version
- Randomization, block, replicate, center-point metadata
- Response import
- Effects, OLS, ANOVA, diagnostics

Backend work:

- Generate deterministic design/run order from explicit seed.
- Preserve design after response entry; changes create a new design version.
- Add design analysis only after response data is present and validated.

Frontend work:

- Add DOE design creation flow.
- Show factor settings, randomization seed, run order, and response entry status.
- Prevent accidental rerandomization after responses are recorded.

DB/migration work:

- Add `experiment_designs` and `experiment_runs` when this gate starts.
- Store factor definitions and run order as versioned design assets.

Tests:

- Same seed produces same run order.
- Design immutability after response entry.
- Reference effect and ANOVA fixtures.

Completion criteria:

- Factorial design creation and analysis are reproducible and auditable.

Current status:

- Not started.

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

- Not started.

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

Validation so far:

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

Validation so far:

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

Validation so far:

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
