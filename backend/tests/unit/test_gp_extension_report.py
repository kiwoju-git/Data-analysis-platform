from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient
from test_completed_predictions import _model
from test_gp_mixed_integration import _columns, _options, _rows

from app.core.config import Settings
from app.main import create_app
from app.services.gaussian_process_report import gp_saved_sections, gp_surface_sections
from app.statistics.gaussian_process_regression import calculate_gaussian_process_regression
from app.storage.metadata import get_analysis_run_record


def test_real_mixed_result_report_preserves_category_and_three_surface_quantities(monkeypatch):
    columns = _columns()
    result = calculate_gaussian_process_regression(
        _rows(), columns[0], columns[1:], options=_options()
    )
    payload = {key: value for key, value in result.items() if key != "prediction_basis"}
    before = json.dumps(payload, sort_keys=True, allow_nan=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("report must not fit or reload source rows")

    monkeypatch.setattr("app.statistics.gaussian_process_regression._fit_model", forbidden)
    monkeypatch.setattr("app.services.dataset_rows.get_dataset_rows_context", forbidden)
    for locale in ("ko", "en"):
        sections = gp_saved_sections(payload, locale) + gp_surface_sections(payload, locale)
        by_id = {section.section_id: section for section in sections}
        profile = by_id["gp_profiles"].markup
        assert "first" in profile and "second" in profile
        assert "<table" in profile and "<svg" in profile
        assert all(
            by_id[key].status == "rendered"
            for key in (
                "gp_surface_mean",
                "gp_surface_sd",
                "gp_surface_latent_sd",
                "gp_validation_plan",
                "gp_resource_budget",
            )
        )
        assert payload["validation_plan"]["split_plan_sha256"] in by_id["gp_validation_plan"].markup
        assert "row_weighted" in by_id["gp_validation_plan"].markup
    assert json.dumps(payload, sort_keys=True, allow_nan=False) == before


def test_custom_surface_save_restore_and_managed_report_use_applied_view(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis, pointer, body, url = _model(client, "gaussian_process")
        predictors = analysis["result"]["predictors"]
        x_id, y_id = [item["column_id"] for item in predictors[:2]]
        holds = {item["column_id"]: 1.5 for item in predictors[2:]}
        rows = [
            {"client_row_id": f"cell:{x}:{y}", "values": {x_id: x, y_id: y, **holds}}
            for x in [1.0, 2.0]
            for y in [3.0, 4.0]
        ]
        body.update(
            rows=rows,
            save_result=True,
            surface_view={
                "x_column_id": x_id,
                "y_column_id": y_id,
                "hold_values": holds,
                "grid_size": 2,
                "display_mode": "latent_sd",
            },
        )
        owner = get_analysis_run_record(tmp_path, analysis["analysis_id"])
        original = (tmp_path / owner.result_path).read_bytes()
        saved = client.post(url, json=body)
        assert saved.status_code == 200, saved.text
        source = saved.json()["saved_prediction"]["source"]
        invalid = client.post(url, json={**body, "rows": rows[:-1]})
        assert invalid.status_code == 400, invalid.text
        assert invalid.json()["error"]["code"] == "gp_surface_view_invalid"

        def forbidden(*args, **kwargs):
            raise AssertionError("export cannot predict or refit")

        monkeypatch.setattr(
            "app.services.gaussian_process_predictions.predict_from_gaussian_process_state",
            forbidden,
        )
        monkeypatch.setattr("app.services.dataset_rows.get_dataset_rows_context", forbidden)
        capability = client.post(
            "/api/v1/reports/capability", json={"source": source, "locale": "en"}
        )
        assert capability.status_code == 200, capability.text
        assert capability.json()["report_level"] == "full"
        exported = client.post(
            "/api/v1/reports",
            json={
                "source": source,
                "locale": "en",
                "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
            },
        )
        assert exported.status_code == 201, exported.text
        artifact = exported.json()
        downloaded = client.post(
            f"/api/v1/reports/{artifact['export_id']}/download",
            json={
                "source": source,
                "expected_sha256": artifact["sha256"],
            },
        )
        assert downloaded.status_code == 200, downloaded.text
        assert hashlib.sha256(downloaded.content).hexdigest() == artifact["sha256"]
        surface = downloaded.text.split('data-report-section="surface_view"', 1)[1]
        assert "Latent Response SD" in surface and "<svg" in surface
        assert 'data-x="1"' in surface or 'data-x="1.0"' in surface
        assert client.get(f"/api/v1/reports/{artifact['export_id']}").status_code == 200
        assert (tmp_path / owner.result_path).read_bytes() == original
