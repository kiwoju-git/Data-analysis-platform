from __future__ import annotations

import errno
import os
import stat
import sys
from pathlib import Path
from types import TracebackType
from typing import Literal

WORKSPACE_LOCK_NAME = ".workspace.lock"
WORKSPACE_RESTORE_MARKER_NAME = ".workspace-restore-in-progress"


class WorkspaceRestoreIncompleteError(RuntimeError):
    code = "workspace_restore_incomplete"

    def __init__(self) -> None:
        super().__init__(self.code)


class WorkspaceLeaseError(RuntimeError):
    def __init__(self, code: Literal["workspace_in_use", "workspace_lease_unavailable"]) -> None:
        super().__init__(code)
        self.code = code


def ensure_workspace_restore_complete(root: Path) -> None:
    if os.path.lexists(root / WORKSPACE_RESTORE_MARKER_NAME):
        raise WorkspaceRestoreIncompleteError()


class WorkspaceLease:
    def __init__(self, root: Path, descriptor: int) -> None:
        self.root = root
        self._descriptor: int | None = descriptor
        self._entered = False

    def __enter__(self) -> WorkspaceLease:
        if self._descriptor is None or self._entered:
            raise WorkspaceLeaseError("workspace_lease_unavailable")
        self._entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    def release(self) -> None:
        descriptor = self._descriptor
        if descriptor is None:
            return
        self._descriptor = None
        try:
            try:
                _unlock_descriptor(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise WorkspaceLeaseError("workspace_lease_unavailable") from exc


def acquire_workspace_lease(root: Path) -> WorkspaceLease:
    """Acquire immediately; retain the returned lease until all workspace work stops."""
    descriptor: int | None = None
    try:
        canonical_root = root.resolve()
        canonical_root.mkdir(parents=True, exist_ok=True)
        lock_path = canonical_root / WORKSPACE_LOCK_NAME
        if lock_path.is_symlink():
            raise WorkspaceLeaseError("workspace_lease_unavailable")
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(lock_path, flags, 0o600)
        os.set_inheritable(descriptor, False)
        opened = os.fstat(descriptor)
        named = lock_path.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(named.st_mode)
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
            or getattr(named, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise WorkspaceLeaseError("workspace_lease_unavailable")
        _lock_descriptor(descriptor)
        lease = WorkspaceLease(canonical_root, descriptor)
        descriptor = None
        return lease
    except WorkspaceLeaseError:
        raise
    except (OSError, RuntimeError) as exc:
        raise WorkspaceLeaseError("workspace_lease_unavailable") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _lock_descriptor(descriptor: int) -> None:
    try:
        if sys.platform == "win32":
            import msvcrt

            # Windows permits a byte-range lock beyond EOF, so the file stays untouched.
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        code: Literal["workspace_in_use", "workspace_lease_unavailable"] = (
            "workspace_in_use"
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}
            else "workspace_lease_unavailable"
        )
        raise WorkspaceLeaseError(code) from exc


def _unlock_descriptor(descriptor: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)
