"""Six-response capacity without changing curves, raw observations or budgets."""

import hashlib
from copy import deepcopy

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.schemas.bayesian_desirability import DesirabilityObjective
from app.core.config import Settings
from app.main import create_app
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import DesirabilityGoal, composite_desirability
from tests.unit.test_bayesian_multiresponse_lifecycle import study_request
from tests.unit.test_bo_dataset_import_api import ROOT, commit_request, import_request, preflight
from tests.unit.test_bo_planning_api import candidate_request, fit_request
from tests.unit.test_bo_views import _save_body


def response_goals(count=6):
    return [
        {
            "response_id": f"y{i}",
            "name": f"Response {i}",
            "unit": None,
            "goal": "maximize",
            "lower": 0.0,
            "target": 10.0,
            "upper": None,
            "importance": float(i + 1),
        }
        for i in range(count)
    ]


def test_six_response_composite_matches_independent_weighted_geometric_mean():
    goals = [
        DesirabilityGoal(g["response_id"], "maximize", 0.0, 10.0, None, g["importance"])
        for g in response_goals()
    ]
    values = {f"y{i}": float(i + 1) for i in range(6)}
    original = deepcopy(values)
    expected = float(
        np.prod([(values[g.response_id] / 10) ** ((i + 1) / 21) for i, g in enumerate(goals)])
    )
    assert composite_desirability(values, goals) == pytest.approx(expected, rel=2e-14)
    assert values == original
    values["y5"] = 0.0
    assert composite_desirability(values, goals) == 0


@pytest.mark.parametrize("count", [1, 4, 5, 6])
def test_response_contract_accepts_complete_vectors(count):
    body = {"responses": response_goals(count)}
    parsed = DesirabilityObjective.model_validate(body)
    assert parsed.model_dump() == body


def test_seventh_response_is_rejected_by_schema_and_calculation():
    with pytest.raises(ValidationError):
        DesirabilityObjective.model_validate({"responses": response_goals(7)})
    goals = [DesirabilityGoal(f"y{i}", "maximize", 0, 10, None) for i in range(7)]
    with pytest.raises(BayesianOptimizationError):
        composite_desirability({f"y{i}": 1.0 for i in range(7)}, goals)


def test_planning_size_guards_remain_bounded_before_worker_or_storage(monkeypatch):
    from app.core.bo_limits import MAX_BO_PLANNING_BYTES
    from app.services import bo_desirability_worker, bo_planning_worker
    from app.storage import bo_planning
    from app.storage.bayesian_studies import BayesianStorageConflict

    assert MAX_BO_PLANNING_BYTES == 24 * 1024 * 1024
    assert (
        bo_planning.MAX_DOCUMENT_BYTES
        == bo_planning_worker.MAX_PLANNING_BYTES
        == MAX_BO_PLANNING_BYTES
    )
    assert bo_planning.MAX_OWNER_BYTES == 128 * 1024 * 1024
    assert bo_planning.MAX_WORKSPACE_BYTES == 256 * 1024 * 1024
    monkeypatch.setattr(bo_planning, "MAX_DOCUMENT_BYTES", 64)
    monkeypatch.setattr(bo_planning_worker, "MAX_PLANNING_BYTES", 64)
    monkeypatch.setattr(
        bo_desirability_worker,
        "_run_owned_worker",
        lambda *args, **kwargs: pytest.fail("Oversized input must not start a worker"),
    )
    text = "x" * 65
    with pytest.raises(BayesianStorageConflict, match="bayesian_planning_artifact_invalid"):
        bo_planning._documents(
            {"snapshot_json": text, "sha": hashlib.sha256(text.encode()).hexdigest()},
            (("snapshot_json", "sha"),),
        )
    with pytest.raises(BayesianOptimizationError, match="bayesian_desirability_input_too_large"):
        bo_planning_worker.run_planning_operation("fit", {"value": text}, time_budget_ms=1000)


@pytest.mark.parametrize("kind", ["mixed", "numeric_mixture", "mixed_mixture"])
def test_six_models_preserve_mixed_and_mixture_prediction_and_loo(kind):
    from threadpoolctl import threadpool_limits

    from app.api.v1.schemas.bo_loo import LooCalculation
    from app.statistics.bo_auto_strategy import suggest_augmentation
    from app.statistics.bo_loo import planning_loo
    from app.statistics.bo_mixed_planning import (
        evaluate_mixed_planning_points,
        fit_mixed_planning_model,
    )
    from app.statistics.bo_mixture_planning import (
        evaluate_mixture_planning_points,
        fit_mixture_planning_model,
    )
    from tests.unit.test_bo_mixed_planning import payload as mixed_payload
    from tests.unit.test_bo_mixture_planning import payload as mixture_payload

    body = mixed_payload() if kind == "mixed" else mixture_payload(kind == "mixed_mixture")
    fit = body if kind == "mixed" else body["fit"]
    goal, model = body["objective"]["responses"][0], fit["response_models"][0]
    body["objective"]["responses"] = [
        dict(goal, response_id=f"y{i}", name=f"Response {i}") for i in range(6)
    ]
    fit["response_models"] = [dict(model, response_id=f"y{i}") for i in range(6)]
    for row in body["observations"]:
        value = row["response_values"]["yield"]
        row["response_values"] = {f"y{i}": value + i * 0.01 for i in range(6)}
    fitter = fit_mixed_planning_model if kind == "mixed" else fit_mixture_planning_model
    evaluator = (
        evaluate_mixed_planning_points if kind == "mixed" else evaluate_mixture_planning_points
    )
    original = deepcopy(body)
    with threadpool_limits(limits=1):
        snapshot = fitter(body)
        before = deepcopy(snapshot)
        points = [body["observations"][2]["actual_coordinates"]]
        prediction = evaluator(snapshot, points)
        assert prediction == evaluator(deepcopy(snapshot), points)
        assert len(prediction[0]["response_predictions"]) == 6
        if kind == "mixed":
            loo = planning_loo(snapshot, mixed=True)
            assert len(LooCalculation.model_validate(loo).responses) == 6
            rows = [
                {"response_id": row["response_id"], "r_squared": row["r_squared"]}
                for row in loo["responses"]
            ]
            assert suggest_augmentation(rows, ["continuous", "nominal"], 0.25)
        assert snapshot == before
    assert body == original


def test_six_response_dataset_import_restore_and_complete_vector(tmp_path):
    csv = b"x,y0,y1,y2,y3,y4,y5\n0,1,2,3,4,5,6\n5,2,3,4,5,6,7\n10,3,4,5,6,7,8\n"
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client, csv)
        body["objective"] = {**study_request()["objective"], "responses": response_goals()}
        body["response_mappings"] = [
            {"column_id": version["columns"][i + 1]["column_id"], "response_id": f"y{i}"}
            for i in range(6)
        ]
        preview = preflight(client, body)
        response = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert response.status_code == 201, response.text
        study = response.json()
        assert len(study["objective"]["responses"]) == 6
        assert study["trials"][0]["response_values"] == {f"y{i}": i + 1 for i in range(6)}
        assert study["completed_trial_count"] == 3
        assert client.get(f"{ROOT}/{study['study_id']}").json() == study
        bad = deepcopy(body)
        bad["response_mappings"].pop()
        assert client.post(f"{ROOT}/import-preflight", json=bad).status_code == 422


def test_six_response_fit_candidates_profiler_report_and_next_trial(tmp_path, monkeypatch):
    from app.services import bo_planning, bo_view_report
    from tests.unit.test_bayesian_multiresponse_lifecycle import url
    from tests.unit.test_bo_planning_api import selection_request

    csv = b"x,y0,y1,y2,y3,y4,y5\n0,1,2,3,4,5,6\n5,2,3,4,5,6,7\n10,3,4,5,6,7,8\n"
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        body, version = import_request(client, csv)
        body["objective"] = {**study_request()["objective"], "responses": response_goals()}
        body["response_mappings"] = [
            {"column_id": version["columns"][i + 1]["column_id"], "response_id": f"y{i}"}
            for i in range(6)
        ]
        created = client.post(
            f"{ROOT}/from-dataset", json=commit_request(body, preflight(client, body))
        )
        assert created.status_code == 201, created.text
        study = created.json()
        fit = fit_request(study)
        for response in fit["fit"]["response_models"]:
            response["surrogate"] = {"noise_mode": "fixed", "fixed_noise_sd": 0.2}
        fitted = client.post(url(study) + "/planning-models", json=fit)
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        original = bo_planning.run_planning_operation

        def no_refit(operation, *args, **kwargs):
            assert operation != "fit", "Saved six-response models must not refit"
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_planning, "run_planning_operation", no_refit)
        assert client.post(url(study) + "/planning-models", json=fit).json() == model
        candidates = client.post(
            url(study) + "/candidate-revisions", json=candidate_request(study, model)
        )
        assert candidates.status_code == 201, candidates.text
        page = candidates.json()
        endpoint = url(study) + f"/planning-models/{model['model_id']}/view-evaluations"
        view_response = client.post(
            endpoint,
            json={
                "kind": "profiler_matrix",
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
                "holds": {"x": 5},
                "points_per_axis": 5,
                "time_budget_ms": 60000,
            },
        )
        assert view_response.status_code == 200, view_response.text
        view = view_response.json()
        assert len(view["payload"]["responses"]) == 6
        for point in view["payload"]["axes"][0]["points"]:
            assert [r["response_id"] for r in point["response_predictions"]] == [
                f"y{i}" for i in range(6)
            ]
            assert all(
                r["predictive_standard_deviation_raw"] >= r["latent_standard_deviation_raw"]
                for r in point["response_predictions"]
            )
        saved_response = client.post(url(study) + "/views", json=_save_body(view))
        assert saved_response.status_code == 201, saved_response.text
        saved = saved_response.json()
        saved_url = url(study) + f"/views/{saved['view_id']}"
        assert client.get(saved_url).json() == saved
        for locale in ("en", "ko"):
            html = bo_view_report.render_view_body({"saved_view": saved}, locale).render()
            for i in range(6):
                assert f"Response {i}" in html
        assert client.get(saved_url).json() == saved
        selection = client.post(
            url(study) + "/planning-selections", json=selection_request(study, model, page)
        )
        assert selection.status_code == 201, selection.text
        selected = selection.json()
        confirmed = client.post(
            url(study) + f"/planning-selections/{selected['selection_id']}/confirm",
            json={
                "expected_config_sha256": selected["config_sha256"],
                "expected_result_sha256": selected["result_sha256"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        batch = confirmed.json()
        assert len(batch["calculation"]["items"][0]["response_predictions"]) == 6
        assert client.get(url(study) + f"/planning-batches/{batch['batch_id']}").json() == batch
        assert client.get(url(study)).json()["pending_trial_count"] == 2
    with TestClient(create_app(settings)) as client:
        assert client.get(saved_url).json() == saved
        restored = client.get(url(study) + f"/planning-batches/{batch['batch_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json()["result_sha256"] == batch["result_sha256"]
