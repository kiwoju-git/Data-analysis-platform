import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import NAMESPACE_URL, uuid5

SCHEMA_VERSION: Final = 13
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
class DatasetVersionCatalogRecord:
    version_id: str
    dataset_id: str
    original_filename: str
    version_number: int
    row_count: int
    column_count: int
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
class AttributeControlLimitSetRecord:
    limit_set_id: str
    source_analysis_id: str
    source_dataset_version_id: str
    asset_schema_version: int
    method_id: str
    source_method_version: str
    phase2_method_version: str
    chart_type: str
    count_definition: str
    count_column_id: str
    denominator_column_id: str | None
    source_schema_hash: str
    source_canonical_sha256: str
    source_config_sha256: str
    source_result_sha256: str
    filter_snapshot_sha256: str
    row_snapshot_sha256: str
    baseline_point_count: int
    total_count: int
    total_denominator: float | None
    center_line: float
    fixed_sample_size: int | None
    constant_opportunity_confirmed: bool
    sigma_multiplier: float
    calculation_policy: str
    natural_bound_policy: str
    asset_path: str
    asset_sha256: str
    created_at: str
    closed_at: str
    app_version: str


_ATTRIBUTE_CONTROL_LIMIT_SET_COLUMNS: Final = """
    limit_set_id,
    source_analysis_id,
    source_dataset_version_id,
    asset_schema_version,
    method_id,
    source_method_version,
    phase2_method_version,
    chart_type,
    count_definition,
    count_column_id,
    denominator_column_id,
    source_schema_hash,
    source_canonical_sha256,
    source_config_sha256,
    source_result_sha256,
    filter_snapshot_sha256,
    row_snapshot_sha256,
    baseline_point_count,
    total_count,
    total_denominator,
    center_line,
    fixed_sample_size,
    constant_opportunity_confirmed,
    sigma_multiplier,
    calculation_policy,
    natural_bound_policy,
    asset_path,
    asset_sha256,
    created_at,
    closed_at,
    app_version
"""


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
class ExperimentResponseRevisionRecord:
    response_revision_id: str
    design_version_id: str
    response_name: str
    unit: str | None
    revision_number: int
    state: str
    schema_version: int
    response_sha256: str
    value_count: int
    supersedes_response_revision_id: str | None
    created_at: str
    closed_at: str | None


@dataclass(frozen=True)
class ExperimentResponseRevisionValueRecord:
    response_revision_id: str
    run_id: str
    run_order: int
    response_value: float


@dataclass(frozen=True)
class ExperimentDesignAnalysisRecord:
    analysis_id: str
    design_version_id: str
    response_name: str
    method_id: str
    method_version: str
    config_json: str
    result_json: str
    result_sha256: str
    response_sha256: str
    created_at: str
    app_version: str
    response_revision_id: str | None = None
    response_revision_sha256: str | None = None


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
    Migration(
        version=9,
        name="create_experiment_design_analyses",
        sql="""
        CREATE TABLE IF NOT EXISTS experiment_design_analyses (
            analysis_id TEXT PRIMARY KEY,
            design_version_id TEXT NOT NULL
                REFERENCES experiment_design_versions(design_version_id) ON DELETE CASCADE,
            response_name TEXT NOT NULL,
            method_id TEXT NOT NULL,
            method_version TEXT NOT NULL,
            config_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            result_sha256 TEXT NOT NULL,
            response_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            app_version TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_design_analyses_version_response
        ON experiment_design_analyses(design_version_id, response_name, created_at);
        """,
    ),
    Migration(
        version=10,
        name="create_experiment_response_revisions",
        sql="""
        CREATE TABLE IF NOT EXISTS experiment_response_revisions (
            response_revision_id TEXT PRIMARY KEY,
            design_version_id TEXT NOT NULL
                REFERENCES experiment_design_versions(design_version_id) ON DELETE CASCADE,
            response_name TEXT NOT NULL,
            unit TEXT,
            revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
            state TEXT NOT NULL CHECK (state IN ('completed', 'abandoned')),
            schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
            response_sha256 TEXT NOT NULL CHECK (length(response_sha256) = 64),
            value_count INTEGER NOT NULL CHECK (value_count >= 1),
            supersedes_response_revision_id TEXT
                REFERENCES experiment_response_revisions(response_revision_id) ON DELETE RESTRICT,
            created_at TEXT NOT NULL,
            closed_at TEXT,
            UNIQUE(design_version_id, response_name, revision_number)
        );

        CREATE INDEX IF NOT EXISTS idx_experiment_response_revisions_history
        ON experiment_response_revisions(
            design_version_id,
            response_name,
            revision_number DESC
        );

        CREATE TABLE IF NOT EXISTS experiment_response_revision_values (
            response_revision_id TEXT NOT NULL
                REFERENCES experiment_response_revisions(response_revision_id) ON DELETE CASCADE,
            run_id TEXT NOT NULL
                REFERENCES experiment_runs(run_id) ON DELETE RESTRICT,
            run_order INTEGER NOT NULL CHECK (run_order >= 1),
            response_value REAL NOT NULL,
            PRIMARY KEY(response_revision_id, run_order),
            UNIQUE(response_revision_id, run_id)
        );

        CREATE TABLE IF NOT EXISTS experiment_response_heads (
            design_version_id TEXT NOT NULL
                REFERENCES experiment_design_versions(design_version_id) ON DELETE CASCADE,
            response_name TEXT NOT NULL,
            response_revision_id TEXT NOT NULL UNIQUE
                REFERENCES experiment_response_revisions(response_revision_id) ON DELETE RESTRICT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(design_version_id, response_name)
        );

        CREATE TABLE IF NOT EXISTS experiment_design_analysis_response_revisions (
            analysis_id TEXT PRIMARY KEY
                REFERENCES experiment_design_analyses(analysis_id) ON DELETE CASCADE,
            response_revision_id TEXT NOT NULL
                REFERENCES experiment_response_revisions(response_revision_id) ON DELETE RESTRICT,
            response_revision_sha256 TEXT NOT NULL CHECK (
                length(response_revision_sha256) = 64
            ),
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_response_revision_id
        ON experiment_design_analysis_response_revisions(response_revision_id);
        """,
    ),
    Migration(
        version=11,
        name="create_bayesian_study_history",
        sql="""
        CREATE TABLE IF NOT EXISTS bayesian_studies (
            study_id TEXT PRIMARY KEY,
            method_id TEXT NOT NULL,
            method_version TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'abandoned')),
            current_version INTEGER NOT NULL CHECK (current_version >= 1),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            app_version TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_bayesian_studies_method
        ON bayesian_studies(method_id, method_version, created_at);

        CREATE TABLE IF NOT EXISTS bayesian_study_versions (
            study_version_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL
                REFERENCES bayesian_studies(study_id) ON DELETE CASCADE,
            version_number INTEGER NOT NULL CHECK (version_number >= 1),
            schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
            factors_json TEXT NOT NULL,
            objective_json TEXT NOT NULL,
            constraints_json TEXT NOT NULL,
            initial_design_json TEXT NOT NULL,
            definition_sha256 TEXT NOT NULL CHECK (length(definition_sha256) = 64),
            created_at TEXT NOT NULL,
            UNIQUE(study_id, version_number)
        );

        CREATE INDEX IF NOT EXISTS idx_bayesian_study_versions_study
        ON bayesian_study_versions(study_id, version_number);

        CREATE TABLE IF NOT EXISTS bayesian_trials (
            trial_id TEXT PRIMARY KEY,
            study_version_id TEXT NOT NULL
                REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
            trial_number INTEGER NOT NULL CHECK (trial_number >= 1),
            origin TEXT NOT NULL CHECK (origin IN ('initial_design')),
            state TEXT NOT NULL CHECK (state IN ('pending', 'completed', 'abandoned')),
            actual_coordinates_json TEXT NOT NULL,
            normalized_coordinates_json TEXT NOT NULL,
            coordinates_sha256 TEXT NOT NULL CHECK (length(coordinates_sha256) = 64),
            objective_value REAL,
            created_at TEXT NOT NULL,
            closed_at TEXT,
            UNIQUE(study_version_id, trial_number)
        );

        CREATE INDEX IF NOT EXISTS idx_bayesian_trials_version_state
        ON bayesian_trials(study_version_id, state, trial_number);

        CREATE TABLE IF NOT EXISTS bayesian_observation_history_revisions (
            history_revision_id TEXT PRIMARY KEY,
            study_version_id TEXT NOT NULL
                REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
            revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
            schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
            completed_trial_ids_json TEXT NOT NULL,
            completed_trial_count INTEGER NOT NULL CHECK (completed_trial_count >= 0),
            observation_history_sha256 TEXT NOT NULL CHECK (
                length(observation_history_sha256) = 64
            ),
            previous_history_sha256 TEXT CHECK (
                previous_history_sha256 IS NULL OR length(previous_history_sha256) = 64
            ),
            created_at TEXT NOT NULL,
            UNIQUE(study_version_id, revision_number)
        );

        CREATE INDEX IF NOT EXISTS idx_bayesian_history_revisions_version
        ON bayesian_observation_history_revisions(study_version_id, revision_number DESC);

        CREATE TABLE IF NOT EXISTS bayesian_observation_history_heads (
            study_version_id TEXT PRIMARY KEY
                REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
            history_revision_id TEXT NOT NULL UNIQUE
                REFERENCES bayesian_observation_history_revisions(history_revision_id)
                ON DELETE RESTRICT,
            updated_at TEXT NOT NULL
        );
        """,
    ),
    Migration(
        version=12,
        name="create_bayesian_recommendations",
        sql="""
        ALTER TABLE bayesian_trials RENAME TO bayesian_trials_v11;

        CREATE TABLE bayesian_trials (
            trial_id TEXT PRIMARY KEY,
            study_version_id TEXT NOT NULL
                REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
            trial_number INTEGER NOT NULL CHECK (trial_number >= 1),
            origin TEXT NOT NULL CHECK (origin IN ('initial_design', 'recommendation')),
            state TEXT NOT NULL CHECK (state IN ('pending', 'completed', 'abandoned')),
            actual_coordinates_json TEXT NOT NULL,
            normalized_coordinates_json TEXT NOT NULL,
            coordinates_sha256 TEXT NOT NULL CHECK (length(coordinates_sha256) = 64),
            objective_value REAL,
            created_at TEXT NOT NULL,
            closed_at TEXT,
            UNIQUE(study_version_id, trial_number)
        );

        INSERT INTO bayesian_trials (
            trial_id, study_version_id, trial_number, origin, state,
            actual_coordinates_json, normalized_coordinates_json,
            coordinates_sha256, objective_value, created_at, closed_at
        )
        SELECT
            trial_id, study_version_id, trial_number, origin, state,
            actual_coordinates_json, normalized_coordinates_json,
            coordinates_sha256, objective_value, created_at, closed_at
        FROM bayesian_trials_v11;

        DROP TABLE bayesian_trials_v11;

        CREATE INDEX idx_bayesian_trials_version_state
        ON bayesian_trials(study_version_id, state, trial_number);

        CREATE TABLE bayesian_recommendations (
            recommendation_id TEXT PRIMARY KEY,
            study_version_id TEXT NOT NULL
                REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
            trial_id TEXT NOT NULL UNIQUE
                REFERENCES bayesian_trials(trial_id) ON DELETE RESTRICT,
            source_history_revision_id TEXT NOT NULL
                REFERENCES bayesian_observation_history_revisions(history_revision_id)
                ON DELETE RESTRICT,
            source_observation_history_sha256 TEXT NOT NULL CHECK (
                length(source_observation_history_sha256) = 64
            ),
            method_id TEXT NOT NULL,
            method_version TEXT NOT NULL,
            config_schema_version INTEGER NOT NULL CHECK (config_schema_version >= 1),
            result_schema_version INTEGER NOT NULL CHECK (result_schema_version >= 1),
            model_schema_version INTEGER NOT NULL CHECK (model_schema_version >= 1),
            config_json TEXT NOT NULL,
            config_sha256 TEXT NOT NULL CHECK (length(config_sha256) = 64),
            result_json TEXT NOT NULL,
            result_sha256 TEXT NOT NULL CHECK (length(result_sha256) = 64),
            result_payload_sha256 TEXT NOT NULL CHECK (
                length(result_payload_sha256) = 64
            ),
            created_at TEXT NOT NULL,
            app_version TEXT NOT NULL
        );

        CREATE INDEX idx_bayesian_recommendations_version_created
        ON bayesian_recommendations(study_version_id, created_at, recommendation_id);
        """,
    ),
    Migration(
        version=13,
        name="create_attribute_control_limit_sets",
        sql="""
        CREATE TABLE attribute_control_limit_sets (
            limit_set_id TEXT PRIMARY KEY,
            source_analysis_id TEXT NOT NULL UNIQUE
                REFERENCES analysis_runs(analysis_id) ON DELETE RESTRICT,
            source_dataset_version_id TEXT NOT NULL
                REFERENCES dataset_versions(version_id) ON DELETE RESTRICT,
            asset_schema_version INTEGER NOT NULL CHECK (asset_schema_version = 1),
            method_id TEXT NOT NULL CHECK (method_id = 'quality.attribute_control_chart'),
            source_method_version TEXT NOT NULL,
            phase2_method_version TEXT NOT NULL,
            chart_type TEXT NOT NULL CHECK (chart_type IN ('p', 'np', 'c', 'u')),
            count_definition TEXT NOT NULL CHECK (
                count_definition IN ('defectives', 'defects')
            ),
            count_column_id TEXT NOT NULL
                REFERENCES dataset_columns(column_id) ON DELETE RESTRICT,
            denominator_column_id TEXT
                REFERENCES dataset_columns(column_id) ON DELETE RESTRICT,
            source_schema_hash TEXT NOT NULL CHECK (length(source_schema_hash) = 64),
            source_canonical_sha256 TEXT NOT NULL CHECK (
                length(source_canonical_sha256) = 64
            ),
            source_config_sha256 TEXT NOT NULL CHECK (length(source_config_sha256) = 64),
            source_result_sha256 TEXT NOT NULL CHECK (length(source_result_sha256) = 64),
            filter_snapshot_sha256 TEXT NOT NULL CHECK (
                length(filter_snapshot_sha256) = 64
            ),
            row_snapshot_sha256 TEXT NOT NULL CHECK (length(row_snapshot_sha256) = 64),
            baseline_point_count INTEGER NOT NULL CHECK (baseline_point_count >= 2),
            total_count INTEGER NOT NULL CHECK (total_count >= 0),
            total_denominator REAL,
            center_line REAL NOT NULL,
            fixed_sample_size INTEGER,
            constant_opportunity_confirmed INTEGER NOT NULL CHECK (
                constant_opportunity_confirmed IN (0, 1)
            ),
            sigma_multiplier REAL NOT NULL CHECK (sigma_multiplier = 3.0),
            calculation_policy TEXT NOT NULL,
            natural_bound_policy TEXT NOT NULL,
            asset_path TEXT NOT NULL UNIQUE,
            asset_sha256 TEXT NOT NULL CHECK (length(asset_sha256) = 64),
            created_at TEXT NOT NULL,
            closed_at TEXT NOT NULL,
            app_version TEXT NOT NULL
        );

        CREATE INDEX idx_attribute_control_limit_sets_dataset_created
        ON attribute_control_limit_sets(
            source_dataset_version_id, created_at, limit_set_id
        );

        CREATE INDEX idx_attribute_control_limit_sets_chart_created
        ON attribute_control_limit_sets(chart_type, created_at, limit_set_id);
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
            migration_table_exists = connection.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'schema_migrations';
                """
            ).fetchone()
            if migration_table_exists is not None:
                applied = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?;",
                    (migration.version,),
                ).fetchone()
                if applied is not None:
                    continue
            connection.executescript(migration.sql)
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (?, ?);
                """,
                (migration.version, migration.name),
            )
        _backfill_legacy_response_revisions(connection)


def _backfill_legacy_response_revisions(connection: sqlite3.Connection) -> None:
    groups = connection.execute(
        """
        SELECT response.design_version_id, response.response_name
        FROM experiment_run_responses AS response
        LEFT JOIN experiment_response_heads AS head
            ON head.design_version_id = response.design_version_id
            AND head.response_name = response.response_name
        WHERE head.response_revision_id IS NULL
        GROUP BY response.design_version_id, response.response_name
        ORDER BY response.design_version_id, response.response_name;
        """
    ).fetchall()
    for design_version_id_value, response_name_value in groups:
        design_version_id = str(design_version_id_value)
        response_name = str(response_name_value)
        rows = connection.execute(
            """
            SELECT
                response.run_id,
                run.run_order,
                response.response_value,
                response.unit,
                response.created_at,
                response.updated_at
            FROM experiment_run_responses AS response
            INNER JOIN experiment_runs AS run ON run.run_id = response.run_id
            WHERE response.design_version_id = ? AND response.response_name = ?
            ORDER BY run.run_order;
            """,
            (design_version_id, response_name),
        ).fetchall()
        if not rows:
            continue
        units = {None if row[3] is None else str(row[3]) for row in rows}
        if len(units) != 1:
            continue
        unit = next(iter(units))
        values = [{"run_order": int(row[1]), "value": float(row[2])} for row in rows]
        response_sha256 = _legacy_response_sha256(
            design_version_id=design_version_id,
            response_name=response_name,
            unit=unit,
            values=values,
        )
        response_revision_id = str(
            uuid5(
                NAMESPACE_URL,
                f"datalab-response-revision:{design_version_id}:{response_name}:{response_sha256}",
            )
        )
        created_at = min(str(row[4]) for row in rows)
        closed_at = max(str(row[5]) for row in rows)
        connection.execute(
            """
            INSERT OR IGNORE INTO experiment_response_revisions (
                response_revision_id,
                design_version_id,
                response_name,
                unit,
                revision_number,
                state,
                schema_version,
                response_sha256,
                value_count,
                supersedes_response_revision_id,
                created_at,
                closed_at
            ) VALUES (?, ?, ?, ?, 1, 'completed', 1, ?, ?, NULL, ?, ?);
            """,
            (
                response_revision_id,
                design_version_id,
                response_name,
                unit,
                response_sha256,
                len(values),
                created_at,
                closed_at,
            ),
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO experiment_response_revision_values (
                response_revision_id,
                run_id,
                run_order,
                response_value
            ) VALUES (?, ?, ?, ?);
            """,
            [(response_revision_id, str(row[0]), int(row[1]), float(row[2])) for row in rows],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO experiment_response_heads (
                design_version_id,
                response_name,
                response_revision_id,
                updated_at
            ) VALUES (?, ?, ?, ?);
            """,
            (design_version_id, response_name, response_revision_id, closed_at),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO experiment_design_analysis_response_revisions (
                analysis_id,
                response_revision_id,
                response_revision_sha256,
                created_at
            )
            SELECT analysis_id, ?, ?, created_at
            FROM experiment_design_analyses
            WHERE design_version_id = ?
              AND response_name = ?
              AND response_sha256 = ?;
            """,
            (
                response_revision_id,
                response_sha256,
                design_version_id,
                response_name,
                response_sha256,
            ),
        )


def _legacy_response_sha256(
    *,
    design_version_id: str,
    response_name: str,
    unit: str | None,
    values: list[dict[str, int | float]],
) -> str:
    payload = {
        "schema_version": 1,
        "design_version_id": design_version_id,
        "response_name": response_name,
        "unit": unit,
        "values": values,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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


def count_dataset_version_catalog_records(workspace_root: Path) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute("SELECT COUNT(*) FROM dataset_versions;").fetchone()
    return 0 if row is None else _row_int(row[0])


def list_dataset_version_catalog_records(
    workspace_root: Path,
    *,
    limit: int,
    offset: int,
) -> list[DatasetVersionCatalogRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                version.version_id,
                version.dataset_id,
                dataset.original_filename,
                version.version_number,
                version.row_count,
                version.column_count,
                version.created_at
            FROM dataset_versions AS version
            INNER JOIN datasets AS dataset
                ON dataset.dataset_id = version.dataset_id
            ORDER BY version.created_at DESC, version.rowid DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        ).fetchall()

    return [
        DatasetVersionCatalogRecord(
            version_id=str(row[0]),
            dataset_id=str(row[1]),
            original_filename=str(row[2]),
            version_number=_row_int(row[3]),
            row_count=_row_int(row[4]),
            column_count=_row_int(row[5]),
            created_at=str(row[6]),
        )
        for row in rows
    ]


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


def insert_experiment_response_revision_records(
    workspace_root: Path,
    *,
    design_id: str,
    revision: ExperimentResponseRevisionRecord,
    values: list[ExperimentResponseRevisionValueRecord],
    current_records: list[ExperimentRunResponseRecord],
    updated_at: str,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO experiment_response_revisions (
                    response_revision_id,
                    design_version_id,
                    response_name,
                    unit,
                    revision_number,
                    state,
                    schema_version,
                    response_sha256,
                    value_count,
                    supersedes_response_revision_id,
                    created_at,
                    closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    revision.response_revision_id,
                    revision.design_version_id,
                    revision.response_name,
                    revision.unit,
                    revision.revision_number,
                    revision.state,
                    revision.schema_version,
                    revision.response_sha256,
                    revision.value_count,
                    revision.supersedes_response_revision_id,
                    revision.created_at,
                    revision.closed_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO experiment_response_revision_values (
                    response_revision_id,
                    run_id,
                    run_order,
                    response_value
                ) VALUES (?, ?, ?, ?);
                """,
                [
                    (
                        value.response_revision_id,
                        value.run_id,
                        value.run_order,
                        value.response_value,
                    )
                    for value in values
                ],
            )
            connection.execute(
                """
                INSERT INTO experiment_response_heads (
                    design_version_id,
                    response_name,
                    response_revision_id,
                    updated_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(design_version_id, response_name) DO UPDATE SET
                    response_revision_id = excluded.response_revision_id,
                    updated_at = excluded.updated_at;
                """,
                (
                    revision.design_version_id,
                    revision.response_name,
                    revision.response_revision_id,
                    updated_at,
                ),
            )
            connection.execute(
                """
                DELETE FROM experiment_run_responses
                WHERE design_version_id = ? AND response_name = ?;
                """,
                (revision.design_version_id, revision.response_name),
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
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
                    for record in current_records
                ],
            )
            connection.execute(
                """
                UPDATE experiment_designs
                SET status = 'completed', updated_at = ?
                WHERE design_id = ?;
                """,
                (updated_at, design_id),
            )


def get_current_experiment_response_revision_record(
    workspace_root: Path,
    design_version_id: str,
    response_name: str,
) -> ExperimentResponseRevisionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                revision.response_revision_id,
                revision.design_version_id,
                revision.response_name,
                revision.unit,
                revision.revision_number,
                revision.state,
                revision.schema_version,
                revision.response_sha256,
                revision.value_count,
                revision.supersedes_response_revision_id,
                revision.created_at,
                revision.closed_at
            FROM experiment_response_heads AS head
            INNER JOIN experiment_response_revisions AS revision
                ON revision.response_revision_id = head.response_revision_id
            WHERE head.design_version_id = ? AND head.response_name = ?;
            """,
            (design_version_id, response_name),
        ).fetchone()
    return None if row is None else _experiment_response_revision_from_row(row)


def get_experiment_response_revision_record(
    workspace_root: Path,
    response_revision_id: str,
) -> ExperimentResponseRevisionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                response_revision_id,
                design_version_id,
                response_name,
                unit,
                revision_number,
                state,
                schema_version,
                response_sha256,
                value_count,
                supersedes_response_revision_id,
                created_at,
                closed_at
            FROM experiment_response_revisions
            WHERE response_revision_id = ?;
            """,
            (response_revision_id,),
        ).fetchone()
    return None if row is None else _experiment_response_revision_from_row(row)


def list_experiment_response_revision_records(
    workspace_root: Path,
    design_version_id: str,
    response_name: str,
    *,
    offset: int,
    limit: int,
) -> list[ExperimentResponseRevisionRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT
                response_revision_id,
                design_version_id,
                response_name,
                unit,
                revision_number,
                state,
                schema_version,
                response_sha256,
                value_count,
                supersedes_response_revision_id,
                created_at,
                closed_at
            FROM experiment_response_revisions
            WHERE design_version_id = ? AND response_name = ?
            ORDER BY revision_number DESC
            LIMIT ? OFFSET ?;
            """,
            (design_version_id, response_name, limit, offset),
        ).fetchall()
    return [_experiment_response_revision_from_row(row) for row in rows]


def count_experiment_response_revision_records(
    workspace_root: Path,
    design_version_id: str,
    response_name: str,
) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM experiment_response_revisions
            WHERE design_version_id = ? AND response_name = ?;
            """,
            (design_version_id, response_name),
        ).fetchone()
    return 0 if row is None else int(row[0])


def list_experiment_response_revision_value_records(
    workspace_root: Path,
    response_revision_id: str,
) -> list[ExperimentResponseRevisionValueRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT response_revision_id, run_id, run_order, response_value
            FROM experiment_response_revision_values
            WHERE response_revision_id = ?
            ORDER BY run_order;
            """,
            (response_revision_id,),
        ).fetchall()
    return [_experiment_response_revision_value_from_row(row) for row in rows]


def abandon_experiment_response_revision_record(
    workspace_root: Path,
    response_revision_id: str,
    *,
    closed_at: str,
) -> bool:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            cursor = connection.execute(
                """
                UPDATE experiment_response_revisions
                SET state = 'abandoned', closed_at = ?
                WHERE response_revision_id = ?
                  AND state = 'completed'
                  AND NOT EXISTS (
                      SELECT 1 FROM experiment_response_heads
                      WHERE response_revision_id = ?
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM experiment_design_analysis_response_revisions
                      WHERE response_revision_id = ?
                  );
                """,
                (
                    closed_at,
                    response_revision_id,
                    response_revision_id,
                    response_revision_id,
                ),
            )
    return cursor.rowcount == 1


def insert_experiment_design_analysis_record(
    workspace_root: Path,
    *,
    design_id: str,
    record: ExperimentDesignAnalysisRecord,
    updated_at: str,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO experiment_design_analyses (
                    analysis_id,
                    design_version_id,
                    response_name,
                    method_id,
                    method_version,
                    config_json,
                    result_json,
                    result_sha256,
                    response_sha256,
                    created_at,
                    app_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    record.analysis_id,
                    record.design_version_id,
                    record.response_name,
                    record.method_id,
                    record.method_version,
                    record.config_json,
                    record.result_json,
                    record.result_sha256,
                    record.response_sha256,
                    record.created_at,
                    record.app_version,
                ),
            )
            if record.response_revision_id is not None:
                connection.execute(
                    """
                    INSERT INTO experiment_design_analysis_response_revisions (
                        analysis_id,
                        response_revision_id,
                        response_revision_sha256,
                        created_at
                    ) VALUES (?, ?, ?, ?);
                    """,
                    (
                        record.analysis_id,
                        record.response_revision_id,
                        record.response_sha256,
                        record.created_at,
                    ),
                )
            connection.execute(
                """
                UPDATE experiment_designs
                SET status = 'analyzed', updated_at = ?
                WHERE design_id = ?;
                """,
                (updated_at, design_id),
            )


def get_experiment_design_analysis_record(
    workspace_root: Path,
    analysis_id: str,
) -> ExperimentDesignAnalysisRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT
                analysis.analysis_id,
                analysis.design_version_id,
                analysis.response_name,
                analysis.method_id,
                analysis.method_version,
                analysis.config_json,
                analysis.result_json,
                analysis.result_sha256,
                analysis.response_sha256,
                analysis.created_at,
                analysis.app_version,
                dependency.response_revision_id,
                dependency.response_revision_sha256
            FROM experiment_design_analyses AS analysis
            LEFT JOIN experiment_design_analysis_response_revisions AS dependency
                ON dependency.analysis_id = analysis.analysis_id
            WHERE analysis.analysis_id = ?;
            """,
            (analysis_id,),
        ).fetchone()
    return None if row is None else _experiment_design_analysis_from_row(row)


def get_latest_experiment_design_analysis_record(
    workspace_root: Path,
    design_version_id: str,
    *,
    method_id: str | None = None,
) -> ExperimentDesignAnalysisRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        query = """
            SELECT
                analysis.analysis_id,
                analysis.design_version_id,
                analysis.response_name,
                analysis.method_id,
                analysis.method_version,
                analysis.config_json,
                analysis.result_json,
                analysis.result_sha256,
                analysis.response_sha256,
                analysis.created_at,
                analysis.app_version,
                dependency.response_revision_id,
                dependency.response_revision_sha256
            FROM experiment_design_analyses AS analysis
            LEFT JOIN experiment_design_analysis_response_revisions AS dependency
                ON dependency.analysis_id = analysis.analysis_id
            WHERE analysis.design_version_id = ?
        """
        parameters: tuple[str, ...] = (design_version_id,)
        if method_id is not None:
            query += " AND analysis.method_id = ?"
            parameters = (design_version_id, method_id)
        query += """
            ORDER BY analysis.created_at DESC, analysis.rowid DESC
            LIMIT 1;
        """
        row = connection.execute(query, parameters).fetchone()
    return None if row is None else _experiment_design_analysis_from_row(row)


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


def insert_attribute_control_limit_set_record(
    workspace_root: Path,
    record: AttributeControlLimitSetRecord,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO attribute_control_limit_sets (
                    limit_set_id,
                    source_analysis_id,
                    source_dataset_version_id,
                    asset_schema_version,
                    method_id,
                    source_method_version,
                    phase2_method_version,
                    chart_type,
                    count_definition,
                    count_column_id,
                    denominator_column_id,
                    source_schema_hash,
                    source_canonical_sha256,
                    source_config_sha256,
                    source_result_sha256,
                    filter_snapshot_sha256,
                    row_snapshot_sha256,
                    baseline_point_count,
                    total_count,
                    total_denominator,
                    center_line,
                    fixed_sample_size,
                    constant_opportunity_confirmed,
                    sigma_multiplier,
                    calculation_policy,
                    natural_bound_policy,
                    asset_path,
                    asset_sha256,
                    created_at,
                    closed_at,
                    app_version
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
                """,
                (
                    record.limit_set_id,
                    record.source_analysis_id,
                    record.source_dataset_version_id,
                    record.asset_schema_version,
                    record.method_id,
                    record.source_method_version,
                    record.phase2_method_version,
                    record.chart_type,
                    record.count_definition,
                    record.count_column_id,
                    record.denominator_column_id,
                    record.source_schema_hash,
                    record.source_canonical_sha256,
                    record.source_config_sha256,
                    record.source_result_sha256,
                    record.filter_snapshot_sha256,
                    record.row_snapshot_sha256,
                    record.baseline_point_count,
                    record.total_count,
                    record.total_denominator,
                    record.center_line,
                    record.fixed_sample_size,
                    1 if record.constant_opportunity_confirmed else 0,
                    record.sigma_multiplier,
                    record.calculation_policy,
                    record.natural_bound_policy,
                    record.asset_path,
                    record.asset_sha256,
                    record.created_at,
                    record.closed_at,
                    record.app_version,
                ),
            )


def get_attribute_control_limit_set_record(
    workspace_root: Path,
    limit_set_id: str,
) -> AttributeControlLimitSetRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            f"""
            SELECT {_ATTRIBUTE_CONTROL_LIMIT_SET_COLUMNS}
            FROM attribute_control_limit_sets
            WHERE limit_set_id = ?;
            """,
            (limit_set_id,),
        ).fetchone()
    return None if row is None else _attribute_control_limit_set_from_row(row)


def get_attribute_control_limit_set_record_by_source_analysis(
    workspace_root: Path,
    source_analysis_id: str,
) -> AttributeControlLimitSetRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            f"""
            SELECT {_ATTRIBUTE_CONTROL_LIMIT_SET_COLUMNS}
            FROM attribute_control_limit_sets
            WHERE source_analysis_id = ?;
            """,
            (source_analysis_id,),
        ).fetchone()
    return None if row is None else _attribute_control_limit_set_from_row(row)


def list_attribute_control_limit_set_records(
    workspace_root: Path,
    *,
    source_dataset_version_id: str | None,
    chart_type: str | None,
    limit: int,
    offset: int,
) -> list[AttributeControlLimitSetRecord]:
    where_conditions: list[str] = []
    parameters: list[object] = []
    if source_dataset_version_id is not None:
        where_conditions.append("source_dataset_version_id = ?")
        parameters.append(source_dataset_version_id)
    if chart_type is not None:
        where_conditions.append("chart_type = ?")
        parameters.append(chart_type)
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    parameters.extend([limit, offset])
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            f"""
            SELECT {_ATTRIBUTE_CONTROL_LIMIT_SET_COLUMNS}
            FROM attribute_control_limit_sets
            {where_clause}
            ORDER BY created_at DESC, rowid DESC
            LIMIT ? OFFSET ?;
            """,
            tuple(parameters),
        ).fetchall()
    return [_attribute_control_limit_set_from_row(row) for row in rows]


def count_attribute_control_limit_set_records(
    workspace_root: Path,
    *,
    source_dataset_version_id: str | None,
    chart_type: str | None,
) -> int:
    where_conditions: list[str] = []
    parameters: list[object] = []
    if source_dataset_version_id is not None:
        where_conditions.append("source_dataset_version_id = ?")
        parameters.append(source_dataset_version_id)
    if chart_type is not None:
        where_conditions.append("chart_type = ?")
        parameters.append(chart_type)
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM attribute_control_limit_sets
            {where_clause};
            """,
            tuple(parameters),
        ).fetchone()
    return 0 if row is None else _row_int(row[0])


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


def _attribute_control_limit_set_from_row(
    row: tuple[object, ...],
) -> AttributeControlLimitSetRecord:
    return AttributeControlLimitSetRecord(
        limit_set_id=str(row[0]),
        source_analysis_id=str(row[1]),
        source_dataset_version_id=str(row[2]),
        asset_schema_version=_row_int(row[3]),
        method_id=str(row[4]),
        source_method_version=str(row[5]),
        phase2_method_version=str(row[6]),
        chart_type=str(row[7]),
        count_definition=str(row[8]),
        count_column_id=str(row[9]),
        denominator_column_id=None if row[10] is None else str(row[10]),
        source_schema_hash=str(row[11]),
        source_canonical_sha256=str(row[12]),
        source_config_sha256=str(row[13]),
        source_result_sha256=str(row[14]),
        filter_snapshot_sha256=str(row[15]),
        row_snapshot_sha256=str(row[16]),
        baseline_point_count=_row_int(row[17]),
        total_count=_row_int(row[18]),
        total_denominator=None if row[19] is None else _row_float(row[19]),
        center_line=_row_float(row[20]),
        fixed_sample_size=None if row[21] is None else _row_int(row[21]),
        constant_opportunity_confirmed=_row_bool(row[22]),
        sigma_multiplier=_row_float(row[23]),
        calculation_policy=str(row[24]),
        natural_bound_policy=str(row[25]),
        asset_path=str(row[26]),
        asset_sha256=str(row[27]),
        created_at=str(row[28]),
        closed_at=str(row[29]),
        app_version=str(row[30]),
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


def _experiment_response_revision_from_row(
    row: tuple[object, ...],
) -> ExperimentResponseRevisionRecord:
    return ExperimentResponseRevisionRecord(
        response_revision_id=str(row[0]),
        design_version_id=str(row[1]),
        response_name=str(row[2]),
        unit=None if row[3] is None else str(row[3]),
        revision_number=_row_int(row[4]),
        state=str(row[5]),
        schema_version=_row_int(row[6]),
        response_sha256=str(row[7]),
        value_count=_row_int(row[8]),
        supersedes_response_revision_id=None if row[9] is None else str(row[9]),
        created_at=str(row[10]),
        closed_at=None if row[11] is None else str(row[11]),
    )


def _experiment_response_revision_value_from_row(
    row: tuple[object, ...],
) -> ExperimentResponseRevisionValueRecord:
    return ExperimentResponseRevisionValueRecord(
        response_revision_id=str(row[0]),
        run_id=str(row[1]),
        run_order=_row_int(row[2]),
        response_value=_row_float(row[3]),
    )


def _experiment_design_analysis_from_row(
    row: tuple[object, ...],
) -> ExperimentDesignAnalysisRecord:
    return ExperimentDesignAnalysisRecord(
        analysis_id=str(row[0]),
        design_version_id=str(row[1]),
        response_name=str(row[2]),
        method_id=str(row[3]),
        method_version=str(row[4]),
        config_json=str(row[5]),
        result_json=str(row[6]),
        result_sha256=str(row[7]),
        response_sha256=str(row[8]),
        created_at=str(row[9]),
        app_version=str(row[10]),
        response_revision_id=None if len(row) < 12 or row[11] is None else str(row[11]),
        response_revision_sha256=None if len(row) < 13 or row[12] is None else str(row[12]),
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
