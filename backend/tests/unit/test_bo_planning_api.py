"""Real HTTP/owned-worker planning lifecycle using only synthetic observations."""

import hashlib
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import observations, url
from tests.unit.test_bo_desirability_public_batch import batch_request
from tests.unit.test_bo_desirability_review_api import completed


def fit_request(study):
    return {"request_id": str(uuid4()), "fit": batch_request(study, 2)}


def candidate_request(study, model):
    return {
        "request_id": str(uuid4()),
        "candidate_set_id": str(uuid4()),
        "name": "Synthetic candidates",
        "model_id": model["model_id"],
        "expected_model_sha256": model["snapshot_sha256"],
        "expected_history_revision_id": model["source_history_revision_id"],
        "expected_history_sha256": model["history_sha256"],
        "expected_trial_count": len(study["trials"]),
        "expected_head_revision_id": None,
        "source": {"kind": "explicit_rows", "points": [{"x": 1.23}, {"x": 6.33}, {"x": 8.12}]},
        "include_constraint_violations": False,
    }


def selection_request(study, model, page):
    candidate = candidate_request(study, model)
    return {
        key: candidate[key]
        for key in (
            "model_id",
            "expected_model_sha256",
            "expected_history_revision_id",
            "expected_history_sha256",
            "expected_trial_count",
        )
    } | {
        "request_id": str(uuid4()),
        "candidate_revision_id": page["revision"]["revision_id"],
        "expected_rows_sha256": page["revision"]["rows_sha256"],
        "row_ids": [row["row_id"] for row in page["items"][:2]],
        "total_trial_budget": 20,
    }


def _database_rows(root):
    with sqlite3.connect(metadata_db_path(root)) as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in (
                "bayesian_planning_models",
                "bayesian_candidate_revisions",
                "bayesian_planning_selections",
                "bayesian_planning_confirmations",
                "bayesian_observation_history_revisions",
            )
        }


def test_real_planning_manual_batch_restore_backup_and_report(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "workspace")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        fit = fit_request(study)
        response = client.post(url(study) + "/planning-models", json=fit)
        assert response.status_code == 201, response.text
        model = response.json()
        assert model["model_reusable_without_refit"] and model["source_is_current"]
        assert client.get(url(study)).json() == study
        from app.services import bo_planning

        original = bo_planning.run_planning_operation

        def no_new_fit(operation, *args, **kwargs):
            assert operation != "fit", "saved planning must not refit"
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_planning, "run_planning_operation", no_new_fit)
        assert client.post(url(study) + "/planning-models", json=fit).json() == model
        assert (
            client.get(url(study) + "/planning-models").json()["items"][0]["model_id"]
            == model["model_id"]
        )
        body = candidate_request(study, model)
        response = client.post(url(study) + "/candidate-revisions", json=body)
        assert response.status_code == 201, response.text
        page = response.json()
        assert page["revision"]["row_count"] == 3
        with monkeypatch.context() as context:
            context.setattr(
                bo_planning,
                "_read_model",
                lambda *args: pytest.fail("list must not load GP arrays"),
            )
            context.setattr(
                bo_planning,
                "_read_revision",
                lambda *args: pytest.fail("list must not load full candidate rows"),
            )
            listed = client.get(url(study) + "/candidate-sets")
            assert listed.status_code == 200, listed.text
            assert listed.json()["items"] == [page["revision"]]
        assert client.post(url(study) + "/candidate-revisions", json=body).json() == page
        revision_id = page["revision"]["revision_id"]
        later_page = client.get(url(study) + f"/candidate-revisions/{revision_id}?offset=1&limit=1")
        assert later_page.status_code == 200, later_page.text
        assert later_page.json()["items"] == [page["items"][1]]
        evaluated = client.post(
            url(study) + f"/planning-models/{model['model_id']}/evaluate",
            json={
                "expected_model_sha256": model["snapshot_sha256"],
                "points": body["source"]["points"],
            },
        )
        assert evaluated.status_code == 200, evaluated.text
        assert evaluated.json()["model_refit"] is False
        assert evaluated.json()["eligibility_is_current"] is True
        selection_body = selection_request(study, model, page)
        response = client.post(url(study) + "/planning-selections", json=selection_body)
        assert response.status_code == 201, response.text
        selection = response.json()
        assert selection["calculation"]["items"][0]["planning"]["score"] == pytest.approx(
            evaluated.json()["items"][0]["acquisition"]["value"],
            rel=2e-11,
        )
        assert client.get(url(study)).json()["trials"] == study["trials"]
        confirm_url = url(study) + f"/planning-selections/{selection['selection_id']}/confirm"
        confirm = {
            "expected_config_sha256": selection["config_sha256"],
            "expected_result_sha256": selection["result_sha256"],
        }
        response = client.post(confirm_url, json=confirm)
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["result_schema_version"] == 8 and batch["method_version"] == "0.13.0"
        assert batch["batch_policy"] == "manual_ordered_fixed_model_v1"
        assert batch["calculation"] == selection["calculation"]
        assert "search_budget" not in batch["calculation"]
        assert client.post(confirm_url, json=confirm).json() == batch
        current = client.get(url(study)).json()
        assert len(current["trials"]) == len(study["trials"]) + 2
        for item in batch["items"]:
            assert item["trial"]["state"] == "pending" and item["trial"]["objective_value"] is None
        common = url(study) + "/recommendation-batches"
        assert client.get(common + f"/{batch['batch_id']}").json() == batch
        assert client.get(common + "/latest").json()["item"] == batch
        assert client.get(common).json()["items"] == [batch]
        assert (
            client.put(
                url(study) + "/observations/batch", json=observations(current, (4,))
            ).status_code
            == 200
        )
        saved_url = url(study) + f"/planning-batches/{batch['batch_id']}"
        stored = client.get(saved_url)
        assert stored.status_code == 200, stored.text
        restored_batch = stored.json()
        assert restored_batch["batch_state"] == "partially_completed"
        assert restored_batch["result_sha256"] == batch["result_sha256"]
        before_report = _database_rows(settings.workspace_root)
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            json_hash = db.execute(
                "SELECT result_sha256 FROM bayesian_recommendation_batches WHERE batch_id=?",
                (batch["batch_id"],),
            ).fetchone()[0]
        source = {
            "kind": "bayesian_history_revision",
            "study_id": study["study_id"],
            "study_version_id": study["study_version_id"],
            "definition_sha256": study["definition_sha256"],
            "history_revision_id": model["source_history_revision_id"],
            "expected_source_sha256": model["history_sha256"],
            "attachment": {
                "kind": "batch",
                "batch_id": batch["batch_id"],
                "result_json_sha256": json_hash,
                "result_payload_sha256": batch["result_sha256"],
            },
        }
        descriptor_response = client.get(saved_url + "/report-source")
        assert descriptor_response.status_code == 200, descriptor_response.text
        descriptor = descriptor_response.json()
        assert descriptor["source"] == source
        assert descriptor["stale"] is True
        assert f"planning_batch_id={batch['batch_id']}" in descriptor["open_target"]
        catalog = client.get(
            "/api/v1/reports/sources?source_kind=bayesian_history_revision&limit=100"
        )
        assert catalog.status_code == 200, catalog.text
        assert descriptor in catalog.json()["items"]
        assert (
            client.get(
                f"/api/v1/bayesian-studies/{uuid4()}/planning-batches/{batch['batch_id']}/report-source"
            ).status_code
            == 404
        )
        for locale in ("en", "ko"):
            capability = client.post(
                "/api/v1/reports/capability", json={"source": source, "locale": locale}
            )
            assert capability.status_code == 200, capability.text
            assert capability.json()["source_ref_sha256"] == descriptor["source_ref_sha256"]
            report = client.post(
                "/api/v1/reports",
                json={
                    "source": source,
                    "locale": locale,
                    "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
                },
            )
            assert report.status_code == 201, report.text
            record = report.json()
            downloaded = client.post(
                f"/api/v1/reports/{record['export_id']}/download",
                json={"source": source, "expected_sha256": record["sha256"]},
            )
            assert downloaded.status_code == 200, downloaded.text
            assert "manual_ordered_fixed_model_v1" in downloaded.text
            assert model["snapshot_sha256"] in downloaded.text
            assert hashlib.sha256(downloaded.content).hexdigest() == record["sha256"]
        assert _database_rows(settings.workspace_root) == before_report
    archive = tmp_path / "planning-backup.tar.gz"
    destination = tmp_path / "restored workspace"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, destination)
    with TestClient(create_app(Settings(workspace_root=destination))) as client:
        assert client.get(saved_url).json() == restored_batch
        assert (
            client.get(url(study) + f"/candidate-revisions/{revision_id}").json()["items"]
            == page["items"]
        )
        assert client.get(url(study) + f"/planning-models/{model['model_id']}").status_code == 200
        from tests.unit.test_bayesian_study_lifecycle_api import _close_request

        current = client.get(url(study)).json()
        completion = client.put(
            url(study) + "/observations/batch", json=observations(current, (3,))
        )
        assert completion.status_code == 200, completion.text
        closed = client.post(
            url(study) + "/close",
            json=_close_request(
                completion.json()["study"],
                target_status="completed",
                reason_code="confirmation_complete",
            ),
        )
        assert closed.status_code == 200, closed.text
        preflight_response = client.get(url(study) + "/deletion-preflight")
        assert preflight_response.status_code == 200, preflight_response.text
        preflight = preflight_response.json()
        for kind in (
            "planning_model",
            "candidate_set",
            "candidate_revision",
            "planning_selection",
            "planning_confirmation",
        ):
            assert preflight["counts"][kind + "_count"] == 1
        assert preflight["counts"]["report_count"] == 2
        removed = client.request(
            "DELETE",
            url(study),
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        assert removed.status_code == 200, removed.text
        assert client.get(saved_url).status_code == 404
        with sqlite3.connect(metadata_db_path(destination)) as db:
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            for table in (
                "bayesian_planning_models",
                "bayesian_candidate_sets",
                "bayesian_candidate_revisions",
                "bayesian_candidate_heads",
                "bayesian_planning_selections",
                "bayesian_planning_confirmations",
            ):
                assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("point", [{"x": "1"}, {"x": True}, {"x": None}, {"wrong": 1.0}])
def test_invalid_point_contract_never_enters_worker(tmp_path, monkeypatch, point):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid point must not enter worker")

    monkeypatch.setattr("app.services.bo_planning.run_planning_operation", forbidden)
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        response = client.post(
            url(study) + f"/planning-models/{uuid4()}/evaluate",
            json={
                "expected_model_sha256": "a" * 64,
                "points": [point],
            },
        )
        assert response.status_code in {404, 422}


def test_fit_budget_is_not_a_new_trial_budget(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        body = fit_request(study)
        body["fit"]["total_trial_budget"] = len(study["trials"])
        response = client.post(url(study) + "/planning-models", json=body)
        assert response.status_code == 201, response.text
        assert client.get(url(study)).json()["trial_count"] == len(study["trials"])


def test_corrupt_worker_fit_is_rejected_before_any_model_commit(tmp_path, monkeypatch):
    def corrupt(*args, **kwargs):
        return {"calculation_request": {}, "response_states": {}}

    monkeypatch.setattr("app.services.bo_planning.run_planning_operation", corrupt)
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        response = client.post(url(study) + "/planning-models", json=fit_request(study))
        assert response.status_code == 409
        assert client.get(url(study) + "/planning-models").json() == {"items": []}
