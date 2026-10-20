import hashlib
import json
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_response_optimizer_api import _create_source_analysis

from app.api.v1.schemas.doe import DoeResponseSurfaceAnalysisResponse, ResponseSurfaceDesignResponse
from app.api.v1.schemas.reports import DoeAnalysisReportSource
from app.api.v1.schemas.rsm_plots import RsmPlotSettings
from app.core.config import Settings
from app.main import create_app
from app.services.report_source_contract import canonical_report_source_json
from app.services.rsm_plot_builder import build_rsm_plot_bundle
from app.storage.metadata import get_experiment_design_analysis_record


def test_saved_plot_view_exact_source_report_and_no_refit(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design, analysis = _create_source_analysis(client)
        design_id, analysis_id = design["design_id"], analysis["analysis_id"]
        route = f"/api/v1/doe-designs/{design_id}/response-surface-analyses/{analysis_id}"
        original = get_experiment_design_analysis_record(tmp_path, analysis_id)
        assert analysis["result"]["plot_bundle"]["geometry"]["algorithm"] == "contourpy.serial"

        def forbidden(*args, **kwargs):
            pytest.fail("plot view/report must not fit, select, or reload dataset rows")

        monkeypatch.setattr(
            "app.services.doe_response_surface_analysis.calculate_response_surface_analysis",
            forbidden,
        )
        monkeypatch.setattr(
            "app.statistics.term_block_model_selection.select_term_blocks", forbidden
        )
        source = client.get(route + "/plot-source").json()
        request = {
            **source,
            "settings": {
                "x_factor_id": "factor_2",
                "y_factor_id": "factor_1",
                "held_actual_values": {},
                "axis_scale": "actual",
                "grid_size": 11,
                "contour_levels": {"count": 4},
                "design_points": True,
            },
        }
        response = client.post(route + "/plot-view", json=request)
        assert response.status_code == 200, response.text
        view = response.json()
        assert view["bundle"]["x_axis"]["name"] == design["factors"][1]["name"]
        assert len(view["bundle"]["points"]) == 121
        assert len(view["bundle"]["geometry"]["levels"]) == 4
        saved_response = client.post(
            route + "/plot-views", json={**request, "expected_view_sha256": view["view_sha256"]}
        )
        assert saved_response.status_code == 201, saved_response.text
        saved = saved_response.json()
        assert client.get(route + "/plot-views/" + saved["asset_id"]).json() == saved
        with monkeypatch.context() as listing:
            listing.setattr("app.services.rsm_plot_views.read_rsm_plot_view", forbidden)
            assert client.get(route + "/plot-views").json() == [
                {key: saved[key] for key in ("asset_id", "sha256", "created_at")}
            ]
        wrong = client.post(
            route + "/plot-view", json={**request, "expected_result_sha256": "0" * 64}
        )
        assert wrong.status_code == 409
        wrong_view = client.post(
            route + "/plot-views", json={**request, "expected_view_sha256": "0" * 64}
        )
        assert wrong_view.status_code == 409
        assert len(client.get(route + "/plot-views").json()) == 1
        sources = client.get("/api/v1/reports/sources", params={"source_kind": "doe_analysis"})
        ref = next(
            item["source"] for item in sources.json()["items"] if item["source"].get("plot_view")
        )
        assert ref["plot_view"]["plot_view_id"] == saved["asset_id"]

        # Once stored, a report must use those exact bytes without even evaluating
        # a new prediction grid or generating new geometry.
        monkeypatch.setattr("app.services.rsm_plot_views.build_rsm_plot_bundle", forbidden)
        monkeypatch.setattr("app.services.rsm_plot_builder.evaluate_rsm_basis", forbidden)
        monkeypatch.setattr("app.services.rsm_plot_builder.contour_geometry", forbidden)
        query = {"source": ref, "locale": "en"}
        capability = client.post("/api/v1/reports/capability", json=query)
        assert capability.status_code == 200, capability.text
        report = client.post(
            "/api/v1/reports",
            json={
                **query,
                "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
            },
        )
        assert report.status_code == 201, report.text
        export_id = report.json()["export_id"]
        downloaded = client.post(
            f"/api/v1/reports/{export_id}/download",
            json={
                "source": ref,
                "expected_sha256": report.json()["sha256"],
            },
        )
        assert downloaded.status_code == 200, downloaded.text
        html = downloaded.text
        assert 'data-rsm-contour="stored-geometry"' in html
        assert "Selected saved custom view" in html
        assert 'fill-rule="evenodd"' in html
        assert "<script" not in html
        assert hashlib.sha256(downloaded.content).hexdigest() == report.json()["sha256"]
        assert get_experiment_design_analysis_record(tmp_path, analysis_id) == original


def test_plot_settings_holds_actual_coded_prediction_equality(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        design_json, analysis_json = _create_source_analysis(client)
        design = ResponseSurfaceDesignResponse.model_validate(design_json)
        analysis = DoeResponseSurfaceAnalysisResponse.model_validate(analysis_json)
        basis = analysis.result.final_basis
        assert basis is not None
        actual = build_rsm_plot_bundle(
            design,
            basis,
            RsmPlotSettings(x_factor_id="factor_1", y_factor_id="factor_2"),
            response_name="Y",
            response_unit="g",
        )
        coded = build_rsm_plot_bundle(
            design,
            basis,
            RsmPlotSettings(x_factor_id="factor_1", y_factor_id="factor_2", axis_scale="coded"),
            response_name="Y",
            response_unit="g",
        )
        assert [point.predicted for point in actual.points] == [
            point.predicted for point in coded.points
        ]
        for point, coded_point in zip(actual.points, coded.points, strict=True):
            coordinates = [
                (value - basis.coding[factor.name].center) / basis.coding[factor.name].scale
                for factor, value in zip(design.factors, [point.x, point.y], strict=True)
            ]
            # Literal exponent evaluation independent of production basis helper.
            expected = 0.0
            for powers, coefficient in zip(basis.powers, basis.coefficients, strict=True):
                term = coefficient
                for value, power in zip(coordinates, powers, strict=True):
                    term *= value**power
                expected += term
            assert point.predicted == pytest.approx(expected, abs=1e-11)
            assert coded_point.x == pytest.approx(coordinates[0], abs=1e-12)
            assert coded_point.y == pytest.approx(coordinates[1], abs=1e-12)
        with pytest.raises(ValueError, match="hold_values_invalid"):
            build_rsm_plot_bundle(
                design,
                basis,
                RsmPlotSettings(
                    x_factor_id="factor_1",
                    y_factor_id="factor_2",
                    held_actual_values={"factor_1": 0},
                ),
                response_name="Y",
                response_unit=None,
            )


def test_legacy_report_source_hash_unchanged_when_optional_plot_absent():
    legacy = {
        "kind": "doe_analysis",
        "family": "response_surface",
        "design_id": str(UUID(int=1)),
        "design_version_id": str(UUID(int=2)),
        "design_sha256": "a" * 64,
        "analysis_id": str(UUID(int=3)),
        "expected_source_sha256": "b" * 64,
        "response_revision": {
            "response_revision_id": str(UUID(int=4)),
            "response_revision_sha256": "c" * 64,
        },
    }
    expected = json.dumps(legacy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert canonical_report_source_json(DoeAnalysisReportSource.model_validate(legacy)) == expected
