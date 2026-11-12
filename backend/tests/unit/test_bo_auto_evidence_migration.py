"""SQL migration evidence only; synthetic payloads are not fitted BO artifacts."""

import sqlite3

import pytest

from app.storage import metadata
from tests.unit.test_bayesian_vector_storage import STAMP, _study
from tests.unit.test_bo_fit_quality_metadata_migration import (
    LEGACY_CONTRACTS,
    _insert_batch,
    _sha,
)

CONTRACTS = LEGACY_CONTRACTS + (
    (6, 6, 4, "0.11.0", "conditional_mc_desirability_beta_marginal_v1"),
    (7, 7, 4, "0.12.0", "conditional_mc_desirability_beta_marginal_v1"),
    (8, 8, 4, "0.13.0", "manual_ordered_fixed_model_v1"),
    (9, 9, 4, "0.14.0", "source_owned_augmentation_v1"),
    (10, 10, 5, "0.15.0", "source_owned_mixed_planning_v1"),
)
AUTO_CONTRACT = (11, 11, 4, "0.16.0", "source_owned_augmentation_v1")
MIXED_AUTO_CONTRACT = (12, 12, 5, "0.16.0", "source_owned_mixed_planning_v1")


def _rows(db):
    tables = [
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bayesian_%' "
            "ORDER BY name"
        )
    ]
    return {table: db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall() for table in tables}


def _schema(db):
    return db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name LIKE '%bayesian%' "
        "ORDER BY type,name"
    ).fetchall()


def _insert_selection(db, version, schema, *, model=None, identity="auto"):
    config = '{ "synthetic": "selection config" }\n'
    result = '{ "synthetic": "selection result", "retained": true }\n'
    db.execute(
        "INSERT INTO bayesian_planning_selections VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            identity,
            version.study_version_id,
            model,
            f"revision-{version.study_version_id}",
            f"request-{identity}",
            schema,
            config,
            _sha(config),
            result,
            _sha(result),
            STAMP,
        ),
    )


def _planning(db, version, history, schema):
    owner = version.study_version_id
    model, revision, candidate_set = f"model-{owner}", f"revision-{owner}", f"set-{owner}"
    config, snapshot, rows = '{ "synthetic": "config" }\n', '{ "state": [] }\n', "[ 1 ]\n"
    db.execute(
        "INSERT INTO bayesian_planning_models VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            model,
            owner,
            history.history_revision_id,
            version.definition_sha256,
            history.observation_history_sha256,
            2 if schema == 3 else 1,
            f"model-request-{owner}",
            config,
            _sha(config),
            snapshot,
            _sha(snapshot),
            STAMP,
        ),
    )
    db.execute(
        "INSERT INTO bayesian_candidate_sets VALUES (?,?,?,?)",
        (candidate_set, owner, "Synthetic migration", STAMP),
    )
    db.execute(
        "INSERT INTO bayesian_candidate_revisions VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            revision,
            candidate_set,
            owner,
            model if schema == 1 else None,
            1,
            schema,
            f"candidate-request-{owner}",
            None,
            3,
            "b" * 64,
            config,
            _sha(config),
            rows,
            _sha(rows),
            1,
            STAMP,
            history.history_revision_id if schema != 1 else None,
            history.observation_history_sha256 if schema != 1 else None,
            version.definition_sha256 if schema != 1 else None,
        ),
    )
    db.execute("INSERT INTO bayesian_candidate_heads VALUES (?,?)", (candidate_set, revision))
    _insert_selection(
        db, version, schema, model=model if schema == 1 else None, identity=f"selection-{owner}"
    )
    db.execute(
        "INSERT INTO bayesian_planning_confirmations VALUES (?,?)",
        (f"selection-{owner}", f"batch-{schema + 7}"),
    )


@pytest.fixture
def legacy32(tmp_path, monkeypatch):
    root = tmp_path / "auto migration \ud55c\uae00 workspace"
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 32)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 32)
        )
        store = metadata.initialize_metadata_store(root)
        sources = [
            _study(root, vector=contract[0] >= 4, suffix=str(contract[0])) for contract in CONTRACTS
        ]
        with sqlite3.connect(store.path) as db:
            db.execute("PRAGMA foreign_keys=ON")
            for contract, (version, trials, history) in zip(CONTRACTS, sources, strict=True):
                schema = contract[0]
                _insert_batch(db, version, history, contract, identity=f"batch-{schema}")
                payload = f'{{ "synthetic_item": {schema} }}\n'
                db.execute(
                    "INSERT INTO bayesian_recommendation_batch_items VALUES (?,?,?,?,?,?,?,?)",
                    (
                        f"item-{schema}",
                        f"batch-{schema}",
                        trials[0].trial_id,
                        1,
                        contract[2],
                        payload,
                        _sha(payload),
                        STAMP,
                    ),
                )
                if schema >= 8:
                    _planning(db, version, history, schema - 7)
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            version, _, history = sources[-2]
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                _insert_selection(db, version, 4)
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                _insert_batch(db, version, history, AUTO_CONTRACT, identity="auto")
            before = _rows(db)
            migrations = db.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
    return root, store.path, sources[-2], before, migrations


def test_upgrade32_to33_preserves_all_old_payloads_hashes_and_relations(legacy32):
    root, path, (version, _, history), before, migrations = legacy32
    assert metadata.initialize_metadata_store(root).schema_version == 34
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        upgraded = _rows(db)
        assert {table: upgraded[table] for table in before} == before
        assert upgraded["bayesian_dataset_imports"] == []
        assert db.execute("PRAGMA user_version").fetchone() == (34,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert (
            db.execute(
                "SELECT * FROM schema_migrations WHERE version<=32 ORDER BY version"
            ).fetchall()
            == migrations
        )
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IN "
            "('idx_bayesian_recommendation_batches_version_created',"
            "'uq_bayesian_batch_report_owner') "
            "ORDER BY name"
        ).fetchall() == [
            ("idx_bayesian_recommendation_batches_version_created",),
            ("uq_bayesian_batch_report_owner",),
        ]
        for table in before:
            columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
            for column in columns:
                if column.endswith("_json") and column[:-5] + "_sha256" in columns:
                    for value, digest in db.execute(
                        f"SELECT {column},{column[:-5]}_sha256 FROM {table}"
                    ):
                        if value is not None:
                            assert _sha(value) == digest
        _insert_selection(db, version, 4)
        _insert_batch(db, version, history, AUTO_CONTRACT, identity="auto")
        db.execute("INSERT INTO bayesian_planning_confirmations VALUES ('auto','auto')")
        after = _rows(db)
    metadata.initialize_metadata_store(root)
    with sqlite3.connect(path) as db:
        assert _rows(db) == after
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize(
    ("column", "value"),
    (
        ("method_version", "0.15.0"),
        ("batch_policy", "source_owned_mixed_planning_v1"),
        ("config_schema_version", 10),
        ("result_schema_version", 10),
        ("model_schema_version", 10),
        ("item_schema_version", 5),
        ("batch_size", 0),
        ("batch_size", 9),
    ),
)
def test_auto_batch_rejects_mixed_version_tuples(legacy32, column, value):
    root, path, (version, _, history), _, _ = legacy32
    metadata.initialize_metadata_store(root)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        _insert_batch(db, version, history, AUTO_CONTRACT, identity="auto", count=8)
        before = _rows(db)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            db.execute(
                f"UPDATE bayesian_recommendation_batches SET {column}=? WHERE batch_id='auto'",
                (value,),
            )
        assert _rows(db) == before


def test_selection_schema_owner_uniqueness_and_child_restrictions_survive(legacy32):
    root, path, (version, _, history), _, _ = legacy32
    metadata.initialize_metadata_store(root)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        for schema in (0, 1, 6):
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                _insert_selection(db, version, schema, identity=f"invalid-{schema}")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            _insert_selection(db, version, 4, model="model-version-8", identity="wrong-owner")
        _insert_selection(db, version, 4)
        _insert_batch(db, version, history, AUTO_CONTRACT, identity="auto")
        db.execute("INSERT INTO bayesian_planning_confirmations VALUES ('auto','auto')")
        _insert_selection(
            db, version, 4, model=f"model-{version.study_version_id}", identity="other"
        )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
            db.execute(
                "UPDATE bayesian_planning_selections SET request_id='request-auto' "
                "WHERE selection_id='other'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            db.execute(
                "UPDATE bayesian_planning_selections "
                "SET candidate_revision_id='revision-version-8' "
                "WHERE selection_id='other'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
            db.execute("DELETE FROM bayesian_planning_selections WHERE selection_id='auto'")
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_mixed_auto_tuple_preserves_nullable_model_and_rejects_cross_family(legacy32):
    root, path, (version, _, history), _, _ = legacy32
    metadata.initialize_metadata_store(root)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        _insert_selection(db, version, 5, identity="mixed-auto")
        _insert_selection(
            db, version, 5, model=f"model-{version.study_version_id}", identity="mixed-refine"
        )
        _insert_batch(db, version, history, MIXED_AUTO_CONTRACT, identity="mixed-auto", count=8)
        db.execute("INSERT INTO bayesian_planning_confirmations VALUES ('mixed-auto','mixed-auto')")
        before = _rows(db)
        for column, value in (
            ("method_version", "0.15.0"),
            ("config_schema_version", 11),
            ("result_schema_version", 11),
            ("model_schema_version", 11),
            ("item_schema_version", 4),
            ("batch_policy", "source_owned_augmentation_v1"),
        ):
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                db.execute(
                    f"UPDATE bayesian_recommendation_batches SET {column}=? "
                    "WHERE batch_id='mixed-auto'",
                    (value,),
                )
            assert _rows(db) == before
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_migration_failure_rolls_back_both_replacements_and_version_markers(legacy32):
    root, path, _, _, _ = legacy32
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute(
            "INSERT INTO bayesian_planning_confirmations VALUES ('missing-selection','batch-1')"
        )
        before, schema = _rows(db), _schema(db)
    with pytest.raises(
        metadata.MetadataSchemaCompatibilityError, match="workspace_metadata_invalid"
    ):
        metadata.initialize_metadata_store(root)
    with sqlite3.connect(path) as db:
        assert _rows(db) == before
        assert _schema(db) == schema
        assert db.execute("PRAGMA user_version").fetchone() == (32,)
        assert db.execute("SELECT version FROM schema_migrations WHERE version=33").fetchall() == []
