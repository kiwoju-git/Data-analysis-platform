"""Mixed typed coordinates keep the same source-CAS and explicit lifecycle semantics."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.unit.test_bayesian_study_lifecycle_api import _close_request
from tests.unit.test_bo_mixed_studies import request


def _observations(study):
    return {
        "request_id": str(uuid4()),
        "expected_study_version_id": study["study_version_id"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_observation_history_sha256": study["observation_history"][
            "observation_history_sha256"
        ],
        "observations": [
            {
                "trial_id": trial["trial_id"],
                "response_values": {"yield": float(trial["trial_number"])},
            }
            for trial in study["trials"]
            if trial["state"] == "pending"
        ],
    }


def test_mixed_http_observations_replicates_replay_abandon_close_restore_delete(tmp_path):
    settings = Settings(workspace_root=tmp_path / "mixed lifecycle 한글")
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/bayesian-studies/mixed", json=request())
        assert response.status_code == 201, response.text
        initial = response.json()
        endpoint = "/api/v1/bayesian-studies/" + initial["study_id"]
        assert client.get(endpoint).json() == initial
        assert client.get(endpoint + "/trials").json()["items"] == initial["trials"]
        body = _observations(initial)
        response = client.put(endpoint + "/observations/batch", json=body)
        assert response.status_code == 200, response.text
        assert response.json()["batch_schema_version"] == 2
        study = response.json()["study"]
        assert study["definition_sha256"] == initial["definition_sha256"]
        assert client.put(endpoint + "/observations/batch", json=body).json() == response.json()
        conflict = body | {
            "observations": [body["observations"][0] | {"response_values": {"yield": 99.0}}]
        }
        assert client.put(endpoint + "/observations/batch", json=conflict).status_code == 409
        assert client.get(endpoint + "/history").json()["total"] == 2
        parent = study["trials"][0]
        replicate = {
            "request_id": str(uuid4()),
            "count": 2,
            "confirm_replicate_intent": True,
            "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            "expected_history_sha256": study["observation_history"]["observation_history_sha256"],
            "total_trial_budget": 20,
        }
        replicate_url = endpoint + "/trials/" + parent["trial_id"] + "/replicates"
        response = client.post(replicate_url, json=replicate)
        assert response.status_code == 201, response.text
        children = response.json()["trials"]
        assert all(
            trial["actual_coordinates"] == parent["actual_coordinates"] for trial in children
        )
        replay = client.post(replicate_url, json=replicate)
        assert replay.status_code == 201 and replay.json()["replayed"]
        assert replay.json()["trials"] == children
        pending = client.get(endpoint).json()
        assert pending["trial_count"] == 10
        assert (
            client.post(replicate_url, json=replicate | {"request_id": str(uuid4())}).status_code
            == 409
        )
        for trial in children:
            abandoned = client.post(
                endpoint + "/trials/" + trial["trial_id"] + "/abandon",
                json={
                    "expected_history_revision_id": study["observation_history"][
                        "history_revision_id"
                    ],
                    "intent": "close_study",
                },
            )
            assert abandoned.status_code == 200, abandoned.text
            assert abandoned.json()["trial"]["actual_coordinates"] == parent["actual_coordinates"]
        current = client.get(endpoint).json()
        close = _close_request(current, target_status="abandoned", reason_code="study_cancelled")
        response = client.post(endpoint + "/close", json=close)
        assert response.status_code == 200, response.text
        closed = response.json()["study"]
        assert client.post(endpoint + "/close", json=close).json() == response.json()
        assert client.get(endpoint + "/initial-design.csv").status_code == 200
    with TestClient(create_app(settings)) as client:
        assert client.get(endpoint).json() == closed
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
