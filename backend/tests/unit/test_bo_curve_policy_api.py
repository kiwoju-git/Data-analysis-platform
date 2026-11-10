"""Actual HTTP and owned worker, synthetic workspace only."""

import sqlite3

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_multiresponse_lifecycle import observations, study_request, url
from tests.unit.test_bo_desirability_public_batch import batch_request


def curve_study_request():
    body = study_request()
    body["objective"]["curve_policy"] = "per_response_target_gaussian_or_ds_v1"
    body["objective"]["responses"][1].update(
        goal="match_target",
        lower=1.0,
        target=4.0,
        upper=10.0,
        curve={
            "policy": "two_sided_gaussian_target_peak_one_v1",
            "lower_desirability": 0.04,
            "upper_desirability": 0.2,
        },
    )
    return body


def test_curve_review_confirm_observe_restart_report(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/bayesian-studies", json=curve_study_request())
        assert response.status_code == 201, response.text
        study = response.json()
        assert study["study_schema_version"] == 6
        from uuid import UUID

        from app.services.bayesian_studies import get_bayesian_study

        get_bayesian_study(settings, UUID(study["study_id"]))
        saved = client.put(url(study) + "/observations/batch", json=observations(study))
        assert saved.status_code == 200, saved.text
        study = saved.json()["study"]
        request = batch_request(study, 2)
        assert client.post(url(study) + "/desirability-reviews", json=request).status_code == 409
        request.update(schema_version=7, fit_policy=None)
        response = client.post(url(study) + "/desirability-reviews", json=request)
        assert response.status_code == 200, response.text
        review = response.json()
        assert review["schema_version"] == 5
        assert client.get(url(study)).json() == study

        def forbidden(*args, **kwargs):
            raise AssertionError("must not fit during confirm/restore/report")

        monkeypatch.setattr(
            "app.services.bo_desirability_worker.run_desirability_batch_calculation", forbidden
        )
        confirm = url(study) + f"/desirability-reviews/{review['review_id']}/confirm"
        response = client.post(confirm, json={"expected_config_sha256": review["config_sha256"]})
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["method_version"] == "0.12.0"
        assert batch["result_schema_version"] == 7
        assert (
            client.post(confirm, json={"expected_config_sha256": review["config_sha256"]}).json()
            == batch
        )
        current = client.get(url(study)).json()
        measured = client.put(url(study) + "/observations/batch", json=observations(current, (3,)))
        assert measured.status_code == 200, measured.text
        saved_url = url(study) + f"/desirability-recommendations/{batch['batch_id']}"
        restored = client.get(saved_url)
        assert restored.status_code == 200, restored.text
        assert restored.json()["batch_state"] == "partially_completed"
        assert restored.json()["calculation"] == batch["calculation"]
        from app.services.bo_noise_report import bo_noise_report_section

        for locale in ("en", "ko"):
            section = bo_noise_report_section(
                batch, {"objective": study["objective"], "factors": study["factors"]}, locale
            )
            assert section.status == "rendered"
            assert "two_sided_gaussian_target_peak_one_v1" in section.markup
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            original = db.execute(
                "SELECT config_json,result_json,result_sha256 FROM bayesian_recommendation_batches"
            ).fetchone()
        source = {
            "kind": "bayesian_history_revision",
            "study_id": study["study_id"],
            "study_version_id": study["study_version_id"],
            "definition_sha256": study["definition_sha256"],
            "history_revision_id": review["source_history_revision_id"],
            "expected_source_sha256": review["source_observation_history_sha256"],
            "attachment": {
                "kind": "batch",
                "batch_id": batch["batch_id"],
                "result_json_sha256": original[2],
                "result_payload_sha256": batch["result_sha256"],
            },
        }
        from tests.unit.test_dedicated_report_sources import no_recompute

        with monkeypatch.context() as report_guard:
            no_recompute(report_guard)
            for locale in ("en", "ko"):
                capability = client.post(
                    "/api/v1/reports/capability", json={"source": source, "locale": locale}
                )
                assert capability.status_code == 200, capability.text
                created = client.post(
                    "/api/v1/reports",
                    json={
                        "source": source,
                        "locale": locale,
                        "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
                    },
                )
                assert created.status_code == 201, created.text
                record = created.json()
                download = client.post(
                    f"/api/v1/reports/{record['export_id']}/download",
                    json={"source": source, "expected_sha256": record["sha256"]},
                )
                assert download.status_code == 200, download.text
                assert "two_sided_gaussian_target_peak_one_v1" in download.text
    with TestClient(create_app(settings)) as client:
        assert client.get(saved_url).json() == restored.json()
        assert (
            client.get(url(study) + "/recommendation-batches/latest").json()["item"]
            == restored.json()
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            assert (
                db.execute(
                    "SELECT config_json,result_json,result_sha256 "
                    "FROM bayesian_recommendation_batches"
                ).fetchone()
                == original
            )


def test_old_study_rejects_new_curve_request_without_mutation(tmp_path, monkeypatch):
    from tests.unit.test_bo_desirability_review_api import completed

    def forbidden(*args, **kwargs):
        raise AssertionError("policy mismatch must be rejected before worker admission")

    monkeypatch.setattr(
        "app.services.bo_desirability_worker.run_desirability_batch_calculation", forbidden
    )
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed(client)
        body = batch_request(study, 1)
        body.update(schema_version=7, fit_policy=None)
        response = client.post(url(study) + "/desirability-reviews", json=body)
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "bayesian_desirability_response_mapping_invalid"
        assert client.get(url(study)).json() == study
