# DataLab Studio Backend

FastAPI backend package for the local-first DataLab Studio application.

The public API is versioned under `/api/v1`.

Current Gate B0 surface:

- `GET /api/v1/health`
- `POST /api/v1/datasets`
- `POST /api/v1/datasets/{dataset_id}/confirm-parsing`
- `GET /api/v1/datasets/{dataset_id}/versions`
- `GET /api/v1/dataset-versions/{version_id}`
- `GET /api/v1/dataset-versions/{version_id}/schema`
- `PATCH /api/v1/dataset-versions/{version_id}/schema`
- `GET /api/v1/dataset-versions/{version_id}/rows`
- `GET /api/v1/dataset-versions/{version_id}/profile`
- `GET /api/v1/analysis-methods`
- `POST /api/v1/analysis-runs`
- `GET /api/v1/analysis-runs/{analysis_id}`
- `DELETE /api/v1/analysis-runs/{analysis_id}`
- `GET /api/v1/jobs/{job_id}`
- `DELETE /api/v1/jobs/{job_id}`

The Gate B0 slice creates immutable dataset-version metadata for delimited text files, materializes canonical JSONL rows plus a manifest, allows column metadata confirmation, and exposes bounded row preview plus an aggregate profile/preflight scan.
Delimited-text parsing confirmation supports both header rows and headerless tabular data after a leading preamble through explicit `has_header` and `data_start_row` options.
It also exposes the 6-module analysis method catalog.
`eda.descriptive` is the first executable inline method and computes real descriptive statistics from validated canonical rows for an immutable dataset version.
Other methods remain `planned` or `disabled` and return structured unavailable-method errors.
Schema version `5` includes dataset artifact metadata plus analysis run, artifact, and job metadata tables with status/cancel API skeletons.
The profile endpoint reads validated canonical rows and returns aggregate counts, canonical artifact metadata, duplicate-row count, memory estimate, and warnings only, not raw value samples.
It does not create mock results.
