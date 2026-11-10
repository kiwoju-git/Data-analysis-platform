"""Mixed model/candidate HTTP path, synthetic data and exact no-refit restoration."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.unit.test_bo_mixed_lifecycle_api import _observations
from tests.unit.test_bo_mixed_planning import payload
from tests.unit.test_bo_mixed_studies import request


def source(study):
    return {
        "expected_study_version_id": study["study_version_id"],
        "expected_definition_sha256": study["definition_sha256"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_history_sha256": study["observation_history"]["observation_history_sha256"],
        "expected_trial_count": study["trial_count"],
    }


def fit_options():
    core = payload()
    return {
        key: core[key]
        for key in (
            "response_models",
            "observation_policy",
            "xi_desirability",
            "search",
            "fit_policy",
            "max_moment_evaluations",
        )
    }


def test_mixed_fit_candidate_profiler_identity_replay_restart(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "mixed candidate workspace")
    with TestClient(create_app(settings)) as client:
        raw = request()
        raw["factors"][0].update(domain_kind="continuous", step=None, display_decimals=None)
        created = client.post("/api/v1/bayesian-studies/mixed", json=raw)
        assert created.status_code == 201, created.text
        study = created.json()
        endpoint = "/api/v1/bayesian-studies/" + study["study_id"]
        saved = client.put(endpoint + "/observations/batch", json=_observations(study))
        assert saved.status_code == 200, saved.text
        study = saved.json()["study"]
        body = source(study) | {"request_id": str(uuid4()), "fit": fit_options()}
        response = client.post(endpoint + "/mixed-planning-models", json=body)
        assert response.status_code == 201, response.text
        model = response.json()
        assert model["schema_version"] == 2
        assert model["observation_view"]["raw_observation_count"] == 8
        from app.services import bo_planning

        original = bo_planning.run_planning_operation

        def no_fit(operation, *args, **kwargs):
            assert operation != "mixed_fit"
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_planning, "run_planning_operation", no_fit)
        assert client.post(endpoint + "/mixed-planning-models", json=body).json() == model
        assert (
            client.get(endpoint + "/mixed-planning-models").json()["items"][0]["model_id"]
            == model["model_id"]
        )
        candidate = source(study) | {
            "schema_version": 3,
            "request_id": str(uuid4()),
            "candidate_set_id": str(uuid4()),
            "name": "Synthetic mixed candidates",
            "expected_head_revision_id": None,
            "model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "duplicate_tolerance": body["fit"]["search"]["duplicate_tolerance"],
            "source": {"kind": "seeded_uniform", "seed": 12, "count": 12},
        }
        response = client.post(endpoint + "/mixed-candidate-revisions", json=candidate)
        assert response.status_code == 201, response.text
        page = response.json()
        assert len(page["items"]) == 12
        assert page["revision"]["schema_version"] == 3
        assert all(isinstance(row["actual_coordinates"]["kind"], str) for row in page["items"])
        assert all("normalized_coordinates" not in row for row in page["items"])
        assert client.get(endpoint + "/mixed-candidate-sets").json()["items"] == [page["revision"]]
        assert client.post(endpoint + "/mixed-candidate-revisions", json=candidate).json() == page
        points = [{"x": 1000.2, "kind": value} for value in raw["factors"][1]["levels"]]
        evaluate = {"expected_model_sha256": model["snapshot_sha256"], "points": points}
        evaluated = client.post(
            endpoint + "/mixed-planning-models/" + model["model_id"] + "/evaluate", json=evaluate
        )
        assert evaluated.status_code == 200, evaluated.text
        values = evaluated.json()
        assert values["model_refit"] is False
        assert [row["actual_coordinates"] for row in values["items"]] == points
        assert client.get(endpoint).json() == study
    with TestClient(create_app(settings)) as client:
        assert client.get(endpoint + "/mixed-planning-models/" + model["model_id"]).json() == model
        assert (
            client.get(
                endpoint + "/mixed-candidate-revisions/" + page["revision"]["revision_id"]
            ).json()
            == page
        )
        restored = client.post(
            endpoint + "/mixed-planning-models/" + model["model_id"] + "/evaluate", json=evaluate
        )
        assert restored.json() == values
