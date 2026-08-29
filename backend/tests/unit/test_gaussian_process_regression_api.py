from __future__ import annotations

import hashlib
import io
import json

import numpy as np
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_regression_model_record


def _create_dataset(client: TestClient) -> dict[str, object]:
    lines = ["response,x1,x2"]
    for index in range(1, 17):
        x1 = index / 3
        x2 = ((index * 7) % 11) / 4
        response = np.sin(x1) + 0.35 * x2
        lines.append(f"{response:.12f},{x1:.12f},{x2:.12f}")
    uploaded = client.post(
        "/api/v1/datasets",
        files={"file": ("gp.csv", ("\n".join(lines) + "\n").encode(), "text/csv")},
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


def _create_gp_analysis(client: TestClient, version: dict[str, object]) -> dict[str, object]:
    columns = version["columns"]
    assert isinstance(columns, list)
    response_id = columns[0]["column_id"]
    predictor_ids = [item["column_id"] for item in columns[1:]]
    response = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "regression.gaussian_process",
            "method_version": "0.1.0",
            "dataset_version_id": version["version_id"],
            "filter_snapshot": {"expression_version": 1, "conditions": []},
            "roles": {"response": response_id, "predictors": ",".join(predictor_ids)},
            "options": {
                "response_column_id": response_id,
                "predictor_column_ids": predictor_ids,
                "missing_policy": "complete_case",
                "kernel_preset": "matern_5_2_ard",
                "noise_mode": "estimate",
                "fixed_noise_standard_deviation": None,
                "standardize_predictors": True,
                "normalize_response": True,
                "jitter": 1e-8,
                "optimizer_restarts": 0,
                "cv_optimizer_restarts": 0,
                "cv": {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 29},
                "plot_point_limit": 100,
                "profile_points": 10,
                "surface_grid_size": 10,
                "time_budget_seconds": 120,
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_gp_analysis_persists_safe_numeric_state_and_predicts(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_dataset(client)
        payload = _create_gp_analysis(client, version)
        result = payload["result"]
        model_pointer = result["model_manifest"]
        model_id = model_pointer["model_id"]
        catalog = client.get("/api/v1/regression-models")
        workspace_catalog = client.get("/api/v1/assets?category=models")
        manifest_response = client.get(f"/api/v1/regression-models/{model_id}")
        predictors = result["predictors"]
        prediction = client.post(
            f"/api/v1/regression-models/{model_id}/gaussian-process-predictions",
            json={
                "expected_model_manifest_sha256": model_pointer["manifest_sha256"],
                "rows": [
                    {
                        "client_row_id": "inside",
                        "values": {
                            predictors[0]["column_id"]: 2.5,
                            predictors[1]["column_id"]: 1.0,
                        },
                    },
                    {
                        "client_row_id": "outside",
                        "values": {
                            predictors[0]["column_id"]: 100.0,
                            predictors[1]["column_id"]: 100.0,
                        },
                    },
                ],
            },
        )

        assert payload["method_id"] == "regression.gaussian_process"
        assert result["schema_version"] == 1
        assert result["summary_type"] == "gaussian_process_regression"
        assert "prediction_basis" not in result
        assert result["conditional_profiles"]
        assert result["two_predictor_surface"]["points"]
        assert result["model_summary"]["press"] is not None
        assert catalog.status_code == 200
        assert catalog.json()["models"][0]["method_id"] == "regression.gaussian_process"
        assert workspace_catalog.status_code == 200
        open_path = workspace_catalog.json()["items"][0]["open_target"]["path"]
        assert "/regression.gaussian_process?" in open_path
        assert f"analysis_id={payload['analysis_id']}" in open_path
        assert "section=prediction" in open_path
        assert manifest_response.status_code == 200
        assert prediction.status_code == 200, prediction.text
        prediction_payload = prediction.json()
        assert prediction_payload["interval_kind"] == "latent_and_new_observation"
        assert (
            prediction_payload["rows"][0]["predictive_standard_deviation"]
            >= (prediction_payload["rows"][0]["latent_standard_deviation"])
        )
        assert prediction_payload["rows"][1]["warnings"] == ["gp_extrapolation"]

    model_record = get_regression_model_record(settings.workspace_root, model_id)
    assert model_record is not None
    manifest_path = settings.workspace_root / model_record.manifest_path
    manifest_bytes = manifest_path.read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == model_record.manifest_sha256
    manifest = json.loads(manifest_bytes)
    assert manifest["manifest_kind"] == "gaussian_process_model_manifest"
    artifact = manifest["prediction_state"]["numeric_artifact"]
    artifact_path = settings.workspace_root / artifact["path"]
    artifact_bytes = artifact_path.read_bytes()
    assert hashlib.sha256(artifact_bytes).hexdigest() == artifact["sha256"]
    with np.load(io.BytesIO(artifact_bytes), allow_pickle=False) as arrays:
        assert set(arrays.files) == set(artifact["arrays"])
        assert all(not arrays[name].dtype.hasobject for name in arrays.files)
    assert "absolute_path" not in json.dumps(manifest)


def test_gp_prediction_rejects_tampered_artifact_and_deletion_removes_both_files(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_dataset(client)
        payload = _create_gp_analysis(client, version)
        model = payload["result"]["model_manifest"]
        model_record = get_regression_model_record(settings.workspace_root, model["model_id"])
        assert model_record is not None
        manifest_path = settings.workspace_root / model_record.manifest_path
        manifest = json.loads(manifest_path.read_bytes())
        numeric_path = (
            settings.workspace_root / manifest["prediction_state"]["numeric_artifact"]["path"]
        )
        numeric_path.write_bytes(numeric_path.read_bytes() + b"tamper")
        predictor_ids = [item["column_id"] for item in payload["result"]["predictors"]]
        rejected = client.post(
            f"/api/v1/regression-models/{model['model_id']}/gaussian-process-predictions",
            json={
                "expected_model_manifest_sha256": model["manifest_sha256"],
                "rows": [{"client_row_id": "row", "values": {item: 1 for item in predictor_ids}}],
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "gp_model_artifact_checksum_mismatch"

        numeric_path.write_bytes(numeric_path.read_bytes()[:-6])
        preflight = client.get(f"/api/v1/regression-models/{model['model_id']}/deletion-preflight")
        assert preflight.status_code == 200, preflight.text
        preflight_payload = preflight.json()
        assert preflight_payload["counts"]["manifest_artifact_count"] == 2
        deleted = client.request(
            "DELETE",
            f"/api/v1/regression-models/{model['model_id']}",
            json={
                "confirmation_model_id": model["model_id"],
                "expected_deletion_manifest_sha256": preflight_payload["deletion_manifest_sha256"],
                "mode": "model_only",
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert not manifest_path.exists()
        assert not numeric_path.exists()


def test_gp_invalid_prediction_is_atomic(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_dataset(client)
        payload = _create_gp_analysis(client, version)
        model = payload["result"]["model_manifest"]
        predictor_ids = [item["column_id"] for item in payload["result"]["predictors"]]
        response = client.post(
            f"/api/v1/regression-models/{model['model_id']}/gaussian-process-predictions",
            json={
                "expected_model_manifest_sha256": model["manifest_sha256"],
                "rows": [
                    {"client_row_id": "valid", "values": {item: 1 for item in predictor_ids}},
                    {"client_row_id": "invalid", "values": {predictor_ids[0]: 1}},
                ],
            },
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "gp_prediction_input_invalid"


def test_gp_html_reports_use_saved_result_and_requested_locale(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _create_dataset(client)
        analysis = _create_gp_analysis(client, version)
        analysis_id = analysis["analysis_id"]
        english = client.post(
            f"/api/v1/analysis-runs/{analysis_id}/exports/html",
            json={"locale": "en"},
        )
        korean = client.post(
            f"/api/v1/analysis-runs/{analysis_id}/exports/html",
            json={"locale": "ko"},
        )
        assert english.status_code == 201, english.text
        assert korean.status_code == 201, korean.text
        english_download = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{english.json()['export_id']}/download"
        )
        korean_download = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/" f"{korean.json()['export_id']}/download"
        )

    english_text = english_download.content.decode("utf-8")
    korean_text = korean_download.content.decode("utf-8")
    assert '<html lang="en">' in english_text
    assert "Gaussian Process Model Summary" in english_text
    assert "Kernel Hyperparameters" in english_text
    assert "Observed versus Fitted" in english_text
    assert '<html lang="ko">' in korean_text
    assert "Gaussian Process 모형 요약" in korean_text
    assert "음의 로그 예측밀도" in korean_text
    assert "관측값 대 적합값" in korean_text
    assert "<script" not in english_text
    assert "https://" not in english_text
