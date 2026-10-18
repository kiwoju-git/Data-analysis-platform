from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_regression_workflow_extensions_api import _fit_model

from app.core.config import Settings
from app.core.errors import ApiError
from app.main import create_app
from app.services import stored_prediction_report
from app.storage.metadata import get_analysis_run_record


def test_prediction_report_rejects_path_before_legacy_loader_opens_it(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        version, model_id, _ = _fit_model(client)
        response = client.post(
            f"/api/v1/regression-models/{model_id}/predictions",
            json={"dataset_version_id": version["version_id"]},
        )
        assert response.status_code == 200, response.text
        prediction_id = UUID(response.json()["prediction_id"])
        record = get_analysis_run_record(tmp_path, str(prediction_id))
        assert record is not None
        calls = []

        def reject(root, path, **kwargs):
            calls.append(path)
            assert path == f"workspaces/analyses/{prediction_id}/prediction_rows.jsonl"
            raise ApiError(
                code="analysis_report_source_dependency_mismatch",
                message="Unsafe stored path.",
                status_code=409,
            )

        def legacy_open(*args, **kwargs):
            raise AssertionError("Legacy row loader opened before safe path validation")

        monkeypatch.setattr(stored_prediction_report, "_safe_owned_path", reject)
        monkeypatch.setattr(stored_prediction_report, "_load_prediction_rows_context", legacy_open)
        with pytest.raises(ApiError) as captured:
            stored_prediction_report.load_stored_prediction_report(
                settings, prediction_id, record.result_sha256, "en"
            )
        assert captured.value.code == "analysis_report_source_dependency_mismatch"
        assert len(calls) == 1
