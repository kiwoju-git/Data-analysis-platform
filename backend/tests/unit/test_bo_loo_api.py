"""Synthetic HTTP and owned worker checks, including no model/history writes."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.unit.test_bo_planning_api import _database_rows, completed, fit_request, url


@pytest.mark.parametrize("mixed", [False, True])
def test_real_loo_worker_exact_source_restart_and_read_only(tmp_path, monkeypatch, mixed):
    settings = Settings(workspace_root=tmp_path / "synthetic LOO workspace")
    with TestClient(create_app(settings)) as client:
        if mixed:
            from tests.unit.test_bo_mixed_lifecycle_api import _observations
            from tests.unit.test_bo_mixed_planning_api import fit_options, source
            from tests.unit.test_bo_mixed_studies import request

            raw = request()
            raw["factors"][0].update(domain_kind="continuous", step=None, display_decimals=None)
            created = client.post("/api/v1/bayesian-studies/mixed", json=raw)
            assert created.status_code == 201, created.text
            study = created.json()
            endpoint = url(study)
            saved = client.put(endpoint + "/observations/batch", json=_observations(study))
            assert saved.status_code == 200, saved.text
            study = saved.json()["study"]
            fit = source(study) | {"request_id": str(uuid4()), "fit": fit_options()}
        else:
            study = completed(client)
            endpoint = url(study)
            fit = fit_request(study)
        family = "/mixed-planning-models" if mixed else "/planning-models"
        created = client.post(endpoint + family, json=fit)
        assert created.status_code == 201, created.text
        model = created.json()
        model_url = endpoint + family + "/" + model["model_id"]
        body = {
            "expected_model_sha256": model["snapshot_sha256"],
            "expected_history_sha256": model["history_sha256"],
        }
        before = _database_rows(settings.workspace_root)
        from app.services import bo_loo

        original = bo_loo._run

        def only_loo(operation, *args, **kwargs):
            assert operation == "loo"
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_loo, "_run", only_loo)
        result = client.post(model_url + "/loo", json=body)
        assert result.status_code == 200, result.text
        view = result.json()
        assert view["model_sha256"] == model["snapshot_sha256"]
        assert view["history_sha256"] == model["history_sha256"]
        assert view["calculation"]["responses"][0]["n_scored"] == study["completed_trial_count"]
        assert (
            client.post(
                model_url + "/loo", json=body | {"expected_model_sha256": "0" * 64}
            ).status_code
            == 409
        )
        assert (
            client.post(
                model_url + "/loo", json=body | {"expected_history_sha256": "0" * 64}
            ).status_code
            == 409
        )
        assert client.get(model_url).json() == model
        assert client.get(endpoint).json() == study
        assert _database_rows(settings.workspace_root) == before
        # Simulate a new head becoming visible while the owned worker runs. The
        # saved diagnostic is unchanged, but it must no longer claim currentness.
        target = (
            "app.services.bo_mixed_studies.get_mixed_study"
            if mixed
            else "app.services.bo_loo.get_bayesian_study"
        )
        from importlib import import_module

        module_name, name = target.rsplit(".", 1)
        original_read = getattr(import_module(module_name), name)
        reads = 0

        def advanced_head(*args, **kwargs):
            nonlocal reads
            reads += 1
            current = original_read(*args, **kwargs)
            if reads == 1:
                return current
            return current.model_copy(
                update={
                    "observation_history": current.observation_history.model_copy(
                        update={"observation_history_sha256": "0" * 64}
                    )
                }
            )

        with monkeypatch.context() as patch:
            patch.setattr(target, advanced_head)
            historical = client.post(model_url + "/loo", json=body)
            assert historical.status_code == 200, historical.text
            stale = historical.json()
            assert stale["source_is_current"] is False
            assert stale["calculation"] == view["calculation"]
            assert stale["history_sha256"] == view["history_sha256"]
    with TestClient(create_app(settings)) as client:
        assert client.post(model_url + "/loo", json=body).json() == view
        assert _database_rows(settings.workspace_root) == before
