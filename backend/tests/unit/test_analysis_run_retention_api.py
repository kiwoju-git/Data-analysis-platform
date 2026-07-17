import json
import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

import app.services.analysis_run_retention as analysis_run_retention
from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import (
    AnalysisRunStorageConflict,
    AttributeControlLimitSetRecord,
    JobRecord,
    get_analysis_run_record,
    insert_attribute_control_limit_set_record,
    insert_job_record,
    list_analysis_artifact_records,
    metadata_db_path,
)


def _create_analysis(client: TestClient) -> dict[str, object]:
    upload = client.post(
        "/api/v1/datasets",
        files={"file": ("retention.csv", b"value\n1\n2\n3\n", "text/csv")},
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
    assert confirmed.status_code == 201
    version = confirmed.json()
    analysis = client.post(
        "/api/v1/analysis-runs",
        json={
            "method_id": "eda.descriptive",
            "method_version": "0.1.0",
            "dataset_version_id": version["version_id"],
            "roles": {},
            "options": {
                "column_ids": [version["columns"][0]["column_id"]],
                "missing_policy": "available_case_by_column",
            },
        },
    )
    assert analysis.status_code == 201, analysis.text
    return {
        **analysis.json(),
        "dataset_id": dataset_id,
        "dataset_version_id": version["version_id"],
        "column_id": version["columns"][0]["column_id"],
    }


def _create_export(client: TestClient, analysis_id: str, format_name: str) -> dict:
    response = client.post(f"/api/v1/analysis-runs/{analysis_id}/exports/{format_name}")
    assert response.status_code == 201, response.text
    return response.json()


def _delete_body(analysis_id: str, manifest_sha256: str) -> dict[str, str]:
    return {
        "confirmation_analysis_id": analysis_id,
        "expected_deletion_manifest_sha256": manifest_sha256,
    }


def test_analysis_run_deletion_removes_owned_result_snapshot_and_exports_only(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        analysis = _create_analysis(client)
        retained = _create_analysis(client)
        analysis_id = str(analysis["analysis_id"])
        for format_name in ("json", "csv", "html"):
            _create_export(client, analysis_id, format_name)
        run = get_analysis_run_record(tmp_path, analysis_id)
        artifacts = list_analysis_artifact_records(tmp_path, analysis_id)
        assert run is not None
        owned_paths = [tmp_path / run.result_path] if run.result_path else []
        owned_paths.extend(tmp_path / artifact.path for artifact in artifacts)
        owned_file_bytes = sum(path.stat().st_size for path in owned_paths)

        preflight_response = client.get(f"/api/v1/analysis-runs/{analysis_id}/deletion-preflight")
        preflight = preflight_response.json()
        wrong_confirmation = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/deletion",
            json=_delete_body(str(uuid4()), preflight["deletion_manifest_sha256"]),
        )
        deleted = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/deletion",
            json=_delete_body(analysis_id, preflight["deletion_manifest_sha256"]),
        )
        deleted_status = client.get(f"/api/v1/analysis-runs/{analysis_id}")
        deleted_result = client.get(f"/api/v1/analysis-runs/{analysis_id}/result")
        retained_result = client.get(f"/api/v1/analysis-runs/{retained['analysis_id']}/result")

    assert preflight_response.status_code == 200
    assert preflight["deletion_ready"] is True
    assert preflight["blockers"] == []
    assert preflight["counts"] == {
        "analysis_run_count": 1,
        "analysis_artifact_count": 4,
        "result_file_count": 1,
        "artifact_file_count": 4,
        "export_file_count": 3,
        "total_file_count": 5,
        "file_bytes": owned_file_bytes,
        "metadata_record_count": 5,
        "regression_model_count": 0,
        "regression_prediction_count": 0,
        "attribute_control_limit_set_count": 0,
        "job_reference_count": 0,
    }
    assert str(tmp_path) not in json.dumps(preflight)
    assert wrong_confirmation.status_code == 409
    assert wrong_confirmation.json()["error"]["code"] == (
        "analysis_run_deletion_confirmation_mismatch"
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_counts"] == preflight["counts"]
    assert deleted.json()["cleanup_status"] == "deleted"
    assert get_analysis_run_record(tmp_path, analysis_id) is None
    assert list_analysis_artifact_records(tmp_path, analysis_id) == []
    assert not any(path.exists() for path in owned_paths)
    assert deleted_status.status_code == 404
    assert deleted_result.status_code == 404
    assert retained_result.status_code == 200


def test_analysis_run_deletion_rejects_tamper_and_stale_confirmation(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        path_analysis = _create_analysis(client)
        path_id = str(path_analysis["analysis_id"])
        snapshot = next(
            artifact
            for artifact in list_analysis_artifact_records(tmp_path, path_id)
            if artifact.kind == "analysis_row_snapshot"
        )
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute(
                "UPDATE analysis_artifacts SET path = ? WHERE artifact_id = ?;",
                ("outside.json", snapshot.artifact_id),
            )
        path_error = client.get(f"/api/v1/analysis-runs/{path_id}/deletion-preflight")

        checksum_analysis = _create_analysis(client)
        checksum_id = str(checksum_analysis["analysis_id"])
        checksum_run = get_analysis_run_record(tmp_path, checksum_id)
        assert checksum_run is not None and checksum_run.result_path is not None
        (tmp_path / checksum_run.result_path).write_bytes(b"tampered result")
        checksum_error = client.get(f"/api/v1/analysis-runs/{checksum_id}/deletion-preflight")

        stale_analysis = _create_analysis(client)
        stale_id = str(stale_analysis["analysis_id"])
        preflight = client.get(f"/api/v1/analysis-runs/{stale_id}/deletion-preflight").json()
        _create_export(client, stale_id, "json")
        stale_delete = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{stale_id}/deletion",
            json=_delete_body(stale_id, preflight["deletion_manifest_sha256"]),
        )

    assert path_error.status_code == 409
    assert path_error.json()["error"]["code"] == "analysis_run_artifact_path_invalid"
    assert checksum_error.status_code == 409
    assert checksum_error.json()["error"]["code"] == ("analysis_run_file_checksum_mismatch")
    assert stale_delete.status_code == 409
    assert stale_delete.json()["error"]["code"] == ("analysis_run_deletion_confirmation_mismatch")
    for response in (path_error, checksum_error, stale_delete):
        assert str(tmp_path) not in response.text
        assert "outside.json" not in response.text


def test_analysis_run_deletion_reports_model_limit_set_and_job_blockers(tmp_path) -> None:
    settings = Settings(workspace_root=tmp_path)
    created_at = "2026-07-17T00:00:00.000Z"
    with TestClient(create_app(settings)) as client:
        model_analysis = _create_analysis(client)
        model_id = str(model_analysis["analysis_id"])
        prediction_analysis = _create_analysis(client)
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON;")
            connection.execute(
                """
                INSERT INTO regression_models (
                    model_id, analysis_id, dataset_version_id, method_id, method_version,
                    manifest_path, manifest_sha256, schema_hash, created_at, app_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(uuid4()),
                    model_id,
                    model_analysis["dataset_version_id"],
                    "regression.linear_model",
                    "0.2.0",
                    f"workspaces/analyses/{model_id}/model.json",
                    "0" * 64,
                    "1" * 64,
                    created_at,
                    "0.1.0",
                ),
            )
            connection.execute(
                "UPDATE analysis_runs SET method_id = ?, config_json = ? WHERE analysis_id = ?;",
                (
                    "regression.predict",
                    json.dumps({"source_analysis_id": model_id}),
                    prediction_analysis["analysis_id"],
                ),
            )
        model_preflight = client.get(f"/api/v1/analysis-runs/{model_id}/deletion-preflight")

        limit_analysis = _create_analysis(client)
        limit_id = str(limit_analysis["analysis_id"])
        insert_attribute_control_limit_set_record(
            tmp_path,
            AttributeControlLimitSetRecord(
                limit_set_id=str(uuid4()),
                source_analysis_id=limit_id,
                source_dataset_version_id=str(limit_analysis["dataset_version_id"]),
                asset_schema_version=1,
                method_id="quality.attribute_control_chart",
                source_method_version="0.2.0",
                phase2_method_version="0.2.0",
                chart_type="c",
                count_definition="defects",
                count_column_id=str(limit_analysis["column_id"]),
                denominator_column_id=None,
                source_schema_hash="2" * 64,
                source_canonical_sha256="3" * 64,
                source_config_sha256="4" * 64,
                source_result_sha256="5" * 64,
                filter_snapshot_sha256="6" * 64,
                row_snapshot_sha256="7" * 64,
                baseline_point_count=3,
                total_count=6,
                total_denominator=None,
                center_line=2.0,
                fixed_sample_size=None,
                constant_opportunity_confirmed=True,
                sigma_multiplier=3.0,
                calculation_policy="phase_1",
                natural_bound_policy="nonnegative",
                asset_path=f"quality/attribute-control-limit-sets/{uuid4()}.json",
                asset_sha256="8" * 64,
                created_at=created_at,
                closed_at=created_at,
                app_version="0.1.0",
            ),
        )
        limit_preflight = client.get(f"/api/v1/analysis-runs/{limit_id}/deletion-preflight")

        job_analysis = _create_analysis(client)
        job_id = str(job_analysis["analysis_id"])
        insert_job_record(
            tmp_path,
            JobRecord(
                job_id=str(uuid4()),
                analysis_id=job_id,
                job_type="analysis",
                state="succeeded",
                progress=1.0,
                cancel_requested=False,
                error_code=None,
                created_at=created_at,
                updated_at=created_at,
                completed_at=created_at,
            ),
        )
        job_preflight = client.get(f"/api/v1/analysis-runs/{job_id}/deletion-preflight")

    assert model_preflight.status_code == 200
    assert model_preflight.json()["deletion_ready"] is False
    assert model_preflight.json()["blockers"] == [
        "analysis_run_deletion_regression_model_dependency",
        "analysis_run_deletion_regression_prediction_dependency",
    ]
    assert model_preflight.json()["counts"]["regression_model_count"] == 1
    assert model_preflight.json()["counts"]["regression_prediction_count"] == 1
    assert limit_preflight.status_code == 200
    assert limit_preflight.json()["blockers"] == ["analysis_run_deletion_limit_set_dependency"]
    assert limit_preflight.json()["counts"]["attribute_control_limit_set_count"] == 1
    assert job_preflight.status_code == 200
    assert job_preflight.json()["blockers"] == ["analysis_run_deletion_job_dependency"]
    assert job_preflight.json()["counts"]["job_reference_count"] == 1


def test_analysis_run_quarantine_and_metadata_failures_restore_every_file(
    tmp_path, monkeypatch
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        move_analysis = _create_analysis(client)
        move_id = str(move_analysis["analysis_id"])
        _create_export(client, move_id, "json")
        move_run = get_analysis_run_record(tmp_path, move_id)
        assert move_run is not None and move_run.result_path is not None
        move_paths = [tmp_path / move_run.result_path]
        move_paths.extend(
            tmp_path / artifact.path
            for artifact in list_analysis_artifact_records(tmp_path, move_id)
        )
        move_preflight = client.get(f"/api/v1/analysis-runs/{move_id}/deletion-preflight").json()
        real_replace = os.replace
        quarantine_move_count = 0

        def fail_second_quarantine(source: Path, target: Path) -> None:
            nonlocal quarantine_move_count
            if target.name.startswith(".delete-"):
                quarantine_move_count += 1
                if quarantine_move_count == 2:
                    raise PermissionError("locked")
            real_replace(source, target)

        monkeypatch.setattr(analysis_run_retention.os, "replace", fail_second_quarantine)
        move_error = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{move_id}/deletion",
            json=_delete_body(move_id, move_preflight["deletion_manifest_sha256"]),
        )
        monkeypatch.setattr(analysis_run_retention.os, "replace", real_replace)

        conflict_analysis = _create_analysis(client)
        conflict_id = str(conflict_analysis["analysis_id"])
        _create_export(client, conflict_id, "csv")
        conflict_run = get_analysis_run_record(tmp_path, conflict_id)
        assert conflict_run is not None and conflict_run.result_path is not None
        conflict_paths = [tmp_path / conflict_run.result_path]
        conflict_paths.extend(
            tmp_path / artifact.path
            for artifact in list_analysis_artifact_records(tmp_path, conflict_id)
        )
        conflict_preflight = client.get(
            f"/api/v1/analysis-runs/{conflict_id}/deletion-preflight"
        ).json()

        def conflict(*args, **kwargs) -> None:
            raise AnalysisRunStorageConflict("analysis_run_deletion_conflict")

        monkeypatch.setattr(analysis_run_retention, "delete_analysis_run_record", conflict)
        conflict_error = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{conflict_id}/deletion",
            json=_delete_body(conflict_id, conflict_preflight["deletion_manifest_sha256"]),
        )

    assert move_error.status_code == 409
    assert move_error.json()["error"]["code"] == "analysis_run_quarantine_failed"
    assert all(path.exists() for path in move_paths)
    assert get_analysis_run_record(tmp_path, move_id) is not None
    assert conflict_error.status_code == 409, conflict_error.text
    assert conflict_error.json()["error"]["code"] == "analysis_run_deletion_conflict"
    assert all(path.exists() for path in conflict_paths)
    assert get_analysis_run_record(tmp_path, conflict_id) is not None
    assert not list(tmp_path.glob("workspaces/analyses/*/.delete-*"))


def test_analysis_run_quarantine_recovery_restores_or_cleans_by_metadata_state(
    tmp_path, monkeypatch
) -> None:
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        restore_analysis = _create_analysis(client)
        restore_id = str(restore_analysis["analysis_id"])
        restore_run = get_analysis_run_record(tmp_path, restore_id)
        restore_artifacts = list_analysis_artifact_records(tmp_path, restore_id)
        assert restore_run is not None and restore_run.result_path is not None
        snapshot = restore_artifacts[0]
        result_path = tmp_path / restore_run.result_path
        snapshot_path = tmp_path / snapshot.path
        result_quarantine = result_path.with_name(f".delete-r-{uuid4().hex[:16]}.q")
        snapshot_quarantine = snapshot_path.with_name(
            f".delete-a-{snapshot.artifact_id}-{uuid4().hex[:16]}.q"
        )
        assert result_path.exists(), list(result_path.parent.glob("*"))
        os.replace(result_path, result_quarantine)
        os.replace(snapshot_path, snapshot_quarantine)

    with TestClient(create_app(settings)) as client:
        restore_recovery = client.app.state.analysis_run_quarantine_recovery
        restored_result = client.get(f"/api/v1/analysis-runs/{restore_id}/result")

    assert restore_recovery.restored_file_count == 2
    assert restore_recovery.deleted_file_count == 0
    assert restore_recovery.pending_file_count == 0
    assert result_path.exists() and snapshot_path.exists()
    assert restored_result.status_code == 200

    with TestClient(create_app(settings)) as client:
        delete_analysis = _create_analysis(client)
        delete_id = str(delete_analysis["analysis_id"])
        _create_export(client, delete_id, "json")
        preflight = client.get(f"/api/v1/analysis-runs/{delete_id}/deletion-preflight").json()
        real_unlink = Path.unlink

        def deny_quarantine_unlink(path: Path, *args, **kwargs) -> None:
            if path.name.startswith(".delete-"):
                raise PermissionError("cleanup pending")
            real_unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", deny_quarantine_unlink)
        deleted = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{delete_id}/deletion",
            json=_delete_body(delete_id, preflight["deletion_manifest_sha256"]),
        )
        pending_quarantines = list(
            (tmp_path / "workspaces" / "analyses" / delete_id).rglob(".delete-*")
        )

    assert deleted.status_code == 200
    assert deleted.json()["cleanup_status"] == "quarantined_pending_cleanup"
    assert len(pending_quarantines) == 3, [path.name for path in pending_quarantines]
    monkeypatch.setattr(Path, "unlink", real_unlink)

    with TestClient(create_app(settings)) as client:
        export_recovery = client.app.state.analysis_export_quarantine_recovery
        run_recovery = client.app.state.analysis_run_quarantine_recovery

    assert export_recovery.deleted_file_count == 0
    assert run_recovery.deleted_file_count == 3
    assert run_recovery.restored_file_count == 0
    assert run_recovery.pending_file_count == 0
    assert not any(path.exists() for path in pending_quarantines)
