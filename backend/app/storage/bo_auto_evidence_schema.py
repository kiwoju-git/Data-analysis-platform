"""Extend only CHECK tuples for numeric/mixed Auto evidence; preserve stored bytes."""

BO_AUTO_EVIDENCE_MIGRATION_SQL = """
BEGIN IMMEDIATE;
CREATE TABLE bayesian_planning_selections_v33 (
    selection_id TEXT PRIMARY KEY,
    study_version_id TEXT NOT NULL
        REFERENCES bayesian_study_versions(study_version_id) ON DELETE CASCADE,
    model_id TEXT,
    candidate_revision_id TEXT NOT NULL,
    request_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK(schema_version IN (1,2,3,4,5)),
    config_json TEXT NOT NULL,
    config_sha256 TEXT NOT NULL CHECK(length(config_sha256)=64),
    result_json TEXT NOT NULL CHECK(length(result_json)<=16777216),
    result_sha256 TEXT NOT NULL CHECK(length(result_sha256)=64),
    created_at TEXT NOT NULL,
    CHECK(schema_version IN (2,3,4,5) OR model_id IS NOT NULL),
    FOREIGN KEY(model_id,study_version_id)
        REFERENCES bayesian_planning_models(model_id,study_version_id) ON DELETE RESTRICT,
    FOREIGN KEY(candidate_revision_id,study_version_id)
        REFERENCES bayesian_candidate_revisions(revision_id,study_version_id) ON DELETE RESTRICT,
    UNIQUE(study_version_id,request_id),
    UNIQUE(selection_id,study_version_id)
);
INSERT INTO bayesian_planning_selections_v33 SELECT * FROM bayesian_planning_selections;
DROP TABLE bayesian_planning_selections;
ALTER TABLE bayesian_planning_selections_v33 RENAME TO bayesian_planning_selections;
CREATE TABLE bayesian_recommendation_batches_v33 (
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
        OR (batch_policy='source_owned_augmentation_v1'
         AND method_version='0.16.0'
         AND config_schema_version=11 AND result_schema_version=11
         AND model_schema_version=11 AND item_schema_version=4)
        OR (batch_policy='source_owned_mixed_planning_v1'
         AND method_version='0.16.0'
         AND config_schema_version=12 AND result_schema_version=12
         AND model_schema_version=12 AND item_schema_version=5)
    )
);
INSERT INTO bayesian_recommendation_batches_v33 SELECT * FROM bayesian_recommendation_batches;
DROP TABLE bayesian_recommendation_batches;
ALTER TABLE bayesian_recommendation_batches_v33 RENAME TO bayesian_recommendation_batches;
CREATE INDEX idx_bayesian_recommendation_batches_version_created
    ON bayesian_recommendation_batches(study_version_id,created_at,batch_id);
CREATE UNIQUE INDEX uq_bayesian_batch_report_owner
    ON bayesian_recommendation_batches(study_version_id,source_history_revision_id,batch_id);
"""
