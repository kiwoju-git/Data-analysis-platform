from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _request(*, policy: str = "latin_hypercube_random_cd_v1") -> dict:
    return {
        "name": "LHS initialized study",
        "factors": [
            {"factor_id": "x1", "name": "Input 1", "low": -1, "high": 1},
            {"factor_id": "x2", "name": "Input 2", "low": 0, "high": 10},
        ],
        "objective": {
            "name": "Response",
            "direction": "maximize",
            "observation_policy": "manual_single_observation",
        },
        "constraints": [],
        "initial_design_seed": 23,
        "initial_design_size": 3,
        "initial_design_policy": policy,
    }


def test_bayesian_lhs_trials_require_real_observations_before_recommendation(tmp_path) -> None:
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created_response = client.post("/api/v1/bayesian-studies", json=_request())
        assert created_response.status_code == 201
        study = created_response.json()

        assert study["study_schema_version"] == 4
        assert study["method_version"] == "0.5.0"
        assert study["initial_design"]["policy"] == "latin_hypercube_random_cd_v1"
        assert study["initial_design"]["strata_valid"] is True
        assert study["completed_trial_count"] == 0
        assert study["surrogate_available"] is False
        assert study["recommendation_available"] is False
        assert all(item["state"] == "pending" for item in study["trials"])
        assert all(item["objective_value"] is None for item in study["trials"])

        for index, trial in enumerate(study["trials"], start=1):
            observation = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}"
                f"/trials/{trial['trial_id']}/observation",
                json={
                    "objective_value": float(index),
                    "expected_history_revision_id": study["observation_history"][
                        "history_revision_id"
                    ],
                },
            )
            assert observation.status_code == 200
            restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
            assert restored.status_code == 200
            study = restored.json()
            if index < len(study["trials"]):
                assert study["recommendation_available"] is False

        assert study["completed_trial_count"] == 3
        assert study["pending_trial_count"] == 0
        assert study["surrogate_available"] is True
        assert study["recommendation_available"] is True

        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert restored.status_code == 200
        assert restored.json() == study


def test_bayesian_lhs_rejects_linear_constraints_without_silent_policy_switch(
    tmp_path,
) -> None:
    request = _request()
    request["constraints"] = [
        {
            "constraint_id": "limit",
            "name": "Limit",
            "terms": [{"factor_id": "x1", "coefficient": 1}],
            "relation": "less_than_or_equal",
            "bound": 0.5,
        }
    ]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post("/api/v1/bayesian-studies", json=request)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "bayesian_lhs_constraints_unsupported"
