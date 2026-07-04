# Dataset Notes

Gate B currently covers upload, parsing confirmation, canonical JSONL materialization, schema metadata update, paginated row preview, and a profile/preflight scan with persisted profile artifacts for delimited text and basic XLSX datasets.

The current React data-preparation surface is rendered through `frontend/src/DatasetPreparationPage.tsx`, `frontend/src/DatasetParsingPanel.tsx`, `frontend/src/DatasetVersionPanel.tsx`, profile/schema/preview section components, and shared formatting and label helpers in `frontend/src/datasetDisplay.ts`; `frontend/src/AppChrome.tsx` owns the sidebar, topbar, and dataset context layout, while `frontend/src/useDatasetWorkflow.ts` owns dataset upload/paste/parsing/schema/preview/profile workflow state and handlers. `App.tsx` still owns API bootstrap, route state, and analysis orchestration, so this split does not change dataset behavior.
`frontend/src/WorkspaceRouter.tsx` chooses between this data-preparation surface on root/dataset routes and the analysis page on `/analysis/{module_id}/{method_id}` routes against the same in-memory dataset state.

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
- Treats requests that do not change any persisted display name, measurement level, role, or unit as no-ops; no-op requests keep the same `schema_hash` and do not mark existing analysis runs stale.
- Marks existing analysis runs for the same dataset version stale only when the schema metadata actually changes.
- Does not change raw bytes, original column names, inferred data types, row count, or source SHA-256.
- Rejects duplicate display names and unknown column IDs without echoing raw row values.
- The current UI includes a guarded helper for headerless 34-column Bayesian optimization samples: `column_1` as ID, `column_2` through `column_25` as features, and `column_26` through `column_34` as responses. It only updates schema metadata drafts; it does not edit cell values.

`GET /api/v1/dataset-versions/{version_id}/rows`

- Returns a bounded row preview using `offset` and `limit`.
- Enforces `offset >= 0`, `1 <= limit <= 100`.
- Verifies the entire canonical rows artifact before returning a page, then streams canonical rows for the requested page.
- Detects row count, file size, SHA-256, row-index order, column count, and value-type mismatches before exposing preview values.
- For headerless datasets, row index `0` maps to the confirmed `data_start_row`.
- Current performance tradeoff: every preview request pays a full canonical JSONL verification cost before paging, which favors corruption detection over speed for large datasets. Future optimization candidates are a verified-artifact cache keyed by artifact hash, a row offset index, chunk-level hashes, and a verified-session cache.

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
- Browser state must not hold the full dataset; the current UI stores upload metadata, parsing options, version/schema/artifact metadata, one preview page, aggregate profile/preflight data, and transient pasted text only until successful registration.

## Analysis Use

`POST /api/v1/analysis-runs`

- `eda.descriptive`, `eda.graphical_summary`, `eda.normality`, `eda.equal_variances`, `hypothesis.one_sample_t`, `hypothesis.paired_t`, `hypothesis.one_sample_wilcoxon`, `hypothesis.two_sample_t`, `hypothesis.mann_whitney`, `hypothesis.kruskal_wallis`, `hypothesis.one_way_anova`, `hypothesis.equivalence_tost`, `categorical.one_proportion`, `categorical.two_proportion`, `categorical.chi_square_association`, `regression.pearson`, `regression.xy_correlation`, `regression.linear_model`, `quality.individuals_chart`, `quality.subgroup_chart`, `quality.run_chart`, `quality.capability`, `quality.gage_rr`, and `quality.gage_run_chart` are currently executable generic analysis-run methods.
- `doe.factorial_design` is registry-available but intentionally uses dedicated DOE design routes, not the generic analysis-run endpoint.
- `regression.predict` remains disabled in the generic method registry; predictions are available only through the dedicated regression-model prediction API after a stored app-created model manifest is validated.
- All executable dataset-backed methods require a confirmed `dataset_version_id` and stream the validated canonical rows artifact instead of reparsing the raw upload.
- `eda.descriptive`, `eda.graphical_summary`, and `eda.normality` use `options.column_ids` for selected numeric columns.
- `eda.equal_variances` uses a numeric response role plus a grouping role from `roles` or method-specific options.
- `hypothesis.one_sample_t` uses a numeric response role plus an explicit `null_mean`, defaults to a two-sided test, and reports CI plus Cohen dz.
- `hypothesis.paired_t` uses two numeric wide-format measurement columns, defines the pair difference as `after - before`, applies complete-pair exclusion, and reports CI plus Cohen dz.
- `hypothesis.one_sample_wilcoxon` uses a numeric response role plus an explicit `null_location`, records zero/tie handling, and reports signed-rank p-value plus rank-biserial effect size.
- `hypothesis.two_sample_t` uses a numeric response role plus an exactly two-level grouping role, defaults to Welch unequal-variance, and allows pooled Student only through explicit `variance_assumption="pooled"`.
- `hypothesis.mann_whitney` uses a numeric response role plus an exactly two-level grouping role, records exact/asymptotic p-value handling, and reports rank-biserial plus common-language probability.
- `hypothesis.kruskal_wallis` uses a numeric response role plus a 3-or-more-level grouping role, reports tie-corrected H/df/p, epsilon-squared, rank summaries, and Dunn/Holm post-hoc comparisons only when the overall test is significant.
- `hypothesis.one_way_anova` uses a numeric response role plus a 2-or-more-level grouping role, reports a standard ANOVA table, F/p-value, eta/omega squared, and Tukey-Kramer post-hoc comparisons only when the overall test is significant.
- `hypothesis.equivalence_tost` uses one numeric response column, an explicit reference mean, and user-defined raw-unit lower/upper equivalence bounds for one-sample mean TOST.
- `categorical.one_proportion` uses one binary response column plus an explicit `event_level`, computes an exact binomial p-value, and reports Wilson or Clopper-Pearson CI plus Cohen h.
- `categorical.two_proportion` uses one binary response column plus an exactly two-level grouping role and explicit `event_level`, computes a Fisher exact p-value, and reports Newcombe-Wilson CI for the proportion difference plus risk ratio and odds ratio where finite.
- `categorical.chi_square_association` uses two categorical columns, computes a Pearson chi-square independence test without continuity correction, reports expected-count diagnostics plus Cramer's V, and recommends Fisher exact for sparse 2x2 tables without automatically switching methods.
- `eda.descriptive` computes real descriptive statistics for selected numeric columns. The result records `n_total`, `n_used`, missing count, non-numeric exclusion count, mean, sample standard deviation, min, Q1, median, Q3, max, warning codes, and provenance.
- `eda.graphical_summary` streams the same canonical row source and computes real histogram, boxplot, Q-Q, and ECDF chart-data payloads for selected numeric columns, with inline frontend rendering for the current UI slice.
- `eda.normality` streams the same canonical row source and computes real SciPy-backed Shapiro-Wilk, Anderson-Darling, and Q-Q point payloads for selected numeric columns. It does not automatically choose a downstream parametric or nonparametric method.
- `eda.equal_variances` streams the same canonical row source and computes real SciPy-backed Brown-Forsythe and Levene(mean) results for grouped numeric responses. It does not automatically choose pooled/Welch or ANOVA variants.
- `hypothesis.one_sample_t` streams the same canonical row source and computes real one-sample mean comparison results with N/exclusions, sample summary, CI, p-value, Cohen dz, warnings, and provenance.
- `hypothesis.paired_t` streams the same canonical row source and computes real paired mean-difference results with N/exclusions, before/after means, difference summary, CI, p-value, Cohen dz, warnings, and provenance.
- `hypothesis.one_sample_wilcoxon` streams the same canonical row source and computes real signed-rank results with N/exclusions, zero/tie counts, signed rank sums, W statistic, p-value, rank-biserial effect size, warnings, and provenance.
- `hypothesis.two_sample_t` streams the same canonical row source and computes real two-group mean comparison results with N/exclusions, group summaries, CI, p-value, Cohen's d, Hedges g, warnings, and provenance.
- `hypothesis.mann_whitney` streams the same canonical row source and computes real two-group rank comparison results with N/exclusions, rank summaries, U statistic, p-value, rank-biserial effect size, common-language probability, tie warnings, and provenance.
- `hypothesis.kruskal_wallis` streams the same canonical row source and computes real 3-or-more-group rank comparison results with N/exclusions, rank summaries, H statistic, p-value, epsilon-squared effect size, optional Dunn/Holm post-hoc details, tie warnings, and provenance.
- `hypothesis.one_way_anova` streams the same canonical row source and computes real standard one-way ANOVA results with N/exclusions, group summaries, ANOVA table, F statistic, p-value, eta squared, omega squared, optional Tukey-Kramer post-hoc details, design warnings, and provenance.
- `hypothesis.equivalence_tost` streams the same canonical row source and computes real one-sample mean TOST results with N/exclusions, two one-sided tests, TOST p-value, `1 - 2 * alpha` CI, Cohen dz, warnings, and provenance.
- `categorical.one_proportion` streams the same canonical row source and computes real one-proportion exact binomial results with N/exclusions, event/non-event counts, sample proportion, CI, p-value, Cohen h, design warnings, and provenance.
- `categorical.two_proportion` streams the same canonical row source and computes real two-proportion Fisher exact results with N/exclusions, group event/non-event counts, sample proportions, proportion difference CI, p-value, risk/odds ratios, design warnings, and provenance.
- `categorical.chi_square_association` streams the same canonical row source and computes real Pearson chi-square association results with N/exclusions, observed/expected counts, row/column percentages, standardized residuals, p-value, Cramer's V, sparse-cell warnings, and provenance.
- Filter snapshots are frozen into an `analysis_row_snapshot` artifact linked from `analysis_artifacts`; the snapshot records the filter hash, canonical artifact hash, row identity, row ranges, and included row count without raw cell values.
- The current filter expression engine supports conjunctions of `is_missing`, `is_not_missing`, `eq`, `ne`, and numeric `gt`/`gte`/`lt`/`lte` conditions.
- The current Workbench UI exposes those supported AND filter conditions for dataset-backed method pages, and the current generic executable methods serialize them into executable analysis requests.
- Other analysis methods remain unavailable and must not return mock results.

## Next Step

The next Gate B slice should implement the next reference-backed method only after its statistical dependency and reference-test plan are clear.
Full dataset parsing must remain explicit and must not silently coerce values or infer study design from dtype alone.
