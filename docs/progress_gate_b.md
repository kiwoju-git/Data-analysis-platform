# Gate B Progress

Last updated: 2026-06-26

## Summary

Gate B has completed the upload/version, paste-as-dataset intake, canonical JSONL artifact materialization, canonical row reader adoption for preview/profile/`eda.descriptive`, schema/preview, profile/preflight with duplicate-row and memory estimates, persisted profile summary artifacts, conservative date/time preflight, analysis catalog, storage/run foundation, selected-method six-module Workbench shell, shared Workbench component split, route-level selected-analysis restore, filter snapshot row freezing, a narrow filter expression engine and frontend filter controls for `eda.descriptive`, basic XLSX parsing confirmation, and the first real exploration-method slice in the working tree. The app can accept a local multipart dataset upload or pasted spreadsheet text, validate the file/text envelope, preserve raw bytes unchanged, store SHA-256 provenance in SQLite metadata, return parsing-option candidates, revalidate raw upload integrity before parsing confirmation, confirm delimited-text and basic XLSX parsing, create immutable dataset version `v1`, materialize canonical rows plus a manifest under the workspace, store dataset columns and artifact metadata, retrieve version metadata, update confirmed column metadata while marking dependent analysis runs stale, return paginated row preview from canonical rows, return aggregate profile/preflight counts and warnings from validated canonical rows, summarize date/time format candidates and timezone-awareness risks without raw samples, persist and reuse raw-value-free `profile_summary` artifacts tied to schema/canonical hashes, expose the 6-module analysis method catalog, show planned/disabled methods in a route-restorable Workbench shell with legacy hash fallback, initialize analysis run/artifact/job metadata tables with status/cancel API skeletons, execute `eda.descriptive` with real descriptive statistics from validated canonical rows, persist an `analysis_row_snapshot` artifact for the executed row selection, and re-read stored analysis result envelopes after checksum validation. Delimited-text parsing also handles leading preamble plus headerless tabular data through explicit `has_header=false` and `data_start_row` confirmation. The schema UI includes a guarded 34-column Bayesian sample role preset for headerless generated columns. It does not yet provide cell-level data edits, deeper dedicated analysis page decomposition, executable methods beyond `eda.descriptive`, generated chart artifacts, cross-method filter reuse, formula recalculation/display-format restoration for XLSX, or inferential statistical results.

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
| Minimal UI | Done for B0/profile slices | upload, parsing option confirmation with header/no-header controls, Context Bar, schema controls, Bayesian sample role preset, paginated preview, profile/preflight table, canonical/preflight summary |
| Analysis method registry | Done for B0/B1 first method | `GET /api/v1/analysis-methods`, 6 modules, 29 stable method IDs, only `eda.descriptive` available |
| Analysis run request guard | Done for B0/B1 first method | `POST /api/v1/analysis-runs` executes `eda.descriptive`; planned/disabled methods still reject without a result body |
| Analysis run status/cancel API | Done for B0 storage/run slice | `GET/DELETE /api/v1/analysis-runs/{analysis_id}` skeleton |
| Analysis result retrieval API | Done for `eda.descriptive` | `GET /api/v1/analysis-runs/{analysis_id}/result` validates stored result path and SHA-256 before returning the envelope |
| Filter snapshot row freezing | Done for `eda.descriptive` | creates `analysis_row_snapshot` artifacts with filter hash, canonical artifact hash, included row counts, and row ranges for supported filters |
| Frontend filter controls | Done for `eda.descriptive` | UI creates supported AND conditions, validates missing values/operators before API submission, and serializes to `filter_snapshot.conditions` |
| Basic XLSX parser | Done for current slice | stdlib ZIP/XML reader confirms first or named sheet, writes canonical JSONL rows, and keeps formula recalculation/display formatting out of scope |
| Job status/cancel API | Done for B0 storage/run slice | `GET/DELETE /api/v1/jobs/{job_id}` skeleton |
| Six-module navigation shell | Done for B0 third slice | frontend catalog fetch, module selector, planned/disabled method cards |
| Six-module Workbench shell | Done for current slice | selected method details, `/analysis/{module_id}/{method_id}` restore with legacy hash fallback, shared `AnalysisWorkbench` component, common data/role/option/preflight/run/result step rail, method-specific role/option/preflight/result guidance for all 29 methods, no execution controls for planned/disabled methods |
| Common analysis schemas | Started | request, filter snapshot, warning, provenance, result envelope, run status, and job status schemas exist |
| `eda.descriptive` | Done for first B1 slice | pure calculation module, dataset-version streaming reader, inline API execution, result JSON persistence, minimal UI result table |
| Analysis stale handling | Done for schema edits | schema PATCH marks existing runs for the same dataset version `stale=true` in the same SQLite transaction |
| Metadata migration | Done | schema version `5`, `datasets`, `dataset_versions`, `dataset_columns`, `dataset_artifacts`, `analysis_runs`, `analysis_artifacts`, `jobs`, upgrade tests from versions 1, 2, 3, and 4 |
| Canonical parsed artifact | Done for stdlib delimited-text slice | UTF-8 JSONL canonical rows plus JSON manifest are materialized with SHA-256 metadata; Parquet remains candidate after `pyarrow` review |
| Canonical row reader | Done for profile/B1 first method | profile and `eda.descriptive` read validated canonical rows; corrupt/missing artifact metadata returns explicit recovery errors without raw fallback |
| Full profile | Started | aggregate profile/preflight, duplicate-row analysis, memory estimate, persisted profile artifacts, and conservative date/time preflight exist; richer distribution/outlier profiling remains |
| Statistical analysis | Started | `eda.descriptive` only; no inferential tests, p-values, fake charts, or mock results |

## Latest Validation

Last validated on 2026-06-26:

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
- WSL `npm --prefix ./frontend run test -- --run` failed because the Windows-installed native `node_modules` lacks the Linux Rolldown binding; PowerShell/Windows Node is the supported validation environment for this repository.
- `pyarrow` local availability check: `pyarrow_available=False`; no dependency was added.

## Risks And Notes

- Statistical: `eda.descriptive` now produces descriptive statistics only. It reports N, missing values, non-numeric exclusions, mean, sample SD, min, quartiles, median, max, warnings, and provenance. It does not produce inferential statistics, p-values, effect sizes, or confidence intervals.
- Privacy/security: committed tests use synthetic bytes only. The local `input_example/` file was used only for manual HTTP smoke and was not copied into fixtures or committed.
- Compatibility: upload, parsing-confirmation, schema update, and rows preview logic use Python 3.10-compatible stdlib streaming, `pathlib`, SQLite, and FastAPI `UploadFile`.
- Migration/storage: schema version advanced to `5`; upgrades from schema versions `1`, `2`, `3`, and `4` are tested.
- Performance: upload reads in 1 MB chunks and enforces `DATALAB_MAX_UPLOAD_BYTES`; confirm-parsing streams delimited text or XLSX worksheet XML for header, row count, column type candidates, and canonical JSONL materialization; rows preview streams only until the requested page is filled; profile streams the dataset once, caps per-column unique tracking at 1,000 values, caps duplicate-row signature tracking at 100,000 signatures, uses conservative stdlib date/time candidate parsing, and returns a memory estimate.
- Dependency: `python-multipart==0.0.32` was added for FastAPI multipart uploads and recorded in `docs/dependency_review.md`.
- XLSX: basic stdlib parsing confirmation exists for worksheet cached values. Formula recalculation, merged-cell expansion, hidden row/column handling, and Excel display-format/date serial restoration remain out of scope.

## Next Gate B Slice

The next slice should stay narrow and avoid mock statistics:

1. Continue the Workbench split into deeper dedicated route-level components/pages or generalize filter controls for cross-method reuse.
2. Keep every method except `eda.descriptive` non-executable until it has real calculation code and tests.
3. Keep Bayesian optimization, DOE, regression, quality control, optimizer work, and general ML out of the next slice unless the user explicitly changes gates.
