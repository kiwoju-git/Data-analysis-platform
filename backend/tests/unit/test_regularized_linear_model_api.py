import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    get_analysis_run_record,
    get_regression_model_record,
    metadata_db_path,
)


def upload(client):
    content = "y,x1,x2\n" + "\n".join(
        f"{2 + 3*i + (i % 3)*0.6},{i},{i*0.7 + (i % 4)*0.2}" for i in range(1, 25)
    )
    response = client.post(
        "/api/v1/datasets", files={"file": ("synthetic.csv", content, "text/csv")}
    )
    assert response.status_code == 201, response.text
    dataset_id = response.json()["dataset_id"]
    response = client.post(
        f"/api/v1/datasets/{dataset_id}/confirm-parsing",
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
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("estimator", ["ridge", "lasso", "elastic_net"])
@pytest.mark.parametrize("mode", ["fixed", "automatic_cv"])
def test_regularized_fit_model_dataset_and_manual_prediction_optimizer(tmp_path, estimator, mode):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = upload(client)
        columns = [column["column_id"] for column in version["columns"]]
        options = {
            "response_column_id": columns[0],
            "predictor_column_ids": columns[1:],
            "estimator": estimator,
            "fixed_alpha": 0.2 if mode == "fixed" else None,
            "regularization": {
                "mode": mode,
                "alpha_candidates": 5,
                "alpha_min": 0.001,
                "alpha_max": 10,
                "outer_folds": 3,
                "inner_folds": 3,
            },
        }
        if estimator == "elastic_net":
            options.update(fixed_l1_ratio=0.7, l1_ratio_candidates=[0.1, 0.7])
        response = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": METHOD_VERSIONS["regression.linear_model"],
                "dataset_version_id": version["version_id"],
                "options": options,
            },
        )
        assert response.status_code == 201, response.text
        envelope = response.json()
        result = envelope["result"]
        assert result["schema_version"] == 6
        assert result["estimator"]["kind"] == estimator
        assert result["validation"]["nested"] == (mode == "automatic_cv")
        assert "anova" not in result and "f_p_value" not in result["fit"]
        model_id = result["model_manifest"]["model_id"]
        model_response = client.get(f"/api/v1/regression-models/{model_id}")
        assert model_response.status_code == 200, model_response.text
        manifest = model_response.json()["manifest"]
        assert manifest["manifest_schema_version"] == 4 and manifest["model_kind"] == estimator
        catalog = client.get("/api/v1/regression-models").json()
        assert catalog["models"][0]["model_kind"] == estimator
        model_record = get_regression_model_record(tmp_path, model_id)
        model_path = tmp_path / model_record.manifest_path
        original = model_path.read_bytes()
        assert hashlib.sha256(original).hexdigest() == result["model_manifest"]["manifest_sha256"]
        response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={
                "dataset_version_id": version["version_id"],
                "include_intervals": True,
            },
        )
        assert response.status_code == 200, response.text
        prediction = response.json()
        assert prediction["model_kind"] == estimator
        assert prediction["prediction_uncertainty_kind"] == "point_only"
        assert prediction["interval_unavailability_reason"]
        assert all(
            row["mean_confidence_interval"] is None and row["prediction_interval"] is None
            for row in prediction["rows"]
        )
        restored = client.get(f"/api/v1/analysis-runs/{prediction['prediction_id']}/result")
        assert restored.status_code == 200, restored.text
        assert restored.json()["result"]["rows"] == prediction["rows"]
        manual = {
            "content": "x1\tx2\n5\t3.7",
            "delimiter": "tab",
            "has_header": True,
            "column_mappings": [
                {"source_column_id": c, "input_column_index": i} for i, c in enumerate(columns[1:])
            ],
            "expected_model_manifest_sha256": result["model_manifest"]["manifest_sha256"],
        }
        preflight = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-prediction-preflight", json=manual
        )
        assert preflight.status_code == 200, preflight.text
        manual["expected_normalized_input_sha256"] = preflight.json()["normalized_input_sha256"]
        response = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-predictions", json=manual
        )
        assert response.status_code == 201, response.text
        assert response.json()["rows"][0]["prediction_interval"] is None
        optimizer = client.post(
            f"/api/v1/regression-models/{model_id}/response-optimizations",
            json={
                "expected_model_manifest_sha256": result["model_manifest"]["manifest_sha256"],
                "goal": {"kind": "maximize", "lower": 0, "target": 100},
            },
        )
        assert optimizer.status_code == 201, optimizer.text
        assert optimizer.json()["result"]["model_kind"] == estimator
        optimization_id = optimizer.json()["optimization_id"]
        restored_optimizer = client.get(
            f"/api/v1/regression-models/{model_id}/response-optimizations/{optimization_id}"
        )
        assert restored_optimizer.status_code == 200, restored_optimizer.text
        assert restored_optimizer.json()["result"] == optimizer.json()["result"]
        for locale, title in (("en", "Regularized Regression"), ("ko", "정규화 회귀")):
            report = client.post(
                f"/api/v1/analysis-runs/{envelope['analysis_id']}/exports/html",
                json={"locale": locale},
            )
            assert report.status_code == 201, report.text
            report_id = report.json()["export_id"]
            html = client.get(
                f"/api/v1/analysis-runs/{envelope['analysis_id']}/exports/{report_id}/download"
            ).text
            assert title in html and f'<html lang="{locale}">' in html
            assert "<svg" in html and "<script" not in html
            assert "<th>p-value</th>" not in html and "<th>VIF</th>" not in html
        assert model_path.read_bytes() == original
        model_path.write_text(json.dumps({"tampered": True}), encoding="utf-8")
        assert client.get(f"/api/v1/regression-models/{model_id}").status_code == 409


def test_regularized_options_are_discriminated_and_legacy_ols_normalizes():
    from app.core.errors import ApiError
    from app.services.analysis_runners_regression import _validate_linear_model_options

    common = {"response_column_id": "y", "predictor_column_ids": ["x"]}
    assert _validate_linear_model_options(common)["estimator"] == "ols"
    for invalid in (
        {"estimator": "lasso", "model_selection": {"method": "backward_elimination"}},
        {"estimator": "ridge", "fixed_alpha": 0},
        {"estimator": "elastic_net", "fixed_l1_ratio": 1},
        {"estimator": "invalid"},
    ):
        with pytest.raises(ApiError):
            _validate_linear_model_options({**common, **invalid})


@pytest.mark.parametrize(
    "manifest_schema,result_schema,method_version", [(2, 4, "0.1.0"), (3, 5, "0.2.0")]
)
def test_legacy_ols_result_and_manifest_restore_without_rewrite(
    tmp_path, manifest_schema, result_schema, method_version
):
    from app.services.analysis_run_execution import canonical_json_bytes

    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = upload(client)
        columns = [column["column_id"] for column in version["columns"]]
        fitted = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "regression.linear_model",
                "method_version": "0.3.0",
                "dataset_version_id": version["version_id"],
                "options": {"response_column_id": columns[0], "predictor_column_ids": columns[1:]},
            },
        )
        assert fitted.status_code == 201, fitted.text
        envelope = fitted.json()
        analysis_id = envelope["analysis_id"]
        model_id = envelope["result"]["model_manifest"]["model_id"]
        model = get_regression_model_record(tmp_path, model_id)
        analysis = get_analysis_run_record(tmp_path, analysis_id)
        manifest_path = tmp_path / model.manifest_path
        result_path = tmp_path / analysis.result_path
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["manifest_schema_version"] = manifest_schema
        manifest["linear_model_result_schema_version"] = result_schema
        manifest["method_version"] = method_version
        manifest.pop("model_kind")
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        envelope["method_version"] = method_version
        envelope["provenance"]["method_version"] = method_version
        envelope["result"]["schema_version"] = result_schema
        envelope["result"].pop("estimator")
        envelope["result"]["model_manifest"].update(
            manifest_schema_version=manifest_schema, manifest_sha256=manifest_sha
        )
        result_bytes = canonical_json_bytes(envelope)
        config = json.loads(analysis.config_json)
        config["method_version"] = method_version
        config["options"].pop("estimator", None)
        # Construct a synthetic legacy fixture; production readers must not rewrite it.
        manifest_path.write_bytes(manifest_bytes)
        result_path.write_bytes(result_bytes)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE regression_models SET method_version=?, manifest_sha256=? WHERE model_id=?",
                (method_version, manifest_sha, model_id),
            )
            connection.execute(
                "UPDATE analysis_runs SET method_version=?, result_sha256=?, config_json=? "
                "WHERE analysis_id=?",
                (
                    method_version,
                    hashlib.sha256(result_bytes).hexdigest(),
                    json.dumps(config),
                    analysis_id,
                ),
            )
            connection.execute(
                "UPDATE analysis_artifacts SET sha256=? WHERE path=?",
                (manifest_sha, model.manifest_path),
            )
        restored = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        assert restored.status_code == 200, restored.text
        assert restored.json()["result"]["schema_version"] == result_schema
        assert client.get(f"/api/v1/regression-models/{model_id}").status_code == 200
        prediction = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={
                "dataset_version_id": version["version_id"],
                "include_intervals": True,
            },
        )
        assert prediction.status_code == 200, prediction.text
        assert prediction.json()["prediction_uncertainty_kind"] == "classical_ols"
        assert all(row["prediction_interval"] is not None for row in prediction.json()["rows"])
        assert manifest_path.read_bytes() == manifest_bytes
        assert result_path.read_bytes() == result_bytes
