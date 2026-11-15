"""Real SQLite snapshot capacity, atomic upgrades and unchanged historical bytes."""

import sqlite3
from dataclasses import replace

import pytest

from app.storage import bo_planning as storage
from app.storage import metadata
from app.storage.bayesian_studies import BayesianStorageConflict
from tests.unit.test_bo_planning_storage import _candidate, _model, _selection


def test_large_snapshot_is_really_persisted_and_read_back(tmp_path):
    metadata.initialize_metadata_store(tmp_path)
    old, _ = _model(tmp_path)
    snapshot = {"synthetic_padding": "a" * (16 * 1024 * 1024)}
    record = {
        **old,
        "model_id": "large",
        "request_id": "large-fit",
        "snapshot_json": storage.planning_json(snapshot),
        "snapshot_sha256": storage.planning_sha(snapshot),
    }
    assert storage.insert_planning_model(tmp_path, record) == "large"
    assert storage.get_planning_model(tmp_path, "large", old["study_version_id"]) == record
    assert storage.get_planning_model(tmp_path, old["model_id"], old["study_version_id"]) == old


def test_non_model_document_retains_16_mib_guard():
    snapshot = {"synthetic_padding": "a" * (16 * 1024 * 1024)}
    record = {"rows_json": storage.planning_json(snapshot), "sha": storage.planning_sha(snapshot)}
    with pytest.raises(BayesianStorageConflict, match="artifact_invalid"):
        storage._documents(record, (("rows_json", "sha"),))


def _old_workspace(root, monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 38)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 38)
        )
        metadata.initialize_metadata_store(root)
    model, _ = _model(root)
    candidate = _candidate(model)
    storage.insert_candidate_revision(root, candidate, name="Synthetic", expected_head=None)
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        db.execute(
            "UPDATE bayesian_trials SET state='abandoned',closed_at=?", (model["created_at"],)
        )
    storage.insert_planning_selection(root, _selection(model, candidate))
    return model


def _records(root):
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        return {
            name: db.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
            for (name,) in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }


def test_schema38_upgrade_preserves_records_foreign_keys_and_old_migrations(tmp_path, monkeypatch):
    _old_workspace(tmp_path, monkeypatch)
    before = _records(tmp_path)
    assert metadata.initialize_metadata_store(tmp_path).schema_version == 39
    after = _records(tmp_path)
    assert after.pop("schema_migrations")[:-1] == before.pop("schema_migrations")
    assert after == before
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA user_version").fetchone() == (39,)


def test_failed_schema39_upgrade_rolls_back_table_and_version(tmp_path, monkeypatch):
    _old_workspace(tmp_path, monkeypatch)
    before = _records(tmp_path)
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        schema = db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
    broken = tuple(
        replace(m, sql=m.sql + "\nINSERT INTO missing_synthetic_table VALUES (1);")
        if m.version == 39
        else m
        for m in metadata.MIGRATIONS
    )
    monkeypatch.setattr(metadata, "MIGRATIONS", broken)
    with pytest.raises(sqlite3.OperationalError):
        metadata.initialize_metadata_store(tmp_path)
    assert _records(tmp_path) == before
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert db.execute("PRAGMA user_version").fetchone() == (38,)
        assert (
            db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall() == schema
        )
