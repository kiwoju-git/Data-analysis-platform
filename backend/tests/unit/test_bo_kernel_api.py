import hashlib
import json
import sqlite3
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from test_bayesian_batches_api import _completed_study
from test_bayesian_noise_api import _noise_request

from app.core.config import Settings
from app.main import create_app
from app.services.dedicated_report_sources import (
    list_dedicated_report_sources,
    prepare_dedicated_report_source,
)
from app.storage.metadata import metadata_db_path


def kernel_request(study, kind, count=1):
    body = _noise_request(study, count=count)
    body.update(schema_version=3, kernel={"kind": kind})
    if study["objective"]["goal_type"] == "match_target":
        body["acquisition"]["kind"] = "expected_target_improvement"
    return body


@pytest.mark.parametrize("kind", ["matern_5_2", "matern_3_2", "gaussian", "exponential"])
@pytest.mark.parametrize("goal,count", [("maximize", 1), ("match_target", 2)])
def test_kernel_review_spawn_confirm_restore_report(tmp_path, monkeypatch, kind, goal, count):
    settings = Settings(workspace_root=tmp_path)
    with TestClient(create_app(settings)) as client:
        study = _completed_study(client, goal_type=goal)
        base = f"/api/v1/bayesian-studies/{study['study_id']}"
        reviewed = client.post(
            f"{base}/recommendation-reviews", json=kernel_request(study, kind, count)
        )
        assert reviewed.status_code == 200, reviewed.json()
        review = reviewed.json()
        assert review["calculation"]["schema_version"] == 3
        assert client.get(base).json()["trials"] == study["trials"]
        model = review["calculation"]["shared_model"]
        assert model["schema_version"] == 4
        assert model["signal_kernel"]["family"] == kind
        assert model["factor_ids"] == [f["factor_id"] for f in study["factors"]]

        def forbidden(*args, **kwargs):
            raise AssertionError("Confirmation, restore and report cannot refit")

        monkeypatch.setattr("app.services.bayesian_noise_recommendations._run_worker", forbidden)
        path = f"{base}/recommendation-reviews/{review['review_id']}/confirm"
        confirmation = {"expected_config_sha256": review["config_sha256"]}
        response = client.post(path, json=confirmation)
        assert response.status_code == 201, response.json()
        batch = response.json()
        assert batch["method_version"] == "0.8.0"
        assert batch["shared_model"] == model
        assert batch["result_schema_version"] == batch["config_schema_version"] == 3
        for item, preview in zip(batch["items"], review["calculation"]["items"], strict=True):
            assert {key: item[key] for key in preview} == preview
        assert client.post(path, json=confirmation).json() == batch
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            before = connection.execute(
                "SELECT config_json,result_json,config_sha256,result_sha256 "
                "FROM bayesian_recommendation_batches"
            ).fetchall()
        source = next(
            item.source
            for item in list_dedicated_report_sources(settings, "bayesian_history_revision").items
            if item.source.attachment.kind == "batch"
        )
        for locale in ("en", "ko"):
            report = prepare_dedicated_report_source(settings, source, locale)
            rendered = report.body.render()
            assert "radial_scaled_euclidean_v1" in rendered
            assert "factor_bounds_normalized_0_1" in rendered
            assert report.payload["attachment"]["shared_model"] == model
            assert report.definition.renderer_version == "1.11.0"
            request = {"source": source.model_dump(mode="json"), "locale": locale}
            capability = client.post("/api/v1/reports/capability", json=request)
            assert capability.status_code == 200, capability.json()
            exported = client.post(
                "/api/v1/reports",
                json={
                    **request,
                    "expected_source_ref_sha256": capability.json()["source_ref_sha256"],
                },
            )
            assert exported.status_code == 201, exported.json()
            descriptor = exported.json()
            downloaded = client.post(
                f"/api/v1/reports/{descriptor['export_id']}/download",
                json={"source": request["source"], "expected_sha256": descriptor["sha256"]},
            )
            assert downloaded.status_code == 200
            assert hashlib.sha256(downloaded.content).hexdigest() == descriptor["sha256"]
            assert "radial_scaled_euclidean_v1" in downloaded.text
            assert client.get(f"/api/v1/reports/{descriptor['export_id']}").status_code == 200
        with sqlite3.connect(metadata_db_path(tmp_path)) as connection:
            assert (
                before
                == connection.execute(
                    "SELECT config_json,result_json,config_sha256,result_sha256 "
                    "FROM bayesian_recommendation_batches"
                ).fetchall()
            )
    with TestClient(create_app(settings)) as restarted:
        assert restarted.post(path, json=confirmation).json() == batch
        assert restarted.get(f"{base}/recommendation-batches/latest").json()["item"] == batch


def test_kernel_and_version_mismatch_rejected_before_commit(tmp_path, monkeypatch):
    from app.services import bayesian_noise_recommendations as service
    from app.statistics.bo_recommendation_core import calculate_noise_aware_batch

    app = create_app(Settings(workspace_root=tmp_path))
    with TestClient(app) as client:
        study = _completed_study(client)
        base = f"/api/v1/bayesian-studies/{study['study_id']}"
        path = f"{base}/recommendation-reviews"
        body = kernel_request(study, "gaussian")
        for bad in (
            {**body, "kernel": {"kind": "cubic"}},
            {**body, "schema_version": 2},
            {k: v for k, v in body.items() if k != "kernel"},
        ):
            assert client.post(path, json=bad).status_code == 422

        def tamper(payload, **kwargs):
            result = calculate_noise_aware_batch(payload)
            result["shared_model"]["signal_kernel"]["family"] = "exponential"
            return result

        monkeypatch.setattr(service, "_run_worker", tamper)
        assert client.post(path, json=body).status_code == 409
        assert client.get(base).json()["trials"] == study["trials"]
        monkeypatch.setattr(service, "_run_worker", lambda p, **kw: calculate_noise_aware_batch(p))
        review = client.post(path, json=body).json()
        entry = app.state.bayesian_reviews._entries[UUID(review["review_id"])]
        tampered = json.loads(entry.response_json)
        tampered["calculation"]["shared_model"]["factor_ids"] = ["different-factor"]
        from dataclasses import replace

        app.state.bayesian_reviews._entries[UUID(review["review_id"])] = replace(
            entry, response_json=json.dumps(tampered)
        )
        result = client.post(
            f"{path}/{review['review_id']}/confirm",
            json={"expected_config_sha256": review["config_sha256"]},
        )
        assert result.status_code == 409
        assert client.get(base).json()["trials"] == study["trials"]


def test_explicit_kernel_single_target_route_uses_same_versioned_batch(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        study = _completed_study(client, goal_type="match_target")
        base = f"/api/v1/bayesian-studies/{study['study_id']}"
        response = client.post(
            f"{base}/recommendations",
            json={
                "schema_version": 3,
                "kernel": {"kind": "gaussian"},
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
                "expected_history_sha256": study["observation_history"][
                    "observation_history_sha256"
                ],
                "search": {
                    "candidate_count": 32,
                    "local_start_count": 0,
                    "model_max_iterations": 20,
                },
            },
        )
        assert response.status_code == 201, response.json()
        batch = response.json()
        assert batch["batch_size"] == 1 and batch["result_schema_version"] == 3
        assert batch["shared_model"]["signal_kernel"]["family"] == "gaussian"
        assert batch["acquisition"]["kind"] == "expected_target_improvement"
        assert batch["items"][0]["planning"]["effective_sample_count"] == 0
        assert client.get(f"{base}/recommendation-batches/{batch['batch_id']}").json() == batch


def test_populated_metadata24_migration_preserves_legacy_hashes(tmp_path, monkeypatch):
    from app.storage import metadata
    from app.storage.workspace_backup import backup_workspace, restore_workspace

    root = tmp_path / "workspace with spaces"
    fixture_root = tmp_path / "synthetic scalar fixture source"
    with TestClient(create_app(Settings(workspace_root=fixture_root))) as client:
        study = _completed_study(client)
        base = f"/api/v1/bayesian-studies/{study['study_id']}"
        result = client.post(f"{base}/recommendation-batches", json=_noise_request(study))
        assert result.status_code == 201, result.json()
        batch = result.json()
        assert study["study_schema_version"] == 4
        assert study["observation_history"]["schema_version"] == 1
        assert (
            batch["config_schema_version"],
            batch["result_schema_version"],
            batch["model_schema_version"],
            batch["item_schema_version"],
        ) == (2, 2, 3, 2)
    # Build a genuine v24 database containing only its columns. The current
    # application requires migration and must not run against an unmigrated DB.
    with monkeypatch.context() as old:
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 24)
        )
        old.setattr(metadata, "SCHEMA_VERSION", 24)
        metadata.initialize_metadata_store(root)
    fixture_tables = (
        "bayesian_studies",
        "bayesian_study_versions",
        "bayesian_trials",
        "bayesian_observation_history_revisions",
        "bayesian_observation_history_heads",
        "bayesian_recommendation_batches",
        "bayesian_recommendation_batch_items",
    )
    legacy_columns = {}
    with (
        sqlite3.connect(metadata_db_path(fixture_root)) as source,
        sqlite3.connect(metadata_db_path(root)) as destination,
    ):
        destination.execute("PRAGMA foreign_keys=ON")
        for table in fixture_tables:
            columns = [row[1] for row in destination.execute(f"PRAGMA table_info({table})")]
            legacy_columns[table] = ",".join(columns)
            rows = source.execute(
                f"SELECT {legacy_columns[table]} FROM {table} ORDER BY 1"
            ).fetchall()
            placeholders = ",".join("?" for _ in columns)
            destination.executemany(
                f"INSERT INTO {table} ({legacy_columns[table]}) VALUES ({placeholders})",
                rows,
            )
        assert destination.execute("PRAGMA foreign_key_check").fetchall() == []
        assert "response_values_json" not in legacy_columns["bayesian_trials"]
    tables = fixture_tables
    with sqlite3.connect(metadata_db_path(root)) as connection:
        before = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in tables
        }
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 24
    archive = tmp_path / "metadata24.zip"
    backup_workspace(root, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    restored = tmp_path / "restored"
    restore_workspace(archive, restored)
    with TestClient(create_app(Settings(workspace_root=restored))) as client:
        read = client.get(f"{base}/recommendation-batches/{batch['batch_id']}")
        assert read.status_code == 200, read.json()
        assert read.json() == batch
        with sqlite3.connect(metadata_db_path(restored)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 34
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
            for table in tables:
                assert (
                    before[table]
                    == connection.execute(
                        f"SELECT {legacy_columns[table]} FROM {table} ORDER BY 1"
                    ).fetchall()
                )
            assert (
                connection.execute(
                    "SELECT count(*) FROM bayesian_trials WHERE response_values_json IS NOT NULL"
                ).fetchone()[0]
                == 0
            )
        trial = batch["items"][0]["trial"]
        done = client.put(
            f"{base}/trials/{trial['trial_id']}/observation",
            json={
                "objective_value": 0.5,
                "expected_history_revision_id": study["observation_history"]["history_revision_id"],
            },
        )
        assert done.status_code == 200, done.json()
        current = client.get(base).json()
        created = client.post(
            f"{base}/recommendation-batches", json=kernel_request(current, "gaussian")
        )
        assert created.status_code == 201, created.json()
        assert created.json()["result_schema_version"] == 3
        assert client.get(f"{base}/recommendation-batches/{batch['batch_id']}").status_code == 200
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
