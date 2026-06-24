import sqlite3
from uuid import uuid4

from app.storage.metadata import (
    SCHEMA_VERSION,
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetRecord,
    DatasetVersionRecord,
    JobRecord,
    count_analysis_artifact_records,
    get_analysis_run_record,
    get_dataset_artifact_record,
    get_job_record,
    initialize_metadata_store,
    insert_analysis_artifact_record,
    insert_analysis_run_record,
    insert_dataset_record,
    insert_dataset_version_record,
    insert_job_record,
    list_dataset_artifact_records,
    metadata_db_path,
    update_analysis_run_status_record,
    update_job_cancellation_record,
    upsert_dataset_artifact_record,
)


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

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
    ]
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_is_idempotent(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"

    first = initialize_metadata_store(workspace_root)
    second = initialize_metadata_store(workspace_root)

    assert first == second

    with sqlite3.connect(second.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

    assert count == 5


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

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
    ]
    assert datasets_table == ("datasets",)
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_two(tmp_path) -> None:
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
            """
            CREATE TABLE datasets (
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
            """,
        )
        connection.executemany(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
            [
                (1, "create_schema_migrations"),
                (2, "create_datasets"),
            ],
        )
        connection.execute("PRAGMA user_version = 2;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        dataset_versions_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'dataset_versions';
            """,
        ).fetchone()
        dataset_columns_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'dataset_columns';
            """,
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
    ]
    assert dataset_versions_table == ("dataset_versions",)
    assert dataset_columns_table == ("dataset_columns",)
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_three(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE TABLE datasets (
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

            CREATE TABLE dataset_versions (
                version_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL CHECK (version_number >= 1),
                source_sha256 TEXT NOT NULL,
                parsing_options_json TEXT NOT NULL,
                row_count INTEGER NOT NULL CHECK (row_count >= 0),
                column_count INTEGER NOT NULL CHECK (column_count >= 1),
                schema_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(dataset_id, version_number)
            );

            CREATE TABLE dataset_columns (
                column_id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL REFERENCES dataset_versions(version_id) ON DELETE CASCADE,
                column_index INTEGER NOT NULL CHECK (column_index >= 0),
                original_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                measurement_level TEXT NOT NULL,
                role TEXT NOT NULL,
                unit TEXT,
                UNIQUE(version_id, column_index),
                UNIQUE(version_id, display_name)
            );
            """,
        )
        connection.executemany(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
            [
                (1, "create_schema_migrations"),
                (2, "create_datasets"),
                (3, "create_dataset_versions_and_columns"),
            ],
        )
        connection.execute("PRAGMA user_version = 3;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name IN ('analysis_runs', 'analysis_artifacts', 'jobs', 'dataset_artifacts');
                """,
            ).fetchall()
        }
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
    ]
    assert table_names == {"analysis_runs", "analysis_artifacts", "jobs", "dataset_artifacts"}
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_four(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE TABLE datasets (
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

            CREATE TABLE dataset_versions (
                version_id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
                version_number INTEGER NOT NULL CHECK (version_number >= 1),
                source_sha256 TEXT NOT NULL,
                parsing_options_json TEXT NOT NULL,
                row_count INTEGER NOT NULL CHECK (row_count >= 0),
                column_count INTEGER NOT NULL CHECK (column_count >= 1),
                schema_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(dataset_id, version_number)
            );

            CREATE TABLE dataset_columns (
                column_id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL REFERENCES dataset_versions(version_id) ON DELETE CASCADE,
                column_index INTEGER NOT NULL CHECK (column_index >= 0),
                original_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                measurement_level TEXT NOT NULL,
                role TEXT NOT NULL,
                unit TEXT,
                UNIQUE(version_id, column_index),
                UNIQUE(version_id, display_name)
            );

            CREATE TABLE analysis_runs (
                analysis_id TEXT PRIMARY KEY,
                method_id TEXT NOT NULL,
                method_version TEXT NOT NULL,
                dataset_version_id TEXT REFERENCES dataset_versions(version_id) ON DELETE RESTRICT,
                config_json TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'queued',
                        'running',
                        'succeeded',
                        'failed',
                        'cancel_requested',
                        'cancelled'
                    )
                ),
                result_path TEXT,
                result_sha256 TEXT,
                stale INTEGER NOT NULL DEFAULT 0 CHECK (stale IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                app_version TEXT NOT NULL
            );

            CREATE TABLE analysis_artifacts (
                artifact_id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                media_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(analysis_id, kind, path)
            );

            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                analysis_id TEXT REFERENCES analysis_runs(analysis_id) ON DELETE SET NULL,
                job_type TEXT NOT NULL,
                state TEXT NOT NULL CHECK (
                    state IN (
                        'queued',
                        'running',
                        'succeeded',
                        'failed',
                        'cancel_requested',
                        'cancelled'
                    )
                ),
                progress REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 1),
                cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0, 1)),
                error_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );
            """,
        )
        connection.executemany(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
            [
                (1, "create_schema_migrations"),
                (2, "create_datasets"),
                (3, "create_dataset_versions_and_columns"),
                (4, "create_analysis_runs_artifacts_and_jobs"),
            ],
        )
        connection.execute("PRAGMA user_version = 4;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        dataset_artifacts_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'dataset_artifacts';
            """,
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
    ]
    assert dataset_artifacts_table == ("dataset_artifacts",)
    assert user_version == SCHEMA_VERSION


def test_dataset_artifact_records_round_trip_with_dataset_version(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    initialize_metadata_store(workspace_root)
    dataset_id = str(uuid4())
    version_id = str(uuid4())
    artifact_id = str(uuid4())
    created_at = "2026-06-24T00:00:00.000Z"

    insert_dataset_record(
        workspace_root,
        DatasetRecord(
            dataset_id=dataset_id,
            original_filename="sample.csv",
            safe_filename="sample.csv",
            media_type="text/csv",
            detected_format="csv",
            stored_path="workspaces/datasets/raw/source.csv",
            sha256="1" * 64,
            size_bytes=12,
            created_at=created_at,
        ),
    )
    insert_dataset_version_record(
        workspace_root,
        DatasetVersionRecord(
            version_id=version_id,
            dataset_id=dataset_id,
            version_number=1,
            source_sha256="1" * 64,
            parsing_options_json='{"kind":"delimited_text"}',
            row_count=1,
            column_count=1,
            schema_hash="2" * 64,
            created_at=created_at,
        ),
        [
            DatasetColumnRecord(
                column_id=str(uuid4()),
                version_id=version_id,
                column_index=0,
                original_name="alpha",
                display_name="alpha",
                data_type="integer",
                measurement_level="unknown",
                role="unspecified",
                unit=None,
            ),
        ],
        artifacts=[
            DatasetArtifactRecord(
                artifact_id=artifact_id,
                version_id=version_id,
                kind="canonical_rows",
                path="workspaces/datasets/versions/canonical.rows.jsonl",
                sha256="3" * 64,
                media_type="application/x-ndjson",
                size_bytes=128,
                created_at=created_at,
            ),
        ],
    )

    artifacts = list_dataset_artifact_records(workspace_root, version_id)
    artifact = get_dataset_artifact_record(workspace_root, version_id, "canonical_rows")

    assert artifacts == [
        DatasetArtifactRecord(
            artifact_id=artifact_id,
            version_id=version_id,
            kind="canonical_rows",
            path="workspaces/datasets/versions/canonical.rows.jsonl",
            sha256="3" * 64,
            media_type="application/x-ndjson",
            size_bytes=128,
            created_at=created_at,
        ),
    ]
    assert artifact == artifacts[0]


def test_dataset_artifact_record_upsert_replaces_same_kind(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    initialize_metadata_store(workspace_root)
    dataset_id = str(uuid4())
    version_id = str(uuid4())
    created_at = "2026-06-24T00:00:00.000Z"

    insert_dataset_record(
        workspace_root,
        DatasetRecord(
            dataset_id=dataset_id,
            original_filename="sample.csv",
            safe_filename="sample.csv",
            media_type="text/csv",
            detected_format="csv",
            stored_path="workspaces/datasets/raw/source.csv",
            sha256="1" * 64,
            size_bytes=12,
            created_at=created_at,
        ),
    )
    insert_dataset_version_record(
        workspace_root,
        DatasetVersionRecord(
            version_id=version_id,
            dataset_id=dataset_id,
            version_number=1,
            source_sha256="1" * 64,
            parsing_options_json='{"kind":"delimited_text"}',
            row_count=1,
            column_count=1,
            schema_hash="2" * 64,
            created_at=created_at,
        ),
        [
            DatasetColumnRecord(
                column_id=str(uuid4()),
                version_id=version_id,
                column_index=0,
                original_name="alpha",
                display_name="alpha",
                data_type="integer",
                measurement_level="unknown",
                role="unspecified",
                unit=None,
            ),
        ],
    )

    first = DatasetArtifactRecord(
        artifact_id=str(uuid4()),
        version_id=version_id,
        kind="profile_summary",
        path="workspaces/datasets/versions/first.profile.json",
        sha256="3" * 64,
        media_type="application/json",
        size_bytes=128,
        created_at=created_at,
    )
    second = DatasetArtifactRecord(
        artifact_id=str(uuid4()),
        version_id=version_id,
        kind="profile_summary",
        path="workspaces/datasets/versions/second.profile.json",
        sha256="4" * 64,
        media_type="application/json",
        size_bytes=256,
        created_at="2026-06-24T00:00:01.000Z",
    )

    upsert_dataset_artifact_record(workspace_root, first)
    upsert_dataset_artifact_record(workspace_root, second)

    artifacts = list_dataset_artifact_records(workspace_root, version_id)

    assert artifacts == [second]


def test_analysis_run_artifact_and_job_records_round_trip(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    initialize_metadata_store(workspace_root)
    analysis_id = str(uuid4())
    artifact_id = str(uuid4())
    job_id = str(uuid4())
    created_at = "2026-06-24T00:00:00.000Z"

    insert_analysis_run_record(
        workspace_root,
        AnalysisRunRecord(
            analysis_id=analysis_id,
            method_id="eda.descriptive",
            method_version="0.1.0",
            dataset_version_id=None,
            config_json='{"schema_version":1,"roles":{},"options":{}}',
            status="queued",
            result_path=None,
            result_sha256=None,
            stale=False,
            created_at=created_at,
            updated_at=created_at,
            completed_at=None,
            app_version="0.1.0",
        ),
    )
    insert_analysis_artifact_record(
        workspace_root,
        AnalysisArtifactRecord(
            artifact_id=artifact_id,
            analysis_id=analysis_id,
            kind="manifest",
            path="workspaces/analyses/result.json",
            sha256="0" * 64,
            media_type="application/json",
            created_at=created_at,
        ),
    )
    insert_job_record(
        workspace_root,
        JobRecord(
            job_id=job_id,
            analysis_id=analysis_id,
            job_type="analysis",
            state="running",
            progress=0.25,
            cancel_requested=False,
            error_code=None,
            created_at=created_at,
            updated_at=created_at,
            completed_at=None,
        ),
    )

    run = get_analysis_run_record(workspace_root, analysis_id)
    job = get_job_record(workspace_root, job_id)
    updated_run = update_analysis_run_status_record(
        workspace_root,
        analysis_id,
        "cancel_requested",
        "2026-06-24T00:00:01.000Z",
    )
    updated_job = update_job_cancellation_record(
        workspace_root,
        job_id,
        "2026-06-24T00:00:01.000Z",
    )

    assert run is not None
    assert run.method_id == "eda.descriptive"
    assert run.dataset_version_id is None
    assert count_analysis_artifact_records(workspace_root, analysis_id) == 1
    assert job is not None
    assert job.progress == 0.25
    assert updated_run is not None
    assert updated_run.status == "cancel_requested"
    assert updated_job is not None
    assert updated_job.state == "cancel_requested"
    assert updated_job.cancel_requested is True
