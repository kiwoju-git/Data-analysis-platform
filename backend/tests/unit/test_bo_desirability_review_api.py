"""Actual HTTP/owned worker q1 review, confirmation and immutable restoration."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from threadpoolctl import threadpool_limits

from app.core.config import Settings
from app.main import create_app
from app.storage import metadata
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import create_study, observations, url


def review_request(study):
    return {
        "schema_version": 4,
        "batch_size": 1,
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_history_sha256": study["observation_history"]["observation_history_sha256"],
        "response_models": [
            {
                "response_id": r["response_id"],
                "kernel": {"kind": "matern_5_2"},
                "surrogate": {"noise_mode": "estimate"},
            }
            for r in study["objective"]["responses"]
        ],
        "observation_policy": {"mode": "retain_raw"},
        "xi_desirability": 0.01,
        "total_trial_budget": 20,
        "search": {
            "random_seed": 42,
            "candidate_count_per_step": 32,
            "local_start_count_per_step": 0,
            "max_iterations_per_step": 50,
            "max_evaluations_total": 128,
            "model_max_iterations": 40,
            "model_max_evaluations": 1000,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 60000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
    }


def completed(client):
    study = create_study(client)
    saved = client.put(url(study) + "/observations/batch", json=observations(study))
    assert saved.status_code == 200, saved.text
    return saved.json()["study"]


def test_review_only_then_confirm_once_and_restore(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        from uuid import UUID

        from app.api.v1.schemas.bayesian_desirability_recommendations import (
            DesirabilityReviewRequest,
        )
        from app.services.bayesian_desirability_recommendations import _source

        _source(
            settings,
            UUID(study["study_id"]),
            DesirabilityReviewRequest.model_validate(review_request(study)),
        )
        reviewed = client.post(url(study) + "/desirability-reviews", json=review_request(study))
        assert reviewed.status_code == 200, reviewed.text
        review = reviewed.json()
        assert client.get(url(study)).json()["trials"] == study["trials"]
        from app.services import bo_desirability_worker

        def no_fit(*args, **kwargs):
            raise AssertionError("confirmation/restore must not fit")

        monkeypatch.setattr(bo_desirability_worker, "run_desirability_calculation", no_fit)
        confirm_url = url(study) + f"/desirability-reviews/{review['review_id']}/confirm"
        body = {"expected_config_sha256": review["config_sha256"]}
        confirmed = client.post(confirm_url, json=body)
        assert confirmed.status_code == 201, confirmed.text
        batch = confirmed.json()
        assert batch["calculation"] == review["calculation"]
        assert batch["items"][0]["trial"]["objective_value"] is None
        assert "response_values" not in batch["items"][0]["trial"]
        assert client.post(confirm_url, json=body).json() == batch
        assert len(client.get(url(study)).json()["trials"]) == 4
    with TestClient(create_app(settings)) as client:
        restored = client.get(url(study) + f"/desirability-recommendations/{batch['batch_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json() == batch
        assert client.post(confirm_url, json=body).json() == batch
        current = client.get(url(study)).json()
        observed = client.put(url(study) + "/observations/batch", json=observations(current, (3,)))
        assert observed.status_code == 200, observed.text
        result = client.get(
            url(study) + f"/desirability-recommendations/{batch['batch_id']}"
        ).json()
        assert result["result_sha256"] == batch["result_sha256"]
        assert result["calculation"] == batch["calculation"]
        assert result["batch_state"] == "completed"
        assert result["items"][0]["current_trial"]["response_values"] == {
            "yield": 43.0,
            "cost": 6.0,
        }
        common = url(study) + "/recommendation-batches"
        assert client.get(common + f"/{batch['batch_id']}").json() == result
        assert client.get(common + "/latest").json()["item"] == result
        assert client.get(common).json()["items"] == [result]
    archive = tmp_path.parent / f"vector-{uuid4()}.tar.gz"
    destination = tmp_path.parent / f"vector-restored-{uuid4()}"
    backup_workspace(tmp_path, archive)
    restore_workspace(archive, destination)
    with TestClient(create_app(Settings(workspace_root=destination))) as client:
        restored = client.get(url(study) + f"/desirability-recommendations/{batch['batch_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json() == result


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    from app.api.v1.schemas.bo_desirability_calculation import DesirabilityCalculationResult
    from app.services import bo_desirability_worker
    from app.statistics.bo_desirability_core import calculate_desirability_recommendation

    def local_worker(request):
        with threadpool_limits(limits=1):
            result = calculate_desirability_recommendation(request.worker_payload())
        return SimpleNamespace(
            calculation=DesirabilityCalculationResult.model_validate_json(json.dumps(result))
        )

    monkeypatch.setattr(bo_desirability_worker, "run_desirability_calculation", local_worker)
    app = create_app(Settings(workspace_root=tmp_path / "workspace"))
    with TestClient(app) as client:
        study = completed(client)
        response = client.post(url(study) + "/desirability-reviews", json=review_request(study))
        assert response.status_code == 200, response.text
        review = response.json()
        confirm_url = url(study) + f"/desirability-reviews/{review['review_id']}/confirm"
        yield client, app, study, review, confirm_url


def test_review_owner_hash_expiry_and_q1_contract(reviewed):
    client, app, study, review, confirm_url = reviewed
    bad = client.post(confirm_url, json={"expected_config_sha256": "0" * 64})
    assert bad.status_code == 409
    other = create_study(client)
    wrong_owner = confirm_url.replace(study["study_id"], other["study_id"])
    assert (
        client.post(
            wrong_owner, json={"expected_config_sha256": review["config_sha256"]}
        ).status_code
        == 409
    )
    for value in (2, True, "1"):
        body = review_request(study)
        body["batch_size"] = value
        assert client.post(url(study) + "/desirability-reviews", json=body).status_code == 422
    app.state.bayesian_reviews.clear()
    expired = client.post(confirm_url, json={"expected_config_sha256": review["config_sha256"]})
    assert expired.status_code == 409
    assert len(client.get(url(study)).json()["trials"]) == 3


def test_concurrent_confirmations_and_competing_review(reviewed):
    client, _, study, review, confirm_url = reviewed
    competing = client.post(url(study) + "/desirability-reviews", json=review_request(study)).json()
    body = {"expected_config_sha256": review["config_sha256"]}
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: client.post(confirm_url, json=body), range(2)))
    assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
    assert replies[0].json() == replies[1].json()
    second = client.post(
        url(study) + f"/desirability-reviews/{competing['review_id']}/confirm",
        json={"expected_config_sha256": competing["config_sha256"]},
    )
    assert second.status_code == 409
    assert len(client.get(url(study)).json()["trials"]) == 4


def test_confirmation_transaction_failure_keeps_review_and_writes_nothing(reviewed):
    client, app, study, review, confirm_url = reviewed
    root = app.state.settings.workspace_root
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        db.execute(
            "CREATE TRIGGER synthetic_batch_failure "
            "BEFORE INSERT ON bayesian_recommendation_batch_items "
            "BEGIN SELECT RAISE(ABORT,'synthetic failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic failure"):
        client.post(confirm_url, json={"expected_config_sha256": review["config_sha256"]})
    assert len(client.get(url(study)).json()["trials"]) == 3
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        assert db.execute("SELECT count(*) FROM bayesian_recommendation_batches").fetchone() == (0,)
        db.execute("DROP TRIGGER synthetic_batch_failure")
    assert (
        client.post(
            confirm_url, json={"expected_config_sha256": review["config_sha256"]}
        ).status_code
        == 201
    )


def test_new_abandoned_trial_invalidates_review_without_advancing_history(reviewed):
    client, _, study, review, confirm_url = reviewed
    body = review_request(study)
    body["search"]["random_seed"] = 43
    second = client.post(url(study) + "/desirability-reviews", json=body)
    assert second.status_code == 200, second.text
    second = second.json()
    first = client.post(confirm_url, json={"expected_config_sha256": review["config_sha256"]})
    assert first.status_code == 201, first.text
    trial_id = first.json()["items"][0]["trial"]["trial_id"]
    abandoned = client.post(url(study) + f"/trials/{trial_id}/abandon")
    assert abandoned.status_code == 200, abandoned.text
    current = client.get(url(study)).json()
    assert current["observation_history"] == study["observation_history"]
    rejected = client.post(
        url(study) + f"/desirability-reviews/{second['review_id']}/confirm",
        json={"expected_config_sha256": second["config_sha256"]},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "bayesian_optimization_history_stale"
    assert client.get(url(study)).json()["trial_count"] == 4


def test_source_changes_during_fit_rejects_review(reviewed, monkeypatch):
    client, _, study, _, confirm_url = reviewed
    from app.services import bo_desirability_worker

    original = bo_desirability_worker.run_desirability_calculation

    def changed(request):
        calculated = original(request)
        close = client.post(
            url(study) + "/close",
            json={
                "target_status": "abandoned",
                "reason_code": "study_cancelled",
                "request_id": str(uuid4()),
                "expected_study_version_id": study["study_version_id"],
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
                "expected_observation_history_sha256": study["observation_history"][
                    "observation_history_sha256"
                ],
            },
        )
        assert close.status_code == 200, close.text
        return calculated

    # A real owner lifecycle change, not a fabricated stale error.
    monkeypatch.setattr(bo_desirability_worker, "run_desirability_calculation", changed)
    response = client.post(url(study) + "/desirability-reviews", json=review_request(study))
    assert response.status_code == 409
    assert len(client.get(url(study)).json()["trials"]) == 3


def test_saved_vector_report_and_source_tamper(reviewed, monkeypatch):
    from test_dedicated_report_sources import no_recompute
    from test_managed_report_api import VisibleReport

    from app.services import bayesian_studies

    original_reader = bayesian_studies._load_validated_study

    client, app, study, review, confirm_url = reviewed
    batch_response = client.post(
        confirm_url, json={"expected_config_sha256": review["config_sha256"]}
    )
    assert batch_response.status_code == 201, batch_response.text
    batch = batch_response.json()
    root = app.state.settings.workspace_root
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        result_json, result_hash = db.execute(
            "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches"
        ).fetchone()
    source = {
        "kind": "bayesian_history_revision",
        "study_id": study["study_id"],
        "study_version_id": study["study_version_id"],
        "definition_sha256": study["definition_sha256"],
        "history_revision_id": review["source_history_revision_id"],
        "expected_source_sha256": review["source_observation_history_sha256"],
        "attachment": {
            "kind": "batch",
            "batch_id": batch["batch_id"],
            "result_json_sha256": result_hash,
            "result_payload_sha256": batch["result_sha256"],
        },
    }
    no_recompute(monkeypatch)
    for locale in ("ko", "en"):
        request = {"source": source, "locale": locale}
        capability = client.post("/api/v1/reports/capability", json=request)
        assert capability.status_code == 200, capability.text
        report = client.post(
            "/api/v1/reports",
            json={**request, "expected_source_ref_sha256": capability.json()["source_ref_sha256"]},
        )
        assert report.status_code == 201, report.text
        report = report.json()
        download = client.post(
            f"/api/v1/reports/{report['export_id']}/download",
            json={"source": source, "expected_sha256": report["sha256"]},
        )
        assert download.status_code == 200, download.text
        assert hashlib.sha256(download.content).hexdigest() == report["sha256"]
        parsed = VisibleReport()
        parsed.feed(download.text)
        assert parsed.svgs == 2
        assert ("Beta moment-matched EI" if locale == "en" else "Beta 모멘트 근사 EI") in "".join(
            parsed.text
        )
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        assert db.execute(
            "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches"
        ).fetchone() == (result_json, result_hash)
        # Updating a blob plus its storage hash cannot bypass typed/source checks.
        bad = json.loads(result_json)
        bad["calculation"]["shared_model"]["response_ids"].reverse()
        encoded = json.dumps(bad, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        db.execute(
            "UPDATE bayesian_recommendation_batches SET result_json=?,result_sha256=?",
            (encoded, hashlib.sha256(encoded.encode()).hexdigest()),
        )
    monkeypatch.setattr(bayesian_studies, "_load_validated_study", original_reader)
    assert client.get(url(study)).status_code == 409


def test_migration_26_to_27_preserves_populated_scalar_and_vector(tmp_path, monkeypatch):
    from test_bayesian_batches_api import _completed_study
    from test_bayesian_review_api import _review_body

    from app.statistics.bo_recommendation_core import calculate_noise_aware_batch

    monkeypatch.setattr(
        "app.services.bayesian_noise_recommendations._run_worker",
        lambda payload, **kwargs: calculate_noise_aware_batch(payload),
    )
    settings = Settings(workspace_root=tmp_path)
    with monkeypatch.context() as context:
        context.setattr(metadata, "SCHEMA_VERSION", 26)
        context.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 26)
        )
        with TestClient(create_app(settings)) as client:
            vector = completed(client)
            scalar = _completed_study(client)
            response = client.post(
                url(scalar) + "/recommendation-batches", json=_review_body(scalar)
            )
            assert response.status_code == 201, response.text
            batch = response.json()
    tables = (
        "bayesian_trials",
        "bayesian_study_versions",
        "bayesian_observation_history_revisions",
        "bayesian_recommendation_batches",
        "bayesian_recommendation_batch_items",
    )

    def rows():
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
            return {
                table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                for table in tables
            }

    before = rows()
    with monkeypatch.context() as context:
        context.setattr(metadata, "SCHEMA_VERSION", 27)
        context.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 27)
        )
        assert metadata.initialize_metadata_store(tmp_path).schema_version == 27
    assert rows() == before
    with TestClient(create_app(settings)) as client:
        assert client.get(url(vector)).status_code == 200
        restored = client.get(url(scalar) + f"/recommendation-batches/{batch['batch_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json() == batch
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE bayesian_recommendation_batches SET result_schema_version=4")
