"""Storage invariants with synthetic SQL records, separate from API/fit evidence."""

import sqlite3
from copy import deepcopy

import pytest

from app.storage import bo_planning as storage
from app.storage import metadata
from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.bo_planning_schema import BO_PLANNING_SQL
from tests.unit.test_bayesian_vector_storage import _study


@pytest.fixture
def workspace(tmp_path):
    metadata.initialize_metadata_store(tmp_path)
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        if (
            db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='bayesian_planning_models'"
            ).fetchone()
            is None
        ):
            db.executescript(BO_PLANNING_SQL)
    return tmp_path


def _model(root, suffix="a"):
    version, trials, history = _study(root, suffix=suffix)
    config = {"synthetic": suffix}
    snapshot = {"numeric_state": [0.0, 1.0]}
    record = {
        "model_id": f"model-{suffix}",
        "study_version_id": version.study_version_id,
        "source_history_revision_id": history.history_revision_id,
        "definition_sha256": version.definition_sha256,
        "history_sha256": history.observation_history_sha256,
        "schema_version": 1,
        "request_id": f"fit-{suffix}",
        "config_json": storage.planning_json(config),
        "config_sha256": storage.planning_sha(config),
        "snapshot_json": storage.planning_json(snapshot),
        "snapshot_sha256": storage.planning_sha(snapshot),
        "created_at": "2026-11-10T00:00:00Z",
    }
    assert storage.insert_planning_model(root, record) == record["model_id"]
    return record, trials


def _candidate(model, number=1, *, parent=None):
    rows = [{"synthetic_coordinate": 0.123}]
    config = {"synthetic_revision": number}
    return {
        "revision_id": f"revision-{model['model_id']}-{number}",
        "candidate_set_id": f"set-{model['model_id']}",
        "study_version_id": model["study_version_id"],
        "model_id": model["model_id"],
        "revision_number": number,
        "schema_version": 1,
        "request_id": f"candidate-{number}",
        "parent_revision_id": parent,
        "source_trial_count": 3,
        "excluded_coordinates_sha256": "b" * 64,
        "config_json": storage.planning_json(config),
        "config_sha256": storage.planning_sha(config),
        "rows_json": storage.planning_json(rows),
        "rows_sha256": storage.planning_sha(rows),
        "row_count": 1,
        "created_at": model["created_at"],
    }


def _selection(model, candidate):
    config = {
        "expected_model_sha256": model["snapshot_sha256"],
        "expected_rows_sha256": candidate["rows_sha256"],
        "expected_history_revision_id": model["source_history_revision_id"],
        "expected_history_sha256": model["history_sha256"],
        "expected_trial_count": 3,
    }
    result = {"synthetic_only": True}
    return {
        "selection_id": "selection-a",
        "study_version_id": model["study_version_id"],
        "model_id": model["model_id"],
        "candidate_revision_id": candidate["revision_id"],
        "request_id": "choose-a",
        "schema_version": 1,
        "config_json": storage.planning_json(config),
        "config_sha256": storage.planning_sha(config),
        "result_json": storage.planning_json(result),
        "result_sha256": storage.planning_sha(result),
        "created_at": model["created_at"],
    }


def test_immutable_model_replay_and_hash_validation(workspace):
    model, _ = _model(workspace)
    assert storage.insert_planning_model(workspace, model) == model["model_id"]
    restored = storage.get_planning_model(workspace, model["model_id"], model["study_version_id"])
    assert restored == model
    assert storage.get_planning_model(workspace, model["model_id"], "other-owner") is None
    changed = deepcopy(model)
    changed["config_json"] = storage.planning_json({"different": 1})
    changed["config_sha256"] = storage.planning_sha({"different": 1})
    with pytest.raises(BayesianStorageConflict, match="request_conflict"):
        storage.insert_planning_model(workspace, changed)
    with sqlite3.connect(metadata.metadata_db_path(workspace)) as db:
        db.execute("UPDATE bayesian_planning_models SET snapshot_json='{}'")
    with pytest.raises(BayesianStorageConflict, match="artifact_invalid"):
        storage.get_planning_model(workspace, model["model_id"], model["study_version_id"])


def test_candidate_head_cas_replay_owner_and_original_revision(workspace):
    model, _ = _model(workspace)
    first = _candidate(model)
    assert (
        storage.insert_candidate_revision(workspace, first, name="Synthetic", expected_head=None)
        == first["revision_id"]
    )
    second = _candidate(model, 2, parent=first["revision_id"])
    storage.insert_candidate_revision(
        workspace, second, name="Synthetic", expected_head=first["revision_id"]
    )
    assert (
        storage.get_candidate_revision(workspace, first["revision_id"], model["study_version_id"])
        == first
    )
    assert (
        storage.insert_candidate_revision(workspace, first, name="Synthetic", expected_head=None)
        == first["revision_id"]
    )
    raced = _candidate(model, 2, parent=first["revision_id"])
    raced.update(request_id="competing-edit", revision_id="competing-revision")
    with pytest.raises(BayesianStorageConflict, match="revision_conflict"):
        storage.insert_candidate_revision(
            workspace, raced, name="Synthetic", expected_head=first["revision_id"]
        )
    wrong_owner = {**first, "study_version_id": "version-another"}
    with pytest.raises(BayesianStorageConflict, match="request_conflict"):
        storage.insert_candidate_revision(
            workspace, wrong_owner, name="Synthetic", expected_head=None
        )
    assert (
        storage.list_candidate_sets(workspace, model["study_version_id"])[0]["revision_id"]
        == second["revision_id"]
    )


def test_capacity_rejection_has_no_partial_candidate_set(workspace, monkeypatch):
    model, _ = _model(workspace)
    monkeypatch.setattr(storage, "MAX_OWNER_BYTES", 1)
    with pytest.raises(BayesianStorageConflict, match="capacity_exceeded"):
        storage.insert_candidate_revision(
            workspace, _candidate(model), name="Synthetic", expected_head=None
        )
    assert storage.list_candidate_sets(workspace, model["study_version_id"]) == []


def test_selection_pending_stale_source_and_delete_rollback(workspace):
    model, _ = _model(workspace)
    first = _candidate(model)
    storage.insert_candidate_revision(workspace, first, name="Synthetic", expected_head=None)
    second = _candidate(model, 2, parent=first["revision_id"])
    storage.insert_candidate_revision(
        workspace, second, name="Synthetic", expected_head=first["revision_id"]
    )
    selection = _selection(model, second)
    with pytest.raises(BayesianStorageConflict, match="pending_recommendation_exists"):
        storage.insert_planning_selection(workspace, selection)
    with sqlite3.connect(metadata.metadata_db_path(workspace)) as db:
        db.execute(
            "UPDATE bayesian_trials SET state='abandoned',closed_at=?", (model["created_at"],)
        )
    storage.insert_planning_selection(workspace, selection)
    assert storage.insert_planning_selection(workspace, selection) == selection["selection_id"]
    with sqlite3.connect(metadata.metadata_db_path(workspace)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        storage.delete_planning_owner(db, model["study_version_id"])
        db.rollback()
    assert (
        storage.get_planning_selection(
            workspace, selection["selection_id"], model["study_version_id"]
        )
        is not None
    )
    with sqlite3.connect(metadata.metadata_db_path(workspace)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        storage.delete_planning_owner(db, model["study_version_id"])
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert storage.list_planning_models(workspace, model["study_version_id"]) == []
    assert storage.list_candidate_sets(workspace, model["study_version_id"]) == []


def test_changed_history_prevents_new_revision_but_preserves_existing(workspace):
    model, _ = _model(workspace)
    first = _candidate(model)
    storage.insert_candidate_revision(workspace, first, name="Synthetic", expected_head=None)
    with sqlite3.connect(metadata.metadata_db_path(workspace)) as db:
        db.execute(
            "UPDATE bayesian_observation_history_revisions SET observation_history_sha256=?",
            ("f" * 64,),
        )
    second = _candidate(model, 2, parent=first["revision_id"])
    with pytest.raises(BayesianStorageConflict, match="history_stale"):
        storage.insert_candidate_revision(
            workspace, second, name="Synthetic", expected_head=first["revision_id"]
        )
    assert (
        storage.get_candidate_revision(workspace, first["revision_id"], model["study_version_id"])
        == first
    )
