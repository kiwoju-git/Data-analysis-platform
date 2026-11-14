"""Metadata37 preserves populated immutable planning graphs and sidecar bytes."""

import sqlite3
from uuid import uuid4

import pytest

from app.storage import metadata
from app.storage.bo_views import read_view
from tests.unit.test_bo_augmentation_renewal import legacy_selection as legacy_selection
from tests.unit.test_bo_views import source as source

TABLES = (
    "bayesian_studies",
    "bayesian_study_versions",
    "bayesian_trials",
    "bayesian_observation_history_revisions",
    "bayesian_planning_models",
    "bayesian_candidate_sets",
    "bayesian_candidate_revisions",
    "bayesian_planning_selections",
    "bayesian_augmentation_renewals",
    "bayesian_saved_views",
)


def snapshot(root):
    with sqlite3.connect(metadata.metadata_db_path(root)) as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in TABLES
        }


@pytest.mark.parametrize("fixture_name", ["source", "legacy_selection"])
def test_populated_graph_and_renewal_are_not_rewritten(request, monkeypatch, fixture_name):
    with monkeypatch.context() as old:
        old.setattr(metadata, "SCHEMA_VERSION", 36)
        old.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 36)
        )
        fixture = request.getfixturevalue(fixture_name)
        client, settings, study = fixture.client, fixture.settings, fixture.study
        if fixture_name == "legacy_selection":
            renewed = client.post(fixture.endpoint + "/renew", json=fixture.body)
            assert renewed.status_code == 201, renewed.text
        with sqlite3.connect(metadata.metadata_db_path(settings.workspace_root)) as db:
            db.row_factory = sqlite3.Row
            model = dict(db.execute("SELECT * FROM bayesian_planning_models LIMIT 1").fetchone())
        base = "/api/v1/bayesian-studies/" + study["study_id"]
        evaluated = client.post(
            base + "/planning-models/" + model["model_id"] + "/view-evaluations",
            json={
                "kind": "profiler_matrix",
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_history_sha256": model["history_sha256"],
                "holds": {"x": 5},
                "points_per_axis": 3,
            },
        )
        assert evaluated.status_code == 200, evaluated.text
        receipt = evaluated.json()
        saved = client.post(
            base + "/views",
            json={
                "request_id": str(uuid4()),
                "receipt_id": receipt["receipt_id"],
                "expected_model_sha256": model["snapshot_sha256"],
                "expected_request_sha256": receipt["request_sha256"],
                "expected_view_sha256": receipt["view_sha256"],
            },
        )
        assert saved.status_code == 201, saved.text
        value = saved.json()
        fixture.close()
        before = snapshot(settings.workspace_root)
    metadata.initialize_metadata_store(settings.workspace_root)
    assert snapshot(settings.workspace_root) == before
    with sqlite3.connect(metadata.metadata_db_path(settings.workspace_root)) as db:
        assert db.execute("PRAGMA user_version").fetchone() == (37,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert (
        read_view(settings.workspace_root, study["study_id"], value["view_id"]).model_dump(
            mode="json"
        )
        == value
    )
