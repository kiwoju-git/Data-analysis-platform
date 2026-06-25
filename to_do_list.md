# DataLab Studio To-Do List

Last updated: 2026-06-25

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
- SQLite migration skeleton through schema version `5`
- `datasets` metadata table for raw upload provenance
- `dataset_versions` metadata table for immutable parsing-confirmed versions
- `dataset_columns` metadata table preserving original names and unique display names
- `dataset_artifacts` metadata table for app-owned dataset artifact paths and hashes
- Atomic file write helper for small app-owned artifacts, with short temporary filename prefixes for deep Windows workspace paths
- `POST /api/v1/datasets` multipart upload
- `POST /api/v1/datasets/{dataset_id}/confirm-parsing` for delimited text files
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
- Upload size limit through `DATALAB_MAX_UPLOAD_BYTES`
- Sanitized filename handling and UUID-based raw workspace paths
- Raw upload preservation with SHA-256 and byte size metadata
- Confirm-parsing raw upload integrity recheck against stored SHA-256 and byte size before canonical artifact creation
- Parsing suggestions for encoding, delimiter, quote, decimal, thousands, header presence, header row, and data start row
- Explicit parsing confirmation records encoding, delimiter, quote, decimal/thousands, header presence, header row, data start row, and missing tokens
- Delimited TXT files with leading preamble and no header can be confirmed with generated `column_1...column_n` names
- Default parsing-confirmation missing tokens include `N/T` for local no-test/not-tested style entries, while still remaining user-editable before confirmation
- Immutable dataset version `v1` creation for confirmed delimited text uploads
- Streamed header and row-count scan for delimited text without browser full-data loading
- Dataset schema lookup/update for display name, measurement level, role, and unit
- Paginated canonical row preview with `limit <= 100`
- Canonical UTF-8 JSONL rows and JSON manifest materialization for confirmed delimited text dataset versions
- Basic delimited-text profile/preflight API with aggregate missing, unique-count, numeric, date/time, constant-column, possible-ID, non-numeric-in-numeric, non-datetime-in-datetime, duplicate-row, canonical-artifact, persisted profile-artifact, and memory-estimate warnings
- Minimal React UI for upload, parsing confirmation, dataset Context Bar, schema update, and row preview
- Minimal React UI for profile/preflight warnings, canonical/profile artifact summary, preflight summary, and column-level aggregate/numeric/date-time profile table
- Minimal React schema UI includes a guarded 34-column headerless Bayesian sample role preset: `column_1` as ID, `column_2`-`column_25` as X/features, and `column_26`-`column_34` as Y/responses
- Analysis method registry with 6 modules and 29 stable method IDs
- Common analysis request, filter snapshot, warning, provenance, and result envelope schemas
- Common analysis run status and job status schemas
- `analysis_runs`, `analysis_artifacts`, and `jobs` metadata tables
- Analysis run and job status/cancel API skeletons
- Six-module planned/disabled navigation shell in the React UI
- Six-module selected-method Workbench shell in the React UI:
  - module and method selection comes from the backend catalog
  - selected module/method is restorable through `/analysis/{module_id}/{method_id}` with legacy hash fallback
  - common shell rendering is split into `frontend/src/AnalysisWorkbench.tsx`
  - Workbench steps show data, roles, options, preflight, execution, and results
  - all 29 documented methods show UI guidance for required roles, options, preflight checks, and result focus
  - only `eda.descriptive` exposes execution controls
- Analysis run API guard that rejects planned/disabled methods without returning fake results
- `eda.descriptive` is the first executable method and computes real descriptive statistics from confirmed dataset versions
- Descriptive statistics result persistence stores app-owned JSON under the workspace and records result SHA-256 in `analysis_runs`
- `eda.descriptive` runs persist an `analysis_row_snapshot` artifact with filter snapshot hash, source canonical artifact hash, included row counts, and row ranges for supported filters
- XLSX container checks and sheet-selection warning
- XLSX parsing confirmation is intentionally rejected with `xlsx_confirmation_pending` until workbook parser adoption
- Synthetic upload tests, parsing confirmation tests, canonical artifact tests, and migration upgrade tests from schema version `1`/`2`/`3`/`4` to `5`
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
- Filter snapshot row freezing:
  - `eda.descriptive` filter snapshots are frozen into `analysis_row_snapshot` artifacts
  - analysis provenance records filter snapshot hash, row snapshot hash, total row count, and included row count
  - supported non-empty filters select canonical row-index ranges before calculation

Not implemented yet:

- Full profile API beyond the current aggregate/duplicate/memory/date-time preflight slice
- Deeper route-based Analysis Workbench page decomposition and additional shared feature components
- Frontend controls for supported filter conditions
- Cell-level data editing or transformations that create a new immutable dataset version
- Executable analysis method dispatch beyond the inline `eda.descriptive` slice
- Any statistical calculation beyond `eda.descriptive`
- Any Bayesian, optimizer, DOE, regression, quality, or hypothesis test calculation
- Any mock/fake statistical result

Strict rule:

- Do not add statistical calculation mock results, fake charts, fake tables, or placeholder numeric outputs.
- Unimplemented methods may be shown only as `planned` or `disabled`; they must not look executable or complete.

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
- `POST /api/v1/analysis-runs` executes `eda.descriptive` and rejects planned/disabled methods without result payloads
- Minimal six-module navigation shell using the backend catalog
- Hash-restorable selected-method Workbench shell:
  - selected method details are shown for all 29 method IDs
  - method-specific guidance describes required roles, options, preflight checks, and result focus for all 29 method IDs
  - common module, method, guidance, and status rendering is split into `frontend/src/AnalysisWorkbench.tsx`
  - planned/disabled methods show availability state without execution controls
  - `eda.descriptive` remains the only executable Workbench method
- Tests for method ID stability, disabled method behavior, and no mock results
- `eda.descriptive` first real method:
  - pure calculation module independent of FastAPI/UI
  - hand-checkable descriptive fixture and edge tests
  - API integration test through dataset version abstraction
  - minimal UI column selector and result table
  - result JSON persisted under workspace with SHA-256 in `analysis_runs`
- SQLite schema v4:
  - `analysis_runs`
  - `analysis_artifacts`
  - `jobs`
- SQLite schema v5:
  - `dataset_artifacts`
- Analysis run status/cancel API skeleton:
  - `GET /api/v1/analysis-runs/{analysis_id}`
  - `DELETE /api/v1/analysis-runs/{analysis_id}`
- Job status/cancel API skeleton:
  - `GET /api/v1/jobs/{job_id}`
  - `DELETE /api/v1/jobs/{job_id}`
- Tests for v3 to v4 migration, v4 to v5 migration, analysis/job metadata round trip, dataset artifact metadata round trip, status lookup, cancellation request, and no fake results
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

- Move the shared Workbench into deeper dedicated route-level analysis components/pages, or add frontend controls for supported filter conditions.
- Keep every method except `eda.descriptive` unavailable until real calculation code and tests exist.
- Keep analysis run status/job storage as infrastructure unless a later method requires worker execution.

Still explicitly out of scope:

- Statistical method calculations beyond `eda.descriptive`
- Analysis mock results
- Full profile implementation beyond the current aggregate/duplicate/memory/date-time/profile-artifact preflight slice
- Full dedicated route-based Analysis Workbench beyond the current path-restorable shared component shell
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
- Still missing in Gate B0/B1 transition: deeper route-based Analysis Workbench page decomposition, frontend filter controls, and additional reference-backed methods.
- XLSX upload is accepted for envelope validation only; parsing confirmation remains blocked until a workbook parser dependency is reviewed.

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

- Not started.

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

- Not started.

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

- Add or complete `regression_models` storage.
- Store model manifest and schema hash, not unsafe arbitrary deserialization payloads.

Tests:

- Reference correlation and OLS fixtures.
- Multicollinearity, singular matrix, non-finite, extrapolation, schema drift tests.
- Prediction reproducibility tests.

Completion criteria:

- Stored regression model predictions are reproducible with the same dataset version and schema.
- Model explanation text avoids causal claims.

Current status:

- Not started.

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
- XLSX confirmation remains intentionally blocked until workbook parser dependency review.
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
- Frontend navigation is still a shell; selected analyses now have path-level restore, but the Workbench has not been decomposed into dedicated route pages.

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
- Next narrow slice should split deeper route-level Workbench views or add frontend controls for supported filters.
- Keep frontend filter controls and deeper Workbench decomposition as separate narrow slices unless one is explicitly selected.
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
- XLSX parsing confirmation remains intentionally blocked until workbook parser dependency review.

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
- Next narrow slice should add frontend controls for supported filters or deeper route-level Workbench separation.
- Keep frontend filter controls and deeper Workbench decomposition as separate narrow slices.
- Do not add Parquet/`pyarrow` until dependency review is complete.

Validation:

- Targeted backend pytest for dataset upload/profile plus API contracts: passed, 35 tests.
- Backend ruff check: passed.
- Backend mypy: passed, 35 source files.
- Full `scripts/check.ps1`: passed; backend pytest 53 tests, frontend lint/typecheck/Vitest 6 tests/build passed.

Known limitations:

- Rows preview still streams the raw upload for bounded user preview.
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
- Next narrow slice should split the shared Workbench into deeper dedicated route-level analysis pages or add frontend controls for supported filters.
- Keep frontend filter controls as a separate narrow slice unless the selected next slice needs it.
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
- Rows preview still streams the raw upload for bounded user preview.
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

- Split the shared Workbench into deeper dedicated route-level analysis pages, or add frontend controls for supported filters.
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
- Rows preview still streams the raw upload for bounded user preview.
- JSONL canonical rows are a stdlib local format; Parquet remains a future candidate after `pyarrow` review.
