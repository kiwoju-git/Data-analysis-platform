"""Saved BO diagnostics are immutable model-owned views, not candidate receipts."""

import sqlite3
from contextlib import ExitStack
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services import bo_desirability_worker as execution
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_multiresponse_lifecycle import url
from tests.unit.test_bo_desirability_review_api import completed
from tests.unit.test_bo_planning_api import fit_request
from tests.unit.test_bo_planning_worker import _Output


@pytest.fixture
def source(tmp_path, monkeypatch):
    def in_process(encoded, *, entrypoint, timeout_ms, cancel, max_result_bytes):
        output = _Output()
        entrypoint(output, encoded)
        assert output.closed and len(output.data) <= max_result_bytes
        return output.data

    monkeypatch.setattr(execution, "_run_owned_worker", in_process)
    settings = Settings(workspace_root=tmp_path / "synthetic saved views")
    with ExitStack() as lifetime:
        app = create_app(settings)
        client = lifetime.enter_context(TestClient(app))
        study = completed(client)
        response = client.post(url(study) + "/planning-models", json=fit_request(study))
        assert response.status_code == 201, response.text
        model = response.json()
        yield SimpleNamespace(
            client=client,
            app=app,
            settings=settings,
            study=study,
            model=model,
            close=lifetime.close,
            endpoint=url(study) + "/planning-models/" + model["model_id"] + "/view-evaluations",
            body={
                "kind": "profiler_matrix",
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
                "holds": {"x": 5},
                "points_per_axis": 5,
                "time_budget_ms": 60000,
            },
        )


def _evaluate(source, *, kind="profiler_matrix"):
    body = (
        source.body
        if kind == "profiler_matrix"
        else {
            "kind": "conditional_loo",
            "expected_model_sha256": source.model["snapshot_sha256"],
            "expected_history_sha256": source.model["history_sha256"],
        }
    )
    result = source.client.post(source.endpoint, json=body)
    assert result.status_code == 200, result.text
    return result.json()


def _save_body(receipt):
    return {
        "request_id": str(uuid4()),
        "receipt_id": receipt["receipt_id"],
        "expected_model_sha256": receipt["payload"]["source"]["model_sha256"],
        "expected_request_sha256": receipt["request_sha256"],
        "expected_view_sha256": receipt["view_sha256"],
    }


def test_matrix_receipt_all_responses_and_no_live_eligibility(source):
    value = _evaluate(source)
    payload = value["payload"]
    assert payload["kind"] == "profiler_matrix"
    assert payload["source"]["history_sha256"] == source.model["history_sha256"]
    assert payload["model_refit"] is False
    assert payload["point_count"] == 5
    assert len(payload["axes"]) == 1
    assert payload["axes"][0]["factor_id"] == "x"
    points = payload["axes"][0]["points"]
    assert [point["actual_coordinates"]["x"] for point in points] == [0, 2.5, 5, 7.5, 10]
    assert [row["response_id"] for row in points[0]["response_predictions"]] == ["yield", "cost"]
    for row in points:
        assert "constraints_satisfied" in row
        assert not {"novel", "eligible", "nearest_existing_distance", "pending"}.intersection(row)
        assert row["prediction_source"] == "completed_observations_base_posterior"
        assert all(
            p["predictive_standard_deviation_raw"] >= p["latent_standard_deviation_raw"]
            for p in row["response_predictions"]
        )


@pytest.mark.parametrize("kind", ["profiler_matrix", "conditional_loo"])
def test_explicit_save_replays_after_receipt_expiry_without_evaluation(source, monkeypatch, kind):
    receipt = _evaluate(source, kind=kind)
    from app.services import bo_loo, bo_planning

    def forbidden(*args, **kwargs):
        pytest.fail("save/read must not evaluate or refit")

    monkeypatch.setattr(bo_planning, "_run", forbidden)
    monkeypatch.setattr(bo_loo, "_run", forbidden)
    body = _save_body(receipt)
    endpoint = url(source.study) + "/views"
    saved = source.client.post(endpoint, json=body)
    assert saved.status_code == 201, saved.text
    record = saved.json()
    assert record["payload"] == receipt["payload"]
    assert record["view_sha256"] == receipt["view_sha256"]
    source.app.state.bo_view_receipts.clear()
    assert source.client.post(endpoint, json=body).json() == record
    read = source.client.get(endpoint + "/" + record["view_id"])
    assert read.status_code == 200, read.text
    assert read.json() == record
    assert source.client.get(endpoint).json()["items"][0]["view_id"] == record["view_id"]
    conflict = source.client.post(endpoint, json=body | {"expected_view_sha256": "f" * 64})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "bayesian_view_request_conflict"
    expired = source.client.post(endpoint, json=body | {"request_id": str(uuid4())})
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "bayesian_view_receipt_expired"


def test_save_does_not_accept_client_prediction_payload(source):
    receipt = _evaluate(source)
    body = _save_body(receipt) | {"payload": receipt["payload"]}
    response = source.client.post(url(source.study) + "/views", json=body)
    assert response.status_code == 422


def test_wrong_view_or_source_digest_never_saves(source):
    receipt = _evaluate(source)
    body = _save_body(receipt)
    for field in ("expected_model_sha256", "expected_request_sha256", "expected_view_sha256"):
        response = source.client.post(url(source.study) + "/views", json=body | {field: "f" * 64})
        assert response.status_code == 409, response.text
    assert source.client.get(url(source.study) + "/views").json()["items"] == []


def test_historical_closed_model_view_is_not_candidate_permission(source):
    from tests.unit.test_bayesian_study_lifecycle_api import _close_request

    closed = source.client.post(
        url(source.study) + "/close",
        json=_close_request(
            source.study,
            target_status="abandoned",
            reason_code="study_cancelled",
        ),
    )
    assert closed.status_code == 200, closed.text
    receipt = _evaluate(source)
    saved = source.client.post(url(source.study) + "/views", json=_save_body(receipt))
    assert saved.status_code == 201, saved.text
    assert saved.json()["payload"]["source"]["model_sha256"] == source.model["snapshot_sha256"]


def test_saved_view_restore_backup_uses_stored_payload_and_preserves_owner(
    source, tmp_path, monkeypatch
):
    from app.services import bo_planning
    from app.storage.workspace_backup import backup_workspace, restore_workspace

    receipt = _evaluate(source)
    endpoint = url(source.study) + "/views"
    body = _save_body(receipt)
    saved = source.client.post(endpoint, json=body)
    assert saved.status_code == 201, saved.text
    value = saved.json()
    source.close()
    archive, restored = tmp_path / "views backup.tar.gz", tmp_path / "restored view workspace"
    backup_workspace(source.settings.workspace_root, archive)
    restore_workspace(archive, restored)

    def forbidden(*args, **kwargs):
        pytest.fail("reading a saved diagnostic cannot read raw history or evaluate")

    monkeypatch.setattr(bo_planning, "get_bayesian_study", forbidden)
    monkeypatch.setattr(bo_planning, "_read_model", forbidden)
    monkeypatch.setattr(bo_planning, "_run", forbidden)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        assert client.get(endpoint + "/" + value["view_id"]).json() == value
        assert client.post(endpoint, json=body).json() == value


def test_view_owner_guard_and_deletion_cas(source):
    from tests.unit.test_bayesian_multiresponse_lifecycle import create_study
    from tests.unit.test_bayesian_study_lifecycle_api import _close_request

    before = source.client.get(url(source.study) + "/deletion-preflight").json()
    receipt = _evaluate(source)
    body = _save_body(receipt)
    other = create_study(source.client)
    assert source.client.post(url(other) + "/views", json=body).status_code == 409
    saved = source.client.post(url(source.study) + "/views", json=body).json()
    assert source.client.get(url(other) + "/views/" + saved["view_id"]).status_code == 404
    current = source.client.get(url(source.study) + "/deletion-preflight").json()
    assert current["counts"]["saved_view_count"] == 1
    assert current["deletion_manifest_sha256"] != before["deletion_manifest_sha256"]
    closed = source.client.post(
        url(source.study) + "/close",
        json=_close_request(
            source.study,
            target_status="abandoned",
            reason_code="study_cancelled",
        ),
    )
    assert closed.status_code == 200, closed.text
    request = {
        "confirmation_study_id": source.study["study_id"],
        "expected_deletion_manifest_sha256": before["deletion_manifest_sha256"],
    }
    assert source.client.request("DELETE", url(source.study), json=request).status_code == 409
    fresh = source.client.get(url(source.study) + "/deletion-preflight").json()
    request["expected_deletion_manifest_sha256"] = fresh["deletion_manifest_sha256"]
    deleted = source.client.request("DELETE", url(source.study), json=request)
    assert deleted.status_code == 200, deleted.text
    assert source.client.get(url(source.study) + "/views/" + saved["view_id"]).status_code == 404


def test_view_save_failure_leaves_no_partial_record(source):
    receipt = _evaluate(source)
    path = metadata_db_path(source.settings.workspace_root)
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TRIGGER reject_view BEFORE INSERT ON bayesian_saved_views "
            "BEGIN SELECT RAISE(ABORT, 'synthetic disk failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic disk failure"):
        source.client.post(url(source.study) + "/views", json=_save_body(receipt))
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_saved_views").fetchone()[0] == 0
    assert (
        source.client.get(url(source.study)).json()["observation_history"]
        == source.study["observation_history"]
    )


def test_invalid_holds_and_late_chunk_do_not_create_receipt(source, monkeypatch):
    from app.services import bo_views

    for holds in ({}, {"x": "5"}, {"x": 11}, {"x": 5, "extra": 1}):
        response = source.client.post(source.endpoint, json=source.body | {"holds": holds})
        assert response.status_code == 422, response.text
    clock = iter([0, 0, 61])
    monkeypatch.setattr(bo_views, "monotonic", lambda: next(clock))
    response = source.client.post(source.endpoint, json=source.body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "bayesian_view_time_budget_exceeded"
    assert not source.app.state.bo_view_receipts._items
