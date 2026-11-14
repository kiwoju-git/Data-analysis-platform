"""Synthetic exact-source Auto review/confirm/replay/report and offline restore."""

import copy
import hashlib
import json
import re
import sqlite3
from html import unescape
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.bo_planning import planning_json, planning_sha
from app.storage.metadata import metadata_db_path
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import observations, url
from tests.unit.test_bo_candidates_v2 import request
from tests.unit.test_bo_desirability_review_api import completed
from tests.unit.test_bo_planning_api import _database_rows, fit_request


def test_auto_evidence_exact_source_replay_report_and_restore(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "Auto 근거 synthetic workspace")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        fitted = client.post(url(study) + "/planning-models", json=fit_request(study))
        assert fitted.status_code == 201, fitted.text
        model = fitted.json()
        candidate_body = request(study) | {
            "model_id": None,
            "expected_model_sha256": None,
            "duplicate_tolerance": model["fit"]["search"]["duplicate_tolerance"],
            "source": {
                "kind": "explicit_rows",
                "points": [{"x": value} for value in (1.25, 3.25, 4.25, 6.25, 7.25, 8.25)],
            },
        }
        response = client.post(url(study) + "/candidate-revisions", json=candidate_body)
        assert response.status_code == 201, response.text
        candidate = response.json()["revision"]
        advice_path = url(study) + "/planning-models/" + model["model_id"] + "/auto-strategy"
        advice = client.post(
            advice_path,
            json={
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
                "r_squared_threshold": 1,
            },
        )
        assert advice.status_code == 200, advice.text
        view = advice.json()
        assert view["decision"]["recommended_policy"] == "greedy_incremental_maxpro_v1"
        body = {
            key: candidate_body[key]
            for key in (
                "expected_study_version_id",
                "expected_definition_sha256",
                "expected_history_revision_id",
                "expected_history_sha256",
                "expected_trial_count",
                "model_id",
                "expected_model_sha256",
                "duplicate_tolerance",
            )
        } | {
            "schema_version": 4,
            "request_id": str(uuid4()),
            "candidate_revision_id": candidate["revision_id"],
            "expected_rows_sha256": candidate["rows_sha256"],
            "batch_size": 2,
            "total_trial_budget": 20,
            "policy": view["decision"]["recommended_policy"],
            "auto_strategy": {
                "schema_version": 1,
                "routing_model_id": model["model_id"],
                "expected_model_sha256": model["snapshot_sha256"],
                "r_squared_threshold": 1,
                "expected_decision_sha256": view["decision_sha256"],
            },
        }
        from app.services import bo_augmentation

        original, operations = bo_augmentation._run, []

        def only_owned_review(operation, *args, **kwargs):
            assert operation == "auto_augmentation"
            operations.append(operation)
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_augmentation, "_run", only_owned_review)
        before = _database_rows(settings.workspace_root)
        for field, value in (
            ("expected_decision_sha256", "0" * 64),
            ("r_squared_threshold", 0.5),
            ("expected_model_sha256", "0" * 64),
        ):
            invalid = copy.deepcopy(body)
            invalid["auto_strategy"][field] = value
            rejected = client.post(url(study) + "/augmentations", json=invalid)
            assert rejected.status_code == 409, rejected.text
            assert _database_rows(settings.workspace_root) == before
        response = client.post(url(study) + "/augmentations", json=body)
        assert response.status_code == 201, response.text
        selected = response.json()
        evidence = selected["calculation"]["auto_evidence"]
        assert evidence["decision_sha256"] == view["decision_sha256"]
        assert evidence["diagnostic"] == {
            k: v for k, v in view["diagnostic"].items() if k != "source_is_current"
        }
        assert selected["model_id"] is None
        assert selected["calculation"]["prediction_evaluations"] == 0
        assert selected["calculation"]["augmentation"]["source"]["model_snapshot_id"] is None
        assert client.get(url(study)).json() == study
        count = len(operations)
        assert client.post(url(study) + "/augmentations", json=body).json() == selected
        assert len(operations) == count
        changed = body | {"batch_size": 1}
        assert client.post(url(study) + "/augmentations", json=changed).status_code == 409
        refine_advice = client.post(
            advice_path,
            json={
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
                "r_squared_threshold": 0,
            },
        )
        assert refine_advice.status_code == 200, refine_advice.text
        refined_view = refine_advice.json()
        assert (
            refined_view["decision"]["recommended_policy"]
            == "refine_ei_alternating_desirability_response_sd_v2"
        )
        refine_body = body | {
            "request_id": str(uuid4()),
            "batch_size": 1,
            "policy": refined_view["decision"]["recommended_policy"],
            "model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "auto_strategy": body["auto_strategy"]
            | {
                "r_squared_threshold": 0,
                "expected_decision_sha256": refined_view["decision_sha256"],
            },
        }
        refined = client.post(url(study) + "/augmentations", json=refine_body)
        assert refined.status_code == 201, refined.text
        assert refined.json()["calculation"]["prediction_evaluations"] == 6
        assert refined.json()["model_id"] == model["model_id"]
        from app.storage import bo_planning

        insert = bo_planning.insert_planning_selection
        before_race = _database_rows(settings.workspace_root)

        def changed_routing_before_commit(root, record, *, renewal=None):
            assert renewal is None
            with sqlite3.connect(metadata_db_path(root)) as connection:
                connection.execute(
                    "UPDATE bayesian_planning_models SET snapshot_sha256=? WHERE model_id=?",
                    ("0" * 64, model["model_id"]),
                )
            try:
                return insert(root, record, renewal=renewal)
            finally:
                with sqlite3.connect(metadata_db_path(root)) as connection:
                    connection.execute(
                        "UPDATE bayesian_planning_models SET snapshot_sha256=? WHERE model_id=?",
                        (model["snapshot_sha256"], model["model_id"]),
                    )

        with monkeypatch.context() as patch:
            patch.setattr(bo_planning, "insert_planning_selection", changed_routing_before_commit)
            raced = client.post(
                url(study) + "/augmentations", json=body | {"request_id": str(uuid4())}
            )
            assert raced.status_code == 409, raced.text
        assert _database_rows(settings.workspace_root) == before_race
        endpoint = url(study) + "/augmentations/" + selected["selection_id"]
        confirm = {
            "expected_config_sha256": selected["config_sha256"],
            "expected_result_sha256": selected["result_sha256"],
        }
        response = client.post(endpoint + "/confirm", json=confirm)
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["result_schema_version"] == 11 and batch["model"] is None
        assert batch["calculation"]["auto_evidence"] == evidence
        current = client.get(url(study)).json()
        response = client.put(
            url(study) + "/observations/batch",
            json=observations(
                current,
                tuple(i for i, row in enumerate(current["trials"]) if row["state"] == "pending"),
            ),
        )
        assert response.status_code == 200, response.text

        # A lost POST response may be retried after the history has advanced.
        def no_calculation(*args, **kwargs):
            raise AssertionError("restore/report/replay must not calculate")

        monkeypatch.setattr(bo_augmentation, "_run", no_calculation)
        monkeypatch.setattr("app.statistics.bo_loo.planning_loo", no_calculation)
        monkeypatch.setattr("app.statistics.bo_planning_model.fit_planning_model", no_calculation)
        monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", no_calculation)
        replay = client.post(url(study) + "/augmentations", json=body)
        assert replay.status_code == 201, replay.text
        assert replay.json()["result_sha256"] == selected["result_sha256"]
        assert not replay.json()["source_is_current"]
        again = client.post(endpoint + "/confirm", json=confirm)
        assert again.status_code == 201 and again.json()["batch_id"] == batch["batch_id"]
        saved_url = url(study) + "/augmentation-batches/" + batch["batch_id"]
        stored = client.get(saved_url)
        assert stored.status_code == 200, stored.text
        before = _database_rows(settings.workspace_root)
        descriptor = client.get(saved_url + "/report-source").json()
        for locale in ("en", "ko"):
            report = client.post(
                "/api/v1/reports",
                json={
                    "source": descriptor["source"],
                    "locale": locale,
                    "expected_source_ref_sha256": descriptor["source_ref_sha256"],
                },
            )
            assert report.status_code == 201, report.text
            record = report.json()
            download = client.post(
                f"/api/v1/reports/{record['export_id']}/download",
                json={"source": descriptor["source"], "expected_sha256": record["sha256"]},
            )
            assert download.status_code == 200, download.text
            assert hashlib.sha256(download.content).hexdigest() == record["sha256"]
            assert 'data-auto-evidence="1"' in download.text
            assert evidence["decision_sha256"] in download.text
            assert diagnostic_values_visible(evidence, download.text)
        assert _database_rows(settings.workspace_root) == before
        # Rehashing a locally altered result does not bypass the evidence/source links.
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
            original_row = connection.execute(
                "SELECT result_json,result_sha256 FROM bayesian_planning_selections "
                "WHERE selection_id=?",
                (selected["selection_id"],),
            ).fetchone()
            corrupt = json.loads(original_row[0])
            corrupt["auto_evidence"]["decision"]["threshold"] = 0.5
            connection.execute(
                "UPDATE bayesian_planning_selections SET result_json=?,result_sha256=? "
                "WHERE selection_id=?",
                (planning_json(corrupt), planning_sha(corrupt), selected["selection_id"]),
            )
        assert client.get(endpoint).status_code == 409
        with sqlite3.connect(metadata_db_path(settings.workspace_root)) as connection:
            connection.execute(
                "UPDATE bayesian_planning_selections SET result_json=?,result_sha256=? "
                "WHERE selection_id=?",
                (*original_row, selected["selection_id"]),
            )
    archive, restored = tmp_path / "backup.tar.gz", tmp_path / "restored 근거 workspace"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, restored)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        assert client.get(saved_url).json() == stored.json()
        assert client.get(endpoint).json()["calculation"]["auto_evidence"] == evidence
        assert (
            client.get(url(study) + "/augmentations/" + refined.json()["selection_id"]).json()[
                "calculation"
            ]
            == refined.json()["calculation"]
        )


def diagnostic_values_visible(evidence, html):
    section = html.split('<section data-auto-evidence="1">', 1)[1].split("</section>", 1)[0]
    for row in evidence["diagnostic"]["calculation"]["responses"]:
        for key in ("r_squared", "rmse"):
            cell = re.search(
                r'<td title="' + re.escape(repr(row[key])) + r'"[^>]*>([^<]+)</td>', section
            )
            assert cell is not None
            displayed = float(unescape(cell[1]).replace(",", ""))
            assert displayed == pytest.approx(row[key], rel=1e-9, abs=0)
    return True
