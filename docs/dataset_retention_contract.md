# Dataset Version Retention Contract

Last updated: 2026-07-24

## Scope

This operation deletes one immutable dataset version after a full dependency
and file-integrity preflight. The default operation remains dependency-blocked.
An explicit cascade operation can additionally remove the exact planned
analysis/model/prediction/export/job/control-limit/Phase II closure.

APIs:

- `GET /api/v1/dataset-versions/{version_id}/deletion-preflight`
- `GET /api/v1/dataset-versions/{version_id}/deletion-dependencies`
- `DELETE /api/v1/dataset-versions/{version_id}/deletion`

Operational preflight and delete-response schemas are 3. Delete requires the
exact version ID, an explicit operation ID, and that operation's current
manifest SHA. The v2 mode names remain safe aliases for dependency-free
clients.

## Dependency Graph

Preflight separately counts direct analysis runs, regression models,
predictions using the version as source or target, exports belonging to those
runs, jobs, attribute-control limit sets, and Phase II target analyses. Any
inbound reference blocks the default deletion. Preflight returns a bounded
descriptor preview; the paged dependency route returns safe IDs, method/status,
relationship, timestamps, cross-dataset references, and blocker codes without
raw values or paths.

The explicit cascade closure includes direct analyses, models fitted from the
target version, every prediction using those models or the version as
source/target, owned exports and completed jobs, limit sets derived from the
version, and Phase II analyses using those sets. It is recalculated to a fixed
point. Other dataset versions, unrelated assets, and other dataset records are
never included. Active jobs and unsupported inbound references block cascade.

Stable blocker codes include:

- `dataset_version_deletion_analysis_dependency`
- `dataset_version_deletion_regression_model_dependency`
- `dataset_version_deletion_prediction_dependency`
- `dataset_version_deletion_limit_set_dependency`
- `dataset_version_deletion_job_dependency`
- `dataset_version_deletion_blocked`

## File Ownership

Every `dataset_artifacts` row for the target version is required to resolve
under `workspaces/datasets/{dataset_id}/versions/{version_id}`. Canonical rows
and canonical manifest are mandatory; a profile artifact is included when it
exists. Stored relative paths normalize Windows `\` to `/` and compare the
recognized workspace layout case-insensitively. Drive-letter, UNC, absolute,
escaping, empty-component, and unrecognized layouts remain invalid. Reparse
checks begin at the workspace root's children, so a workspace root that is
itself on a Windows junction does not invalidate every asset. Preflight rejects
symlinks, duplicate paths, missing/non-file entries, size mismatch, and SHA-256
mismatch.

If another version belongs to the same dataset root, deletion scope is
`version_only`: only the target version, columns, user metadata, artifact rows,
and verified version-owned files are removed. The shared raw upload and dataset
root remain. If this is the last version, scope is `dataset_root` and the exact
recorded `raw/source.<type>` file is also verified and removed with the root
metadata. API responses expose counts and hashes, not internal paths or raw
filenames.

## Integrity Modes

Dependency counting is independent of file verification. Preflight reports
`integrity_state`, issue codes, and four operation choices:

- `verified_files_and_metadata` retains checksum/path/size validation,
  quarantine, transaction, restore, and recovery behavior.
- `metadata_only_preserve_unverified_files` is offered only when every inbound
  dependency count is zero and physical file ownership cannot be verified.

Metadata-only cleanup never opens, moves, hashes, or unlinks an unverified
file. It removes the exact version/column/artifact/user-metadata snapshot in a
`BEGIN IMMEDIATE` transaction and may remove the last dataset-root metadata
row, while leaving raw and artifact bytes on disk. The response reports the
preserved-file count and warns that disk space might not be reclaimed.
Absolute/escaping or symlink metadata therefore cannot delete an external file.

- `delete_dataset_and_dependents_verified` is ready only when the full closure
  and every owned file validate.
- `delete_dataset_and_dependents_preserve_unverified` removes the exact metadata
  closure but quarantines and deletes only verified files. Unverified,
  escaping, symlink/reparse, missing, mismatched, or duplicate references are
  never opened or moved and may remain on disk.

## Transaction And Recovery

1. Preflight builds a canonical manifest from immutable records, operational
   metadata, dependency counts, and file identities.
2. Delete re-runs preflight and requires its exact manifest SHA.
3. Owned files are moved to short same-directory quarantine names. Short owner
   tokens avoid Windows path-length failures; token collisions remain pending
   instead of restoring an ambiguous file.
4. `BEGIN IMMEDIATE` reloads the full version and dependency closure. A changed
   ID set, row, metadata update, sibling count, artifact, or dependency rolls
   back.
5. Cascade removes jobs, limit sets, models, analysis runs and their owned
   artifact rows before the version. Exact row counts are checked. The dataset
   root row is deleted only for the last version.
6. A DB failure restores moved files in reverse order. Restore failure is a
   typed error.
7. A final unlink failure returns `quarantined_pending_cleanup`. Startup
   recovery restores only checksum-matching metadata-owned files and removes
   committed orphans. A tampered or ambiguous quarantine remains pending.

Stable integrity/transition errors include
`dataset_version_deletion_confirmation_mismatch`,
`dataset_version_deletion_conflict`, `dataset_version_quarantine_failed`,
`dataset_version_restore_failed`, `dataset_version_artifact_mismatch`,
`dataset_version_file_missing`, and `dataset_version_path_invalid`.

## UI Contract

The management page shows dependency counts before the irreversible checkbox.
Referenced versions show their dependency items and an explicit cascade choice.
The active version must be changed first. Successful deletion refreshes manager,
selector, project summary, history/report/model and restored-result state. The
cascade confirmation requires both a checkbox and the user label or short
version ID; it never shows a workspace path.

For an unverified, dependency-free version the UI presents a separate checkbox
and `파일을 보존하고 목록에서 제거` action. It is never offered for a
referenced or active version.

The UI distinguishes a generic route 404 (runtime contract mismatch) from
`dataset_version_not_found`, dependency blockers, optimistic metadata conflict,
and artifact-integrity failures. The runtime gate must pass before preflight or
DELETE can be initiated from the management page.

## Non-goals

Bulk deletion, age-based cleanup, automatic retention, DOE root deletion,
multi-project ownership, and in-place dataset mutation remain out of scope.
## Archive Versus Delete

Archive is reversible catalog metadata. It never validates, moves, or deletes
workspace files and never removes analyses, exports, models, predictions,
limit sets, jobs, or other dependent assets. Ordinary catalogs default to
visible versions; `/manage` can list archived versions and restore them.

Permanent deletion remains a separate exact-manifest operation. Verified
deletion removes only checksum-validated owned files. Preserve-unverified
cleanup may remove metadata after explicit confirmation while leaving
unverified files untouched, so it may not reclaim disk space.
