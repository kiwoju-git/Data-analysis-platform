"""Study-8 create/observe/fit/candidate/confirm/observe API path."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_study_lifecycle_api import _close_request
from tests.unit.test_bo_mixed_planning import payload
from tests.unit.test_bo_mixed_planning_api import fit_options, source


def request(mixed=False):
    process = []
    if mixed:
        process = [
            {
                "factor_id": "temp",
                "name": "Temp",
                "domain_kind": "discrete_numeric",
                "low": 10.0,
                "high": 30.0,
                "step": 10.0,
                "display_decimals": 0,
                "unit": "C",
            },
            {
                "factor_id": "lot",
                "name": "Lot",
                "domain_kind": "nominal",
                "levels": ["A", "B"],
                "correlation_policy": "equal_positive_correlation_v1",
                "unit": None,
            },
        ]
    return {
        "schema_version": 8,
        "name": "Synthetic mixture",
        "mixture": {
            "total": 1.0,
            "coding": "lower",
            "components": [
                {"factor_id": "a", "name": "A", "low": 0.1, "high": 0.8, "unit": "g"},
                {"factor_id": "b", "name": "B", "low": 0.1, "high": 0.8, "unit": "g"},
                {"factor_id": "fixed", "name": "Fixed", "low": 0.1, "high": 0.1, "unit": "g"},
            ],
        },
        "process_factors": process,
        "objective": payload()["objective"],
        "constraints": [],
        "initial_design_seed": 9,
        "initial_design_size": 8,
    }


def observations(study):
    return {
        "request_id": str(uuid4()),
        "expected_study_version_id": study["study_version_id"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_observation_history_sha256": study["observation_history"][
            "observation_history_sha256"
        ],
        "observations": [
            {
                "trial_id": t["trial_id"],
                "response_values": {
                    "yield": t["actual_coordinates"]["a"] * 3 - t["actual_coordinates"]["b"]
                },
            }
            for t in study["trials"]
            if t["state"] == "pending"
        ],
    }


@pytest.mark.parametrize("mixed", [False, True])
def test_real_mixture_workflow_is_atomic_and_restorable(tmp_path, mixed, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "mixture workspace")
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/v1/bayesian-studies/mixture", json=request(mixed))
        assert created.status_code == 201, created.text
        study = created.json()
        endpoint = "/api/v1/bayesian-studies/" + study["study_id"]
        completed = client.put(endpoint + "/observations/batch", json=observations(study))
        assert completed.status_code == 200, completed.text
        study = completed.json()["study"]
        model_body = {**source(study), "request_id": str(uuid4()), "fit": fit_options()}
        fitted = client.post(endpoint + "/mixture-planning-models", json=model_body)
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        candidate_body = {
            **source(study),
            "schema_version": 4,
            "request_id": str(uuid4()),
            "candidate_set_id": str(uuid4()),
            "name": "Synthetic candidates",
            "model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "source": {"kind": "seeded_uniform", "seed": 17, "count": 8},
        }
        candidate = client.post(endpoint + "/mixture-candidate-revisions", json=candidate_body)
        assert candidate.status_code == 201, candidate.text
        page = candidate.json()
        assert all(item["constraints_satisfied"] for item in page["items"])
        point = page["items"][0]["actual_coordinates"]
        bad = client.post(
            endpoint + "/mixture-planning-models/" + model["model_id"] + "/evaluate",
            json={
                "expected_model_sha256": model["snapshot_sha256"],
                "points": [{**point, "a": point["a"] + 0.01}],
            },
        )
        assert bad.status_code in {409, 422}, bad.text
        selection_body = {
            **source(study),
            "schema_version": 6,
            "request_id": str(uuid4()),
            "candidate_revision_id": page["revision"]["revision_id"],
            "expected_rows_sha256": page["revision"]["rows_sha256"],
            "model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "policy": "manual_mixture_base_posterior_v1",
            "row_ids": [page["items"][0]["row_id"]],
            "batch_size": 1,
            "total_trial_budget": 20,
        }
        selected = client.post(endpoint + "/mixture-selections", json=selection_body)
        assert selected.status_code == 201, selected.text
        selection = selected.json()
        confirm = {
            "expected_config_sha256": selection["config_sha256"],
            "expected_result_sha256": selection["result_sha256"],
        }
        path = endpoint + "/mixture-selections/" + selection["selection_id"] + "/confirm"
        rejected = client.post(path, json={**confirm, "expected_result_sha256": "0" * 64})
        assert rejected.status_code == 409
        assert client.get(endpoint).json()["pending_trial_count"] == 0
        confirmed = client.post(path, json=confirm)
        assert confirmed.status_code == 201, confirmed.text
        from app.services import bo_mixture_workflow

        def forbidden_worker(*args, **kwargs):
            raise AssertionError(
                "historical reads and exact confirmation replay must not run workers"
            )

        monkeypatch.setattr(bo_mixture_workflow, "_run", forbidden_worker)
        assert client.post(path, json=confirm).json() == confirmed.json()
        current = client.get(endpoint).json()
        assert current["pending_trial_count"] == 1
        saved = client.put(endpoint + "/observations/batch", json=observations(current))
        assert saved.status_code == 200, saved.text
        current = saved.json()["study"]
        assert current["completed_trial_count"] == 9
        assert current["recommendation_available"]
    with TestClient(create_app(settings)) as client:
        assert (
            client.get(endpoint + "/mixture-planning-models/" + model["model_id"]).status_code
            == 200
        )

        assert (
            client.get(
                endpoint + "/mixture-planning-batches/" + selection["selection_id"]
            ).status_code
            == 200
        )


def test_mixture_replicate_replay_close_backup_restore_and_delete(tmp_path):
    root = tmp_path / "mixture lifecycle workspace"
    settings = Settings(workspace_root=root)
    with TestClient(create_app(settings)) as client:
        created = client.post("/api/v1/bayesian-studies/mixture", json=request(True))
        assert created.status_code == 201, created.text
        initial = created.json()
        endpoint = "/api/v1/bayesian-studies/" + initial["study_id"]
        completed = client.put(endpoint + "/observations/batch", json=observations(initial))
        assert completed.status_code == 200, completed.text
        study = completed.json()["study"]
        parent = study["trials"][0]
        replicate = {
            "request_id": str(uuid4()),
            "count": 2,
            "confirm_replicate_intent": True,
            "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            "expected_history_sha256": study["observation_history"]["observation_history_sha256"],
            "total_trial_budget": 20,
        }
        path = endpoint + "/trials/" + parent["trial_id"] + "/replicates"
        response = client.post(path, json=replicate)
        assert response.status_code == 201, response.text
        assert response.json()["schema_version"] == 3
        children = response.json()["trials"]
        assert all(t["actual_coordinates"] == parent["actual_coordinates"] for t in children)
        replay = client.post(path, json=replicate)
        assert replay.status_code == 201 and replay.json()["replayed"]
        assert replay.json()["trials"] == children
        conflict = client.post(path, json={**replicate, "count": 1})
        assert conflict.status_code == 409
        current = client.get(endpoint).json()
        assert current["trial_count"] == 10
        observed = client.put(endpoint + "/observations/batch", json=observations(current))
        assert observed.status_code == 200, observed.text
        study = observed.json()["study"]
        close = client.post(
            endpoint + "/close",
            json=_close_request(study, target_status="abandoned", reason_code="study_cancelled"),
        )
        assert close.status_code == 200, close.text
        closed = close.json()["study"]
        csv = client.get(endpoint + "/initial-design.csv")
        assert csv.status_code == 200, csv.text
        assert "Fixed [g]" in csv.text
    archive, restored = tmp_path / "mixture.zip", tmp_path / "restored mixture"
    backup_workspace(root, archive)
    restore_workspace(archive, restored)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        response = client.get(endpoint)
        assert response.status_code == 200, response.text
        assert response.json() == closed
        preflight = client.get(endpoint + "/deletion-preflight")
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["counts"]["replicate_request_count"] == 1
        deleted = client.request(
            "DELETE",
            endpoint,
            json={
                "confirmation_study_id": closed["study_id"],
                "expected_deletion_manifest_sha256": preflight.json()["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert client.get(endpoint).status_code == 404
