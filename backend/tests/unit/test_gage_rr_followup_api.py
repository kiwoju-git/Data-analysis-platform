import hashlib
import json
from dataclasses import replace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.services.analysis_run_results import load_analysis_run_result
from app.services.quality_report import quality_report_body
from app.services.report_coverage import INLINE_REPORT_CONTRACTS
from app.storage.metadata import get_analysis_run_record


def upload(client, *, explicit=False):
    content = (
        "part,operator,measurement"
        + (",replicate" if explicit else "")
        + "\n"
        + "".join(
            f"P{part},O{operator},{100+2*part+operator+0.01*(part-4.5)*(operator-1)+error}"
            + (f",r{repeat}" if explicit else "")
            + "\n"
            for part in range(10)
            for operator in range(3)
            for repeat, error in enumerate((-0.2, 0.2), start=1)
        )
    )
    uploaded = client.post(
        "/api/v1/datasets", files={"file": ("synthetic-gage.csv", content.encode(), "text/csv")}
    )
    assert uploaded.status_code == 201
    confirmed = client.post(
        f"/api/v1/datasets/{uploaded.json()['dataset_id']}/confirm-parsing",
        json={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "quote_char": '"',
                "decimal": ".",
                "thousands": None,
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": [""],
            },
            "columns": [],
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()


def test_three_column_filtered_preflight_run_restore_and_report(tmp_path, monkeypatch):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = upload(client)
        columns = {column["display_name"]: column["column_id"] for column in version["columns"]}
        options = {
            "measurement_column_id": columns["measurement"],
            "part_column_id": columns["part"],
            "operator_column_id": columns["operator"],
            "replicate_mode": "infer_from_rows",
            "replicate_column_id": None,
        }
        preflight_body = {"dataset_version_id": version["version_id"], **options}
        checked = client.post("/api/v1/quality/gage-rr/preflight", json=preflight_body)
        assert checked.status_code == 200, checked.text
        assert checked.json()["schema_version"] == 2
        assert checked.json()["design"]["ready_for_anova"]
        assert checked.json()["sample"]["n_used"] == 60
        assert checked.json()["columns"]["replicate"] is None
        filter_snapshot = {
            "expression_version": 1,
            "conditions": [{"column_id": columns["measurement"], "operator": "gt", "value": 100}],
        }
        filtered = client.post(
            "/api/v1/quality/gage-rr/preflight",
            json={**preflight_body, "filter_snapshot": filter_snapshot},
        )
        assert filtered.status_code == 200, filtered.text
        assert not filtered.json()["design"]["ready_for_anova"]
        assert filtered.json()["sample"]["n_used"] < 60
        assert filtered.json()["filter_snapshot_sha256"] != checked.json()["filter_snapshot_sha256"]
        request = {
            "method_id": "quality.gage_rr",
            "method_version": METHOD_VERSIONS["quality.gage_rr"],
            "dataset_version_id": version["version_id"],
            "roles": {},
            "options": {**options, "interaction_policy": "auto_pool"},
        }
        rejected = client.post(
            "/api/v1/analysis-runs", json={**request, "filter_snapshot": filter_snapshot}
        )
        assert rejected.status_code == 400, rejected.text
        assert rejected.json()["error"]["code"] == "gage_rr_replicate_count_too_small"
        response = client.post("/api/v1/analysis-runs", json=request)
        assert response.status_code == 201, response.text
        envelope = response.json()
        result = envelope["result"]
        assert result["schema_version"] == 2
        assert result["interaction_selection"]["pooled"]
        assert result["design"]["replicate_count"] == 2
        path = f"/api/v1/analysis-runs/{envelope['analysis_id']}"
        before = client.get(path + "/result")
        assert before.json() == envelope
        digest = hashlib.sha256(before.content).hexdigest()
        old_version = upload(client, explicit=True)
        old_columns = {
            column["display_name"]: column["column_id"] for column in old_version["columns"]
        }
        old_response = client.post(
            "/api/v1/analysis-runs",
            json={
                **request,
                "dataset_version_id": old_version["version_id"],
                "options": {
                    f"{name}_column_id": column_id for name, column_id in old_columns.items()
                },
            },
        )
        assert old_response.status_code == 201, old_response.text
        assert (
            old_response.json()["result"]["interaction_selection"]["effective_policy"] == "retain"
        )

        def forbidden(*args, **kwargs):
            pytest.fail("stored report must not read source rows or recalculate Gage ANOVA")

        monkeypatch.setattr("app.statistics.gage_rr.calculate_gage_rr_anova", forbidden)
        monkeypatch.setattr(
            "app.services.analysis_runners_quality.calculate_gage_rr_anova", forbidden
        )
        monkeypatch.setattr("app.services.gage_rr.iter_dataset_rows", forbidden)
        monkeypatch.setattr("app.services.dataset_rows.iter_dataset_rows", forbidden)
        for locale in ("ko", "en"):
            exported = client.post(path + "/exports/html", json={"locale": locale})
            assert exported.status_code == 201, exported.text
            descriptor = exported.json()
            downloaded = client.get(path + f"/exports/{descriptor['export_id']}/download")
            assert downloaded.status_code == 200, downloaded.text
            assert 'data-report-section="gage_policy"' in downloaded.text
            assert 'data-report-section="gage_full_anova"' in downloaded.text
            assert "auto_pool" in downloaded.text
            assert "infer_from_rows" in downloaded.text
        assert hashlib.sha256(client.get(path + "/result").content).hexdigest() == digest
        assert not list(tmp_path.rglob("*preflight*"))
        assert "P0" not in json.dumps(result)

        # Synthetic schema-1 archive exercises the unchanged checksum reader.
        legacy = old_response.json()
        legacy["method_version"] = "0.1.0"
        legacy["result"]["schema_version"] = 1
        for key in (
            "replicate_mode",
            "interaction_selection",
            "full_anova_table",
            "reduced_anova_table",
        ):
            legacy["result"].pop(key, None)
        legacy_bytes = json.dumps(legacy, ensure_ascii=False).encode()
        legacy_path = tmp_path / "synthetic-schema1-result.json"
        legacy_path.write_bytes(legacy_bytes)
        record = get_analysis_run_record(tmp_path, legacy["analysis_id"])
        assert record is not None
        legacy_record = replace(
            record,
            method_version="0.1.0",
            result_path=legacy_path.name,
            result_sha256=hashlib.sha256(legacy_bytes).hexdigest(),
        )
        monkeypatch.setattr(
            "app.services.analysis_run_results.get_analysis_run_record", lambda *args: legacy_record
        )
        restored = load_analysis_run_result(
            Settings(workspace_root=tmp_path), UUID(legacy["analysis_id"])
        )
        assert restored.envelope.method_version == "0.1.0"
        assert restored.envelope.result == legacy["result"]
        assert 1 in INLINE_REPORT_CONTRACTS["quality.gage_rr"][1]
        for locale in ("ko", "en"):
            html = quality_report_body(restored.envelope.result, locale).render()
            assert "legacy_interaction_retained" in html
            assert 'data-report-section="gage_full_anova"' in html
        assert legacy_path.read_bytes() == legacy_bytes


def test_mode_contradictions_and_empty_alpha_rejected(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = upload(client)
        columns = {column["display_name"]: column["column_id"] for column in version["columns"]}
        body = {
            "dataset_version_id": version["version_id"],
            "measurement_column_id": columns["measurement"],
            "part_column_id": columns["part"],
            "operator_column_id": columns["operator"],
            "replicate_mode": "explicit_column",
            "replicate_column_id": None,
        }
        assert client.post("/api/v1/quality/gage-rr/preflight", json=body).status_code == 422
        invalid_alpha = client.post(
            "/api/v1/analysis-runs",
            json={
                "method_id": "quality.gage_rr",
                "method_version": METHOD_VERSIONS["quality.gage_rr"],
                "dataset_version_id": version["version_id"],
                "roles": {},
                "options": {
                    **{key: value for key, value in body.items() if key != "dataset_version_id"},
                    "replicate_mode": "infer_from_rows",
                    "alpha_to_remove_interaction": "",
                },
            },
        )
        assert invalid_alpha.status_code == 422
        assert invalid_alpha.json()["error"]["code"] == "invalid_gage_rr_options"
