import math
import sqlite3

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def _study_request(*, goal_type: str = "maximize") -> dict:
    objective: dict[str, object] = {
        "name": "Response",
        "unit": None,
        "goal_type": goal_type,
        "observation_policy": "manual_single_observation",
    }
    if goal_type == "match_target":
        objective.update({"target_value": 0.8, "target_tolerance": 0.05})
    return {
        "name": "batch study",
        "factors": [
            {
                "factor_id": "x",
                "name": "Input",
                "low": -1.0,
                "high": 1.0,
                "unit": None,
            }
        ],
        "objective": objective,
        "constraints": [],
        "initial_design_seed": 17,
        "initial_design_size": 2,
    }


def _batch_request(history_id: str, *, batch_size: int, kind: str) -> dict:
    return {
        "expected_history_revision_id": history_id,
        "execution_mode": ("sequential_single" if batch_size == 1 else "parallel_batch"),
        "batch_size": batch_size,
        "acquisition": {
            "kind": kind,
            "exploration_profile": "balanced",
            "xi_standardized": 0.01,
        },
        "search": {
            "random_seed": 23,
            "candidate_count_per_step": 64,
            "local_start_count_per_step": 2,
            "max_iterations_per_step": 40,
            "max_evaluations_total": 1024,
            "model_max_iterations": 30,
            "model_max_evaluations": 100,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 15_000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
            "total_trial_budget": 10,
            "batch_policy": "greedy_posterior_mean_fantasy_ei_v1",
        },
    }


def _completed_study(client: TestClient, *, goal_type: str = "maximize") -> dict:
    created = client.post(
        "/api/v1/bayesian-studies",
        json=_study_request(goal_type=goal_type),
    )
    assert created.status_code == 201, created.json()
    study = created.json()
    history_id = study["observation_history"]["history_revision_id"]
    for trial in study["trials"]:
        x_value = trial["actual_coordinates"]["x"]
        completed = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 1.0 - (x_value - 0.25) ** 2,
                "expected_history_revision_id": history_id,
            },
        )
        assert completed.status_code == 200, completed.json()
        history_id = completed.json()["observation_history"]["history_revision_id"]
    restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
    assert restored.status_code == 200, restored.json()
    return restored.json()


def test_batch_create_is_atomic_distinct_and_blocks_until_terminal(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client)
        request = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=2,
            kind="expected_improvement",
        )
        created_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=request,
        )
        assert created_response.status_code == 201, created_response.json()
        created = created_response.json()
        assert created["batch_size"] == 2
        assert created["batch_state"] == "pending"
        assert [item["rank"] for item in created["items"]] == [1, 2]
        coordinates = [tuple(item["normalized_coordinates"].values()) for item in created["items"]]
        assert len(set(coordinates)) == 2
        assert created["items"][1]["fantasy_step"] == 1
        assert created["items"][1]["conditioned_on_item_ids"] == [created["items"][0]["item_id"]]
        blocked = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=request,
        )
        assert blocked.status_code == 409
        assert (
            blocked.json()["error"]["code"] == "bayesian_optimization_pending_recommendation_exists"
        )
        history_id = study["observation_history"]["history_revision_id"]
        first_trial = created["items"][0]["trial"]
        first_completed = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{first_trial['trial_id']}/observation",
            json={
                "objective_value": 0.75,
                "expected_history_revision_id": history_id,
            },
        )
        assert first_completed.status_code == 200, first_completed.json()
        history_id = first_completed.json()["observation_history"]["history_revision_id"]
        partial = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendation-batches/{created['batch_id']}"
        )
        assert partial.status_code == 200, partial.json()
        assert partial.json()["batch_state"] == "partially_completed"
        second_trial = created["items"][1]["trial"]
        second_completed = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{second_trial['trial_id']}/observation",
            json={
                "objective_value": 0.8,
                "expected_history_revision_id": history_id,
            },
        )
        assert second_completed.status_code == 200, second_completed.json()
        history_id = second_completed.json()["observation_history"]["history_revision_id"]
        closed = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendation-batches/{created['batch_id']}"
        )
        assert closed.status_code == 200, closed.json()
        assert closed.json()["batch_state"] == "completed"
        request["expected_history_revision_id"] = history_id
        next_batch = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=request,
        )
        assert next_batch.status_code == 201, next_batch.json()
        latest = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}" "/recommendation-batches/latest"
        )
        assert latest.status_code == 200, latest.json()
        assert latest.json()["item"]["batch_id"] == next_batch.json()["batch_id"]


def test_target_goal_uses_expected_target_improvement(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client, goal_type="match_target")
        created = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=_batch_request(
                study["observation_history"]["history_revision_id"],
                batch_size=1,
                kind="expected_target_improvement",
            ),
        )
    assert created.status_code == 201, created.json()
    item = created.json()["items"][0]
    assert item["acquisition_kind"] == "expected_target_improvement"
    assert item["target_value"] == 0.8
    assert math.isfinite(item["predicted_target_distance"])


def test_batch_size_larger_than_remaining_budget_is_not_truncated(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client)
        request = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=2,
            kind="expected_improvement",
        )
        request["search"]["total_trial_budget"] = len(study["trials"]) + 1
        response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=request,
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "bayesian_optimization_batch_budget_exceeded"


def test_parallel_batch_returns_exactly_eight_distinct_items(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client)
        request = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=8,
            kind="expected_improvement",
        )
        request["search"]["max_evaluations_total"] = 4096
        response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=request,
        )

    assert response.status_code == 201, response.json()
    items = response.json()["items"]
    assert len(items) == 8
    assert [item["rank"] for item in items] == list(range(1, 9))
    assert len({tuple(item["normalized_coordinates"].values()) for item in items}) == 8


def test_execution_mode_and_batch_size_are_not_interchangeable(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client)
        sequential = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=2,
            kind="expected_improvement",
        )
        sequential["execution_mode"] = "sequential_single"
        sequential_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=sequential,
        )
        parallel = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=1,
            kind="expected_improvement",
        )
        parallel["execution_mode"] = "parallel_batch"
        parallel_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=parallel,
        )

    assert sequential_response.status_code == 422
    assert parallel_response.status_code == 422


def test_exploration_presets_require_fixed_xi_and_custom_xi_is_preserved(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client)
        mismatched = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=1,
            kind="expected_improvement",
        )
        mismatched["acquisition"].update(
            {
                "exploration_profile": "exploration",
                "xi_standardized": 0.01,
            }
        )
        rejected = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=mismatched,
        )
        custom = _batch_request(
            study["observation_history"]["history_revision_id"],
            batch_size=1,
            kind="expected_improvement",
        )
        custom["acquisition"].update(
            {
                "exploration_profile": "custom",
                "xi_standardized": 0.37,
            }
        )
        accepted = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=custom,
        )

    assert rejected.status_code == 422
    assert accepted.status_code == 201, accepted.json()
    assert accepted.json()["acquisition"]["exploration_profile"] == "custom"
    assert accepted.json()["acquisition"]["xi_standardized"] == 0.37


def test_batch_restore_rejects_tampered_item_payload(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client)
        created = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches",
            json=_batch_request(
                study["observation_history"]["history_revision_id"],
                batch_size=2,
                kind="expected_improvement",
            ),
        ).json()
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                """
                UPDATE bayesian_recommendation_batch_items
                SET item_result_json = '{}'
                WHERE item_id = ?;
                """,
                (created["items"][0]["item_id"],),
            )
        restored = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendation-batches/{created['batch_id']}"
        )

    assert restored.status_code == 409
    assert restored.json()["error"]["code"] == "bayesian_study_artifact_mismatch"
