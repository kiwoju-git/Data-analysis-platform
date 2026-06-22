import sqlite3

from app.storage.metadata import SCHEMA_VERSION, initialize_metadata_store, metadata_db_path


def test_initialize_metadata_store_creates_version_table_with_unicode_path(tmp_path) -> None:
    workspace_root = tmp_path / "workspace with spaces" / "한글 경로"

    store = initialize_metadata_store(workspace_root)

    assert store.path == metadata_db_path(workspace_root)
    assert store.path.exists()
    assert store.schema_version == SCHEMA_VERSION

    with sqlite3.connect(store.path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [(1, "create_schema_migrations"), (2, "create_datasets")]
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_is_idempotent(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"

    first = initialize_metadata_store(workspace_root)
    second = initialize_metadata_store(workspace_root)

    assert first == second

    with sqlite3.connect(second.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

    assert count == 2


def test_initialize_metadata_store_upgrades_from_schema_version_one(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            """,
        )
        connection.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (1, ?);",
            ("create_schema_migrations",),
        )
        connection.execute("PRAGMA user_version = 1;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        datasets_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'datasets';
            """,
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [(1, "create_schema_migrations"), (2, "create_datasets")]
    assert datasets_table == ("datasets",)
    assert user_version == SCHEMA_VERSION
