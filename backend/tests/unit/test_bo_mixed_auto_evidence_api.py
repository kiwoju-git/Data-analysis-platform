"""Synthetic mixed Auto receipts, exact-source confirmation, report and restore."""

import copy
import hashlib
import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.bo_planning import planning_json, planning_sha
from app.storage.metadata import metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bo_mixed_batches_api import confirm_payload, selection_body
from tests.unit.test_bo_mixed_lifecycle_api import _observations
from tests.unit.test_bo_mixed_planning_api import fit_options, source
from tests.unit.test_bo_mixed_studies import request
from tests.unit.test_bo_planning_api import _database_rows


def prepare(client, *, ordinal=False):
    raw = request()
    raw["factors"][0].update(domain_kind="continuous", step=None, display_decimals=None)
    if ordinal:
        raw["factors"][1].update(
            domain_kind="ordinal", correlation_policy="ordinal_monotone_latent_rbf_v1"
        )
    response = client.post("/api/v1/bayesian-studies/mixed", json=raw)
    assert response.status_code == 201, response.text
    study = response.json()
    endpoint = "/api/v1/bayesian-studies/" + study["study_id"]
    measured = _observations(study)
    for observation, trial in zip(measured["observations"], study["trials"], strict=True):
        observation["response_values"] = {"yield": 2 + 4 * trial["encoded_coordinates"]["x"]}
    response = client.put(endpoint + "/observations/batch", json=measured)
    assert response.status_code == 200, response.text
    study = response.json()["study"]
    response = client.post(
        endpoint + "/mixed-planning-models",
        json=source(study) | {"request_id": str(uuid4()), "fit": fit_options()},
    )
    assert response.status_code == 201, response.text
    model = response.json()
    response = client.post(
        endpoint + "/mixed-candidate-revisions",
        json=source(study)
        | {
            "schema_version": 3,
            "request_id": str(uuid4()),
            "candidate_set_id": str(uuid4()),
            "name": "Synthetic Auto candidates",
            "expected_head_revision_id": None,
            "model_id": None,
            "expected_model_sha256": None,
            "duplicate_tolerance": 1e-6,
            "ordinal_rank_distance": ordinal,
            "source": {"kind": "seeded_uniform", "seed": 12, "count": 16},
        },
    )
    assert response.status_code == 201, response.text
    return study, endpoint, model, response.json()


def auto_body(client, study, endpoint, model, page, *, threshold, ordinal=False):
    response = client.post(
        endpoint + "/mixed-planning-models/" + model["model_id"] + "/auto-strategy",
        json={
            "expected_model_sha256": model["snapshot_sha256"],
            "expected_history_sha256": model["history_sha256"],
            "r_squared_threshold": threshold,
        },
    )
    assert response.status_code == 200, response.text
    view = response.json()
    policy = view["decision"]["recommended_policy"]
    selected_model = None if policy == "greedy_mixed_maximin_v1" else model
    body = selection_body(study, selected_model, page, size=2, policy=policy)
    body.update(
        schema_version=5,
        ordinal_rank_distance=ordinal,
        auto_strategy={
            "schema_version": 1,
            "routing_model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "r_squared_threshold": threshold,
            "expected_decision_sha256": view["decision_sha256"],
        },
    )
    return body, view


@pytest.mark.parametrize("ordinal", [False, True])
def test_real_mixed_auto_evidence_persistence_and_legacy_preservation(
    tmp_path, monkeypatch, ordinal
):
    settings = Settings(workspace_root=tmp_path / "mixed Auto 한글 workspace")
    with TestClient(create_app(settings)) as client:
        study, endpoint, model, page = prepare(client, ordinal=ordinal)
        body, view = auto_body(client, study, endpoint, model, page, threshold=1, ordinal=ordinal)
        assert body["policy"] == "greedy_mixed_maximin_v1"
        assert view["decision"]["ordinal_rank_distance_requires_consent"] is ordinal
        from app.services import bo_mixed_selections

        original, operations = bo_mixed_selections._run, []

        def no_fit(operation, *args, **kwargs):
            assert operation in {"auto_mixed_augmentation", "mixed_augmentation"}
            operations.append(operation)
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_mixed_selections, "_run", no_fit)
        before = _database_rows(settings.workspace_root)
        invalid = copy.deepcopy(body)
        invalid["kind"] = "manual_ordered"
        assert client.post(endpoint + "/mixed-selections", json=invalid).status_code == 422
        for field, value in (
            ("expected_decision_sha256", "0" * 64),
            ("r_squared_threshold", 0.5),
            ("expected_model_sha256", "0" * 64),
        ):
            invalid = copy.deepcopy(body)
            invalid["auto_strategy"][field] = value
            rejected = client.post(endpoint + "/mixed-selections", json=invalid)
            assert rejected.status_code == 409, rejected.text
            assert _database_rows(settings.workspace_root) == before

        # Old requests produce the old canonical artifact, not a default Auto receipt.
        legacy = {k: v for k, v in body.items() if k != "auto_strategy"} | {
            "schema_version": 3,
            "request_id": str(uuid4()),
        }
        old = client.post(endpoint + "/mixed-selections", json=legacy)
        assert old.status_code == 201, old.text
        assert old.json()["schema_version"] == 3
        assert old.json()["calculation"]["schema_version"] == 3
        assert "auto_evidence" not in old.json()["calculation"]
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            old_bytes = db.execute(
                "SELECT config_json,result_json,config_sha256,result_sha256 "
                "FROM bayesian_planning_selections WHERE selection_id=?",
                (old.json()["selection_id"],),
            ).fetchone()

        selected_response = client.post(endpoint + "/mixed-selections", json=body)
        assert selected_response.status_code == 201, selected_response.text
        selected = selected_response.json()
        evidence = selected["calculation"]["auto_evidence"]
        assert (selected["schema_version"], selected["calculation"]["schema_version"]) == (5, 4)
        assert evidence["decision_sha256"] == view["decision_sha256"]
        assert evidence["diagnostic"] == {
            k: v for k, v in view["diagnostic"].items() if k != "source_is_current"
        }
        assert selected["model_id"] is None
        assert selected["calculation"]["prediction_evaluations"] == 0
        assert selected["calculation"]["augmentation"]["ordinal_rank_distance"] is ordinal
        assert client.get(endpoint).json() == study
        summaries = client.get(endpoint + "/mixed-selections").json()["items"]
        assert {row["schema_version"] for row in summaries} == {3, 5}
        count = len(operations)
        assert client.post(endpoint + "/mixed-selections", json=body).json() == selected
        assert len(operations) == count
        assert (
            client.post(endpoint + "/mixed-selections", json=body | {"batch_size": 1}).status_code
            == 409
        )

        # Same fitted source can also attach the all-pass Refine decision.
        refine, refine_view = auto_body(
            client, study, endpoint, model, page, threshold=0, ordinal=ordinal
        )
        assert refine["policy"] == "refine_ei_alternating_desirability_response_sd_v2"
        result = client.post(endpoint + "/mixed-selections", json=refine)
        assert result.status_code == 201, result.text
        assert result.json()["model_id"] == model["model_id"]
        assert (
            result.json()["calculation"]["auto_evidence"]["decision_sha256"]
            == refine_view["decision_sha256"]
        )

        selection_url = endpoint + "/mixed-selections/" + selected["selection_id"]
        confirmed = client.post(selection_url + "/confirm", json=confirm_payload(selected))
        assert confirmed.status_code == 201, confirmed.text
        batch = confirmed.json()
        assert (
            batch["result_schema_version"],
            batch["method_version"],
            batch["item_schema_version"],
        ) == (12, "0.16.0", 5)
        assert batch["response_models"] is None and batch["source"]["model_id"] is None
        assert batch["calculation"]["auto_evidence"] == evidence
        current = client.get(endpoint).json()
        observed = _observations(current)
        response = client.put(endpoint + "/observations/batch", json=observed)
        assert response.status_code == 200, response.text

        def no_calculation(*args, **kwargs):
            raise AssertionError("restore/report/replay must not fit, calculate or rerun LOO")

        monkeypatch.setattr(bo_mixed_selections, "_run", no_calculation)
        from app.statistics import bo_loo

        monkeypatch.setattr(bo_loo, "planning_loo", no_calculation)
        replay = client.post(endpoint + "/mixed-selections", json=body)
        assert replay.status_code == 201, replay.text
        assert replay.json()["result_sha256"] == selected["result_sha256"]
        assert not replay.json()["source_is_current"]
        batch_url = endpoint + "/mixed-planning-batches/" + batch["batch_id"]
        restored = client.get(batch_url)
        assert restored.status_code == 200, restored.text
        assert restored.json()["batch_state"] == "completed"
        assert (
            client.post(selection_url + "/confirm", json=confirm_payload(selected)).json()
            == restored.json()
        )
        generic = endpoint + "/recommendation-batches"
        assert client.get(generic + "/" + batch["batch_id"]).json() == restored.json()
        assert client.get(generic + "/latest").json()["item"] == restored.json()
        assert client.get(generic).json()["items"] == [restored.json()]
        descriptor = client.get(batch_url + "/report-source")
        assert descriptor.status_code == 200, descriptor.text
        descriptor = descriptor.json()
        assert "mixed_planning_batch_id=" + batch["batch_id"] in descriptor["open_target"]
        before = _database_rows(settings.workspace_root)
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
                json={"source": descriptor["source"], "expected_sha256": artifact["sha256"]},
            )
            assert downloaded.status_code == 200, downloaded.text
            assert hashlib.sha256(downloaded.content).hexdigest() == artifact["sha256"]
            assert 'data-auto-evidence="1"' in downloaded.text
            assert evidence["decision_sha256"] in downloaded.text
        assert _database_rows(settings.workspace_root) == before
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            assert (
                db.execute(
                    "SELECT config_json,result_json,config_sha256,result_sha256 "
                    "FROM bayesian_planning_selections WHERE selection_id=?",
                    (old.json()["selection_id"],),
                ).fetchone()
                == old_bytes
            )
            saved = db.execute(
                "SELECT result_json,result_sha256 FROM bayesian_planning_selections "
                "WHERE selection_id=?",
                (selected["selection_id"],),
            ).fetchone()
            corrupt = json.loads(saved[0])
            corrupt["auto_evidence"]["decision"]["threshold"] = 0.5
            db.execute(
                "UPDATE bayesian_planning_selections SET result_json=?,result_sha256=? "
                "WHERE selection_id=?",
                (planning_json(corrupt), planning_sha(corrupt), selected["selection_id"]),
            )
        assert client.get(selection_url).status_code == 409
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            db.execute(
                "UPDATE bayesian_planning_selections SET result_json=?,result_sha256=? "
                "WHERE selection_id=?",
                (*saved, selected["selection_id"]),
            )
    archive, destination = tmp_path / "backup.tar.gz", tmp_path / "restore mixed Auto"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, destination)
    with TestClient(create_app(Settings(workspace_root=destination))) as client:
        assert client.get(batch_url).json() == restored.json()
        assert client.get(selection_url).json()["calculation"]["auto_evidence"] == evidence


def test_mixed_routing_model_is_rechecked_in_write_transaction(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "mixed routing CAS")
    with TestClient(create_app(settings)) as client:
        study, endpoint, model, page = prepare(client)
        body, _ = auto_body(client, study, endpoint, model, page, threshold=1)
        from app.services import bo_mixed_selections

        original = bo_mixed_selections._run
        before = _database_rows(settings.workspace_root)

        def change_routing_after_worker(*args, **kwargs):
            result = original(*args, **kwargs)
            with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                db.execute(
                    "UPDATE bayesian_planning_models SET snapshot_sha256=? WHERE model_id=?",
                    ("0" * 64, model["model_id"]),
                )
            return result

        with monkeypatch.context() as patch:
            patch.setattr(bo_mixed_selections, "_run", change_routing_after_worker)
            try:
                rejected = client.post(endpoint + "/mixed-selections", json=body)
                assert rejected.status_code == 409, rejected.text
                assert rejected.json()["error"]["code"] == "bayesian_planning_model_mismatch"
            finally:
                with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
                    db.execute(
                        "UPDATE bayesian_planning_models SET snapshot_sha256=? WHERE model_id=?",
                        (model["snapshot_sha256"], model["model_id"]),
                    )
        assert _database_rows(settings.workspace_root) == before
        retry = client.post(endpoint + "/mixed-selections", json=body)
        assert retry.status_code == 201, retry.text
        assert retry.json()["model_id"] is None
