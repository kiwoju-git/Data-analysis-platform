from __future__ import annotations

import hashlib
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from test_gaussian_process_regression_api import _create_dataset, _create_gp_analysis

from app.api.v1.schemas.reports import ReportSourceRef
from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services.completed_predictions import load_completed_prediction
from app.storage.metadata import get_analysis_run_record, metadata_db_path


def _model(client, family):
    version = _create_dataset(client)
    if family == "gaussian_process":
        analysis = _create_gp_analysis(client, version)
    else:
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.partial_least_squares",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "response_column_id": version["columns"][0]["column_id"],
                    "predictor_column_ids": [item["column_id"] for item in version["columns"][1:]],
                    "component_selection": "fixed",
                    "n_components": 2,
                    "max_components": 2,
                    "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 7},
                },
            },
        )
        assert response.status_code == 201, response.text
        analysis = response.json()
    pointer = analysis["result"]["model_manifest"]
    body = {
        "expected_model_manifest_sha256": pointer["manifest_sha256"],
        "rows": [
            {
                "client_row_id": "second <&>",
                "values": {item["column_id"]: 1.5 for item in version["columns"][1:]},
            },
            {
                "client_row_id": "first",
                "values": {item["column_id"]: 200 for item in version["columns"][1:]},
            },
        ],
    }
    suffix = (
        "gaussian-process-predictions" if family == "gaussian_process" else "pls-point-predictions"
    )
    return analysis, pointer, body, f"/api/v1/regression-models/{pointer['model_id']}/{suffix}"


@pytest.mark.parametrize("family", ["pls", "gaussian_process"])
def test_completed_prediction_saved_once_and_report_survives_model_removal(
    tmp_path, monkeypatch, family
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis, pointer, body, url = _model(client, family)
        record = get_analysis_run_record(tmp_path, analysis["analysis_id"])
        original_bytes = (tmp_path / record.result_path).read_bytes()
        unsaved = client.post(url, json=body)
        assert unsaved.status_code == 200, unsaved.text
        assert unsaved.json()["saved_prediction"] is None
        saved = client.post(url, json={**body, "save_result": True})
        assert saved.status_code == 200, saved.text
        payload = saved.json()
        assert payload["rows"] == unsaved.json()["rows"]
        source = payload["saved_prediction"]["source"]
        typed = TypeAdapter(ReportSourceRef).validate_python(source)
        snapshot, artifact = load_completed_prediction(settings, typed.prediction)
        assert snapshot["request"] == {**body, "save_result": True}
        assert snapshot["result"]["rows"] == payload["rows"]
        assert snapshot["result"].get("saved_prediction") is None
        assert (
            hashlib.sha256((tmp_path / artifact.path).read_bytes()).hexdigest() == artifact.sha256
        )
        assert (tmp_path / record.result_path).read_bytes() == original_bytes

        def forbidden(*args, **kwargs):
            raise AssertionError("export must not recalculate or load current source rows")

        monkeypatch.setattr(
            "app.services.gaussian_process_predictions.predict_from_gaussian_process_state",
            forbidden,
        )
        monkeypatch.setattr("app.services.pls_predictions.predict_from_pls_basis", forbidden)
        monkeypatch.setattr("app.services.dataset_rows.get_dataset_rows_context", forbidden)
        capability = client.post(
            "/api/v1/reports/capability", json={"source": source, "locale": "en"}
        )
        assert capability.status_code == 200, capability.text
        assert capability.json()["report_level"] == "full"
        report = client.post(
            "/api/v1/reports",
            json={
                "source": source,
                "locale": "en",
                "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
            },
        )
        assert report.status_code == 201, report.text
        report_payload = report.json()
        action = {"source": source, "expected_sha256": report_payload["sha256"]}
        download = client.post(
            f"/api/v1/reports/{report_payload['export_id']}/download", json=action
        )
        assert download.status_code == 200, download.text
        assert hashlib.sha256(download.content).hexdigest() == report_payload["sha256"]
        assert "second &lt;&amp;&gt;" in download.text
        assert "<table>" in download.text
        assert "script src=" not in download.text
        if family == "pls":
            assert "point predictions only" in download.text
            assert "New-observation 95% lower" not in download.text
        else:
            assert "Latent 95% lower" in download.text
            assert "New-observation 95% lower" in download.text
        listed = client.post(
            "/api/v1/reports/artifacts/query", json={"source": source, "locale": "en"}
        )
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["export_id"] == report_payload["export_id"]
        catalog = client.get("/api/v1/reports/sources?source_kind=regression_prediction")
        assert catalog.status_code == 200, catalog.text
        assert catalog.json()["items"][0]["source"] == source
        with monkeypatch.context() as deleted_owner:
            deleted_owner.setattr(
                "app.services.report_sources.load_completed_prediction",
                lambda *args: (snapshot, artifact),
            )
            deleted_owner.setattr(
                "app.services.report_sources.get_analysis_run_record", lambda *args: None
            )
            raced = client.post(
                "/api/v1/reports/capability", json={"source": source, "locale": "en"}
            )
            assert raced.status_code == 409, raced.text
            assert raced.json()["error"]["code"] == "stored_report_source_changed"
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "DELETE FROM regression_models WHERE model_id=?", (pointer["model_id"],)
            )
        assert load_completed_prediction(settings, typed.prediction)[0] == snapshot
        restored = client.get(f"/api/v1/reports/{report_payload['export_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json()["source"] == source
        deleted = client.request(
            "DELETE", f"/api/v1/reports/{report_payload['export_id']}", json=action
        )
        assert deleted.status_code == 200, deleted.text
        assert client.get(f"/api/v1/reports/{report_payload['export_id']}").status_code == 404
        assert (tmp_path / record.result_path).read_bytes() == original_bytes


def test_completed_prediction_rejects_rehashed_row_identity_corruption(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        _, _, body, url = _model(client, "pls")
        saved = client.post(url, json={**body, "save_result": True})
        assert saved.status_code == 200, saved.text
        source = TypeAdapter(ReportSourceRef).validate_python(
            saved.json()["saved_prediction"]["source"]
        )
        payload, record = load_completed_prediction(settings, source.prediction)
        payload["result"]["rows"][1]["client_row_id"] = payload["result"]["rows"][0][
            "client_row_id"
        ]
        from app.services.analysis_run_execution import canonical_json_bytes

        payload["result_sha256"] = hashlib.sha256(
            canonical_json_bytes(payload["result"])
        ).hexdigest()
        content = canonical_json_bytes(payload)
        sha = hashlib.sha256(content).hexdigest()
        (tmp_path / record.path).write_bytes(content)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_artifacts SET sha256=? WHERE artifact_id=?",
                (sha, record.artifact_id),
            )
        source.prediction.expected_source_sha256 = sha
        with pytest.raises(ApiError) as captured:
            load_completed_prediction(settings, source.prediction)
        assert captured.value.code == "completed_prediction_corrupt"
