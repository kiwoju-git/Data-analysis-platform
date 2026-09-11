import hashlib
import sqlite3

import pytest
from fastapi.testclient import TestClient
from test_factorial_prediction import _analyze

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import initialize_metadata_store, metadata_db_path


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_managed_report_contains_saved_analysis_and_svg_without_recalculation(
    tmp_path, monkeypatch, locale
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis, base = _analyze(client, replicates=1)

        def forbidden(*args, **kwargs):
            raise AssertionError("Reports must not refit a model")

        monkeypatch.setattr(
            "app.services.doe_factorial_analysis.calculate_factorial_analysis", forbidden
        )
        body = {
            "rows": [
                {
                    "row_id": "<script>alert(1)</script>",
                    "factor_settings": {"A": 0.2, "B": -0.4, "C": 0.7},
                }
            ]
        }
        preflight = client.post(base + "/prediction-preflight", json=body).json()
        prediction = client.post(
            base + "/predictions",
            json={
                **body,
                "expected_preflight_sha256": preflight["preflight_sha256"],
            },
        ).json()
        created = client.post(base + "/exports/html", json={"locale": locale})
        assert created.status_code == 201, created.text
        artifact = created.json()
        downloaded = client.get(base + f"/exports/{artifact['asset_id']}/download")
        assert downloaded.status_code == 200
        content = downloaded.content
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]
        assert len(content) == artifact["size_bytes"]
        html = content.decode("utf-8")
        assert f'lang="{locale}"' in html
        assert "<script" not in html.lower()
        assert "<iframe" not in html.lower()
        assert "<link" not in html.lower()
        assert " src=" not in html.lower()
        assert html.count("<svg") >= 12
        assert html.count('class="reference-line"') == 6
        assert str(analysis["analysis_id"]) in html
        assert "PRESS" in html and "VIF" in html
        assert "Initial pooling" in html if locale == "en" else "초기 오차 풀링" in html
        assert analysis["result"]["final_model"]["equation"]["display_equation"] in html
        assert prediction["prediction_id"] in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        assert "Latest saved prediction" in html if locale == "en" else "최근 저장 예측" in html
        listing = client.get(base + "/exports").json()
        assert listing["items"] == [artifact]
        assets = client.get("/api/v1/assets").json()["items"]
        assert any(
            item["asset_id"] == artifact["asset_id"] and item["asset_type"] == "doe_analysis_report"
            for item in assets
        )
        assert any(
            item["asset_id"] == analysis["analysis_id"] and item["asset_type"] == "doe_analysis"
            for item in assets
        )
        legacy = client.get(f"/api/v1/doe-designs/{design['design_id']}/report.html")
        assert legacy.status_code == 200
        assert "<table" in legacy.text


def test_report_deletion_analysis_cascade_and_stale_deletion_preflight(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, analysis, base = _analyze(client)
        first = client.post(base + "/exports/html", json={"locale": "en"}).json()
        snapshot = client.get(base + "/deletion-preflight").json()
        assert snapshot["report_count"] == 1
        second = client.post(base + "/exports/html", json={"locale": "ko"}).json()
        stale = client.request(
            "DELETE",
            base,
            json={
                "confirmation_analysis_id": analysis["analysis_id"],
                "expected_deletion_manifest_sha256": snapshot["deletion_manifest_sha256"],
            },
        )
        assert stale.status_code == 409
        preflight = client.get(base + f"/exports/{first['asset_id']}/deletion-preflight").json()
        deleted = client.request(
            "DELETE",
            base + f"/exports/{first['asset_id']}",
            json={
                "confirmation_asset_id": first["asset_id"],
                "expected_sha256": preflight["sha256"],
            },
        )
        assert deleted.status_code == 200
        snapshot = client.get(base + "/deletion-preflight").json()
        deleted_analysis = client.request(
            "DELETE",
            base,
            json={
                "confirmation_analysis_id": analysis["analysis_id"],
                "expected_deletion_manifest_sha256": snapshot["deletion_manifest_sha256"],
            },
        )
        assert deleted_analysis.status_code == 200, deleted_analysis.text
        assert client.get(base + f"/exports/{second['asset_id']}/download").status_code == 404
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM experiment_design_analysis_assets"
                ).fetchone()[0]
                == 0
            )
            assert (
                connection.execute("SELECT COUNT(*) FROM experiment_response_revisions").fetchone()[
                    0
                ]
                == 1
            )
        assert client.get(f"/api/v1/doe-designs/{design['design_id']}").status_code == 200


def test_design_deletion_counts_and_cascades_reports(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        design, _, base = _analyze(client)
        client.post(base + "/exports/html", json={"locale": "en"})
        design_path = f"/api/v1/doe-designs/{design['design_id']}"
        preflight = client.get(design_path + "/deletion-preflight").json()
        assert preflight["counts"]["report_count"] == 1
        deleted = client.request(
            "DELETE",
            design_path,
            json={
                "confirmation_design_id": design["design_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM experiment_design_analysis_assets"
                ).fetchone()[0]
                == 0
            )


def test_metadata_19_upgrade_does_not_rewrite_existing_analysis_bytes(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, _, _base = _analyze(client)
    with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
        before = connection.execute(
            "SELECT config_json,result_json,result_sha256 FROM experiment_design_analyses"
        ).fetchall()
        connection.execute("DROP TABLE experiment_design_analysis_assets")
        connection.execute("DELETE FROM schema_migrations WHERE version=20")
        connection.execute("PRAGMA user_version=19")
    initialize_metadata_store(tmp_path)
    with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
        assert (
            connection.execute(
                "SELECT config_json,result_json,result_sha256 FROM experiment_design_analyses"
            ).fetchall()
            == before
        )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 20
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_general_report_uses_whole_term_blocks_and_actual_level_labels(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, analysis, base = _analyze(client, general=True)
        report = client.post(base + "/exports/html", json={"locale": "en"})
        assert report.status_code == 201, report.text
        html = client.get(base + f"/exports/{report.json()['asset_id']}/download").text
        assert "Low" in html and "High" in html
        assert "Cube plot:" not in html
        assert analysis["analysis_id"] in html and "Joint group" in html
        assert "treatment coefficients" in html


def test_report_asset_limit_and_atomic_rollback(tmp_path, monkeypatch):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        _, _, base = _analyze(client)
        monkeypatch.setattr("app.storage.factorial_analysis_assets.MAX_ASSETS_PER_ANALYSIS", 1)
        assert client.post(base + "/exports/html", json={"locale": "en"}).status_code == 201
        rejected = client.post(base + "/exports/html", json={"locale": "ko"})
        assert rejected.status_code == 409
        assert len(client.get(base + "/exports").json()["items"]) == 1
