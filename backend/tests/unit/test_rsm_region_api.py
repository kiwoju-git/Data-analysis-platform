import hashlib
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.v1.schemas.doe import DoeResponseSurfaceAnalysisResponse
from app.core.config import Settings
from app.main import create_app
from app.services.response_optimizer import _source_model_eligibility_issues
from app.storage.metadata import get_experiment_design_analysis_record


def test_ccc_axial_plot_optimizer_and_exact_restore(tmp_path, monkeypatch):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        created = client.post(
            "/api/v1/doe-designs/response-surface",
            json={
                "name": "Synthetic CCC region",
                "factors": [{"name": f"x{i}", "low": 10, "high": 20} for i in range(1, 5)],
                "alpha_mode": "rotatable",
                "ccd_type": "circumscribed",
                "center_points": 7,
                "randomize": False,
                "randomization_seed": 42,
                "axial_points_confirmed": True,
            },
        )
        assert created.status_code == 201, created.text
        design = created.json()
        assert len(design["runs"]) == 31
        original_design_hash = design["design_sha256"]
        values, center_index = [], 0
        for run in design["runs"]:
            actual = run["factor_levels"]
            value = (
                100
                - (actual["x1"] - 23) ** 2
                - sum((actual[f"x{i}"] - 15) ** 2 for i in range(2, 5))
            )
            if run["point_type"] == "center":
                value += (center_index - 3) * 0.1
                center_index += 1
            values.append({"run_order": run["run_order"], "value": value})
        root = f"/api/v1/doe-designs/response-surface/{design['design_id']}"
        stored = client.put(
            root + "/responses",
            json={"response_name": "Synthetic response", "unit": "g", "values": values},
        )
        assert stored.status_code == 200, stored.text
        fitted = client.post(root + "/analyses", json={"response_name": "Synthetic response"})
        assert fitted.status_code == 201, fitted.text
        analysis = fitted.json()
        source_record = get_experiment_design_analysis_record(tmp_path, analysis["analysis_id"])
        assert source_record is not None
        assert analysis["result"]["contour"]["coded_range"] == [-2, 2]
        assert analysis["result"]["plot_bundle"]["x_axis"]["minimum"] == 5
        assert analysis["result"]["plot_bundle"]["x_axis"]["maximum"] == 25
        issues = _source_model_eligibility_issues(
            DoeResponseSurfaceAnalysisResponse.model_validate(analysis), 0.95
        )
        assert not [issue for issue in issues if issue.severity == "blocking"]
        acknowledgments = [
            issue.code for issue in issues if issue.severity == "acknowledgment_required"
        ]
        optimizations = []
        for mode, expected_x in (("axial_bounds", 23), ("factorial_cube", 20)):
            response = client.post(
                root + "/optimizations",
                json={
                    "region_mode": mode,
                    "objectives": [
                        {
                            "source_analysis_id": analysis["analysis_id"],
                            "goal": "maximize",
                            "lower": -500,
                            "target": 101,
                        }
                    ],
                    "acknowledged_source_warning_codes": acknowledgments,
                },
            )
            assert response.status_code == 201, response.text
            optimization = response.json()
            optimizations.append(optimization)
            point = optimization["result"]["recommendation"]["actual_coordinates"]
            assert point["x1"] == pytest.approx(expected_x, abs=2e-4)
            assert optimization["result"]["factor_region"]["resolved_bounds"][0]["scale"] == 5
            assert (
                client.get(root + "/optimizations/" + optimization["optimization_id"]).json()
                == optimization
            )
        route = (
            f"/api/v1/doe-designs/{design['design_id']}/response-surface-analyses/"
            f"{analysis['analysis_id']}"
        )
        source = client.get(route + "/plot-source").json()
        request = {
            **source,
            "settings": {
                "x_factor_id": "factor_1",
                "y_factor_id": "factor_2",
                "grid_size": 11,
                "region_mode": "axial_bounds",
                "held_actual_values": {"factor_3": 23, "factor_4": 15},
            },
        }
        plot = client.post(route + "/plot-view", json=request)
        assert plot.status_code == 200, plot.text
        view = plot.json()
        assert view["schema_version"] == 2
        assert view["bundle"]["x_axis"]["minimum"] == 5
        assert any(point["outside_design_hull"] for point in view["bundle"]["points"])
        for point in view["bundle"]["points"]:
            expected = 100 - (point["x"] - 23) ** 2 - (point["y"] - 15) ** 2 - (23 - 15) ** 2
            assert point["predicted"] == pytest.approx(expected, abs=1e-9)
        save = client.post(
            route + "/plot-views", json={**request, "expected_view_sha256": view["view_sha256"]}
        )
        assert save.status_code == 201, save.text
        saved = save.json()
        assert client.get(route + "/plot-views/" + saved["asset_id"]).json() == saved

        def forbidden(*args, **kwargs):
            pytest.fail("report export must read stored geometry, never fit or rebuild a grid")

        with monkeypatch.context() as export:
            export.setattr("app.services.rsm_plot_views.build_rsm_plot_bundle", forbidden)
            export.setattr(
                "app.services.doe_response_surface_analysis.calculate_response_surface_analysis",
                forbidden,
            )
            sources = client.get(
                "/api/v1/reports/sources", params={"source_kind": "doe_analysis"}
            ).json()
            ref = next(
                item["source"]
                for item in sources["items"]
                if (item["source"].get("plot_view") or {}).get("plot_view_id") == saved["asset_id"]
            )
            query = {"source": ref, "locale": "en"}
            capability = client.post("/api/v1/reports/capability", json=query).json()
            report = client.post(
                "/api/v1/reports",
                json={**query, "expected_source_ref_sha256": capability["source_ref_sha256"]},
            )
            assert report.status_code == 201, report.text
            artifact = report.json()
            html = client.post(
                f"/api/v1/reports/{artifact['export_id']}/download",
                json={"source": ref, "expected_sha256": artifact["sha256"]},
            )
            assert html.status_code == 200
            assert "Region policy: axial_bounds" in html.text
            assert "Axial lower" in html.text and "Applied upper" in html.text
            assert hashlib.sha256(html.content).hexdigest() == artifact["sha256"]
        request["settings"]["region_mode"] = "factorial_cube"
        assert client.post(route + "/plot-view", json=request).status_code == 409
        assert client.get(root).json()["design_sha256"] == original_design_hash
        assert (
            get_experiment_design_analysis_record(tmp_path, analysis["analysis_id"])
            == source_record
        )
        assert (
            hashlib.sha256(source_record.result_json.encode()).hexdigest()
            == source_record.result_sha256
        )
        assert UUID(saved["asset_id"])
