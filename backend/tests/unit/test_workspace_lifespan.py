import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app import main
from app.core.config import Settings
from app.storage import metadata
from app.storage.workspace_lease import (
    WORKSPACE_RESTORE_MARKER_NAME,
    WorkspaceLeaseError,
    WorkspaceRestoreIncompleteError,
    acquire_workspace_lease,
)

STARTUP_OPERATIONS = (
    "initialize_metadata_store",
    "recover_analysis_export_quarantine_files",
    "recover_analysis_run_quarantine_files",
    "recover_workspace_asset_quarantine_files",
    "recover_dataset_version_quarantine_files",
    "recover_dataset_cell_correction_files",
)


def _unexpected(*args, **kwargs):
    raise AssertionError("Workspace mutation was reached before ownership/compatibility checks")


def _future_database(root, *, user_version, migration_version=None):
    path = metadata.metadata_db_path(root)
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(f"PRAGMA user_version = {user_version}")
        connection.execute("CREATE TABLE private_data(value TEXT)")
        connection.execute("INSERT INTO private_data VALUES ('synthetic private value')")
        if migration_version is not None:
            connection.execute("CREATE TABLE schema_migrations(version INTEGER, name TEXT)")
            connection.execute(
                "INSERT INTO schema_migrations VALUES (?, 'future')", (migration_version,)
            )
    return path


def test_app_construction_does_not_acquire_workspace_and_lifespan_does(tmp_path):
    app = main.create_app(Settings(workspace_root=tmp_path))
    with acquire_workspace_lease(tmp_path):
        main.create_app(Settings(workspace_root=tmp_path))
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
            with TestClient(app):
                pass
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
            acquire_workspace_lease(tmp_path)
    with acquire_workspace_lease(tmp_path):
        pass


def test_second_app_cannot_migrate_or_recover_an_owned_workspace(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(main.create_app(settings)) as first:
        for name in STARTUP_OPERATIONS:
            monkeypatch.setattr(main, name, _unexpected)
        with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
            with TestClient(main.create_app(settings)):
                pass
        assert first.get("/api/v1/health").status_code == 200
    with acquire_workspace_lease(tmp_path):
        pass


@pytest.mark.parametrize("failing_operation", STARTUP_OPERATIONS)
def test_startup_error_releases_lease_and_prevents_later_recovery(
    tmp_path, monkeypatch, failing_operation
):
    called = []

    def operation(name):
        def run(root):
            with pytest.raises(WorkspaceLeaseError, match="^workspace_in_use$"):
                acquire_workspace_lease(root)
            called.append(name)
            if name == failing_operation:
                raise ValueError("synthetic startup failure")
            return None

        return run

    for name in STARTUP_OPERATIONS:
        monkeypatch.setattr(main, name, operation(name))
    with pytest.raises(ValueError, match="^synthetic startup failure$"):
        with TestClient(main.create_app(Settings(workspace_root=tmp_path))):
            pass
    assert called == list(STARTUP_OPERATIONS[: STARTUP_OPERATIONS.index(failing_operation) + 1])
    with acquire_workspace_lease(tmp_path):
        pass


def test_incomplete_restore_refuses_startup_without_cleanup(tmp_path, monkeypatch):
    marker = tmp_path / WORKSPACE_RESTORE_MARKER_NAME
    marker.write_text("synthetic-operation", encoding="utf-8")
    partial = tmp_path / "partially-restored.bin"
    partial.write_bytes(b"preserve synthetic partial content")
    for name in STARTUP_OPERATIONS:
        monkeypatch.setattr(main, name, _unexpected)
    with pytest.raises(WorkspaceRestoreIncompleteError, match="^workspace_restore_incomplete$"):
        with TestClient(main.create_app(Settings(workspace_root=tmp_path))):
            pass
    assert marker.read_text(encoding="utf-8") == "synthetic-operation"
    assert partial.read_bytes() == b"preserve synthetic partial content"
    assert not metadata.metadata_db_path(tmp_path).exists()
    with acquire_workspace_lease(tmp_path):
        pass


@pytest.mark.parametrize("user_version,migration_version", [(21, None), (20, 21), (0, 21)])
def test_future_metadata_refuses_startup_and_initialization_without_mutation(
    tmp_path, monkeypatch, user_version, migration_version
):
    path = _future_database(
        tmp_path, user_version=user_version, migration_version=migration_version
    )
    before = path.read_bytes()
    monkeypatch.setattr(metadata, "_apply_migrations", _unexpected)
    for name in STARTUP_OPERATIONS[1:]:
        monkeypatch.setattr(main, name, _unexpected)
    with pytest.raises(
        metadata.MetadataSchemaCompatibilityError, match="^workspace_metadata_newer$"
    ):
        metadata.initialize_metadata_store(tmp_path)
    assert path.read_bytes() == before
    with pytest.raises(
        metadata.MetadataSchemaCompatibilityError, match="^workspace_metadata_newer$"
    ):
        with TestClient(main.create_app(Settings(workspace_root=tmp_path))):
            pass
    assert path.read_bytes() == before
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == user_version
        assert connection.execute("SELECT value FROM private_data").fetchone() == (
            "synthetic private value",
        )
    with acquire_workspace_lease(tmp_path):
        pass


@pytest.mark.parametrize("corruption", ["bytes", "negative_version", "invalid_migration_version"])
def test_invalid_metadata_is_not_replaced_by_empty_workspace(tmp_path, corruption):
    path = metadata.metadata_db_path(tmp_path)
    path.parent.mkdir()
    if corruption == "bytes":
        path.write_bytes(b"private invalid database")
    else:
        with closing(sqlite3.connect(path)) as connection, connection:
            if corruption == "negative_version":
                connection.execute("PRAGMA user_version = -1")
            else:
                connection.execute("CREATE TABLE schema_migrations(version TEXT)")
                connection.execute("INSERT INTO schema_migrations VALUES ('invalid')")
    before = path.read_bytes()
    with pytest.raises(metadata.MetadataSchemaCompatibilityError) as error:
        metadata.initialize_metadata_store(tmp_path)
    assert error.value.code == "workspace_metadata_invalid"
    assert "private" not in str(error.value)
    assert str(tmp_path) not in str(error.value)
    assert path.read_bytes() == before


def test_metadata_version_reader_is_usable_on_readonly_connection(tmp_path):
    store = metadata.initialize_metadata_store(tmp_path)
    before = store.path.read_bytes()
    with closing(
        sqlite3.connect(f"{store.path.resolve().as_uri()}?mode=ro", uri=True)
    ) as connection:
        assert metadata.validate_metadata_compatibility(connection) == 20
    assert store.path.read_bytes() == before
