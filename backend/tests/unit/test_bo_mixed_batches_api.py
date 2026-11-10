"""Real mixed selection/atomic confirmation/immutable result workflow, synthetic only."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.bayesian_noise_recommendations import _json, _sha
from app.storage.metadata import metadata_db_path
from tests.unit.test_bo_mixed_lifecycle_api import _observations
from tests.unit.test_bo_mixed_planning_api import fit_options, source
from tests.unit.test_bo_mixed_studies import request


def prepare(client, *, fit):
    raw = request()
    raw["factors"][0].update(domain_kind="continuous", step=None, display_decimals=None)
    response = client.post("/api/v1/bayesian-studies/mixed", json=raw)
    assert response.status_code == 201, response.text
    study = response.json()
    endpoint = "/api/v1/bayesian-studies/" + study["study_id"]
    response = client.put(endpoint + "/observations/batch", json=_observations(study))
    assert response.status_code == 200, response.text
    study = response.json()["study"]
    model = None
    if fit:
        response = client.post(
            endpoint + "/mixed-planning-models",
            json=source(study)
            | {
                "request_id": str(uuid4()),
                "fit": fit_options(),
            },
        )
        assert response.status_code == 201, response.text
        model = response.json()
    candidate = source(study) | {
        "schema_version": 3,
        "request_id": str(uuid4()),
        "candidate_set_id": str(uuid4()),
        "name": "Synthetic ordered candidate rows",
        "expected_head_revision_id": None,
        "model_id": None if model is None else model["model_id"],
        "expected_model_sha256": None if model is None else model["snapshot_sha256"],
        "duplicate_tolerance": 1e-6,
        "source": {"kind": "seeded_uniform", "seed": 12, "count": 16},
    }
    response = client.post(endpoint + "/mixed-candidate-revisions", json=candidate)
    assert response.status_code == 201, response.text
    return study, endpoint, model, response.json()


def selection_body(study, model, page, *, size=2, policy=None):
    return source(study) | {
        "schema_version": 3,
        "request_id": str(uuid4()),
        "kind": "manual_ordered" if policy is None else "augmentation",
        "candidate_revision_id": page["revision"]["revision_id"],
        "expected_rows_sha256": page["revision"]["rows_sha256"],
        "model_id": None if model is None else model["model_id"],
        "expected_model_sha256": None if model is None else model["snapshot_sha256"],
        "row_ids": [row["row_id"] for row in page["items"][:size]] if policy is None else [],
        "policy": policy,
        "batch_size": size,
        "total_trial_budget": 40,
        "sample_count": 16,
        "max_moment_evaluations": 4096,
    }


def create_selection(client, endpoint, body):
    response = client.post(endpoint + "/mixed-selections", json=body)
    assert response.status_code == 201, response.text
    selection = response.json()
    assert client.post(endpoint + "/mixed-selections", json=body).json() == selection
    return selection


def confirm_payload(selection):
    return {
        "expected_config_sha256": selection["config_sha256"],
        "expected_result_sha256": selection["result_sha256"],
    }


def test_real_mixed_manual_batch_partial_measurement_restore_report(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "mixed batch 한글 workspace")
    with TestClient(create_app(settings)) as client:
        study, endpoint, model, page = prepare(client, fit=True)
        from app.services import bo_planning

        worker = bo_planning.run_planning_operation

        def no_refit(operation, *args, **kwargs):
            assert operation != "mixed_fit"
            return worker(operation, *args, **kwargs)

        monkeypatch.setattr(bo_planning, "run_planning_operation", no_refit)
        for policy in (
            "refine_ei_alternating_desirability_response_sd_v2",
            "confirm_mean_then_competitive_sd_v1",
        ):
            automatic = create_selection(
                client, endpoint, selection_body(study, model, page, size=1, policy=policy)
            )
            assert automatic["calculation"]["model_refit"] is False
            assert automatic["calculation"]["augmentation"]["policy"] == policy
            assert len(automatic["calculation"]["selected_rows"]) == 1
            assert client.get(endpoint).json() == study
        body = selection_body(study, model, page)
        selection = create_selection(client, endpoint, body)
        assert client.get(endpoint).json() == study
        confirm_url = endpoint + "/mixed-selections/" + selection["selection_id"] + "/confirm"
        response = client.post(confirm_url, json=confirm_payload(selection))
        assert response.status_code == 201, response.text
        batch = response.json()
        assert (
            batch["result_schema_version"],
            batch["method_version"],
            batch["item_schema_version"],
        ) == (10, "0.15.0", 5)
        assert batch["calculation"] == selection["calculation"]
        assert batch["batch_size"] == 2
        assert client.post(confirm_url, json=confirm_payload(selection)).json() == batch
        current = client.get(endpoint).json()
        assert current["trial_count"] == study["trial_count"] + 2
        assert all(item["trial"]["response_values"] is None for item in batch["items"])
        assert all(
            isinstance(item["trial"]["actual_coordinates"]["kind"], str) for item in batch["items"]
        )
        assert all("normalized_coordinates" not in item["trial"] for item in batch["items"])
        observed = _observations(current)
        observed["observations"] = [
            observed["observations"][-1] | {"response_values": {"yield": 4.25}}
        ]
        response = client.put(endpoint + "/observations/batch", json=observed)
        assert response.status_code == 200, response.text
        saved_url = endpoint + "/mixed-planning-batches/" + batch["batch_id"]
        response = client.get(saved_url)
        assert response.status_code == 200, response.text
        restored = response.json()
        assert restored["batch_state"] == "partially_completed"
        assert restored["result_sha256"] == batch["result_sha256"]
        assert restored["items"][1]["trial"]["response_values"] is None
        assert restored["items"][1]["current_trial"]["response_values"] == {"yield": 4.25}
        assert client.post(confirm_url, json=confirm_payload(selection)).json() == restored
        catalog_url = endpoint + "/recommendation-batches"
        assert client.get(catalog_url + "/" + batch["batch_id"]).json() == restored
        assert client.get(catalog_url + "/latest").json()["item"] == restored
        assert client.get(catalog_url).json()["items"] == [restored]

        monkeypatch.setattr(
            bo_planning,
            "run_planning_operation",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("report/read must not fit or evaluate")
            ),
        )
        descriptor_response = client.get(saved_url + "/report-source")
        assert descriptor_response.status_code == 200, descriptor_response.text
        descriptor = descriptor_response.json()
        for locale in ("en", "ko"):
            report = client.post(
                "/api/v1/reports",
                json={
                    "source": descriptor["source"],
                    "locale": locale,
                    "expected_source_ref_sha256": descriptor["source_ref_sha256"],
                },
            )
            assert report.status_code == 201, report.text
            artifact = report.json()
            downloaded = client.post(
                "/api/v1/reports/" + artifact["export_id"] + "/download",
                json={
                    "source": descriptor["source"],
                    "expected_sha256": artifact["sha256"],
                },
            )
            assert downloaded.status_code == 200, downloaded.text
            assert hashlib.sha256(downloaded.content).hexdigest() == artifact["sha256"]
            assert (
                'data-batch-rank="1"' in downloaded.text
                and 'data-batch-rank="2"' in downloaded.text
            )
            assert model["snapshot_sha256"] in downloaded.text
            assert "manual_ordered_mixed_model_v1" in downloaded.text
        assert client.get(saved_url).json() == restored
    with TestClient(create_app(settings)) as client:
        assert client.get(saved_url).json() == restored
        assert client.post(confirm_url, json=confirm_payload(selection)).json() == restored
        assert client.get(endpoint).json()["trial_count"] == current["trial_count"]

    from app.storage.workspace_backup import backup_workspace, restore_workspace
    from tests.unit.test_bayesian_study_lifecycle_api import _close_request

    archive, destination = tmp_path / "mixed-backup.tar.gz", tmp_path / "mixed restored workspace"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, destination)
    with TestClient(create_app(Settings(workspace_root=destination))) as client:
        assert client.get(saved_url).json() == restored
        restored_model = client.get(endpoint + "/mixed-planning-models/" + model["model_id"]).json()
        assert restored_model == model | {"source_is_current": False}
        assert client.get(saved_url + "/report-source").json() == descriptor
        pending = client.get(endpoint).json()
        completion = client.put(endpoint + "/observations/batch", json=_observations(pending))
        assert completion.status_code == 200, completion.text
        closed = client.post(
            endpoint + "/close",
            json=_close_request(
                completion.json()["study"],
                target_status="completed",
                reason_code="confirmation_complete",
            ),
        )
        assert closed.status_code == 200, closed.text
        preflight = client.get(endpoint + "/deletion-preflight")
        assert preflight.status_code == 200, preflight.text
        manifest = preflight.json()
        assert manifest["counts"]["report_count"] == 2
        for kind in (
            "planning_model",
            "candidate_set",
            "candidate_revision",
            "planning_selection",
            "planning_confirmation",
        ):
            assert manifest["counts"][kind + "_count"] == (3 if kind == "planning_selection" else 1)
        removed = client.request(
            "DELETE",
            endpoint,
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": manifest["deletion_manifest_sha256"],
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


def test_model_free_q8_atomic_rollback_and_retry_has_no_phantom_predictions(tmp_path):
    settings = Settings(workspace_root=tmp_path / "mixed atomic")
    with TestClient(create_app(settings), raise_server_exceptions=False) as client:
        study, endpoint, model, page = prepare(client, fit=False)
        selection = create_selection(
            client,
            endpoint,
            selection_body(study, model, page, size=8, policy="greedy_mixed_maximin_v1"),
        )
        confirm_url = endpoint + "/mixed-selections/" + selection["selection_id"] + "/confirm"
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            db.execute(
                "CREATE TRIGGER synthetic_batch_failure BEFORE INSERT ON "
                "bayesian_recommendation_batch_items WHEN NEW.rank=2 "
                "BEGIN SELECT RAISE(ABORT, 'synthetic fixture'); END"
            )
        failed = client.post(confirm_url, json=confirm_payload(selection))
        assert failed.status_code >= 400
        assert client.get(endpoint).json() == study
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            assert (
                db.execute("SELECT COUNT(*) FROM bayesian_recommendation_batches").fetchone()[0]
                == 0
            )
            assert (
                db.execute("SELECT COUNT(*) FROM bayesian_planning_confirmations").fetchone()[0]
                == 0
            )
            db.execute("DROP TRIGGER synthetic_batch_failure")
        response = client.post(confirm_url, json=confirm_payload(selection))
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["batch_size"] == 8 and len(batch["items"]) == 8
        assert batch["source"]["model_id"] is None
        assert batch["response_models"] is None and batch["incumbent"] is None
        assert all(
            "response_predictions" not in row for row in batch["calculation"]["selected_rows"]
        )
        assert all(item["trial"]["response_values"] is None for item in batch["items"])
        assert client.post(confirm_url, json=confirm_payload(selection)).json() == batch
        assert client.get(endpoint).json()["trial_count"] == study["trial_count"] + 8
        invalid = confirm_payload(selection) | {"expected_result_sha256": "0" * 64}
        assert client.post(confirm_url, json=invalid).status_code == 409


def test_mixed_saved_trial_coordinate_tampering_is_rejected_even_with_outer_hashes(tmp_path):
    settings = Settings(workspace_root=tmp_path / "mixed tamper")
    with TestClient(create_app(settings)) as client:
        study, endpoint, model, page = prepare(client, fit=False)
        selection = create_selection(
            client, endpoint, selection_body(study, model, page, policy="greedy_mixed_maximin_v1")
        )
        response = client.post(
            endpoint + "/mixed-selections/" + selection["selection_id"] + "/confirm",
            json=confirm_payload(selection),
        )
        assert response.status_code == 201, response.text
        batch = response.json()
        saved_url = endpoint + "/mixed-planning-batches/" + batch["batch_id"]
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            original = db.execute(
                "SELECT result_json,result_sha256 FROM bayesian_recommendation_batches "
                "WHERE batch_id=?",
                (batch["batch_id"],),
            ).fetchone()
            changed = deepcopy(json.loads(original[0]))
            changed["items"][0]["trial"]["actual_coordinates"]["kind"] = "changed identity"
            changed["items"][0]["current_trial"] = deepcopy(changed["items"][0]["trial"])
            changed["result_sha256"] = "0" * 64
            changed["result_sha256"] = _sha(changed)
            payload_json = _json(changed)
            db.execute(
                "UPDATE bayesian_recommendation_batches SET result_json=?,result_sha256=? "
                "WHERE batch_id=?",
                (
                    payload_json,
                    hashlib.sha256(payload_json.encode()).hexdigest(),
                    batch["batch_id"],
                ),
            )
        try:
            response = client.get(saved_url)
            assert response.status_code == 409, response.text
        finally:
            with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                db.execute(
                    "UPDATE bayesian_recommendation_batches SET result_json=?,result_sha256=? "
                    "WHERE batch_id=?",
                    (*original, batch["batch_id"]),
                )
        assert client.get(saved_url).json() == batch
