# Managed Report Storage Contract

## Ownership and Compatibility

Metadata schema 21 adds `managed_report_artifacts` plus three composite owner
indexes and expands the existing DOE asset table's HTML-report schema constraint.
The DOE table is transactionally rebuilt with explicit unchanged columns and bytes:
prediction schema remains 1; HTML schema 1 and the new managed HTML schema 2 are
accepted. Existing row values, BLOBs, and checksums are preserved. The migration
does not rewrite existing results, design revisions, model files, or
reports. Generic analysis exports remain `analysis_artifacts`; existing DOE analysis
reports remain `experiment_design_analysis_assets`. This new table covers:

- `lhs_design_revision`: an exact LHS design version, with an explicitly selected
  list of immutable response revision IDs/hashes (empty means design-only).
- `bayesian_history_revision`: an exact study version and history revision,
  optionally one exact recommendation or batch from that same history.

BO initial empty history is valid. A report never implicitly selects the current
head, newest recommendation, or newest response. Composite foreign keys enforce
study/history/attachment identity, not merely independent existence of each ID.

## Immutable Files and Hashes

Each report has a server-created UUID and one app-owned relative path:
`workspaces/reports/<UUID>/report.html`. No caller-supplied file path is accepted.
The file is bounded to 16 MiB; each design version or study version may own at
most 100 reports. BO's limit spans its history revisions, not 100 per revision.
Pagination is bounded to 100 records per request.

Metadata stores canonical typed source-reference JSON and its SHA-256, the exact
source payload SHA (LHS design or BO history), locale, renderer ID/version, report
level, section manifest, HTML SHA/size/media type, and creation time. Reference and
section JSON are each bounded to 64 KiB. Canonical JSON uses UTF-8, sorted keys,
compact separators, and no non-finite numbers. Optional attachment JSON-byte and
payload hashes remain distinct. A batch payload hash resides in its stored JSON;
a recommendation also has a dedicated payload-hash column.

The report service validates stored source semantics before rendering. Storage
rechecks exact source/owner/hash identities under `BEGIN IMMEDIATE`, including
selected response revisions and recommendation/batch history ownership. It does
not invoke a design generator, quality metric, fit, prediction, or raw-row reader.
Downloads verify report metadata and exact file bytes. Path checks reject links,
junctions, traversal, and hard-linked files. Windows extended paths are internal
I/O details, never persisted in metadata or exposed to clients.

## Creation, Deletion, and Recovery

Creation allocates an exclusive UUID directory, writes/fsyncs a creation marker
and the new HTML, and inserts metadata in the same owner-checked transaction.
Failure rolls back metadata and removes only that operation's newly created files.
The creation marker remains recoverable if the process exits before final cleanup.

Individual deletion requires both expected artifact and source-reference hashes.
LHS design/BO study deletion gathers all managed reports from every owned version.
The existing preflight/CAS includes the complete sorted report metadata manifest,
not only report counts. A replacement with the same count therefore conflicts.
BO preflight now records `report_count`, file count, and total file bytes. Existing
DOE `report_count` includes LHS reports. No report is deleted without appearing in
the confirmed current deletion scope.

After the SQL writer lock is acquired, exact verified HTML files are renamed to
operation-owned `.delete-<SHA>-<size>.q` quarantine paths. SQL/rename failure restores
already moved files and rolls back metadata. After commit, only those quarantined
files are removed. A cleanup failure is retained for recovery, not represented as
a rollback of committed metadata.

Startup recovery runs under the workspace lease through the existing workspace
asset recovery aggregator. It recognizes only exact creation/deletion marker names,
valid UUID directories, and matching file hashes/sizes. If the record still exists,
a deletion quarantine is restored; if deletion committed, the quarantine is removed.
A creation marker with a committed record is cleaned without rewriting HTML; an
uncommitted matching HTML is removed. Unknown files and corrupt markers are not
deleted. Conflicts remain pending rather than overwriting another file.

## Backup Boundary

`MANAGED_REPORT_COLUMNS` and `validate_managed_report_record(connection, record)`
provide a read-only inventory boundary. The latter supports tuple and `sqlite.Row`
connections, checks typed canonical metadata and exact owner identities, and never
writes files or metadata. Backup verification separately streams/checks the exact
registered report path, size, and SHA. Schema20 archives remain schema20 until
normal application startup performs migration 21 after verified restore;
the archive is never rewritten to pretend it was originally schema21.

## Validation Scope

Focused storage tests exercise actual SQLite transactions and synthetic files:
20-to-21 migration without legacy-row/file mutation; LHS/BO round trips; history-only
BO; exact attachment/hash binding; composite foreign keys; count-preserving report
replacement; two independent create/delete connections; SQL partial failure;
quarantine restoration/committed cleanup; bounded/canonical metadata; corruption,
hard links, and parent symlinks. Real API and whole-project gates are separate from
these focused storage tests. A Windows symlink privilege failure is explicitly
skipped, not counted as successful symlink validation.

## Analysis-Owned Completed Artifacts

GP/PLS completed prediction snapshots and managed HTML reports use the existing
analysis owner and `analysis_artifacts` table. Their exact server-UUID paths are
`workspaces/analyses/<analysis-id>/exports/<artifact-id>.completed-prediction.json`
and `<artifact-id>.managed-report.html`. Reads reject noncanonical paths, links,
oversized files, and hash mismatches. Creation is exclusive, never an overwrite.

Under the SQL writer lock, source/model/dependency CAS checks precede a durable
`.create-<artifact-id>.source-bound.json` journal and the complete artifact file.
Only after file flush/fsync does the metadata row commit. Startup recovery checks
the exact journal ID, record, path, hash, and size; it preserves committed files
and removes verified unregistered complete files. Partial or corrupt bytes remain
pending for inspection. Windows uses file fsync; POSIX also fsyncs directories.
The existing recovery `restored_file_count` includes committed files preserved
while their creation journal is cleaned; no file movement is implied for those.

Deleting the saved regression model remains an explicit prerequisite to deleting
its source analysis. GP's NPZ must match its manifest, path, and hash before a
preflight can report that model dependency. Once the model is explicitly removed,
source-analysis deletion includes completed snapshots and managed reports in the
same full artifact manifest and quarantine lifecycle.

A completed snapshot can itself be deleted through its artifact deletion route.
An already completed HTML report remains a historical analysis-owned artifact:
its descriptor and download validate the report's own bytes/embedded identity,
not current availability of the prediction snapshot. Capability/new export for
the missing snapshot returns a conflict; no prediction is recomputed and neither
the source analysis nor an existing HTML report is rewritten.

`test_source_bound_artifacts.py` includes real child-process termination before
and after SQL commit, ordinary SQL failure, unregistered-path collision, corrupt
journals, strict source CAS, hard-link rejection, and real GP/PLS API model deletion
followed by full source-owner deletion. Execution results must be reported by the
platform actually used, not inferred from this inventory.
