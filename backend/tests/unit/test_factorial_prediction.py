import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_factorial_model_selection_api import create_full

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path


def _analyze(client, *, general=False, centers=0, selection="backward_elimination", replicates=2):
    design, base = create_full(client, general=general, centers=centers, replicates=replicates)
    response = client.post(
        base + "/analyses",
        json={
            "response_name": "Yield",
            "max_interaction_order": 2 if general else 3,
            "model_selection": {"method": selection},
        },
    )
    assert response.status_code == 201, response.text
    analysis = response.json()
    return (
        design,
        analysis,
        f"/api/v1/doe-designs/{design['design_id']}/analyses/{analysis['analysis_id']}",
    )


def test_prediction_matches_independent_statsmodels_intervals_and_is_immutable(tmp_path):
    reference = json.loads(
        (
            Path(__file__).parents[1] / "reference/fixtures/factorial_selection_statsmodels.json"
        ).read_text(encoding="utf-8")
    )["cases"][0]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis, base = _analyze(client, replicates=1)
        body = {"rows": [{"row_id": "one", "factor_settings": {"A": 0.2, "B": -0.4, "C": 0.7}}]}
        preflight = client.post(base + "/prediction-preflight", json=body)
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["valid"]
        saved = client.post(
            base + "/predictions",
            json={**body, "expected_preflight_sha256": preflight.json()["preflight_sha256"]},
        )
        assert saved.status_code == 201, saved.text
        row = saved.json()["rows"][0]
        for actual, expected in [
            (row["fitted_mean"], "mean"),
            (row["standard_error_fit"], "mean_se"),
            (row["mean_confidence_interval"]["lower"], "mean_ci_lower"),
            (row["individual_prediction_interval"]["upper"], "obs_ci_upper"),
        ]:
            assert actual == pytest.approx(reference["prediction"][expected], rel=1e-8, abs=1e-9)
        restored = client.get(base + f"/predictions/{saved.json()['prediction_id']}")
        assert restored.json() == saved.json()
        assert saved.json()["response_revision_sha256"] == analysis["response_revision_sha256"]
        assert (
            client.get(f"/api/v1/doe-designs/{design['design_id']}").json()["design_sha256"]
            == design["design_sha256"]
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE experiment_design_analysis_assets SET content=? WHERE asset_id=?",
                (b"x" * len(restored.content), saved.json()["prediction_id"]),
            )
        corrupt = client.get(base + f"/predictions/{saved.json()['prediction_id']}")
        assert corrupt.status_code == 409
        assert corrupt.json()["error"]["code"] == "doe_analysis_asset_checksum_mismatch"


def test_preflight_atomic_rows_domain_and_stale_request(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, _, base = _analyze(client)
        good = {"row_id": "good", "factor_settings": {"A": 0, "B": 0, "C": 0}}
        bad = {"row_id": "bad", "factor_settings": {"A": 2, "B": 0, "C": 0}}
        body = {"rows": [good, bad]}
        check = client.post(base + "/prediction-preflight", json=body).json()
        assert not check["valid"]
        assert check["issues"][0]["code"] == "doe_factorial_prediction_outside_domain"
        invalid = client.post(
            base + "/predictions",
            json={**body, "expected_preflight_sha256": check["preflight_sha256"]},
        )
        assert invalid.status_code == 409
        valid = client.post(base + "/prediction-preflight", json={"rows": [good]}).json()
        good["factor_settings"]["A"] = 0.5
        stale = client.post(
            base + "/predictions",
            json={"rows": [good], "expected_preflight_sha256": valid["preflight_sha256"]},
        )
        assert stale.status_code == 409
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM experiment_design_analysis_assets"
                ).fetchone()[0]
                == 0
            )


def test_curvature_only_accepts_corners_or_observed_center_settings(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, _, base = _analyze(client, centers=2, selection="none")
        rows = [
            {"row_id": str(index), "factor_settings": dict(zip("ABC", values, strict=True))}
            for index, values in enumerate([(1, -1, 1), (0, 0, 0), (0, 1, 1), (0.2, 0.2, 0.2)])
        ]
        result = client.post(base + "/prediction-preflight", json={"rows": rows}).json()
        assert [issue["row_id"] for issue in result["issues"]] == ["2", "3"]
        assert all(
            issue["code"] == "doe_factorial_prediction_center_curvature_domain_invalid"
            for issue in result["issues"]
        )


def test_general_factorial_uses_known_levels_without_interpolation(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, _, base = _analyze(client, general=True)
        body = {"rows": [{"row_id": "valid", "factor_settings": {"A": 2, "B": "High"}}]}
        check = client.post(base + "/prediction-preflight", json=body).json()
        assert check["valid"]
        result = client.post(
            base + "/predictions",
            json={**body, "expected_preflight_sha256": check["preflight_sha256"]},
        )
        assert result.status_code == 201, result.text
        body["rows"][0]["factor_settings"]["A"] = 2.5
        assert not client.post(base + "/prediction-preflight", json=body).json()["valid"]


def test_saturated_none_allows_point_prediction_but_no_intervals(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, _, base = _analyze(client, selection="none", replicates=1)
        body = {"rows": [{"row_id": "one", "factor_settings": {"A": 1, "B": -1, "C": 1}}]}
        check = client.post(base + "/prediction-preflight", json=body).json()
        result = client.post(
            base + "/predictions",
            json={**body, "expected_preflight_sha256": check["preflight_sha256"]},
        )
        assert result.status_code == 201, result.text
        row = result.json()["rows"][0]
        assert row["mean_confidence_interval"] is None
        assert row["individual_prediction_interval"] is None
        assert (
            row["interval_unavailability_reason"] == "doe_factorial_prediction_variance_unavailable"
        )
