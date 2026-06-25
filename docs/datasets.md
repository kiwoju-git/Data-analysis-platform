# Dataset Notes

Gate B currently covers upload, parsing confirmation, canonical JSONL materialization, schema metadata update, paginated row preview, and a profile/preflight scan with persisted profile artifacts for delimited text and basic XLSX datasets.

## Current API

`POST /api/v1/datasets`

- Accepts multipart file uploads.
- Supports `.csv`, `.tsv`, `.xlsx`, and `.txt` as a nonstandard delimited-text candidate.
- Preserves the raw upload unchanged under the configured local workspace.
- Records SHA-256, byte size, sanitized original filename, detected format, media type, and stored relative path in SQLite metadata.
- Returns parsing suggestions, including encoding, delimiter, header presence, header row, and data start row where applicable.
- For delimited text with leading notes/preamble, the suggestion scans the initial text window for the first consistent tabular row run. If the first tabular row looks like data instead of headers, it suggests `has_header=false` and a 1-based `data_start_row`.
- Upload does not parse full data, preview rows, or run analysis.

`POST /api/v1/datasets/paste`

- Accepts pasted delimited text, such as cells copied from Excel or another spreadsheet.
- Stores the pasted text as a preserved local raw dataset with SHA-256, byte size, sanitized filename, detected format, and parsing suggestions.
- Defaults to `pasted-data.txt`, so delimiter detection can choose tab, comma, semicolon, or pipe from the pasted content.
- Uses the same parsing confirmation, immutable version, canonical artifact, preview, profile, and analysis path as file uploads.
- The current UI clears the textarea after a successful paste registration and keeps only the returned upload metadata in React state.

`POST /api/v1/datasets/{dataset_id}/confirm-parsing`

- Accepts explicit parsing options for delimited text files: encoding, delimiter, quote char, decimal/thousands, header presence, header row, data start row, and missing tokens.
- Accepts basic XLSX parsing confirmation for the first worksheet by default or a user-specified `xlsx_sheet_name`. XLSX confirmation reads cached cell values from worksheet XML into the same canonical JSONL row format used by delimited text.
- The current default missing-token list shown by the UI is empty string, `NA`, `N/A`, `null`, and `N/T`; users can edit it before confirmation.
- Streams the raw file with the confirmed options and records immutable dataset version `v1`.
- Materializes app-owned canonical UTF-8 JSONL rows plus a JSON manifest under the local workspace and stores only artifact metadata/hash in SQLite.
- For headerless delimited text, generated original column names are `column_1`, `column_2`, and so on, based on the confirmed first data row width.
- Stores `dataset_columns` with preserved `original_name`, unique `display_name`, inferred physical `data_type`, and unresolved measurement/role defaults unless the request explicitly confirms them.
- Rejects repeated confirmation for the same raw dataset with `dataset_already_confirmed`.
- XLSX support does not recalculate formulas, expand merged cells, restore Excel display formatting, or convert Excel date serials into formatted datetimes in this slice.

`GET /api/v1/datasets/{dataset_id}/versions`

- Lists immutable versions for one raw dataset.

`GET /api/v1/dataset-versions/{version_id}`

- Returns version metadata, schema hash, confirmed parsing options, column metadata, and canonical rows artifact metadata when present.

`GET /api/v1/dataset-versions/{version_id}/schema`

- Returns the current dataset schema hash and column metadata.

`PATCH /api/v1/dataset-versions/{version_id}/schema`

- Updates confirmed column display name, measurement level, role, and unit.
- Does not change raw bytes, original column names, inferred data types, row count, or source SHA-256.
- Rejects duplicate display names and unknown column IDs without echoing raw row values.
- The current UI includes a guarded helper for headerless 34-column Bayesian optimization samples: `column_1` as ID, `column_2` through `column_25` as features, and `column_26` through `column_34` as responses. It only updates schema metadata drafts; it does not edit cell values.

`GET /api/v1/dataset-versions/{version_id}/rows`

- Returns a bounded row preview using `offset` and `limit`.
- Enforces `offset >= 0`, `1 <= limit <= 100`.
- Streams the validated canonical rows artifact and returns only the requested page.
- For headerless datasets, row index `0` maps to the confirmed `data_start_row`.

`GET /api/v1/dataset-versions/{version_id}/profile`

- Streams the validated canonical rows artifact and returns aggregate profile/preflight data only.
- Reports row count, schema hash, per-column present/missing counts, missing rate, capped unique count, numeric parse count, numeric min/max/mean, date/time parse count, date/time min/max, date/time format candidates, timezone-awareness counts, constant-column flag, and warnings.
- Reports canonical artifact metadata plus preflight fields for estimated memory bytes, duplicate row count, duplicate row check cap, and cap status.
- Persists a raw-value-free `profile_summary` JSON artifact under the local workspace, records its SHA-256/size/path metadata in `dataset_artifacts`, and returns `profile_artifact` metadata in the API response.
- Detects all-missing columns, high missing rate, constant columns, possible identifier columns, possible date/time columns, capped high-cardinality columns, non-numeric values inside columns currently marked as numeric, non-date/time values inside columns currently marked as datetime/time, mixed date/time formats, mixed timezone awareness, duplicate rows, and missing/incomplete canonical artifacts.
- Does not return raw cell values or value samples.
- This is still not the final full profile contract. Date/time detection is a conservative preflight summary only and does not coerce values or create a new dataset version.

## Safety Rules

- Default upload limit: 100 MB via `DATALAB_MAX_UPLOAD_BYTES`.
- Filenames are sanitized and never used as storage paths.
- Stored raw upload paths are UUID-based relative paths.
- Unsupported binary files, path traversal filenames, extension/type mismatches, empty files, oversized files, invalid XLSX containers, and excessive XLSX decompression ratios are rejected.
- Client errors must not include raw cell values, absolute paths, SQL, or tracebacks.
- Browser state must not hold the full dataset; the current UI stores upload metadata, parsing options, version/schema/artifact metadata, one preview page, and aggregate profile/preflight data only.

## Analysis Use

`POST /api/v1/analysis-runs`

- `eda.descriptive` is currently the only executable method.
- It requires a confirmed `dataset_version_id` and `options.column_ids`.
- It streams the validated canonical rows artifact and computes real descriptive statistics for selected numeric columns.
- The result records `n_total`, `n_used`, missing count, non-numeric exclusion count, mean, sample standard deviation, min, Q1, median, Q3, max, warning codes, and provenance.
- Filter snapshots are frozen into an `analysis_row_snapshot` artifact linked from `analysis_artifacts`; the snapshot records the filter hash, canonical artifact hash, row identity, row ranges, and included row count without raw cell values.
- The current filter expression engine supports conjunctions of `is_missing`, `is_not_missing`, `eq`, `ne`, and numeric `gt`/`gte`/`lt`/`lte` conditions.
- The current `eda.descriptive` UI can create those supported AND filter conditions and validates incomplete filter values before submitting the analysis request.
- Other analysis methods remain unavailable and must not return mock results.

## Next Step

The next Gate B slice should move toward deeper Workbench page/component separation or cross-method filter reuse.
Full dataset parsing must remain explicit and must not silently coerce values or infer study design from dtype alone.
