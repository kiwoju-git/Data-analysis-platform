"""Actual synthetic RSM assets: exact ownership, integrity, and deletion races."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_response_optimizer_api import _create_source_analysis

from app.api.v1.schemas.rsm_plots import RsmContourGeometry, RsmPlotBundle
from app.core.config import Settings
from app.main import create_app
from app.services.rsm_plot_report import rsm_plot_report
from app.statistics.rsm_plot_geometry import (
    contour_geometry,
    design_hull_equations,
    hull_slice_polygon,
    outside_design_hull,
)
from app.storage import factorial_analysis_assets as storage
from app.storage.metadata import metadata_db_path


@pytest.fixture
def saved_view(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis = _create_source_analysis(client)
        route = (
            f"/api/v1/doe-designs/{design['design_id']}"
            f"/response-surface-analyses/{analysis['analysis_id']}"
        )
        source = client.get(route + "/plot-source")
        assert source.status_code == 200, source.text
        request = {
            **source.json(),
            "settings": {
                "x_factor_id": "factor_1",
                "y_factor_id": "factor_2",
                "grid_size": 11,
            },
        }
        view = client.post(route + "/plot-view", json=request)
        assert view.status_code == 200, view.text
        save = {**request, "expected_view_sha256": view.json()["view_sha256"]}
        response = client.post(route + "/plot-views", json=save)
        assert response.status_code == 201, response.text
        yield client, tmp_path, design, analysis, route, save, response.json()


def rewrite_envelope(root, saved, field, value) -> None:
    # Only corrupt this test's newly created asset. Keep its bytes/checksum internally
    # consistent to exercise cross-record ownership, not merely checksum rejection.
    payload = dict(saved["view"], **{field: value})
    content = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute(
            "UPDATE experiment_design_analysis_assets SET content=?,sha256=?,size_bytes=? "
            "WHERE asset_id=?",
            (content, hashlib.sha256(content).hexdigest(), len(content), saved["asset_id"]),
        )


def report_query(client, asset_id: str) -> dict:
    response = client.get("/api/v1/reports/sources", params={"source_kind": "doe_analysis"})
    assert response.status_code == 200, response.text
    source = next(
        item["source"]
        for item in response.json()["items"]
        if (item["source"].get("plot_view") or {}).get("plot_view_id") == asset_id
    )
    return {"source": source, "locale": "en"}


@pytest.mark.parametrize("field", ["design_version_id", "design_sha256"])
def test_consistent_asset_checksum_cannot_substitute_design_identity(saved_view, field) -> None:
    client, root, _, _, route, _, saved = saved_view
    value = str(uuid4()) if field == "design_version_id" else "0" * 64
    rewrite_envelope(root, saved, field, value)
    response = client.get(route + "/plot-views/" + saved["asset_id"])
    assert (
        response.status_code == 409
    ), f"Saved view accepted mismatched {field} despite its original analysis owner"
    assert response.json()["error"]["code"] == "doe_rsm_plot_source_changed"


def test_report_capability_rejects_view_bound_to_different_design_revision(saved_view) -> None:
    client, root, _, _, _, _, saved = saved_view
    rewrite_envelope(root, saved, "design_version_id", str(uuid4()))
    query = report_query(client, saved["asset_id"])
    response = client.post("/api/v1/reports/capability", json=query)
    assert response.status_code == 409, "Report capability accepted a mismatched saved design"


@pytest.mark.parametrize(
    "field", ["analysis_id", "design_id", "response_revision_id", "expected_result_sha256"]
)
def test_existing_source_fields_reject_checksum_consistent_substitution(saved_view, field) -> None:
    client, root, _, _, route, _, saved = saved_view
    value = "0" * 64 if field.endswith("sha256") else str(uuid4())
    rewrite_envelope(root, saved, field, value)
    response = client.get(route + "/plot-views/" + saved["asset_id"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "doe_rsm_plot_source_changed"


def test_saved_geometry_is_not_accepted_from_client(saved_view) -> None:
    client, root, _, analysis, route, save, _ = saved_view
    response = client.post(route + "/plot-views", json={**save, "bundle": {"points": []}})
    assert response.status_code == 422
    assert len(storage.list_assets(root, analysis["analysis_id"], "plot_view")) == 1


def test_asset_is_not_readable_under_another_analysis_owner(saved_view) -> None:
    client, _, design, _, _, _, saved = saved_view
    response = client.post(
        f"/api/v1/doe-designs/response-surface/{design['design_id']}/analyses",
        json={"response_name": "Yield"},
    )
    assert response.status_code == 201, response.text
    route = (
        f"/api/v1/doe-designs/{design['design_id']}/response-surface-analyses/"
        f"{response.json()['analysis_id']}/plot-views/{saved['asset_id']}"
    )
    response = client.get(route)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "doe_rsm_plot_view_not_found"


def test_save_rejects_source_deleted_after_view_evaluation(saved_view, monkeypatch) -> None:
    client, root, _, analysis, route, save, _ = saved_view
    original_insert = storage.insert_asset
    called = []

    def delete_before_insert(workspace, record, content, **kwargs):
        snapshot = storage.analysis_deletion_snapshot(workspace, analysis["analysis_id"])
        assert snapshot is not None
        storage.delete_analysis(workspace, analysis["analysis_id"], snapshot[0])
        called.append(record.asset_id)
        return original_insert(workspace, record, content, **kwargs)

    monkeypatch.setattr(storage, "insert_asset", delete_before_insert)
    response = client.post(route + "/plot-views", json=save)
    assert len(called) == 1
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "doe_factorial_prediction_source_changed"
    assert storage.analysis_deletion_snapshot(root, analysis["analysis_id"]) is None
    assert storage.list_assets(root, analysis["analysis_id"]) == []


def test_report_rejects_plot_deleted_between_read_and_insert(saved_view, monkeypatch) -> None:
    client, root, _, analysis, _, _, saved = saved_view
    query = report_query(client, saved["asset_id"])
    capability = client.post("/api/v1/reports/capability", json=query)
    assert capability.status_code == 200, capability.text
    original_insert = storage.insert_asset
    called = []

    def delete_before_insert(workspace, record, content, **kwargs):
        storage.delete_asset(workspace, analysis["analysis_id"], saved["asset_id"], saved["sha256"])
        called.append(kwargs)
        return original_insert(workspace, record, content, **kwargs)

    monkeypatch.setattr("app.services.report_exports.insert_asset", delete_before_insert)
    response = client.post(
        "/api/v1/reports",
        json={**query, "expected_source_ref_sha256": capability.json()["source_ref_sha256"]},
    )
    assert called == [
        {"dependency_asset": (saved["asset_id"], saved["sha256"]), "dependency_kind": "plot_view"}
    ]
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "stored_report_source_changed"
    assert storage.list_assets(root, analysis["analysis_id"], "html_report") == []


def test_historical_report_survives_view_delete_but_new_capability_does_not(saved_view) -> None:
    client, root, _, analysis, route, _, saved = saved_view
    query = report_query(client, saved["asset_id"])
    capability = client.post("/api/v1/reports/capability", json=query)
    assert capability.status_code == 200, capability.text
    response = client.post(
        "/api/v1/reports",
        json={**query, "expected_source_ref_sha256": capability.json()["source_ref_sha256"]},
    )
    assert response.status_code == 201, response.text
    report = response.json()
    download = {"source": query["source"], "expected_sha256": report["sha256"]}
    before = client.post(f"/api/v1/reports/{report['export_id']}/download", json=download)
    assert before.status_code == 200, before.text
    deleted = client.delete(
        route + "/plot-views/" + saved["asset_id"], params={"expected_sha256": saved["sha256"]}
    )
    assert deleted.status_code == 204, deleted.text
    after = client.post(f"/api/v1/reports/{report['export_id']}/download", json=download)
    assert after.status_code == 200, after.text
    assert after.content == before.content
    assert hashlib.sha256(after.content).hexdigest() == report["sha256"]
    assert client.post("/api/v1/reports/capability", json=query).status_code == 409
    snapshot = storage.analysis_deletion_snapshot(root, analysis["analysis_id"])
    assert snapshot is not None and snapshot[2:] == (1, 0)
    storage.delete_analysis(root, analysis["analysis_id"], snapshot[0])
    assert storage.list_assets(root, analysis["analysis_id"]) == []


def test_filled_band_holes_reach_html_as_separate_evenodd_subpaths(saved_view) -> None:
    _, _, _, _, _, _, saved = saved_view
    coordinates = np.linspace(-1, 1, 51)
    geometry = contour_geometry(
        coordinates,
        coordinates,
        coordinates[None, :] ** 2 + coordinates[:, None] ** 2,
        thresholds=[0.2, 0.5],
    )
    bundle = RsmPlotBundle.model_validate(saved["view"]["bundle"])
    bundle.geometry = RsmContourGeometry.model_validate(geometry)
    assert len(geometry["bands"][1]["polygons"]) == 1
    assert len(geometry["bands"][1]["polygons"][0]["rings"]) == 2
    html = rsm_plot_report(bundle, "en")
    svg_text = html[html.index("<svg ") : html.index("</svg>") + len("</svg>")]
    svg = ET.fromstring(svg_text)
    band = svg.find(".//path[@data-band='1']")
    assert band is not None
    assert band.attrib["fill-rule"] == "evenodd"
    assert band.attrib["d"].count("M") == band.attrib["d"].count("Z") == 2


def test_five_dimensional_hull_holds_all_non_displayed_coordinates() -> None:
    # The full hull is sum(abs(x_i)) <= 1. With held sum=.6 the display
    # diamond has radius .4; the 2D projection alone would wrongly use radius 1.
    equations = design_hull_equations(np.concatenate([np.eye(5), -np.eye(5)]))
    held = np.array([0.2, 0.0, 0.1, 0.0, 0.3])
    polygon = hull_slice_polygon(equations, held, 1, 3, (-1, 1), (-1, 1))
    assert len(polygon) == 4
    assert all(abs(x) + abs(y) == pytest.approx(0.4, abs=1e-12) for x, y in polygon)
    rows = np.tile(held, (3, 1))
    rows[:, 1] = [0.4, 0.41, 0.1]
    rows[:, 3] = [0.0, 0.0, 0.1]
    assert outside_design_hull(rows, equations).tolist() == [False, True, False]
    held[0] = 1.1
    assert hull_slice_polygon(equations, held, 1, 3, (-1, 1), (-1, 1)) == []


def test_curve_report_preserves_stored_hull_flags_without_claiming_hatching(saved_view) -> None:
    _, _, _, analysis, _, _, _ = saved_view
    bundle = RsmPlotBundle.model_validate(analysis["result"]["plot_overview"][0])
    assert bundle.geometry is None
    bundle.curves[0].points[0].outside_design_hull = True
    bundle.curves[0].points[1].outside_design_hull = False
    html = rsm_plot_report(bundle, "en")
    assert "Hatching" not in html
    assert "not observed data means" in html
    root = ET.fromstring("<div>" + html + "</div>")
    table = root.findall(".//table")[-1]
    assert table.findtext("./thead/tr/th[4]") == "Outside design hull"
    rows = table.findall("./tbody/tr")
    assert len(rows) == sum(len(curve.points) for curve in bundle.curves)
    assert rows[0].findtext("./td[4]") == "True"
    assert rows[1].findtext("./td[4]") == "False"
