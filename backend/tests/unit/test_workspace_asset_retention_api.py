import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    WorkspaceAssetStorageConflict,
    get_attribute_control_limit_set_record,
    get_regression_model_record,
)


def test_regression_model_deletion_preserves_source_analysis_and_blocks_predictions(
    tmp_path: Path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        first = _create_linear_model(client)
        model_id = first["model_id"]
        source_analysis_id = first["analysis_id"]
        record = get_regression_model_record(tmp_path, model_id)
        assert record is not None
        manifest_path = tmp_path / record.manifest_path
        manifest_size = manifest_path.stat().st_size
        preflight_response = client.get(f"/api/v1/regression-models/{model_id}/deletion-preflight")
        preflight = preflight_response.json()
        wrong_confirmation = client.request(
            "DELETE",
            f"/api/v1/regression-models/{model_id}",
            json={
                "confirmation_model_id": str(uuid4()),
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        deleted = client.request(
            "DELETE",
            f"/api/v1/regression-models/{model_id}",
            json={
                "confirmation_model_id": model_id,
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        source_result = client.get(f"/api/v1/analysis-runs/{source_analysis_id}/result")
        source_delete = client.get(f"/api/v1/analysis-runs/{source_analysis_id}/deletion-preflight")
        missing_model = client.get(f"/api/v1/regression-models/{model_id}")

        second = _create_linear_model(client)
        prediction = client.post(
            f"/api/v1/regression-models/{second['model_id']}/predictions",
            json={
                "dataset_version_id": second["dataset_version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            },
        )
        blocked_preflight_response = client.get(
            f"/api/v1/regression-models/{second['model_id']}/deletion-preflight"
        )
        blocked_preflight = blocked_preflight_response.json()
        blocked = client.request(
            "DELETE",
            f"/api/v1/regression-models/{second['model_id']}",
            json={
                "confirmation_model_id": second["model_id"],
                "expected_deletion_manifest_sha256": blocked_preflight["deletion_manifest_sha256"],
            },
        )
        dependent_page = client.get(
            f"/api/v1/regression-models/{second['model_id']}/predictions",
            params={"offset": 0, "limit": 20},
        )
        cascaded = client.request(
            "DELETE",
            f"/api/v1/regression-models/{second['model_id']}",
            json={
                "confirmation_model_id": second["model_id"],
                "expected_deletion_manifest_sha256": blocked_preflight[
                    "cascade_deletion_manifest_sha256"
                ],
                "mode": "model_and_predictions",
            },
        )
        prediction_after_cascade = client.get(
            f"/api/v1/analysis-runs/{prediction.json()['prediction_id']}"
        )
        source_after_cascade = client.get(f"/api/v1/analysis-runs/{second['analysis_id']}/result")
        dataset_after_cascade = client.get(
            f"/api/v1/dataset-versions/{second['dataset_version_id']}"
        )

    assert preflight_response.status_code == 200
    assert preflight["deletion_ready"] is True
    assert preflight["blockers"] == []
    assert preflight["counts"]["regression_model_count"] == 1
    assert preflight["counts"]["manifest_artifact_count"] == 1
    assert preflight["counts"]["manifest_file_count"] == 1
    assert preflight["counts"]["manifest_file_bytes"] == manifest_size
    assert preflight["counts"]["metadata_record_count"] == 2
    assert preflight["counts"]["dependent_prediction_count"] == 0
    assert preflight["counts"]["dependent_prediction_file_count"] == 0
    assert wrong_confirmation.status_code == 409
    assert wrong_confirmation.json()["error"]["code"] == (
        "regression_model_deletion_confirmation_mismatch"
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["cleanup_status"] == "deleted"
    assert get_regression_model_record(tmp_path, model_id) is None
    assert not manifest_path.exists()
    assert source_result.status_code == 200
    assert source_delete.status_code == 200
    assert source_delete.json()["deletion_ready"] is True
    assert source_delete.json()["counts"]["regression_model_count"] == 0
    assert source_delete.json()["counts"]["analysis_artifact_count"] == 1
    assert missing_model.status_code == 404
    assert missing_model.json()["error"]["code"] == "regression_model_not_found"
    assert str(tmp_path) not in json.dumps(missing_model.json())
    assert prediction.status_code == 200, prediction.text
    assert blocked_preflight_response.status_code == 200
    assert blocked_preflight["deletion_ready"] is False
    assert blocked_preflight["blockers"] == ["regression_model_deletion_prediction_dependency"]
    assert blocked_preflight["counts"]["dependent_prediction_count"] == 1
    assert blocked_preflight["cascade_deletion_ready"] is True
    assert blocked_preflight["cascade_deletion_manifest_sha256"] is not None
    assert len(blocked_preflight["dependent_predictions"]) == 1
    assert (
        blocked_preflight["dependent_predictions"][0]["analysis_id"]
        == (prediction.json()["prediction_id"])
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "regression_model_deletion_blocked"
    assert str(tmp_path) not in json.dumps(blocked.json())
    assert dependent_page.status_code == 200, dependent_page.text
    assert dependent_page.json()["total"] == 1
    assert dependent_page.json()["predictions"][0]["target_dataset_display_name"].startswith(
        "Dataset v"
    )
    assert str(tmp_path) not in dependent_page.text
    assert cascaded.status_code == 200, cascaded.text
    assert cascaded.json()["deletion_mode"] == "model_and_predictions"
    assert prediction_after_cascade.status_code == 404
    assert source_after_cascade.status_code == 200
    assert dataset_after_cascade.status_code == 200


def test_limit_set_deletion_preserves_phase_one_and_blocks_phase_two(tmp_path: Path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        first = _create_limit_set(client)
        limit_set_id = first["limit_set_id"]
        source_analysis_id = first["source_analysis_id"]
        record = get_attribute_control_limit_set_record(tmp_path, limit_set_id)
        assert record is not None
        asset_path = tmp_path / record.asset_path
        asset_size = asset_path.stat().st_size
        preflight_response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{limit_set_id}" "/deletion-preflight"
        )
        preflight = preflight_response.json()
        deleted = client.request(
            "DELETE",
            f"/api/v1/quality/attribute-control-limit-sets/{limit_set_id}",
            json={
                "confirmation_limit_set_id": limit_set_id,
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        source_result = client.get(f"/api/v1/analysis-runs/{source_analysis_id}/result")
        source_delete = client.get(f"/api/v1/analysis-runs/{source_analysis_id}/deletion-preflight")

        second = _create_limit_set(client)
        phase_2 = _run_phase_2(client, second)
        blocked_preflight_response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{second['limit_set_id']}"
            "/deletion-preflight"
        )
        blocked_preflight = blocked_preflight_response.json()
        blocked = client.request(
            "DELETE",
            f"/api/v1/quality/attribute-control-limit-sets/{second['limit_set_id']}",
            json={
                "confirmation_limit_set_id": second["limit_set_id"],
                "expected_deletion_manifest_sha256": blocked_preflight["deletion_manifest_sha256"],
            },
        )

    assert preflight_response.status_code == 200
    assert preflight["deletion_ready"] is True
    assert preflight["blockers"] == []
    assert preflight["counts"] == {
        "limit_set_count": 1,
        "asset_file_count": 1,
        "asset_file_bytes": asset_size,
        "metadata_record_count": 1,
        "dependent_phase_2_analysis_count": 0,
    }
    assert deleted.status_code == 200, deleted.text
    assert get_attribute_control_limit_set_record(tmp_path, limit_set_id) is None
    assert not asset_path.exists()
    assert source_result.status_code == 200
    assert source_delete.status_code == 200
    assert source_delete.json()["deletion_ready"] is True
    assert phase_2.status_code == 201, phase_2.text
    assert blocked_preflight_response.status_code == 200
    assert blocked_preflight["deletion_ready"] is False
    assert blocked_preflight["blockers"] == [
        "attribute_control_limit_set_deletion_phase_2_dependency"
    ]
    assert blocked_preflight["counts"]["dependent_phase_2_analysis_count"] == 1
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == ("attribute_control_limit_set_deletion_blocked")
    assert str(tmp_path) not in json.dumps(blocked.json())


def test_workspace_asset_quarantine_recovery_restores_uncommitted_moves(
    tmp_path: Path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        model = _create_linear_model(client)
        model_record = get_regression_model_record(tmp_path, model["model_id"])
        assert model_record is not None
        model_path = tmp_path / model_record.manifest_path
        model_quarantine = model_path.with_name(
            f".delete-m-{model_record.model_id}-{uuid4().hex[:16]}.q"
        )
        os.replace(model_path, model_quarantine)

        limit_set = _create_limit_set(client)
        limit_record = get_attribute_control_limit_set_record(tmp_path, limit_set["limit_set_id"])
        assert limit_record is not None
        limit_path = tmp_path / limit_record.asset_path
        limit_quarantine = limit_path.with_name(
            f".delete-l-{limit_record.limit_set_id}-{uuid4().hex[:16]}.q"
        )
        os.replace(limit_path, limit_quarantine)

    with TestClient(create_app(settings)) as client:
        recovery = client.app.state.workspace_asset_quarantine_recovery
        model_restored = client.get(f"/api/v1/regression-models/{model['model_id']}")
        limit_restored = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{limit_set['limit_set_id']}"
        )

    assert recovery.restored_file_count == 2
    assert recovery.deleted_file_count == 0
    assert recovery.pending_file_count == 0
    assert model_path.exists() and limit_path.exists()
    assert not model_quarantine.exists() and not limit_quarantine.exists()
    assert model_restored.status_code == 200
    assert limit_restored.status_code == 200


def test_model_prediction_cascade_restores_files_on_database_conflict(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        model = _create_linear_model(client)
        prediction = client.post(
            f"/api/v1/regression-models/{model['model_id']}/predictions",
            json={
                "dataset_version_id": model["dataset_version_id"],
                "confidence_level": 0.95,
                "missing_policy": "complete_case",
                "include_intervals": True,
            },
        ).json()
        preflight = client.get(
            f"/api/v1/regression-models/{model['model_id']}/deletion-preflight"
        ).json()
        record = get_regression_model_record(tmp_path, model["model_id"])
        assert record is not None
        model_path = tmp_path / record.manifest_path

        def conflict(*args, **kwargs):
            del args, kwargs
            raise WorkspaceAssetStorageConflict("regression_model_deletion_conflict")

        monkeypatch.setattr(
            "app.services.workspace_asset_retention."
            "delete_regression_model_with_prediction_records",
            conflict,
        )
        response = client.request(
            "DELETE",
            f"/api/v1/regression-models/{model['model_id']}",
            json={
                "confirmation_model_id": model["model_id"],
                "expected_deletion_manifest_sha256": preflight["cascade_deletion_manifest_sha256"],
                "mode": "model_and_predictions",
            },
        )
        prediction_after = client.get(f"/api/v1/analysis-runs/{prediction['prediction_id']}/result")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "regression_model_deletion_conflict"
    assert model_path.exists()
    assert get_regression_model_record(tmp_path, model["model_id"]) is not None
    assert prediction_after.status_code == 200


def test_limit_set_can_be_deleted_after_source_schema_marks_analysis_stale(
    tmp_path: Path,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client)
        version_id = limit_set["target_dataset_version_id"]
        schema = client.get(f"/api/v1/dataset-versions/{version_id}/schema").json()
        column = schema["columns"][0]
        changed = client.patch(
            f"/api/v1/dataset-versions/{version_id}/schema",
            json={
                "columns": [
                    {
                        "column_id": column["column_id"],
                        "display_name": "Count revised",
                        "measurement_level": column["measurement_level"],
                        "role": column["role"],
                        "unit": column["unit"],
                    }
                ]
            },
        )
        source = client.get(f"/api/v1/analysis-runs/{limit_set['source_analysis_id']}")
        preflight_response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{limit_set['limit_set_id']}"
            "/deletion-preflight"
        )
        preflight = preflight_response.json()
        deleted = client.request(
            "DELETE",
            f"/api/v1/quality/attribute-control-limit-sets/{limit_set['limit_set_id']}",
            json={
                "confirmation_limit_set_id": limit_set["limit_set_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )

    assert changed.status_code == 200
    assert source.json()["stale"] is True
    assert preflight_response.status_code == 200, preflight_response.text
    assert preflight["deletion_ready"] is True
    assert deleted.status_code == 200, deleted.text


def _create_linear_model(client: TestClient) -> dict[str, str]:
    version = _upload_confirmed_csv(
        client,
        b"y,x1,x2\n10,1,3\n13,2,2\n15,3,4\n18,4,3\n21,5,5\n23,6,4\n26,7,6\n29,8,5\n",
    )
    response_id = version["columns"][0]["column_id"]
    predictor_ids = [column["column_id"] for column in version["columns"][1:]]
    response = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "regression.linear_model",
            "method_version": METHOD_VERSIONS["regression.linear_model"],
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
            },
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return {
        "analysis_id": payload["analysis_id"],
        "dataset_version_id": version["version_id"],
        "model_id": payload["result"]["model_manifest"]["model_id"],
    }


def _create_limit_set(client: TestClient) -> dict[str, str]:
    rows = "\n".join(f"{value},20" for value in ([10, 9, 11, 10] * 5))
    version = _upload_confirmed_csv(client, f"count,total\n{rows}\n".encode())
    count_id = version["columns"][0]["column_id"]
    denominator_id = version["columns"][1]["column_id"]
    phase_1 = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "quality.attribute_control_chart",
            "method_version": METHOD_VERSIONS["quality.attribute_control_chart"],
            "dataset_version_id": version["version_id"],
            "roles": {"count": count_id},
            "options": {
                "phase": "phase_1",
                "chart_type": "p",
                "count_definition": "defectives",
                "count_column_id": count_id,
                "denominator_column_id": denominator_id,
                "constant_opportunity_confirmed": False,
                "point_limit": 100,
            },
        },
    )
    assert phase_1.status_code == 201, phase_1.text
    created = client.post(
        "/api/v1/quality/attribute-control-limit-sets",
        json={"source_analysis_id": phase_1.json()["analysis_id"]},
    )
    assert created.status_code == 201, created.text
    return {
        **created.json(),
        "count_column_id": count_id,
        "denominator_column_id": denominator_id,
        "target_dataset_version_id": version["version_id"],
    }


def _run_phase_2(client: TestClient, limit_set: dict[str, str]):
    return client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "quality.attribute_control_chart",
            "method_version": METHOD_VERSIONS["quality.attribute_control_chart"],
            "dataset_version_id": limit_set["target_dataset_version_id"],
            "roles": {"count": limit_set["count_column_id"]},
            "options": {
                "phase": "phase_2",
                "limit_set_id": limit_set["limit_set_id"],
                "chart_type": "p",
                "count_definition": "defectives",
                "count_column_id": limit_set["count_column_id"],
                "denominator_column_id": limit_set["denominator_column_id"],
                "constant_opportunity_confirmed": False,
                "point_limit": 100,
            },
        },
    )


def _upload_confirmed_csv(client: TestClient, content: bytes) -> dict:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("asset-retention.csv", content, "text/csv")},
    )
    assert upload.status_code == 201
    confirmed = client.post(
        f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
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
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()
