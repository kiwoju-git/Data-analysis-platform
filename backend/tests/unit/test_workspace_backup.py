from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import struct
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from app.storage.metadata import initialize_metadata_store, metadata_db_path
from app.storage.workspace_archive import DEFAULT_LIMITS, checked_path, relative_path
from app.storage.workspace_backup import (
    WorkspaceBackupError,
    backup_workspace,
    restore_workspace,
    verify_backup,
)
from app.storage.workspace_lease import WorkspaceLeaseError, acquire_workspace_lease


def _workspace(root: Path) -> Path:
    initialize_metadata_store(root)
    raw = root / "workspaces/datasets/dataset-1/raw/source.csv"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"x,y\n1,2\n3,4\n")
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute(
            "INSERT INTO datasets(dataset_id,original_filename,safe_filename,media_type,"
            "detected_format,stored_path,sha256,size_bytes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "dataset-1",
                "synthetic.csv",
                "synthetic.csv",
                "text/csv",
                "csv",
                raw.relative_to(root).as_posix(),
                hashlib.sha256(raw.read_bytes()).hexdigest(),
                raw.stat().st_size,
                "2026-10-18T00:00:00Z",
            ),
        )
    return root


def _rewrite(
    archive: Path, destination: Path, *, mutate_manifest=None, extra=None, omit=None, corrupt=None
) -> None:
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(destination, "w") as target:
        for info in source.infolist():
            if info.filename == omit:
                continue
            data = source.read(info.filename)
            if info.filename == "manifest.json" and mutate_manifest:
                manifest = json.loads(data)
                mutate_manifest(manifest)
                data = json.dumps(manifest).encode()
            if info.filename == corrupt:
                data = b"!" + data[1:]
            target.writestr(info, data)
        if extra:
            target.writestr(extra, b"untrusted")


def test_backup_restore_preserves_owned_bytes_and_db_rows(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    before = metadata_db_path(source).read_bytes()
    (source / "local-secret.env").write_text("not an asset", encoding="utf-8")
    archive = tmp_path / "archive.zip"
    manifest = backup_workspace(source, archive)
    assert manifest == verify_backup(archive)
    assert metadata_db_path(source).read_bytes() == before
    assert {entry["path"] for entry in manifest["files"]} == {
        "db/metadata.sqlite3",
        "workspaces/datasets/dataset-1/raw/source.csv",
    }
    target = tmp_path / "restored"
    assert restore_workspace(archive, target) == manifest
    assert not (target / "local-secret.env").exists()
    assert not (target / ".workspace-restore-in-progress").exists()
    assert (target / ".workspace.lock").is_file()
    for path in ["workspaces/datasets/dataset-1/raw/source.csv"]:
        assert (source / path).read_bytes() == (target / path).read_bytes()
    with (
        sqlite3.connect(metadata_db_path(source)) as original,
        sqlite3.connect(metadata_db_path(target)) as restored,
    ):
        assert (
            original.execute("SELECT * FROM datasets").fetchall()
            == restored.execute("SELECT * FROM datasets").fetchall()
        )


def test_lease_refuses_backup_and_restore(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "archive.zip"
    with (
        acquire_workspace_lease(source),
        pytest.raises(WorkspaceLeaseError, match="workspace_in_use"),
    ):
        backup_workspace(source, archive)
    backup_workspace(source, archive)
    target = tmp_path / "target"
    with (
        acquire_workspace_lease(target),
        pytest.raises(WorkspaceLeaseError, match="workspace_in_use"),
    ):
        restore_workspace(archive, target)


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "C:/escape",
        "x\\y",
        "x//y",
        "x/./y",
        "x/../y",
        "x:stream",
        "CON",
        "x/NUL.csv",
        "x. ",
        "x\x00y",
    ],
)
def test_archive_path_rejection(name: str) -> None:
    with pytest.raises(WorkspaceBackupError, match="unsafe_path"):
        relative_path(name)


@pytest.mark.parametrize(
    "extra",
    [
        "../outside",
        "workspaces/../outside",
        "db/metadata.sqlite3",
        "DB/METADATA.SQLITE3",
        "workspace/.env",
    ],
)
def test_archive_rejects_traversal_duplicate_case_and_unknown_entries(
    tmp_path: Path, extra: str
) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    bad = tmp_path / "bad.zip"
    _rewrite(archive, bad, extra=extra)
    with pytest.raises(WorkspaceBackupError):
        restore_workspace(bad, tmp_path / "target")
    assert not (tmp_path / "target/db").exists()
    assert not (tmp_path / "outside").exists()


@pytest.mark.parametrize("mode", ["missing", "corrupt", "metadata_size", "metadata_hash", "owner"])
def test_archive_rejects_missing_corrupt_and_false_manifest(tmp_path: Path, mode: str) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    bad = tmp_path / "bad.zip"
    name = "workspaces/datasets/dataset-1/raw/source.csv"

    def mutate(manifest):
        entry = next(item for item in manifest["files"] if item["path"] == name)
        if mode == "metadata_size":
            entry["size_bytes"] += 1
        elif mode == "metadata_hash":
            entry["sha256"] = "0" * 64
        elif mode == "owner":
            entry["owners"] = []

    _rewrite(
        archive,
        bad,
        mutate_manifest=mutate,
        omit=name if mode == "missing" else None,
        corrupt=name if mode == "corrupt" else None,
    )
    with pytest.raises(WorkspaceBackupError):
        verify_backup(bad)


def test_symlink_archive_entry_and_compression_rejected(tmp_path: Path) -> None:
    for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        archive = tmp_path / f"bad-{compression}.zip"
        with zipfile.ZipFile(archive, "w", compression=compression) as target:
            info = zipfile.ZipInfo("manifest.json")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            target.writestr(info, "../../private")
        with pytest.raises(WorkspaceBackupError):
            verify_backup(archive)


@pytest.mark.parametrize(
    "mode",
    ["missing", "corrupt", "unknown", "pending", "restore_marker", "unregistered", "hardlink"],
)
def test_source_integrity_and_recovery_refused_without_archive(tmp_path: Path, mode: str) -> None:
    source = _workspace(tmp_path / "source")
    raw = source / "workspaces/datasets/dataset-1/raw/source.csv"
    if mode == "missing":
        raw.unlink()
    elif mode == "corrupt":
        raw.write_bytes(b"altered")
    elif mode == "unknown":
        with sqlite3.connect(metadata_db_path(source)) as connection:
            connection.execute("CREATE TABLE unknown_assets(path TEXT)")
    elif mode == "pending":
        (raw.parent / ".delete-r-pending.q").write_bytes(b"pending")
    elif mode == "restore_marker":
        (source / ".workspace-restore-in-progress").write_text("operation")
    elif mode == "unregistered":
        (raw.parent / "unregistered.json").write_bytes(b"{}")
    elif mode == "hardlink":
        os.link(raw, tmp_path / "other-file")
    with pytest.raises(WorkspaceBackupError):
        backup_workspace(source, tmp_path / "failed.zip")
    assert not (tmp_path / "failed.zip").exists()
    assert metadata_db_path(source).exists()


def test_empty_target_only_and_output_never_overwritten(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    old = archive.read_bytes()
    with pytest.raises(WorkspaceBackupError, match="output_exists"):
        backup_workspace(source, archive)
    assert archive.read_bytes() == old
    with pytest.raises(WorkspaceBackupError, match="destination_inside_source"):
        backup_workspace(source, source / "inside.zip")
    with pytest.raises(WorkspaceBackupError, match="target_not_empty"):
        restore_workspace(archive, source)
    target = tmp_path / "target"
    target.mkdir()
    (target / "important.txt").write_bytes(b"original")
    with pytest.raises(WorkspaceBackupError, match="target_not_empty"):
        restore_workspace(archive, target)
    assert (target / "important.txt").read_bytes() == b"original"


def test_size_and_count_limits_are_enforced(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    for limits in (
        replace(DEFAULT_LIMITS, max_files=1),
        replace(DEFAULT_LIMITS, max_file_bytes=10),
        replace(DEFAULT_LIMITS, max_total_bytes=10),
        replace(DEFAULT_LIMITS, max_manifest_bytes=10),
    ):
        with pytest.raises(WorkspaceBackupError):
            verify_backup(archive, limits=limits)


def test_failed_publication_rolls_back_only_owned_directories(tmp_path: Path, monkeypatch) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    target = tmp_path / "target"
    rename = Path.rename

    def interrupted(path, destination):
        if Path(destination) == checked_path(target) / "workspaces":
            raise OSError("synthetic interruption")
        return rename(path, destination)

    monkeypatch.setattr(Path, "rename", interrupted)
    with pytest.raises(WorkspaceBackupError, match="restore_failed"):
        restore_workspace(archive, target)
    assert {item.name for item in target.iterdir()} == {".workspace.lock"}
    assert (source / "workspaces/datasets/dataset-1/raw/source.csv").exists()


def test_reparse_attributes_rejected_without_resolving_target(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "regular"
    path.write_bytes(b"x")
    original = Path.lstat

    class Junction:
        st_mode = stat.S_IFDIR | 0o755
        st_file_attributes = 0x400

    def lstat(candidate):
        return Junction() if candidate.name == path.name else original(candidate)

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(WorkspaceBackupError, match="unsafe_path"):
        checked_path(path)


@pytest.mark.parametrize(
    "ddl",
    [
        "CREATE VIEW external_view AS SELECT * FROM datasets",
        "CREATE TRIGGER injected AFTER INSERT ON datasets BEGIN DELETE FROM dataset_versions; END",
        "CREATE INDEX injected ON datasets(size_bytes)",
        "CREATE TABLE sqlitex_hidden(path TEXT)",
    ],
)
def test_unexpected_schema_objects_rejected(tmp_path: Path, ddl: str) -> None:
    source = _workspace(tmp_path / "source")
    with sqlite3.connect(metadata_db_path(source)) as connection:
        connection.execute(ddl)
    with pytest.raises(WorkspaceBackupError, match="unsupported_inventory"):
        backup_workspace(source, tmp_path / "archive.zip")


@pytest.mark.parametrize("seconds", [float("nan"), float("inf"), -1, 0, True, "600", None, 10**400])
def test_invalid_time_limits_rejected(tmp_path: Path, seconds) -> None:
    with pytest.raises(WorkspaceBackupError, match="invalid_limits"):
        verify_backup(tmp_path / "missing.zip", limits=replace(DEFAULT_LIMITS, max_seconds=seconds))


def test_chunk_read_deadline_is_checked(tmp_path: Path) -> None:
    from app.storage.workspace_archive import stream_file

    source = tmp_path / "input"
    source.write_bytes(b"123")
    with pytest.raises(WorkspaceBackupError, match="time_limit"):
        stream_file(source, DEFAULT_LIMITS, deadline=0)


@pytest.mark.parametrize("locator_offset", [0, 10**12, 2**64 - 1])
def test_malformed_zip64_locator_typed_failure(tmp_path: Path, locator_offset: int) -> None:
    archive = tmp_path / "bad.zip"
    archive.write_bytes(
        b"garbage" * 12
        + struct.pack("<4sLQL", b"PK\x06\x07", 0, locator_offset, 1)
        + struct.pack("<4s4H2LH", b"PK\x05\x06", 0, 0, 65535, 65535, 0xFFFFFFFF, 0xFFFFFFFF, 0)
    )
    with pytest.raises(WorkspaceBackupError, match="archive_invalid"):
        verify_backup(archive)


@pytest.mark.parametrize("mutation", ["nan", "bool_schema", "duplicate_key"])
def test_manifest_is_strict_json(tmp_path: Path, mutation: str) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive) as original, zipfile.ZipFile(bad, "w") as target:
        for info in original.infolist():
            data = original.read(info)
            if info.filename == "manifest.json":
                if mutation == "nan":
                    data = data[:-1] + b',"test":NaN}'
                elif mutation == "duplicate_key":
                    data = data[:-1] + b',"schema_version":1}'
                else:
                    value = json.loads(data)
                    value["schema_version"] = True
                    data = json.dumps(value).encode()
            target.writestr(info, data)
    with pytest.raises(WorkspaceBackupError, match="archive_invalid"):
        verify_backup(bad)


def test_module_cli_runs_without_source_script(tmp_path: Path, capsys) -> None:
    from app.storage.workspace_backup import main

    source = _workspace(tmp_path / "source")
    archive = tmp_path / "archive.zip"
    assert main(["backup", "--workspace", str(source), "--output", str(archive)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "verified"
    assert main(["verify", "--archive", str(archive)]) == 0
    assert (
        main(["restore", "--archive", str(archive), "--workspace", str(tmp_path / "restored")]) == 0
    )
    capsys.readouterr()
    assert main(["backup", "--workspace", str(source), "--output", str(archive)]) == 1
    failed = capsys.readouterr().err
    assert json.loads(failed)["code"] == "workspace_backup_output_exists"
    assert str(tmp_path) not in failed


def test_real_long_korean_staging_paths_preserve_files(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    parent = checked_path(tmp_path)
    while len(str(parent)) < 290:
        parent = parent / "backup path with spaces \ud55c\uae00"
    parent.mkdir(parents=True)
    archive = parent / "archive.zip"
    target = parent / "restored workspace \ud55c\uae00"
    manifest = backup_workspace(source, archive)
    assert verify_backup(archive) == manifest
    assert restore_workspace(archive, target) == manifest
    restored_raw = target / "workspaces/datasets/dataset-1/raw/source.csv"
    assert restored_raw.read_bytes() == b"x,y\n1,2\n3,4\n"
    assert all("\\\\?\\" not in item["path"] for item in manifest["files"])


def test_compressed_regular_archive_is_not_accepted(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    archive = tmp_path / "good.zip"
    backup_workspace(source, archive)
    bad = tmp_path / "compressed.zip"
    with (
        zipfile.ZipFile(archive) as original,
        zipfile.ZipFile(bad, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        for info in original.infolist():
            target.writestr(info.filename, original.read(info))
    with pytest.raises(WorkspaceBackupError, match="archive_invalid"):
        verify_backup(bad)


def test_wal_committed_rows_are_included_without_raw_database_copy(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    with sqlite3.connect(metadata_db_path(source)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("UPDATE datasets SET original_filename='committed-in-wal.csv'")
        connection.commit()
        assert Path(str(metadata_db_path(source)) + "-wal").is_file()
        archive = tmp_path / "wal.zip"
        backup_workspace(source, archive)
        target = tmp_path / "restored"
        restore_workspace(archive, target)
        with sqlite3.connect(metadata_db_path(target)) as restored:
            assert (
                restored.execute("SELECT original_filename FROM datasets").fetchone()[0]
                == "committed-in-wal.csv"
            )
        with zipfile.ZipFile(archive) as saved:
            assert not any(name.endswith(("-wal", "-shm")) for name in saved.namelist())


def test_forged_low_eocd_count_does_not_bypass_actual_entry_limit(tmp_path: Path) -> None:
    from app.storage.workspace_archive import check_zip_directory

    archive = tmp_path / "forged.zip"
    with zipfile.ZipFile(archive, "w") as target:
        for name in ("a", "b", "c"):
            target.writestr(name, b"x")
    data = bytearray(archive.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    struct.pack_into("<HH", data, end + 8, 0, 0)
    archive.write_bytes(data)
    with pytest.raises(WorkspaceBackupError, match="limit_exceeded"):
        check_zip_directory(archive, replace(DEFAULT_LIMITS, max_files=1))


def test_concatenated_fake_central_directory_is_rejected(tmp_path: Path) -> None:
    from app.storage.workspace_archive import check_zip_directory

    archive = tmp_path / "forged.zip"
    with zipfile.ZipFile(archive, "w") as target:
        for name in ("a", "b", "c"):
            target.writestr(name, b"x")
    data = bytearray(archive.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    directory_size, directory_offset = struct.unpack_from("<2L", data, end + 12)
    fake = bytearray(data[directory_offset : directory_offset + 46])
    struct.pack_into("<3H", fake, 28, 1, directory_size - 47, 0)
    fake.extend(b"a" + b"x" * (directory_size - 47))
    struct.pack_into("<HH", data, end + 8, 1, 1)
    struct.pack_into("<L", data, end + 16, 0)
    archive.write_bytes(fake + data)
    with pytest.raises(WorkspaceBackupError, match="archive_invalid"):
        check_zip_directory(archive, replace(DEFAULT_LIMITS, max_files=1))


def test_publication_never_replaces_existing_empty_directory(tmp_path: Path) -> None:
    from app.storage.workspace_backup import _publish_directory

    source = tmp_path / "source"
    target = tmp_path / "existing"
    source.mkdir()
    target.mkdir()
    (source / "data").write_bytes(b"verified")
    inode = target.stat().st_ino
    with pytest.raises(OSError):
        _publish_directory(source, target)
    assert target.stat().st_ino == inode
    assert not list(target.iterdir())
    assert (source / "data").read_bytes() == b"verified"


def test_oversized_identity_rejected_before_fetch(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    with sqlite3.connect(metadata_db_path(source)) as connection:
        connection.execute("UPDATE datasets SET stored_path=?", ("x" * 4097,))
    with pytest.raises(WorkspaceBackupError, match="limit_exceeded"):
        backup_workspace(source, tmp_path / "archive.zip")


def test_excess_migration_rows_are_rejected_before_list(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    with sqlite3.connect(metadata_db_path(source)) as connection:
        connection.execute("INSERT INTO schema_migrations(version,name) VALUES(1000,'unknown')")
    with pytest.raises(WorkspaceBackupError, match="unsupported_schema"):
        backup_workspace(source, tmp_path / "archive.zip")


def test_confirmed_version_missing_canonical_registration_is_refused(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    with sqlite3.connect(metadata_db_path(source)) as connection:
        connection.execute(
            "INSERT INTO dataset_versions(version_id,dataset_id,version_number,source_sha256,"
            "parsing_options_json,row_count,column_count,schema_hash,created_at) "
            "VALUES('version-1','dataset-1',1,?,'{}',2,2,?,'2026-10-18T00:00:00Z')",
            ("a" * 64, "b" * 64),
        )
    with pytest.raises(WorkspaceBackupError, match="asset_missing"):
        backup_workspace(source, tmp_path / "archive.zip")


def test_unsupported_zip_extract_version_is_a_typed_failure(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as target:
        target.writestr("manifest.json", b"{}")
    data = bytearray(archive.read_bytes())
    central = data.find(b"PK\x01\x02")
    struct.pack_into("<H", data, central + 6, 999)
    archive.write_bytes(data)
    with pytest.raises(WorkspaceBackupError, match="archive_invalid"):
        verify_backup(archive)
