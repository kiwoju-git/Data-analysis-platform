"""Synthetic legacy-shaped artifacts verify read-only version dispatch, not old fit parity."""

import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services import doe_response_surface_analysis as service
from app.services.dedicated_report_renderers import render_doe_analysis_body
from app.storage.metadata import metadata_db_path


@pytest.mark.parametrize(
    "version,envelope,result_schema,config_schema",
    [
        ("0.3.1", 2, 1, 2),
        ("0.4.0", 3, 2, 3),
    ],
)
def test_old_rsm_result_read_preserves_original_bytes(
    tmp_path,
    monkeypatch,
    version,
    envelope,
    result_schema,
    config_schema,
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post(
            "/api/v1/doe-designs/response-surface",
            json={
                "name": "Synthetic legacy read fixture",
                "factors": [
                    {"name": "A", "low": 0, "high": 1},
                    {"name": "B", "low": 0, "high": 1},
                ],
                "center_points": 5,
                "randomize": False,
                "randomization_seed": 17,
            },
        )
        assert created.status_code == 201, created.text
        design = created.json()
        base = f"/api/v1/doe-designs/response-surface/{design['design_id']}"
        values = [
            {
                "run_order": row["run_order"],
                "value": 10
                + row["coded_levels"]["A"]
                - 2 * row["coded_levels"]["B"]
                + (row["run_order"] % 3) * 0.1,
            }
            for row in design["runs"]
        ]
        assert (
            client.put(
                base + "/responses", json={"response_name": "Y", "values": values}
            ).status_code
            == 200
        )
        calculate = service.calculate_response_surface_analysis
        default_view = service.default_rsm_plot_settings
        overview = service.default_rsm_overview_settings

        def legacy_payload(*args, **kwargs):
            payload = calculate(*args, **kwargs)
            payload["schema_version"] = result_schema
            payload.pop("residual_plots")
            payload.pop("observed_response_summary")
            payload["contour"].pop("region_mode", None)
            payload["contour"].pop("region_policy_version", None)
            if result_schema == 1:
                for key in (
                    "final_basis",
                    "model_selection",
                    "term_preset",
                    "press",
                    "predicted_r_squared",
                ):
                    payload.pop(key, None)
                payload["coding"].pop("factors", None)
                payload["method"] = "full_quadratic_ordinary_least_squares"
            return payload

        with monkeypatch.context() as patch:
            patch.setitem(service.METHOD_VERSIONS, "doe.response_surface", version)
            patch.setattr(service, "DOE_RESPONSE_SURFACE_ANALYSIS_SCHEMA_VERSION", envelope)
            patch.setattr(service, "DOE_RESPONSE_SURFACE_CONFIG_SCHEMA_VERSION", config_schema)
            patch.setattr(service, "calculate_response_surface_analysis", legacy_payload)
            patch.setattr(
                service,
                "default_rsm_plot_settings",
                lambda design: default_view(design, legacy=True),
            )
            patch.setattr(
                service,
                "default_rsm_overview_settings",
                lambda design: overview(design, legacy=True),
            )
            response = client.post(base + "/analyses", json={"response_name": "Y"})
        assert response.status_code == 201, response.text
        analysis_id = response.json()["analysis_id"]
        # The old artifact lacks new optional fields entirely, rather than carrying
        # current-reader null defaults. This writes only the isolated synthetic fixture.
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            serialized = db.execute(
                "SELECT result_json FROM experiment_design_analyses WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone()[0]
            payload = json.loads(serialized)
            payload["result"].pop("residual_plots", None)
            payload["result"].pop("observed_response_summary", None)
            payload["result"]["contour"].pop("region_mode", None)
            payload["result"]["contour"].pop("region_policy_version", None)
            serialized = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            db.execute(
                "UPDATE experiment_design_analyses SET result_json=?,result_sha256=? "
                "WHERE analysis_id=?",
                (serialized, hashlib.sha256(serialized.encode()).hexdigest(), analysis_id),
            )
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            before = db.execute(
                "SELECT result_json, result_sha256, config_json FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone()
        assert hashlib.sha256(before[0].encode()).hexdigest() == before[1]
        restored = client.get(base + "/analyses/" + analysis_id)
        assert restored.status_code == 200, restored.text
        assert restored.json()["method_version"] == version
        assert restored.json()["result"]["residual_plots"] is None
        assert restored.json()["result"]["observed_response_summary"] is None
        report = render_doe_analysis_body(restored.json(), "response_surface", "en")
        assert (
            next(s for s in report.sections if s.section_id == "residual_plots").status == "missing"
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            after = db.execute(
                "SELECT result_json, result_sha256, config_json FROM experiment_design_analyses "
                "WHERE analysis_id=?",
                (analysis_id,),
            ).fetchone()
        assert after == before
