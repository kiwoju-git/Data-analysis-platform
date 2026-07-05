import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 8
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


@dataclass(frozen=True)
class DatasetVersionRecord:
    version_id: str
    dataset_id: str
    version_number: int
    source_sha256: str
    parsing_options_json: str
    row_count: int
    column_count: int
    schema_hash: str
    created_at: str


@dataclass(frozen=True)
class DatasetColumnRecord:
    column_id: str
    version_id: str
    column_index: int
    original_name: str
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class DatasetArtifactRecord:
    artifact_id: str
    version_id: str
    kind: str
    path: str
    sha256: str
    media_type: str
    size_bytes: int
    created_at: str


@dataclass(frozen=True)
class AnalysisRunRecord:
    analysis_id: str
    method_id: str
    method_version: str
    dataset_version_id: str | None
    config_json: str
    status: str
    result_path: str | None
    result_sha256: str | None
    stale: bool
    created_at: str
    updated_at: str
    completed_at: str | None
    app_version: str


@dataclass(frozen=True)
class AnalysisArtifactRecord:
    artifact_id: str
    analysis_id: str
    kind: str
    path: str
    sha256: str
    media_type: str
    created_at: str


@dataclass(frozen=True)
class RegressionModelRecord:
    model_id: str
    analysis_id: str
    dataset_version_id: str
    method_id: str
    method_version: str
    manifest_path: str
    manifest_sha256: str
    schema_hash: str
    created_at: str
    app_version: str


@dataclass(frozen=True)
class ExperimentDesignRecord:
    design_id: str
    method_id: str
    method_version: str
    family: str
    name: str
    status: str
    current_version: int
    created_at: str
    updated_at: str
    app_version: str


@dataclass(frozen=True)
class ExperimentDesignVersionRecord:
    design_version_id: str
    design_id: str
    version_number: int
    factors_json: str
    options_json: str
    run_count: int
    design_sha256: str
    created_at: str


@dataclass(frozen=True)
class ExperimentRunRecord:
    run_id: str
    design_version_id: str
    standard_order: int
    run_order: int
    replicate_index: int
    center_point: bool
    block_index: int | None
    factor_levels_json: str
    coded_levels_json: str


@dataclass(frozen=True)
class ExperimentRunResponseRecord:
    response_id: str
    design_version_id: str
    run_id: str
    response_name: str
    response_value: float
    unit: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    analysis_id: str | None
    job_type: str
    state: str
    progress: float
    cancel_requested: bool
    error_code: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


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
    Migration(
        version=3,
        name="create_dataset_versions_and_columns",
        sql="""
        CREATE TABLE IF NOT EXISTS dataset_versions (
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

        CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset_id
        ON dataset_versions(dataset_id, version_number);

        CREATE TABLE IF NOT EXISTS dataset_columns (
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

        CREATE INDEX IF NOT EXISTS idx_dataset_columns_version_id
        ON dataset_columns(version_id, column_index);
        """,
    ),
    Migration(
        version=4,
        name="create_analysis_runs_artifacts_and_jobs",
        sql="""
        CREATE TABLE IF NOT EXISTS analysis_runs (
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

        CREATE INDEX IF NOT EXISTS idx_analysis_runs_dataset_version_id
        ON analysis_runs(dataset_version_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_analysis_runs_method
        ON analysis_runs(method_id, method_version);

        CREATE INDEX IF NOT EXISTS idx_analysis_runs_status
        ON analysis_runs(status, updated_at);

        CREATE TABLE IF NOT EXISTS analysis_artifacts (
            artifact_id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL REFERENCES analysis_runs(analysis_id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            media_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(analysis_id, kind, path)
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_artifacts_analysis_id
        ON analysis_artifacts(analysis_id, kind);

        CREATE TABLE IF NOT EXISTS jobs (
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

        CREATE INDEX IF NOT EXISTS idx_jobs_analysis_id
        ON jobs(analysis_id);

        CREATE INDEX IF NOT EXISTS idx_jobs_state
        ON jobs(state, updated_at);
        """,
    ),
    Migration(
        version=5,
        name="create_dataset_artifacts",
        sql="""
        CREATE TABLE IF NOT EXISTS dataset_artifacts (
            artifact_id TEXT PRIMARY KEY,
            version_id TEXT NOT NULL REFERENCES dataset_versions(version_id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            media_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
            created_at TEXT NOT NULL,
            UNIQUE(version_id, kind)
        );

        CREATE INDEX IF NOT EXISTS idx_dataset_artifacts_version_id
        ON dataset_artifacts(version_id, kind);
        """,
    ),
    Migration(
        version=6,
        name="create_regression_models",
        sql="""
        CREATE TABLE IF NOT EXISTS regression_models (
            model_id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL UNIQUE
                REFERENCES analysis_runs(analysis_id) ON DELETE CASCADE,
            dataset_version_id TEXT NOT NULL
                REFERENCES dataset_versions(version_id) ON DELETE RESTRICT,
            method_id TEXT NOT NULL,
            method_version TEXT NOT NULL,
            manifest_path TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            schema_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            app_version TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_regression_models_analysis_id
        ON regression_models(analysis_id);

        CREATE INDEX IF NOT EXISTS idx_regression_models_dataset_version_id
        ON regression_models(dataset_version_id, created_at);
        """,
    ),
    Migration(
        version=7,
        name="create_experiment_designs",
        sql="""
        CREATE TABLE IF NOT EXISTS experiment_designs (
            design_id TEXT PRIMARY KEY,
            method_id TEXT NOT NULL,
            method_version TEXT NOT NULL,
            family TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN (
                    'designed',
                    'responses_in_progress',
                    'completed',
                    'analyzed'
                )
            ),
            current_version INTEGER NOT NULL CHECK (current_version >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            app_version TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_designs_method
        ON experiment_designs(method_id, method_version, created_at);

        CREATE TABLE IF NOT EXISTS experiment_design_versions (
            design_version_id TEXT PRIMARY KEY,
            design_id TEXT NOT NULL
                REFERENCES experiment_designs(design_id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL CHECK (version_number >= 1),
            factors_json TEXT NOT NULL,
            options_json TEXT NOT NULL,
            run_count INTEGER NOT NULL CHECK (run_count >= 1),
            design_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(design_id, version_number)
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_design_versions_design_id
        ON experiment_design_versions(design_id, version_number);

        CREATE TABLE IF NOT EXISTS experiment_runs (
            run_id TEXT PRIMARY KEY,
            design_version_id TEXT NOT NULL
                REFERENCES experiment_design_versions(design_version_id) ON DELETE CASCADE,
            standard_order INTEGER NOT NULL CHECK (standard_order >= 1),
            run_order INTEGER NOT NULL CHECK (run_order >= 1),
            replicate_index INTEGER NOT NULL CHECK (replicate_index >= 1),
            center_point INTEGER NOT NULL CHECK (center_point IN (0, 1)),
            block_index INTEGER CHECK (block_index IS NULL OR block_index >= 1),
            factor_levels_json TEXT NOT NULL,
            coded_levels_json TEXT NOT NULL,
            UNIQUE(design_version_id, run_order)
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_runs_design_version_id
        ON experiment_runs(design_version_id, run_order);
        """,
    ),
    Migration(
        version=8,
        name="create_experiment_run_responses",
        sql="""
        CREATE TABLE IF NOT EXISTS experiment_run_responses (
            response_id TEXT PRIMARY KEY,
            design_version_id TEXT NOT NULL
                REFERENCES experiment_design_versions(design_version_id) ON DELETE CASCADE,
            run_id TEXT NOT NULL
                REFERENCES experiment_runs(run_id) ON DELETE CASCADE,
            response_name TEXT NOT NULL,
            response_value REAL NOT NULL,
            unit TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(design_version_id, run_id, response_name)
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_run_responses_version_name
        ON experiment_run_responses(design_version_id, response_name, run_id);
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


def insert_dataset_version_record(
    workspace_root: Path,
    version: DatasetVersionRecord,
    columns: list[DatasetColumnRecord],
    artifacts: list[DatasetArtifactRecord] | None = None,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO dataset_versions (
                    version_id,
                    dataset_id,
                    version_number,
                    source_sha256,
                    parsing_options_json,
                    row_count,
                    column_count,
                    schema_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    version.version_id,
                    version.dataset_id,
                    version.version_number,
                    version.source_sha256,
                    version.parsing_options_json,
                    version.row_count,
                    version.column_count,
                    version.schema_hash,
                    version.created_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO dataset_columns (
                    column_id,
                    version_id,
                    column_index,
                    original_name,
                    display_name,
                    data_type,
                    measurement_level,
                    role,
                    unit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        column.column_id,
                        column.version_id,
                        column.column_index,
                        column.original_name,
                        column.display_name,
                        column.data_type,
                        column.measurement_level,
                        column.role,
                        column.unit,
                    )
                    for column in columns
                ],
            )
            if artifacts:
                connection.executemany(
                    """
                    INSERT INTO dataset_artifacts (
                        artifact_id,
                        version_id,
                        kind,
                        path,
                        sha256,
                        media_type,
                        size_bytes,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    [
                        (
                            artifact.artifact_id,
                            artifact.version_id,
                            artifact.kind,
                            artifact.path,
                            artifact.sha256,
                            artifact.media_type,
                            artifact.size_bytes,
                            artifact.created_at,
                        )
                        for artifact in artifacts
                    ],
                )


def list_dataset_version_records(
    workspace_root: Path,
    dataset_id: str,
) -> list[DatasetVersionRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                version_id,
                dataset_id,
                version_number,
                source_sha256,
                parsing_options_json,
                row_count,
                column_count,
                schema_hash,
                created_at
            FROM dataset_versions
            WHERE dataset_id = ?
            ORDER BY version_number;
            """,
            (dataset_id,),
        ).fetchall()

    return [_dataset_version_from_row(row) for row in rows]


def get_dataset_version_record(
    workspace_root: Path,
    version_id: str,
) -> DatasetVersionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                version_id,
                dataset_id,
                version_number,
                source_sha256,
                parsing_options_json,
                row_count,
                column_count,
                schema_hash,
                created_at
            FROM dataset_versions
            WHERE version_id = ?;
            """,
            (version_id,),
        ).fetchone()

    if row is None:
        return None

    return _dataset_version_from_row(row)


def list_dataset_column_records(
    workspace_root: Path,
    version_id: str,
) -> list[DatasetColumnRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                column_id,
                version_id,
                column_index,
                original_name,
                display_name,
                data_type,
                measurement_level,
                role,
                unit
            FROM dataset_columns
            WHERE version_id = ?
            ORDER BY column_index;
            """,
            (version_id,),
        ).fetchall()

    return [_dataset_column_from_row(row) for row in rows]


def list_dataset_artifact_records(
    workspace_root: Path,
    version_id: str,
) -> list[DatasetArtifactRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                artifact_id,
                version_id,
                kind,
                path,
                sha256,
                media_type,
                size_bytes,
                created_at
            FROM dataset_artifacts
            WHERE version_id = ?
            ORDER BY kind;
            """,
            (version_id,),
        ).fetchall()

    return [_dataset_artifact_from_row(row) for row in rows]


def get_dataset_artifact_record(
    workspace_root: Path,
    version_id: str,
    kind: str,
) -> DatasetArtifactRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                artifact_id,
                version_id,
                kind,
                path,
                sha256,
                media_type,
                size_bytes,
                created_at
            FROM dataset_artifacts
            WHERE version_id = ? AND kind = ?;
            """,
            (version_id, kind),
        ).fetchone()

    if row is None:
        return None

    return _dataset_artifact_from_row(row)


def upsert_dataset_artifact_record(workspace_root: Path, record: DatasetArtifactRecord) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            cursor = connection.execute(
                """
                UPDATE dataset_artifacts
                SET
                    artifact_id = ?,
                    path = ?,
                    sha256 = ?,
                    media_type = ?,
                    size_bytes = ?,
                    created_at = ?
                WHERE version_id = ? AND kind = ?;
                """,
                (
                    record.artifact_id,
                    record.path,
                    record.sha256,
                    record.media_type,
                    record.size_bytes,
                    record.created_at,
                    record.version_id,
                    record.kind,
                ),
            )
            if cursor.rowcount > 0:
                return

            connection.execute(
                """
                INSERT INTO dataset_artifacts (
                    artifact_id,
                    version_id,
                    kind,
                    path,
                    sha256,
                    media_type,
                    size_bytes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.artifact_id,
                    record.version_id,
                    record.kind,
                    record.path,
                    record.sha256,
                    record.media_type,
                    record.size_bytes,
                    record.created_at,
                ),
            )


def update_dataset_schema_records(
    workspace_root: Path,
    version_id: str,
    schema_hash: str,
    columns: list[DatasetColumnRecord],
    *,
    stale_updated_at: str,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                UPDATE dataset_versions
                SET schema_hash = ?
                WHERE version_id = ?;
                """,
                (schema_hash, version_id),
            )
            connection.executemany(
                """
                UPDATE dataset_columns
                SET
                    display_name = ?,
                    measurement_level = ?,
                    role = ?,
                    unit = ?
                WHERE column_id = ? AND version_id = ?;
                """,
                [
                    (
                        column.display_name,
                        column.measurement_level,
                        column.role,
                        column.unit,
                        column.column_id,
                        version_id,
                    )
                    for column in columns
                ],
            )
            connection.execute(
                """
                UPDATE analysis_runs
                SET stale = 1, updated_at = ?
                WHERE dataset_version_id = ?;
                """,
                (stale_updated_at, version_id),
            )


def insert_analysis_run_record(workspace_root: Path, record: AnalysisRunRecord) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            _insert_analysis_run(connection, record)


def insert_analysis_run_record_with_artifacts(
    workspace_root: Path,
    record: AnalysisRunRecord,
    artifacts: list[AnalysisArtifactRecord],
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            _insert_analysis_run(connection, record)
            for artifact in artifacts:
                _insert_analysis_artifact(connection, artifact)


def insert_analysis_run_record_with_artifacts_and_regression_model(
    workspace_root: Path,
    record: AnalysisRunRecord,
    artifacts: list[AnalysisArtifactRecord],
    regression_model: RegressionModelRecord,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            _insert_analysis_run(connection, record)
            for artifact in artifacts:
                _insert_analysis_artifact(connection, artifact)
            _insert_regression_model(connection, regression_model)


def insert_experiment_design_records(
    workspace_root: Path,
    design: ExperimentDesignRecord,
    version: ExperimentDesignVersionRecord,
    runs: list[ExperimentRunRecord],
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO experiment_designs (
                    design_id,
                    method_id,
                    method_version,
                    family,
                    name,
                    status,
                    current_version,
                    created_at,
                    updated_at,
                    app_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    design.design_id,
                    design.method_id,
                    design.method_version,
                    design.family,
                    design.name,
                    design.status,
                    design.current_version,
                    design.created_at,
                    design.updated_at,
                    design.app_version,
                ),
            )
            connection.execute(
                """
                INSERT INTO experiment_design_versions (
                    design_version_id,
                    design_id,
                    version_number,
                    factors_json,
                    options_json,
                    run_count,
                    design_sha256,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    version.design_version_id,
                    version.design_id,
                    version.version_number,
                    version.factors_json,
                    version.options_json,
                    version.run_count,
                    version.design_sha256,
                    version.created_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO experiment_runs (
                    run_id,
                    design_version_id,
                    standard_order,
                    run_order,
                    replicate_index,
                    center_point,
                    block_index,
                    factor_levels_json,
                    coded_levels_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        run.run_id,
                        run.design_version_id,
                        run.standard_order,
                        run.run_order,
                        run.replicate_index,
                        1 if run.center_point else 0,
                        run.block_index,
                        run.factor_levels_json,
                        run.coded_levels_json,
                    )
                    for run in runs
                ],
            )


def get_experiment_design_record(
    workspace_root: Path,
    design_id: str,
) -> ExperimentDesignRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                design_id,
                method_id,
                method_version,
                family,
                name,
                status,
                current_version,
                created_at,
                updated_at,
                app_version
            FROM experiment_designs
            WHERE design_id = ?;
            """,
            (design_id,),
        ).fetchone()

    if row is None:
        return None
    return _experiment_design_from_row(row)


def get_experiment_design_version_record(
    workspace_root: Path,
    design_id: str,
    version_number: int,
) -> ExperimentDesignVersionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                design_version_id,
                design_id,
                version_number,
                factors_json,
                options_json,
                run_count,
                design_sha256,
                created_at
            FROM experiment_design_versions
            WHERE design_id = ? AND version_number = ?;
            """,
            (design_id, version_number),
        ).fetchone()

    if row is None:
        return None
    return _experiment_design_version_from_row(row)


def list_experiment_run_records(
    workspace_root: Path,
    design_version_id: str,
) -> list[ExperimentRunRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                run_id,
                design_version_id,
                standard_order,
                run_order,
                replicate_index,
                center_point,
                block_index,
                factor_levels_json,
                coded_levels_json
            FROM experiment_runs
            WHERE design_version_id = ?
            ORDER BY run_order;
            """,
            (design_version_id,),
        ).fetchall()

    return [_experiment_run_from_row(row) for row in rows]


def replace_experiment_run_response_records(
    workspace_root: Path,
    *,
    design_id: str,
    design_version_id: str,
    response_name: str,
    records: list[ExperimentRunResponseRecord],
    design_status: str,
    updated_at: str,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                DELETE FROM experiment_run_responses
                WHERE design_version_id = ? AND response_name = ?;
                """,
                (design_version_id, response_name),
            )
            connection.executemany(
                """
                INSERT INTO experiment_run_responses (
                    response_id,
                    design_version_id,
                    run_id,
                    response_name,
                    response_value,
                    unit,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    (
                        record.response_id,
                        record.design_version_id,
                        record.run_id,
                        record.response_name,
                        record.response_value,
                        record.unit,
                        record.created_at,
                        record.updated_at,
                    )
                    for record in records
                ],
            )
            connection.execute(
                """
                UPDATE experiment_designs
                SET status = ?, updated_at = ?
                WHERE design_id = ?;
                """,
                (design_status, updated_at, design_id),
            )


def list_experiment_run_response_records(
    workspace_root: Path,
    design_version_id: str,
) -> list[ExperimentRunResponseRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                response.response_id,
                response.design_version_id,
                response.run_id,
                response.response_name,
                response.response_value,
                response.unit,
                response.created_at,
                response.updated_at
            FROM experiment_run_responses AS response
            INNER JOIN experiment_runs AS run
                ON run.run_id = response.run_id
            WHERE response.design_version_id = ?
            ORDER BY response.response_name, run.run_order;
            """,
            (design_version_id,),
        ).fetchall()

    return [_experiment_run_response_from_row(row) for row in rows]


def get_analysis_run_record(
    workspace_root: Path,
    analysis_id: str,
) -> AnalysisRunRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                analysis_id,
                method_id,
                method_version,
                dataset_version_id,
                config_json,
                status,
                result_path,
                result_sha256,
                stale,
                created_at,
                updated_at,
                completed_at,
                app_version
            FROM analysis_runs
            WHERE analysis_id = ?;
            """,
            (analysis_id,),
        ).fetchone()

    if row is None:
        return None

    return _analysis_run_from_row(row)


def list_analysis_run_records(
    workspace_root: Path,
    *,
    dataset_version_id: str | None,
    method_id: str | None,
    status: str | None,
    stale: bool | None,
    result_available: bool | None,
    limit: int,
    offset: int,
) -> list[AnalysisRunRecord]:
    where_conditions: list[str] = []
    parameters: list[object] = []

    if dataset_version_id is not None:
        where_conditions.append("dataset_version_id = ?")
        parameters.append(dataset_version_id)
    if method_id is not None:
        where_conditions.append("method_id = ?")
        parameters.append(method_id)
    if status is not None:
        where_conditions.append("status = ?")
        parameters.append(status)
    if stale is not None:
        where_conditions.append("stale = ?")
        parameters.append(1 if stale else 0)
    if result_available is not None:
        if result_available:
            where_conditions.append("result_path IS NOT NULL AND result_sha256 IS NOT NULL")
        else:
            where_conditions.append("(result_path IS NULL OR result_sha256 IS NULL)")

    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(f"({condition})" for condition in where_conditions)
    parameters.extend([limit, offset])

    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            f"""
            SELECT
                analysis_id,
                method_id,
                method_version,
                dataset_version_id,
                config_json,
                status,
                result_path,
                result_sha256,
                stale,
                created_at,
                updated_at,
                completed_at,
                app_version
            FROM analysis_runs
            {where_clause}
            ORDER BY created_at DESC, rowid DESC
            LIMIT ? OFFSET ?;
            """,
            tuple(parameters),
        ).fetchall()

    return [_analysis_run_from_row(row) for row in rows]


def get_regression_model_record(
    workspace_root: Path,
    model_id: str,
) -> RegressionModelRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                model_id,
                analysis_id,
                dataset_version_id,
                method_id,
                method_version,
                manifest_path,
                manifest_sha256,
                schema_hash,
                created_at,
                app_version
            FROM regression_models
            WHERE model_id = ?;
            """,
            (model_id,),
        ).fetchone()

    if row is None:
        return None

    return _regression_model_from_row(row)


def count_analysis_artifact_records(workspace_root: Path, analysis_id: str) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM analysis_artifacts
            WHERE analysis_id = ?;
            """,
            (analysis_id,),
        ).fetchone()

    if row is None:
        return 0
    return _row_int(row[0])


def get_analysis_artifact_record(
    workspace_root: Path,
    analysis_id: str,
    artifact_id: str,
) -> AnalysisArtifactRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                artifact_id,
                analysis_id,
                kind,
                path,
                sha256,
                media_type,
                created_at
            FROM analysis_artifacts
            WHERE analysis_id = ? AND artifact_id = ?;
            """,
            (analysis_id, artifact_id),
        ).fetchone()

    if row is None:
        return None

    return _analysis_artifact_from_row(row)


def list_analysis_artifact_records(
    workspace_root: Path,
    analysis_id: str,
) -> list[AnalysisArtifactRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                artifact_id,
                analysis_id,
                kind,
                path,
                sha256,
                media_type,
                created_at
            FROM analysis_artifacts
            WHERE analysis_id = ?
            ORDER BY created_at DESC, rowid DESC;
            """,
            (analysis_id,),
        ).fetchall()

    return [_analysis_artifact_from_row(row) for row in rows]


def update_analysis_run_status_record(
    workspace_root: Path,
    analysis_id: str,
    status: str,
    updated_at: str,
) -> AnalysisRunRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                UPDATE analysis_runs
                SET status = ?, updated_at = ?
                WHERE analysis_id = ?;
                """,
                (status, updated_at, analysis_id),
            )
            row = connection.execute(
                """
                SELECT
                    analysis_id,
                    method_id,
                    method_version,
                    dataset_version_id,
                    config_json,
                    status,
                    result_path,
                    result_sha256,
                    stale,
                    created_at,
                    updated_at,
                    completed_at,
                    app_version
                FROM analysis_runs
                WHERE analysis_id = ?;
                """,
                (analysis_id,),
            ).fetchone()

    if row is None:
        return None

    return _analysis_run_from_row(row)


def insert_analysis_artifact_record(
    workspace_root: Path,
    record: AnalysisArtifactRecord,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            _insert_analysis_artifact(connection, record)


def insert_job_record(workspace_root: Path, record: JobRecord) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id,
                    analysis_id,
                    job_type,
                    state,
                    progress,
                    cancel_requested,
                    error_code,
                    created_at,
                    updated_at,
                    completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.job_id,
                    record.analysis_id,
                    record.job_type,
                    record.state,
                    record.progress,
                    1 if record.cancel_requested else 0,
                    record.error_code,
                    record.created_at,
                    record.updated_at,
                    record.completed_at,
                ),
            )


def _insert_analysis_run(
    connection: sqlite3.Connection,
    record: AnalysisRunRecord,
) -> None:
    connection.execute(
        """
        INSERT INTO analysis_runs (
            analysis_id,
            method_id,
            method_version,
            dataset_version_id,
            config_json,
            status,
            result_path,
            result_sha256,
            stale,
            created_at,
            updated_at,
            completed_at,
            app_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            record.analysis_id,
            record.method_id,
            record.method_version,
            record.dataset_version_id,
            record.config_json,
            record.status,
            record.result_path,
            record.result_sha256,
            1 if record.stale else 0,
            record.created_at,
            record.updated_at,
            record.completed_at,
            record.app_version,
        ),
    )


def _insert_analysis_artifact(
    connection: sqlite3.Connection,
    record: AnalysisArtifactRecord,
) -> None:
    connection.execute(
        """
        INSERT INTO analysis_artifacts (
            artifact_id,
            analysis_id,
            kind,
            path,
            sha256,
            media_type,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            record.artifact_id,
            record.analysis_id,
            record.kind,
            record.path,
            record.sha256,
            record.media_type,
            record.created_at,
        ),
    )


def _insert_regression_model(
    connection: sqlite3.Connection,
    record: RegressionModelRecord,
) -> None:
    connection.execute(
        """
        INSERT INTO regression_models (
            model_id,
            analysis_id,
            dataset_version_id,
            method_id,
            method_version,
            manifest_path,
            manifest_sha256,
            schema_hash,
            created_at,
            app_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            record.model_id,
            record.analysis_id,
            record.dataset_version_id,
            record.method_id,
            record.method_version,
            record.manifest_path,
            record.manifest_sha256,
            record.schema_hash,
            record.created_at,
            record.app_version,
        ),
    )


def get_job_record(workspace_root: Path, job_id: str) -> JobRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                job_id,
                analysis_id,
                job_type,
                state,
                progress,
                cancel_requested,
                error_code,
                created_at,
                updated_at,
                completed_at
            FROM jobs
            WHERE job_id = ?;
            """,
            (job_id,),
        ).fetchone()

    if row is None:
        return None

    return _job_from_row(row)


def update_job_cancellation_record(
    workspace_root: Path,
    job_id: str,
    updated_at: str,
) -> JobRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                UPDATE jobs
                SET state = 'cancel_requested',
                    cancel_requested = 1,
                    updated_at = ?
                WHERE job_id = ?;
                """,
                (updated_at, job_id),
            )
            row = connection.execute(
                """
                SELECT
                    job_id,
                    analysis_id,
                    job_type,
                    state,
                    progress,
                    cancel_requested,
                    error_code,
                    created_at,
                    updated_at,
                    completed_at
                FROM jobs
                WHERE job_id = ?;
                """,
                (job_id,),
            ).fetchone()

    if row is None:
        return None

    return _job_from_row(row)


def _dataset_version_from_row(row: tuple[object, ...]) -> DatasetVersionRecord:
    return DatasetVersionRecord(
        version_id=str(row[0]),
        dataset_id=str(row[1]),
        version_number=_row_int(row[2]),
        source_sha256=str(row[3]),
        parsing_options_json=str(row[4]),
        row_count=_row_int(row[5]),
        column_count=_row_int(row[6]),
        schema_hash=str(row[7]),
        created_at=str(row[8]),
    )


def _dataset_column_from_row(row: tuple[object, ...]) -> DatasetColumnRecord:
    return DatasetColumnRecord(
        column_id=str(row[0]),
        version_id=str(row[1]),
        column_index=_row_int(row[2]),
        original_name=str(row[3]),
        display_name=str(row[4]),
        data_type=str(row[5]),
        measurement_level=str(row[6]),
        role=str(row[7]),
        unit=None if row[8] is None else str(row[8]),
    )


def _dataset_artifact_from_row(row: tuple[object, ...]) -> DatasetArtifactRecord:
    return DatasetArtifactRecord(
        artifact_id=str(row[0]),
        version_id=str(row[1]),
        kind=str(row[2]),
        path=str(row[3]),
        sha256=str(row[4]),
        media_type=str(row[5]),
        size_bytes=_row_int(row[6]),
        created_at=str(row[7]),
    )


def _analysis_run_from_row(row: tuple[object, ...]) -> AnalysisRunRecord:
    return AnalysisRunRecord(
        analysis_id=str(row[0]),
        method_id=str(row[1]),
        method_version=str(row[2]),
        dataset_version_id=None if row[3] is None else str(row[3]),
        config_json=str(row[4]),
        status=str(row[5]),
        result_path=None if row[6] is None else str(row[6]),
        result_sha256=None if row[7] is None else str(row[7]),
        stale=_row_bool(row[8]),
        created_at=str(row[9]),
        updated_at=str(row[10]),
        completed_at=None if row[11] is None else str(row[11]),
        app_version=str(row[12]),
    )


def _analysis_artifact_from_row(row: tuple[object, ...]) -> AnalysisArtifactRecord:
    return AnalysisArtifactRecord(
        artifact_id=str(row[0]),
        analysis_id=str(row[1]),
        kind=str(row[2]),
        path=str(row[3]),
        sha256=str(row[4]),
        media_type=str(row[5]),
        created_at=str(row[6]),
    )


def _regression_model_from_row(row: tuple[object, ...]) -> RegressionModelRecord:
    return RegressionModelRecord(
        model_id=str(row[0]),
        analysis_id=str(row[1]),
        dataset_version_id=str(row[2]),
        method_id=str(row[3]),
        method_version=str(row[4]),
        manifest_path=str(row[5]),
        manifest_sha256=str(row[6]),
        schema_hash=str(row[7]),
        created_at=str(row[8]),
        app_version=str(row[9]),
    )


def _experiment_design_from_row(row: tuple[object, ...]) -> ExperimentDesignRecord:
    return ExperimentDesignRecord(
        design_id=str(row[0]),
        method_id=str(row[1]),
        method_version=str(row[2]),
        family=str(row[3]),
        name=str(row[4]),
        status=str(row[5]),
        current_version=_row_int(row[6]),
        created_at=str(row[7]),
        updated_at=str(row[8]),
        app_version=str(row[9]),
    )


def _experiment_design_version_from_row(
    row: tuple[object, ...],
) -> ExperimentDesignVersionRecord:
    return ExperimentDesignVersionRecord(
        design_version_id=str(row[0]),
        design_id=str(row[1]),
        version_number=_row_int(row[2]),
        factors_json=str(row[3]),
        options_json=str(row[4]),
        run_count=_row_int(row[5]),
        design_sha256=str(row[6]),
        created_at=str(row[7]),
    )


def _experiment_run_from_row(row: tuple[object, ...]) -> ExperimentRunRecord:
    return ExperimentRunRecord(
        run_id=str(row[0]),
        design_version_id=str(row[1]),
        standard_order=_row_int(row[2]),
        run_order=_row_int(row[3]),
        replicate_index=_row_int(row[4]),
        center_point=_row_bool(row[5]),
        block_index=None if row[6] is None else _row_int(row[6]),
        factor_levels_json=str(row[7]),
        coded_levels_json=str(row[8]),
    )


def _experiment_run_response_from_row(row: tuple[object, ...]) -> ExperimentRunResponseRecord:
    return ExperimentRunResponseRecord(
        response_id=str(row[0]),
        design_version_id=str(row[1]),
        run_id=str(row[2]),
        response_name=str(row[3]),
        response_value=_row_float(row[4]),
        unit=None if row[5] is None else str(row[5]),
        created_at=str(row[6]),
        updated_at=str(row[7]),
    )


def _job_from_row(row: tuple[object, ...]) -> JobRecord:
    return JobRecord(
        job_id=str(row[0]),
        analysis_id=None if row[1] is None else str(row[1]),
        job_type=str(row[2]),
        state=str(row[3]),
        progress=_row_float(row[4]),
        cancel_requested=_row_bool(row[5]),
        error_code=None if row[6] is None else str(row[6]),
        created_at=str(row[7]),
        updated_at=str(row[8]),
        completed_at=None if row[9] is None else str(row[9]),
    )


def _row_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str | bytes | bytearray):
        return int(value)
    raise TypeError("SQLite row value is not an integer-compatible type")


def _row_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str | bytes | bytearray):
        return float(value)
    raise TypeError("SQLite row value is not a float-compatible type")


def _row_bool(value: object) -> bool:
    return _row_int(value) == 1
