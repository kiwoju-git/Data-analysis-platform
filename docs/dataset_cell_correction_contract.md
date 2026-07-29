# Dataset Cell Correction Contract

Last updated: 2026-07-29

## Scope

`POST /api/v1/dataset-versions/{parent_version_id}/cell-corrections` creates one
new immutable dataset version from one confirmed canonical cell correction.
Correction schema version `1` accepts exactly one edit. The list shape is
reserved for a future separately reviewed batch-edit contract.

The parent version, raw upload, canonical artifact, profile artifact, analyses,
models, and reports are never updated. A successful correction creates a child
version with a new version ID, new column IDs, a new canonical artifact, and a
`dataset_version_lineage` row.

## Optimistic Verification

The request supplies the confirmed parent ID, expected parent schema hash, and
expected canonical SHA-256. The service revalidates all three, validates the
canonical path/size/checksum, checks the row and column ownership, and rejects a
no-op or type-incompatible value before insertion.

Supported operations are:

- `set_value`, where an empty string remains an empty string;
- `set_missing`, where the canonical value is `null`.

Formula-looking text is stored as text and is never evaluated. Errors and logs
do not contain the previous or proposed cell value, SQL, traceback, or an
absolute path.

## Lineage And Recovery

SQLite metadata schema `17` adds `dataset_version_lineage` with child version,
parent version, operation kind/schema, affected cell count, operation SHA-256,
and creation time. The correction manifest contains the parent/child canonical
hashes, row index, parent/child column IDs, and before/after context-envelope
hashes. It does not contain either raw cell value.

Canonical and manifest files are written atomically. A scoped pending marker is
created before materialization and removed after the DB transaction commits.
Startup recovery does not follow symlinks, junctions, or reparse points. It
keeps registered child files, and for an unregistered marker removes only the
three named app-owned correction files. Unrelated files and directories are
not swept.

Parent deletion preflight reports
`dataset_version_deletion_child_version_dependency` while a child exists.
Deleting a child does not delete or mutate its parent. Parent cascade does not
silently include a child dataset version.

## Frontend Behavior

The selected canonical preview cell has explicit read and edit states. Empty
string and missing are separate controls. Saving requires a modal confirmation
that names the parent version and makes the immutable child-version behavior
clear. A dirty edit is confirmed before cell, page, dataset, or route changes.

After success the child becomes the active analysis dataset, catalogs and the
project overview are invalidated, preview/profile/schema drafts are reloaded,
and transient analysis and Graph Builder results are cleared. The parent
remains available.
