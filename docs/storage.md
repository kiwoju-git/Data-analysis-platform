# Storage and Migration Notes

Gate A introduced a minimal SQLite metadata store skeleton.
Gate B0 extends it with immutable dataset-version metadata and analysis run/job metadata contracts.

## Metadata Database

- Default workspace root: `%LOCALAPPDATA%\DataLabStudio\` on Windows.
- Development override: `DATALAB_WORKSPACE_ROOT`.
- Metadata path under the workspace root: `db\metadata.sqlite3`.
- Runtime workspace and database files must not be committed to Git.

## Migration Skeleton

- Current schema version: `8`.
- Migration history is recorded in `schema_migrations`.
- `PRAGMA user_version` is set to the current schema version after migrations run.
- Startup initializes the metadata store during FastAPI lifespan startup.
- Version `2` adds the `datasets` table for raw upload provenance and parsing-entry metadata.
- Version `3` adds `dataset_versions` and `dataset_columns`.
- Version `4` adds `analysis_runs`, `analysis_artifacts`, and `jobs`.
- Version `5` adds `dataset_artifacts`.
- Version `6` adds `regression_models` for safe app-created regression model manifest metadata.
- Version `7` adds `experiment_designs`, `experiment_design_versions`, and `experiment_runs` for DOE design assets.
- Version `8` adds `experiment_run_responses` for numeric DOE response entry keyed to immutable design versions and run IDs.
- `dataset_versions.parsing_options_json` stores confirmed parsing options as canonical JSON.
- `dataset_columns` preserves the original header text separately from the unique display name.
- `analysis_runs.config_json` stores request/config snapshots and must include `schema_version`.
- `analysis_runs.result_path` and `result_sha256` are populated for succeeded inline analysis runs.
- `PATCH /api/v1/dataset-versions/{version_id}/schema` treats unchanged display name, measurement level, role, and unit values as a no-op that preserves `schema_hash` and stale state. Real schema metadata changes update `dataset_versions`, `dataset_columns`, and mark existing `analysis_runs` for the same `dataset_version_id` as `stale=true` in one SQLite transaction.
- `dataset_artifacts` stores relative workspace paths, hashes, media type, and byte size for app-owned dataset artifacts such as canonical rows, canonical manifests, and profile summaries.
- `analysis_artifacts` stores relative workspace paths and hashes for app-owned artifacts, not raw result blobs. Available inline analysis methods record an `analysis_row_snapshot` artifact for the frozen row selection.
- `regression_models` stores model ID, source analysis ID, dataset version ID, method ID/version, schema hash, relative manifest path, manifest SHA-256, app version, and creation time for app-created regression models only.
- `experiment_designs`, `experiment_design_versions`, and `experiment_runs` store DOE design assets, generated run order, factor settings, and design checksum metadata.
- `experiment_run_responses` stores numeric DOE response values by design version and run ID; response saving updates the design status in the same SQLite transaction without mutating run metadata.
- `jobs` stores job state, progress, cancellation request state, and sanitized error codes.
- Upgrade from schema versions `1`, `2`, `3`, `4`, `5`, `6`, and `7` to `8` is covered by unit tests.

## Canonical Parsed Artifact Decision

- The current stdlib canonical materialization writes UTF-8 JSONL rows plus a JSON manifest under `workspaces/datasets/{dataset_id}/versions/{version_id}/`.
- SQLite records only relative artifact paths, SHA-256 hashes, media types, and byte sizes; raw row values are not stored in metadata tables.
- `confirm-parsing` re-reads the preserved raw upload in streaming mode and compares SHA-256 plus byte size against `datasets` metadata before schema scan or canonical materialization.
- Rows preview, profile, `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart` all read validated canonical rows after parsing confirmation. They do not reparse the raw upload as a fallback.
- Paginated rows preview now verifies the entire canonical JSONL artifact before returning a page, so `limit` cannot stop validation before row count, size, SHA-256, row-index order, column count, and value-type checks complete.
- This preview policy intentionally spends a full artifact scan before serving a small page. It is the safer Gate B default, but large datasets should later move to a verified-artifact cache, row offset index, chunk-level hash manifest, or verified-session cache so repeated previews do not rescan unchanged artifacts every time.
- Profile scans persist raw-value-free `profile_summary` JSON artifacts under the dataset version workspace and upsert the latest profile artifact metadata in `dataset_artifacts`.
- Profile artifacts include `schema_hash`, `profile_schema_version`, and `source_canonical_artifact_sha256`; `GET /profile` reuses the latest artifact only when those values and the artifact checksums still match.
- Succeeded inline analysis result JSON can be fetched through `GET /api/v1/analysis-runs/{analysis_id}/result`; the service validates the relative `result_path` and `result_sha256` before returning the stored envelope.
- Stored inline analysis run history can be fetched through `GET /api/v1/analysis-runs?dataset_version_id={version_id}&limit=50&offset=0`. The list response is metadata-only: it includes status, stale state, result availability, artifact count, timestamps, method ID/version, dataset version ID, and `has_more`, but not raw result payloads, raw cell values, or internal artifact paths. The endpoint also accepts metadata-only filters for `method_id`, `status`, `stale`, and `result_available`.
- Two stored inline analysis results can be compared through `GET /api/v1/analysis-runs/comparison?left_analysis_id={left_id}&right_analysis_id={right_id}`. The service checksum-validates both stored result envelopes, then returns only comparison metadata: method/version/dataset compatibility, stale/result SHA/warning/provenance counts, summary type, and field-level metadata differences. For compatible `eda.descriptive` stored results, it also returns a method-specific comparison of saved column summary metrics (`n_*`, mean, std, min, quartiles, median, max) by common `column_id`. For compatible `hypothesis.one_sample_t` stored results, it returns response-column identity, saved option differences, and saved sample/contrast metric deltas. For compatible `hypothesis.two_sample_t` stored results, it returns response/group column identity, group-set/order compatibility without group-label values, saved option differences, group summary deltas by stored group index, and contrast/effect-size metric deltas. For compatible `hypothesis.paired_t` stored results, it returns before/after column identity, saved option differences, complete-pair exclusion deltas, paired-sample summary deltas, and contrast/effect-size metric deltas. For compatible `hypothesis.equivalence_tost` stored results, it returns response-column identity, saved equivalence bounds/reference/decision differences, one-sided test deltas, TOST p-value deltas, CI deltas, and effect-size metric deltas. For compatible `hypothesis.one_way_anova` stored results, it returns response/group column identity, group-set/order compatibility without raw group-label values, saved option differences, group summary deltas by stored group index, ANOVA table/test/effect-size deltas, and post-hoc metadata such as comparison count without post-hoc group-label values. For compatible `hypothesis.kruskal_wallis` stored results, it returns response/group column identity, group-set/order compatibility without raw group-label values, saved option differences, group rank-summary deltas by stored group index, H-test/effect-size/tie-correction deltas, and post-hoc comparison count without Dunn post-hoc group-label values. These comparisons use only stored result payloads. They do not expose raw result payloads, raw cell values, or internal paths, and they do not recalculate statistics.
- `POST /api/v1/analysis-runs/{analysis_id}/exports/json` creates a checksum-recorded `analysis_result_json_export` artifact under the analysis workspace after revalidating the stored result file. The response exposes export IDs, media type, size, SHA-256, stale flag, and the exported envelope, but not internal relative or absolute filesystem paths.
- `POST /api/v1/analysis-runs/{analysis_id}/exports/csv` creates a checksum-recorded `analysis_result_csv_export` artifact under the analysis workspace after revalidating the stored result file. The first CSV contract is a generic long-form `section,path,value` table over the stored result envelope. Each cell is escaped for spreadsheet formula injection when it begins, after leading whitespace, with `=`, `+`, `-`, or `@`, or begins with tab/newline control characters. The response exposes export IDs, media type, size, SHA-256, stale flag, row count, columns, and a small preview, but not internal relative or absolute filesystem paths.
- `POST /api/v1/analysis-runs/{analysis_id}/exports/html` creates a checksum-recorded `analysis_result_html_report` artifact under the analysis workspace after revalidating the stored result file. The HTML report is self-contained and static, with escaped text content, no scripts, no external resources, and no internal relative or absolute filesystem paths. It includes method-specific stored-result sections for `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, the current generic `hypothesis.*` analysis-run methods, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, and the current generic `quality.*` analysis-run methods, and falls back to the generic result-envelope table for every method.
- `GET /api/v1/analysis-runs/{analysis_id}/exports/{export_id}/download` downloads created JSON/CSV/HTML export artifacts only after validating the `analysis_artifacts` row, artifact kind, relative path safety, file existence, and SHA-256 checksum. Download responses stream validated bytes with an attachment filename derived only from IDs and do not expose internal workspace paths. Recovery failures use stable codes: `analysis_export_not_found`, `analysis_export_path_invalid`, `analysis_export_file_missing`, and `analysis_export_checksum_mismatch`.
- `GET /api/v1/analysis-runs/{analysis_id}/exports` lists created JSON/CSV/HTML export artifact metadata with export IDs, artifact kind, media type, SHA-256, creation time, and download endpoint URL. It does not expose `analysis_artifacts.path`, relative workspace paths, or absolute filesystem paths.
- New generic analysis-run result envelopes include runtime/build provenance fields: Python version, platform, `Settings.git_commit` with `DATALAB_GIT_COMMIT` fallback, and NumPy/SciPy package versions.
- Available inline analysis methods freeze filter snapshots as `analysis_row_snapshot` JSON artifacts under `workspaces/analyses/{analysis_id}/row_snapshot.json`. The payload records the dataset version, source schema hash, source canonical artifact hash, filter snapshot hash, row identity, and included row count without raw cell values.
- `regression.linear_model` also writes a safe JSON regression model manifest under the analysis workspace, records it as a `regression_model_manifest` analysis artifact, and stores a `regression_models` metadata row in the same SQLite transaction as the analysis run. The manifest contains the app-created OLS specification, coefficients, fit summary, diagnostic summary, dataset version, schema hash, canonical artifact hash, row snapshot hash, package versions, and OLS prediction basis. It does not use pickle/joblib or external model uploads.
- `GET /api/v1/regression-models/{model_id}` validates the stored manifest relative path and SHA-256 before returning the manifest envelope. Missing, invalid, or checksum-mismatched manifests return explicit recovery errors and do not expose absolute filesystem paths.
- `POST /api/v1/regression-models/{model_id}/prediction-preflight` validates the same manifest checksum, reads the source row snapshot when deriving numeric training ranges, and scans only the target dataset version's validated canonical rows. It returns schema/column/range/category issue counts without raw cell samples or absolute paths.
- `POST /api/v1/regression-models/{model_id}/predictions` reuses that validation path, stores a `regression.predict` result envelope under the analysis workspace with SHA-256 metadata, caps inline prediction rows, and omits raw target cell values from the response and stored config.
- `doe.factorial_design` design creation stores design/version/run metadata in SQLite and response entry stores only the app-entered numeric response series in `experiment_run_responses`; it does not create DOE effects, OLS, ANOVA, or fake analysis result artifacts.
- `GET /api/v1/doe-designs/{design_id}/report.html` renders a checksum-verified, self-contained static HTML report from the stored DOE design metadata and entered response series. It does not create an analysis-run artifact, does not compute DOE effects/OLS/ANOVA/diagnostics, and does not expose internal workspace paths.
- The current filter expression engine supports conjunctions of `is_missing`, `is_not_missing`, `eq`, `ne`, and numeric `gt`/`gte`/`lt`/`lte` conditions. Unsupported or invalid filters fail before row snapshot or result artifacts are written.
- Parquet remains the preferred higher-performance canonical data format candidate for later slices.
- Current Windows Python 3.10 environment check on 2026-06-24 found `pyarrow_available=False`.
- `pyarrow` is not added in this slice because dependency compatibility, wheel availability, license, size, and offline runtime behavior still need a recorded review.
- Until that review is done, delimited-text dataset versions use preserved raw upload plus confirmed `parsing_options_json`, `dataset_columns`, and the app-owned JSONL canonical rows manifest as the reproducible source of truth.
- Pickle/joblib are not allowed as a temporary canonical data format.

## Recovery Direction

Future schema changes must add forward migrations with tests for upgrade from the previous schema. Before destructive or non-idempotent migrations are introduced, add a backup step and document the restore path.

## Atomic File Writes

- Use `backend.app.storage.atomic.atomic_write_bytes` or `atomic_write_text` for small metadata-adjacent artifacts such as manifests, analysis result JSON, and export manifests.
- The helper writes a temporary file in the target directory, flushes and fsyncs file content, then replaces the target with `os.replace`.
- The target directory is created before writing.
- The helper uses a short temporary filename prefix to avoid Windows path-length failures in deep workspace paths.
- If the writer fails before replacement, the previous target file is preserved and the temporary file is removed.
- Do not use this helper to stream large uploaded datasets directly; large file ingestion needs chunked validation, hashing, size checks, and cleanup logic in Gate B.
