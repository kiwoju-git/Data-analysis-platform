# Workspace Retention And Deletion Contract

Last updated: 2026-07-22

## Scope And Current Slice

This contract separates lifecycle close from physical deletion. Six bounded
slices are implemented:

1. deletion of one closed Bayesian Optimization study's metadata ownership
   graph; and
2. deletion of one app-created analysis-result or regression-prediction export
   file plus its single `analysis_artifacts` metadata row; and
3. deletion of one succeeded analysis run together with its verified owned
   result, row snapshot, prediction-row artifact, and export files;
4. deletion of one app-created regression-model manifest plus its model and
   `analysis_artifacts` metadata rows; and
5. deletion of one immutable attribute-control limit-set asset plus its
   metadata row; and
6. deletion of one dependency-free, checksum-validated dataset version,
   including its owned artifacts and, only for the last version, its shared raw
   upload and dataset-root record.

Individual export deletion preserves the stored analysis result and every
other artifact. Analysis-run deletion is intentionally narrower than cascade
deletion: a run that owns a regression model, is the source of an attribute
control limit set, or is referenced by a job is blocked. DOE-design,
response-revision, bulk, and automatic deletion remain unavailable.

Deleting a regression-model asset never deletes or rewrites its source linear-
model analysis result. The source fit remains restorable, but the UI rechecks
the checksum-validated model GET on every displayed current or restored fit.
A missing model is shown as `unavailable_or_deleted`; manifest/path/checksum
failures are shown separately as `integrity_error`. Both states disable new
prediction preflight, execution, and prediction CSV actions while preserving
the fit table and provenance.

The current Bayesian graph owns no filesystem artifact. Its deletion preflight
therefore reports `file_count=0` and `file_bytes=0`; this is a verified property
of this graph, not a claim that the whole application is metadata-only.

## Safety Invariants

1. An `active` Bayesian study cannot be deleted. It must first be explicitly
   closed as `completed` or `abandoned`.
2. A study referenced by a successor's `predecessor_study_id` cannot be
   deleted. The application does not cascade into successors or silently sever
   lineage.
3. Preflight reloads and checksum-validates the study, current version, trials,
   complete history, history head, recommendations, and lifecycle event.
4. Preflight returns typed record counts and a canonical deletion-manifest
   SHA-256. It exposes counts, IDs needed for confirmation, and blocker codes,
   never objective values, factor coordinates, filenames, SQL, or paths.
5. Delete requires the exact study ID and the exact latest manifest SHA. The
   storage layer reacquires `BEGIN IMMEDIATE`, recomputes the graph, and rejects
   any change since preflight.
6. Lifecycle events, recommendations, and history heads are removed before the
   owning study. SQLite foreign keys then cascade through versions, trials, and
   history revisions in the same transaction. Row-count disagreement rolls the
   transaction back.
7. Deletion has no undo or reopen semantics. The UI uses an impact step followed
   by a separate irreversible confirmation.
8. Analysis-run preflight accepts only a succeeded run with a stored result. It
   validates the result envelope, config-to-row-snapshot relationship, all
   artifact kinds, exact relative paths, media types, file SHA-256/size, and
   prediction cross-artifact consistency when applicable.
9. Regression-model, limit-set, and job inbound references block analysis-run
   deletion. The operation never relies on SQLite cascade to sever those audit
   relationships.
10. Analysis-run delete moves every owned file to a short same-directory
    quarantine name before one `BEGIN IMMEDIATE` transaction rechecks and
    removes the run plus artifact metadata. A move or DB conflict restores all
    previously moved files in reverse order.
11. Cleanup failure leaves checksum-bound quarantine files for startup
    recovery. Metadata-owned files are restored only to their exact expected
    path; committed orphans are removed; tampered or unknown files stay
    pending. Short names avoid UUID duplication and Windows path-limit issues.
12. Regression-model deletion validates the model row, source analysis, source
    result model reference, manifest payload, artifact row, exact path,
    SHA-256, and size. Any dependent prediction blocks deletion.
13. Limit-set deletion validates the immutable asset, metadata row, source
    result/config hashes, exact path, SHA-256, and size. Any referencing Phase
    II analysis blocks deletion. A stale source may still shed a verified asset;
    normal limit-set use keeps its stricter freshness checks.
14. Both asset deletes use exact-ID and exact-manifest confirmation,
    same-directory quarantine, `BEGIN IMMEDIATE` revalidation, compensating
    restore, and startup recovery without cascading into source results.
15. Dataset-version deletion uses the full inbound-reference and file-ownership
    graph in `docs/dataset_retention_contract.md`. It preserves a shared raw
    upload while sibling versions remain, and never cascades into a dependent
    analysis, model, prediction, export, limit set, Phase II result, or job.

## Implemented API

- `GET /api/v1/bayesian-studies/{study_id}/deletion-preflight`
- `DELETE /api/v1/bayesian-studies/{study_id}`
- `GET /api/v1/analysis-runs/{analysis_id}/exports/{export_id}/deletion-preflight`
- `DELETE /api/v1/analysis-runs/{analysis_id}/exports/{export_id}`
- `GET /api/v1/analysis-runs/{analysis_id}/deletion-preflight`
- `DELETE /api/v1/analysis-runs/{analysis_id}/deletion`
- `GET /api/v1/regression-models/{model_id}/deletion-preflight`
- `DELETE /api/v1/regression-models/{model_id}`
- `GET /api/v1/quality/attribute-control-limit-sets/{limit_set_id}/deletion-preflight`
- `DELETE /api/v1/quality/attribute-control-limit-sets/{limit_set_id}`
- `GET /api/v1/dataset-versions/{version_id}/deletion-preflight`
- `DELETE /api/v1/dataset-versions/{version_id}/deletion`

Stable blocker/error codes are:

- `bayesian_study_deletion_active`
- `bayesian_study_deletion_referenced`
- `bayesian_study_deletion_confirmation_mismatch`
- `bayesian_study_deletion_conflict`

Individual export deletion uses these stable error codes:

- `analysis_export_not_found`
- `analysis_export_metadata_invalid`
- `analysis_export_path_invalid`
- `analysis_export_file_missing`
- `analysis_export_checksum_mismatch`
- `analysis_export_deletion_confirmation_mismatch`
- `analysis_export_quarantine_failed`
- `analysis_export_deletion_conflict`
- `analysis_export_restore_failed`

Analysis-run deletion uses stable blockers and errors including:

- `analysis_run_deletion_status_unsupported`
- `analysis_run_deletion_result_unavailable`
- `analysis_run_deletion_regression_model_dependency`
- `analysis_run_deletion_regression_prediction_dependency`
- `analysis_run_deletion_limit_set_dependency`
- `analysis_run_deletion_job_dependency`
- `analysis_run_deletion_blocked`
- `analysis_run_deletion_confirmation_mismatch`
- `analysis_run_quarantine_failed`
- `analysis_run_deletion_conflict`
- `analysis_run_restore_failed`
- `analysis_run_artifact_path_invalid`
- `analysis_run_file_missing`
- `analysis_run_file_unavailable`
- `analysis_run_file_checksum_mismatch`
- `analysis_run_row_snapshot_mismatch`

Regression-model deletion uses stable blockers and errors including:

- `regression_model_deletion_prediction_dependency`
- `regression_model_deletion_blocked`
- `regression_model_deletion_confirmation_mismatch`
- `regression_model_quarantine_failed`
- `regression_model_deletion_conflict`
- `regression_model_artifact_mismatch`
- `regression_model_source_analysis_invalid`
- `regression_model_source_result_mismatch`

Limit-set deletion uses stable blockers and errors including:

- `attribute_control_limit_set_deletion_phase_2_dependency`
- `attribute_control_limit_set_deletion_blocked`
- `attribute_control_limit_set_deletion_confirmation_mismatch`
- `attribute_control_limit_set_quarantine_failed`
- `attribute_control_limit_set_deletion_conflict`
- `attribute_control_limit_set_artifact_mismatch`

Dataset-version deletion uses the stable blockers and operational errors
defined in `docs/dataset_retention_contract.md`, including dependency-specific
analysis/model/prediction/limit-set/job codes, confirmation conflict, path and
artifact mismatch, quarantine, restore, and missing-file codes.

Preflight schema 1 and deletion-response schema 1 report study-version, trial,
history-revision, history-head, recommendation, lifecycle-event, and total
metadata counts. They also report successor count and the canonical manifest.

Export preflight schema 1 reports exactly one metadata row, one file, its byte
size, artifact kind/media type/SHA, and a canonical deletion-manifest SHA. The
manifest also binds the parent analysis method/version/update/stale/result SHA
and exact internal relative path without returning those internal values to the
client. Delete requires exact analysis ID, export ID, and manifest SHA.

The service accepts only the four app-created export kinds and their exact
kind-specific relative path and media type. It verifies file type, non-symlink
status, size, and SHA before preflight and again after a same-directory
quarantine rename. A `BEGIN IMMEDIATE` metadata transaction compares the full
artifact row and parent analysis update/stale/result state before deleting one
row. If that transaction fails, the file is restored. If final unlink fails,
the response is successful with `quarantined_pending_cleanup`; next startup
deletes a committed orphan quarantine or restores a metadata-owned quarantine
only when its SHA still matches. Tampered or unrecognized quarantine files stay
pending for explicit recovery and are never restored as valid exports.

Analysis-run preflight schema 1 reports run/artifact/result/export/file and
dependency counts plus one canonical manifest SHA without returning paths.
Delete schema 1 requires the exact analysis ID and manifest SHA. Successful
delete removes only the owning `analysis_runs` row and its
`analysis_artifacts` rows; dataset versions and unrelated runs remain. A
prediction run is eligible only after its result/config/rows/model relations
validate. A source linear-model run remains blocked by its model record.

Regression-model and limit-set preflight/delete operational schemas are 1.
They report one owned file, byte and metadata counts, dependent prediction or
Phase II counts, blockers, and a canonical manifest SHA without returning an
internal path, filename, predictor value, or raw observation.

## Filesystem Ownership Contract For Later Slices

Dataset-version deletion now implements the SQLite-row and relative-workspace
file controls below. DOE root deletion remains a later slice and must reuse
these invariants rather than infer ownership from a directory name:

1. Resolve every path from trusted metadata under the configured workspace and
   reject absolute, escaping, missing, duplicate, or unexpected paths.
2. Revalidate file SHA-256 and byte size before preflight and immediately before
   mutation. Never infer ownership from a directory name alone.
3. Compute inbound references from analyses, models, predictions, exports,
   limit sets, DOE analyses/revisions, optimizers, and Bayesian lineage.
4. Default to blocking referenced-root deletion. Cascade may be added only as a
   separately reviewed, complete graph operation with an explicit affected-item
   list.
5. On Windows, close handles before rename/delete and treat sharing violations
   as typed recoverable failures. Do not remove SQLite metadata while files
   remain ambiguously owned.
6. Prefer a workspace-local quarantine rename followed by a DB transaction and
   final removal. Define crash recovery for each boundary: before rename, after
   quarantine, after DB commit, and during final removal.
7. Keep user-visible retention defaults and bulk cleanup separate from one-item
   deletion. No age-based or size-based automatic deletion is currently active.

## Future Acceptance Criteria

- Dataset-root bulk deletion remains unavailable; the current API removes only
  one verified version and removes its root/raw upload only when it is the last
  version.
- DOE root deletion must preserve model, prediction, limit-set,
  response-revision, analysis, and optimizer references without silent cascade.
- DOE design deletion preserves immutable response-revision and analysis links;
  old revisions are never overwritten as a shortcut.
- Tampered metadata/path/hash, locked files, stale preflight, concurrent writes,
  partial quarantine, and startup recovery have dedicated tests.
- API/UI errors contain no raw rows, objective values, filenames, relative or
  absolute paths, traceback, or SQL.
- E2E covers individual export deletion plus analysis-run impact review,
  confirmed removal, history reduction, and clearing deleted restore/comparison
  state. Unit/API tests cover exact confirmation, stale manifests, path/hash
  tamper, dependency blockers, partial rename, DB rollback restoration,
  pending cleanup, and next-start recovery. Later root-graph slices must add
  their own impact, cancellation, confirmed removal, and reload coverage.

## Version Decision

The Bayesian metadata-deletion slice does not change GP/EI calculations,
study/history/recommendation/lifecycle artifact meaning, or any existing
checksum payload. `doe.bayesian_optimization` remains `0.2.2`; study, history,
recommendation config/result/model, and lifecycle-event schemas remain 1.
That slice required no migration because the ownership relations and cascade
keys already existed at schema 14. The current database is schema 15 solely for
asset user metadata. Deletion preflight and response schemas start at 1.

Individual export deletion likewise changes no statistical calculation,
persisted result/export interpretation, or SQLite relation. Method versions,
existing export schemas, and the then-current database relations remained unchanged. Its operational
preflight/delete schemas start at 1; startup quarantine recovery is an internal
crash-consistency mechanism, not a stored statistical artifact schema.

Analysis-run deletion also changes no calculation, result interpretation,
artifact checksum payload, or database relation. Method versions, result/config
schemas, and the then-current database relations remained unchanged. Its operational preflight and
delete schemas start at 1. Quarantine filenames are recovery state, not a
public or statistical artifact schema.

Regression-model and limit-set deletion likewise do not change calculations,
immutable manifest/asset meaning, source results, or SQLite relations. Method
versions, result/config schemas, model manifest schema 2, limit-set asset schema
1, and the then-current database relations remained unchanged. Their operational preflight and
deletion-response schemas start at 1.

The current dataset-version/user-metadata slice advances SQLite to schema 15
for `dataset_version_user_metadata` and `regression_model_user_metadata` only.
Dataset deletion uses existing ownership keys plus operational preflight/delete
schema 1. No statistical method, result/config schema, dataset schema hash, or
model manifest schema is changed by this migration.
