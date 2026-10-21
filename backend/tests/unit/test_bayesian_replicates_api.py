import copy
import hashlib
import shutil
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_bayesian_batches_api import _batch_request
from test_bayesian_study_lifecycle_api import _close_request

from app.core.config import Settings
from app.main import create_app
from app.storage import metadata
from app.storage.workspace_backup import backup_workspace, restore_workspace


def completed_study(client):
    result = client.post(
        "/api/v1/bayesian-studies",
        json={
            "name": "Synthetic replicate study",
            "factors": [
                {
                    "factor_id": "x",
                    "name": "Synthetic input",
                    "low": 0,
                    "high": 1,
                    "unit": None,
                }
            ],
            "objective": {
                "name": "Synthetic response",
                "unit": None,
                "goal_type": "maximize",
                "observation_policy": "manual_single_observation",
            },
            "constraints": [],
            "initial_design_seed": 17,
            "initial_design_size": 2,
        },
    )
    assert result.status_code == 201, result.json()
    study = result.json()
    history_id = study["observation_history"]["history_revision_id"]
    for trial in study["trials"]:
        result = client.put(
            f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 1 + trial["actual_coordinates"]["x"],
                "expected_history_revision_id": history_id,
            },
        )
        assert result.status_code == 200, result.json()
        history_id = result.json()["observation_history"]["history_revision_id"]
    return client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()


def request_for(study, count=2):
    history = study["observation_history"]
    return {
        "request_id": str(uuid4()),
        "count": count,
        "confirm_replicate_intent": True,
        "expected_history_revision_id": history["history_revision_id"],
        "expected_history_sha256": history["observation_history_sha256"],
        "total_trial_budget": 20,
    }


def url(study, trial=None):
    parent = study["trials"][0] if trial is None else trial
    return f"/api/v1/bayesian-studies/{study['study_id']}/trials/{parent['trial_id']}/replicates"


def test_offline_backup_restores_replicate_ownership_and_idempotency(tmp_path):
    source = tmp_path / "source"
    with TestClient(create_app(Settings(workspace_root=source))) as client:
        study = completed_study(client)
        request = request_for(study)
        created = client.post(url(study), json=request)
        assert created.status_code == 201, created.json()
        before = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
    archive = tmp_path / "synthetic-replicate-backup.zip"
    manifest = backup_workspace(source, archive)
    assert manifest["metadata_schema_version"] == 24
    assert manifest["database"]["row_counts"]["bayesian_replicate_requests"] == 1
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    destination = tmp_path / "restored workspace"
    restore_workspace(archive, destination)
    with TestClient(create_app(Settings(workspace_root=destination))) as client:
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json() == before
        retry = client.post(url(study), json=request)
        assert retry.status_code == 201 and retry.json()["replayed"] is True
        assert [row["trial_id"] for row in retry.json()["trials"]] == [
            row["trial_id"] for row in created.json()["trials"]
        ]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == archive_hash


def test_explicit_replicates_preserve_parent_history_and_are_idempotent(tmp_path):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = completed_study(client)
        original = copy.deepcopy(study["trials"])
        request = request_for(study)
        first = client.post(url(study), json=request)
        assert first.status_code == 201, first.json()
        created = first.json()
        assert not created["replayed"]
        assert len(created["trials"]) == 2
        for trial in created["trials"]:
            assert trial["origin"] == "replicate"
            assert trial["replicate_of_trial_id"] == original[0]["trial_id"]
            assert trial["actual_coordinates"] == original[0]["actual_coordinates"]
            assert trial["state"] == "pending" and trial["objective_value"] is None
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert restored.status_code == 200, restored.json()
        assert restored.json()["trials"][:2] == original
        assert restored.json()["observation_history"] == study["observation_history"]
        assert (
            "bayesian_optimization_pending_recommendation_exists"
            in restored.json()["recommendation_blockers"]
        )
        replay = client.post(url(study), json=request)
        assert replay.status_code == 201, replay.json()
        assert replay.json()["replayed"]
        assert replay.json()["trials"] == created["trials"]
        conflict = client.post(url(study), json={**request, "count": 3})
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "bayesian_replicate_request_conflict"
        history_id = study["observation_history"]["history_revision_id"]
        for index, trial in enumerate(created["trials"]):
            result = client.put(
                f"/api/v1/bayesian-studies/{study['study_id']}/trials/{trial['trial_id']}/observation",
                json={
                    "objective_value": 4 + index,
                    "expected_history_revision_id": history_id,
                },
            )
            assert result.status_code == 200, result.json()
            history_id = result.json()["observation_history"]["history_revision_id"]
        final = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
        assert final["completed_trial_count"] == 4
        assert final["trials"][:2] == original
        assert [trial["objective_value"] for trial in final["trials"][2:]] == [4, 5]
        assert final["recommendation_available"]
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM bayesian_replicate_requests").fetchone()[0] == 1


@pytest.mark.parametrize(
    "change,code",
    [
        ({"expected_history_sha256": "0" * 64}, "bayesian_optimization_history_stale"),
        ({"total_trial_budget": 3}, "bayesian_optimization_budget_exhausted"),
    ],
)
def test_conflict_is_atomic(tmp_path, change, code):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed_study(client)
        result = client.post(url(study), json={**request_for(study), **change})
        assert result.status_code == 409, result.json()
        assert result.json()["error"]["code"] == code
        assert (
            client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()["trial_count"] == 2
        )
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_replicate_requests").fetchone()[0] == 0


@pytest.mark.parametrize(
    "change", [{"count": 0}, {"count": 9}, {"count": 1.5}, {"confirm_replicate_intent": False}]
)
def test_invalid_replicate_request_is_rejected(tmp_path, change):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed_study(client)
        result = client.post(url(study), json={**request_for(study), **change})
        assert result.status_code == 422


def test_pending_experiment_blocks_another_replicate_bundle(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed_study(client)
        first = client.post(url(study), json=request_for(study, 1))
        assert first.status_code == 201, first.json()
        second = client.post(url(study), json=request_for(study, 1))
        assert second.status_code == 409
        assert (
            second.json()["error"]["code"] == "bayesian_optimization_pending_recommendation_exists"
        )
        pending_parent = client.post(
            url(study, first.json()["trials"][0]), json=request_for(study, 1)
        )
        assert pending_parent.status_code == 409
        assert pending_parent.json()["error"]["code"] == "bayesian_replicate_parent_not_completed"


def test_schema23_migration_preserves_original_trials_and_checksums(tmp_path, monkeypatch):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = completed_study(client)
        batch_root = f"/api/v1/bayesian-studies/{study['study_id']}/recommendation-batches"
        created = client.post(
            batch_root,
            json=_batch_request(
                study["observation_history"]["history_revision_id"],
                batch_size=1,
                kind="expected_improvement",
            ),
        )
        assert created.status_code == 201, created.text
        batch = created.json()
        before = client.get(f"/api/v1/bayesian-studies/{study['study_id']}").json()
    artifacts = {
        path.relative_to(tmp_path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in tmp_path.rglob("*.json")
    }
    database = metadata.metadata_db_path(tmp_path)
    with sqlite3.connect(database) as db:
        names = [
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if not row[0].startswith("sqlite_") and row[0] != "schema_migrations"
        ]
        snapshot = {
            name: (
                [row[1] for row in db.execute(f'PRAGMA table_info("{name}")')],
                db.execute(f'SELECT * FROM "{name}"').fetchall(),
            )
            for name in names
        }
    # Construct a populated previous-schema fixture in a different workspace.
    previous_root = tmp_path / "previous-schema"
    for relative in artifacts:
        destination = previous_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_path / relative, destination)
    tmp_path = previous_root
    settings = Settings(workspace_root=tmp_path)
    database = metadata.metadata_db_path(tmp_path)
    migrations = metadata.MIGRATIONS
    with monkeypatch.context() as context:
        context.setattr(metadata, "MIGRATIONS", tuple(m for m in migrations if m.version <= 23))
        context.setattr(metadata, "SCHEMA_VERSION", 23)
        metadata.initialize_metadata_store(tmp_path)
    with sqlite3.connect(database) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        for name, (old_columns, rows) in snapshot.items():
            if not rows:
                continue
            columns = [row[1] for row in db.execute(f'PRAGMA table_info("{name}")')]
            assert columns
            indices = [old_columns.index(column) for column in columns]
            placeholders = ",".join("?" for _ in columns)
            db.executemany(
                f'INSERT INTO "{name}" VALUES ({placeholders})',
                [tuple(row[index] for index in indices) for row in rows],
            )
        db.commit()
        assert db.execute("PRAGMA user_version").fetchone()[0] == 23
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    metadata.initialize_metadata_store(tmp_path)
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 24
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        columns = {row[1] for row in db.execute("PRAGMA table_info(bayesian_trials)")}
        assert "replicate_of_trial_id" in columns
    with TestClient(create_app(settings)) as client:
        restored = client.get(f"/api/v1/bayesian-studies/{study['study_id']}")
        assert restored.status_code == 200, restored.text
        assert restored.json() == before
        assert client.get(f"{batch_root}/{batch['batch_id']}").json() == batch
    assert {
        path: hashlib.sha256((tmp_path / path).read_bytes()).hexdigest() for path in artifacts
    } == artifacts


def test_replicate_abandon_close_and_owner_delete_preserve_atomic_graph(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = completed_study(client)
        request = request_for(study, 1)
        created = client.post(url(study), json=request)
        assert created.status_code == 201, created.text
        trial = created.json()["trials"][0]
        endpoint = f"/api/v1/bayesian-studies/{study['study_id']}"
        abandoned = client.post(
            endpoint + f"/trials/{trial['trial_id']}/abandon",
            json={"expected_history_revision_id": request["expected_history_revision_id"]},
        )
        assert abandoned.status_code == 200, abandoned.text
        current = client.get(endpoint).json()
        rejected = client.post(url(study, trial), json=request_for(current, 1))
        assert rejected.status_code == 409
        closed = client.post(
            endpoint + "/close",
            json=_close_request(current, target_status="abandoned", reason_code="study_cancelled"),
        )
        assert closed.status_code == 200, closed.text
        rejected = client.post(url(study), json=request_for(current, 1))
        assert rejected.status_code == 409
        replay = client.post(url(study), json=request)
        assert replay.status_code == 201 and replay.json()["replayed"]
        preflight = client.get(endpoint + "/deletion-preflight").json()
        assert preflight["counts"]["replicate_request_count"] == 1
        deleted = client.request(
            "DELETE",
            endpoint,
            json={
                "confirmation_study_id": study["study_id"],
                "expected_deletion_manifest_sha256": preflight["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert client.get(endpoint).status_code == 404
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("SELECT COUNT(*) FROM bayesian_replicate_requests").fetchone()[0] == 0
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
