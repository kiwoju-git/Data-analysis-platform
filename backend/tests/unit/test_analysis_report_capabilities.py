import hashlib
import json
import sqlite3
from html.parser import HTMLParser
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_analysis_export_retention_api import _create_analysis

from app.core.config import Settings
from app.main import create_app
from app.services import analysis_run_exports as exports
from app.storage.metadata import get_analysis_run_record, metadata_db_path


class _Sections(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.tables = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "data-report-section" in attributes:
            self.ids.append(attributes["data-report-section"])
        if tag == "table":
            self.tables += 1


@pytest.mark.parametrize("locale", ["en", "ko"])
def test_capability_and_html_use_same_rendered_sections_source_hash_and_no_csv_flattening(
    tmp_path, monkeypatch, locale
):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        saved = _create_analysis(client)
        analysis_id = saved["analysis_id"]
        record = get_analysis_run_record(tmp_path, analysis_id)
        before = (tmp_path / record.result_path).read_bytes()

        def forbidden(*args, **kwargs):
            pytest.fail("HTML export attempted CSV flattening, fitting or raw-source loading")

        monkeypatch.setattr(exports, "_analysis_result_csv_rows", forbidden)
        monkeypatch.setattr("app.services.dataset_rows.iter_dataset_rows", forbidden)
        monkeypatch.setattr("app.services.dataset_rows.verify_canonical_rows_artifact", forbidden)
        capability_response = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/report-capability", params={"locale": locale}
        )
        assert capability_response.status_code == 200, capability_response.text
        capability = capability_response.json()
        assert capability["report_level"] == "full"
        assert capability["html_available"] is True
        assert capability["source_validation"] == "stored_dependencies_only"
        assert capability["locale"] == locale
        assert capability["source_result_sha256"] == hashlib.sha256(before).hexdigest()
        created = client.post(
            f"/api/v1/analysis-runs/{analysis_id}/exports/html",
            json={
                "locale": locale,
                "expected_source_result_sha256": capability["source_result_sha256"],
            },
        )
        assert created.status_code == 201, created.text
        result = created.json()
        assert result["schema_version"] == 4
        assert result["report_level"] == capability["report_level"]
        assert result["renderer_version"] == capability["renderer_version"]
        expected_ids = [
            s["section_id"] for s in capability["sections"] if s["status"] == "rendered"
        ]
        assert result["rendered_section_ids"] == expected_ids
        assert result["section_count"] == len(expected_ids)
        download = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/{result['export_id']}/download"
        )
        assert download.status_code == 200
        html = download.text
        parser = _Sections()
        parser.feed(html.split("<pre>")[0])
        assert parser.ids == expected_ids
        assert parser.tables >= 2
        assert "default-src 'none'" in html and "<script" not in html
        assert (tmp_path / record.result_path).read_bytes() == before


def test_hash_bound_report_rejects_stale_capability_without_new_artifact(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        saved = _create_analysis(client)
        analysis_id = saved["analysis_id"]
        before = client.get(f"/api/v1/analysis-runs/{analysis_id}/exports").json()
        response = client.post(
            f"/api/v1/analysis-runs/{analysis_id}/exports/html",
            json={
                "expected_source_result_sha256": "0" * 64,
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "analysis_report_source_changed"
        assert client.get(f"/api/v1/analysis-runs/{analysis_id}/exports").json() == before


@pytest.mark.parametrize("change", ["unsupported_schema", "missing_core"])
def test_unknown_schema_or_empty_core_has_no_successful_html(tmp_path, change):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        saved = _create_analysis(client)
        analysis_id = saved["analysis_id"]
        record = get_analysis_run_record(tmp_path, analysis_id)
        if change == "unsupported_schema":
            saved["result"]["schema_version"] = 999
        else:
            saved["result"] = {
                "schema_version": 2,
                "summary_type": "descriptive_statistics",
                "warnings": [],
            }
        encoded = json.dumps(saved, ensure_ascii=False, sort_keys=True).encode()
        (tmp_path / record.result_path).write_bytes(encoded)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_runs SET result_sha256=? WHERE analysis_id=?",
                (hashlib.sha256(encoded).hexdigest(), analysis_id),
            )
        capability = client.get(f"/api/v1/analysis-runs/{analysis_id}/report-capability").json()
        assert capability["report_level"] == "unsupported"
        assert capability["html_available"] is False
        assert capability["reason"] in {
            "analysis_report_schema_unsupported",
            "analysis_report_payload_invalid",
        }
        response = client.post(f"/api/v1/analysis-runs/{analysis_id}/exports/html")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "analysis_report_payload_unsupported"
        assert client.get(f"/api/v1/analysis-runs/{analysis_id}/exports").json()["exports"] == []
        assert (tmp_path / record.result_path).read_bytes() == encoded


def test_method_catalog_is_same_report_contract_as_capability(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        saved = _create_analysis(client)
        catalog = client.get("/api/v1/analysis-methods").json()
        descriptor = next(m for m in catalog["methods"] if m["method_id"] == saved["method_id"])
        definition = descriptor["report_contract"]
        capability = client.get(
            f"/api/v1/analysis-runs/{saved['analysis_id']}/report-capability"
        ).json()
        assert definition["renderer_id"] == capability["renderer_id"]
        assert definition["renderer_version"] == capability["renderer_version"]
        assert capability["result_schema_version"] in definition["accepted_schema_versions"]
        assert capability["variant_id"] in [v["variant_id"] for v in definition["variants"]]
        assert UUID(capability["analysis_id"]) == UUID(saved["analysis_id"])
