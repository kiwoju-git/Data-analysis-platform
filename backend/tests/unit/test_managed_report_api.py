from __future__ import annotations

import hashlib
import sqlite3
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient
from test_bayesian_recommendations_api import _create_study
from test_dedicated_report_sources import no_recompute
from test_factorial_prediction import _analyze
from test_lhs_design_api import _request as lhs_request
from test_regression_workflow_extensions_api import _fit_model
from test_response_optimizer_api import _create_source_analysis, _optimizer_request

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import SCHEMA_VERSION, metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace


class VisibleReport(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.tables = 0
        self.svgs = 0

    def handle_starttag(self, tag, attrs):
        self.tables += tag == "table"
        self.svgs += tag == "svg"

    def handle_data(self, data):
        self.text.append(data)


def _source(client, family):
    if family in {"factorial", "general_factorial"}:
        _analyze(client, general=family == "general_factorial")
        kind = "doe_analysis"
    elif family in {"rsm", "optimizer"}:
        design, analysis = _create_source_analysis(client)
        if family == "optimizer":
            response = client.post(
                f"/api/v1/doe-designs/response-surface/{design['design_id']}/optimizations",
                json=_optimizer_request(analysis["analysis_id"]),
            )
            assert response.status_code == 201, response.text
        kind = "doe_analysis" if family == "rsm" else "doe_optimizer_result"
    elif family == "lhs":
        response = client.post("/api/v1/doe-designs/latin-hypercube", json=lhs_request())
        assert response.status_code == 201, response.text
        kind = "lhs_design_revision"
    elif family == "bayesian":
        _create_study(client)
        kind = "bayesian_history_revision"
    elif family in {"analysis", "pasted_prediction", "dataset_prediction"}:
        version, model_id, manifest_sha = _fit_model(client)
        kind = "analysis_run"
        if family == "dataset_prediction":
            response = client.post(
                f"/api/v1/regression-models/{model_id}/predictions",
                json={"dataset_version_id": version["version_id"]},
            )
            assert response.status_code == 200, response.text
            kind = "regression_prediction"
        if family == "pasted_prediction":
            request = {
                "content": "x1\tx2\n2\t4\n4\t3\n20\t5\n",
                "has_header": True,
                "delimiter": "tab",
                "column_mappings": [],
                "expected_model_manifest_sha256": manifest_sha,
            }
            preflight = client.post(
                f"/api/v1/regression-models/{model_id}/pasted-prediction-preflight", json=request
            )
            assert preflight.status_code == 200, preflight.text
            response = client.post(
                f"/api/v1/regression-models/{model_id}/pasted-predictions",
                json={
                    **request,
                    "confidence_level": 0.95,
                    "include_intervals": True,
                    "expected_normalized_input_sha256": preflight.json()["normalized_input_sha256"],
                },
            )
            assert response.status_code == 201, response.text
            kind = "regression_prediction"
    else:
        raise AssertionError(family)
    catalog = client.get("/api/v1/reports/sources", params={"source_kind": kind})
    assert catalog.status_code == 200, catalog.text
    return catalog.json()["items"][0]["source"]


def _source_checksums(root):
    with sqlite3.connect(metadata_db_path(root)) as connection:
        return {
            table: connection.execute(f"SELECT {columns} FROM {table} ORDER BY 1").fetchall()
            for table, columns in (
                ("analysis_runs", "analysis_id,result_sha256"),
                ("experiment_design_analyses", "analysis_id,result_sha256"),
                ("regression_models", "model_id,manifest_sha256"),
            )
        }


@pytest.mark.parametrize(
    "family",
    [
        "factorial",
        "general_factorial",
        "rsm",
        "optimizer",
        "lhs",
        "bayesian",
        "analysis",
        "pasted_prediction",
        "dataset_prediction",
    ],
)
def test_managed_report_actual_sources_locale_roundtrip_and_delete(tmp_path, monkeypatch, family):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        source = _source(client, family)
        checksums = _source_checksums(tmp_path)
        no_recompute(monkeypatch)
        reports = []
        for locale in ("ko", "en"):
            request = {"source": source, "locale": locale}
            capability = client.post("/api/v1/reports/capability", json=request)
            assert capability.status_code == 200, capability.text
            assert capability.json()["html_available"]
            snapshot = client.post("/api/v1/reports/source-snapshot", json=request)
            assert snapshot.status_code == 200, snapshot.text
            assert snapshot.json()["source"] == source
            assert snapshot.json()["source_ref_sha256"] == capability.json()["source_ref_sha256"]
            assert snapshot.json()["locale"] == locale
            assert snapshot.json()["payload"]
            if family == "dataset_prediction":
                assert capability.json()["report_level"] == "summary"
                missing = next(
                    s for s in capability.json()["sections"] if s["section_id"] == "inputs"
                )
                assert missing["reason"] == "legacy_dataset_prediction_does_not_store_input_values"
            response = client.post(
                "/api/v1/reports",
                json={
                    **request,
                    "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
                },
            )
            assert response.status_code == 201, response.text
            report = response.json()
            reports.append(report)
            action = {"source": source, "expected_sha256": report["sha256"]}
            downloaded = client.post(f"/api/v1/reports/{report['export_id']}/download", json=action)
            assert downloaded.status_code == 200, downloaded.text
            assert hashlib.sha256(downloaded.content).hexdigest() == report["sha256"]
            assert f'<html lang="{locale}">' in downloaded.text
            visible = VisibleReport()
            visible.feed(downloaded.text)
            assert visible.tables >= 3
            assert "data-report-section=" in downloaded.text
            assert "<script" not in downloaded.text
            if family in {"factorial", "general_factorial", "rsm", "analysis"}:
                assert visible.svgs > 0
            if family == "pasted_prediction" and locale == "en":
                assert "Exact prediction inputs" in " ".join(visible.text)
                assert "New-observation PI lower" in " ".join(visible.text)
            assert client.get(f"/api/v1/reports/{report['export_id']}").json() == report
            if family in {"analysis", "factorial"}:
                with monkeypatch.context() as deleted_report:
                    reader = "get_analysis_artifact_record" if family == "analysis" else "get_asset"
                    deleted_report.setattr(
                        f"app.services.report_exports.{reader}", lambda *args: None
                    )
                    raced = client.get(f"/api/v1/reports/{report['export_id']}")
                    assert raced.status_code == 404, raced.text
                    assert raced.json()["error"]["code"] == "stored_report_not_found"
                    if family == "factorial":
                        raced_list = client.post("/api/v1/reports/artifacts/query", json=request)
                        assert raced_list.status_code == 404, raced_list.text
                        assert raced_list.json()["error"]["code"] == "stored_report_not_found"
            if family in {"factorial", "general_factorial"}:
                legacy_list = client.get(
                    f"/api/v1/doe-designs/{source['design_id']}/analyses/"
                    f"{source['analysis_id']}/exports"
                )
                assert legacy_list.status_code == 200, legacy_list.text
                assert report["export_id"] in [
                    item["asset_id"] for item in legacy_list.json()["items"]
                ]
        for report in reports:
            listed = client.post(
                "/api/v1/reports/artifacts/query",
                json={
                    "source": source,
                    "locale": report["locale"],
                },
            )
            assert listed.status_code == 200, listed.text
            assert [item["export_id"] for item in listed.json()["items"]] == [report["export_id"]]
            bad = client.post(
                f"/api/v1/reports/{report['export_id']}/download",
                json={
                    "source": source,
                    "expected_sha256": "0" * 64,
                },
            )
            assert bad.status_code == 409
            deleted = client.request(
                "DELETE",
                f"/api/v1/reports/{report['export_id']}",
                json={
                    "source": source,
                    "expected_sha256": report["sha256"],
                },
            )
            assert deleted.status_code == 200, deleted.text
            assert client.get(f"/api/v1/reports/{report['export_id']}").status_code == 404
        assert _source_checksums(tmp_path) == checksums


def test_new_report_stores_survive_offline_backup_restore(tmp_path):
    root = tmp_path / "source workspace"
    settings = Settings(workspace_root=root)
    reports = []
    with TestClient(create_app(settings)) as client:
        for family in ("lhs", "bayesian", "factorial", "pasted_prediction"):
            source = _source(client, family)
            capability = client.post("/api/v1/reports/capability", json={"source": source}).json()
            response = client.post(
                "/api/v1/reports",
                json={
                    "source": source,
                    "expected_source_ref_sha256": capability["source_ref_sha256"],
                },
            )
            assert response.status_code == 201, response.text
            report = response.json()
            action = {"source": source, "expected_sha256": report["sha256"]}
            content = client.post(f"/api/v1/reports/{report['export_id']}/download", json=action)
            assert content.status_code == 200, content.text
            reports.append((report, action, content.content))
    archive = tmp_path / "backup.zip"
    manifest = backup_workspace(root, archive)
    assert manifest["metadata_schema_version"] == SCHEMA_VERSION
    assert any("workspaces/reports/" in item["path"] for item in manifest["files"])
    restored_root = tmp_path / "restored workspace"
    restore_workspace(archive, restored_root)
    with TestClient(create_app(Settings(workspace_root=restored_root))) as client:
        for report, action, expected in reports:
            restored = client.get(f"/api/v1/reports/{report['export_id']}")
            assert restored.status_code == 200, restored.text
            assert restored.json()["sha256"] == report["sha256"]
            downloaded = client.post(f"/api/v1/reports/{report['export_id']}/download", json=action)
            assert downloaded.status_code == 200, downloaded.text
            assert downloaded.content == expected
