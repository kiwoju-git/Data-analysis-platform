"""Bounded, portable archive paths and regular-file I/O for offline backups."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO


class WorkspaceBackupError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class BackupLimits:
    max_files: int = 100_000
    max_file_bytes: int = 2 * 1024**3
    max_total_bytes: int = 20 * 1024**3
    max_manifest_bytes: int = 16 * 1024**2
    max_seconds: float = 600


DEFAULT_LIMITS = BackupLimits()
CHUNK_SIZE = 1024 * 1024
_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def relative_path(value: object, *, legacy_windows: bool = False) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise WorkspaceBackupError("workspace_backup_unsafe_path")
    if legacy_windows:
        value = value.replace("\\", "/")
    parts = value.split("/")
    if any(
        not part
        or part in {".", ".."}
        or part.endswith((".", " "))
        or _RESERVED.match(part)
        or any(ord(char) < 32 or char in '\\:<>"|?*' for char in part)
        for part in parts
    ):
        raise WorkspaceBackupError("workspace_backup_unsafe_path")
    return value


def checked_path(path: Path, *, file: bool = False) -> Path:
    """Reject links/junctions in every existing segment, before resolving."""
    raw = os.path.abspath(path)
    if os.name == "nt":
        # Internal Win32 long-path syntax is never stored in manifests or metadata.
        if raw.startswith("\\\\?\\"):
            raw = raw[4:]
        if not re.match(r"^[A-Za-z]:\\", raw):
            raise WorkspaceBackupError("workspace_backup_unsafe_path")
        absolute = Path("\\\\?\\" + raw)
    else:
        absolute = Path(raw)
    for item in reversed((absolute, *absolute.parents)):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise WorkspaceBackupError("workspace_backup_unsafe_path")
        if item != absolute and not stat.S_ISDIR(info.st_mode):
            raise WorkspaceBackupError("workspace_backup_unsafe_path")
    if file:
        try:
            info = absolute.lstat()
        except FileNotFoundError as exc:
            raise WorkspaceBackupError("workspace_backup_asset_missing") from exc
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise WorkspaceBackupError("workspace_backup_unsafe_path")
    return absolute


def stream_file(
    path: Path,
    limits: BackupLimits,
    destination: IO[bytes] | None = None,
    *,
    deadline: float | None = None,
) -> tuple[int, str]:
    checked_path(path, file=True)
    before = path.stat()
    if before.st_size > limits.max_file_bytes:
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        opened = os.fstat(source.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise WorkspaceBackupError("workspace_backup_source_changed")
        while chunk := source.read(CHUNK_SIZE):
            if deadline is not None and time.monotonic() > deadline:
                raise WorkspaceBackupError("workspace_backup_time_limit")
            size += len(chunk)
            if size > limits.max_file_bytes:
                raise WorkspaceBackupError("workspace_backup_limit_exceeded")
            digest.update(chunk)
            if destination is not None:
                destination.write(chunk)
            if deadline is not None and time.monotonic() > deadline:
                raise WorkspaceBackupError("workspace_backup_time_limit")
        after = os.fstat(source.fileno())
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise WorkspaceBackupError("workspace_backup_source_changed")
    if size != before.st_size:
        raise WorkspaceBackupError("workspace_backup_source_changed")
    return size, digest.hexdigest()


def check_zip_directory(path: Path, limits: BackupLimits) -> None:
    """Bound central-directory allocation before ZipFile reads its entries."""
    checked_path(path, file=True)
    size = path.stat().st_size
    if size > limits.max_total_bytes + limits.max_manifest_bytes + limits.max_files * 2048:
        raise WorkspaceBackupError("workspace_backup_limit_exceeded")
    with path.open("rb") as stream:
        stream.seek(max(0, size - 65557))
        tail = stream.read()
        offset = tail.rfind(b"PK\x05\x06")
        if offset < 0 or len(tail) - offset < 22:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        eocd = struct.unpack_from("<4s4H2LH", tail, offset)
        if eocd[1] or eocd[2] or eocd[3] != eocd[4]:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        if len(tail) - offset != 22 + eocd[7]:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        count, directory_size, directory_offset = eocd[4:7]
        end_offset = size - len(tail) + offset
        directory_end = end_offset
        if count == 65535 or directory_size == 0xFFFFFFFF or directory_offset == 0xFFFFFFFF:
            if end_offset < 20:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            stream.seek(end_offset - 20)
            locator = struct.unpack("<4sLQL", stream.read(20))
            if locator[0] != b"PK\x06\x07" or locator[1] or locator[3] != 1:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            if locator[2] > end_offset - 76:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            stream.seek(locator[2])
            record = stream.read(56)
            if len(record) != 56:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            zipped = struct.unpack("<4sQ2H2L4Q", record)
            if zipped[0] != b"PK\x06\x06" or zipped[4] or zipped[5] or zipped[6] != zipped[7]:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            if zipped[1] != 44 or locator[2] + 56 != end_offset - 20:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            count, directory_size, directory_offset = zipped[7:10]
            directory_end = locator[2]
        if count > limits.max_files + 1 or directory_size > (limits.max_files + 1) * 2048:
            raise WorkspaceBackupError("workspace_backup_limit_exceeded")
        if directory_offset + directory_size != directory_end:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
        stream.seek(directory_offset)
        remaining = directory_size
        actual_count = 0
        while remaining:
            if remaining < 46:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            header = stream.read(46)
            if len(header) != 46 or header[:4] != b"PK\x01\x02":
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            name_size, extra_size, comment_size = struct.unpack_from("<3H", header, 28)
            record_size = 46 + name_size + extra_size + comment_size
            if record_size > remaining:
                raise WorkspaceBackupError("workspace_backup_archive_invalid")
            actual_count += 1
            if actual_count > limits.max_files + 1:
                raise WorkspaceBackupError("workspace_backup_limit_exceeded")
            stream.seek(record_size - 46, os.SEEK_CUR)
            remaining -= record_size
        if actual_count != count:
            raise WorkspaceBackupError("workspace_backup_archive_invalid")
