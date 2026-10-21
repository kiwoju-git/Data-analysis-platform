"""Storage-only fixtures for immutable RSM plot views; no model is fitted."""

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from app.storage import factorial_analysis_assets as assets
from app.storage.metadata import (
    MIGRATIONS,
    SCHEMA_VERSION,
    ExperimentDesignAnalysisRecord,
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    WorkspaceAssetStorageConflict,
    initialize_metadata_store,
    insert_experiment_design_analysis_record,
    insert_experiment_design_records,
    metadata_db_path,
)

NOW = "2026-10-20T00:00:00+00:00"
HTML = b"<!doctype html><html><body>Stored plot view report</body></html>"


def _owner(root: Path) -> ExperimentDesignAnalysisRecord:
    design_id, version_id, analysis_id = (str(uuid4()) for _ in range(3))
    insert_experiment_design_records(
        root,
        ExperimentDesignRecord(
            design_id,
            "doe.response_surface",
            "0.1.0",
            "central_composite",
            "Synthetic RSM owner",
            "designed",
            1,
            NOW,
            NOW,
            "test",
        ),
        ExperimentDesignVersionRecord(version_id, design_id, 1, "[]", "{}", 1, "a" * 64, NOW),
        [],
    )
    result_json = json.dumps(
        {"storage_fixture": True, "analysis_id": analysis_id},
        sort_keys=True,
        separators=(",", ":"),
    )
    record = ExperimentDesignAnalysisRecord(
        analysis_id,
        version_id,
        "Synthetic response",
        "doe.response_surface",
        "0.1.0",
        '{"storage_fixture":true}',
        result_json,
        hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        "b" * 64,
        NOW,
        "test",
    )
    insert_experiment_design_analysis_record(
        root, design_id=design_id, record=record, updated_at=NOW
    )
    return record


def _asset(
    owner: ExperimentDesignAnalysisRecord,
    kind: assets.AssetKind = "plot_view",
    *,
    schema: int = 1,
    content: bytes | None = None,
) -> tuple[assets.FactorialAnalysisAsset, bytes]:
    identifier = str(uuid4())
    if content is None:
        content = json.dumps(
            {
                "schema_version": schema,
                "storage_fixture": True,
                "plot_view_id": identifier,
                "analysis_id": owner.analysis_id,
                "source_analysis_sha256": owner.result_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    return (
        assets.FactorialAnalysisAsset(
            identifier,
            owner.analysis_id,
            kind,
            schema,
            "en" if kind == "html_report" else None,
            owner.result_sha256,
            hashlib.sha256(content).hexdigest(),
            "text/html" if kind == "html_report" else "application/json",
            len(content),
            NOW,
        ),
        content,
    )


def _store(
    root: Path, owner: ExperimentDesignAnalysisRecord, kind: assets.AssetKind = "plot_view"
) -> tuple[assets.FactorialAnalysisAsset, bytes]:
    record, content = _asset(owner, kind)
    assets.insert_asset(root, record, content)
    return record, content


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "RSM workspace with spaces" / "한글"
    initialize_metadata_store(root)
    return root


def _legacy22(root: Path) -> None:
    metadata_db_path(root).parent.mkdir(parents=True)
    with closing(sqlite3.connect(metadata_db_path(root))) as connection, connection:
        for migration in MIGRATIONS:
            if migration.version > 22:
                break
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version=22")


def test_schema22_upgrade_preserves_all_existing_doe_asset_bytes_and_hashes(tmp_path):
    root = tmp_path / "legacy22 한글"
    _legacy22(root)
    owner = _owner(root)
    for kind, schema, content in (
        ("prediction", 1, '{"schema_version":1,"name":"기존 예측"}'.encode()),
        ("html_report", 1, "<h1>기존 HTML schema 1</h1>".encode()),
        ("html_report", 2, "<h1>기존 HTML schema 2</h1>".encode()),
    ):
        record, payload = _asset(owner, kind, schema=schema, content=content)
        assets.insert_asset(root, record, payload)
    new_record, new_payload = _asset(owner)
    with pytest.raises(sqlite3.IntegrityError):
        assets.insert_asset(root, new_record, new_payload)
    with closing(sqlite3.connect(metadata_db_path(root))) as connection:
        before_assets = connection.execute(
            "SELECT * FROM experiment_design_analysis_assets ORDER BY asset_id"
        ).fetchall()
        before_analysis = connection.execute("SELECT * FROM experiment_design_analyses").fetchall()
        before_migrations = connection.execute(
            "SELECT version,name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert len(before_assets) == 3

    upgraded = initialize_metadata_store(root)
    assert SCHEMA_VERSION == 24
    assert upgraded.schema_version == SCHEMA_VERSION
    with closing(sqlite3.connect(metadata_db_path(root))) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert (
            connection.execute(
                "SELECT * FROM experiment_design_analysis_assets ORDER BY asset_id"
            ).fetchall()
            == before_assets
        )
        assert (
            connection.execute("SELECT * FROM experiment_design_analyses").fetchall()
            == before_analysis
        )
        assert (
            connection.execute(
                "SELECT version,name FROM schema_migrations WHERE version<=22 ORDER BY version"
            ).fetchall()
            == before_migrations
        )
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='index' "
                "AND name='idx_experiment_analysis_assets'"
            ).fetchone()
            is not None
        )
    assets.insert_asset(root, new_record, new_payload)
    assert assets.get_asset(root, owner.analysis_id, new_record.asset_id) == (
        new_record,
        new_payload,
    )


def test_plot_view_schema1_roundtrip_filter_and_owner_isolation(workspace):
    owner, other_owner = _owner(workspace), _owner(workspace)
    view, content = _store(workspace, owner)
    prediction, _ = _store(workspace, owner, "prediction")
    assert assets.get_asset(workspace, owner.analysis_id, view.asset_id) == (view, content)
    assert assets.get_asset(workspace, other_owner.analysis_id, view.asset_id) is None
    assert assets.list_assets(workspace, owner.analysis_id, "plot_view") == [view]
    assert assets.list_assets(workspace, owner.analysis_id, "prediction") == [prediction]
    assert assets.list_assets(workspace, other_owner.analysis_id, "plot_view") == []


@pytest.mark.parametrize("schema", [0, 2])
def test_plot_view_rejects_unsupported_schema_without_inserting(workspace, schema):
    owner = _owner(workspace)
    record, content = _asset(owner, schema=schema)
    with pytest.raises(sqlite3.IntegrityError):
        assets.insert_asset(workspace, record, content)
    assert assets.list_assets(workspace, owner.analysis_id) == []


def test_plot_view_insert_and_read_verify_exact_content_hash(workspace):
    owner = _owner(workspace)
    record, content = _asset(owner)
    with pytest.raises(WorkspaceAssetStorageConflict, match="doe_analysis_asset_checksum_mismatch"):
        assets.insert_asset(workspace, replace(record, sha256="0" * 64), content)
    assert assets.list_assets(workspace, owner.analysis_id) == []
    assets.insert_asset(workspace, record, content)
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute(
            "UPDATE experiment_design_analysis_assets SET content=? WHERE asset_id=?",
            (b"x" * len(content), record.asset_id),
        )
    with pytest.raises(WorkspaceAssetStorageConflict, match="doe_analysis_asset_checksum_mismatch"):
        assets.get_asset(workspace, owner.analysis_id, record.asset_id)


@pytest.mark.parametrize("mismatch", ["missing_owner", "source_hash", "source_bytes"])
def test_plot_view_source_mismatch_is_atomic(workspace, mismatch):
    owner = _owner(workspace)
    record, content = _asset(owner)
    if mismatch == "missing_owner":
        record = replace(record, analysis_id=str(uuid4()))
    elif mismatch == "source_hash":
        record = replace(record, source_analysis_sha256="0" * 64)
    else:
        with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
            connection.execute(
                "UPDATE experiment_design_analyses SET result_json=? WHERE analysis_id=?",
                ('{"tampered":true}', owner.analysis_id),
            )
    with pytest.raises(
        WorkspaceAssetStorageConflict, match="doe_factorial_prediction_source_changed"
    ):
        assets.insert_asset(workspace, record, content)
    assert assets.list_assets(workspace, owner.analysis_id) == []
    assert assets.list_assets(workspace, record.analysis_id) == []


def test_plot_view_delete_requires_exact_owner_and_hash(workspace):
    owner, other_owner = _owner(workspace), _owner(workspace)
    view, content = _store(workspace, owner)
    sibling, sibling_content = _store(workspace, owner)
    for owner_id, expected_sha in (
        (other_owner.analysis_id, view.sha256),
        (owner.analysis_id, "0" * 64),
    ):
        with pytest.raises(
            WorkspaceAssetStorageConflict, match="doe_analysis_asset_deletion_conflict"
        ):
            assets.delete_asset(workspace, owner_id, view.asset_id, expected_sha)
        assert assets.get_asset(workspace, owner.analysis_id, view.asset_id) == (view, content)
    assert assets.delete_asset(workspace, owner.analysis_id, view.asset_id, view.sha256)
    assert assets.get_asset(workspace, owner.analysis_id, view.asset_id) is None
    assert assets.get_asset(workspace, owner.analysis_id, sibling.asset_id) == (
        sibling,
        sibling_content,
    )


def test_analysis_delete_cascades_views_but_preserves_other_owner(workspace):
    owner, other_owner = _owner(workspace), _owner(workspace)
    _store(workspace, owner)
    _store(workspace, owner, "prediction")
    other, other_content = _store(workspace, other_owner)
    before = assets.analysis_deletion_snapshot(workspace, owner.analysis_id)
    assert before is not None
    assets.delete_analysis(workspace, owner.analysis_id, before[0])
    assert assets.analysis_deletion_snapshot(workspace, owner.analysis_id) is None
    assert assets.list_assets(workspace, owner.analysis_id) == []
    assert assets.get_asset(workspace, other_owner.analysis_id, other.asset_id) == (
        other,
        other_content,
    )
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_new_view_invalidates_analysis_deletion_preflight(workspace):
    owner = _owner(workspace)
    _store(workspace, owner)
    before = assets.analysis_deletion_snapshot(workspace, owner.analysis_id)
    assert before is not None
    second, content = _store(workspace, owner)
    with pytest.raises(WorkspaceAssetStorageConflict, match="doe_analysis_deletion_conflict"):
        assets.delete_analysis(workspace, owner.analysis_id, before[0])
    assert assets.get_asset(workspace, owner.analysis_id, second.asset_id) == (second, content)


@pytest.mark.parametrize("dependency_kind", ["prediction", "plot_view"])
def test_report_dependency_checks_preserve_default_prediction_contract(workspace, dependency_kind):
    owner = _owner(workspace)
    dependency, _ = _store(workspace, owner, dependency_kind)
    report, content = _asset(owner, "html_report", schema=2, content=HTML)
    options = {} if dependency_kind == "prediction" else {"dependency_kind": "plot_view"}
    assets.insert_asset(
        workspace,
        report,
        content,
        dependency_asset=(dependency.asset_id, dependency.sha256),
        **options,
    )
    assert assets.get_asset(workspace, owner.analysis_id, report.asset_id) == (report, content)


@pytest.mark.parametrize(
    "mismatch", ["missing", "wrong_owner", "wrong_kind", "wrong_hash", "tampered_bytes", "deleted"]
)
def test_report_view_dependency_mismatch_never_publishes_html(workspace, mismatch):
    owner, other_owner = _owner(workspace), _owner(workspace)
    dependency, content = _store(
        workspace,
        other_owner if mismatch == "wrong_owner" else owner,
        "prediction" if mismatch == "wrong_kind" else "plot_view",
    )
    dependency_id, expected_hash = dependency.asset_id, dependency.sha256
    if mismatch == "missing":
        dependency_id = str(uuid4())
    elif mismatch == "wrong_hash":
        expected_hash = "0" * 64
    elif mismatch == "tampered_bytes":
        with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
            connection.execute(
                "UPDATE experiment_design_analysis_assets SET content=? WHERE asset_id=?",
                (b"x" * len(content), dependency.asset_id),
            )
    elif mismatch == "deleted":
        assets.delete_asset(workspace, owner.analysis_id, dependency.asset_id, dependency.sha256)
    report, html = _asset(owner, "html_report", schema=2, content=HTML)
    with pytest.raises(WorkspaceAssetStorageConflict, match="stored_report_source_changed"):
        assets.insert_asset(
            workspace,
            report,
            html,
            dependency_asset=(dependency_id, expected_hash),
            dependency_kind="plot_view",
        )
    assert assets.list_assets(workspace, owner.analysis_id, "html_report") == []
