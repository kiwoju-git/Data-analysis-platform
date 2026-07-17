from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.api.v1.schemas.bayesian import MAX_BAYESIAN_TRIALS, MAX_HISTORY_REVISIONS
from app.storage.metadata import metadata_db_path


class BayesianStorageConflict(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class BayesianStudyRecord:
    study_id: str
    method_id: str
    method_version: str
    name: str
    status: str
    current_version: int
    created_at: str
    updated_at: str
    app_version: str
    predecessor_study_id: str | None = None


@dataclass(frozen=True)
class BayesianStudyVersionRecord:
    study_version_id: str
    study_id: str
    version_number: int
    schema_version: int
    factors_json: str
    objective_json: str
    constraints_json: str
    initial_design_json: str
    definition_sha256: str
    created_at: str


@dataclass(frozen=True)
class BayesianTrialRecord:
    trial_id: str
    study_version_id: str
    trial_number: int
    origin: str
    state: str
    actual_coordinates_json: str
    normalized_coordinates_json: str
    coordinates_sha256: str
    objective_value: float | None
    created_at: str
    closed_at: str | None


@dataclass(frozen=True)
class BayesianHistoryRevisionRecord:
    history_revision_id: str
    study_version_id: str
    revision_number: int
    schema_version: int
    completed_trial_ids_json: str
    completed_trial_count: int
    observation_history_sha256: str
    previous_history_sha256: str | None
    created_at: str


@dataclass(frozen=True)
class BayesianRecommendationRecord:
    recommendation_id: str
    study_version_id: str
    trial_id: str
    source_history_revision_id: str
    source_observation_history_sha256: str
    method_id: str
    method_version: str
    config_schema_version: int
    result_schema_version: int
    model_schema_version: int
    config_json: str
    config_sha256: str
    result_json: str
    result_sha256: str
    result_payload_sha256: str
    created_at: str
    app_version: str


@dataclass(frozen=True)
class BayesianStudyLifecycleEventRecord:
    lifecycle_event_id: str
    study_id: str
    study_version_id: str
    schema_version: int
    lifecycle_revision: int
    previous_status: str
    resulting_status: str
    reason_code: str
    note: str | None
    request_id: str
    final_history_revision_id: str
    final_observation_history_sha256: str
    final_trial_count: int
    final_completed_trial_count: int
    final_abandoned_trial_count: int
    latest_recommendation_id: str | None
    definition_sha256: str
    event_sha256: str
    closed_at: str
    created_at: str
    app_version: str
    build_commit: str | None


@dataclass(frozen=True)
class BayesianStudyDeletionGraphRecord:
    study_id: str
    status: str
    updated_at: str
    current_version: int
    current_study_version_id: str
    current_history_revision_id: str
    lifecycle_event_id: str | None
    study_version_count: int
    trial_count: int
    history_revision_count: int
    history_head_count: int
    recommendation_count: int
    lifecycle_event_count: int
    successor_study_ids: tuple[str, ...]


def insert_bayesian_study_bundle(
    workspace_root: Path,
    *,
    study: BayesianStudyRecord,
    version: BayesianStudyVersionRecord,
    trials: list[BayesianTrialRecord],
    initial_history: BayesianHistoryRevisionRecord,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        with connection:
            connection.execute(
                """
                INSERT INTO bayesian_studies (
                    study_id, method_id, method_version, name, status,
                    current_version, created_at, updated_at, app_version,
                    predecessor_study_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    study.study_id,
                    study.method_id,
                    study.method_version,
                    study.name,
                    study.status,
                    study.current_version,
                    study.created_at,
                    study.updated_at,
                    study.app_version,
                    study.predecessor_study_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO bayesian_study_versions (
                    study_version_id, study_id, version_number, schema_version,
                    factors_json, objective_json, constraints_json,
                    initial_design_json, definition_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    version.study_version_id,
                    version.study_id,
                    version.version_number,
                    version.schema_version,
                    version.factors_json,
                    version.objective_json,
                    version.constraints_json,
                    version.initial_design_json,
                    version.definition_sha256,
                    version.created_at,
                ),
            )
            connection.executemany(
                """
                INSERT INTO bayesian_trials (
                    trial_id, study_version_id, trial_number, origin, state,
                    actual_coordinates_json, normalized_coordinates_json,
                    coordinates_sha256, objective_value, created_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                [_trial_values(trial) for trial in trials],
            )
            _insert_history_revision(connection, initial_history)
            connection.execute(
                """
                INSERT INTO bayesian_observation_history_heads (
                    study_version_id, history_revision_id, updated_at
                ) VALUES (?, ?, ?);
                """,
                (
                    version.study_version_id,
                    initial_history.history_revision_id,
                    initial_history.created_at,
                ),
            )


def get_bayesian_study_record(workspace_root: Path, study_id: str) -> BayesianStudyRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT study_id, method_id, method_version, name, status,
                   current_version, created_at, updated_at, app_version,
                   predecessor_study_id
            FROM bayesian_studies
            WHERE study_id = ?;
            """,
            (study_id,),
        ).fetchone()
    return None if row is None else _study_from_row(row)


def list_bayesian_study_records(
    workspace_root: Path, *, offset: int, limit: int
) -> list[BayesianStudyRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT study_id, method_id, method_version, name, status,
                   current_version, created_at, updated_at, app_version,
                   predecessor_study_id
            FROM bayesian_studies
            ORDER BY created_at DESC, rowid DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        ).fetchall()
    return [_study_from_row(row) for row in rows]


def count_bayesian_study_records(workspace_root: Path) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute("SELECT COUNT(*) FROM bayesian_studies;").fetchone()
    return 0 if row is None else _row_int(row[0])


def get_bayesian_study_deletion_graph_record(
    workspace_root: Path,
    study_id: str,
) -> BayesianStudyDeletionGraphRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        return _deletion_graph_from_connection(connection, study_id)


def delete_bayesian_study_graph_record(
    workspace_root: Path,
    *,
    expected: BayesianStudyDeletionGraphRecord,
) -> None:
    connection = sqlite3.connect(metadata_db_path(workspace_root), isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("BEGIN IMMEDIATE;")
        current = _deletion_graph_from_connection(connection, expected.study_id)
        if current is None:
            raise BayesianStorageConflict("bayesian_study_not_found")
        if current.status == "active":
            raise BayesianStorageConflict("bayesian_study_deletion_active")
        if current.successor_study_ids:
            raise BayesianStorageConflict("bayesian_study_deletion_referenced")
        if current != expected:
            raise BayesianStorageConflict("bayesian_study_deletion_conflict")

        lifecycle = connection.execute(
            "DELETE FROM bayesian_study_lifecycle_events WHERE study_id = ?;",
            (expected.study_id,),
        )
        recommendations = connection.execute(
            """
            DELETE FROM bayesian_recommendations
            WHERE study_version_id IN (
                SELECT study_version_id FROM bayesian_study_versions
                WHERE study_id = ?
            );
            """,
            (expected.study_id,),
        )
        history_heads = connection.execute(
            """
            DELETE FROM bayesian_observation_history_heads
            WHERE study_version_id IN (
                SELECT study_version_id FROM bayesian_study_versions
                WHERE study_id = ?
            );
            """,
            (expected.study_id,),
        )
        if (
            lifecycle.rowcount != expected.lifecycle_event_count
            or recommendations.rowcount != expected.recommendation_count
            or history_heads.rowcount != expected.history_head_count
        ):
            raise BayesianStorageConflict("bayesian_study_deletion_conflict")
        deleted = connection.execute(
            "DELETE FROM bayesian_studies WHERE study_id = ?;",
            (expected.study_id,),
        )
        if deleted.rowcount != 1:
            raise BayesianStorageConflict("bayesian_study_deletion_conflict")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_bayesian_study_version_record(
    workspace_root: Path, *, study_id: str, version_number: int
) -> BayesianStudyVersionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT study_version_id, study_id, version_number, schema_version,
                   factors_json, objective_json, constraints_json,
                   initial_design_json, definition_sha256, created_at
            FROM bayesian_study_versions
            WHERE study_id = ? AND version_number = ?;
            """,
            (study_id, version_number),
        ).fetchone()
    return None if row is None else _version_from_row(row)


def get_bayesian_trial_record(workspace_root: Path, trial_id: str) -> BayesianTrialRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT trial_id, study_version_id, trial_number, origin, state,
                   actual_coordinates_json, normalized_coordinates_json,
                   coordinates_sha256, objective_value, created_at, closed_at
            FROM bayesian_trials
            WHERE trial_id = ?;
            """,
            (trial_id,),
        ).fetchone()
    return None if row is None else _trial_from_row(row)


def list_bayesian_trial_records(
    workspace_root: Path,
    study_version_id: str,
    *,
    offset: int = 0,
    limit: int = MAX_BAYESIAN_TRIALS,
) -> list[BayesianTrialRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT trial_id, study_version_id, trial_number, origin, state,
                   actual_coordinates_json, normalized_coordinates_json,
                   coordinates_sha256, objective_value, created_at, closed_at
            FROM bayesian_trials
            WHERE study_version_id = ?
            ORDER BY trial_number
            LIMIT ? OFFSET ?;
            """,
            (study_version_id, limit, offset),
        ).fetchall()
    return [_trial_from_row(row) for row in rows]


def count_bayesian_trial_records(workspace_root: Path, study_version_id: str) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM bayesian_trials WHERE study_version_id = ?;",
            (study_version_id,),
        ).fetchone()
    return 0 if row is None else _row_int(row[0])


def insert_bayesian_recommendation_bundle(
    workspace_root: Path,
    *,
    trial: BayesianTrialRecord,
    recommendation: BayesianRecommendationRecord,
    expected_history_revision_id: str,
    expected_history_sha256: str,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("BEGIN IMMEDIATE;")
        with connection:
            if not _study_is_active(connection, recommendation.study_version_id):
                raise BayesianStorageConflict("bayesian_study_closed")
            head = connection.execute(
                """
                SELECT revision.history_revision_id,
                       revision.observation_history_sha256
                FROM bayesian_observation_history_heads AS head
                INNER JOIN bayesian_observation_history_revisions AS revision
                    ON revision.history_revision_id = head.history_revision_id
                WHERE head.study_version_id = ?;
                """,
                (recommendation.study_version_id,),
            ).fetchone()
            if head is None or (
                str(head[0]) != expected_history_revision_id
                or str(head[1]) != expected_history_sha256
            ):
                raise BayesianStorageConflict("bayesian_optimization_history_stale")
            pending = connection.execute(
                """
                SELECT 1
                FROM bayesian_recommendations AS recommendation
                INNER JOIN bayesian_trials AS trial
                    ON trial.trial_id = recommendation.trial_id
                WHERE recommendation.study_version_id = ?
                  AND trial.state = 'pending'
                LIMIT 1;
                """,
                (recommendation.study_version_id,),
            ).fetchone()
            if pending is not None:
                raise BayesianStorageConflict("bayesian_optimization_pending_recommendation_exists")
            row = connection.execute(
                """
                SELECT COALESCE(MAX(trial_number), 0)
                FROM bayesian_trials
                WHERE study_version_id = ?;
                """,
                (recommendation.study_version_id,),
            ).fetchone()
            current_trial_count = 0 if row is None else _row_int(row[0])
            if current_trial_count >= MAX_BAYESIAN_TRIALS:
                raise BayesianStorageConflict("bayesian_optimization_budget_exhausted")
            if current_trial_count + 1 != trial.trial_number:
                raise BayesianStorageConflict("bayesian_optimization_artifact_mismatch")
            connection.execute(
                """
                INSERT INTO bayesian_trials (
                    trial_id, study_version_id, trial_number, origin, state,
                    actual_coordinates_json, normalized_coordinates_json,
                    coordinates_sha256, objective_value, created_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                _trial_values(trial),
            )
            connection.execute(
                """
                INSERT INTO bayesian_recommendations (
                    recommendation_id, study_version_id, trial_id,
                    source_history_revision_id,
                    source_observation_history_sha256,
                    method_id, method_version, config_schema_version,
                    result_schema_version, model_schema_version,
                    config_json, config_sha256, result_json, result_sha256,
                    result_payload_sha256, created_at, app_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                _recommendation_values(recommendation),
            )
            connection.execute(
                """
                UPDATE bayesian_studies
                SET updated_at = ?
                WHERE study_id = (
                    SELECT study_id FROM bayesian_study_versions
                    WHERE study_version_id = ?
                );
                """,
                (recommendation.created_at, recommendation.study_version_id),
            )


def get_bayesian_recommendation_record(
    workspace_root: Path, recommendation_id: str
) -> BayesianRecommendationRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT recommendation_id, study_version_id, trial_id,
                   source_history_revision_id,
                   source_observation_history_sha256,
                   method_id, method_version, config_schema_version,
                   result_schema_version, model_schema_version,
                   config_json, config_sha256, result_json, result_sha256,
                   result_payload_sha256, created_at, app_version
            FROM bayesian_recommendations
            WHERE recommendation_id = ?;
            """,
            (recommendation_id,),
        ).fetchone()
    return None if row is None else _recommendation_from_row(row)


def get_bayesian_recommendation_record_for_trial(
    workspace_root: Path, trial_id: str
) -> BayesianRecommendationRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT recommendation_id, study_version_id, trial_id,
                   source_history_revision_id,
                   source_observation_history_sha256,
                   method_id, method_version, config_schema_version,
                   result_schema_version, model_schema_version,
                   config_json, config_sha256, result_json, result_sha256,
                   result_payload_sha256, created_at, app_version
            FROM bayesian_recommendations
            WHERE trial_id = ?;
            """,
            (trial_id,),
        ).fetchone()
    return None if row is None else _recommendation_from_row(row)


def list_bayesian_recommendation_records(
    workspace_root: Path,
    study_version_id: str,
    *,
    offset: int = 0,
    limit: int = MAX_BAYESIAN_TRIALS,
) -> list[BayesianRecommendationRecord]:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            """
            SELECT recommendation_id, study_version_id, trial_id,
                   source_history_revision_id,
                   source_observation_history_sha256,
                   method_id, method_version, config_schema_version,
                   result_schema_version, model_schema_version,
                   config_json, config_sha256, result_json, result_sha256,
                   result_payload_sha256, created_at, app_version
            FROM bayesian_recommendations
            WHERE study_version_id = ?
            ORDER BY created_at, recommendation_id
            LIMIT ? OFFSET ?;
            """,
            (study_version_id, limit, offset),
        ).fetchall()
    return [_recommendation_from_row(row) for row in rows]


def get_latest_bayesian_recommendation_record(
    workspace_root: Path,
    study_version_id: str,
) -> BayesianRecommendationRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT recommendation_id, study_version_id, trial_id,
                   source_history_revision_id,
                   source_observation_history_sha256,
                   method_id, method_version, config_schema_version,
                   result_schema_version, model_schema_version,
                   config_json, config_sha256, result_json, result_sha256,
                   result_payload_sha256, created_at, app_version
            FROM bayesian_recommendations
            WHERE study_version_id = ?
            ORDER BY rowid DESC
            LIMIT 1;
            """,
            (study_version_id,),
        ).fetchone()
    return None if row is None else _recommendation_from_row(row)


def count_bayesian_recommendation_records(workspace_root: Path, study_version_id: str) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM bayesian_recommendations WHERE study_version_id = ?;",
            (study_version_id,),
        ).fetchone()
    return 0 if row is None else _row_int(row[0])


def get_bayesian_study_lifecycle_event_record(
    workspace_root: Path, study_id: str
) -> BayesianStudyLifecycleEventRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT lifecycle_event_id, study_id, study_version_id,
                   schema_version, lifecycle_revision, previous_status,
                   resulting_status, reason_code, note, request_id,
                   final_history_revision_id,
                   final_observation_history_sha256, final_trial_count,
                   final_completed_trial_count, final_abandoned_trial_count,
                   latest_recommendation_id, definition_sha256, event_sha256,
                   closed_at, created_at, app_version, build_commit
            FROM bayesian_study_lifecycle_events
            WHERE study_id = ?;
            """,
            (study_id,),
        ).fetchone()
    return None if row is None else _lifecycle_event_from_row(row)


def close_bayesian_study_record(
    workspace_root: Path,
    *,
    event: BayesianStudyLifecycleEventRecord,
    expected_current_version: int,
) -> BayesianStudyLifecycleEventRecord:
    connection = sqlite3.connect(metadata_db_path(workspace_root), isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("BEGIN IMMEDIATE;")
        existing = connection.execute(
            """
            SELECT lifecycle_event_id, study_id, study_version_id,
                   schema_version, lifecycle_revision, previous_status,
                   resulting_status, reason_code, note, request_id,
                   final_history_revision_id,
                   final_observation_history_sha256, final_trial_count,
                   final_completed_trial_count, final_abandoned_trial_count,
                   latest_recommendation_id, definition_sha256, event_sha256,
                   closed_at, created_at, app_version, build_commit
            FROM bayesian_study_lifecycle_events
            WHERE study_id = ?;
            """,
            (event.study_id,),
        ).fetchone()
        if existing is not None:
            connection.commit()
            return _lifecycle_event_from_row(existing)
        study = connection.execute(
            """
            SELECT status, current_version
            FROM bayesian_studies
            WHERE study_id = ?;
            """,
            (event.study_id,),
        ).fetchone()
        if study is None or str(study[0]) != "active":
            raise BayesianStorageConflict("bayesian_study_closed")
        if _row_int(study[1]) != expected_current_version:
            raise BayesianStorageConflict("bayesian_study_close_conflict")
        head = connection.execute(
            """
            SELECT head.history_revision_id,
                   revision.observation_history_sha256
            FROM bayesian_observation_history_heads AS head
            INNER JOIN bayesian_observation_history_revisions AS revision
                ON revision.history_revision_id = head.history_revision_id
            WHERE head.study_version_id = ?;
            """,
            (event.study_version_id,),
        ).fetchone()
        if head is None or (
            str(head[0]) != event.final_history_revision_id
            or str(head[1]) != event.final_observation_history_sha256
        ):
            raise BayesianStorageConflict("bayesian_study_close_conflict")
        counts = connection.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN state = 'pending' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN state = 'abandoned' THEN 1 ELSE 0 END)
            FROM bayesian_trials
            WHERE study_version_id = ?;
            """,
            (event.study_version_id,),
        ).fetchone()
        if counts is None:
            raise BayesianStorageConflict("bayesian_study_close_conflict")
        trial_count = _row_int(counts[0])
        pending_count = 0 if counts[1] is None else _row_int(counts[1])
        completed_count = 0 if counts[2] is None else _row_int(counts[2])
        abandoned_count = 0 if counts[3] is None else _row_int(counts[3])
        latest = connection.execute(
            """
            SELECT recommendation_id
            FROM bayesian_recommendations
            WHERE study_version_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1;
            """,
            (event.study_version_id,),
        ).fetchone()
        latest_id = None if latest is None else str(latest[0])
        if (
            pending_count != 0
            or trial_count != event.final_trial_count
            or completed_count != event.final_completed_trial_count
            or abandoned_count != event.final_abandoned_trial_count
            or latest_id != event.latest_recommendation_id
        ):
            raise BayesianStorageConflict("bayesian_study_close_conflict")
        cursor = connection.execute(
            """
            UPDATE bayesian_studies
            SET status = ?, updated_at = ?
            WHERE study_id = ? AND status = 'active' AND current_version = ?;
            """,
            (
                event.resulting_status,
                event.closed_at,
                event.study_id,
                expected_current_version,
            ),
        )
        if cursor.rowcount != 1:
            raise BayesianStorageConflict("bayesian_study_close_conflict")
        connection.execute(
            """
            INSERT INTO bayesian_study_lifecycle_events (
                lifecycle_event_id, study_id, study_version_id,
                schema_version, lifecycle_revision, previous_status,
                resulting_status, reason_code, note, request_id,
                final_history_revision_id,
                final_observation_history_sha256, final_trial_count,
                final_completed_trial_count, final_abandoned_trial_count,
                latest_recommendation_id, definition_sha256, event_sha256,
                closed_at, created_at, app_version, build_commit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            _lifecycle_event_values(event),
        )
        connection.commit()
        return event
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_current_bayesian_history_revision_record(
    workspace_root: Path, study_version_id: str
) -> BayesianHistoryRevisionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT revision.history_revision_id, revision.study_version_id,
                   revision.revision_number, revision.schema_version,
                   revision.completed_trial_ids_json,
                   revision.completed_trial_count,
                   revision.observation_history_sha256,
                   revision.previous_history_sha256,
                   revision.created_at
            FROM bayesian_observation_history_heads AS head
            INNER JOIN bayesian_observation_history_revisions AS revision
                ON revision.history_revision_id = head.history_revision_id
            WHERE head.study_version_id = ?;
            """,
            (study_version_id,),
        ).fetchone()
    return None if row is None else _history_from_row(row)


def get_bayesian_history_revision_record(
    workspace_root: Path, history_revision_id: str
) -> BayesianHistoryRevisionRecord | None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT history_revision_id, study_version_id, revision_number,
                   schema_version, completed_trial_ids_json,
                   completed_trial_count, observation_history_sha256,
                   previous_history_sha256, created_at
            FROM bayesian_observation_history_revisions
            WHERE history_revision_id = ?;
            """,
            (history_revision_id,),
        ).fetchone()
    return None if row is None else _history_from_row(row)


def list_bayesian_history_revision_records(
    workspace_root: Path,
    study_version_id: str,
    *,
    offset: int = 0,
    limit: int = MAX_HISTORY_REVISIONS,
    ascending: bool = False,
) -> list[BayesianHistoryRevisionRecord]:
    direction = "ASC" if ascending else "DESC"
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        rows = connection.execute(
            f"""
            SELECT history_revision_id, study_version_id, revision_number,
                   schema_version, completed_trial_ids_json,
                   completed_trial_count, observation_history_sha256,
                   previous_history_sha256, created_at
            FROM bayesian_observation_history_revisions
            WHERE study_version_id = ?
            ORDER BY revision_number {direction}
            LIMIT ? OFFSET ?;
            """,
            (study_version_id, limit, offset),
        ).fetchall()
    return [_history_from_row(row) for row in rows]


def count_bayesian_history_revision_records(workspace_root: Path, study_version_id: str) -> int:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM bayesian_observation_history_revisions
            WHERE study_version_id = ?;
            """,
            (study_version_id,),
        ).fetchone()
    return 0 if row is None else _row_int(row[0])


def complete_bayesian_trial_record(
    workspace_root: Path,
    *,
    trial_id: str,
    objective_value: float,
    closed_at: str,
    expected_history_revision_id: str,
    new_history: BayesianHistoryRevisionRecord,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("BEGIN IMMEDIATE;")
        with connection:
            if not _study_is_active(connection, new_history.study_version_id):
                raise BayesianStorageConflict("bayesian_study_closed")
            history_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM bayesian_observation_history_revisions
                WHERE study_version_id = ?;
                """,
                (new_history.study_version_id,),
            ).fetchone()
            if history_count is None or _row_int(history_count[0]) >= MAX_HISTORY_REVISIONS:
                raise BayesianStorageConflict("bayesian_observation_limit_reached")
            head = connection.execute(
                """
                SELECT history_revision_id
                FROM bayesian_observation_history_heads
                WHERE study_version_id = ?;
                """,
                (new_history.study_version_id,),
            ).fetchone()
            if head is None or str(head[0]) != expected_history_revision_id:
                raise BayesianStorageConflict("history head changed")
            cursor = connection.execute(
                """
                UPDATE bayesian_trials
                SET state = 'completed', objective_value = ?, closed_at = ?
                WHERE trial_id = ? AND study_version_id = ? AND state = 'pending';
                """,
                (
                    objective_value,
                    closed_at,
                    trial_id,
                    new_history.study_version_id,
                ),
            )
            if cursor.rowcount != 1:
                raise BayesianStorageConflict("trial is no longer pending")
            _insert_history_revision(connection, new_history)
            cursor = connection.execute(
                """
                UPDATE bayesian_observation_history_heads
                SET history_revision_id = ?, updated_at = ?
                WHERE study_version_id = ? AND history_revision_id = ?;
                """,
                (
                    new_history.history_revision_id,
                    new_history.created_at,
                    new_history.study_version_id,
                    expected_history_revision_id,
                ),
            )
            if cursor.rowcount != 1:
                raise BayesianStorageConflict("history head changed")
            connection.execute(
                """
                UPDATE bayesian_studies
                SET updated_at = ?
                WHERE study_id = (
                    SELECT study_id FROM bayesian_study_versions
                    WHERE study_version_id = ?
                );
                """,
                (closed_at, new_history.study_version_id),
            )


def abandon_bayesian_trial_record(
    workspace_root: Path,
    *,
    trial_id: str,
    study_version_id: str,
    closed_at: str,
    required_minimum_completed_observations: int | None = None,
    expected_history_revision_id: str | None = None,
) -> None:
    with sqlite3.connect(metadata_db_path(workspace_root)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("BEGIN IMMEDIATE;")
        with connection:
            if not _study_is_active(connection, study_version_id):
                raise BayesianStorageConflict("bayesian_study_closed")
            if expected_history_revision_id is not None:
                head = connection.execute(
                    """
                    SELECT history_revision_id
                    FROM bayesian_observation_history_heads
                    WHERE study_version_id = ?;
                    """,
                    (study_version_id,),
                ).fetchone()
                if head is None or str(head[0]) != expected_history_revision_id:
                    raise BayesianStorageConflict("bayesian_observation_history_stale")
            if required_minimum_completed_observations is not None:
                counts = connection.execute(
                    """
                    SELECT
                        SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN origin = 'initial_design'
                                      AND state = 'pending'
                                      AND trial_id <> ? THEN 1 ELSE 0 END)
                    FROM bayesian_trials
                    WHERE study_version_id = ?;
                    """,
                    (trial_id, study_version_id),
                ).fetchone()
                completed = 0 if counts is None or counts[0] is None else _row_int(counts[0])
                remaining_initial = (
                    0 if counts is None or counts[1] is None else _row_int(counts[1])
                )
                if completed + remaining_initial < required_minimum_completed_observations:
                    raise BayesianStorageConflict("bayesian_trial_abandon_would_strand_study")
            cursor = connection.execute(
                """
                UPDATE bayesian_trials
                SET state = 'abandoned', closed_at = ?
                WHERE trial_id = ? AND study_version_id = ? AND state = 'pending';
                """,
                (closed_at, trial_id, study_version_id),
            )
            if cursor.rowcount != 1:
                raise BayesianStorageConflict("trial is no longer pending")
            connection.execute(
                """
                UPDATE bayesian_studies
                SET updated_at = ?
                WHERE study_id = (
                    SELECT study_id FROM bayesian_study_versions
                    WHERE study_version_id = ?
                );
                """,
                (closed_at, study_version_id),
            )


def _insert_history_revision(
    connection: sqlite3.Connection, revision: BayesianHistoryRevisionRecord
) -> None:
    connection.execute(
        """
        INSERT INTO bayesian_observation_history_revisions (
            history_revision_id, study_version_id, revision_number,
            schema_version, completed_trial_ids_json, completed_trial_count,
            observation_history_sha256, previous_history_sha256, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            revision.history_revision_id,
            revision.study_version_id,
            revision.revision_number,
            revision.schema_version,
            revision.completed_trial_ids_json,
            revision.completed_trial_count,
            revision.observation_history_sha256,
            revision.previous_history_sha256,
            revision.created_at,
        ),
    )


def _trial_values(trial: BayesianTrialRecord) -> tuple[object, ...]:
    return (
        trial.trial_id,
        trial.study_version_id,
        trial.trial_number,
        trial.origin,
        trial.state,
        trial.actual_coordinates_json,
        trial.normalized_coordinates_json,
        trial.coordinates_sha256,
        trial.objective_value,
        trial.created_at,
        trial.closed_at,
    )


def _recommendation_values(
    recommendation: BayesianRecommendationRecord,
) -> tuple[object, ...]:
    return (
        recommendation.recommendation_id,
        recommendation.study_version_id,
        recommendation.trial_id,
        recommendation.source_history_revision_id,
        recommendation.source_observation_history_sha256,
        recommendation.method_id,
        recommendation.method_version,
        recommendation.config_schema_version,
        recommendation.result_schema_version,
        recommendation.model_schema_version,
        recommendation.config_json,
        recommendation.config_sha256,
        recommendation.result_json,
        recommendation.result_sha256,
        recommendation.result_payload_sha256,
        recommendation.created_at,
        recommendation.app_version,
    )


def _lifecycle_event_values(
    event: BayesianStudyLifecycleEventRecord,
) -> tuple[object, ...]:
    return (
        event.lifecycle_event_id,
        event.study_id,
        event.study_version_id,
        event.schema_version,
        event.lifecycle_revision,
        event.previous_status,
        event.resulting_status,
        event.reason_code,
        event.note,
        event.request_id,
        event.final_history_revision_id,
        event.final_observation_history_sha256,
        event.final_trial_count,
        event.final_completed_trial_count,
        event.final_abandoned_trial_count,
        event.latest_recommendation_id,
        event.definition_sha256,
        event.event_sha256,
        event.closed_at,
        event.created_at,
        event.app_version,
        event.build_commit,
    )


def _study_is_active(connection: sqlite3.Connection, study_version_id: str) -> bool:
    row = connection.execute(
        """
        SELECT study.status
        FROM bayesian_studies AS study
        INNER JOIN bayesian_study_versions AS version
            ON version.study_id = study.study_id
        WHERE version.study_version_id = ?;
        """,
        (study_version_id,),
    ).fetchone()
    return row is not None and str(row[0]) == "active"


def _deletion_graph_from_connection(
    connection: sqlite3.Connection,
    study_id: str,
) -> BayesianStudyDeletionGraphRecord | None:
    study = connection.execute(
        """
        SELECT status, updated_at, current_version
        FROM bayesian_studies WHERE study_id = ?;
        """,
        (study_id,),
    ).fetchone()
    if study is None:
        return None
    current_version = _row_int(study[2])
    version = connection.execute(
        """
        SELECT study_version_id
        FROM bayesian_study_versions
        WHERE study_id = ? AND version_number = ?;
        """,
        (study_id, current_version),
    ).fetchone()
    if version is None:
        raise BayesianStorageConflict("bayesian_study_deletion_conflict")
    current_study_version_id = str(version[0])
    head = connection.execute(
        """
        SELECT history_revision_id
        FROM bayesian_observation_history_heads
        WHERE study_version_id = ?;
        """,
        (current_study_version_id,),
    ).fetchone()
    if head is None:
        raise BayesianStorageConflict("bayesian_study_deletion_conflict")
    lifecycle = connection.execute(
        """
        SELECT lifecycle_event_id
        FROM bayesian_study_lifecycle_events
        WHERE study_id = ?;
        """,
        (study_id,),
    ).fetchone()
    counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM bayesian_study_versions WHERE study_id = ?),
            (SELECT COUNT(*) FROM bayesian_trials AS trial
             INNER JOIN bayesian_study_versions AS version
                ON version.study_version_id = trial.study_version_id
             WHERE version.study_id = ?),
            (SELECT COUNT(*) FROM bayesian_observation_history_revisions AS history
             INNER JOIN bayesian_study_versions AS version
                ON version.study_version_id = history.study_version_id
             WHERE version.study_id = ?),
            (SELECT COUNT(*) FROM bayesian_observation_history_heads AS head
             INNER JOIN bayesian_study_versions AS version
                ON version.study_version_id = head.study_version_id
             WHERE version.study_id = ?),
            (SELECT COUNT(*) FROM bayesian_recommendations AS recommendation
             INNER JOIN bayesian_study_versions AS version
                ON version.study_version_id = recommendation.study_version_id
             WHERE version.study_id = ?),
            (SELECT COUNT(*) FROM bayesian_study_lifecycle_events WHERE study_id = ?);
        """,
        (study_id, study_id, study_id, study_id, study_id, study_id),
    ).fetchone()
    if counts is None:
        raise BayesianStorageConflict("bayesian_study_deletion_conflict")
    successors = connection.execute(
        """
        SELECT study_id FROM bayesian_studies
        WHERE predecessor_study_id = ?
        ORDER BY study_id;
        """,
        (study_id,),
    ).fetchall()
    return BayesianStudyDeletionGraphRecord(
        study_id=study_id,
        status=str(study[0]),
        updated_at=str(study[1]),
        current_version=current_version,
        current_study_version_id=current_study_version_id,
        current_history_revision_id=str(head[0]),
        lifecycle_event_id=None if lifecycle is None else str(lifecycle[0]),
        study_version_count=_row_int(counts[0]),
        trial_count=_row_int(counts[1]),
        history_revision_count=_row_int(counts[2]),
        history_head_count=_row_int(counts[3]),
        recommendation_count=_row_int(counts[4]),
        lifecycle_event_count=_row_int(counts[5]),
        successor_study_ids=tuple(str(row[0]) for row in successors),
    )


def _study_from_row(row: tuple[object, ...]) -> BayesianStudyRecord:
    return BayesianStudyRecord(
        study_id=str(row[0]),
        method_id=str(row[1]),
        method_version=str(row[2]),
        name=str(row[3]),
        status=str(row[4]),
        current_version=_row_int(row[5]),
        created_at=str(row[6]),
        updated_at=str(row[7]),
        app_version=str(row[8]),
        predecessor_study_id=None if row[9] is None else str(row[9]),
    )


def _version_from_row(row: tuple[object, ...]) -> BayesianStudyVersionRecord:
    return BayesianStudyVersionRecord(
        study_version_id=str(row[0]),
        study_id=str(row[1]),
        version_number=_row_int(row[2]),
        schema_version=_row_int(row[3]),
        factors_json=str(row[4]),
        objective_json=str(row[5]),
        constraints_json=str(row[6]),
        initial_design_json=str(row[7]),
        definition_sha256=str(row[8]),
        created_at=str(row[9]),
    )


def _trial_from_row(row: tuple[object, ...]) -> BayesianTrialRecord:
    return BayesianTrialRecord(
        trial_id=str(row[0]),
        study_version_id=str(row[1]),
        trial_number=_row_int(row[2]),
        origin=str(row[3]),
        state=str(row[4]),
        actual_coordinates_json=str(row[5]),
        normalized_coordinates_json=str(row[6]),
        coordinates_sha256=str(row[7]),
        objective_value=None if row[8] is None else _row_float(row[8]),
        created_at=str(row[9]),
        closed_at=None if row[10] is None else str(row[10]),
    )


def _history_from_row(row: tuple[object, ...]) -> BayesianHistoryRevisionRecord:
    return BayesianHistoryRevisionRecord(
        history_revision_id=str(row[0]),
        study_version_id=str(row[1]),
        revision_number=_row_int(row[2]),
        schema_version=_row_int(row[3]),
        completed_trial_ids_json=str(row[4]),
        completed_trial_count=_row_int(row[5]),
        observation_history_sha256=str(row[6]),
        previous_history_sha256=None if row[7] is None else str(row[7]),
        created_at=str(row[8]),
    )


def _recommendation_from_row(row: tuple[object, ...]) -> BayesianRecommendationRecord:
    return BayesianRecommendationRecord(
        recommendation_id=str(row[0]),
        study_version_id=str(row[1]),
        trial_id=str(row[2]),
        source_history_revision_id=str(row[3]),
        source_observation_history_sha256=str(row[4]),
        method_id=str(row[5]),
        method_version=str(row[6]),
        config_schema_version=_row_int(row[7]),
        result_schema_version=_row_int(row[8]),
        model_schema_version=_row_int(row[9]),
        config_json=str(row[10]),
        config_sha256=str(row[11]),
        result_json=str(row[12]),
        result_sha256=str(row[13]),
        result_payload_sha256=str(row[14]),
        created_at=str(row[15]),
        app_version=str(row[16]),
    )


def _lifecycle_event_from_row(
    row: tuple[object, ...],
) -> BayesianStudyLifecycleEventRecord:
    return BayesianStudyLifecycleEventRecord(
        lifecycle_event_id=str(row[0]),
        study_id=str(row[1]),
        study_version_id=str(row[2]),
        schema_version=_row_int(row[3]),
        lifecycle_revision=_row_int(row[4]),
        previous_status=str(row[5]),
        resulting_status=str(row[6]),
        reason_code=str(row[7]),
        note=None if row[8] is None else str(row[8]),
        request_id=str(row[9]),
        final_history_revision_id=str(row[10]),
        final_observation_history_sha256=str(row[11]),
        final_trial_count=_row_int(row[12]),
        final_completed_trial_count=_row_int(row[13]),
        final_abandoned_trial_count=_row_int(row[14]),
        latest_recommendation_id=None if row[15] is None else str(row[15]),
        definition_sha256=str(row[16]),
        event_sha256=str(row[17]),
        closed_at=str(row[18]),
        created_at=str(row[19]),
        app_version=str(row[20]),
        build_commit=None if row[21] is None else str(row[21]),
    )


def _row_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str | bytes | bytearray):
        return int(value)
    raise TypeError("SQLite row value is not integer-compatible")


def _row_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str | bytes | bytearray):
        return float(value)
    raise TypeError("SQLite row value is not float-compatible")
