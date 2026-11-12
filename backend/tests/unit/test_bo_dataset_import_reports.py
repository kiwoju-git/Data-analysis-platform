"""Stored-only managed reports for imported observations and generated legacy designs."""

import hashlib
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path
from tests.unit.test_bayesian_multiresponse_lifecycle import study_request
from tests.unit.test_bayesian_studies_api import _study_request
from tests.unit.test_bo_dataset_import_api import ROOT, commit_request, import_request, preflight
from tests.unit.test_bo_mixed_studies import request as mixed_request
from tests.unit.test_dedicated_report_sources import forbidden, no_recompute


def _create_import(client, mode):
    body, version = import_request(
        client,
        b"x,y,kind\n0,1,A\n5,2,B\n5,3,B\n10,4,A\n"
        if mode == "mixed"
        else b"x,y,cost\n0,10,4\n5,20,3\n5,21,2\n10,30,1\n",
    )
    if mode == "vector":
        body["objective"] = study_request()["objective"]
        body["response_mappings"] = [
            {"column_id": version["columns"][1]["column_id"], "response_id": "yield"},
            {"column_id": version["columns"][2]["column_id"], "response_id": "cost"},
        ]
    elif mode == "mixed":
        definition = mixed_request()
        category = definition["factors"][1]
        category["levels"] = ["A", "B"]
        body["factor_mappings"].append(
            {"column_id": version["columns"][2]["column_id"], "factor": category}
        )
        body["objective"] = definition["objective"]
        body["response_mappings"][0]["response_id"] = "yield"
    response = client.post(
        ROOT + "/from-dataset", json=commit_request(body, preflight(client, body))
    )
    assert response.status_code == 201, response.text
    return response.json()


def _source(study):
    return {
        "kind": "bayesian_history_revision",
        "study_id": study["study_id"],
        "study_version_id": study["study_version_id"],
        "definition_sha256": study["definition_sha256"],
        "history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_source_sha256": study["observation_history"]["observation_history_sha256"],
        "attachment": {"kind": "none"},
    }


def _forbid_live_dependencies(monkeypatch):
    no_recompute(monkeypatch)
    for module, name in (
        ("app.services.bo_dataset_import", "get_dataset_rows_context"),
        ("app.services.bo_dataset_import", "iter_dataset_rows"),
        ("app.services.bo_mixed_studies", "load_validated_mixed_study"),
        ("app.services.bo_mixed_studies", "get_mixed_study"),
        ("app.services.bo_planning", "run_planning_operation"),
    ):
        monkeypatch.setattr(module + "." + name, forbidden)


def _source_rows(root):
    with sqlite3.connect(metadata_db_path(root)) as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in (
                "bayesian_study_versions",
                "bayesian_dataset_imports",
                "bayesian_observation_history_revisions",
                "bayesian_trials",
            )
        }


def _append_unrelated_corrupt_trial(root, study):
    with sqlite3.connect(metadata_db_path(root)) as db:
        db.row_factory = sqlite3.Row
        row = dict(
            db.execute(
                "SELECT * FROM bayesian_trials WHERE trial_id=?", (study["trials"][0]["trial_id"],)
            ).fetchone()
        )
        row.update(
            trial_id=str(uuid4()),
            trial_number=study["trial_count"] + 1,
            origin="recommendation",
            state="pending",
            actual_coordinates_json="{}",
            normalized_coordinates_json="{}",
            coordinates_sha256="0" * 64,
            objective_value=None,
            response_values_json=None,
            closed_at=None,
        )
        db.execute(
            f"INSERT INTO bayesian_trials ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()),
        )


def _managed_report(client, study):
    source = _source(study)
    request = {"source": source, "locale": "en"}
    capability = client.post("/api/v1/reports/capability", json=request)
    assert capability.status_code == 200, capability.text
    assert capability.json()["html_available"]
    snapshot = client.post("/api/v1/reports/source-snapshot", json=request)
    assert snapshot.status_code == 200, snapshot.text
    payload = snapshot.json()["payload"]
    assert payload["history"]["history_revision_id"] == source["history_revision_id"]
    assert payload["history"]["observation_history_sha256"] == source["expected_source_sha256"]
    assert len(payload["observations"]) == study["completed_trial_count"]
    exported = client.post(
        "/api/v1/reports",
        json={**request, "expected_source_ref_sha256": capability.json()["source_ref_sha256"]},
    )
    assert exported.status_code == 201, exported.text
    report = exported.json()
    download = client.post(
        "/api/v1/reports/" + report["export_id"] + "/download",
        json={"source": source, "expected_sha256": report["sha256"]},
    )
    assert download.status_code == 200, download.text
    assert hashlib.sha256(download.content).hexdigest() == report["sha256"]
    assert "<script" not in download.text
    return payload


@pytest.mark.parametrize("mode", ["scalar", "vector", "mixed"])
def test_imported_managed_report_reads_only_exact_history_and_initial_receipt(
    tmp_path, monkeypatch, mode
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _create_import(client, mode)
        _append_unrelated_corrupt_trial(tmp_path, study)
        before = _source_rows(tmp_path)
        _forbid_live_dependencies(monkeypatch)
        payload = _managed_report(client, study)
        assert payload["definition"]["initial_design"] == study["initial_design"]
        assert payload["definition"]["initial_design"]["source_row_indices"] == [0, 1, 2, 3]
        assert _source_rows(tmp_path) == before


@pytest.mark.parametrize("mode", ["scalar", "vector", "mixed"])
def test_generated_design_managed_report_retains_legacy_reader_and_hashes(
    tmp_path, monkeypatch, mode
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        request = (
            mixed_request()
            if mode == "mixed"
            else study_request()
            if mode == "vector"
            else _study_request()
        )
        created = client.post(ROOT + ("/mixed" if mode == "mixed" else ""), json=request)
        assert created.status_code == 201, created.text
        study = created.json()
        before = _source_rows(tmp_path)
        _forbid_live_dependencies(monkeypatch)
        payload = _managed_report(client, study)
        assert payload["observations"] == []
        assert (
            payload["definition"]["initial_design"]["policy"] == study["initial_design"]["policy"]
        )
        assert payload["definition"]["initial_design"]["policy"] != "dataset_observations_v1"
        assert _source_rows(tmp_path) == before


@pytest.mark.parametrize("mode", ["scalar", "mixed"])
@pytest.mark.parametrize("corruption", ["ownership", "initial_observation"])
def test_imported_managed_report_rejects_receipt_ownership_or_initial_data_tampering(
    tmp_path, monkeypatch, mode, corruption
):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _create_import(client, mode)
        with sqlite3.connect(metadata_db_path(tmp_path)) as db:
            if corruption == "ownership":
                db.execute(
                    "UPDATE bayesian_dataset_imports SET source_canonical_sha256=? "
                    "WHERE study_version_id=?",
                    ("0" * 64, study["study_version_id"]),
                )
            else:
                db.execute(
                    "UPDATE bayesian_trials SET normalized_coordinates_json='{}' WHERE trial_id=?",
                    (study["trials"][0]["trial_id"],),
                )
        _forbid_live_dependencies(monkeypatch)
        response = client.post("/api/v1/reports/capability", json={"source": _source(study)})
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "report_source_changed"
        assert response.json()["error"]["correlation_id"]
