# Storage and Migration Notes

Gate A introduces a minimal SQLite metadata store skeleton.

## Metadata Database

- Default workspace root: `%LOCALAPPDATA%\DataLabStudio\` on Windows.
- Development override: `DATALAB_WORKSPACE_ROOT`.
- Metadata path under the workspace root: `db\metadata.sqlite3`.
- Runtime workspace and database files must not be committed to Git.

## Migration Skeleton

- Current schema version: `1`.
- Migration history is recorded in `schema_migrations`.
- `PRAGMA user_version` is set to the current schema version after migrations run.
- Startup initializes the metadata store during FastAPI lifespan startup.

## Recovery Direction

Future schema changes must add forward migrations with tests for upgrade from the previous schema. Before destructive or non-idempotent migrations are introduced, add a backup step and document the restore path.

## Atomic File Writes

- Use `backend.app.storage.atomic.atomic_write_bytes` or `atomic_write_text` for small metadata-adjacent artifacts such as manifests, analysis result JSON, and export manifests.
- The helper writes a temporary file in the target directory, flushes and fsyncs file content, then replaces the target with `os.replace`.
- The target directory is created before writing.
- If the writer fails before replacement, the previous target file is preserved and the temporary file is removed.
- Do not use this helper to stream large uploaded datasets directly; large file ingestion needs chunked validation, hashing, size checks, and cleanup logic in Gate B.
