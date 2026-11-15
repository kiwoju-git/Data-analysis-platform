"""Rebuild BO capacity CHECKs without rewriting historical records or artifacts."""

BO_CAPACITY_MIGRATION_SQL = """
BEGIN IMMEDIATE;
CREATE TABLE bayesian_study_lifecycle_events_v38 (
            lifecycle_event_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL UNIQUE
                REFERENCES bayesian_studies(study_id) ON DELETE RESTRICT,
            study_version_id TEXT NOT NULL
                REFERENCES bayesian_study_versions(study_version_id) ON DELETE RESTRICT,
            schema_version INTEGER NOT NULL CHECK (schema_version IN (1, 2)),
            lifecycle_revision INTEGER NOT NULL CHECK (lifecycle_revision = 1),
            previous_status TEXT NOT NULL CHECK (previous_status = 'active'),
            resulting_status TEXT NOT NULL CHECK (
                resulting_status IN ('completed', 'abandoned')
            ),
            reason_code TEXT NOT NULL CHECK (reason_code IN (
                'objective_satisfied', 'budget_reached', 'confirmation_complete',
                'unsafe_or_infeasible', 'resources_unavailable', 'study_cancelled'
            )),
            note TEXT CHECK (note IS NULL OR length(note) <= 500),
            request_id TEXT NOT NULL,
            final_history_revision_id TEXT NOT NULL
                REFERENCES bayesian_observation_history_revisions(history_revision_id)
                ON DELETE RESTRICT,
            final_observation_history_sha256 TEXT NOT NULL CHECK (
                length(final_observation_history_sha256) = 64
            ),
            final_trial_count INTEGER NOT NULL CHECK (
                final_trial_count >= 1 AND final_trial_count <= 500
            ),
            final_completed_trial_count INTEGER NOT NULL CHECK (
                final_completed_trial_count >= 0 AND
                final_completed_trial_count <= 500
            ),
            final_abandoned_trial_count INTEGER NOT NULL CHECK (
                final_abandoned_trial_count >= 0 AND
                final_abandoned_trial_count <= 500
            ),
            latest_recommendation_id TEXT
                REFERENCES bayesian_recommendations(recommendation_id) ON DELETE RESTRICT,
            latest_recommendation_batch_id TEXT
                REFERENCES bayesian_recommendation_batches(batch_id) ON DELETE RESTRICT,
            definition_sha256 TEXT NOT NULL CHECK (length(definition_sha256) = 64),
            event_sha256 TEXT NOT NULL CHECK (length(event_sha256) = 64),
            closed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            app_version TEXT NOT NULL,
            build_commit TEXT,
            UNIQUE(study_id, lifecycle_revision),
            UNIQUE(study_id, request_id)
        );
INSERT INTO bayesian_study_lifecycle_events_v38 SELECT * FROM bayesian_study_lifecycle_events;
DROP TABLE bayesian_study_lifecycle_events;
ALTER TABLE bayesian_study_lifecycle_events_v38 RENAME TO bayesian_study_lifecycle_events;
CREATE INDEX idx_bayesian_lifecycle_version
    ON bayesian_study_lifecycle_events(study_version_id, closed_at);
CREATE TABLE bayesian_candidate_revisions_v38 (
    revision_id TEXT PRIMARY KEY,
    candidate_set_id TEXT NOT NULL
        REFERENCES bayesian_candidate_sets(candidate_set_id) ON DELETE CASCADE,
    study_version_id TEXT NOT NULL,
    model_id TEXT,
    revision_number INTEGER NOT NULL CHECK(revision_number BETWEEN 1 AND 64),
    schema_version INTEGER NOT NULL CHECK(schema_version IN (1,2,3,4)),
    request_id TEXT NOT NULL,
    parent_revision_id TEXT
        REFERENCES bayesian_candidate_revisions(revision_id) ON DELETE RESTRICT,
    source_trial_count INTEGER NOT NULL CHECK(source_trial_count BETWEEN 1 AND 500),
    excluded_coordinates_sha256 TEXT NOT NULL CHECK(length(excluded_coordinates_sha256)=64),
    config_json TEXT NOT NULL,
    config_sha256 TEXT NOT NULL CHECK(length(config_sha256)=64),
    rows_json TEXT NOT NULL CHECK(length(rows_json)<=16777216),
    rows_sha256 TEXT NOT NULL CHECK(length(rows_sha256)=64),
    row_count INTEGER NOT NULL CHECK(row_count BETWEEN 1 AND 10000),
    created_at TEXT NOT NULL,
    source_history_revision_id TEXT
        REFERENCES bayesian_observation_history_revisions(history_revision_id) ON DELETE RESTRICT,
    history_sha256 TEXT CHECK(history_sha256 IS NULL OR length(history_sha256)=64),
    definition_sha256 TEXT CHECK(definition_sha256 IS NULL OR length(definition_sha256)=64),
    CHECK ((schema_version=1 AND model_id IS NOT NULL
            AND source_history_revision_id IS NULL AND history_sha256 IS NULL
            AND definition_sha256 IS NULL)
        OR (schema_version IN (2,3,4) AND source_history_revision_id IS NOT NULL
            AND history_sha256 IS NOT NULL AND definition_sha256 IS NOT NULL)),
    FOREIGN KEY(candidate_set_id,study_version_id)
        REFERENCES bayesian_candidate_sets(candidate_set_id,study_version_id) ON DELETE CASCADE,
    FOREIGN KEY(model_id,study_version_id)
        REFERENCES bayesian_planning_models(model_id,study_version_id) ON DELETE RESTRICT,
    UNIQUE(candidate_set_id,revision_number),
    UNIQUE(candidate_set_id,request_id),
    UNIQUE(study_version_id,request_id),
    UNIQUE(revision_id,candidate_set_id),
    UNIQUE(revision_id,study_version_id)
);
INSERT INTO bayesian_candidate_revisions_v38 SELECT * FROM bayesian_candidate_revisions;
DROP TABLE bayesian_candidate_revisions;
ALTER TABLE bayesian_candidate_revisions_v38 RENAME TO bayesian_candidate_revisions;
CREATE INDEX idx_bayesian_candidate_revisions_model ON bayesian_candidate_revisions(model_id);
"""
