# Workspace Ownership Lease

## Scope

One cooperating application or maintenance process may own a canonical local
workspace at a time. This is not authentication or a multi-user access policy.
It does not replace SQLite transactions or per-request schema compare-and-swap.
SMB/NFS and hostile local processes are outside this guarantee.

## Interface and Lifetime

`app.storage.workspace_lease.acquire_workspace_lease(root)` acquires immediately
and returns a context manager. Its `root` is the resolved canonical path.
`release()` is idempotent; nested entry or re-entry after release is rejected.

The stdlib-only module is usable by the application and an offline backup CLI.
Its stable errors are `workspace_in_use` and `workspace_lease_unavailable`.
Error text does not include paths, file contents, process IDs, or SQL.

The owner holds a non-inheritable descriptor for `.workspace.lock` until all
workspace work is finished. Windows uses a nonblocking one-byte range lock;
POSIX uses an exclusive nonblocking `flock`. The lock can cover the first byte
of an empty file, so acquisition never writes or truncates ownership contents.
There is no PID-based takeover, expiry, stale-file deletion, or `force` bypass.
The lock file is not unlinked or replaced on release: its stable inode is part
of the exclusion boundary. Symlink, reparse-point, and hard-linked lock files
are rejected rather than used to lock another location.

Platform references: [Python msvcrt locking](https://docs.python.org/3.10/library/msvcrt.html#msvcrt.locking),
[Python fcntl flock](https://docs.python.org/3.10/library/fcntl.html#fcntl.flock),
[Microsoft byte-range locking](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170).

## Integration Boundary

The application acquires before metadata initialization, migrations,
backfills, and all five quarantine/correction recovery operations. It releases
after shutdown, including startup exceptions. Importing a module or constructing an app does not acquire
the lease; Windows spawned calculation workers are not workspace owners.

Backup and restore use the same lease and exclude `.workspace.lock` from the
archive. Restore must retain the destination lock inode during publication.
A `.workspace-restore-in-progress` marker identifies incomplete publication;
the app and backup must reject it before reading or changing metadata. Partial
restore contents are not automatically deleted. Retry into a new empty target.

Before opening an existing database for initialization writes,
`validate_metadata_compatibility(connection)` inspects `PRAGMA user_version`
and the highest recorded `schema_migrations.version` using a read-only
connection. Both markers must be no newer than metadata schema 20. Future
versions fail with `workspace_metadata_newer`; invalid version markers or an
unreadable database format fail with `workspace_metadata_invalid`. The same
check runs before migrations on the initialization connection. Neither future
version marker is downgraded, and the validator never migrates or recovers.

## Verification

`backend/tests/unit/test_workspace_lease.py` exercises same-process exclusion,
canonical aliases, independent workspaces, non-inherited handles, stable lock
contents, invalid link targets, and genuine child-process contention. Child
owners are tested with both normal exit and forced termination. Only child
processes created by the test are terminated; workspaces are synthetic pytest
temporary directories. Native Windows and Linux runs are separate evidence;
passing one platform does not validate the other.

`backend/tests/unit/test_workspace_lifespan.py` verifies the application holds
the lease before every startup operation, refuses a second owner before any
mutation, releases after each startup failure, preserves incomplete restore
contents, and refuses future/invalid metadata without changing database bytes.
Full acceptance also requires all existing startup, retention, backup, and
release workflows to pass.
