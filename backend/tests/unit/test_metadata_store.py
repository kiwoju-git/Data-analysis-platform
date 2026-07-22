import sqlite3
from uuid import uuid4

from app.services.doe_response_revisions import canonical_response_revision_sha256
from app.storage.metadata import (
    MIGRATIONS,
    SCHEMA_VERSION,
    AnalysisArtifactRecord,
    AnalysisRunRecord,
    AttributeControlLimitSetRecord,
    DatasetArtifactRecord,
    DatasetColumnRecord,
    DatasetRecord,
    DatasetVersionRecord,
    ExperimentDesignAnalysisRecord,
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    ExperimentRunRecord,
    ExperimentRunResponseRecord,
    JobRecord,
    RegressionModelRecord,
    count_analysis_artifact_records,
    count_attribute_control_limit_set_records,
    get_analysis_run_record,
    get_attribute_control_limit_set_record,
    get_attribute_control_limit_set_record_by_source_analysis,
    get_current_experiment_response_revision_record,
    get_dataset_artifact_record,
    get_experiment_design_analysis_record,
    get_experiment_design_record,
    get_experiment_design_version_record,
    get_job_record,
    get_latest_experiment_design_analysis_record,
    get_regression_model_record,
    initialize_metadata_store,
    insert_analysis_artifact_record,
    insert_analysis_run_record,
    insert_analysis_run_record_with_artifacts_and_regression_model,
    insert_attribute_control_limit_set_record,
    insert_dataset_record,
    insert_dataset_version_record,
    insert_experiment_design_analysis_record,
    insert_experiment_design_records,
    insert_job_record,
    list_attribute_control_limit_set_records,
    list_dataset_artifact_records,
    list_experiment_response_revision_value_records,
    list_experiment_run_records,
    list_experiment_run_response_records,
    metadata_db_path,
    replace_experiment_run_response_records,
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
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
    ]
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_is_idempotent(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"

    first = initialize_metadata_store(workspace_root)
    second = initialize_metadata_store(workspace_root)

    assert first == second

    with sqlite3.connect(second.path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]

    assert count == SCHEMA_VERSION


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
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
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
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
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
                AND name IN (
                    'analysis_runs',
                    'analysis_artifacts',
                    'jobs',
                    'dataset_artifacts',
                    'regression_models',
                    'experiment_designs',
                    'experiment_design_versions',
                    'experiment_runs'
                );
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
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
    ]
    assert table_names == {
        "analysis_runs",
        "analysis_artifacts",
        "jobs",
        "dataset_artifacts",
        "regression_models",
        "experiment_designs",
        "experiment_design_versions",
        "experiment_runs",
    }
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
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
    ]
    assert dataset_artifacts_table == ("dataset_artifacts",)
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_five(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 5:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (?, ?);
                """,
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 5;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        regression_models_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'regression_models';
            """,
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
    ]
    assert regression_models_table == ("regression_models",)
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_six(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 6:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (?, ?);
                """,
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 6;")

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
                AND name IN (
                    'experiment_designs',
                    'experiment_design_versions',
                    'experiment_runs'
                );
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
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
    ]
    assert table_names == {
        "experiment_designs",
        "experiment_design_versions",
        "experiment_runs",
    }
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_seven(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 7:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (?, ?);
                """,
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 7;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version",
        ).fetchall()
        response_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'experiment_run_responses';
            """,
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert rows == [
        (1, "create_schema_migrations"),
        (2, "create_datasets"),
        (3, "create_dataset_versions_and_columns"),
        (4, "create_analysis_runs_artifacts_and_jobs"),
        (5, "create_dataset_artifacts"),
        (6, "create_regression_models"),
        (7, "create_experiment_designs"),
        (8, "create_experiment_run_responses"),
        (9, "create_experiment_design_analyses"),
        (10, "create_experiment_response_revisions"),
        (11, "create_bayesian_study_history"),
        (12, "create_bayesian_recommendations"),
        (13, "create_attribute_control_limit_sets"),
        (14, "create_bayesian_study_lifecycle_events"),
        (15, "create_asset_user_metadata"),
    ]
    assert response_table == ("experiment_run_responses",)
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_from_schema_version_eight(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)

    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 8:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (?, ?);
                """,
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 8;")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        analysis_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'experiment_design_analyses';
            """,
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert analysis_table == ("experiment_design_analyses",)
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_v9_responses_to_immutable_revision(tmp_path) -> None:
    workspace_root = tmp_path / "workspace with spaces" / "한글 경로"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 9:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 9")

    design_id = str(uuid4())
    design_version_id = str(uuid4())
    runs = [
        ExperimentRunRecord(
            run_id=str(uuid4()),
            design_version_id=design_version_id,
            standard_order=run_order,
            run_order=run_order,
            replicate_index=1,
            center_point=False,
            block_index=None,
            factor_levels_json='{"A":1}',
            coded_levels_json='{"A":1}',
        )
        for run_order in (1, 2)
    ]
    insert_experiment_design_records(
        workspace_root,
        ExperimentDesignRecord(
            design_id=design_id,
            method_id="doe.factorial_design",
            method_version="0.2.0",
            family="two_level_full_factorial",
            name="legacy",
            status="designed",
            current_version=1,
            created_at="2026-07-14T00:00:00.000Z",
            updated_at="2026-07-14T00:00:00.000Z",
            app_version="0.1.0",
        ),
        ExperimentDesignVersionRecord(
            design_version_id=design_version_id,
            design_id=design_id,
            version_number=1,
            factors_json="[]",
            options_json="{}",
            run_count=2,
            design_sha256="a" * 64,
            created_at="2026-07-14T00:00:00.000Z",
        ),
        runs,
    )
    replace_experiment_run_response_records(
        workspace_root,
        design_id=design_id,
        design_version_id=design_version_id,
        response_name="Yield",
        records=[
            ExperimentRunResponseRecord(
                response_id=str(uuid4()),
                design_version_id=design_version_id,
                run_id=run.run_id,
                response_name="Yield",
                response_value=10.0 + run.run_order,
                unit="kg",
                created_at="2026-07-14T00:01:00.000Z",
                updated_at="2026-07-14T00:01:00.000Z",
            )
            for run in runs
        ],
        design_status="completed",
        updated_at="2026-07-14T00:01:00.000Z",
    )

    initialize_metadata_store(workspace_root)

    revision = get_current_experiment_response_revision_record(
        workspace_root, design_version_id, "Yield"
    )
    assert revision is not None
    assert revision.revision_number == 1
    assert revision.state == "completed"
    assert revision.response_sha256 == canonical_response_revision_sha256(
        design_version_id=design_version_id,
        response_name="Yield",
        unit="kg",
        values=[
            {"run_order": 1, "value": 11.0},
            {"run_order": 2, "value": 12.0},
        ],
    )
    values = list_experiment_response_revision_value_records(
        workspace_root, revision.response_revision_id
    )
    assert [(value.run_order, value.response_value) for value in values] == [
        (1, 11.0),
        (2, 12.0),
    ]


def test_initialize_metadata_store_upgrades_v10_with_empty_bayesian_foundation(
    tmp_path,
) -> None:
    workspace_root = tmp_path / "workspace with spaces" / "한글 경로"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 10:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 10")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name LIKE 'bayesian_%';
                """
            ).fetchall()
        }
        study_count = connection.execute("SELECT COUNT(*) FROM bayesian_studies").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert table_names == {
        "bayesian_studies",
        "bayesian_study_versions",
        "bayesian_trials",
        "bayesian_observation_history_revisions",
        "bayesian_observation_history_heads",
        "bayesian_recommendations",
        "bayesian_study_lifecycle_events",
    }
    assert study_count == 0
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_v11_and_preserves_bayesian_trials(
    tmp_path,
) -> None:
    workspace_root = tmp_path / "workspace"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 11:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        connection.execute(
            """
            INSERT INTO bayesian_studies (
                study_id, method_id, method_version, name, status,
                current_version, created_at, updated_at, app_version
            ) VALUES ('study', 'doe.bayesian_optimization', '0.1.0', 'legacy',
                      'active', 1, 'created', 'created', '0.1.0');
            """
        )
        connection.execute(
            """
            INSERT INTO bayesian_study_versions (
                study_version_id, study_id, version_number, schema_version,
                factors_json, objective_json, constraints_json,
                initial_design_json, definition_sha256, created_at
            ) VALUES ('version', 'study', 1, 1, '[]', '{}', '[]', '{}', ?, 'created');
            """,
            ("a" * 64,),
        )
        connection.execute(
            """
            INSERT INTO bayesian_trials (
                trial_id, study_version_id, trial_number, origin, state,
                actual_coordinates_json, normalized_coordinates_json,
                coordinates_sha256, objective_value, created_at, closed_at
            ) VALUES ('trial', 'version', 1, 'initial_design', 'completed',
                      '{"x":0.5}', '{"x":0.5}', ?, 1.25, 'created', 'closed');
            """,
            ("b" * 64,),
        )
        connection.execute(
            """
            INSERT INTO bayesian_observation_history_revisions (
                history_revision_id, study_version_id, revision_number,
                schema_version, completed_trial_ids_json, completed_trial_count,
                observation_history_sha256, previous_history_sha256, created_at
            ) VALUES ('history', 'version', 1, 1, '["trial"]', 1, ?, NULL, 'created');
            """,
            ("c" * 64,),
        )
        connection.execute(
            """
            INSERT INTO bayesian_observation_history_heads (
                study_version_id, history_revision_id, updated_at
            ) VALUES ('version', 'history', 'created');
            """
        )
        connection.execute("PRAGMA user_version = 11")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        trial = connection.execute(
            """
            SELECT trial_id, origin, state, objective_value
            FROM bayesian_trials WHERE trial_id = 'trial';
            """
        ).fetchone()
        recommendation_count = connection.execute(
            "SELECT COUNT(*) FROM bayesian_recommendations;"
        ).fetchone()[0]
        trial_table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'bayesian_trials';"
        ).fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert trial == ("trial", "initial_design", "completed", 1.25)
    assert recommendation_count == 0
    assert "'recommendation'" in trial_table_sql
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_v12_with_empty_attribute_limit_sets(
    tmp_path,
) -> None:
    workspace_root = tmp_path / "workspace with spaces" / "한글 경로"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 12:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version = 12")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        table = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'attribute_control_limit_sets';
            """
        ).fetchone()
        count = connection.execute("SELECT COUNT(*) FROM attribute_control_limit_sets;").fetchone()[
            0
        ]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert table == ("attribute_control_limit_sets",)
    assert count == 0
    assert user_version == SCHEMA_VERSION


def test_initialize_metadata_store_upgrades_v13_without_inventing_lifecycle_events(
    tmp_path,
) -> None:
    workspace_root = tmp_path / "workspace with spaces"
    db_path = metadata_db_path(workspace_root)
    db_path.parent.mkdir(parents=True)
    with sqlite3.connect(db_path) as connection:
        for migration in MIGRATIONS:
            if migration.version > 13:
                continue
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
        connection.execute(
            """
            INSERT INTO bayesian_studies (
                study_id, method_id, method_version, name, status,
                current_version, created_at, updated_at, app_version
            ) VALUES ('legacy-study', 'doe.bayesian_optimization', '0.2.1',
                      'legacy active study', 'active', 1, 'created', 'created', '0.1.0');
            """
        )
        connection.execute("PRAGMA user_version = 13")

    initialize_metadata_store(workspace_root)

    with sqlite3.connect(db_path) as connection:
        study = connection.execute(
            """
            SELECT status, predecessor_study_id
            FROM bayesian_studies WHERE study_id = 'legacy-study';
            """
        ).fetchone()
        event_count = connection.execute(
            "SELECT COUNT(*) FROM bayesian_study_lifecycle_events;"
        ).fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert study == ("active", None)
    assert event_count == 0
    assert user_version == SCHEMA_VERSION


def test_attribute_control_limit_set_metadata_round_trip_and_filters(tmp_path) -> None:
    workspace_root = tmp_path / "workspace with spaces" / "한글 경로"
    initialize_metadata_store(workspace_root)
    dataset_id = str(uuid4())
    version_id = str(uuid4())
    count_column_id = str(uuid4())
    denominator_column_id = str(uuid4())
    analysis_id = str(uuid4())
    limit_set_id = str(uuid4())
    created_at = "2026-07-16T00:00:00.000Z"
    insert_dataset_record(
        workspace_root,
        DatasetRecord(
            dataset_id=dataset_id,
            original_filename="source.csv",
            safe_filename="source.csv",
            media_type="text/csv",
            detected_format="csv",
            stored_path="workspaces/datasets/raw/source.csv",
            sha256="1" * 64,
            size_bytes=10,
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
            row_count=20,
            column_count=2,
            schema_hash="2" * 64,
            created_at=created_at,
        ),
        [
            DatasetColumnRecord(
                column_id=count_column_id,
                version_id=version_id,
                column_index=0,
                original_name="count",
                display_name="count",
                data_type="integer",
                measurement_level="count",
                role="measure",
                unit=None,
            ),
            DatasetColumnRecord(
                column_id=denominator_column_id,
                version_id=version_id,
                column_index=1,
                original_name="n",
                display_name="n",
                data_type="integer",
                measurement_level="count",
                role="measure",
                unit=None,
            ),
        ],
    )
    insert_analysis_run_record(
        workspace_root,
        AnalysisRunRecord(
            analysis_id=analysis_id,
            method_id="quality.attribute_control_chart",
            method_version="0.1.0",
            dataset_version_id=version_id,
            config_json="{}",
            status="succeeded",
            result_path="analysis/result.json",
            result_sha256="3" * 64,
            stale=False,
            created_at=created_at,
            updated_at=created_at,
            completed_at=created_at,
            app_version="0.1.0",
        ),
    )
    record = AttributeControlLimitSetRecord(
        limit_set_id=limit_set_id,
        source_analysis_id=analysis_id,
        source_dataset_version_id=version_id,
        asset_schema_version=1,
        method_id="quality.attribute_control_chart",
        source_method_version="0.1.0",
        phase2_method_version="0.2.0",
        chart_type="p",
        count_definition="defectives",
        count_column_id=count_column_id,
        denominator_column_id=denominator_column_id,
        source_schema_hash="2" * 64,
        source_canonical_sha256="4" * 64,
        source_config_sha256="5" * 64,
        source_result_sha256="3" * 64,
        filter_snapshot_sha256="6" * 64,
        row_snapshot_sha256="7" * 64,
        baseline_point_count=20,
        total_count=200,
        total_denominator=400.0,
        center_line=0.5,
        fixed_sample_size=None,
        constant_opportunity_confirmed=False,
        sigma_multiplier=3.0,
        calculation_policy="phase_2_frozen_three_sigma_v1",
        natural_bound_policy="binomial_zero_one",
        asset_path=f"quality/attribute-control-limit-sets/{limit_set_id}.json",
        asset_sha256="8" * 64,
        created_at=created_at,
        closed_at=created_at,
        app_version="0.1.0",
    )

    insert_attribute_control_limit_set_record(workspace_root, record)

    assert get_attribute_control_limit_set_record(workspace_root, limit_set_id) == record
    assert (
        get_attribute_control_limit_set_record_by_source_analysis(workspace_root, analysis_id)
        == record
    )
    assert list_attribute_control_limit_set_records(
        workspace_root,
        source_dataset_version_id=version_id,
        chart_type="p",
        limit=20,
        offset=0,
    ) == [record]
    assert (
        list_attribute_control_limit_set_records(
            workspace_root,
            source_dataset_version_id=None,
            chart_type="c",
            limit=20,
            offset=0,
        )
        == []
    )
    assert (
        count_attribute_control_limit_set_records(
            workspace_root,
            source_dataset_version_id=version_id,
            chart_type=None,
        )
        == 1
    )


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


def test_regression_model_record_round_trips_with_analysis_artifacts(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    initialize_metadata_store(workspace_root)
    dataset_id = str(uuid4())
    version_id = str(uuid4())
    analysis_id = str(uuid4())
    model_id = str(uuid4())
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
            row_count=8,
            column_count=1,
            schema_hash="2" * 64,
            created_at=created_at,
        ),
        [
            DatasetColumnRecord(
                column_id=str(uuid4()),
                version_id=version_id,
                column_index=0,
                original_name="y",
                display_name="y",
                data_type="integer",
                measurement_level="continuous",
                role="response",
                unit=None,
            ),
        ],
    )

    regression_model = RegressionModelRecord(
        model_id=model_id,
        analysis_id=analysis_id,
        dataset_version_id=version_id,
        method_id="regression.linear_model",
        method_version="0.1.0",
        manifest_path=f"workspaces/analyses/{analysis_id}/model-{model_id}.json",
        manifest_sha256="4" * 64,
        schema_hash="2" * 64,
        created_at=created_at,
        app_version="0.1.0",
    )
    insert_analysis_run_record_with_artifacts_and_regression_model(
        workspace_root,
        AnalysisRunRecord(
            analysis_id=analysis_id,
            method_id="regression.linear_model",
            method_version="0.1.0",
            dataset_version_id=version_id,
            config_json='{"schema_version":2,"roles":{},"options":{}}',
            status="succeeded",
            result_path=f"workspaces/analyses/{analysis_id}/result.json",
            result_sha256="3" * 64,
            stale=False,
            created_at=created_at,
            updated_at=created_at,
            completed_at=created_at,
            app_version="0.1.0",
        ),
        artifacts=[
            AnalysisArtifactRecord(
                artifact_id=str(uuid4()),
                analysis_id=analysis_id,
                kind="analysis_row_snapshot",
                path=f"workspaces/analyses/{analysis_id}/row_snapshot.json",
                sha256="5" * 64,
                media_type="application/json",
                created_at=created_at,
            ),
            AnalysisArtifactRecord(
                artifact_id=str(uuid4()),
                analysis_id=analysis_id,
                kind="regression_model_manifest",
                path=regression_model.manifest_path,
                sha256=regression_model.manifest_sha256,
                media_type="application/json",
                created_at=created_at,
            ),
        ],
        regression_model=regression_model,
    )

    run = get_analysis_run_record(workspace_root, analysis_id)
    stored_model = get_regression_model_record(workspace_root, model_id)

    assert run is not None
    assert run.method_id == "regression.linear_model"
    assert count_analysis_artifact_records(workspace_root, analysis_id) == 2
    assert stored_model == regression_model


def test_experiment_design_records_round_trip(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    initialize_metadata_store(workspace_root)
    design_id = str(uuid4())
    design_version_id = str(uuid4())
    created_at = "2026-07-02T00:00:00.000Z"
    factors_json = (
        '[{"high":80.0,"low":60.0,"name":"Temperature","unit":"C"},'
        '{"high":15.0,"low":5.0,"name":"Pressure","unit":"bar"}]'
    )
    options_json = (
        '{"block_count":1,"center_points":0,"randomization_seed":123,'
        '"randomize":false,"replicates":1}'
    )

    design = ExperimentDesignRecord(
        design_id=design_id,
        method_id="doe.factorial_design",
        method_version="0.1.0",
        family="two_level_full_factorial",
        name="screening design",
        status="designed",
        current_version=1,
        created_at=created_at,
        updated_at=created_at,
        app_version="0.1.0",
    )
    version = ExperimentDesignVersionRecord(
        design_version_id=design_version_id,
        design_id=design_id,
        version_number=1,
        factors_json=factors_json,
        options_json=options_json,
        run_count=2,
        design_sha256="a" * 64,
        created_at=created_at,
    )
    runs = [
        ExperimentRunRecord(
            run_id=str(uuid4()),
            design_version_id=design_version_id,
            standard_order=1,
            run_order=1,
            replicate_index=1,
            center_point=False,
            block_index=None,
            factor_levels_json='{"Pressure":5.0,"Temperature":60.0}',
            coded_levels_json='{"Pressure":-1,"Temperature":-1}',
        ),
        ExperimentRunRecord(
            run_id=str(uuid4()),
            design_version_id=design_version_id,
            standard_order=2,
            run_order=2,
            replicate_index=1,
            center_point=False,
            block_index=None,
            factor_levels_json='{"Pressure":5.0,"Temperature":80.0}',
            coded_levels_json='{"Pressure":-1,"Temperature":1}',
        ),
    ]

    insert_experiment_design_records(workspace_root, design=design, version=version, runs=runs)

    stored_design = get_experiment_design_record(workspace_root, design_id)
    stored_version = get_experiment_design_version_record(workspace_root, design_id, 1)
    stored_runs = list_experiment_run_records(workspace_root, design_version_id)

    assert stored_design == design
    assert stored_version == version
    assert stored_runs == runs

    response_updated_at = "2026-07-02T00:05:00.000Z"
    response_records = [
        ExperimentRunResponseRecord(
            response_id=str(uuid4()),
            design_version_id=design_version_id,
            run_id=runs[0].run_id,
            response_name="Yield",
            response_value=10.5,
            unit="kg",
            created_at=response_updated_at,
            updated_at=response_updated_at,
        ),
        ExperimentRunResponseRecord(
            response_id=str(uuid4()),
            design_version_id=design_version_id,
            run_id=runs[1].run_id,
            response_name="Yield",
            response_value=12.25,
            unit="kg",
            created_at=response_updated_at,
            updated_at=response_updated_at,
        ),
    ]

    replace_experiment_run_response_records(
        workspace_root,
        design_id=design_id,
        design_version_id=design_version_id,
        response_name="Yield",
        records=response_records,
        design_status="completed",
        updated_at=response_updated_at,
    )

    stored_responses = list_experiment_run_response_records(workspace_root, design_version_id)
    stored_design_after_response = get_experiment_design_record(workspace_root, design_id)
    stored_runs_after_response = list_experiment_run_records(workspace_root, design_version_id)

    assert stored_responses == response_records
    assert stored_design_after_response is not None
    assert stored_design_after_response.status == "completed"
    assert stored_design_after_response.updated_at == response_updated_at
    assert stored_runs_after_response == runs

    analysis_id = str(uuid4())
    analysis_created_at = "2026-07-02T00:06:00.000Z"
    analysis = ExperimentDesignAnalysisRecord(
        analysis_id=analysis_id,
        design_version_id=design_version_id,
        response_name="Yield",
        method_id="doe.factorial_design",
        method_version="0.2.0",
        config_json='{"schema_version":1}',
        result_json='{"analysis_schema_version":1}',
        result_sha256="b" * 64,
        response_sha256="c" * 64,
        created_at=analysis_created_at,
        app_version="0.1.0",
    )
    insert_experiment_design_analysis_record(
        workspace_root,
        design_id=design_id,
        record=analysis,
        updated_at=analysis_created_at,
    )

    optimizer = ExperimentDesignAnalysisRecord(
        analysis_id=str(uuid4()),
        design_version_id=design_version_id,
        response_name="response_optimizer",
        method_id="regression.response_optimizer",
        method_version="0.1.0",
        config_json='{"schema_version":1}',
        result_json='{"result_schema_version":1}',
        result_sha256="d" * 64,
        response_sha256="e" * 64,
        created_at="2026-07-02T00:07:00.000Z",
        app_version="0.1.0",
    )
    insert_experiment_design_analysis_record(
        workspace_root,
        design_id=design_id,
        record=optimizer,
        updated_at=optimizer.created_at,
    )

    stored_analysis = get_experiment_design_analysis_record(workspace_root, analysis_id)
    latest_analysis = get_latest_experiment_design_analysis_record(
        workspace_root,
        design_version_id,
    )
    latest_factorial_analysis = get_latest_experiment_design_analysis_record(
        workspace_root,
        design_version_id,
        method_id="doe.factorial_design",
    )
    stored_design_after_analysis = get_experiment_design_record(workspace_root, design_id)

    assert stored_analysis == analysis
    assert latest_analysis == optimizer
    assert latest_factorial_analysis == analysis
    assert stored_design_after_analysis is not None
    assert stored_design_after_analysis.status == "analyzed"
    assert stored_design_after_analysis.updated_at == optimizer.created_at


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
