import hashlib
import sqlite3

import pytest
from test_bayesian_vector_storage import STAMP, _study

from app.storage import metadata

TABLES = (
    "bayesian_studies",
    "bayesian_study_versions",
    "bayesian_trials",
    "bayesian_observation_history_revisions",
    "bayesian_recommendation_batches",
    "bayesian_recommendation_batch_items",
)
LEGACY_CONTRACTS = (
    (1, 2, 1, "0.6.0", "greedy_posterior_mean_fantasy_ei_v1"),
    (2, 3, 2, "0.7.0", "greedy_mc_joint_latent_improvement_v2"),
    (3, 4, 2, "0.8.0", "greedy_mc_joint_latent_improvement_v2"),
    (4, 5, 3, "0.9.0", "independent_latent_desirability_beta_ei_v1"),
    (5, 5, 4, "0.10.0", "conditional_mc_desirability_beta_marginal_v1"),
)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _insert_batch(connection, version, history, contract, *, identity, count=1):
    schema, model, item, method, policy = contract
    # This is a SQL migration fixture, not a service-readable statistical result.
    # Whitespace and key order deliberately detect any payload reserialization.
    config = f'{{ "schema_version": {schema}, "synthetic": "config" }}\n'
    result = f'{{ "synthetic": "result", "schema_version": {schema} }}\n'
    connection.execute(
        """INSERT INTO bayesian_recommendation_batches (
            batch_id,study_version_id,source_history_revision_id,
            source_observation_history_sha256,method_id,method_version,batch_size,
            batch_policy,config_schema_version,result_schema_version,model_schema_version,
            item_schema_version,config_json,config_sha256,result_json,result_sha256,
            created_at,app_version
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            identity,
            version.study_version_id,
            history.history_revision_id,
            history.observation_history_sha256,
            "doe.bayesian_optimization",
            method,
            count,
            policy,
            schema,
            schema,
            model,
            item,
            config,
            _sha(config),
            result,
            _sha(result),
            STAMP,
            "synthetic-test",
        ),
    )


def _snapshot(connection):
    return {
        table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        for table in TABLES
    }


def test_migration28_to_current_preserves_legacy_payload_bytes_hashes_and_owners(
    tmp_path, monkeypatch
):
    root = tmp_path / "fit migration \ud55c\uae00 workspace"
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 28)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 28)
        )
        store = metadata.initialize_metadata_store(root)
        assert store.schema_version == 28
        sources = [
            _study(root, vector=contract[0] >= 4, suffix=str(contract[0]))
            for contract in LEGACY_CONTRACTS
        ]
        with sqlite3.connect(store.path) as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            for contract, (version, trials, history) in zip(LEGACY_CONTRACTS, sources, strict=True):
                count = 2 if contract[0] == 5 else 1
                identity = f"batch-{contract[0]}"
                _insert_batch(
                    connection, version, history, contract, identity=identity, count=count
                )
                for rank, trial in enumerate(trials[:count], 1):
                    payload = f'{{ "synthetic_rank": {rank}, "source": "unchanged" }}\n'
                    connection.execute(
                        """INSERT INTO bayesian_recommendation_batch_items (
                            item_id,batch_id,trial_id,rank,item_schema_version,
                            item_result_json,item_result_sha256,created_at
                        ) VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            f"item-{contract[0]}-{rank}",
                            identity,
                            trial.trial_id,
                            rank,
                            contract[2],
                            payload,
                            _sha(payload),
                            STAMP,
                        ),
                    )
            version, _, history = sources[-1]
            current = (6, 6, 4, "0.11.0", "conditional_mc_desirability_beta_marginal_v1")
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                _insert_batch(connection, version, history, current, identity="not-supported-yet")
            before = _snapshot(connection)
            migrations_before = connection.execute(
                "SELECT * FROM schema_migrations ORDER BY version"
            ).fetchall()
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    migrated = metadata.initialize_metadata_store(root)
    assert migrated.schema_version == metadata.SCHEMA_VERSION
    with sqlite3.connect(migrated.path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("PRAGMA user_version").fetchone() == (metadata.SCHEMA_VERSION,)
        assert _snapshot(connection) == before
        assert (
            connection.execute(
                "SELECT * FROM schema_migrations WHERE version<=28 ORDER BY version"
            ).fetchall()
            == migrations_before
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        for config, config_sha, result, result_sha in connection.execute(
            "SELECT config_json,config_sha256,result_json,result_sha256 "
            "FROM bayesian_recommendation_batches"
        ):
            assert _sha(config) == config_sha
            assert _sha(result) == result_sha
        for payload, digest in connection.execute(
            "SELECT item_result_json,item_result_sha256 FROM bayesian_recommendation_batch_items"
        ):
            assert _sha(payload) == digest
        _insert_batch(connection, version, history, current, identity="fit-policy-now-supported")
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            _insert_batch(
                connection,
                version,
                history,
                (6, 5, 4, "0.11.0", current[-1]),
                identity="mixed-model-version",
            )
        after = _snapshot(connection)

    metadata.initialize_metadata_store(root)
    with sqlite3.connect(migrated.path) as connection:
        assert _snapshot(connection) == after
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
