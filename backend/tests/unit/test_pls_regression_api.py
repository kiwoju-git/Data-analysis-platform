from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_analysis_run_record, get_regression_model_record


def _create_dataset(client: TestClient) -> dict[str, object]:
    content = (
        b"response,x1,x2,x3\n"
        b"3.3,1,1.01,2\n"
        b"5.9,2,2.02,1\n"
        b"8.8,3,3.00,4\n"
        b"11.5,4,3.99,2\n"
        b"14.6,5,5.02,5\n"
        b"17.2,6,6.01,3\n"
        b"20.1,7,6.98,6\n"
        b"22.8,8,8.03,4\n"
        b"25.9,9,9.00,7\n"
        b"28.4,10,10.02,5\n"
        b"31.5,11,10.99,8\n"
        b"34.0,12,12.01,6\n"
    )
    uploaded = client.post(
        "/api/v1/datasets",
        files={"file": ("pls.csv", content, "text/csv")},
    )
    assert uploaded.status_code == 201
    confirmed = client.post(
        f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
        json={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "decimal": ".",
                "thousands": None,
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
            },
            "columns": [],
        },
    )
    assert confirmed.status_code == 201
    return confirmed.json()


def test_pls_analysis_persists_json_model_and_predicts_points(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_dataset(client)
        columns = version["columns"]
        response_id = columns[0]["column_id"]
        predictor_ids = [item["column_id"] for item in columns[1:]]
        analysis = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.partial_least_squares",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "filter_snapshot": {"expression_version": 1, "conditions": []},
                "roles": {
                    "response": response_id,
                    "predictors": ",".join(predictor_ids),
                },
                "options": {
                    "response_column_id": response_id,
                    "predictor_column_ids": predictor_ids,
                    "missing_policy": "complete_case",
                    "scale": True,
                    "component_selection": "automatic_cv",
                    "n_components": None,
                    "max_components": 3,
                    "cv": {
                        "method": "k_fold",
                        "folds": 4,
                        "shuffle": True,
                        "seed": 19,
                    },
                    "max_iter": 500,
                    "tol": 1e-6,
                    "plot_point_limit": 100,
                },
            },
        )
        assert analysis.status_code == 201, analysis.text
        payload = analysis.json()
        result = payload["result"]
        model_id = result["model_manifest"]["model_id"]
        manifest_response = client.get(f"/api/v1/regression-models/{model_id}")
        catalog_response = client.get("/api/v1/regression-models")
        prediction = client.post(
            f"/api/v1/regression-models/{model_id}/pls-point-predictions",
            json={
                "expected_model_manifest_sha256": result["model_manifest"]["manifest_sha256"],
                "rows": [
                    {
                        "client_row_id": "row-1",
                        "values": {
                            predictor_ids[0]: 13,
                            predictor_ids[1]: 13.01,
                            predictor_ids[2]: 7,
                        },
                    },
                    {
                        "client_row_id": "row-2",
                        "values": {
                            predictor_ids[0]: 30,
                            predictor_ids[1]: 30,
                            predictor_ids[2]: 20,
                        },
                    },
                ],
            },
        )

    assert payload["method_id"] == "regression.partial_least_squares"
    assert result["schema_version"] == 1
    assert result["summary_type"] == "partial_least_squares_regression"
    assert "prediction_basis" not in result
    assert result["model_summary"]["selected_components"] in {1, 2, 3}
    assert result["component_selection"]["rows"][0]["components"] == 1
    assert result["coefficients"]
    assert result["diagnostics"]["points"]
    stored = get_analysis_run_record(settings.workspace_root, payload["analysis_id"])
    assert stored is not None
    assert stored.method_id == "regression.partial_least_squares"
    model_record = get_regression_model_record(settings.workspace_root, model_id)
    assert model_record is not None
    assert model_record.method_id == "regression.partial_least_squares"
    manifest_path = settings.workspace_root / model_record.manifest_path
    manifest_bytes = manifest_path.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == model_record.manifest_sha256
    assert not manifest_bytes.startswith(b"\x80")
    manifest = json.loads(manifest_bytes)
    assert manifest["manifest_kind"] == "pls_model_manifest"
    assert manifest["manifest_schema_version"] == 1
    assert manifest["model_family"] == "partial_least_squares_regression"
    assert manifest["prediction_basis"]["predictor_order"] == predictor_ids
    assert "absolute_path" not in manifest
    assert manifest_response.status_code == 200
    assert manifest_response.json()["method_id"] == "regression.partial_least_squares"
    assert catalog_response.status_code == 200
    assert catalog_response.json()["models"][0]["method_id"] == ("regression.partial_least_squares")
    assert prediction.status_code == 200, prediction.text
    prediction_payload = prediction.json()
    assert prediction_payload["intervals_supported"] is False
    assert prediction_payload["row_count"] == 2
    assert prediction_payload["rows"][0]["predicted_value"] == pytest.approx(36.8, abs=1.5)
    assert prediction_payload["rows"][0]["warnings"] == ["prediction_extrapolation_risk"]
    assert prediction_payload["rows"][1]["warnings"] == ["prediction_extrapolation_risk"]


def test_pls_point_prediction_rejects_entire_invalid_request(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_dataset(client)
        columns = version["columns"]
        response_id = columns[0]["column_id"]
        predictor_ids = [item["column_id"] for item in columns[1:]]
        analysis = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.partial_least_squares",
                "method_version": "0.1.0",
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    "response_column_id": response_id,
                    "predictor_column_ids": predictor_ids,
                    "scale": True,
                    "component_selection": "fixed",
                    "n_components": 2,
                    "max_components": 2,
                    "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 7},
                    "max_iter": 500,
                    "tol": 1e-6,
                    "plot_point_limit": 100,
                },
            },
        ).json()
        model = analysis["result"]["model_manifest"]
        response = client.post(
            f"/api/v1/regression-models/{model['model_id']}/pls-point-predictions",
            json={
                "expected_model_manifest_sha256": model["manifest_sha256"],
                "rows": [
                    {
                        "client_row_id": "valid",
                        "values": {column_id: 1.0 for column_id in predictor_ids},
                    },
                    {
                        "client_row_id": "invalid",
                        "values": {predictor_ids[0]: 2.0},
                    },
                ],
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "pls_prediction_predictor_mapping_invalid"
    assert "2.0" not in response.text
