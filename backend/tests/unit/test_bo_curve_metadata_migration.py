import sqlite3

import pytest
from test_bayesian_vector_storage import _study
from test_bo_fit_quality_metadata_migration import _insert_batch, _snapshot

from app.storage import metadata


def test_migration29_to30_preserves_bytes_and_extends_only_curve_tuple(tmp_path, monkeypatch):
    legacy = (6, 6, 4, "0.11.0", "conditional_mc_desirability_beta_marginal_v1")
    current = (7, 7, 4, "0.12.0", legacy[-1])
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 29)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 29)
        )
        store = metadata.initialize_metadata_store(tmp_path)
        version, _, history = _study(tmp_path, vector=True, suffix="curve")
        with sqlite3.connect(store.path) as db:
            _insert_batch(db, version, history, legacy, identity="old")
            with pytest.raises(sqlite3.IntegrityError):
                _insert_batch(db, version, history, current, identity="new")
            before = _snapshot(db)
    metadata.initialize_metadata_store(tmp_path)
    with sqlite3.connect(store.path) as db:
        assert _snapshot(db) == before
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        _insert_batch(db, version, history, current, identity="new")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_batch(db, version, history, (7, 6, 4, "0.12.0", legacy[-1]), identity="mixed")
