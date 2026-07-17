import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import get_analysis_run_record, metadata_db_path


def test_phase_2_preflight_execute_restore_and_export_cross_dataset(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type="p")
        target = _upload_confirmed_csv(
            client,
            b"defectives,denominator\n6,20\n1,40\n5,10\n",
        )
        count_id = target["columns"][0]["column_id"]
        denominator_id = target["columns"][1]["column_id"]
        preflight = _preflight(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=denominator_id,
        )
        executed = _run_phase_2(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=denominator_id,
        )
        payload = executed.json()
        restored = client.get(f"/api/v1/analysis-runs/{payload['analysis_id']}/result")
        exports = [
            client.post(f"/api/v1/analysis-runs/{payload['analysis_id']}/exports/{format_name}")
            for format_name in ("json", "csv", "html")
        ]

    assert preflight.status_code == 200
    assert preflight.json()["ready"] is True
    assert preflight.json()["schema_version"] == 2
    assert preflight.json()["method_version"] == "0.3.0"
    assert preflight.json()["validation_scope"] == "schema_and_dependency_only"
    assert preflight.json()["row_data_validated"] is False
    assert executed.status_code == 201, executed.text
    assert restored.status_code == 200, restored.text
    assert all(response.status_code == 201 for response in exports)
    result = payload["result"]
    assert result["schema_version"] == 3
    assert result["phase"] == "phase_2"
    assert result["center_line"] == limit_set["frozen_center_line"]
    assert result["limit_set_dependency"]["limit_set_id"] == limit_set["limit_set_id"]
    assert result["limit_set_dependency"]["asset_sha256"] == limit_set["asset_sha256"]
    assert result["target_dependency"]["dataset_version_id"] == target["version_id"]
    assert (
        result["target_dependency"]["canonical_sha256"]
        == preflight.json()["target_canonical_sha256"]
    )
    assert [signal["position"] for signal in result["signals"]] == [2]


@pytest.mark.parametrize(
    ("chart_type", "content", "has_denominator"),
    [
        ("p", b"defectives,denominator\n6,20\n", True),
        ("np", b"defectives,denominator\n6,20\n", True),
        ("c", b"defects\n6\n", False),
        ("u", b"defects,denominator\n6,20\n", True),
    ],
)
def test_phase_2_one_point_restore_and_exports(
    tmp_path,
    chart_type,
    content,
    has_denominator,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type=chart_type)
        target = _upload_confirmed_csv(client, content)
        count_id = target["columns"][0]["column_id"]
        denominator_id = target["columns"][1]["column_id"] if has_denominator else None
        executed = _run_phase_2(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=denominator_id,
        )
        assert executed.status_code == 201, executed.text
        analysis_id = executed.json()["analysis_id"]
        restored = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        exports = [
            client.post(f"/api/v1/analysis-runs/{analysis_id}/exports/{format_name}")
            for format_name in ("json", "csv", "html")
        ]

    result = executed.json()["result"]
    assert result["n_used"] == 1
    assert result["chart"]["point_count"] == 1
    assert result["dispersion"]["available"] is False
    assert result["dispersion"]["degrees_of_freedom"] == 0
    assert result["dispersion"]["ratio"] is None
    assert result["dispersion"]["reason_code"] == (
        "attribute_control_chart_dispersion_insufficient_points"
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["result"] == result
    assert all(response.status_code == 201 for response in exports)


def test_phase_2_restores_legacy_v020_schema_2_without_rewriting(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type="p")
        target = _upload_confirmed_csv(client, b"defectives,denominator\n6,20\n7,20\n")
        executed = _run_phase_2(
            client,
            limit_set,
            target,
            count_id=target["columns"][0]["column_id"],
            denominator_id=target["columns"][1]["column_id"],
        )
        assert executed.status_code == 201, executed.text
        analysis_id = executed.json()["analysis_id"]
        record = get_analysis_run_record(tmp_path, analysis_id)
        assert record is not None and record.result_path is not None
        result_path = tmp_path / record.result_path
        envelope = json.loads(result_path.read_bytes())
        envelope["method_version"] = "0.2.0"
        envelope["provenance"]["method_version"] = "0.2.0"
        envelope["result"]["schema_version"] = 2
        envelope["result"]["dispersion"].pop("available")
        envelope["result"]["dispersion"].pop("reason_code")
        result_bytes = json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        result_path.write_bytes(result_bytes)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_runs SET method_version = ?, result_sha256 = ? "
                "WHERE analysis_id = ?",
                ("0.2.0", hashlib.sha256(result_bytes).hexdigest(), analysis_id),
            )
        restored = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        exported = client.post(f"/api/v1/analysis-runs/{analysis_id}/exports/json")

    assert restored.status_code == 200, restored.text
    assert restored.json()["method_version"] == "0.2.0"
    assert restored.json()["result"]["schema_version"] == 2
    assert "available" not in restored.json()["result"]["dispersion"]
    assert exported.status_code == 201, exported.text


def test_phase_2_preflight_reports_chart_count_and_target_schema_mismatch(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type="p")
        target = _upload_confirmed_csv(client, b"defectives,denominator\n2,20\n3,20\n")
        count_id = target["columns"][0]["column_id"]
        denominator_id = target["columns"][1]["column_id"]
        chart = _preflight(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=denominator_id,
            chart_type="u",
            count_definition="defects",
        )
        count_definition = _preflight(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=denominator_id,
            count_definition="defects",
        )
        schema = _preflight(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=count_id,
        )

    assert chart.json()["issues"][0]["code"] == (
        "attribute_control_chart_limit_set_chart_type_mismatch"
    )
    assert count_definition.json()["issues"][0]["code"] == (
        "attribute_control_chart_limit_set_count_definition_mismatch"
    )
    assert schema.json()["issues"][0]["code"] == (
        "attribute_control_chart_phase_2_target_schema_mismatch"
    )


def test_phase_2_np_rejects_target_sample_size_mismatch(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type="np")
        target = _upload_confirmed_csv(client, b"defectives,denominator\n2,20\n3,21\n")
        preflight = _preflight(
            client,
            limit_set,
            target,
            count_id=target["columns"][0]["column_id"],
            denominator_id=target["columns"][1]["column_id"],
        )
        response = _run_phase_2(
            client,
            limit_set,
            target,
            count_id=target["columns"][0]["column_id"],
            denominator_id=target["columns"][1]["column_id"],
        )

    assert preflight.status_code == 200
    assert preflight.json()["ready"] is True
    assert preflight.json()["validation_scope"] == "schema_and_dependency_only"
    assert preflight.json()["row_data_validated"] is False
    assert response.status_code == 400
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_phase_2_np_sample_size_mismatch"
    )
    _assert_public_error(response, tmp_path)


def test_phase_2_c_requires_current_opportunity_confirmation(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type="c")
        target = _upload_confirmed_csv(client, b"defects\n4\n6\n")
        count_id = target["columns"][0]["column_id"]
        preflight = _preflight(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=None,
            constant_opportunity_confirmed=False,
        )
        executed = _run_phase_2(
            client,
            limit_set,
            target,
            count_id=count_id,
            denominator_id=None,
            constant_opportunity_confirmed=False,
        )

    assert preflight.json()["ready"] is False
    assert preflight.json()["issues"][0]["code"] == (
        "attribute_control_chart_phase_2_c_opportunity_confirmation_required"
    )
    assert executed.status_code == 409
    assert executed.json()["error"]["code"] == (
        "attribute_control_chart_phase_2_c_opportunity_confirmation_required"
    )


def test_phase_2_restore_and_export_reject_rehashed_dependency_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        limit_set = _create_limit_set(client, chart_type="p")
        target = _upload_confirmed_csv(client, b"defectives,denominator\n2,20\n3,20\n")
        executed = _run_phase_2(
            client,
            limit_set,
            target,
            count_id=target["columns"][0]["column_id"],
            denominator_id=target["columns"][1]["column_id"],
        )
        assert executed.status_code == 201, executed.text
        analysis_id = executed.json()["analysis_id"]
        record = get_analysis_run_record(tmp_path, analysis_id)
        assert record is not None and record.result_path is not None
        path = tmp_path / record.result_path
        envelope = json.loads(path.read_bytes())
        envelope["result"]["target_dependency"]["dataset_version_id"] = "0" * 36
        data = json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        path.write_bytes(data)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_runs SET result_sha256 = ? WHERE analysis_id = ?",
                (hashlib.sha256(data).hexdigest(), analysis_id),
            )
        restored = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        exported = client.post(f"/api/v1/analysis-runs/{analysis_id}/exports/json")

    assert restored.status_code == 409
    assert exported.status_code == 409
    for response in (restored, exported):
        assert response.json()["error"]["code"] == (
            "attribute_control_chart_phase_2_dependency_mismatch"
        )
        _assert_public_error(response, tmp_path)


def _create_limit_set(client: TestClient, *, chart_type: str) -> dict[str, object]:
    definition = "defectives" if chart_type in {"p", "np"} else "defects"
    if chart_type == "c":
        content = (
            definition + "\n" + "\n".join("8" if i % 2 == 0 else "12" for i in range(20)) + "\n"
        ).encode()
    else:
        content = (
            f"{definition},denominator\n"
            + "\n".join(f"{8 if i % 2 == 0 else 12},20" for i in range(20))
            + "\n"
        ).encode()
    source = _upload_confirmed_csv(client, content)
    count_id = source["columns"][0]["column_id"]
    denominator_id = None if chart_type == "c" else source["columns"][1]["column_id"]
    result = _run_phase_1(
        client,
        source,
        chart_type=chart_type,
        count_id=count_id,
        denominator_id=denominator_id,
    )
    assert result.status_code == 201, result.text
    created = client.post(
        "/api/v1/quality/attribute-control-limit-sets",
        json={"source_analysis_id": result.json()["analysis_id"]},
    )
    assert created.status_code == 201, created.text
    return created.json()


def _run_phase_1(client, dataset, *, chart_type, count_id, denominator_id):
    options = {
        "phase": "phase_1",
        "chart_type": chart_type,
        "count_definition": "defectives" if chart_type in {"p", "np"} else "defects",
        "count_column_id": count_id,
        "constant_opportunity_confirmed": chart_type == "c",
        "point_limit": 100,
    }
    if denominator_id is not None:
        options["denominator_column_id"] = denominator_id
    return client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "quality.attribute_control_chart",
            "method_version": METHOD_VERSIONS["quality.attribute_control_chart"],
            "dataset_version_id": dataset["version_id"],
            "roles": {"count": count_id},
            "options": options,
        },
    )


def _run_phase_2(
    client,
    limit_set,
    dataset,
    *,
    count_id,
    denominator_id,
    constant_opportunity_confirmed=True,
):
    options = {
        "phase": "phase_2",
        "limit_set_id": limit_set["limit_set_id"],
        "chart_type": limit_set["chart_type"],
        "count_definition": limit_set["count_definition"],
        "count_column_id": count_id,
        "constant_opportunity_confirmed": constant_opportunity_confirmed,
        "point_limit": 100,
    }
    if denominator_id is not None:
        options["denominator_column_id"] = denominator_id
    return client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "quality.attribute_control_chart",
            "method_version": METHOD_VERSIONS["quality.attribute_control_chart"],
            "dataset_version_id": dataset["version_id"],
            "roles": {"count": count_id},
            "options": options,
        },
    )


def _preflight(
    client,
    limit_set,
    dataset,
    *,
    count_id,
    denominator_id,
    chart_type=None,
    count_definition=None,
    constant_opportunity_confirmed=True,
):
    return client.post(
        f"/api/v1/quality/attribute-control-limit-sets/{limit_set['limit_set_id']}"
        "/monitoring-preflight",
        json={
            "target_dataset_version_id": dataset["version_id"],
            "chart_type": chart_type or limit_set["chart_type"],
            "count_definition": count_definition or limit_set["count_definition"],
            "count_column_id": count_id,
            "denominator_column_id": denominator_id,
            "constant_opportunity_confirmed": constant_opportunity_confirmed,
        },
    )


def _upload_confirmed_csv(client: TestClient, content: bytes) -> dict[str, object]:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("private-monitor.csv", content, "text/csv")},
    )
    assert upload.status_code == 201
    confirmed = client.post(
        f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
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
                "missing_tokens": ["", "NA", "N/A", "null", "N/T"],
            },
            "columns": [],
        },
    )
    assert confirmed.status_code == 201, confirmed.text
    return confirmed.json()


def _assert_public_error(response, workspace_root: Path) -> None:
    public = json.dumps(response.json(), ensure_ascii=False)
    assert "private-monitor.csv" not in public
    assert str(workspace_root) not in public
    assert "traceback" not in public.lower()
