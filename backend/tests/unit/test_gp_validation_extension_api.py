from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.analyses import GaussianProcessRegressionOptions
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_regression_model_record


def _dataset(client: TestClient, count: int = 24) -> dict[str, Any]:
    lines = ["y,x,batch,time"]
    for index in range(count):
        x = index / 5
        lines.append(f"{np.sin(x) + .05*x},{x},{'X'*121}-{index//8},{index}")
    uploaded = client.post(
        "/api/v1/datasets",
        files={
            "file": ("synthetic-validation.csv", "\n".join(lines).encode(), "text/csv"),
        },
    )
    assert uploaded.status_code == 201, uploaded.text
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
                "missing_tokens": ["", "NA"],
            },
            "columns": [],
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    version = confirmed.json()
    group = version["columns"][2]
    updated = client.patch(
        f"/api/v1/dataset-versions/{version['version_id']}/schema",
        json={
            "expected_schema_hash": version["schema_hash"],
            "columns": [
                {
                    "column_id": group["column_id"],
                    "display_name": "Batch ID",
                    "measurement_level": "nominal",
                    "role": "id",
                    "unit": None,
                }
            ],
        },
    )
    assert updated.status_code == 200, updated.text
    return client.get(f"/api/v1/dataset-versions/{version['version_id']}").json()


def _request(version: dict[str, Any], method: str) -> dict[str, Any]:
    ids = [column["column_id"] for column in version["columns"]]
    cv: dict[str, Any] = {"method": method, "folds": 3, "shuffle": False, "seed": 29}
    if method == "group_k_fold":
        cv["group_column_id"] = ids[2]
    else:
        cv.update(time_column_id=ids[3], time_format="numeric", time_unit="hour")
    return {
        "method_id": "regression.gaussian_process",
        "method_version": METHOD_VERSIONS["regression.gaussian_process"],
        "dataset_version_id": version["version_id"],
        "filter_snapshot": {"expression_version": 1, "conditions": []},
        "roles": {"response": ids[0], "predictors": ids[1]},
        "options": {
            "response_column_id": ids[0],
            "predictor_column_ids": [ids[1]],
            "optimizer_restarts": 0,
            "cv_optimizer_restarts": 0,
            "profile_points": 10,
            "surface_grid_size": 10,
            "cv": cv,
        },
    }


@pytest.mark.parametrize("method", ["group_k_fold", "time_series_split"])
def test_api_validation_metadata_storage_restore_and_report(tmp_path, method) -> None:
    settings = Settings(workspace_root=tmp_path / "검증 workspace")
    with TestClient(create_app(settings)) as client:
        version = _dataset(client)
        request = _request(version, method)
        created = client.post("/api/v1/analysis-runs", json=request)
        assert created.status_code == 201, created.text
        envelope = created.json()
        result = envelope["result"]
        plan = result["validation_plan"]
        assert len(result["predictors"]) == 1
        assert plan["effective_method"] == method
        if method == "group_k_fold":
            assert plan["distinct_group_count"] == 3
            assert plan["n_scored"] == 24
            assert all(
                fold["train_validation_group_intersection_count"] == 0 for fold in plan["folds"]
            )
        else:
            assert plan["n_unscored"] == 6
            assert all(
                point["cross_validated_fitted"] is None
                for point in result["diagnostics"]["points"][:6]
            )
        restored = client.get(f"/api/v1/analysis-runs/{envelope['analysis_id']}/result")
        assert restored.status_code == 200, restored.text
        assert restored.json()["result"]["validation_plan"] == plan
        pointer = result["model_manifest"]
        record = get_regression_model_record(settings.workspace_root, pointer["model_id"])
        assert record is not None
        raw = (settings.workspace_root / record.manifest_path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pointer["manifest_sha256"]
        assert json.loads(raw)["validation_plan"] == plan
        assert client.get(f"/api/v1/regression-models/{pointer['model_id']}").status_code == 200
        export_root = f"/api/v1/analysis-runs/{envelope['analysis_id']}/exports"
        exported = client.post(export_root + "/html", json={"locale": "en"})
        assert exported.status_code == 201, exported.text
        report = client.get(export_root + f"/{exported.json()['export_id']}/download")
        assert report.status_code == 200
        assert "<svg" in report.text and "<table" in report.text
        assert (settings.workspace_root / record.manifest_path).read_bytes() == raw


def test_api_lag_model_requires_explicit_past_values_and_matches_fitted(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _dataset(client)
        request = _request(version, "time_series_split")
        response_id = request["options"]["response_column_id"]
        request["options"]["lag_features"] = {"lagged_column_ids": [response_id], "lags": [1]}
        created = client.post("/api/v1/analysis-runs", json=request)
        assert created.status_code == 201, created.text
        result = created.json()["result"]
        assert result["sample"]["n_excluded_lag"] == 1
        assert result["feature_lineage"]["prediction_horizon"] == 1
        assert result["predictors"][1]["column_id"] == f"gp_lag:{response_id}:1"
        pointer = result["model_manifest"]
        index = 10
        previous_x = (index - 1) / 5
        values = {
            result["predictors"][0]["column_id"]: index / 5,
            result["predictors"][1]["column_id"]: float(np.sin(previous_x) + 0.05 * previous_x),
        }
        predicted = client.post(
            f"/api/v1/regression-models/{pointer['model_id']}/gaussian-process-predictions",
            json={
                "expected_model_manifest_sha256": pointer["manifest_sha256"],
                "rows": [{"client_row_id": "past-known", "values": values}],
            },
        )
        assert predicted.status_code == 200, predicted.text
        point = next(
            point for point in result["diagnostics"]["points"] if point["row_index"] == index
        )
        assert predicted.json()["rows"][0]["predicted_mean"] == pytest.approx(
            point["fitted"], abs=1e-9
        )
        values.pop(result["predictors"][1]["column_id"])
        rejected = client.post(
            f"/api/v1/regression-models/{pointer['model_id']}/gaussian-process-predictions",
            json={
                "expected_model_manifest_sha256": pointer["manifest_sha256"],
                "rows": [{"client_row_id": "missing-history", "values": values}],
            },
        )
        assert rejected.status_code == 422, rejected.text


@pytest.mark.parametrize(
    "cv,lag,code",
    [
        (
            {"method": "group_k_fold", "group_column_id": "g"},
            None,
            "gp_validation_shuffle_unsupported",
        ),
        ({"method": "group_k_fold", "shuffle": False}, None, "gp_group_column_required"),
        (
            {
                "method": "time_series_split",
                "shuffle": False,
                "time_column_id": "t",
                "time_format": "numeric",
            },
            None,
            "gp_time_unit_required",
        ),
        (
            {"method": "k_fold"},
            {"lagged_column_ids": ["y"], "lags": [1]},
            "gp_lag_requires_time_validation",
        ),
        ({"method": "k_fold"}, {"lagged_column_ids": ["y"], "lags": [0]}, "gp_lag_options_invalid"),
    ],
)
def test_api_option_contract_rejects_ambiguous_validation(cv, lag, code) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match=code):
        GaussianProcessRegressionOptions.model_validate(
            {
                "response_column_id": "y",
                "predictor_column_ids": ["x"],
                "cv": cv,
                "lag_features": lag,
            }
        )


@pytest.mark.parametrize("nominal_only", [False, True])
def test_mixed_api_storage_predictions_and_category_identity(tmp_path, nominal_only: bool) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _dataset(client)
        category = version["columns"][2]
        changed = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json={
                "expected_schema_hash": version["schema_hash"],
                "columns": [
                    {
                        "column_id": category["column_id"],
                        "display_name": "Category",
                        "measurement_level": "nominal",
                        "role": "feature",
                        "unit": None,
                    }
                ],
            },
        )
        assert changed.status_code == 200, changed.text
        version = client.get(f"/api/v1/dataset-versions/{version['version_id']}").json()
        request = _request(version, "time_series_split")
        request["options"]["cv"] = {"method": "k_fold", "folds": 3, "shuffle": True, "seed": 29}
        numeric_id = request["options"]["predictor_column_ids"][0]
        request["options"]["predictor_column_ids"] = [category["column_id"]] + (
            [] if nominal_only else [numeric_id]
        )
        request["roles"]["predictors"] = ",".join(request["options"]["predictor_column_ids"])
        created = client.post("/api/v1/analysis-runs", json=request)
        assert created.status_code == 201, created.text
        result = created.json()["result"]
        if nominal_only:
            assert "gp_nominal_only_signal" in result["warnings"]
        pointer = result["model_manifest"]
        record = get_regression_model_record(settings.workspace_root, pointer["model_id"])
        assert record is not None
        raw = (settings.workspace_root / record.manifest_path).read_bytes()
        manifest = json.loads(raw)
        assert manifest["preprocessing"]["predictors"][0]["vocabulary"] == [
            "X" * 121 + f"-{i}" for i in range(3)
        ]
        array_path = (
            settings.workspace_root / manifest["prediction_state"]["numeric_artifact"]["path"]
        )
        with np.load(array_path, allow_pickle=False) as arrays:
            assert not any(arrays[name].dtype.hasobject for name in arrays.files)
        path = f"/api/v1/regression-models/{pointer['model_id']}/gaussian-process-predictions"
        body = {
            "expected_model_manifest_sha256": pointer["manifest_sha256"],
            "save_result": True,
            "rows": [
                {
                    "client_row_id": "known",
                    "values": {
                        category["column_id"]: "X" * 121 + "-1",
                        **({} if nominal_only else {numeric_id: 2.0}),
                    },
                }
            ],
        }
        predicted = client.post(path, json=body)
        assert predicted.status_code == 200, predicted.text
        point = next(point for point in result["diagnostics"]["points"] if point["row_index"] == 10)
        assert predicted.json()["rows"][0]["predicted_mean"] == pytest.approx(
            point["fitted"], abs=1e-9
        )
        assert predicted.json()["saved_prediction"] is not None
        body["save_result"] = False
        body["rows"][0]["values"][category["column_id"]] = "unknown"
        rejected = client.post(path, json=body)
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["error"]["code"] == "gp_category_unknown"
        body["rows"][0]["values"][category["column_id"]] = 1
        assert client.post(path, json=body).status_code == 422
        body["rows"][0]["values"][category["column_id"]] = "X" * 121 + "-1"
        if not nominal_only:
            body["rows"][0]["values"][numeric_id] = "2.0"
            assert client.post(path, json=body).status_code == 422
        assert (settings.workspace_root / record.manifest_path).read_bytes() == raw


def test_extended_exact_api_runs_501_rows_in_owned_spawn_worker(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version = _dataset(client, 501)
        request = _request(version, "time_series_split")
        request["options"].update(
            cv={"method": "none"}, noise_mode="fixed", fixed_noise_standard_deviation=0.05
        )
        rejected = client.post("/api/v1/analysis-runs", json=request)
        assert rejected.status_code == 400
        assert rejected.json()["error"]["code"] == "gp_usable_rows_limit"
        request["options"]["resource_profile"] = "extended_exact"
        created = client.post("/api/v1/analysis-runs", json=request)
        assert created.status_code == 201, created.text
        result = created.json()["result"]
        assert result["sample"]["n_used"] == 501
        assert result["method"]["execution_mode"] == "spawn_worker"
        assert result["resource_budget"]["profile"] == "extended_exact"
        assert result["resource_budget"]["estimated_peak_bytes"] < 512 * 1024**2
        pointer = result["model_manifest"]
        prediction = client.post(
            f"/api/v1/regression-models/{pointer['model_id']}/gaussian-process-predictions",
            json={
                "expected_model_manifest_sha256": pointer["manifest_sha256"],
                "rows": [
                    {
                        "client_row_id": f"query:{i}",
                        "values": {result["predictors"][0]["column_id"]: i / 5},
                    }
                    for i in range(600)
                ],
            },
        )
        assert prediction.status_code == 200, prediction.text
        assert prediction.json()["row_count"] == 600
