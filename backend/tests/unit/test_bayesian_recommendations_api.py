import copy
import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.bayesian import (
    BayesianRecommendationCreateRequest,
    BayesianStudyResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.bayesian_recommendations import (
    _optimization_error,
    _recommendation_worker_payload,
    _run_worker,
    _trial_budget_reached,
)
from app.statistics.bayesian_optimization import calculate_bayesian_recommendation
from app.storage.metadata import metadata_db_path


def _study_request() -> dict:
    return {
        "name": "one factor sequential study",
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
        "constraints": [
            {
                "constraint_id": "upper_x",
                "name": "Upper x",
                "terms": [{"factor_id": "x", "coefficient": 1.0}],
                "relation": "less_than_or_equal",
                "bound": 0.8,
            }
        ],
        "initial_design_seed": 17,
        "initial_design_size": 2,
    }


def _recommendation_request(
    history_revision_id: str,
    *,
    total_trial_budget: int = 10,
    random_seed: int = 23,
    candidate_count: int = 64,
    local_start_count: int = 2,
) -> dict:
    return {
        "expected_history_revision_id": history_revision_id,
        "search": {
            "random_seed": random_seed,
            "xi": 0.01,
            "candidate_count": candidate_count,
            "local_start_count": local_start_count,
            "max_iterations": 40,
            "max_evaluations": 512,
            "model_max_iterations": 30,
            "model_max_evaluations": 100,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 15_000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
            "total_trial_budget": total_trial_budget,
        },
    }


def _create_study(client: TestClient) -> dict:
    response = client.post("/api/v1/bayesian-studies", json=_study_request())
    assert response.status_code == 201
    return response.json()


def _complete_initial_trials(client: TestClient, study: dict) -> dict:
    history_revision_id = study["observation_history"]["history_revision_id"]
    for trial in study["trials"]:
        x_value = trial["actual_coordinates"]["x"]
        response = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 1.0 - (x_value - 0.25) ** 2,
                "expected_history_revision_id": history_revision_id,
            },
        )
        assert response.status_code == 200
        history_revision_id = response.json()["observation_history"]["history_revision_id"]
    restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
    assert restored.status_code == 200
    return restored.json()


def test_recommendation_create_restore_complete_and_tamper_detection(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        assert study["surrogate_available"] is True
        assert study["recommendation_available"] is True
        request_payload = _recommendation_request(
            study["observation_history"]["history_revision_id"]
        )

        created_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=request_payload,
        )
        assert created_response.status_code == 201
        created = created_response.json()

        duplicate_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=request_payload,
        )
        restored_response = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendations/{created['recommendation_id']}"
        )
        list_response = client.get(f"/api/v1/bayesian-studies/{study['study_id']}/recommendations")
        latest_response = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations/latest"
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["error"]["code"] == (
            "bayesian_optimization_pending_recommendation_exists"
        )
        assert restored_response.status_code == 200
        assert restored_response.json() == created
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1
        assert latest_response.status_code == 200
        assert latest_response.json()["item"] == created

        trial = created["trial"]
        complete_response = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 0.95,
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            },
        )
        assert complete_response.status_code == 200

        completed_study_response = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert completed_study_response.status_code == 200
        completed_study = completed_study_response.json()
        assert completed_study["completed_trial_count"] == 3
        assert completed_study["recommendation_available"] is True

        assert created["method_version"] == METHOD_VERSIONS["doe.bayesian_optimization"]
        assert created["method_version"] == "0.2.2"
        assert created["config_schema_version"] == 1
        assert created["result_schema_version"] == 1
        assert created["model_schema_version"] == 1
        assert created["trial"]["origin"] == "recommendation"
        assert created["trial"]["state"] == "pending"
        assert created["current_trial"]["state"] == "pending"
        assert created["is_latest"] is True
        assert created["requested_total_trial_budget"] == 10
        assert created["result"]["model"]["package_versions"]["scikit-learn"] == "1.7.2"
        assert "bayesian_optimization_confirmation_required" in created["result"]["warnings"]
        assert (
            created["provenance"]["source_observation_history_sha256"]
            == (study["observation_history"]["observation_history_sha256"])
        )
        assert (
            created["provenance"]["package_versions"]
            == created["result"]["model"]["package_versions"]
        )
        assert "workspace" not in json.dumps(created).lower()

        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                """
                UPDATE bayesian_recommendations
                SET config_json = json_set(config_json, '$.study_id', 'tampered')
                WHERE recommendation_id = ?;
                """,
                (created["recommendation_id"],),
            )

        tampered_response = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendations/{created['recommendation_id']}"
        )

    assert tampered_response.status_code == 409
    error = tampered_response.json()["error"]
    assert error["code"] == "bayesian_study_artifact_mismatch"
    assert str(tmp_path) not in json.dumps(error)


def test_recommendation_current_trial_state_changes_without_mutating_snapshot(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        created = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(study["observation_history"]["history_revision_id"]),
        ).json()
        transition = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{created['trial']['trial_id']}/observation",
            json={
                "objective_value": 0.9125,
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            },
        )
        latest = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations/latest"
        ).json()["item"]

    assert transition.status_code == 200
    assert latest["trial"]["state"] == "pending"
    assert latest["trial"]["objective_value"] is None
    assert latest["current_trial"]["state"] == "completed"
    assert latest["current_trial"]["objective_value"] == 0.9125
    assert latest["is_latest"] is True


def test_abandoned_trials_are_included_in_future_duplicate_exclusion(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    request = _study_request()
    request["initial_design_size"] = 3
    with TestClient(create_app(settings)) as client:
        created_response = client.post("/api/v1/bayesian-studies", json=request)
        assert created_response.status_code == 201
        study = created_response.json()
        abandoned_trial = study["trials"][0]
        abandoned = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{abandoned_trial['trial_id']}/abandon"
        )
        assert abandoned.status_code == 200
        history_revision_id = study["observation_history"]["history_revision_id"]
        for trial in study["trials"][1:]:
            completed = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}"
                f"/trials/{trial['trial_id']}/observation",
                json={
                    "objective_value": 1.0 - trial["normalized_coordinates"]["x"] ** 2,
                    "expected_history_revision_id": history_revision_id,
                },
            )
            assert completed.status_code == 200
            history_revision_id = completed.json()["observation_history"]["history_revision_id"]
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        body = BayesianRecommendationCreateRequest.model_validate(
            _recommendation_request(history_revision_id)
        )
        typed_study = BayesianStudyResponse.model_validate(restored)
        payload = _recommendation_worker_payload(
            typed_study,
            body,
            [trial for trial in typed_study.trials if trial.state == "completed"],
        )

    excluded = payload["excluded_normalized"]
    assert len(excluded) == 3
    assert [abandoned_trial["normalized_coordinates"]["x"]] in excluded


def test_recommendation_trial_abandon_is_allowed_and_point_is_not_recommended_again(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(workspace_root=tmp_path)

    def run_in_process(payload: dict, *, timeout_ms: int) -> dict:
        assert timeout_ms > 0
        return calculate_bayesian_recommendation(payload)

    monkeypatch.setattr(
        "app.services.bayesian_recommendations._run_worker",
        run_in_process,
    )
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        first = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(study["observation_history"]["history_revision_id"]),
        ).json()
        abandoned = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/trials/{first['trial']['trial_id']}/abandon"
        )
        assert abandoned.status_code == 200
        assert abandoned.json()["observation_history"] == study["observation_history"]
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        latest_after_abandon = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations/latest"
        ).json()["item"]
        second_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(
                restored["observation_history"]["history_revision_id"],
                random_seed=29,
            ),
        )

    assert latest_after_abandon["trial"]["state"] == "pending"
    assert latest_after_abandon["current_trial"]["state"] == "abandoned"
    assert second_response.status_code == 201
    first_x = first["trial"]["normalized_coordinates"]["x"]
    second_x = second_response.json()["trial"]["normalized_coordinates"]["x"]
    assert abs(first_x - second_x) > 1e-6


@pytest.mark.parametrize(
    ("trial_count", "request_budget", "expected"),
    [(49, 50, False), (50, 50, True), (199, 200, False), (200, 200, True)],
)
def test_trial_budget_boundary(
    trial_count: int,
    request_budget: int,
    expected: bool,
) -> None:
    assert (
        _trial_budget_reached(
            trial_count=trial_count,
            total_trial_budget=request_budget,
        )
        is expected
    )


def test_time_budget_internal_code_is_public_budget_error() -> None:
    error = _optimization_error("bayesian_optimization_time_budget_exhausted")

    assert error.code == "bayesian_optimization_budget_exhausted"
    assert error.status_code == 409


def test_worker_hard_timeout_is_public_budget_error(monkeypatch) -> None:
    class FakeQueue:
        def close(self) -> None:
            return None

        def join_thread(self) -> None:
            return None

    class FakeProcess:
        def start(self) -> None:
            return None

        def join(self, timeout: float) -> None:
            assert timeout > 0

        def is_alive(self) -> bool:
            return True

        def terminate(self) -> None:
            return None

        def close(self) -> None:
            return None

    class FakeContext:
        def Queue(self, maxsize: int) -> FakeQueue:
            assert maxsize == 1
            return FakeQueue()

        def Process(self, *, target, args) -> FakeProcess:
            assert target is not None
            assert args
            return FakeProcess()

    monkeypatch.setattr(
        "app.services.bayesian_recommendations.multiprocessing.get_context",
        lambda method: FakeContext(),
    )

    with pytest.raises(ApiError) as captured:
        _run_worker({}, timeout_ms=1_000)

    assert captured.value.code == "bayesian_optimization_budget_exhausted"


def test_latest_recommendation_is_correct_after_more_than_twenty_records(
    tmp_path,
    monkeypatch,
) -> None:
    settings = Settings(workspace_root=tmp_path)

    def run_in_process(payload: dict, *, timeout_ms: int) -> dict:
        assert timeout_ms > 0
        return calculate_bayesian_recommendation(payload)

    monkeypatch.setattr(
        "app.services.bayesian_recommendations._run_worker",
        run_in_process,
    )
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        recommendation_ids: list[str] = []
        for index in range(21):
            created_response = client.post(
                f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
                json=_recommendation_request(
                    study["observation_history"]["history_revision_id"],
                    total_trial_budget=30,
                    random_seed=100 + index,
                    candidate_count=32,
                    local_start_count=0,
                ),
            )
            assert created_response.status_code == 201, created_response.text
            created = created_response.json()
            recommendation_ids.append(created["recommendation_id"])
            x_value = created["trial"]["actual_coordinates"]["x"]
            completed = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}"
                f"/trials/{created['trial']['trial_id']}/observation",
                json={
                    "objective_value": 1.0 - (x_value - 0.25) ** 2,
                    "expected_history_revision_id": study["observation_history"][
                        "history_revision_id"
                    ],
                },
            )
            assert completed.status_code == 200
            study = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()

        first_page = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations" "?offset=0&limit=20"
        )
        latest = client.get(f"/api/v1/bayesian-studies/{study['study_id']}/recommendations/latest")
        oldest = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendations/{recommendation_ids[0]}"
        )

    assert first_page.status_code == 200
    assert first_page.json()["total"] == 21
    assert len(first_page.json()["items"]) == 20
    assert all(item["is_latest"] is False for item in first_page.json()["items"])
    assert latest.status_code == 200
    latest_item = latest.json()["item"]
    assert latest_item["recommendation_id"] == recommendation_ids[-1]
    assert latest_item["is_latest"] is True
    assert latest_item["trial"]["state"] == "pending"
    assert latest_item["current_trial"]["state"] == "completed"
    assert latest_item["requested_total_trial_budget"] == 30
    assert oldest.status_code == 200
    assert oldest.json()["is_latest"] is False
    assert oldest.json()["trial"]["state"] == "pending"
    assert oldest.json()["current_trial"]["state"] == "completed"


def test_stored_v020_recommendation_restores_without_relabeling(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        created = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(study["observation_history"]["history_revision_id"]),
        ).json()
        stored = _stored_json(
            metadata_db_path(tmp_path),
            created["recommendation_id"],
            "result_json",
        )
        stored["method_version"] = "0.2.0"
        stored["provenance"]["method_version"] = "0.2.0"
        result_json = _canonical_json(stored)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                """
                UPDATE bayesian_recommendations
                SET method_version = '0.2.0', result_json = ?, result_sha256 = ?
                WHERE recommendation_id = ?;
                """,
                (
                    result_json,
                    hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
                    created["recommendation_id"],
                ),
            )
        restored = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendations/{created['recommendation_id']}"
        )

    assert restored.status_code == 200
    assert restored.json()["method_version"] == "0.2.0"
    assert restored.json()["provenance"]["method_version"] == "0.2.0"


def test_planning_v010_cannot_be_forged_into_a_recommendation(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        created = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(study["observation_history"]["history_revision_id"]),
        ).json()
        stored = _stored_json(
            metadata_db_path(tmp_path),
            created["recommendation_id"],
            "result_json",
        )
        stored["method_version"] = "0.1.0"
        stored["provenance"]["method_version"] = "0.1.0"
        result_json = _canonical_json(stored)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                """
                UPDATE bayesian_recommendations
                SET method_version = '0.1.0', result_json = ?, result_sha256 = ?
                WHERE recommendation_id = ?;
                """,
                (
                    result_json,
                    hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
                    created["recommendation_id"],
                ),
            )
        restored = client.get(
            f"/api/v1/bayesian-studies/{study['study_id']}"
            f"/recommendations/{created['recommendation_id']}"
        )

    assert restored.status_code == 409
    assert restored.json()["error"]["code"] == "bayesian_study_artifact_mismatch"
    assert str(tmp_path) not in restored.text


def test_recommendation_rejects_incomplete_and_stale_history_without_running_model(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _create_study(client)
        incomplete = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(study["observation_history"]["history_revision_id"]),
        )
        stale_payload = _recommendation_request("00000000-0000-0000-0000-000000000001")
        stale = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=stale_payload,
        )

    assert incomplete.status_code == 409
    assert incomplete.json()["error"]["code"] == ("bayesian_optimization_history_incomplete")
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "bayesian_optimization_history_stale"


def test_recommendation_rejects_rehashed_cross_artifact_relationship_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    database_path = metadata_db_path(tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _complete_initial_trials(client, _create_study(client))
        created_response = client.post(
            f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
            json=_recommendation_request(study["observation_history"]["history_revision_id"]),
        )
        assert created_response.status_code == 201
        created = created_response.json()
        with sqlite3.connect(database_path) as connection:
            initial_history = connection.execute(
                """
                SELECT history_revision_id, observation_history_sha256
                FROM bayesian_observation_history_revisions
                WHERE study_version_id = ? AND revision_number = 1;
                """,
                (study["study_version_id"],),
            ).fetchone()
        assert initial_history is not None
        original_config = _stored_json(
            database_path,
            created["recommendation_id"],
            "config_json",
        )
        original_response = _stored_json(
            database_path,
            created["recommendation_id"],
            "result_json",
        )
        original_source = (
            created["source_history_revision_id"],
            created["source_observation_history_sha256"],
        )

        for case in (
            "result_coordinates",
            "request_budget",
            "result_budget",
            "model_observation_count",
            "incumbent",
            "constraint_evaluation",
            "required_warning",
            "source_history",
            "provenance_package",
        ):
            config = copy.deepcopy(original_config)
            response = copy.deepcopy(original_response)
            source = original_source
            if case == "result_coordinates":
                response["result"]["recommended_actual_coordinates"]["x"] += 0.05
            elif case == "request_budget":
                config["request"]["search"]["candidate_count"] += 1
            elif case == "result_budget":
                response["result"]["budget"]["candidate_count_requested"] += 1
            elif case == "model_observation_count":
                response["result"]["model"]["completed_observation_count"] += 1
            elif case == "incumbent":
                response["result"]["incumbent_objective"] += 0.25
            elif case == "constraint_evaluation":
                response["result"]["constraint_evaluations"][0]["lhs"] += 0.25
            elif case == "required_warning":
                response["result"]["warnings"].remove("bayesian_optimization_confirmation_required")
            elif case == "source_history":
                source = (str(initial_history[0]), str(initial_history[1]))
                config["source_history_revision_id"] = source[0]
                config["source_observation_history_sha256"] = source[1]
                config["request"]["expected_history_revision_id"] = source[0]
                response["source_history_revision_id"] = source[0]
                response["source_observation_history_sha256"] = source[1]
                response["provenance"]["source_history_revision_id"] = source[0]
                response["provenance"]["source_observation_history_sha256"] = source[1]
            elif case == "provenance_package":
                response["provenance"]["package_versions"]["scikit-learn"] = "0.0.0"
            _store_rehashed_recommendation(
                database_path,
                created["recommendation_id"],
                config=config,
                response=response,
                source=source,
            )

            for endpoint in (
                f"/api/v1/bayesian-studies/{study['study_id']}",
                f"/api/v1/bayesian-studies/{study['study_id']}/recommendations",
                f"/api/v1/bayesian-studies/{study['study_id']}"
                f"/recommendations/{created['recommendation_id']}",
            ):
                rejected = client.get(endpoint)
                assert rejected.status_code == 409, case
                assert rejected.json()["error"]["code"] == "bayesian_study_artifact_mismatch"
                assert str(tmp_path) not in json.dumps(rejected.json())

            _store_rehashed_recommendation(
                database_path,
                created["recommendation_id"],
                config=copy.deepcopy(original_config),
                response=copy.deepcopy(original_response),
                source=original_source,
            )
            restored = client.get(
                f"/api/v1/bayesian-studies/{study['study_id']}"
                f"/recommendations/{created['recommendation_id']}"
            )
            assert restored.status_code == 200, case


def _stored_json(database_path, recommendation_id: str, column: str) -> dict:
    assert column in {"config_json", "result_json"}
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            f"SELECT {column} FROM bayesian_recommendations WHERE recommendation_id = ?;",
            (recommendation_id,),
        ).fetchone()
    assert row is not None
    payload = json.loads(str(row[0]))
    assert isinstance(payload, dict)
    return payload


def _store_rehashed_recommendation(
    database_path,
    recommendation_id: str,
    *,
    config: dict,
    response: dict,
    source: tuple[str, str],
) -> None:
    config_json = _canonical_json(config)
    config_sha256 = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
    response["config_sha256"] = config_sha256
    result_payload_sha256 = hashlib.sha256(
        _canonical_json(response["result"]).encode("utf-8")
    ).hexdigest()
    response["result_payload_sha256"] = result_payload_sha256
    result_json = _canonical_json(response)
    result_sha256 = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE bayesian_recommendations
            SET source_history_revision_id = ?,
                source_observation_history_sha256 = ?,
                config_json = ?, config_sha256 = ?,
                result_json = ?, result_sha256 = ?, result_payload_sha256 = ?
            WHERE recommendation_id = ?;
            """,
            (
                source[0],
                source[1],
                config_json,
                config_sha256,
                result_json,
                result_sha256,
                result_payload_sha256,
                recommendation_id,
            ),
        )
        connection.commit()


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
