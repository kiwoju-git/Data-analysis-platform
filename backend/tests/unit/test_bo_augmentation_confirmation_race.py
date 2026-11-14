"""Deterministic service races over real model-free augmentation artifacts."""

import sqlite3
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.schemas.bo_planning import PlanningConfirmRequest
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services import bayesian_studies, bo_augmentation_batches
from app.services import bo_desirability_worker as execution
from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_multiresponse_lifecycle import create_study, url
from tests.unit.test_bo_candidates_v2 import request as candidate_request
from tests.unit.test_bo_desirability_review_api import completed
from tests.unit.test_bo_planning_worker import _Output


@pytest.fixture
def augmentation(tmp_path, monkeypatch):
    def in_process(encoded, *, entrypoint, timeout_ms, cancel, max_result_bytes):
        output = _Output()
        entrypoint(output, encoded)
        assert output.closed and len(output.data) <= max_result_bytes
        assert timeout_ms > 0 and cancel is None
        return output.data

    monkeypatch.setattr(execution, "_run_owned_worker", in_process)
    settings = Settings(workspace_root=tmp_path / "confirmation race")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        candidate_body = candidate_request(study)
        response = client.post(url(study) + "/candidate-revisions", json=candidate_body)
        assert response.status_code == 201, response.text
        candidate = response.json()["revision"]
        body = {
            key: candidate_body[key]
            for key in (
                "schema_version",
                "expected_study_version_id",
                "expected_definition_sha256",
                "expected_history_revision_id",
                "expected_history_sha256",
                "expected_trial_count",
                "model_id",
                "expected_model_sha256",
            )
        } | {
            "request_id": str(uuid4()),
            "candidate_revision_id": candidate["revision_id"],
            "expected_rows_sha256": candidate["rows_sha256"],
            "policy": "greedy_incremental_maxpro_v1",
            "batch_size": 2,
            "total_trial_budget": 5,
        }
        response = client.post(url(study) + "/augmentations", json=body)
        assert response.status_code == 201, response.text
        selection = response.json()
        state = SimpleNamespace(
            client=client,
            settings=settings,
            study=study,
            study_id=UUID(study["study_id"]),
            selection_id=UUID(selection["selection_id"]),
            body=PlanningConfirmRequest(
                expected_config_sha256=selection["config_sha256"],
                expected_result_sha256=selection["result_sha256"],
            ),
            endpoint=url(study) + "/augmentations/" + selection["selection_id"] + "/confirm",
        )
        state.unconfirmed = bo_augmentation_batches.get_augmentation_selection(
            settings, state.study_id, state.selection_id
        )
        state.before_study = bayesian_studies.get_bayesian_study(settings, state.study_id)
        yield state


def _confirm(state):
    return bo_augmentation_batches.confirm_augmentation_selection(
        state.settings, state.study_id, state.selection_id, state.body
    )


def _rows(state):
    with sqlite3.connect(metadata_db_path(state.settings.workspace_root)) as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in (
                "bayesian_trials",
                "bayesian_recommendation_batches",
                "bayesian_recommendation_batch_items",
                "bayesian_planning_selections",
                "bayesian_planning_confirmations",
            )
        }


def _stale_first_read(state, monkeypatch):
    original = bo_augmentation_batches.get_augmentation_selection
    calls = []

    def read(*args):
        calls.append(args)
        return state.unconfirmed if len(calls) == 1 else original(*args)

    monkeypatch.setattr(bo_augmentation_batches, "get_augmentation_selection", read)
    return calls


def test_commit_between_selection_and_source_read_replays_exact_batch(augmentation, monkeypatch):
    state = augmentation
    committed = _confirm(state)
    before = _rows(state)
    calls = _stale_first_read(state, monkeypatch)
    raced = _confirm(state)
    assert raced == committed
    assert len(calls) == 2
    assert _rows(state) == before
    assert len(before["bayesian_trials"]) == 5
    assert len(before["bayesian_planning_confirmations"]) == 1


@pytest.mark.parametrize(
    "code",
    [
        "bayesian_candidate_source_changed",
        "bayesian_optimization_pending_recommendation_exists",
        "bayesian_optimization_batch_budget_exceeded",
    ],
)
def test_guard_error_after_another_commit_uses_hash_bound_replay(augmentation, monkeypatch, code):
    state = augmentation
    committed = _confirm(state)
    before = _rows(state)
    _stale_first_read(state, monkeypatch)
    original = bayesian_studies.get_bayesian_study
    first = True

    def guard_error(*args):
        nonlocal first
        if first:
            first = False
            raise ApiError(code=code, message="Synthetic raced guard", status_code=409)
        return original(*args)

    monkeypatch.setattr(bayesian_studies, "get_bayesian_study", guard_error)
    assert _confirm(state) == committed
    assert _rows(state) == before


def test_transaction_conflict_after_another_commit_replays_exact_batch(augmentation, monkeypatch):
    state = augmentation
    committed = _confirm(state)
    before = _rows(state)
    _stale_first_read(state, monkeypatch)
    original = bayesian_studies.get_bayesian_study
    first = True

    def held_source(*args):
        nonlocal first
        if first:
            first = False
            return state.before_study
        return original(*args)

    def conflict(*args, **kwargs):
        raise BayesianStorageConflict("bayesian_optimization_history_stale")

    monkeypatch.setattr(bayesian_studies, "get_bayesian_study", held_source)
    monkeypatch.setattr(
        bo_augmentation_batches, "insert_bayesian_recommendation_batch_bundle", conflict
    )
    assert _confirm(state) == committed
    assert _rows(state) == before


@pytest.mark.parametrize(
    "code",
    [
        "bayesian_candidate_source_changed",
        "bayesian_optimization_pending_recommendation_exists",
        "bayesian_optimization_batch_budget_exceeded",
    ],
)
def test_uncommitted_guard_failure_is_not_hidden_by_replay(augmentation, monkeypatch, code):
    state = augmentation
    before = _rows(state)
    original = bayesian_studies.get_bayesian_study
    first = True

    def guard_error(*args):
        nonlocal first
        if first:
            first = False
            raise ApiError(code=code, message="Synthetic genuine guard", status_code=409)
        return original(*args)

    monkeypatch.setattr(bayesian_studies, "get_bayesian_study", guard_error)
    with pytest.raises(ApiError) as raised:
        _confirm(state)
    assert raised.value.code == code
    assert _rows(state) == before


def test_uncommitted_transaction_failure_is_not_hidden_by_replay(augmentation, monkeypatch):
    state = augmentation
    before = _rows(state)

    def conflict(*args, **kwargs):
        raise BayesianStorageConflict("bayesian_optimization_history_stale")

    monkeypatch.setattr(
        bo_augmentation_batches, "insert_bayesian_recommendation_batch_bundle", conflict
    )
    with pytest.raises(ApiError) as raised:
        _confirm(state)
    assert raised.value.code == "bayesian_optimization_history_stale"
    assert _rows(state) == before


@pytest.mark.parametrize("field", ["config_sha256", "result_sha256"])
def test_raced_replay_rechecks_both_expected_hashes(augmentation, monkeypatch, field):
    state = augmentation
    _confirm(state)
    before = _rows(state)
    original = bo_augmentation_batches.get_augmentation_selection
    calls = 0

    def changed_hash(*args):
        nonlocal calls
        calls += 1
        if calls == 1:
            return state.unconfirmed
        return original(*args).model_copy(update={field: "f" * 64})

    monkeypatch.setattr(bo_augmentation_batches, "get_augmentation_selection", changed_hash)
    with pytest.raises(ApiError) as raised:
        _confirm(state)
    assert raised.value.code == "bayesian_planning_selection_mismatch"
    assert calls == 2
    assert _rows(state) == before


@pytest.mark.parametrize("field", ["expected_config_sha256", "expected_result_sha256"])
@pytest.mark.parametrize("value,status", [("invalid-hash", 422), ("f" * 64, 409)])
def test_committed_batch_does_not_bypass_malformed_or_wrong_hash(
    augmentation, field, value, status
):
    state = augmentation
    _confirm(state)
    before = _rows(state)
    body = state.body.model_dump(mode="json") | {field: value}
    response = state.client.post(state.endpoint, json=body)
    assert response.status_code == status, response.text
    assert _rows(state) == before


def test_committed_selection_cannot_replay_for_another_owner(augmentation):
    state = augmentation
    _confirm(state)
    other = create_study(state.client)
    before = _rows(state)
    response = state.client.post(
        state.endpoint.replace(str(state.study_id), other["study_id"]),
        json=state.body.model_dump(mode="json"),
    )
    assert response.status_code == 404, response.text
    assert _rows(state) == before
