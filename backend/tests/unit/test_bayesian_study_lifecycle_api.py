import json
import sqlite3
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def _study_request(*, predecessor_study_id: str | None = None) -> dict:
    request = {
        "name": "lifecycle study",
        "factors": [
            {
                "factor_id": "x",
                "name": "Input",
                "low": -1.0,
                "high": 1.0,
                "unit": None,
            }
        ],
        "objective": {
            "name": "Response",
            "unit": None,
            "direction": "maximize",
            "observation_policy": "manual_single_observation",
        },
        "constraints": [],
        "initial_design_seed": 29,
        "initial_design_size": 2,
    }
    if predecessor_study_id is not None:
        request["predecessor_study_id"] = predecessor_study_id
    return request


def _create_study(client: TestClient, *, predecessor_study_id: str | None = None) -> dict:
    response = client.post(
        "/api/v1/bayesian-studies",
        json=_study_request(predecessor_study_id=predecessor_study_id),
    )
    assert response.status_code == 201
    return response.json()


def _complete_initial_trials(client: TestClient, study: dict) -> dict:
    history_id = study["observation_history"]["history_revision_id"]
    for trial in study["trials"]:
        response = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": float(trial["trial_number"]),
                "expected_history_revision_id": history_id,
            },
        )
        assert response.status_code == 200
        history_id = response.json()["observation_history"]["history_revision_id"]
    return client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()


def _create_recommendation(client: TestClient, study: dict) -> dict:
    response = client.post(
        f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
        json={
            "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            "search": {
                "random_seed": 31,
                "xi": 0.01,
                "candidate_count": 64,
                "local_start_count": 2,
                "max_iterations": 40,
                "max_evaluations": 512,
                "model_max_iterations": 30,
                "model_max_evaluations": 100,
                "hyperparameter_restart_count": 0,
                "time_budget_ms": 15_000,
                "jitter": 1e-8,
                "duplicate_tolerance": 1e-6,
                "total_trial_budget": 10,
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def _close_request(
    study: dict,
    *,
    target_status: str,
    reason_code: str,
    request_id: str | None = None,
) -> dict:
    return {
        "target_status": target_status,
        "reason_code": reason_code,
        "note": "terminal lifecycle decision",
        "request_id": request_id or str(uuid4()),
        "expected_study_version_id": study["study_version_id"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_observation_history_sha256": study["observation_history"][
            "observation_history_sha256"
        ],
    }


def _abandon_all_for_close(client: TestClient, study: dict) -> dict:
    history_id = study["observation_history"]["history_revision_id"]
    for trial in study["trials"]:
        response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}" f"/trials/{trial['trial_id']}/abandon",
            json={
                "expected_history_revision_id": history_id,
                "intent": "close_study",
            },
        )
        assert response.status_code == 200
        assert response.json()["observation_history"]["history_revision_id"] == history_id
    return client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()


def test_close_rejects_pending_trials_and_incomplete_completion(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        pending = _create_study(client)
        pending_response = client.post(
            f"/api/v1/bayesian-studies/{pending['study_id']}/close",
            json=_close_request(
                pending,
                target_status="abandoned",
                reason_code="study_cancelled",
            ),
        )

        observed = _complete_initial_trials(client, _create_study(client))
        completion_response = client.post(
            f"/api/v1/bayesian-studies/{observed['study_id']}/close",
            json=_close_request(
                observed,
                target_status="completed",
                reason_code="objective_satisfied",
            ),
        )

    assert pending_response.status_code == 409
    assert pending_response.json()["error"]["code"] == ("bayesian_study_close_pending_trials")
    assert completion_response.status_code == 409
    assert completion_response.json()["error"]["code"] == (
        "bayesian_study_completion_requirements_not_met"
    )


def test_deletion_preflight_blocks_active_study_and_requires_exact_confirmation(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client)
        preflight_response = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/deletion-preflight"
        )
        preflight = preflight_response.json()
        mismatch = client.request(
            "DELETE",
            f"/api/v1/bayesian-studies/{study['study_id']}",
            json={
                "confirmation_study_id": str(uuid4()),
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        blocked = client.request(
            "DELETE",
            f"/api/v1/bayesian-studies/{study['study_id']}",
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )

    assert preflight_response.status_code == 200
    assert preflight["eligible"] is False
    assert preflight["blockers"] == ["bayesian_study_deletion_active"]
    assert preflight["counts"]["file_count"] == 0
    assert preflight["counts"]["file_bytes"] == 0
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == ("bayesian_study_deletion_confirmation_mismatch")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "bayesian_study_deletion_active"


def test_explicit_abandonment_closes_below_minimum_and_restores_read_only(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _abandon_all_for_close(client, _create_study(client))
        request = _close_request(
            study,
            target_status="abandoned",
            reason_code="unsafe_or_infeasible",
        )
        closed_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/close",
            json=request,
        )
        restored_response = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        history_response = client.get(f"/api/v1/bayesian-studies/{study['study_id']}/history")

    assert closed_response.status_code == 200
    closed = closed_response.json()
    assert closed["study"]["status"] == "abandoned"
    assert closed["study"]["pending_trial_count"] == 0
    assert closed["lifecycle_event"] == closed["study"]["lifecycle_event"]
    assert closed["lifecycle_event"]["reason_code"] == "unsafe_or_infeasible"
    assert closed["lifecycle_event"]["final_abandoned_trial_count"] == 2
    assert len(closed["lifecycle_event"]["event_sha256"]) == 64
    assert restored_response.status_code == 200
    assert restored_response.json() == closed["study"]
    assert history_response.status_code == 200
    assert history_response.json()["total"] == 1


def test_closed_abandoned_study_deletes_its_exact_metadata_graph(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _abandon_all_for_close(client, _create_study(client))
        close_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/close",
            json=_close_request(
                study,
                target_status="abandoned",
                reason_code="study_cancelled",
            ),
        )
        assert close_response.status_code == 200
        preflight = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/deletion-preflight"
        ).json()
        deleted_response = client.request(
            "DELETE",
            f"/api/v1/bayesian-studies/{study['study_id']}",
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")

    assert preflight["eligible"] is True
    assert preflight["counts"] == {
        "study_count": 1,
        "study_version_count": 1,
        "trial_count": 2,
        "history_revision_count": 1,
        "history_head_count": 1,
        "recommendation_count": 0,
        "lifecycle_event_count": 1,
        "metadata_record_count": 7,
        "file_count": 0,
        "file_bytes": 0,
    }
    assert deleted_response.status_code == 200
    deleted = deleted_response.json()
    assert deleted["deleted_counts"] == preflight["counts"]
    assert deleted["deletion_manifest_sha256"] == preflight["deletion_manifest_sha256"]
    assert "objective" not in json.dumps(deleted).lower()
    assert str(tmp_path) not in json.dumps(deleted)
    assert restored.status_code == 404


def test_completed_close_is_idempotent_and_blocks_all_mutations(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        recommendation = _create_recommendation(client, study)
        trial = recommendation["trial"]
        transition = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 3.0,
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            },
        )
        assert transition.status_code == 200
        ready = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        request = _close_request(
            ready,
            target_status="completed",
            reason_code="confirmation_complete",
        )
        first = client.post(f"/api/v1/bayesian-studies/{study['study_id']}/close", json=request)
        retry = client.post(f"/api/v1/bayesian-studies/{study['study_id']}/close", json=request)
        conflict_request = {**request, "request_id": str(uuid4())}
        conflict = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/close",
            json=conflict_request,
        )
        observation = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 4.0,
                "expected_history_revision_id": ready["observation_history"]["history_revision_id"],
            },
        )
        abandon = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}" f"/trials/{trial['trial_id']}/abandon"
        )
        recommend = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json={
                "expected_history_revision_id": ready["observation_history"]["history_revision_id"],
                "search": {
                    "random_seed": 1,
                    "xi": 0.01,
                    "candidate_count": 64,
                    "local_start_count": 2,
                    "max_iterations": 40,
                    "max_evaluations": 512,
                    "model_max_iterations": 30,
                    "model_max_evaluations": 100,
                    "hyperparameter_restart_count": 0,
                    "time_budget_ms": 15_000,
                    "jitter": 1e-8,
                    "duplicate_tolerance": 1e-6,
                    "total_trial_budget": 10,
                },
            },
        )
        preflight = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/deletion-preflight"
        ).json()
        deleted = client.request(
            "DELETE",
            f"/api/v1/bayesian-studies/{study['study_id']}",
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json()["lifecycle_event"] == first.json()["lifecycle_event"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "bayesian_study_close_conflict"
    for response in (observation, abandon, recommend):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "bayesian_study_closed"
    assert preflight["counts"]["recommendation_count"] == 1
    assert deleted.status_code == 200


def test_lifecycle_tamper_is_rejected_without_path_leakage_and_successor_is_linked(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _abandon_all_for_close(client, _create_study(client))
        close_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/close",
            json=_close_request(
                study,
                target_status="abandoned",
                reason_code="resources_unavailable",
            ),
        )
        assert close_response.status_code == 200
        successor = _create_study(client, predecessor_study_id=study["study_id"])
        active_predecessor_response = client.post(
            "/api/v1/bayesian-studies",
            json=_study_request(predecessor_study_id=successor["study_id"]),
        )

        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                """
                UPDATE bayesian_study_lifecycle_events
                SET final_trial_count = final_trial_count + 1
                WHERE study_id = ?;
                """,
                (study["study_id"],),
            )
        tampered = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")

    assert successor["predecessor_study_id"] == study["study_id"]
    assert active_predecessor_response.status_code == 409
    assert active_predecessor_response.json()["error"]["code"] == (
        "bayesian_study_predecessor_invalid"
    )
    assert tampered.status_code == 409
    error = tampered.json()["error"]
    assert error["code"] == "bayesian_study_artifact_mismatch"
    assert str(tmp_path) not in json.dumps(error)


def test_successor_reference_and_stale_deletion_manifest_block_predecessor_delete(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        predecessor = _abandon_all_for_close(client, _create_study(client))
        close_response = client.post(
            f"/api/v1/bayesian-studies/{predecessor['study_id']}/close",
            json=_close_request(
                predecessor,
                target_status="abandoned",
                reason_code="resources_unavailable",
            ),
        )
        assert close_response.status_code == 200
        old_preflight = client.get(
            f"/api/v1/bayesian-studies/{predecessor['study_id']}/deletion-preflight"
        ).json()
        _create_study(client, predecessor_study_id=predecessor["study_id"])
        stale_delete = client.request(
            "DELETE",
            f"/api/v1/bayesian-studies/{predecessor['study_id']}",
            json={
                "confirmation_study_id": predecessor["study_id"],
                "expected_deletion_manifest_sha256": old_preflight["deletion_manifest_sha256"],
            },
        )
        current_preflight = client.get(
            f"/api/v1/bayesian-studies/{predecessor['study_id']}/deletion-preflight"
        ).json()
        referenced_delete = client.request(
            "DELETE",
            f"/api/v1/bayesian-studies/{predecessor['study_id']}",
            json={
                "confirmation_study_id": predecessor["study_id"],
                "expected_deletion_manifest_sha256": current_preflight["deletion_manifest_sha256"],
            },
        )

    assert old_preflight["eligible"] is True
    assert stale_delete.status_code == 409
    assert stale_delete.json()["error"]["code"] == ("bayesian_study_deletion_confirmation_mismatch")
    assert current_preflight["eligible"] is False
    assert current_preflight["successor_study_count"] == 1
    assert current_preflight["blockers"] == ["bayesian_study_deletion_referenced"]
    assert referenced_delete.status_code == 409
    assert referenced_delete.json()["error"]["code"] == ("bayesian_study_deletion_referenced")
