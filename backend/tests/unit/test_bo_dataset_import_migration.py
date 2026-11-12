"""The measured-data ownership migration must not rewrite existing BO bytes."""

import sqlite3

from app.api.v1.schemas.bayesian import BayesianStudyCreateRequest
from app.core.config import Settings
from app.services.bayesian_studies import create_bayesian_study, get_bayesian_study
from app.storage import metadata
from tests.unit.test_bayesian_multiresponse_lifecycle import study_request


def test_metadata_33_upgrade_is_additive_and_preserves_generated_study(tmp_path, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(metadata, "SCHEMA_VERSION", 33)
        patch.setattr(
            metadata,
            "MIGRATIONS",
            tuple(item for item in metadata.MIGRATIONS if item.version <= 33),
        )
        assert metadata.initialize_metadata_store(tmp_path).schema_version == 33
    settings = Settings(workspace_root=tmp_path)
    study = create_bayesian_study(
        settings, BayesianStudyCreateRequest.model_validate(study_request())
    )
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bayesian_%'"
            )
        ]
        before = {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        }
    assert metadata.initialize_metadata_store(tmp_path).schema_version == 34
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        } == before
        assert db.execute("SELECT COUNT(*) FROM bayesian_dataset_imports").fetchone() == (0,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert get_bayesian_study(settings, study.study_id) == study
