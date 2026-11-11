"""Real worker and immutable fit-policy lifecycle on a synthetic workspace."""

import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.bo_fit_quality_report import fit_quality_markup
from app.services.bo_noise_report import bo_noise_report_section
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_multiresponse_lifecycle import url
from tests.unit.test_bo_desirability_public_batch import batch_request
from tests.unit.test_bo_desirability_review_api import completed


@pytest.mark.parametrize("explicit_search", [False, True])
def test_fit_review_confirm_restart_report_without_refit(tmp_path, monkeypatch, explicit_search):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        body = batch_request(study, 1 if explicit_search else 2)
        body.update(
            schema_version=6,
            fit_policy={"kind": "bounded_multiscale_starts_v1", "deterministic_start_count": 1},
        )
        body["search"]["model_max_evaluations"] = 1800
        if explicit_search:
            body["search"].update(
                candidate_count_per_step=64,
                local_start_count_per_step=1,
                max_iterations_per_step=5,
                model_max_iterations=80,
                max_evaluations_total=1024,
            )
        response = client.post(url(study) + "/desirability-reviews", json=body)
        assert response.status_code == 200, response.text
        review = response.json()
        assert review["schema_version"] == 4
        assert client.get(url(study)).json() == study
        assert all(
            m["model"]["schema_version"] == 5
            for m in review["calculation"]["shared_model"]["response_models"]
        )

        def forbidden(*args, **kwargs):
            raise AssertionError("confirmation/restore/export must not fit")

        monkeypatch.setattr(
            "app.services.bo_desirability_worker.run_desirability_batch_calculation", forbidden
        )
        confirm = url(study) + f"/desirability-reviews/{review['review_id']}/confirm"
        response = client.post(confirm, json={"expected_config_sha256": review["config_sha256"]})
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["method_version"] == "0.11.0"
        assert batch["result_schema_version"] == batch["model_schema_version"] == 6
        assert (
            client.post(confirm, json={"expected_config_sha256": review["config_sha256"]}).json()
            == batch
        )
        saved_url = url(study) + f"/desirability-recommendations/{batch['batch_id']}"
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            original = db.execute(
                "SELECT config_json,result_json,result_sha256 FROM bayesian_recommendation_batches"
            ).fetchone()
        assert json.loads(original[0])["request"]["search"] == body["search"]
        assert batch["calculation"]["search_budget"]["max_evaluations_total"] == 1024
        assert all(
            model["model"]["optimizer"]["max_iterations"] == body["search"]["model_max_iterations"]
            for model in batch["calculation"]["shared_model"]["response_models"]
        )
        source_digest = hashlib.sha256(
            json.dumps(batch["calculation"], sort_keys=True).encode()
        ).hexdigest()
        for locale in ("en", "ko"):
            markup = fit_quality_markup(batch["calculation"], locale)
            assert "<svg" in markup and 'data-fit-policy="bounded_multiscale_starts_v1"' in markup
            section = bo_noise_report_section(
                batch, {"objective": study["objective"], "factors": study["factors"]}, locale
            )
            assert section.section_id == "noise_summary" and section.status == "rendered"
            assert 'data-fit-policy="bounded_multiscale_starts_v1"' in section.markup
            for model in batch["calculation"]["shared_model"]["response_models"]:
                assert (
                    str(
                        -model["model"]["fit_diagnostics"]["start_best_evaluations"][0][
                            "negative_log_likelihood"
                        ]
                    )
                    in markup
                )
        assert (
            hashlib.sha256(json.dumps(batch["calculation"], sort_keys=True).encode()).hexdigest()
            == source_digest
        )
    with TestClient(create_app(settings)) as client:
        restored = client.get(saved_url)
        assert restored.status_code == 200, restored.text
        assert restored.json() == batch
        assert client.get(url(study) + "/recommendation-batches/latest").json()["item"] == batch
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            assert (
                db.execute(
                    "SELECT config_json,result_json,result_sha256 "
                    "FROM bayesian_recommendation_batches"
                ).fetchone()
                == original
            )


def test_fit_budget_failure_leaves_history_and_trials_unchanged(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        body = batch_request(study)
        body.update(
            schema_version=6,
            fit_policy={"kind": "bounded_multiscale_starts_v1", "deterministic_start_count": 1},
        )
        body["search"]["model_max_evaluations"] = 8
        response = client.post(url(study) + "/desirability-reviews", json=body)
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "bayesian_optimization_budget_exhausted"
        assert client.get(url(study)).json() == study
        assert client.get(url(study) + "/desirability-recommendations/latest").json() == {
            "item": None
        }


def test_worker_precision_error_preserves_source_and_does_not_commit(tmp_path, monkeypatch):
    def reject(request):
        assert request.batch_size == 2
        assert request.search.candidate_count_per_step == 64
        assert request.search.local_start_count_per_step == 1
        assert request.search.max_iterations_per_step == 5
        assert request.search.model_max_iterations == 80
        assert request.search.max_evaluations_total == 1024
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")

    monkeypatch.setattr(
        "app.services.bo_desirability_worker.run_desirability_batch_calculation", reject
    )
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        body = batch_request(study, 2)
        body.update(
            schema_version=6,
            fit_policy={"kind": "bounded_multiscale_starts_v1", "deterministic_start_count": 1},
        )
        body["search"].update(
            candidate_count_per_step=64,
            local_start_count_per_step=1,
            max_iterations_per_step=5,
            model_max_iterations=80,
            model_max_evaluations=1800,
            max_evaluations_total=1024,
        )
        response = client.post(url(study) + "/desirability-reviews", json=body)
        assert response.status_code == 409, response.text
        assert (
            response.json()["error"]["code"] == "bayesian_desirability_beta_precision_unsupported"
        )
        assert client.get(url(study)).json() == study
        assert client.get(url(study) + "/desirability-recommendations/latest").json() == {
            "item": None
        }
