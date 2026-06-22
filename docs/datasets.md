# Dataset Upload Notes

Gate B starts with a minimal upload-to-confirmation slice.

## Current API

`POST /api/v1/datasets`

- Accepts multipart file uploads.
- Supports `.csv`, `.tsv`, `.xlsx`, and `.txt` as a nonstandard delimited-text candidate.
- Preserves the raw upload unchanged under the configured local workspace.
- Records SHA-256, byte size, sanitized original filename, detected format, media type, and stored relative path in SQLite metadata.
- Returns parsing suggestions only; it does not parse full data, infer schema, preview rows, or run analysis yet.

## Safety Rules

- Default upload limit: 100 MB via `DATALAB_MAX_UPLOAD_BYTES`.
- Filenames are sanitized and never used as storage paths.
- Stored raw upload paths are UUID-based relative paths.
- Unsupported binary files, path traversal filenames, extension/type mismatches, empty files, oversized files, invalid XLSX containers, and excessive XLSX decompression ratios are rejected.
- Client errors must not include raw cell values, absolute paths, SQL, or tracebacks.

## Next Step

The next Gate B slice should add schema-confirmation records and a paginated preview API. Full dataset parsing should remain explicit and should not silently coerce values or infer study design from dtype alone.
