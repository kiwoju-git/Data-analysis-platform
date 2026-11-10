"""Real fixed-model augmentation and exact stored report, using synthetic responses."""

import hashlib
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.workspace_backup import backup_workspace, restore_workspace
from tests.unit.test_bayesian_multiresponse_lifecycle import observations, url
from tests.unit.test_bo_candidates_v2 import request
from tests.unit.test_bo_desirability_review_api import completed
from tests.unit.test_bo_planning_api import _database_rows, fit_request


def test_fixed_model_refine_confirm_report_restore_and_no_refit(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path / "augmentation workspace")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        response = client.post(url(study) + "/planning-models", json=fit_request(study))
        assert response.status_code == 201, response.text
        model = response.json()
        from app.services import bo_planning

        original = bo_planning.run_planning_operation

        def no_refit(operation, *args, **kwargs):
            assert operation != "fit"
            return original(operation, *args, **kwargs)

        monkeypatch.setattr(bo_planning, "run_planning_operation", no_refit)
        candidate_body = request(study) | {
            "model_id": model["model_id"],
            "expected_model_sha256": model["snapshot_sha256"],
            "duplicate_tolerance": model["fit"]["search"]["duplicate_tolerance"],
            "source": {
                "kind": "explicit_rows",
                "points": [{"x": value} for value in (1.25, 3.25, 4.25, 6.25, 7.25, 8.25)],
            },
        }
        response = client.post(url(study) + "/candidate-revisions", json=candidate_body)
        assert response.status_code == 201, response.text
        candidate = response.json()["revision"]
        base = {
            key: candidate_body[key]
            for key in (
                "schema_version",
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
            "candidate_revision_id": candidate["revision_id"],
            "expected_rows_sha256": candidate["rows_sha256"],
            "batch_size": 3,
            "total_trial_budget": 20,
        }
        selected = {}
        for policy in (
            "refine_ei_alternating_desirability_response_sd_v2",
            "confirm_mean_then_competitive_sd_v1",
        ):
            body = base | {"request_id": str(uuid4()), "policy": policy}
            if policy == "confirm_mean_then_competitive_sd_v1":
                # Confirmation may reject q>1 when no remaining row is competitive.
                body["batch_size"] = 1
            response = client.post(url(study) + "/augmentations", json=body)
            assert response.status_code == 201, (policy, response.text)
            selected[policy] = response.json()
            assert client.post(url(study) + "/augmentations", json=body).json() == response.json()
            assert response.json()["calculation"]["prediction_evaluations"] == 6
        confirm_selection = selected["confirm_mean_then_competitive_sd_v1"]
        assert all(
            row["acquisition"] is None for row in confirm_selection["calculation"]["selected_rows"]
        )
        selection = selected["refine_ei_alternating_desirability_response_sd_v2"]
        assert selection["calculation"]["augmentation"]["response_uncertainty"]["context"]
        endpoint = url(study) + "/augmentations/" + selection["selection_id"]
        response = client.post(
            endpoint + "/confirm",
            json={
                "expected_config_sha256": selection["config_sha256"],
                "expected_result_sha256": selection["result_sha256"],
            },
        )
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["model"]["snapshot_sha256"] == model["snapshot_sha256"]
        current = client.get(url(study)).json()
        assert current["observation_history"] == study["observation_history"]
        saved = client.put(
            url(study) + "/observations/batch",
            json=observations(
                current,
                tuple(
                    i for i, trial in enumerate(current["trials"]) if trial["state"] == "pending"
                ),
            ),
        )
        assert saved.status_code == 200, saved.text
        saved_url = url(study) + "/augmentation-batches/" + batch["batch_id"]
        stored = client.get(saved_url)
        assert stored.status_code == 200, stored.text
        assert stored.json()["batch_state"] == "completed"
        before = _database_rows(settings.workspace_root)
        descriptor = client.get(saved_url + "/report-source")
        assert descriptor.status_code == 200, descriptor.text
        descriptor = descriptor.json()
        assert "augmentation_batch_id=" in descriptor["open_target"]
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
            downloaded = client.post(
                f"/api/v1/reports/{record['export_id']}/download",
                json={
                    "source": descriptor["source"],
                    "expected_sha256": record["sha256"],
                },
            )
            assert downloaded.status_code == 200, downloaded.text
            assert hashlib.sha256(downloaded.content).hexdigest() == record["sha256"]
            assert model["snapshot_sha256"] in downloaded.text
            assert selection["result_sha256"] in downloaded.text
            assert "refine_ei_alternating_desirability_response_sd_v2" in downloaded.text
        assert _database_rows(settings.workspace_root) == before
    archive, restored = tmp_path / "backup.tar.gz", tmp_path / "복원 workspace"
    backup_workspace(settings.workspace_root, archive)
    restore_workspace(archive, restored)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        assert client.get(saved_url).json() == stored.json()
        assert client.get(endpoint).status_code == 200
