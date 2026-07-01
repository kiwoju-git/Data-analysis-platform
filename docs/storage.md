# Storage and Migration Notes

Gate A introduced a minimal SQLite metadata store skeleton.
Gate B0 extends it with immutable dataset-version metadata and analysis run/job metadata contracts.

## Metadata Database

- Default workspace root: `%LOCALAPPDATA%\DataLabStudio\` on Windows.
- Development override: `DATALAB_WORKSPACE_ROOT`.
- Metadata path under the workspace root: `db\metadata.sqlite3`.
- Runtime workspace and database files must not be committed to Git.

## Migration Skeleton

- Current schema version: `6`.
- Migration history is recorded in `schema_migrations`.
- `PRAGMA user_version` is set to the current schema version after migrations run.
- Startup initializes the metadata store during FastAPI lifespan startup.
- Version `2` adds the `datasets` table for raw upload provenance and parsing-entry metadata.
- Version `3` adds `dataset_versions` and `dataset_columns`.
- Version `4` adds `analysis_runs`, `analysis_artifacts`, and `jobs`.
- Version `5` adds `dataset_artifacts`.
- Version `6` adds `regression_models` for safe app-created regression model manifest metadata.
- `dataset_versions.parsing_options_json` stores confirmed parsing options as canonical JSON.
- `dataset_columns` preserves the original header text separately from the unique display name.
- `analysis_runs.config_json` stores request/config snapshots and must include `schema_version`.
- `analysis_runs.result_path` and `result_sha256` are populated for succeeded inline analysis runs.
- `PATCH /api/v1/dataset-versions/{version_id}/schema` updates `dataset_versions`, `dataset_columns`, and marks existing `analysis_runs` for the same `dataset_version_id` as `stale=true` in one SQLite transaction.
- `dataset_artifacts` stores relative workspace paths, hashes, media type, and byte size for app-owned dataset artifacts such as canonical rows, canonical manifests, and profile summaries.
- `analysis_artifacts` stores relative workspace paths and hashes for app-owned artifacts, not raw result blobs. Available inline analysis methods record an `analysis_row_snapshot` artifact for the frozen row selection.
- `regression_models` stores model ID, source analysis ID, dataset version ID, method ID/version, schema hash, relative manifest path, manifest SHA-256, app version, and creation time for app-created regression models only.
- `jobs` stores job state, progress, cancellation request state, and sanitized error codes.
- Upgrade from schema versions `1`, `2`, `3`, `4`, and `5` to `6` is covered by unit tests.

## Canonical Parsed Artifact Decision

- The current stdlib canonical materialization writes UTF-8 JSONL rows plus a JSON manifest under `workspaces/datasets/{dataset_id}/versions/{version_id}/`.
- SQLite records only relative artifact paths, SHA-256 hashes, media types, and byte sizes; raw row values are not stored in metadata tables.
- `confirm-parsing` re-reads the preserved raw upload in streaming mode and compares SHA-256 plus byte size against `datasets` metadata before schema scan or canonical materialization.
- Rows preview, profile, `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, and `categorical.chi_square_association` all read validated canonical rows after parsing confirmation. They do not reparse the raw upload as a fallback.
- Profile scans persist raw-value-free `profile_summary` JSON artifacts under the dataset version workspace and upsert the latest profile artifact metadata in `dataset_artifacts`.
- Profile artifacts include `schema_hash`, `profile_schema_version`, and `source_canonical_artifact_sha256`; `GET /profile` reuses the latest artifact only when those values and the artifact checksums still match.
- Succeeded inline analysis result JSON can be fetched through `GET /api/v1/analysis-runs/{analysis_id}/result`; the service validates the relative `result_path` and `result_sha256` before returning the stored envelope.
- Available inline analysis methods freeze filter snapshots as `analysis_row_snapshot` JSON artifacts under `workspaces/analyses/{analysis_id}/row_snapshot.json`. The payload records the dataset version, source schema hash, source canonical artifact hash, filter snapshot hash, row identity, and included row count without raw cell values.
- `regression.linear_model` also writes a safe JSON regression model manifest under the analysis workspace, records it as a `regression_model_manifest` analysis artifact, and stores a `regression_models` metadata row in the same SQLite transaction as the analysis run. The manifest contains the app-created OLS specification, coefficients, fit summary, diagnostic summary, dataset version, schema hash, canonical artifact hash, row snapshot hash, package versions, and OLS prediction basis. It does not use pickle/joblib or external model uploads.
- `GET /api/v1/regression-models/{model_id}` validates the stored manifest relative path and SHA-256 before returning the manifest envelope. Missing, invalid, or checksum-mismatched manifests return explicit recovery errors and do not expose absolute filesystem paths.
- `POST /api/v1/regression-models/{model_id}/prediction-preflight` validates the same manifest checksum, reads the source row snapshot when deriving numeric training ranges, and scans only the target dataset version's validated canonical rows. It returns schema/column/range/category issue counts without raw cell samples or absolute paths.
- `POST /api/v1/regression-models/{model_id}/predictions` reuses that validation path, stores a `regression.predict` result envelope under the analysis workspace with SHA-256 metadata, caps inline prediction rows, and omits raw target cell values from the response and stored config.
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
