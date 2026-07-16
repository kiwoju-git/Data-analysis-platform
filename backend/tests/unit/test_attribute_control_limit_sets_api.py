import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    get_analysis_run_record,
    get_attribute_control_limit_set_record,
    get_dataset_artifact_record,
    metadata_db_path,
)


def test_create_restore_list_and_idempotently_reuse_attribute_limit_set(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        source = _create_eligible_phase_one_chart(client)
        created = client.post(
            "/api/v1/quality/attribute-control-limit-sets",
            json={"source_analysis_id": source["analysis_id"]},
        )
        repeated = client.post(
            "/api/v1/quality/attribute-control-limit-sets",
            json={"source_analysis_id": source["analysis_id"]},
        )
        payload = created.json()
        restored = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )
        listed = client.get(
            "/api/v1/quality/attribute-control-limit-sets",
            params={
                "source_dataset_version_id": source["dataset_version_id"],
                "chart_type": "p",
            },
        )

    assert created.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json() == payload
    assert restored.status_code == 200
    assert restored.json() == payload
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"] == [payload]
    assert payload["asset_schema_version"] == 1
    assert payload["source_method_version"] == "0.1.0"
    assert payload["phase2_method_version"] == "0.2.0"
    assert payload["source_result_schema_version"] == 1
    assert payload["status"] == "closed"
    assert payload["chart_type"] == "p"
    assert payload["baseline_point_count"] == 20
    assert payload["frozen_center_line"] == 0.5
    assert payload["total_count"] == 200
    assert payload["total_denominator"] == 400.0
    assert payload["fixed_sample_size"] is None
    assert payload["eligibility"]["eligible"] is True
    assert payload["eligibility"]["checks_passed"] == [
        "minimum_point_count",
        "no_phase_1_limit_signals",
        "usable_normal_approximation",
        "pearson_dispersion_not_above_two",
        "complete_untruncated_point_payload",
    ]
    assert len(payload["asset_sha256"]) == 64
    assert "asset_path" not in payload
    assert "filename" not in json.dumps(payload).lower()
    record = get_attribute_control_limit_set_record(tmp_path, payload["limit_set_id"])
    assert record is not None
    asset_path = tmp_path / record.asset_path
    assert asset_path.exists()
    assert hashlib.sha256(asset_path.read_bytes()).hexdigest() == payload["asset_sha256"]


@pytest.mark.parametrize(
    ("chart_type", "count_definition", "expected_center", "fixed_sample_size", "natural_bound"),
    [
        ("np", "defectives", 10.0, 20, "binomial_zero_fixed_sample_size"),
        ("c", "defects", 10.0, None, "poisson_zero"),
        ("u", "defects", 0.5, None, "poisson_zero"),
    ],
)
def test_promotes_np_c_and_u_phase_one_baselines(
    tmp_path,
    chart_type,
    count_definition,
    expected_center,
    fixed_sample_size,
    natural_bound,
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        source = _create_phase_one_chart(client, point_count=20, chart_type=chart_type)
        response = client.post(
            "/api/v1/quality/attribute-control-limit-sets",
            json={"source_analysis_id": source["analysis_id"]},
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["chart_type"] == chart_type
    assert payload["count_definition"] == count_definition
    assert payload["frozen_center_line"] == expected_center
    assert payload["fixed_sample_size"] == fixed_sample_size
    assert payload["natural_bound_policy"] == natural_bound
    if chart_type == "c":
        assert payload["denominator"] is None
        assert payload["denominator_role"] is None
        assert payload["constant_opportunity_confirmed"] is True
    else:
        assert payload["denominator"] is not None


def test_rejects_small_phase_one_baseline_without_creating_asset(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        source = _create_phase_one_chart(client, point_count=4)
        response = client.post(
            "/api/v1/quality/attribute-control-limit-sets",
            json={"source_analysis_id": source["analysis_id"]},
        )
        listed = client.get("/api/v1/quality/attribute-control-limit-sets")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_source_ineligible"
    )
    assert listed.json()["total"] == 0
    _assert_public_error(response, tmp_path)


def test_rejects_stale_phase_one_source(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        source = _create_eligible_phase_one_chart(client)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_runs SET stale = 1 WHERE analysis_id = ?",
                (source["analysis_id"],),
            )
        response = client.post(
            "/api/v1/quality/attribute-control-limit-sets",
            json={"source_analysis_id": source["analysis_id"]},
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_source_analysis_stale"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_limit_set_file_checksum_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        record = get_attribute_control_limit_set_record(tmp_path, payload["limit_set_id"])
        assert record is not None
        (tmp_path / record.asset_path).write_bytes(b'{"tampered":true}')
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_checksum_mismatch"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_rehashed_metadata_relationship_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE attribute_control_limit_sets SET center_line = 0.55 WHERE limit_set_id = ?",
                (payload["limit_set_id"],),
            )
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_metadata_invalid"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_rehashed_asset_relationship_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        record = get_attribute_control_limit_set_record(tmp_path, payload["limit_set_id"])
        assert record is not None
        asset_path = tmp_path / record.asset_path
        asset_payload = json.loads(asset_path.read_bytes())
        asset_payload["frozen_center_line"] = 0.55
        asset_bytes = json.dumps(
            asset_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        asset_path.write_bytes(asset_bytes)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE attribute_control_limit_sets SET asset_sha256 = ? WHERE limit_set_id = ?",
                (hashlib.sha256(asset_bytes).hexdigest(), payload["limit_set_id"]),
            )
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_metadata_invalid"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_rehashed_source_result_relationship_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        analysis = get_analysis_run_record(tmp_path, payload["source_analysis_id"])
        assert analysis is not None and analysis.result_path is not None
        result_path = tmp_path / analysis.result_path
        result_payload = json.loads(result_path.read_bytes())
        result_payload["result"]["center_line"] = 0.51
        result_bytes = json.dumps(
            result_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        result_path.write_bytes(result_bytes)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_runs SET result_sha256 = ? WHERE analysis_id = ?",
                (hashlib.sha256(result_bytes).hexdigest(), analysis.analysis_id),
            )
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_source_dependency_mismatch"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_source_row_snapshot_file_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        analysis = get_analysis_run_record(tmp_path, payload["source_analysis_id"])
        assert analysis is not None
        config = json.loads(analysis.config_json)
        snapshot_path = tmp_path / config["row_snapshot"]["path"]
        snapshot_path.write_bytes(b'{"tampered":true}')
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_source_artifact_mismatch"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_source_canonical_artifact_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        artifact = get_dataset_artifact_record(
            tmp_path,
            payload["source_dataset_version_id"],
            "canonical_rows",
        )
        assert artifact is not None
        (tmp_path / artifact.path).write_bytes(b'{"tampered":true}\n')
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_source_artifact_mismatch"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_source_schema_relationship_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE dataset_versions SET schema_hash = ? WHERE version_id = ?",
                ("0" * 64, payload["source_dataset_version_id"]),
            )
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "attribute_control_chart_limit_set_source_schema_mismatch"
    )
    _assert_public_error(response, tmp_path)


def test_restore_rejects_absolute_asset_path_without_disclosure(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    private_path = Path("C:/private/attribute-limit-set.json")
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE attribute_control_limit_sets SET asset_path = ? WHERE limit_set_id = ?",
                (str(private_path), payload["limit_set_id"]),
            )
        response = client.get(
            f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "attribute_control_chart_limit_set_invalid"
    public = json.dumps(response.json(), ensure_ascii=False)
    assert str(private_path) not in public
    _assert_public_error(response, tmp_path)


def test_limit_set_has_no_overwrite_or_delete_route(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        payload = _create_limit_set(client)
        path = f"/api/v1/quality/attribute-control-limit-sets/{payload['limit_set_id']}"
        overwrite = client.put(path, json={"frozen_center_line": 0.1})
        delete = client.delete(path)
        restored = client.get(path)

    assert overwrite.status_code == 405
    assert delete.status_code == 405
    assert restored.status_code == 200
    assert restored.json() == payload


def _create_limit_set(client: TestClient) -> dict[str, object]:
    source = _create_eligible_phase_one_chart(client)
    response = client.post(
        "/api/v1/quality/attribute-control-limit-sets",
        json={"source_analysis_id": source["analysis_id"]},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_eligible_phase_one_chart(client: TestClient) -> dict[str, object]:
    return _create_phase_one_chart(client, point_count=20)


def _create_phase_one_chart(
    client: TestClient,
    *,
    point_count: int,
    chart_type: str = "p",
) -> dict[str, object]:
    count_definition = "defectives" if chart_type in {"p", "np"} else "defects"
    count_name = "defectives" if count_definition == "defectives" else "defects"
    if chart_type == "c":
        rows = [count_name]
        rows.extend(str(8 if index % 2 == 0 else 12) for index in range(point_count))
    else:
        rows = [f"{count_name},denominator"]
        rows.extend(f"{8 if index % 2 == 0 else 12},20" for index in range(point_count))
    version = _upload_confirmed_csv(client, ("\n".join(rows) + "\n").encode("utf-8"))
    count_column_id = version["columns"][0]["column_id"]
    denominator_column_id = None if chart_type == "c" else version["columns"][1]["column_id"]
    options = {
        "chart_type": chart_type,
        "count_definition": count_definition,
        "count_column_id": count_column_id,
        "missing_policy": "complete_case",
        "point_limit": 100,
    }
    roles = {"count": count_column_id}
    if denominator_column_id is not None:
        options["denominator_column_id"] = denominator_column_id
        roles["sample_size" if chart_type in {"p", "np"} else "inspection_opportunity"] = (
            denominator_column_id
        )
    if chart_type == "c":
        options["constant_opportunity_confirmed"] = True
    response = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "quality.attribute_control_chart",
            "method_version": METHOD_VERSIONS["quality.attribute_control_chart"],
            "dataset_version_id": version["version_id"],
            "roles": roles,
            "options": options,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload_confirmed_csv(client: TestClient, content: bytes) -> dict[str, object]:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("private-baseline.csv", content, "text/csv")},
    )
    assert upload.status_code == 201
    dataset_id = upload.json()["dataset_id"]
    confirmed = client.post(
        f"/api/v1/datasets/{dataset_id}/confirm-parsing",
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
    assert "private-baseline.csv" not in public
    assert str(workspace_root) not in public
    assert '"defectives"' not in public
