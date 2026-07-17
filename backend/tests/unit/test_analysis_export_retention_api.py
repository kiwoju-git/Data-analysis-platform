import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

import app.services.analysis_run_exports as analysis_run_exports
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    AnalysisArtifactStorageConflict,
    get_analysis_artifact_record,
    metadata_db_path,
)


def _create_analysis(client: TestClient) -> dict:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("retention.csv", b"value\n1\n2\n3\n", "text/csv")},
    )
    assert upload.status_code == 201
    version = client.post(
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
    assert version.status_code == 201
    version_payload = version.json()
    analysis = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "eda.descriptive",
            "method_version": "0.1.0",
            "dataset_version_id": version_payload["version_id"],
            "roles": {},
            "options": {
                "column_ids": [version_payload["columns"][0]["column_id"]],
                "missing_policy": "available_case_by_column",
            },
        },
    )
    assert analysis.status_code == 201
    return analysis.json()


def _create_export(client: TestClient, analysis_id: str, format_name: str = "json") -> dict:
    response = client.post(f"/api/v1/analysis-runs/{analysis_id}/exports/{format_name}")
    assert response.status_code == 201
    return response.json()


def _delete_body(analysis_id: str, export_id: str, manifest_sha256: str) -> dict:
    return {
        "confirmation_analysis_id": analysis_id,
        "confirmation_export_id": export_id,
        "expected_deletion_manifest_sha256": manifest_sha256,
    }


def test_export_deletion_removes_only_confirmed_file_and_metadata(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis = _create_analysis(client)
        analysis_id = analysis["analysis_id"]
        json_export = _create_export(client, analysis_id)
        csv_export = _create_export(client, analysis_id, "csv")
        artifact = get_analysis_artifact_record(tmp_path, analysis_id, json_export["export_id"])
        assert artifact is not None
        export_path = tmp_path / artifact.path

        preflight_response = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{json_export['export_id']}/deletion-preflight"
        )
        preflight = preflight_response.json()
        wrong_id = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/exports/{json_export['export_id']}",
            json=_delete_body(
                str(uuid4()), json_export["export_id"], preflight["deletion_manifest_sha256"]
            ),
        )
        deleted_response = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/exports/{json_export['export_id']}",
            json=_delete_body(
                analysis_id,
                json_export["export_id"],
                preflight["deletion_manifest_sha256"],
            ),
        )
        export_list = client.get(f"/api/v1/analysis-runs/{analysis_id}/exports")
        result_restore = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        deleted_download = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/" f"{json_export['export_id']}/download"
        )

    assert preflight_response.status_code == 200
    assert preflight["counts"] == {
        "metadata_record_count": 1,
        "file_count": 1,
        "file_bytes": json_export["size_bytes"],
    }
    assert preflight["sha256"] == json_export["sha256"]
    assert artifact.path not in json.dumps(preflight)
    assert str(tmp_path) not in json.dumps(preflight)
    assert wrong_id.status_code == 409
    assert wrong_id.json()["error"]["code"] == ("analysis_export_deletion_confirmation_mismatch")
    assert deleted_response.status_code == 200
    assert deleted_response.json()["cleanup_status"] == "deleted"
    assert deleted_response.json()["deleted_counts"] == preflight["counts"]
    assert not export_path.exists()
    assert get_analysis_artifact_record(tmp_path, analysis_id, json_export["export_id"]) is None
    assert [item["export_id"] for item in export_list.json()["exports"]] == [
        csv_export["export_id"]
    ]
    assert result_restore.status_code == 200
    assert deleted_download.status_code == 404


def test_export_deletion_rejects_path_checksum_and_stale_manifest_tamper(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis = _create_analysis(client)
        analysis_id = analysis["analysis_id"]
        path_export = _create_export(client, analysis_id)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_artifacts SET path = ? WHERE artifact_id = ?;",
                ("outside.json", path_export["export_id"]),
            )
        path_error = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{path_export['export_id']}/deletion-preflight"
        )

        checksum_export = _create_export(client, analysis_id, "csv")
        checksum_artifact = get_analysis_artifact_record(
            tmp_path, analysis_id, checksum_export["export_id"]
        )
        assert checksum_artifact is not None
        (tmp_path / checksum_artifact.path).write_bytes(b"tampered")
        checksum_error = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{checksum_export['export_id']}/deletion-preflight"
        )

        media_export = _create_export(client, analysis_id)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_artifacts SET media_type = ? WHERE artifact_id = ?;",
                ("application/octet-stream", media_export["export_id"]),
            )
        media_error = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{media_export['export_id']}/deletion-preflight"
        )

        stale_export = _create_export(client, analysis_id, "html")
        preflight = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{stale_export['export_id']}/deletion-preflight"
        ).json()
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_artifacts SET created_at = ? WHERE artifact_id = ?;",
                ("2026-07-16T23:59:59Z", stale_export["export_id"]),
            )
        stale_delete = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/exports/{stale_export['export_id']}",
            json=_delete_body(
                analysis_id,
                stale_export["export_id"],
                preflight["deletion_manifest_sha256"],
            ),
        )

    assert path_error.status_code == 409
    assert path_error.json()["error"]["code"] == "analysis_export_path_invalid"
    assert checksum_error.status_code == 409
    assert checksum_error.json()["error"]["code"] == "analysis_export_checksum_mismatch"
    assert media_error.status_code == 409
    assert media_error.json()["error"]["code"] == "analysis_export_metadata_invalid"
    assert stale_delete.status_code == 409
    assert stale_delete.json()["error"]["code"] == (
        "analysis_export_deletion_confirmation_mismatch"
    )
    for response in (path_error, checksum_error, media_error, stale_delete):
        assert str(tmp_path) not in response.text
        assert "outside.json" not in response.text


def test_quarantine_failure_and_metadata_conflict_preserve_export(tmp_path, monkeypatch) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis = _create_analysis(client)
        analysis_id = analysis["analysis_id"]
        locked_export = _create_export(client, analysis_id)
        locked_artifact = get_analysis_artifact_record(
            tmp_path, analysis_id, locked_export["export_id"]
        )
        assert locked_artifact is not None
        locked_path = tmp_path / locked_artifact.path
        locked_preflight = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{locked_export['export_id']}/deletion-preflight"
        ).json()

        real_replace = os.replace

        def deny_quarantine(source: Path, target: Path) -> None:
            if str(target).endswith(".quarantine"):
                raise PermissionError("locked")
            real_replace(source, target)

        monkeypatch.setattr(analysis_run_exports.os, "replace", deny_quarantine)
        locked_delete = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/exports/{locked_export['export_id']}",
            json=_delete_body(
                analysis_id,
                locked_export["export_id"],
                locked_preflight["deletion_manifest_sha256"],
            ),
        )
        monkeypatch.setattr(analysis_run_exports.os, "replace", real_replace)

        conflict_export = _create_export(client, analysis_id, "csv")
        conflict_artifact = get_analysis_artifact_record(
            tmp_path, analysis_id, conflict_export["export_id"]
        )
        assert conflict_artifact is not None
        conflict_path = tmp_path / conflict_artifact.path
        conflict_preflight = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{conflict_export['export_id']}/deletion-preflight"
        ).json()

        def conflict(*args, **kwargs) -> None:
            raise AnalysisArtifactStorageConflict("analysis_export_deletion_conflict")

        monkeypatch.setattr(analysis_run_exports, "delete_analysis_artifact_record", conflict)
        conflict_delete = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/exports/{conflict_export['export_id']}",
            json=_delete_body(
                analysis_id,
                conflict_export["export_id"],
                conflict_preflight["deletion_manifest_sha256"],
            ),
        )

    assert locked_delete.status_code == 409
    assert locked_delete.json()["error"]["code"] == "analysis_export_quarantine_failed"
    assert locked_path.exists()
    assert get_analysis_artifact_record(tmp_path, analysis_id, locked_export["export_id"])
    assert conflict_delete.status_code == 409
    assert conflict_delete.json()["error"]["code"] == "analysis_export_deletion_conflict"
    assert conflict_path.exists()
    assert not list(conflict_path.parent.glob(".delete-*.quarantine"))


def test_committed_quarantine_cleanup_is_recovered_on_next_startup(tmp_path, monkeypatch) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis = _create_analysis(client)
        analysis_id = analysis["analysis_id"]
        export = _create_export(client, analysis_id)
        artifact = get_analysis_artifact_record(tmp_path, analysis_id, export["export_id"])
        assert artifact is not None
        export_path = tmp_path / artifact.path
        restore_export = _create_export(client, analysis_id, "csv")
        restore_artifact = get_analysis_artifact_record(
            tmp_path, analysis_id, restore_export["export_id"]
        )
        assert restore_artifact is not None
        restore_path = tmp_path / restore_artifact.path
        restore_quarantine_path = restore_path.with_name(
            f".delete-{restore_export['export_id']}-{uuid4().hex}.quarantine"
        )
        os.replace(restore_path, restore_quarantine_path)
        tampered_export = _create_export(client, analysis_id, "html")
        tampered_artifact = get_analysis_artifact_record(
            tmp_path, analysis_id, tampered_export["export_id"]
        )
        assert tampered_artifact is not None
        tampered_path = tmp_path / tampered_artifact.path
        tampered_quarantine_path = tampered_path.with_name(
            f".delete-{tampered_export['export_id']}-{uuid4().hex}.quarantine"
        )
        os.replace(tampered_path, tampered_quarantine_path)
        tampered_quarantine_path.write_bytes(b"tampered quarantine")
        preflight = client.get(
            f"/api/v1/analysis-runs/{analysis_id}/exports/"
            f"{export['export_id']}/deletion-preflight"
        ).json()
        real_unlink = Path.unlink

        def deny_quarantine_unlink(path: Path, *args, **kwargs) -> None:
            if path.name.endswith(".quarantine"):
                raise PermissionError("cleanup pending")
            real_unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", deny_quarantine_unlink)
        deleted = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/exports/{export['export_id']}",
            json=_delete_body(
                analysis_id,
                export["export_id"],
                preflight["deletion_manifest_sha256"],
            ),
        )
        quarantine_files = list(export_path.parent.glob(".delete-*.quarantine"))

    assert deleted.status_code == 200
    assert deleted.json()["cleanup_status"] == "quarantined_pending_cleanup"
    assert not export_path.exists()
    assert get_analysis_artifact_record(tmp_path, analysis_id, export["export_id"]) is None
    assert len(quarantine_files) == 3

    monkeypatch.setattr(Path, "unlink", real_unlink)
    with TestClient(create_app(settings)) as client:
        recovery = client.app.state.analysis_export_quarantine_recovery
        export_list = client.get(f"/api/v1/analysis-runs/{analysis_id}/exports")

    assert recovery.deleted_file_count == 1
    assert recovery.restored_file_count == 1
    assert recovery.pending_file_count == 1
    assert sum(path.exists() for path in quarantine_files) == 1
    assert restore_path.exists()
    assert not restore_quarantine_path.exists()
    assert not tampered_path.exists()
    assert tampered_quarantine_path.exists()
    assert export_list.status_code == 200
    assert {item["export_id"] for item in export_list.json()["exports"]} == {
        restore_export["export_id"],
        tampered_export["export_id"],
    }
