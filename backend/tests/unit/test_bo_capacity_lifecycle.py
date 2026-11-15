"""Real imported-study fit, saved model, report, and bounded confirmation paths."""

import hashlib
import sqlite3
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.metadata import metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import study_request, url
from tests.unit.test_bayesian_study_lifecycle_api import _close_request
from tests.unit.test_bo_candidates_v2 import request as candidate_request
from tests.unit.test_bo_capacity import process_peak_bytes
from tests.unit.test_bo_dataset_import_api import ROOT, commit_request, import_request, preflight
from tests.unit.test_bo_dataset_import_reports import _managed_report
from tests.unit.test_bo_planning_api import fit_request


def imported_vector(client, count):
    rows = [f"{10*i/count},{20+30*i/count},{5-i/count}" for i in range(count)]
    body, version = import_request(client, ("x,y,cost\n" + "\n".join(rows) + "\n").encode())
    body["objective"] = study_request()["objective"]
    body["response_mappings"] = [
        {"column_id": version["columns"][1]["column_id"], "response_id": "yield"},
        {"column_id": version["columns"][2]["column_id"], "response_id": "cost"},
    ]
    result = client.post(ROOT + "/from-dataset", json=commit_request(body, preflight(client, body)))
    assert result.status_code == 201, result.text
    return result.json()


def test_500_mixed_import_reader_and_stored_report_preserve_observations(tmp_path):
    from tests.unit.test_bo_mixed_studies import request as mixed_request

    content = (
        "x,y,kind\n"
        + "\n".join(f"{i % 10},{i % 5},{'A' if i % 2 else 'B'}" for i in range(500))
        + "\n"
    )
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, version = import_request(client, content.encode())
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
        study = response.json()
        assert study["trial_count"] == 500
        assert client.get(url(study)).json() == study
        assert len(_managed_report(client, study)["observations"]) == 500


@pytest.mark.parametrize("count", [240, 500])
def test_imported_exact_model_saved_prediction_report_close_and_backup(tmp_path, count):
    settings = Settings(workspace_root=tmp_path / "synthetic workspace")
    with TestClient(create_app(settings)) as client:
        study = imported_vector(client, count)
        fit = fit_request(study)
        fit["fit"]["total_trial_budget"] = 500
        fit["fit"]["search"]["model_max_iterations"] = 3
        fit["fit"]["search"]["model_max_evaluations"] = 300
        fit["fit"]["search"]["time_budget_ms"] = 60000
        for response in fit["fit"]["response_models"]:
            response["surrogate"] = {"noise_mode": "fixed", "fixed_noise_sd": 0.1}
        started = time.perf_counter()
        result = client.post(url(study) + "/planning-models", json=fit)
        assert result.status_code == 201, result.text
        model = result.json()
        elapsed = time.perf_counter() - started
        endpoint = url(study) + f"/planning-models/{model['model_id']}"
        evaluation = {
            "expected_model_sha256": model["snapshot_sha256"],
            "points": [{"x": 2.123}, {"x": 7.777}],
        }
        predicted = client.post(endpoint + "/evaluate", json=evaluation)
        assert predicted.status_code == 200, predicted.text
        assert predicted.json()["model_refit"] is False
        assert (
            _managed_report(client, study)["definition"]["initial_design"]["generated_size"]
            == count
        )
        closed = client.post(
            url(study) + "/close",
            json=_close_request(
                study, target_status="abandoned", reason_code="resources_unavailable"
            ),
        )
        assert closed.status_code == 200, closed.text
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as db:
            snapshot, digest = db.execute(
                "SELECT snapshot_json,snapshot_sha256 FROM bayesian_planning_models "
                "WHERE model_id=?",
                (model["model_id"],),
            ).fetchone()
        assert hashlib.sha256(snapshot.encode()).hexdigest() == digest
        print(
            f"capacity_public n={count} fit_seconds={elapsed:.3f} "
            f"snapshot_bytes={len(snapshot.encode())} process_peak_bytes={process_peak_bytes()}"
        )
    archive, restored = tmp_path / "backup.tar.gz", tmp_path / "restored workspace"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, restored)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        assert client.get(endpoint).status_code == 200
        again = client.post(endpoint + "/evaluate", json=evaluation)
        assert again.status_code == 200, again.text
        assert again.json()["items"] == predicted.json()["items"]
        assert client.get(url(study)).json()["completed_trial_count"] == count
    with sqlite3.connect(metadata_db_path(restored)) as db:
        assert db.execute(
            "SELECT snapshot_json,snapshot_sha256 FROM bayesian_planning_models WHERE model_id=?",
            (model["model_id"],),
        ).fetchone() == (snapshot, digest)


def test_499_rejects_two_atomically_accepts_one_then_500_rejects_next(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = imported_vector(client, 499)
        request = candidate_request(study)
        request["source"]["points"] = [{"x": 9.99}, {"x": 9.999}]
        candidate = client.post(url(study) + "/candidate-revisions", json=request)
        assert candidate.status_code == 201, candidate.text
        revision = candidate.json()["revision"]
        base = {
            key: request[key]
            for key in (
                "schema_version",
                "expected_study_version_id",
                "expected_definition_sha256",
                "expected_history_revision_id",
                "expected_history_sha256",
                "expected_trial_count",
                "model_id",
                "expected_model_sha256",
            )
        }
        base.update(
            candidate_revision_id=revision["revision_id"],
            expected_rows_sha256=revision["rows_sha256"],
            policy="greedy_mixed_maximin_v1",
            total_trial_budget=500,
        )
        two = client.post(
            url(study) + "/augmentations", json=base | {"request_id": str(uuid4()), "batch_size": 2}
        )
        assert two.status_code == 409, two.text
        assert client.get(url(study)).json()["trial_count"] == 499
        one = client.post(
            url(study) + "/augmentations", json=base | {"request_id": str(uuid4()), "batch_size": 1}
        )
        assert one.status_code == 201, one.text
        selection = one.json()
        confirmed = client.post(
            url(study) + f"/augmentations/{selection['selection_id']}/confirm",
            json={
                "expected_config_sha256": selection["config_sha256"],
                "expected_result_sha256": selection["result_sha256"],
            },
        )
        assert confirmed.status_code == 201, confirmed.text
        current = client.get(url(study)).json()
        assert current["trial_count"] == 500 and current["pending_trial_count"] == 1
        base["expected_trial_count"] = 500
        rejected = client.post(
            url(study) + "/augmentations", json=base | {"request_id": str(uuid4()), "batch_size": 1}
        )
        assert rejected.status_code == 409, rejected.text
        assert client.get(url(study)).json()["trial_count"] == 500
