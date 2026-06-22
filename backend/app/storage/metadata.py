import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 2
METADATA_DB_RELATIVE_PATH: Final = Path("db") / "metadata.sqlite3"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str


@dataclass(frozen=True)
class MetadataStoreInfo:
    path: Path
    schema_version: int


@dataclass(frozen=True)
class DatasetRecord:
    dataset_id: str
    original_filename: str
    safe_filename: str
    media_type: str | None
    detected_format: str
    stored_path: str
    sha256: str
    size_bytes: int
    created_at: str


MIGRATIONS: Final[tuple[Migration, ...]] = (
    Migration(
        version=1,
        name="create_schema_migrations",
        sql="""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """,
    ),
    Migration(
        version=2,
        name="create_datasets",
        sql="""
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            original_filename TEXT NOT NULL,
            safe_filename TEXT NOT NULL,
            media_type TEXT,
            detected_format TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_datasets_created_at
        ON datasets(created_at);
        """,
    ),
)


def metadata_db_path(workspace_root: Path) -> Path:
    return workspace_root / METADATA_DB_RELATIVE_PATH


def initialize_metadata_store(workspace_root: Path) -> MetadataStoreInfo:
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        _apply_migrations(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")

    return MetadataStoreInfo(path=db_path, schema_version=SCHEMA_VERSION)


def _apply_migrations(connection: sqlite3.Connection) -> None:
    with connection:
        for migration in MIGRATIONS:
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (?, ?);
                """,
                (migration.version, migration.name),
            )


def insert_dataset_record(workspace_root: Path, record: DatasetRecord) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO datasets (
                    dataset_id,
                    original_filename,
                    safe_filename,
                    media_type,
                    detected_format,
                    stored_path,
                    sha256,
                    size_bytes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.dataset_id,
                    record.original_filename,
                    record.safe_filename,
                    record.media_type,
                    record.detected_format,
                    record.stored_path,
                    record.sha256,
                    record.size_bytes,
                    record.created_at,
                ),
            )


def get_dataset_record(workspace_root: Path, dataset_id: str) -> DatasetRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                dataset_id,
                original_filename,
                safe_filename,
                media_type,
                detected_format,
                stored_path,
                sha256,
                size_bytes,
                created_at
            FROM datasets
            WHERE dataset_id = ?;
            """,
            (dataset_id,),
        ).fetchone()

    if row is None:
        return None

    return DatasetRecord(
        dataset_id=row[0],
        original_filename=row[1],
        safe_filename=row[2],
        media_type=row[3],
        detected_format=row[4],
        stored_path=row[5],
        sha256=row[6],
        size_bytes=row[7],
        created_at=row[8],
    )
