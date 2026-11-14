"""Model-free candidate HTTP lifecycle, isolated from model-based posterior tests."""

import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage import bo_planning, metadata
from tests.unit.test_bayesian_multiresponse_lifecycle import observations, url
from tests.unit.test_bayesian_vector_storage import _study
from tests.unit.test_bo_desirability_review_api import completed
from tests.unit.test_bo_planning_storage import _candidate


def request(study):
    return {
        "schema_version": 2,
        "request_id": str(uuid4()),
        "candidate_set_id": str(uuid4()),
        "name": "Synthetic model-free candidates",
        "expected_head_revision_id": None,
        "expected_study_version_id": study["study_version_id"],
        "expected_definition_sha256": study["definition_sha256"],
        "expected_history_revision_id": study["observation_history"]["history_revision_id"],
        "expected_history_sha256": study["observation_history"]["observation_history_sha256"],
        "expected_trial_count": study["trial_count"],
        "model_id": None,
        "expected_model_sha256": None,
        "source": {"kind": "explicit_rows", "points": [{"x": 1.25}, {"x": 4.25}, {"x": 7.25}]},
    }


def test_model_free_candidate_create_replay_append_restore_without_fit(tmp_path, monkeypatch):
    from app.services import bo_candidates_v2
    from app.services import bo_planning as service

    def no_model(*args, **kwargs):
        pytest.fail("model-free candidate operation must not read a model")

    monkeypatch.setattr(bo_candidates_v2, "_read_model", no_model)
    original = service.run_planning_operation

    def candidate_only(operation, *args, **kwargs):
        assert operation == "candidates"
        return original(operation, *args, **kwargs)

    monkeypatch.setattr(service, "run_planning_operation", candidate_only)
    settings = Settings(workspace_root=tmp_path / "workspace")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        body = request(study)
        endpoint = url(study) + "/candidate-revisions"
        response = client.post(endpoint, json=body)
        assert response.status_code == 201, response.text
        page = response.json()
        assert page["revision"]["schema_version"] == 2
        assert page["revision"]["model_id"] is None
        assert page["revision"]["row_count"] == 3
        assert client.post(endpoint, json=body).json() == page
        assert client.get(url(study)).json() == study
        assert client.get(url(study) + "/planning-models").json()["items"] == []
        assert client.get(url(study) + "/candidate-sets").json()["items"] == [page["revision"]]
        revision = page["revision"]["revision_id"]
        updated = body | {
            "request_id": str(uuid4()),
            "expected_head_revision_id": revision,
            "source": {"kind": "append_rows", "points": [{"x": 8.25}]},
        }
        next_page = client.post(endpoint, json=updated)
        assert next_page.status_code == 201, next_page.text
        assert next_page.json()["revision"]["row_count"] == 4
        assert client.get(endpoint + "/" + revision).json() == page
        stale = updated | {"request_id": str(uuid4())}
        assert client.post(endpoint, json=stale).status_code == 409
        conflict = body | {"name": "Different payload"}
        assert client.post(endpoint, json=conflict).status_code == 409
    with TestClient(create_app(settings)) as restored:
        assert restored.get(endpoint + "/" + revision).json() == page


def test_migration31_to32_preserves_old_candidate_bytes_and_owner_links(tmp_path, monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 31)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 31)
        )
        metadata.initialize_metadata_store(tmp_path)
        version, _, history = _study(tmp_path)
        model = {
            "model_id": "model-a",
            "study_version_id": version.study_version_id,
            "source_history_revision_id": history.history_revision_id,
            "definition_sha256": version.definition_sha256,
            "history_sha256": history.observation_history_sha256,
            "schema_version": 1,
            "request_id": "fit-a",
            "config_json": bo_planning.planning_json({"synthetic": "a"}),
            "config_sha256": bo_planning.planning_sha({"synthetic": "a"}),
            "snapshot_json": bo_planning.planning_json({"numeric_state": [0.0, 1.0]}),
            "snapshot_sha256": bo_planning.planning_sha({"numeric_state": [0.0, 1.0]}),
            "created_at": "2026-11-10T00:00:00Z",
        }
        candidate = _candidate(model)
        # Seed the actual schema-31 layout, not a current writer whose capacity
        # contract requires later tables. These are synthetic storage receipts.
        with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
            db.execute("PRAGMA foreign_keys=ON")
            assert db.execute("PRAGMA user_version").fetchone() == (31,)
            assert (
                db.execute(
                    "SELECT name FROM sqlite_master WHERE name IN "
                    "('bayesian_saved_views','bayesian_augmentation_renewals','bayesian_dataset_imports')"
                ).fetchall()
                == []
            )
            fields = tuple(model)
            db.execute(
                f"INSERT INTO bayesian_planning_models ({','.join(fields)}) "
                f"VALUES ({','.join('?' for _ in fields)})",
                tuple(model[field] for field in fields),
            )
            db.execute(
                "INSERT INTO bayesian_candidate_sets "
                "(candidate_set_id,study_version_id,name,created_at) VALUES (?,?,?,?)",
                (
                    candidate["candidate_set_id"],
                    model["study_version_id"],
                    "Synthetic",
                    model["created_at"],
                ),
            )
            fields = tuple(candidate)
            db.execute(
                f"INSERT INTO bayesian_candidate_revisions ({','.join(fields)}) "
                f"VALUES ({','.join('?' for _ in fields)})",
                tuple(candidate[field] for field in fields),
            )
            db.execute(
                "INSERT INTO bayesian_candidate_heads (candidate_set_id,revision_id) VALUES (?,?)",
                (candidate["candidate_set_id"], candidate["revision_id"]),
            )
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        before = bo_planning.get_candidate_revision(
            tmp_path, candidate["revision_id"], model["study_version_id"]
        )
        assert before == candidate
    with monkeypatch.context() as intermediate:
        intermediate.setattr(metadata, "SCHEMA_VERSION", 32)
        intermediate.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 32)
        )
        assert metadata.initialize_metadata_store(tmp_path).schema_version == 32
        assert (
            bo_planning.get_candidate_revision(
                tmp_path, candidate["revision_id"], model["study_version_id"]
            )
            == before
        )
        assert (
            bo_planning.get_planning_model(tmp_path, model["model_id"], model["study_version_id"])
            == model
        )
    metadata.initialize_metadata_store(tmp_path)
    assert (
        bo_planning.get_candidate_revision(
            tmp_path, candidate["revision_id"], model["study_version_id"]
        )
        == before
    )
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute(
            "SELECT config_json,rows_json FROM bayesian_candidate_revisions"
        ).fetchone() == (candidate["config_json"], candidate["rows_json"])
        assert db.execute(
            "SELECT candidate_set_id,revision_id FROM bayesian_candidate_heads"
        ).fetchone() == (candidate["candidate_set_id"], candidate["revision_id"])
        assert db.execute(
            "SELECT candidate_set_id,study_version_id,name,created_at FROM bayesian_candidate_sets"
        ).fetchone() == (
            candidate["candidate_set_id"],
            model["study_version_id"],
            "Synthetic",
            model["created_at"],
        )
    assert (
        bo_planning.get_planning_model(tmp_path, model["model_id"], model["study_version_id"])
        == model
    )


def test_model_free_augmentation_is_stored_without_fit_or_pending_trials(tmp_path, monkeypatch):
    from app.services import bo_augmentation as augmentation
    from app.services import bo_planning as service

    def no_model(*args, **kwargs):
        pytest.fail("space filling must not fit or restore a model")

    monkeypatch.setattr(augmentation, "_read_model", no_model)
    original = service.run_planning_operation

    def no_fit(operation, *args, **kwargs):
        assert operation in {"candidates", "augmentation"}
        return original(operation, *args, **kwargs)

    monkeypatch.setattr(service, "run_planning_operation", no_fit)
    settings = Settings(workspace_root=tmp_path / "augmentation workspace")
    with TestClient(create_app(settings)) as client:
        study = completed(client)
        candidate_body = request(study)
        response = client.post(url(study) + "/candidate-revisions", json=candidate_body)
        assert response.status_code == 201, response.text
        candidate = response.json()["revision"]
        body = {
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
            )
        } | {
            "request_id": str(uuid4()),
            "candidate_revision_id": candidate["revision_id"],
            "expected_rows_sha256": candidate["rows_sha256"],
            "policy": "greedy_incremental_maxpro_v1",
            "batch_size": 2,
            "total_trial_budget": 20,
        }
        endpoint = url(study) + "/augmentations"
        response = client.post(endpoint, json=body)
        assert response.status_code == 201, response.text
        selection = response.json()
        assert selection["model_id"] is None
        assert selection["calculation"]["prediction_evaluations"] == 0
        assert len(selection["calculation"]["selected_rows"]) == 2
        assert all(
            "desirability_moments" not in row for row in selection["calculation"]["selected_rows"]
        )
        assert selection["confirmed_batch_id"] is None
        assert client.post(endpoint, json=body).json() == selection
        assert client.get(endpoint + "/" + selection["selection_id"]).json() == selection
        assert client.get(url(study)).json() == study
        assert client.get(url(study) + "/planning-selections").json()["items"] == []
        changed = body | {"batch_size": 1}
        assert client.post(endpoint, json=changed).status_code == 409
        confirm = {
            "expected_config_sha256": selection["config_sha256"],
            "expected_result_sha256": selection["result_sha256"],
        }
        response = client.post(
            endpoint + "/" + selection["selection_id"] + "/confirm", json=confirm
        )
        assert response.status_code == 201, response.text
        batch = response.json()
        assert batch["result_schema_version"] == 9 and batch["model"] is None
        assert batch["calculation"]["augmentation"]["policy"] == body["policy"]
        assert [item["trial"]["actual_coordinates"] for item in batch["items"]] == [
            row["actual_coordinates"] for row in selection["calculation"]["selected_rows"]
        ]
        assert (
            client.post(
                endpoint + "/" + selection["selection_id"] + "/confirm", json=confirm
            ).json()
            == batch
        )
        current = client.get(url(study)).json()
        assert current["trial_count"] == study["trial_count"] + 2
        assert current["observation_history"] == study["observation_history"]
        saved = client.put(url(study) + "/observations/batch", json=observations(current, (3, 4)))
        assert saved.status_code == 200, saved.text
        selection = client.get(endpoint + "/" + selection["selection_id"]).json()
        assert selection["confirmed_batch_id"] == batch["batch_id"]
        assert selection["source_is_current"] is False
        exact_url = url(study) + "/augmentation-batches/" + batch["batch_id"]
        completed_batch = client.get(exact_url)
        assert completed_batch.status_code == 200, completed_batch.text
        assert completed_batch.json()["batch_state"] == "completed"
        assert completed_batch.json()["result_sha256"] == batch["result_sha256"]
    with TestClient(create_app(settings)) as restored:
        assert restored.get(endpoint + "/" + selection["selection_id"]).json() == selection
        assert restored.get(exact_url).json() == completed_batch.json()
