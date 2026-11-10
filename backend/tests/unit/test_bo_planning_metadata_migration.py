import sqlite3

import pytest
from test_bayesian_vector_storage import _study
from test_bo_fit_quality_metadata_migration import _insert_batch, _snapshot

from app.storage import metadata


def test_migration30_to31_preserves_json_and_enforces_manual_tuple(tmp_path, monkeypatch):
    old_contract = (7, 7, 4, "0.12.0", "conditional_mc_desirability_beta_marginal_v1")
    new_contract = (8, 8, 4, "0.13.0", "manual_ordered_fixed_model_v1")
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 30)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 30)
        )
        store = metadata.initialize_metadata_store(tmp_path)
        version, _, history = _study(tmp_path, vector=True, suffix="planning")
        with sqlite3.connect(store.path) as connection:
            _insert_batch(connection, version, history, old_contract, identity="old")
            with pytest.raises(sqlite3.IntegrityError):
                _insert_batch(connection, version, history, new_contract, identity="new")
            before = _snapshot(connection)
    metadata.initialize_metadata_store(tmp_path)
    with sqlite3.connect(store.path) as connection:
        assert _snapshot(connection) == before
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        _insert_batch(connection, version, history, new_contract, identity="new")
        for index, invalid in enumerate(
            (
                (8, 7, 4, "0.13.0", new_contract[-1]),
                (8, 8, 4, "0.12.0", new_contract[-1]),
                (8, 8, 4, "0.13.0", old_contract[-1]),
            )
        ):
            with pytest.raises(sqlite3.IntegrityError):
                _insert_batch(connection, version, history, invalid, identity=f"mixed-{index}")
        for table in (
            "bayesian_planning_models",
            "bayesian_candidate_sets",
            "bayesian_candidate_heads",
            "bayesian_candidate_revisions",
            "bayesian_planning_selections",
            "bayesian_planning_confirmations",
        ):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (0,)
