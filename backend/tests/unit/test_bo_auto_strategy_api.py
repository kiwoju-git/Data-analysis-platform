"""Real saved models and owned LOO worker, using synthetic observations only."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.bo_planning import planning_sha
from tests.unit.test_bo_planning_api import _database_rows, completed, fit_request, url


@pytest.mark.parametrize("mixed", [False, True])
def test_source_locked_advice_does_not_write_or_refit(tmp_path, monkeypatch, mixed):
    settings = Settings(workspace_root=tmp_path / "Auto synthetic workspace")
    with TestClient(create_app(settings)) as client:
        if mixed:
            from tests.unit.test_bo_mixed_lifecycle_api import _observations
            from tests.unit.test_bo_mixed_planning_api import fit_options, source
            from tests.unit.test_bo_mixed_studies import request

            raw = request()
            created = client.post("/api/v1/bayesian-studies/mixed", json=raw)
            assert created.status_code == 201, created.text
            study = created.json()
            saved = client.put(url(study) + "/observations/batch", json=_observations(study))
            assert saved.status_code == 200, saved.text
            study = saved.json()["study"]
            fit = source(study) | {"request_id": str(uuid4()), "fit": fit_options()}
        else:
            study = completed(client)
            fit = fit_request(study)
        family = "/mixed-planning-models" if mixed else "/planning-models"
        result = client.post(url(study) + family, json=fit)
        assert result.status_code == 201, result.text
        model = result.json()
        path = url(study) + family + "/" + model["model_id"] + "/auto-strategy"
        body = {
            "expected_model_sha256": model["snapshot_sha256"],
            "expected_history_sha256": model["history_sha256"],
            "r_squared_threshold": 0.25,
        }
        before = _database_rows(settings.workspace_root)
        from app.services import bo_loo

        original = bo_loo._run

        def only_diagnostic(operation, *args, **kwargs):
            assert operation == "loo"
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_loo, "_run", only_diagnostic)
        result = client.post(path, json=body)
        assert result.status_code == 200, result.text
        view = result.json()
        assert view["decision_only"] and not view["selection_created"]
        assert view["diagnostic"]["model_sha256"] == model["snapshot_sha256"]
        assert not view["diagnostic"]["calculation"]["auto_routing_applied"]
        assert view["apply_allowed"]
        values = [item["r_squared"] for item in view["diagnostic"]["calculation"]["responses"]]
        assert view["decision"]["reason"] == (
            "any_response_below_threshold"
            if any(value < 0.25 for value in values)
            else "all_responses_meet_threshold"
        )
        diagnostic = {k: v for k, v in view["diagnostic"].items() if k != "source_is_current"}
        assert view["decision_sha256"] == planning_sha(
            {"diagnostic": diagnostic, "decision": view["decision"]}
        )
        assert client.post(path, json=body | {"expected_model_sha256": "0" * 64}).status_code == 409
        for threshold in ("0.25", True, -1, 2):
            assert (
                client.post(path, json=body | {"r_squared_threshold": threshold}).status_code == 422
            )
        assert _database_rows(settings.workspace_root) == before
        assert client.get(url(study)).json() == study
        # Historical diagnostic remains inspectable, never applicable.
        from app.services import bo_auto_strategy

        original_view = bo_auto_strategy.get_loo_view
        with monkeypatch.context() as patch:
            patch.setattr(
                bo_auto_strategy,
                "get_loo_view",
                lambda *a, **kw: original_view(*a, **kw).model_copy(
                    update={"source_is_current": False}
                ),
            )
            historical = client.post(path, json=body).json()
            assert not historical["apply_allowed"]
            assert historical["decision_sha256"] == view["decision_sha256"]
    with TestClient(create_app(settings)) as client:
        assert client.post(path, json=body).json() == view
        assert _database_rows(settings.workspace_root) == before
