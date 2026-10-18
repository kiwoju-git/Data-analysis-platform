from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict, replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_analysis_run_retention_api import _create_analysis
from test_completed_predictions import _model

from app.core.config import Settings
from app.main import create_app
from app.services.workspace_asset_retention import recover_workspace_asset_quarantine_files
from app.storage import source_bound_artifacts as storage
from app.storage.metadata import (
    AnalysisArtifactRecord,
    get_analysis_run_record,
    list_analysis_artifact_records,
    metadata_db_path,
)


@pytest.fixture
def source(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        analysis = _create_analysis(client)
    run = get_analysis_run_record(tmp_path, analysis["analysis_id"])
    assert run is not None
    return tmp_path, run


def _record(run, kind="managed_source_html_report", content=b"<h1>stored</h1>"):
    artifact_id = str(uuid4())
    suffix = (
        "managed-report.html"
        if kind == "managed_source_html_report"
        else "completed-prediction.json"
    )
    return AnalysisArtifactRecord(
        artifact_id=artifact_id,
        analysis_id=run.analysis_id,
        kind=kind,
        path=f"workspaces/analyses/{run.analysis_id}/exports/{artifact_id}.{suffix}",
        sha256=hashlib.sha256(content).hexdigest(),
        media_type="text/html" if kind == "managed_source_html_report" else "application/json",
        created_at="2026-10-18T00:00:00Z",
    )


def _insert(root, run, record, content=b"<h1>stored</h1>"):
    storage.insert_source_bound_artifact(
        root, record, content, expected_source_sha256=run.result_sha256
    )


@pytest.mark.parametrize("kind", list(storage._KINDS))
def test_exact_kind_path_roundtrip_and_no_journal(source, kind):
    root, run = source
    record = _record(run, kind)
    _insert(root, run, record)
    assert storage.read_source_bound_artifact(root, record) == b"<h1>stored</h1>"
    assert record in list_analysis_artifact_records(root, run.analysis_id)
    assert not list((root / "workspaces").rglob("*.source-bound.json"))


@pytest.mark.parametrize("fault", ["before_commit", "after_commit"])
def test_process_crash_recovery_preserves_only_committed_record(source, fault):
    root, run = source
    record = _record(run)
    script = """
import json, os, sys
from pathlib import Path
from app.storage import source_bound_artifacts as s
from app.storage.metadata import AnalysisArtifactRecord
root, record, expected, fault = sys.argv[1:]
record = AnalysisArtifactRecord(**json.loads(record))
if fault == 'before_commit':
    s._insert_record = lambda *args: os._exit(73)
else:
    s._remove_journal = lambda *args: os._exit(74)
s.insert_source_bound_artifact(
    Path(root), record, b'<h1>stored</h1>', expected_source_sha256=expected
)
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(root),
            json.dumps(asdict(record)),
            run.result_sha256,
            fault,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == (73 if fault == "before_commit" else 74), completed.stderr
    path = storage._record_path(root, record)
    assert path.is_file()
    assert path.with_name(f".create-{record.artifact_id}.source-bound.json").is_file()
    result = recover_workspace_asset_quarantine_files(root)
    assert result.pending_file_count == 0
    assert result.deleted_file_count == (fault == "before_commit")
    assert result.restored_file_count == (fault == "after_commit")
    assert path.exists() == (fault == "after_commit")
    assert (record in list_analysis_artifact_records(root, run.analysis_id)) == (
        fault == "after_commit"
    )
    assert storage.recover_source_bound_artifact_files(root) == (0, 0, 0)


def test_sql_failure_rolls_back_file_and_preserves_other_artifacts(source):
    root, run = source
    first = _record(run)
    _insert(root, run, first)
    second = _record(run)
    with sqlite3.connect(metadata_db_path(root)) as connection:
        connection.execute(
            "CREATE TRIGGER fail_new_report BEFORE INSERT ON analysis_artifacts "
            "BEGIN SELECT RAISE(ABORT,'injected'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="injected"):
        _insert(root, run, second)
    assert not storage._record_path(root, second).exists()
    assert storage.read_source_bound_artifact(root, first) == b"<h1>stored</h1>"
    assert storage.recover_source_bound_artifact_files(root) == (0, 0, 0)


def test_unregistered_existing_file_never_overwritten(source):
    root, run = source
    record = _record(run)
    path = storage._record_path(root, record)
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not owned by this operation")
    with pytest.raises(storage.SourceBoundArtifactError, match="stored_report_artifact_exists"):
        _insert(root, run, record)
    assert path.read_bytes() == b"not owned by this operation"


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", "../outside.html"),
        ("kind", "analysis_result_html_report"),
        ("media_type", "application/octet-stream"),
        ("artifact_id", "not-an-id"),
    ],
)
def test_record_contract_rejects_arbitrary_paths_and_kinds(source, field, value):
    root, run = source
    with pytest.raises(storage.SourceBoundArtifactError, match="stored_report_artifact_invalid"):
        _insert(root, run, replace(_record(run), **{field: value}))


@pytest.mark.parametrize("fault", ["truncated", "tampered", "wrong_owner", "registered_changed"])
def test_recovery_never_deletes_unverified_marker_or_content(source, monkeypatch, fault):
    root, run = source
    record = _record(run)
    monkeypatch.setattr(
        storage, "_remove_journal", lambda path: (_ for _ in ()).throw(OSError("busy"))
    )
    _insert(root, run, record)
    monkeypatch.undo()
    path = storage._record_path(root, record)
    marker = path.with_name(f".create-{record.artifact_id}.source-bound.json")
    if fault == "truncated":
        path.write_bytes(b"partial")
    elif fault == "tampered":
        marker.write_bytes(b'{"schema_version":1}')
    elif fault == "wrong_owner":
        payload = json.loads(marker.read_bytes())
        payload["record"]["analysis_id"] = str(uuid4())
        marker.write_text(json.dumps(payload), encoding="utf-8")
    else:
        with sqlite3.connect(metadata_db_path(root)) as connection:
            connection.execute(
                "UPDATE analysis_artifacts SET created_at='changed' WHERE artifact_id=?",
                (record.artifact_id,),
            )
    assert storage.recover_source_bound_artifact_files(root) == (0, 0, 1)
    assert path.is_file() and marker.is_file()


def test_source_and_dependency_cas_before_any_file_write(source):
    root, run = source
    record = _record(run)
    with pytest.raises(storage.SourceBoundArtifactError, match="stored_report_source_changed"):
        storage.insert_source_bound_artifact(
            root, record, b"<h1>stored</h1>", expected_source_sha256="f" * 64
        )
    with pytest.raises(
        storage.SourceBoundArtifactError, match="completed_prediction_source_changed"
    ):
        storage.insert_source_bound_artifact(
            root,
            record,
            b"<h1>stored</h1>",
            expected_source_sha256=run.result_sha256,
            dependency_artifact=(str(uuid4()), "a" * 64),
        )
    assert not storage._record_path(root, record).exists()
    assert storage.recover_source_bound_artifact_files(root) == (0, 0, 0)


def test_hard_link_rejected_for_completed_read(source):
    root, run = source
    record = _record(run)
    _insert(root, run, record)
    path = storage._record_path(root, record)
    os.link(path, root / "retained-link")
    with pytest.raises(storage.SourceBoundArtifactError, match="stored_report_artifact_invalid"):
        storage.read_source_bound_artifact(root, record)


def test_recovery_does_not_traverse_linked_owner_directory(source, monkeypatch):
    root, _ = source
    outside = root / "outside-owner"
    (outside / "exports").mkdir(parents=True)
    marker = outside / "exports" / ".create-outside.source-bound.json"
    marker.write_bytes(b"outside marker")
    link = root / "workspaces" / "analyses" / str(uuid4())
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege unavailable")
        raise

    def forbidden(*args):
        raise AssertionError("linked owner must not be traversed")

    monkeypatch.setattr(storage, "_recover_journal", forbidden)
    assert storage.recover_source_bound_artifact_files(root) == (0, 0, 1)
    assert marker.read_bytes() == b"outside marker"


@pytest.mark.parametrize("family", ["pls", "gaussian_process"])
def test_actual_prediction_report_owner_cascade_after_explicit_model_deletion(tmp_path, family):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        analysis, pointer, body, url = _model(client, family)
        saved = client.post(url, json={**body, "save_result": True})
        assert saved.status_code == 200, saved.text
        source_ref = saved.json()["saved_prediction"]["source"]
        capability = client.post(
            "/api/v1/reports/capability", json={"source": source_ref, "locale": "en"}
        )
        assert capability.status_code == 200, capability.text
        exported = client.post(
            "/api/v1/reports",
            json={
                "source": source_ref,
                "locale": "en",
                "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
            },
        )
        assert exported.status_code == 201, exported.text
        analysis_id = analysis["analysis_id"]
        model_id = pointer["model_id"]
        owned = list_analysis_artifact_records(tmp_path, analysis_id)
        assert {
            "managed_source_html_report",
            f"{'gp' if family == 'gaussian_process' else 'pls'}_completed_prediction",
        } <= {item.kind for item in owned}
        if family == "gaussian_process":
            numeric = next(
                item for item in owned if item.kind == "gaussian_process_model_numeric_state"
            )
            numeric_path = tmp_path / numeric.path
            original = numeric_path.read_bytes()
            numeric_path.write_bytes(b"not the manifest numeric artifact")
            with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
                connection.execute(
                    "UPDATE analysis_artifacts SET sha256=? WHERE artifact_id=?",
                    (hashlib.sha256(numeric_path.read_bytes()).hexdigest(), numeric.artifact_id),
                )
            corrupt = client.get(f"/api/v1/analysis-runs/{analysis_id}/deletion-preflight")
            assert corrupt.status_code == 409, corrupt.text
            assert corrupt.json()["error"]["code"] == "analysis_run_artifact_metadata_invalid"
            numeric_path.write_bytes(original)
            with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
                connection.execute(
                    "UPDATE analysis_artifacts SET sha256=? WHERE artifact_id=?",
                    (numeric.sha256, numeric.artifact_id),
                )
        blocked = client.get(f"/api/v1/analysis-runs/{analysis_id}/deletion-preflight")
        assert blocked.status_code == 200, blocked.text
        assert blocked.json()["deletion_ready"] is False
        assert "analysis_run_deletion_regression_model_dependency" in blocked.json()["blockers"]
        model_preflight = client.get(f"/api/v1/regression-models/{model_id}/deletion-preflight")
        assert model_preflight.status_code == 200, model_preflight.text
        deleted_model = client.request(
            "DELETE",
            f"/api/v1/regression-models/{model_id}",
            json={
                "confirmation_model_id": model_id,
                "expected_deletion_manifest_sha256": model_preflight.json()[
                    "deletion_manifest_sha256"
                ],
            },
        )
        assert deleted_model.status_code == 200, deleted_model.text
        report_id = exported.json()["export_id"]
        assert client.get(f"/api/v1/reports/{report_id}").status_code == 200
        remaining = list_analysis_artifact_records(tmp_path, analysis_id)
        assert any(item.kind == "managed_source_html_report" for item in remaining)
        assert not any(
            item.kind in {"regression_model_manifest", "gaussian_process_model_numeric_state"}
            for item in remaining
        )
        preflight = client.get(f"/api/v1/analysis-runs/{analysis_id}/deletion-preflight")
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["deletion_ready"] is True
        deleted = client.request(
            "DELETE",
            f"/api/v1/analysis-runs/{analysis_id}/deletion",
            json={
                "confirmation_analysis_id": analysis_id,
                "expected_deletion_manifest_sha256": preflight.json()["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert all(not (tmp_path / item.path).exists() for item in owned)
        assert list_analysis_artifact_records(tmp_path, analysis_id) == []
        assert client.get(f"/api/v1/reports/{report_id}").status_code == 404


def test_completed_prediction_can_be_deleted_without_rewriting_historical_report(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        analysis, _, body, url = _model(client, "pls")
        saved = client.post(url, json={**body, "save_result": True})
        assert saved.status_code == 200, saved.text
        source_ref = saved.json()["saved_prediction"]["source"]
        capability = client.post(
            "/api/v1/reports/capability", json={"source": source_ref, "locale": "en"}
        )
        assert capability.status_code == 200, capability.text
        exported = client.post(
            "/api/v1/reports",
            json={
                "source": source_ref,
                "locale": "en",
                "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
            },
        )
        assert exported.status_code == 201, exported.text
        report = exported.json()
        action = {"source": source_ref, "expected_sha256": report["sha256"]}
        report_url = f"/api/v1/reports/{report['export_id']}"
        original = client.post(report_url + "/download", json=action)
        assert original.status_code == 200, original.text
        analysis_id = analysis["analysis_id"]
        prediction = next(
            item
            for item in list_analysis_artifact_records(tmp_path, analysis_id)
            if item.kind == "pls_completed_prediction"
        )
        export_url = f"/api/v1/analysis-runs/{analysis_id}/exports/{prediction.artifact_id}"
        preflight = client.get(export_url + "/deletion-preflight")
        assert preflight.status_code == 200, preflight.text
        deleted = client.request(
            "DELETE",
            export_url,
            json={
                "confirmation_analysis_id": analysis_id,
                "confirmation_export_id": prediction.artifact_id,
                "expected_deletion_manifest_sha256": preflight.json()["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert client.get(report_url).status_code == 200
        after = client.post(report_url + "/download", json=action)
        assert after.status_code == 200 and after.content == original.content
        unavailable = client.post(
            "/api/v1/reports/capability", json={"source": source_ref, "locale": "en"}
        )
        assert unavailable.status_code == 409, unavailable.text
        assert hashlib.sha256(after.content).hexdigest() == report["sha256"]
