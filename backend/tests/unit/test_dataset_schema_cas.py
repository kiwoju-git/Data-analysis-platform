import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHOD_VERSIONS
from app.core.config import Settings
from app.main import create_app
from app.services import dataset_versions
from app.storage import metadata


def _version(client):
    upload = client.post(
        "/api/v1/datasets", files={"file": ("synthetic.csv", b"x,y\n1,2\n3,4\n5,6\n")}
    )
    assert upload.status_code == 201, upload.text
    response = client.post(
        f"/api/v1/datasets/{upload.json()['dataset_id']}/confirm-parsing",
        json={
            "parsing": {
                "kind": "delimited_text",
                "encoding": "utf-8",
                "delimiter": ",",
                "has_header": True,
                "header_row": 1,
                "data_start_row": 2,
                "missing_tokens": ["", "NA"],
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _request(version, *, label=None):
    column = version["columns"][0]
    return {
        "expected_schema_hash": version["schema_hash"],
        "columns": [
            {
                "column_id": column["column_id"],
                "display_name": column["display_name"] if label is None else label,
                "measurement_level": column["measurement_level"],
                "role": column["role"],
                "unit": column["unit"],
            }
        ],
    }


def _analysis(client, version):
    response = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "eda.descriptive",
            "method_version": METHOD_VERSIONS["eda.descriptive"],
            "dataset_version_id": version["version_id"],
            "roles": {},
            "options": {
                "column_ids": [version["columns"][0]["column_id"]],
                "missing_policy": "available_case_by_column",
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["analysis_id"]


def _snapshot(root):
    with sqlite3.connect(metadata.metadata_db_path(root)) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("dataset_versions", "dataset_columns", "analysis_runs")
        }


def _artifact_snapshot(root):
    with sqlite3.connect(metadata.metadata_db_path(root)) as connection:
        records = connection.execute(
            "SELECT artifact_id, path, sha256 FROM analysis_artifacts ORDER BY artifact_id"
        ).fetchall()
        records.extend(
            connection.execute(
                "SELECT analysis_id, result_path, result_sha256 FROM analysis_runs "
                "WHERE result_path IS NOT NULL ORDER BY analysis_id"
            ).fetchall()
        )
    return [
        (record, hashlib.sha256((root / record[1]).read_bytes()).hexdigest()) for record in records
    ]


def test_schema_update_requires_expected_source_hash(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        request = _request(version, label="new label")
        del request["expected_schema_hash"]
        before = _snapshot(tmp_path)
        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema", json=request
        )
        assert response.status_code == 422
        assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("invalid", ["", "a" * 63, "A" * 64, "z" * 64, None, 123])
def test_schema_update_rejects_invalid_hash_without_writes(tmp_path, invalid):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        request = _request(version, label="new label")
        request["expected_schema_hash"] = invalid
        before = _snapshot(tmp_path)
        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema", json=request
        )
        assert response.status_code == 422
        assert _snapshot(tmp_path) == before


def test_schema_noop_and_conflict_preserve_hash_columns_and_stale_state(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        unrelated = _version(client)
        analysis_id = _analysis(client, version)
        unrelated_id = _analysis(client, unrelated)
        path = f"/api/v1/dataset-versions/{version['version_id']}/schema"
        before = _snapshot(tmp_path)
        artifacts = _artifact_snapshot(tmp_path)
        for _ in range(2):
            assert client.patch(path, json=_request(version)).status_code == 200
            assert _snapshot(tmp_path) == before
        changed = client.patch(path, json=_request(version, label="new label"))
        assert changed.status_code == 200, changed.text
        assert changed.json()["schema_hash"] != version["schema_hash"]
        assert client.get(f"/api/v1/analysis-runs/{analysis_id}").json()["stale"] is True
        assert client.get(f"/api/v1/analysis-runs/{unrelated_id}").json()["stale"] is False
        after = _snapshot(tmp_path)
        old_hash_noop = _request(changed.json())
        old_hash_noop["expected_schema_hash"] = version["schema_hash"]
        for request in (_request(version, label="loser"), old_hash_noop):
            response = client.patch(path, json=request)
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "dataset_schema_conflict"
            assert _snapshot(tmp_path) == after
        assert client.patch(path, json=_request(changed.json())).status_code == 200
        assert _snapshot(tmp_path) == after
        assert (
            client.get(f"/api/v1/dataset-versions/{unrelated['version_id']}").json()["schema_hash"]
            == unrelated["schema_hash"]
        )
        assert _artifact_snapshot(tmp_path) == artifacts


def test_valid_noop_preserves_existing_opaque_schema_hash(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        _analysis(client, version)
        opaque_hash = "f" * 64
        assert version["schema_hash"] != opaque_hash
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE dataset_versions SET schema_hash = ? WHERE version_id = ?",
                (opaque_hash, version["version_id"]),
            )
        version["schema_hash"] = opaque_hash
        before = _snapshot(tmp_path)
        artifacts = _artifact_snapshot(tmp_path)
        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema", json=_request(version)
        )
        assert response.status_code == 200, response.text
        assert response.json()["schema_hash"] == opaque_hash
        assert response.json()["columns"] == version["columns"]
        assert _snapshot(tmp_path) == before
        assert _artifact_snapshot(tmp_path) == artifacts


def test_two_concurrent_clients_from_one_hash_have_exactly_one_winner(tmp_path, monkeypatch):
    barrier = Barrier(2)
    original = dataset_versions.update_dataset_schema_records
    connections = []
    write_connections = set()

    def synchronized_write(*args, **kwargs):
        barrier.wait(timeout=10)
        return original(*args, **kwargs)

    original_connect = metadata.sqlite3.connect

    def record_connection(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connections.append(connection)
        connection.set_trace_callback(
            lambda sql: write_connections.add(id(connection)) if sql == "BEGIN IMMEDIATE;" else None
        )
        return connection

    app = create_app(Settings(workspace_root=tmp_path))
    with TestClient(app) as first, closing(TestClient(app)) as second:
        version = _version(first)
        monkeypatch.setattr(dataset_versions, "update_dataset_schema_records", synchronized_write)
        monkeypatch.setattr(metadata.sqlite3, "connect", record_connection)
        path = f"/api/v1/dataset-versions/{version['version_id']}/schema"
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [
                pool.submit(client.patch, path, json=_request(version, label=label))
                for client, label in ((first, "first"), (second, "second"))
            ]
            responses = [future.result(timeout=20) for future in pending]
        assert sorted(response.status_code for response in responses) == [200, 409]
        winner = next(response.json() for response in responses if response.status_code == 200)
        loser = next(response for response in responses if response.status_code == 409)
        assert loser.json()["error"]["code"] == "dataset_schema_conflict"
        assert first.get(path).json() == winner
        assert len(write_connections) == 2


def test_schema_deleted_after_service_read_returns_404_without_orphans(tmp_path, monkeypatch):
    original = dataset_versions.update_dataset_schema_records

    def delete_then_write(root, version_id, *args, **kwargs):
        with sqlite3.connect(metadata.metadata_db_path(root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("DELETE FROM dataset_versions WHERE version_id = ?", (version_id,))
        return original(root, version_id, *args, **kwargs)

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        monkeypatch.setattr(dataset_versions, "update_dataset_schema_records", delete_then_write)
        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json=_request(version, label="new label"),
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "dataset_version_not_found"
        assert all(not rows for rows in _snapshot(tmp_path).values())


def test_schema_deleted_between_version_and_columns_read_returns_404(tmp_path, monkeypatch):
    original = dataset_versions.list_dataset_column_records

    def delete_then_read(root, version_id):
        with sqlite3.connect(metadata.metadata_db_path(root)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("DELETE FROM dataset_versions WHERE version_id = ?", (version_id,))
        return original(root, version_id)

    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        monkeypatch.setattr(dataset_versions, "list_dataset_column_records", delete_then_read)
        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json=_request(version, label="new label"),
        )
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "dataset_version_not_found"
        assert all(not rows for rows in _snapshot(tmp_path).values())


@pytest.mark.parametrize("failure_table", ["dataset_columns", "analysis_runs"])
def test_schema_partial_write_failure_rolls_back_every_changed_record(tmp_path, failure_table):
    with TestClient(
        create_app(Settings(workspace_root=tmp_path)), raise_server_exceptions=False
    ) as client:
        version = _version(client)
        _analysis(client, version)
        when = (
            f"WHEN OLD.column_index = {version['columns'][1]['column_index']} "
            if failure_table == "dataset_columns"
            else ""
        )
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as connection:
            connection.execute(
                f"CREATE TRIGGER fail_schema BEFORE UPDATE ON {failure_table} "
                + when
                + "BEGIN SELECT RAISE(ABORT, 'synthetic private failure'); END"
            )
        before = _snapshot(tmp_path)
        response = client.patch(
            f"/api/v1/dataset-versions/{version['version_id']}/schema",
            json=_request(version, label="private submitted label"),
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "dataset_schema_conflict"
        assert _snapshot(tmp_path) == before
        assert "private" not in response.text
        assert str(tmp_path) not in response.text


def test_schema_missing_owner_returns_404(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        version = _version(client)
        response = client.patch(
            f"/api/v1/dataset-versions/{uuid4()}/schema", json=_request(version)
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "dataset_version_not_found"
