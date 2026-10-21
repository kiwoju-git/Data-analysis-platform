from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.api.v1.schemas.bayesian import MAX_BAYESIAN_TRIALS
from app.storage.bayesian_studies import BayesianStorageConflict, BayesianTrialRecord, _trial_values
from app.storage.metadata import metadata_db_path


@dataclass(frozen=True)
class BayesianReplicateRequestRecord:
    study_version_id: str
    request_id: str
    parent_trial_id: str
    source_history_revision_id: str
    source_history_sha256: str
    request_sha256: str
    request_json: str
    trial_ids_json: str
    created_at: str


def list_bayesian_replicate_requests(
    workspace_root: Path,
    study_version_id: str,
) -> list[BayesianReplicateRequestRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            "SELECT study_version_id,request_id,parent_trial_id,source_history_revision_id,"
            "source_history_sha256,request_sha256,request_json,trial_ids_json,created_at "
            "FROM bayesian_replicate_requests WHERE study_version_id=? "
            "ORDER BY created_at,request_id;",
            (study_version_id,),
        ).fetchall()
    return [BayesianReplicateRequestRecord(*(str(value) for value in row)) for row in rows]


def insert_bayesian_replicates(
    workspace_root: Path,
    *,
    study_version_id: str,
    parent_trial_id: str,
    request_id: str,
    request_sha256: str,
    request_json: str,
    expected_history_revision_id: str,
    expected_history_sha256: str,
    trials: list[BayesianTrialRecord],
    total_trial_budget: int,
) -> tuple[list[str], bool]:
    connection = sqlite3.connect(metadata_db_path(workspace_root), isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys=ON;")
        connection.execute("BEGIN IMMEDIATE;")
        previous = connection.execute(
            "SELECT request_sha256, trial_ids_json FROM bayesian_replicate_requests "
            "WHERE study_version_id=? AND request_id=?;",
            (study_version_id, request_id),
        ).fetchone()
        if previous is not None:
            if previous[0] != request_sha256:
                raise BayesianStorageConflict("bayesian_replicate_request_conflict")
            identities = json.loads(previous[1])
            if (
                not isinstance(identities, list)
                or not 1 <= len(identities) <= 8
                or any(not isinstance(value, str) for value in identities)
            ):
                raise BayesianStorageConflict("bayesian_optimization_artifact_mismatch")
            connection.commit()
            return identities, True
        source = connection.execute(
            "SELECT study.status, history.history_revision_id, history.observation_history_sha256 "
            "FROM bayesian_study_versions AS version "
            "JOIN bayesian_studies AS study ON study.study_id=version.study_id "
            "JOIN bayesian_observation_history_heads AS head "
            "ON head.study_version_id=version.study_version_id "
            "JOIN bayesian_observation_history_revisions AS history "
            "ON history.history_revision_id=head.history_revision_id "
            "WHERE version.study_version_id=?;",
            (study_version_id,),
        ).fetchone()
        if source is None:
            raise BayesianStorageConflict("bayesian_optimization_artifact_mismatch")
        if source[0] != "active":
            raise BayesianStorageConflict("bayesian_study_closed")
        if (source[1], source[2]) != (expected_history_revision_id, expected_history_sha256):
            raise BayesianStorageConflict("bayesian_optimization_history_stale")
        parent = connection.execute(
            "SELECT state, actual_coordinates_json, normalized_coordinates_json, trial_number "
            "FROM bayesian_trials WHERE study_version_id=? AND trial_id=?;",
            (study_version_id, parent_trial_id),
        ).fetchone()
        if parent is None or parent[0] != "completed":
            raise BayesianStorageConflict("bayesian_replicate_parent_not_completed")
        if (
            connection.execute(
                "SELECT 1 FROM bayesian_trials WHERE study_version_id=? "
                "AND state='pending' LIMIT 1;",
                (study_version_id,),
            ).fetchone()
            is not None
        ):
            raise BayesianStorageConflict("bayesian_optimization_pending_recommendation_exists")
        count, maximum = connection.execute(
            "SELECT COUNT(*), COALESCE(MAX(trial_number),0) FROM bayesian_trials "
            "WHERE study_version_id=?;",
            (study_version_id,),
        ).fetchone()
        if count != maximum or not 1 <= len(trials) <= 8:
            raise BayesianStorageConflict("bayesian_optimization_artifact_mismatch")
        if count + len(trials) > min(total_trial_budget, MAX_BAYESIAN_TRIALS):
            raise BayesianStorageConflict("bayesian_optimization_budget_exhausted")
        if [trial.trial_number for trial in trials] != list(
            range(count + 1, count + len(trials) + 1)
        ):
            raise BayesianStorageConflict("bayesian_optimization_history_stale")
        for trial in trials:
            if (
                trial.study_version_id != study_version_id
                or trial.origin != "replicate"
                or trial.replicate_of_trial_id != parent_trial_id
                or trial.state != "pending"
                or trial.objective_value is not None
                or trial.closed_at is not None
                or trial.actual_coordinates_json != parent[1]
                or trial.normalized_coordinates_json != parent[2]
                or trial.trial_number <= parent[3]
            ):
                raise BayesianStorageConflict("bayesian_optimization_artifact_mismatch")
        connection.executemany(
            "INSERT INTO bayesian_trials (trial_id,study_version_id,trial_number,origin,state,"
            "actual_coordinates_json,normalized_coordinates_json,coordinates_sha256,objective_value,"
            "created_at,closed_at,replicate_of_trial_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?);",
            [(*_trial_values(trial), trial.replicate_of_trial_id) for trial in trials],
        )
        identities = [trial.trial_id for trial in trials]
        connection.execute(
            "INSERT INTO bayesian_replicate_requests (study_version_id,request_id,parent_trial_id,"
            "source_history_revision_id,source_history_sha256,request_sha256,request_json,"
            "trial_ids_json,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?);",
            (
                study_version_id,
                request_id,
                parent_trial_id,
                expected_history_revision_id,
                expected_history_sha256,
                request_sha256,
                request_json,
                json.dumps(identities),
                trials[0].created_at,
            ),
        )
        connection.execute(
            "UPDATE bayesian_studies SET updated_at=? WHERE study_id=("
            "SELECT study_id FROM bayesian_study_versions WHERE study_version_id=?);",
            (trials[0].created_at, study_version_id),
        )
        connection.commit()
        return identities, False
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
