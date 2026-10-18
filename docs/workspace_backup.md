# Offline Workspace Backup And Restore

## Scope And Preconditions

This is an explicit offline operation for one cooperating local owner. Stop the
application normally before backup or restore. The CLI and application hold the
same OS workspace lease; they do not kill another process or remove its lock.
There is no web endpoint accepting arbitrary filesystem paths and no network
transfer. The backup is not encrypted or signed: protect it like the source data.
SHA-256 detects corruption, not a malicious party who can replace the archive.

Backup format 1 supports the exact metadata schema 20 inventory. It does not
migrate the source or restored database, execute an analysis, fit a model, or
rebuild an export. Older/newer or structurally different databases are refused;
use the compatible application/tool version rather than modifying metadata to
force acceptance. No metadata migration is added by this feature.

The archive contains all registered workspace assets and the complete SQLite
logical state, including stale analyses, archived datasets, unconfirmed uploads,
DOE/LHS runs and revisions, BO history, and managed Factorial HTML/prediction
BLOBs. It is **not** an arbitrary recursive backup of everything placed beside
the app. Unregistered files under `db`, `workspaces`, or `artifacts` cause refusal
instead of a misleading complete backup. Unrelated root files, logs, credentials,
and browser downloads are not read or included. A browser-downloaded PLS/GP
prediction snapshot outside the workspace must be retained separately.

## Commands

Source checkout, PowerShell (use explicit paths outside the repository):

```powershell
.\.venv\Scripts\python.exe .\scripts\backup_workspace.py `
  --workspace "$env:LOCALAPPDATA\DataLabStudio" `
  --output "$env:USERPROFILE\Documents\datalab-backup.zip"

.\.venv\Scripts\python.exe -m app.storage.workspace_backup verify `
  --archive "$env:USERPROFILE\Documents\datalab-backup.zip"

.\.venv\Scripts\python.exe .\scripts\restore_workspace.py `
  --archive "$env:USERPROFILE\Documents\datalab-backup.zip" `
  --workspace "$env:LOCALAPPDATA\DataLabStudio-restored"
```

Installed Linux release (no Git, Node, or source scripts needed):

```bash
./.venv/bin/python -m app.storage.workspace_backup backup \
  --workspace "$HOME/.datalabstudio" --output "$HOME/datalab-backup.zip"
./.venv/bin/python -m app.storage.workspace_backup verify \
  --archive "$HOME/datalab-backup.zip"
./.venv/bin/python -m app.storage.workspace_backup restore \
  --archive "$HOME/datalab-backup.zip" --workspace "$HOME/.datalabstudio-restored"
```

The output archive must be outside the source workspace, in an existing parent
directory, and must not already exist. Restore accepts a new directory or one
containing only the stable `.workspace.lock` file. It never merges with or
overwrites an existing workspace. Start the app with `DATALAB_WORKSPACE_ROOT`
pointing to the restored directory only after success; keep the original intact.

Success is JSON with `status`, file count, and metadata version. Errors are stable
codes on stderr and nonzero exit status, without raw cell values or absolute
paths. A nonzero exit is not a completed backup/restore. `verify` validates the
archive and its references but does not start the app or assert statistical
validity of the user's historical analysis.

## Inventory Contract

| Owner | Path and digest columns | Size check |
| --- | --- | --- |
| `datasets` | `stored_path`, `sha256` | `size_bytes` |
| `dataset_artifacts` | `path`, `sha256` | `size_bytes` |
| `analysis_runs` | `result_path`, `result_sha256` | actual streamed size |
| `analysis_artifacts` | `path`, `sha256` | actual streamed size |
| `regression_models` | `manifest_path`, `manifest_sha256` | actual streamed size |
| `attribute_control_limit_sets` | `asset_path`, `asset_sha256` | actual streamed size |

Supported dataset artifact kinds are canonical rows, canonical manifest, profile
summary, and cell-correction manifest. Analysis kinds include row snapshots,
regression model JSON, GP NPZ numeric state, saved prediction rows and pasted
inputs, result JSON/CSV/HTML exports, and prediction CSV exports. Exact paths are
checked against the corresponding owner IDs and known writer layouts. Unknown
required kinds fail instead of being silently dropped. Shared model-manifest
ownership is deduplicated only when hashes agree. GP numeric-artifact references
must match a registered NPZ path and digest; NPZ is copied, never deserialized.
Every confirmed version must retain both canonical-row and canonical-manifest
registrations, matching the existing retention completeness contract.

The database is copied with SQLite's read-only connection and backup API, not a
raw `metadata.sqlite3` file copy that loses committed WAL data. WAL/SHM are not
archive members. `integrity_check`, foreign keys, migration markers, and the
known schema definitions (including legitimate cleanup triggers) are checked.
Canonical expected DDL is compiled in private memory only, never on the source.
All tables are copied wholesale, including DB-only DOE/BO/LHS data. Managed
Factorial BLOB size/hash/source-analysis relations and stored DOE/BO JSON digest
pairs are checked. These checks do not rerun domain calculations or synthesize
new design/response/history hashes.

SQLite backup can change the physical database file bytes. The guarantee is
preservation of logical rows, original stored JSON/BLOB content, and external
asset bytes, not equality of the source DB's physical SHA. The archive records
the copied database's SHA independently. No result, model, design, response,
configuration, or report payload is rewritten to a new version.

## Archive And Safety Boundary

Format 1 uses ZIP **STORED** entries (no compression), `manifest.json`, the copied
`db/metadata.sqlite3`, and all owned files under their normalized relative paths.
The manifest contains schema versions, row counts, canonical paths, byte sizes,
SHA-256 digests, and ownership claims. It contains no original absolute path.
Legacy Windows `\\` metadata paths remain byte-for-byte in the database while
archive paths use `/`. Such archives are marked `legacy_windows_paths` and must
be restored on Windows; Linux restore refuses them instead of rewriting the DB.

Default bounds: 100,000 data files, 2 GiB per file (including SQLite), 20 GiB total
file bytes, 16 MiB manifest/model JSON/checked database JSON, and 600 seconds.
These are failure limits, not silent truncation. The Python API accepts an
explicit `BackupLimits` value for controlled callers. There is no CLI bypass.
Directory enumeration and ZIP central-directory allocation are bounded as well.
The actual central-directory records are counted before `ZipFile` allocates its
entry list; forged EOCD counts and concatenated/fake directory spans are refused.
Time checks occur during SQLite work and chunked file copies, not just between
files. OS-level filesystem operations cannot be forcibly interrupted safely.
Temporary staging requires additional free space, approximately the archive plus
one extracted copy; insufficient space is a failure, never partial success.

Rejected inputs include traversal, absolute/drive/UNC paths, NTFS alternate data
streams, reserved Windows filenames, trailing dots/spaces, symlinks, junctions,
reparse points, source hardlinks, duplicate/case-colliding ZIP members, encrypted
or compressed members, non-regular members, unknown files, invalid sizes/hashes,
foreign-key errors, unknown schema objects, and interrupted delete/correction
markers. JSON duplicate keys and nonfinite constants are rejected.

The security boundary is a local filesystem with cooperating app processes.
This is not protection against an administrator replacing directories between
system calls, a compromised kernel, a malicious filesystem, or an untrusted
SQLite engine. Network filesystems without reliable exclusive OS locking and
hardlink publication are not supported. No pickle/joblib loading is introduced.
Windows UNC/device roots are rejected. Valid local drive paths use extended-length
Win32 syntax only for internal I/O, so staging and Korean/space-containing paths
longer than 260 characters work without changing metadata or archive paths.

## Publication And Recovery

Backup is fully verified before publication. Exclusive hardlink publication
cannot overwrite a concurrently created output filename. The temporary link is
removed afterward, leaving one regular archive file.

Restore holds the destination lease and verifies/extracts to a private sibling
directory. Before publishing any top-level directory it creates and fsyncs
`.workspace-restore-in-progress`, containing only an operation UUID. The stable
`.workspace.lock` inode is retained. Verified files are flushed before directory
publication. On normal failure, only this operation's published directories are
moved back to its private staging. No preexisting user files are removed.
Windows rename and Linux `renameat2(RENAME_NOREPLACE)` refuse even an empty
directory concurrently created at a publication path. Linux calls the system API
through stdlib `ctypes`; it does not silently fall back to replacing rename if
that API/filesystem is unavailable. This slice targets Windows and the supported
Ubuntu Linux release, not macOS or arbitrary network filesystems.

On hard process termination, a partial target can remain with the sentinel.
Application startup refuses that target before metadata migration/recovery with
`workspace_restore_incomplete`. Do not delete the marker to pretend completion.
Retain the partial directory for diagnosis and restore again to a new empty
destination from the verified archive. Neither startup nor CLI automatically
deletes a partial target or the source workspace.

POSIX directory entries are fsynced around publication and sentinel changes.
Windows file flushing and rename protect the tested process-crash boundary;
portable directory fsync is unavailable there. This is not an unconditional
power-loss/hardware-write-cache durability guarantee on Windows or Linux.

## Verification Sources

- `backend/tests/unit/test_workspace_backup.py`: deterministic inventory round
  trip, exclusive lease, path/link/reparse rejection, ZIP/manifest corruption,
  size limits, schema objects, deadlines, output preservation, and publication
  rollback. Fault injection targets the shared publication boundary so it runs
  on both Windows rename and Linux `renameat2`; a separate test exercises the
  real platform primitive's refusal to replace an existing empty directory.
  Synthetic fixtures only.
- `backend/tests/unit/test_workspace_backup_api.py`: API-created datasets,
  canonical artifacts, models including GP NPZ, exports, DOE BLOBs and DB-only
  ownership; reopen/prediction/checksum verification without refitting.
- Lease/startup tests separately cover competing processes, release after exit,
  future metadata rejection, and the incomplete-restore marker.

These are test locations, not a claim that every platform run has completed.
The remediation validation ledger records actual commands and OS outcomes.
