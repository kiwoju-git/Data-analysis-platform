from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_regression_pasted_prediction_preflight_execute_and_rows(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version, model_id, manifest_sha = _fit_model(client)
        catalog_before = client.get("/api/v1/dataset-versions?limit=100&offset=0").json()["total"]
        preflight_request = {
            "content": "x1\tx2\n2\t4\n4\t3\n20\t5\n",
            "has_header": True,
            "delimiter": "tab",
            "column_mappings": [],
            "expected_model_manifest_sha256": manifest_sha,
        }
        preflight = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-prediction-preflight",
            json=preflight_request,
        )
        assert preflight.status_code == 200, preflight.text
        preflight_payload = preflight.json()
        assert preflight_payload["prediction_ready"] is True
        assert preflight_payload["row_count_total"] == 3
        assert preflight_payload["row_count_usable"] == 3
        assert len(preflight_payload["normalized_input_sha256"]) == 64

        executed = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-predictions",
            json={
                **preflight_request,
                "expected_normalized_input_sha256": preflight_payload["normalized_input_sha256"],
                "confidence_level": 0.95,
                "include_intervals": True,
            },
        )
        assert executed.status_code == 201, executed.text
        payload = executed.json()
        assert payload["input_kind"] == "pasted_table"
        assert payload["source_dataset_version_id"] == version["version_id"]
        assert payload["row_count_predicted"] == 3
        assert payload["rows"][0]["predictor_values"] == {
            version["columns"][1]["column_id"]: 2.0,
            version["columns"][2]["column_id"]: 4.0,
        }
        assert payload["rows"][0]["mean_confidence_interval"] is not None
        assert "prediction_extrapolation_risk" in payload["rows"][2]["warnings"]

        rows = client.get(
            f"/api/v1/regression-models/pasted-predictions/{payload['prediction_id']}/rows",
        )
        assert rows.status_code == 200
        assert rows.json()["total"] == 3
        assert len(rows.json()["rows"]) == 3
        deletion = client.get(f"/api/v1/regression-models/{model_id}/deletion-preflight")
        assert deletion.status_code == 200
        assert deletion.json()["preflight_schema_version"] == 3
        assert deletion.json()["deletion_ready"] is False
        assert deletion.json()["counts"]["dependent_pasted_prediction_count"] == 1
        assert (
            "regression_model_deletion_pasted_prediction_dependency" in deletion.json()["blockers"]
        )
        run_preflight = client.get(
            f"/api/v1/analysis-runs/{payload['prediction_id']}/deletion-preflight"
        )
        assert run_preflight.status_code == 200, run_preflight.text
        assert run_preflight.json()["counts"]["artifact_file_count"] == 2
        assert run_preflight.json()["counts"]["total_file_count"] == 3
        deleted = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{payload['prediction_id']}/deletion",
            json={
                "confirmation_analysis_id": payload["prediction_id"],
                "expected_deletion_manifest_sha256": run_preflight.json()[
                    "deletion_manifest_sha256"
                ],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["deleted_counts"]["analysis_artifact_count"] == 2
        after_delete = client.get(f"/api/v1/regression-models/{model_id}/deletion-preflight")
        assert after_delete.status_code == 200
        assert after_delete.json()["counts"]["dependent_pasted_prediction_count"] == 0
        catalog_after = client.get("/api/v1/dataset-versions?limit=100&offset=0").json()["total"]
        assert catalog_after == catalog_before


def test_regression_pasted_prediction_rejects_changed_input_hash(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        _, model_id, manifest_sha = _fit_model(client)
        response = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-predictions",
            json={
                "content": "x1,x2\n2,4\n",
                "has_header": True,
                "delimiter": "comma",
                "column_mappings": [],
                "expected_model_manifest_sha256": manifest_sha,
                "expected_normalized_input_sha256": "0" * 64,
                "confidence_level": 0.95,
                "include_intervals": True,
            },
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "regression_pasted_prediction_input_changed"


def test_regression_pasted_prediction_distinguishes_header_only_from_one_data_row(
    tmp_path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version, model_id, manifest_sha = _fit_model(client)
        mappings = [
            {
                "input_column_index": index,
                "source_column_id": version["columns"][index + 1]["column_id"],
            }
            for index in range(2)
        ]
        request = {
            "content": "2\t4",
            "delimiter": "tab",
            "column_mappings": mappings,
            "expected_model_manifest_sha256": manifest_sha,
        }
        header_only = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-prediction-preflight",
            json={**request, "has_header": True},
        )
        one_row = client.post(
            f"/api/v1/regression-models/{model_id}/pasted-prediction-preflight",
            json={**request, "has_header": False},
        )

    assert header_only.status_code == 422
    assert header_only.json()["error"]["code"] == (
        "regression_pasted_prediction_header_without_data"
    )
    assert one_row.status_code == 200, one_row.text
    assert one_row.json()["row_count_total"] == 1
    assert one_row.json()["row_count_usable"] == 1
    assert one_row.json()["prediction_ready"] is True


def test_regression_response_optimizer_api_persists_and_restores(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version, model_id, manifest_sha = _fit_model(client)
        x1 = version["columns"][1]["column_id"]
        response = client.post(
            f"/api/v1/regression-models/{model_id}/response-optimizations",
            json={
                "expected_model_manifest_sha256": manifest_sha,
                "goal": {"kind": "maximize", "lower": 8.0, "target": 30.0, "upper": None},
                "factor_bounds": [],
                "fixed_categorical_levels": [],
                "linear_constraints": [
                    {
                        "name": "x1 cap",
                        "coefficients": {x1: 1.0},
                        "relation": "less_than_or_equal",
                        "bound": 7.0,
                    }
                ],
                "search": {
                    "random_seed": 11,
                    "random_candidate_count": 64,
                    "multi_start_count": 4,
                    "max_iterations": 100,
                    "max_evaluations": 2_000,
                    "profile_point_count": 21,
                },
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["method_id"] == "regression.linear_model_optimizer"
        assert payload["result"]["recommendation"]["within_training_domain"] is True
        assert payload["result"]["search"]["global_optimum_guaranteed"] is False
        restored = client.get(
            f"/api/v1/regression-models/{model_id}/response-optimizations/{payload['optimization_id']}",
        )
        listed = client.get(f"/api/v1/regression-models/{model_id}/response-optimizations")
        deletion = client.get(f"/api/v1/regression-models/{model_id}/deletion-preflight")
        run_preflight = client.get(
            f"/api/v1/analysis-runs/{payload['optimization_id']}/deletion-preflight"
        )
        assert run_preflight.status_code == 200, run_preflight.text
        assert run_preflight.json()["counts"]["artifact_file_count"] == 0
        deleted = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{payload['optimization_id']}/deletion",
            json={
                "confirmation_analysis_id": payload["optimization_id"],
                "expected_deletion_manifest_sha256": run_preflight.json()[
                    "deletion_manifest_sha256"
                ],
            },
        )
        assert deleted.status_code == 200, deleted.text

    assert restored.status_code == 200
    assert restored.json() == payload
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert deletion.status_code == 200
    assert deletion.json()["counts"]["dependent_optimization_count"] == 1
    assert "regression_model_deletion_optimization_dependency" in deletion.json()["blockers"]


def _fit_model(client: TestClient) -> tuple[dict[str, object], str, str]:
    upload = client.post(
        "/api/v1/datasets",
        files={
            "file": (
                "regression.csv",
                b"y,x1,x2\n10,1,3\n13,2,2\n15,3,4\n18,4,3\n20,5,5\n23,6,4\n26,7,6\n29,8,5\n",
                "text/csv",
            )
        },
    )
    dataset_id = upload.json()["dataset_id"]
    confirmed = client.post(
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
                "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
            },
            "columns": [],
        },
    )
    version = confirmed.json()
    response_id = version["columns"][0]["column_id"]
    predictor_ids = [item["column_id"] for item in version["columns"][1:]]
    fitted = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "regression.linear_model",
            "method_version": "0.2.0",
            "dataset_version_id": version["version_id"],
            "roles": {"response": response_id, "predictors": ",".join(predictor_ids)},
            "options": {
                "response_column_id": response_id,
                "predictor_column_ids": predictor_ids,
                "alpha": 0.05,
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intercept": True,
                "covariance_type": "standard",
                "model_selection": {
                    "method": "none",
                    "alpha_to_remove": 0.1,
                    "hierarchy_policy": "strong",
                },
            },
        },
    )
    assert fitted.status_code == 201, fitted.text
    pointer = fitted.json()["result"]["model_manifest"]
    return version, pointer["model_id"], pointer["manifest_sha256"]
