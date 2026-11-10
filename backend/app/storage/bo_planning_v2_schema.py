"""Preserve old planning bytes while allowing source-owned model-free revisions."""

BO_PLANNING_V2_MIGRATION_SQL = """
BEGIN IMMEDIATE;
CREATE TABLE bayesian_planning_models_v32 (
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
    snapshot_json TEXT NOT NULL CHECK(length(snapshot_json)<=16777216),
    snapshot_sha256 TEXT NOT NULL CHECK(length(snapshot_sha256)=64),
    created_at TEXT NOT NULL,
    UNIQUE(study_version_id,request_id),
    UNIQUE(model_id,study_version_id)
);
INSERT INTO bayesian_planning_models_v32 SELECT * FROM bayesian_planning_models;
DROP TABLE bayesian_planning_models;
ALTER TABLE bayesian_planning_models_v32 RENAME TO bayesian_planning_models;
CREATE INDEX idx_bayesian_planning_models_owner
    ON bayesian_planning_models(study_version_id,created_at,model_id);
CREATE TABLE bayesian_candidate_revisions_v32 (
    revision_id TEXT PRIMARY KEY,
    candidate_set_id TEXT NOT NULL
        REFERENCES bayesian_candidate_sets(candidate_set_id) ON DELETE CASCADE,
    study_version_id TEXT NOT NULL,
    model_id TEXT,
    revision_number INTEGER NOT NULL CHECK(revision_number BETWEEN 1 AND 64),
    schema_version INTEGER NOT NULL CHECK(schema_version IN (1,2,3)),
    request_id TEXT NOT NULL,
    parent_revision_id TEXT
        REFERENCES bayesian_candidate_revisions(revision_id) ON DELETE RESTRICT,
    source_trial_count INTEGER NOT NULL CHECK(source_trial_count BETWEEN 1 AND 200),
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
        OR (schema_version IN (2,3) AND source_history_revision_id IS NOT NULL
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
INSERT INTO bayesian_candidate_revisions_v32
    SELECT *,NULL,NULL,NULL FROM bayesian_candidate_revisions;
DROP TABLE bayesian_candidate_revisions;
ALTER TABLE bayesian_candidate_revisions_v32 RENAME TO bayesian_candidate_revisions;
CREATE INDEX idx_bayesian_candidate_revisions_model ON bayesian_candidate_revisions(model_id);
CREATE TABLE bayesian_planning_selections_v32 (
    selection_id TEXT PRIMARY KEY,
    study_version_id TEXT NOT NULL
        REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
    model_id TEXT,
    candidate_revision_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK(schema_version IN (1,2,3)),
    config_json TEXT NOT NULL,
    config_sha256 TEXT NOT NULL CHECK(length(config_sha256)=64),
    result_json TEXT NOT NULL CHECK(length(result_json)<=16777216),
    result_sha256 TEXT NOT NULL CHECK(length(result_sha256)=64),
    created_at TEXT NOT NULL,
    CHECK(schema_version IN (2,3) OR model_id IS NOT NULL),
    FOREIGN KEY(model_id,study_version_id)
        REFERENCES bayesian_planning_models(model_id,study_version_id) ON DELETE RESTRICT,
    FOREIGN KEY(candidate_revision_id,study_version_id)
        REFERENCES bayesian_candidate_revisions(revision_id,study_version_id) ON DELETE RESTRICT,
    UNIQUE(study_version_id,request_id),
    UNIQUE(selection_id,study_version_id)
);
INSERT INTO bayesian_planning_selections_v32 SELECT * FROM bayesian_planning_selections;
DROP TABLE bayesian_planning_selections;
ALTER TABLE bayesian_planning_selections_v32 RENAME TO bayesian_planning_selections;
CREATE TABLE bayesian_recommendation_batches_v32 (
    batch_id TEXT PRIMARY KEY,
    study_version_id TEXT NOT NULL
        REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
    source_history_revision_id TEXT NOT NULL
        REFERENCES bayesian_observation_history_revisions(history_revision_id) ON DELETE RESTRICT,
    source_observation_history_sha256 TEXT NOT NULL
        CHECK(length(source_observation_history_sha256)=64),
    method_id TEXT NOT NULL,
    method_version TEXT NOT NULL,
    batch_size INTEGER NOT NULL CHECK(batch_size BETWEEN 1 AND 8),
    batch_policy TEXT NOT NULL,
    config_schema_version INTEGER NOT NULL,
    result_schema_version INTEGER NOT NULL,
    model_schema_version INTEGER NOT NULL,
    item_schema_version INTEGER NOT NULL,
    config_json TEXT NOT NULL,
    config_sha256 TEXT NOT NULL CHECK(length(config_sha256)=64),
    result_json TEXT NOT NULL,
    result_sha256 TEXT NOT NULL CHECK(length(result_sha256)=64),
    created_at TEXT NOT NULL,
    app_version TEXT NOT NULL,
    CHECK (
        (batch_policy='greedy_posterior_mean_fantasy_ei_v1'
         AND config_schema_version=1 AND result_schema_version=1
         AND model_schema_version=2 AND item_schema_version=1)
        OR (batch_policy='greedy_mc_joint_latent_improvement_v2'
         AND config_schema_version=2 AND result_schema_version=2
         AND model_schema_version=3 AND item_schema_version=2)
        OR (batch_policy='greedy_mc_joint_latent_improvement_v2'
         AND config_schema_version=3 AND result_schema_version=3
         AND model_schema_version=4 AND item_schema_version=2)
        OR (batch_policy='independent_latent_desirability_beta_ei_v1'
         AND method_version='0.9.0' AND batch_size=1
         AND config_schema_version=4 AND result_schema_version=4
         AND model_schema_version=5 AND item_schema_version=3)
        OR (batch_policy='conditional_mc_desirability_beta_marginal_v1'
         AND method_version='0.10.0'
         AND config_schema_version=5 AND result_schema_version=5
         AND model_schema_version=5 AND item_schema_version=4)
        OR (batch_policy='conditional_mc_desirability_beta_marginal_v1'
         AND method_version='0.11.0'
         AND config_schema_version=6 AND result_schema_version=6
         AND model_schema_version=6 AND item_schema_version=4)
        OR (batch_policy='conditional_mc_desirability_beta_marginal_v1'
         AND method_version='0.12.0'
         AND config_schema_version=7 AND result_schema_version=7
         AND model_schema_version=7 AND item_schema_version=4)
        OR (batch_policy='manual_ordered_fixed_model_v1'
         AND method_version='0.13.0'
         AND config_schema_version=8 AND result_schema_version=8
         AND model_schema_version=8 AND item_schema_version=4)
        OR (batch_policy='source_owned_augmentation_v1'
         AND method_version='0.14.0'
         AND config_schema_version=9 AND result_schema_version=9
         AND model_schema_version=9 AND item_schema_version=4)
        OR (batch_policy='source_owned_mixed_planning_v1'
         AND method_version='0.15.0'
         AND config_schema_version=10 AND result_schema_version=10
         AND model_schema_version=10 AND item_schema_version=5)
    )
);
INSERT INTO bayesian_recommendation_batches_v32 SELECT * FROM bayesian_recommendation_batches;
DROP TABLE bayesian_recommendation_batches;
ALTER TABLE bayesian_recommendation_batches_v32 RENAME TO bayesian_recommendation_batches;
CREATE INDEX idx_bayesian_recommendation_batches_version_created
    ON bayesian_recommendation_batches(study_version_id,created_at,batch_id);
CREATE UNIQUE INDEX uq_bayesian_batch_report_owner
    ON bayesian_recommendation_batches(study_version_id,source_history_revision_id,batch_id);
CREATE TABLE bayesian_recommendation_batch_items_v32 (
    item_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL
        REFERENCES bayesian_recommendation_batches(batch_id) ON DELETE CASCADE,
    trial_id TEXT NOT NULL UNIQUE REFERENCES bayesian_trials(trial_id) ON DELETE RESTRICT,
    rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 8),
    item_schema_version INTEGER NOT NULL CHECK(item_schema_version IN (1,2,3,4,5)),
    item_result_json TEXT NOT NULL,
    item_result_sha256 TEXT NOT NULL CHECK(length(item_result_sha256)=64),
    created_at TEXT NOT NULL,
    UNIQUE(batch_id,rank)
);
INSERT INTO bayesian_recommendation_batch_items_v32
SELECT * FROM bayesian_recommendation_batch_items;
DROP TABLE bayesian_recommendation_batch_items;
ALTER TABLE bayesian_recommendation_batch_items_v32 RENAME TO bayesian_recommendation_batch_items;
CREATE INDEX idx_bayesian_recommendation_batch_items_batch_rank
    ON bayesian_recommendation_batch_items(batch_id,rank);
"""
