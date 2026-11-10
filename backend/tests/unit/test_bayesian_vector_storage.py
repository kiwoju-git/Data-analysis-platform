import hashlib
import json
import sqlite3
from dataclasses import replace

import pytest

from app.storage import metadata
from app.storage.bayesian_studies import (
    BayesianHistoryRevisionRecord,
    BayesianStorageConflict,
    BayesianStudyRecord,
    BayesianStudyVersionRecord,
    BayesianTrialRecord,
    complete_bayesian_trial_batch_records,
    complete_bayesian_trial_record,
    get_bayesian_trial_record,
    get_current_bayesian_history_revision_record,
    insert_bayesian_study_bundle,
    list_bayesian_trial_records,
)

STAMP = "2026-11-08T00:00:00Z"


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _study(root, *, vector=True, suffix="a"):
    study_id = f"study-{suffix}"
    version_id = f"version-{suffix}"
    objective = (
        {
            "goal_type": "desirability",
            "observation_policy": "complete_response_vector",
            "curve_policy": "derringer_suich_linear_v1",
            "responses": [{"response_id": "yield"}, {"response_id": "cost"}],
        }
        if vector
        else {"name": "Synthetic response", "direction": "maximize"}
    )
    study = BayesianStudyRecord(
        study_id,
        "doe.bayesian_optimization",
        "0.8.0",
        "Synthetic",
        "active",
        1,
        STAMP,
        STAMP,
        "test",
    )
    version = BayesianStudyVersionRecord(
        version_id,
        study_id,
        1,
        5 if vector else 4,
        "[]",
        _json(objective),
        "[]",
        "{}",
        _digest(objective),
        STAMP,
    )
    trials = [
        BayesianTrialRecord(
            f"trial-{suffix}-{number}",
            version_id,
            number,
            "initial_design",
            "pending",
            _json({"x": number}),
            _json({"x": number / 4}),
            _digest(number),
            None,
            STAMP,
            None,
        )
        for number in (1, 2, 3)
    ]
    history = BayesianHistoryRevisionRecord(
        f"history-{suffix}-0",
        version_id,
        1,
        2 if vector else 1,
        "[]",
        0,
        _digest([version_id, []]),
        None,
        STAMP,
    )
    insert_bayesian_study_bundle(
        root,
        study=study,
        version=version,
        trials=trials,
        initial_history=history,
    )
    return version, trials, history


def _next(history, observations, *, request_id="request-1"):
    previous = json.loads(history.completed_trial_ids_json)
    return replace(
        history,
        history_revision_id=request_id,
        revision_number=history.revision_number + 1,
        completed_trial_ids_json=_json([*previous, *(trial_id for trial_id, _ in observations)]),
        completed_trial_count=len(previous) + len(observations),
        observation_history_sha256=_digest([history.observation_history_sha256, observations]),
        previous_history_sha256=history.observation_history_sha256,
    )


def _complete(root, source, observations, new_history):
    return complete_bayesian_trial_batch_records(
        root,
        observations=observations,
        closed_at=STAMP,
        expected_history_revision_id=source.history_revision_id,
        expected_history_sha256=source.observation_history_sha256,
        new_history=new_history,
    )


@pytest.fixture
def workspace(tmp_path):
    metadata.initialize_metadata_store(tmp_path)
    return tmp_path


def test_vector_completion_round_trip_preserves_raw_values_and_canonical_json(workspace):
    version, trials, history = _study(workspace)
    observations = [
        (trials[0].trial_id, {"yield": 1e-6, "cost": 1000000000001.0}),
        (trials[1].trial_id, {"cost": 0.0, "yield": -2.5}),
    ]
    target = _next(history, observations)
    assert _complete(workspace, history, observations, target) == "created"
    restored = list_bayesian_trial_records(workspace, version.study_version_id)
    for trial, (_, values) in zip(restored[:2], observations, strict=True):
        assert trial.state == "completed" and trial.objective_value is None
        assert trial.response_values_json == _json(values)
        assert json.loads(trial.response_values_json) == values
        assert get_bayesian_trial_record(workspace, trial.trial_id) == trial
        assert trial.coordinates_sha256 == trials[trial.trial_number - 1].coordinates_sha256
    assert restored[2].state == "pending" and restored[2].response_values_json is None
    assert (
        get_current_bayesian_history_revision_record(workspace, version.study_version_id) == target
    )


def test_scalar_history_and_trial_storage_remain_scalar(workspace):
    version, trials, history = _study(workspace, vector=False)
    observations = [(trials[0].trial_id, -3.25)]
    assert _complete(workspace, history, observations, _next(history, observations)) == "created"
    restored = list_bayesian_trial_records(workspace, version.study_version_id)
    assert restored[0].objective_value == -3.25
    assert restored[0].response_values_json is None


@pytest.mark.parametrize("vector,value", [(True, 1.0), (False, {"cost": 1.0, "yield": 2.0})])
def test_observation_mode_mismatch_is_rejected_atomically(workspace, vector, value):
    version, trials, history = _study(workspace, vector=vector)
    observations = [(trials[0].trial_id, value)]
    with pytest.raises(BayesianStorageConflict, match="bayesian_observation_mode_invalid"):
        _complete(workspace, history, observations, _next(history, observations))
    assert list_bayesian_trial_records(workspace, version.study_version_id) == trials
    assert (
        get_current_bayesian_history_revision_record(workspace, version.study_version_id) == history
    )


@pytest.mark.parametrize(
    "values",
    [
        {"yield": 1.0},
        {"yield": 1.0, "cost": 2.0, "unknown": 3.0},
        {"yield": float("nan"), "cost": 2.0},
        {"yield": 1.0, "cost": float("inf")},
        {"yield": True, "cost": 2.0},
        {"yield": "1", "cost": 2.0},
    ],
)
def test_invalid_response_vector_does_not_partially_commit(workspace, values):
    version, trials, history = _study(workspace)
    observations = [
        (trials[0].trial_id, {"yield": 1.0, "cost": 2.0}),
        (trials[1].trial_id, values),
    ]
    with pytest.raises(
        BayesianStorageConflict, match="bayesian_observation_response_values_invalid"
    ):
        _complete(workspace, history, observations, _next(history, observations))
    assert list_bayesian_trial_records(workspace, version.study_version_id) == trials
    assert (
        get_current_bayesian_history_revision_record(workspace, version.study_version_id) == history
    )


def test_history_schema_must_match_owner_even_for_valid_vector(workspace):
    version, trials, history = _study(workspace)
    observations = [(trials[0].trial_id, {"yield": 1.0, "cost": 2.0})]
    target = replace(_next(history, observations), schema_version=1)
    with pytest.raises(BayesianStorageConflict, match="bayesian_observation_mode_invalid"):
        _complete(workspace, history, observations, target)
    assert list_bayesian_trial_records(workspace, version.study_version_id) == trials


def test_vector_request_replay_after_later_completion_and_conflicting_payload(workspace):
    _, trials, history = _study(workspace)
    first = [(trials[0].trial_id, {"yield": 1.0, "cost": 2.0})]
    target = _next(history, first)
    assert _complete(workspace, history, first, target) == "created"
    second = [(trials[1].trial_id, {"yield": 2.0, "cost": 3.0})]
    latest = _next(target, second, request_id="request-2")
    assert _complete(workspace, target, second, latest) == "created"
    reordered = [(trials[0].trial_id, {"cost": 2.0, "yield": 1.0})]
    assert _complete(workspace, history, reordered, target) == "replay"
    changed = [(trials[0].trial_id, {"yield": 1.0, "cost": 9.0})]
    with pytest.raises(BayesianStorageConflict, match="bayesian_observation_request_id_conflict"):
        _complete(workspace, history, changed, target)
    with pytest.raises(BayesianStorageConflict, match="bayesian_observation_request_id_conflict"):
        _complete(workspace, history, first, _next(history, changed))


def test_stale_cas_and_foreign_owner_cannot_commit_vector(workspace):
    version, trials, history = _study(workspace)
    _, other_trials, _ = _study(workspace, suffix="b")
    first = [(trials[0].trial_id, {"yield": 1.0, "cost": 2.0})]
    target = _next(history, first)
    assert _complete(workspace, history, first, target) == "created"
    stale = [(trials[1].trial_id, {"yield": 1.0, "cost": 2.0})]
    with pytest.raises(BayesianStorageConflict, match="history head changed"):
        _complete(workspace, history, stale, _next(history, stale, request_id="stale"))
    mixed = [*stale, (other_trials[0].trial_id, {"yield": 3.0, "cost": 4.0})]
    with pytest.raises(BayesianStorageConflict, match="bayesian_observation_trial_not_found"):
        _complete(workspace, target, mixed, _next(target, mixed, request_id="foreign"))
    restored = list_bayesian_trial_records(workspace, version.study_version_id)
    assert restored[1:] == trials[1:]
    assert (
        get_current_bayesian_history_revision_record(workspace, version.study_version_id) == target
    )


def test_vector_update_failure_rolls_back_all_rows_and_history(workspace):
    version, trials, history = _study(workspace)
    with sqlite3.connect(metadata.metadata_db_path(workspace)) as connection:
        connection.execute(
            "CREATE TRIGGER synthetic_second_row_failure BEFORE UPDATE ON bayesian_trials "
            "WHEN NEW.trial_number=2 BEGIN SELECT RAISE(ABORT,'synthetic write failure'); END;"
        )
    observations = [(trial.trial_id, {"yield": 1.0, "cost": 2.0}) for trial in trials[:2]]
    with pytest.raises(sqlite3.IntegrityError, match="synthetic write failure"):
        _complete(workspace, history, observations, _next(history, observations))
    assert list_bayesian_trial_records(workspace, version.study_version_id) == trials
    assert (
        get_current_bayesian_history_revision_record(workspace, version.study_version_id) == history
    )


def test_migration_25_to_26_preserves_existing_scalar_rows_and_checksums(tmp_path, monkeypatch):
    with monkeypatch.context() as context:
        context.setattr(metadata, "SCHEMA_VERSION", 25)
        context.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 25)
        )
        metadata.initialize_metadata_store(tmp_path)
        version, trials, history = _study(tmp_path, vector=False)
        complete_bayesian_trial_record(
            tmp_path,
            trial_id=trials[0].trial_id,
            objective_value=1e-6,
            closed_at=STAMP,
            expected_history_revision_id=history.history_revision_id,
            new_history=_next(history, [(trials[0].trial_id, 1e-6)]),
        )
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as connection:
        before = connection.execute(
            "SELECT * FROM bayesian_trials ORDER BY trial_number"
        ).fetchall()
        definition = connection.execute("SELECT * FROM bayesian_study_versions").fetchall()
        histories = connection.execute(
            "SELECT * FROM bayesian_observation_history_revisions"
        ).fetchall()
    assert metadata.initialize_metadata_store(tmp_path).schema_version == metadata.SCHEMA_VERSION
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as connection:
        after = connection.execute("SELECT * FROM bayesian_trials ORDER BY trial_number").fetchall()
        assert [row[:-1] for row in after] == before
        assert all(row[-1] is None for row in after)
        assert connection.execute("SELECT * FROM bayesian_study_versions").fetchall() == definition
        assert (
            connection.execute("SELECT * FROM bayesian_observation_history_revisions").fetchall()
            == histories
        )
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    assert all(
        trial.response_values_json is None
        for trial in list_bayesian_trial_records(tmp_path, version.study_version_id)
    )
