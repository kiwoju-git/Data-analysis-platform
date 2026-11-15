"""Widen only fitted-model storage; retain historical JSON and owner relationships."""

BO_SNAPSHOT_CAPACITY_MIGRATION_SQL = """
BEGIN IMMEDIATE;
CREATE TABLE bayesian_planning_models_v39 (
    model_id TEXT PRIMARY KEY,
    study_version_id TEXT NOT NULL
        REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
    source_history_revision_id TEXT NOT NULL
        REFERENCES bayesian_observation_history_revisions(history_revision_id) ON DELETE RESTRICT,
    definition_sha256 TEXT NOT NULL CHECK(length(definition_sha256)=64),
    history_sha256 TEXT NOT NULL CHECK(length(history_sha256)=64),
    schema_version INTEGER NOT NULL CHECK(schema_version IN (1,2)),
    request_id TEXT NOT NULL,
    config_json TEXT NOT NULL,
    config_sha256 TEXT NOT NULL CHECK(length(config_sha256)=64),
    snapshot_json TEXT NOT NULL CHECK(length(CAST(snapshot_json AS BLOB))<=25165824),
    snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64),
    created_at TEXT NOT NULL,
    UNIQUE(study_version_id,request_id),
    UNIQUE(model_id,study_version_id)
);
INSERT INTO bayesian_planning_models_v39 SELECT * FROM bayesian_planning_models;
DROP TABLE bayesian_planning_models;
ALTER TABLE bayesian_planning_models_v39 RENAME TO bayesian_planning_models;
CREATE INDEX idx_bayesian_planning_models_owner
    ON bayesian_planning_models(study_version_id,created_at,model_id);
"""
