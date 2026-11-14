"""Metadata CHECK expansion preserves existing JSON, owners and graph sidecars."""

import sqlite3

import pytest

from app.storage import metadata
from tests.unit.test_bayesian_vector_storage import _study
from tests.unit.test_bo_fit_quality_metadata_migration import _insert_batch, _snapshot


def test_migration36_preserves_bytes_and_accepts_only_coherent_mixture_tuple(tmp_path, monkeypatch):
    root = tmp_path / "mixture migration workspace"
    old_contract = (12, 12, 5, "0.16.0", "source_owned_mixed_planning_v1")
    new_contract = (13, 13, 6, "0.17.0", "source_owned_mixture_planning_v1")
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 36)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 36)
        )
        store = metadata.initialize_metadata_store(root)
        version, _, history = _study(root, vector=True, suffix="mixture migration")
        with sqlite3.connect(store.path) as db:
            _insert_batch(db, version, history, old_contract, identity="old")
            with pytest.raises(sqlite3.IntegrityError):
                _insert_batch(db, version, history, new_contract, identity="new")
            before = _snapshot(db)
    metadata.initialize_metadata_store(root)
    with sqlite3.connect(store.path) as db:
        assert _snapshot(db) == before
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        _insert_batch(db, version, history, new_contract, identity="new")
        for index, invalid in enumerate(
            (
                (13, 12, 6, "0.17.0", new_contract[-1]),
                (13, 13, 5, "0.17.0", new_contract[-1]),
                (13, 13, 6, "0.16.0", new_contract[-1]),
                (13, 13, 6, "0.17.0", old_contract[-1]),
            )
        ):
            with pytest.raises(sqlite3.IntegrityError):
                _insert_batch(db, version, history, invalid, identity=f"invalid{index}")
        for table in ("bayesian_saved_views", "bayesian_augmentation_renewals"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        # Isolate the import-version CHECK; real dataset ownership is covered by API tests.
        db.execute("SAVEPOINT import_contract")
        values = (
            version.study_version_id,
            "synthetic-dataset",
            "import",
            *("a" * 64 for _ in range(4)),
        )
        db.execute("INSERT INTO bayesian_dataset_imports VALUES (?,?,?,?,?,?,?,2)", values)
        db.execute("ROLLBACK TO import_contract")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO bayesian_dataset_imports VALUES (?,?,?,?,?,?,?,3)", values)
