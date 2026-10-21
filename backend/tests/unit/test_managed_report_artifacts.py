import hashlib
import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.schemas.reports import (
    BayesianBatchAttachment,
    BayesianHistoryReportSource,
    BayesianRecommendationAttachment,
    LhsDesignReportSource,
)
from app.core.config import Settings
from app.main import create_app
from app.services.report_source_contract import report_source_sha256
from app.services.workspace_assets import list_workspace_assets
from app.storage import managed_report_artifacts as reports
from app.storage.bayesian_studies import (
    BayesianStorageConflict,
    delete_bayesian_study_graph_record,
    get_bayesian_study_deletion_graph_record,
)
from app.storage.metadata import (
    MIGRATIONS,
    SCHEMA_VERSION,
    ExperimentDesignRecord,
    ExperimentDesignVersionRecord,
    WorkspaceAssetStorageConflict,
    delete_experiment_design_record,
    get_experiment_design_deletion_snapshot,
    get_workspace_summary_counts,
    initialize_metadata_store,
    insert_experiment_design_records,
    metadata_db_path,
)

NOW = "2026-10-18T00:00:00+00:00"
HTML = b"<!doctype html><html><body>Stored synthetic report</body></html>"


def _lhs(root: Path) -> LhsDesignReportSource:
    design_id, version_id = str(uuid4()), str(uuid4())
    insert_experiment_design_records(
        root,
        ExperimentDesignRecord(
            design_id,
            "doe.latin_hypercube",
            "0.3.0",
            "lhs",
            "Synthetic LHS",
            "designed",
            1,
            NOW,
            NOW,
            "test",
        ),
        ExperimentDesignVersionRecord(version_id, design_id, 1, "[]", "{}", 1, "a" * 64, NOW),
        [],
    )
    return LhsDesignReportSource(
        design_id=design_id, design_version_id=version_id, expected_source_sha256="a" * 64
    )


def _bo(root: Path) -> BayesianHistoryReportSource:
    study_id, version_id, history_id = (str(uuid4()) for _ in range(3))
    with closing(sqlite3.connect(metadata_db_path(root))) as connection, connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "INSERT INTO bayesian_studies VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                study_id,
                "doe.bayesian_optimization",
                "0.1.0",
                "Synthetic BO",
                "abandoned",
                1,
                NOW,
                NOW,
                "test",
                None,
            ),
        )
        connection.execute(
            "INSERT INTO bayesian_study_versions VALUES (?,?,?,?,?,?,?,?,?,?)",
            (version_id, study_id, 1, 1, "[]", "{}", "[]", "{}", "b" * 64, NOW),
        )
        connection.execute(
            "INSERT INTO bayesian_observation_history_revisions VALUES (?,?,?,?,?,?,?,?,?)",
            (history_id, version_id, 1, 1, "[]", 0, "c" * 64, None, NOW),
        )
        connection.execute(
            "INSERT INTO bayesian_observation_history_heads VALUES (?,?,?)",
            (version_id, history_id, NOW),
        )
    return BayesianHistoryReportSource(
        study_id=study_id,
        study_version_id=version_id,
        definition_sha256="b" * 64,
        history_revision_id=history_id,
        expected_source_sha256="c" * 64,
    )


def _create(root, source, **overrides):
    options = dict(
        source=source,
        expected_source_ref_sha256=report_source_sha256(source),
        content=HTML,
        locale="en",
        renderer_id="synthetic",
        renderer_version="1",
        report_level="full",
        section_manifest_json='[{"section_id":"summary"}]',
        created_at=NOW,
    )
    options.update(overrides)
    return reports.create_managed_report(root, **options)


def _delete_design(root, snapshot):
    return delete_experiment_design_record(
        root,
        design_id=snapshot.design.design_id,
        expected_design_sha256=snapshot.design_sha256,
        expected_counts=(
            snapshot.version_count,
            snapshot.run_count,
            snapshot.response_count,
            snapshot.response_revision_count,
            snapshot.analysis_count,
            snapshot.prediction_count,
            snapshot.report_count,
        ),
        expected_analysis_assets_sha256=snapshot.analysis_assets_sha256,
        expected_managed_reports_sha256=snapshot.managed_reports_sha256,
    )


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace with spaces" / "한글"
    initialize_metadata_store(root)
    return root


def test_schema20_upgrade_is_additive_and_preserves_legacy_rows_and_files(tmp_path):
    root = tmp_path / "old"
    metadata_db_path(root).parent.mkdir(parents=True)
    with closing(sqlite3.connect(metadata_db_path(root))) as connection, connection:
        for migration in MIGRATIONS[:20]:
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version=20")
    source = _lhs(root)
    analysis_id = str(uuid4())
    with closing(sqlite3.connect(metadata_db_path(root))) as connection, connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "INSERT INTO experiment_design_analyses VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                analysis_id,
                str(source.design_version_id),
                "response",
                "doe.factorial_design",
                "0.8.0",
                "{}",
                "{}",
                "b" * 64,
                "c" * 64,
                NOW,
                "test",
            ),
        )
        for kind, content, media in (
            ("prediction", b'{"schema_version":1,"legacy":"prediction"}', "application/json"),
            ("html_report", b"<h1>Legacy HTML schema 1</h1>", "text/html"),
        ):
            connection.execute(
                "INSERT INTO experiment_design_analysis_assets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    analysis_id,
                    kind,
                    1,
                    "en",
                    "b" * 64,
                    hashlib.sha256(content).hexdigest(),
                    media,
                    len(content),
                    content,
                    NOW,
                ),
            )
        original_assets = connection.execute(
            "SELECT * FROM experiment_design_analysis_assets ORDER BY asset_id"
        ).fetchall()
    legacy = root / "legacy-result.json"
    legacy.write_bytes(b"legacy unchanged")
    with closing(sqlite3.connect(metadata_db_path(root))) as connection:
        before = connection.execute("SELECT * FROM experiment_design_versions").fetchall()
    assert initialize_metadata_store(root).schema_version == SCHEMA_VERSION
    with closing(sqlite3.connect(metadata_db_path(root))) as connection:
        assert connection.execute("SELECT * FROM experiment_design_versions").fetchall() == before
        assert connection.execute("SELECT count(*) FROM managed_report_artifacts").fetchone() == (
            0,
        )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert (
            connection.execute(
                "SELECT * FROM experiment_design_analysis_assets ORDER BY asset_id"
            ).fetchall()
            == original_assets
        )
        content = b"<h1>Managed HTML schema 2</h1>"
        values = (
            str(uuid4()),
            analysis_id,
            "html_report",
            2,
            "en",
            "b" * 64,
            hashlib.sha256(content).hexdigest(),
            "text/html",
            len(content),
            content,
            NOW,
        )
        connection.execute(
            "INSERT INTO experiment_design_analysis_assets VALUES (?,?,?,?,?,?,?,?,?,?,?)", values
        )
        for kind, version in (("prediction", 2), ("html_report", 3)):
            with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
                connection.execute(
                    "INSERT INTO experiment_design_analysis_assets VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid4()), analysis_id, kind, version, *values[4:]),
                )
    assert legacy.read_bytes() == b"legacy unchanged"
    assert _create(root, source).source_payload_sha256 == "a" * 64


@pytest.mark.parametrize("factory", [_lhs, _bo])
def test_create_roundtrip_discovery_and_exact_delete(workspace, factory):
    source = factory(workspace)
    record = _create(workspace, source)
    assert reports.get_managed_report(workspace, record.report_id) == record
    assert reports.list_managed_reports(workspace, source=source) == [record]
    assert reports.read_managed_report(workspace, record) == HTML
    assert record.sha256 == hashlib.sha256(HTML).hexdigest()
    assert (workspace / record.artifact_path).is_file()
    assert not list((workspace / record.artifact_path).parent.glob(".*.q"))
    catalog = list_workspace_assets(
        Settings(workspace_root=workspace),
        category="analyses",
        method_id=None,
        status_filter=None,
        pinned=None,
        search=None,
        sort="created_desc",
        offset=0,
        limit=100,
    )
    assert any(
        item.asset_id == record.report_id
        and item.asset_type == "managed_report"
        and item.open_target.path == f"/reports?report_id={record.report_id}"
        for item in catalog.items
    )
    assert get_workspace_summary_counts(workspace).export_report_count == 1
    reports.delete_managed_report(
        workspace,
        report_id=record.report_id,
        expected_sha256=record.sha256,
        expected_source_ref_sha256=record.source_ref_sha256,
    )
    assert reports.get_managed_report(workspace, record.report_id) is None
    assert not (workspace / record.artifact_path).exists()


@pytest.mark.parametrize("factory", [_lhs, _bo])
def test_create_rejects_stale_or_wrong_owner_without_files(workspace, factory):
    source = factory(workspace)
    stale = source.model_copy(update={"expected_source_sha256": "e" * 64})
    with pytest.raises(reports.ManagedReportStorageError, match="source_conflict"):
        _create(workspace, stale)
    key = "design_id" if isinstance(source, LhsDesignReportSource) else "study_id"
    wrong = source.model_copy(update={key: uuid4()})
    with pytest.raises(reports.ManagedReportStorageError, match="source_not_found"):
        _create(workspace, wrong)
    assert reports.list_managed_reports(workspace) == []
    assert not (workspace / "workspaces/reports").exists()


def test_create_limit_and_size_checked_before_publishing(workspace, monkeypatch):
    source = _lhs(workspace)
    assert reports.MAX_REPORTS_PER_OWNER == 100
    monkeypatch.setattr(reports, "MAX_REPORTS_PER_OWNER", 2)
    first, second = _create(workspace, source), _create(workspace, source)
    with pytest.raises(reports.ManagedReportStorageError, match="limit_exceeded"):
        _create(workspace, source)
    with pytest.raises(reports.ManagedReportStorageError, match="size_invalid"):
        _create(workspace, source, content=b"")
    assert {record.report_id for record in reports.list_managed_reports(workspace)} == {
        first.report_id,
        second.report_id,
    }


def test_insert_failure_removes_only_its_new_files(workspace):
    source = _lhs(workspace)
    existing = _create(workspace, source)
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute(
            "CREATE TRIGGER fail_report BEFORE INSERT ON managed_report_artifacts "
            "BEGIN SELECT RAISE(ABORT,'injected failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        _create(workspace, source)
    assert reports.list_managed_reports(workspace) == [existing]
    assert reports.read_managed_report(workspace, existing) == HTML
    assert len(list((workspace / "workspaces/reports").iterdir())) == 1


def test_design_delete_cas_detects_same_count_report_replacement(workspace):
    source = _lhs(workspace)
    first = _create(workspace, source)
    snapshot = get_experiment_design_deletion_snapshot(workspace, str(source.design_id))
    reports.delete_managed_report(
        workspace,
        report_id=first.report_id,
        expected_sha256=first.sha256,
        expected_source_ref_sha256=first.source_ref_sha256,
    )
    second = _create(workspace, source)
    with pytest.raises(WorkspaceAssetStorageConflict, match="deletion_conflict"):
        _delete_design(workspace, snapshot)
    assert reports.read_managed_report(workspace, second) == HTML
    current = get_experiment_design_deletion_snapshot(workspace, str(source.design_id))
    assert current.report_count == snapshot.report_count == 1
    _delete_design(workspace, current)
    assert reports.get_managed_report(workspace, second.report_id) is None
    assert not (workspace / second.artifact_path).exists()


@pytest.mark.parametrize("factory", [_lhs, _bo])
def test_owner_delete_sql_failure_restores_metadata_and_files(workspace, factory):
    source = factory(workspace)
    record = _create(workspace, source)
    table = (
        "experiment_designs" if isinstance(source, LhsDesignReportSource) else "bayesian_studies"
    )
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute(
            f"CREATE TRIGGER fail_owner BEFORE DELETE ON {table} "
            "BEGIN SELECT RAISE(ABORT,'injected failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        if isinstance(source, LhsDesignReportSource):
            _delete_design(
                workspace, get_experiment_design_deletion_snapshot(workspace, str(source.design_id))
            )
        else:
            graph = get_bayesian_study_deletion_graph_record(workspace, str(source.study_id))
            delete_bayesian_study_graph_record(workspace, expected=graph)
    assert reports.get_managed_report(workspace, record.report_id) == record
    assert reports.read_managed_report(workspace, record) == HTML


def test_bo_history_only_cascade_and_report_race(workspace):
    source = _bo(workspace)
    graph = get_bayesian_study_deletion_graph_record(workspace, str(source.study_id))
    record = _create(workspace, source)
    with pytest.raises(BayesianStorageConflict, match="deletion_conflict"):
        delete_bayesian_study_graph_record(workspace, expected=graph)
    graph = get_bayesian_study_deletion_graph_record(workspace, str(source.study_id))
    assert graph.report_count == 1 and graph.report_bytes == len(HTML)
    delete_bayesian_study_graph_record(workspace, expected=graph)
    assert reports.get_managed_report(workspace, record.report_id) is None
    assert not (workspace / record.artifact_path).exists()


def test_two_connection_creation_and_owner_delete_are_atomic(workspace):
    source = _lhs(workspace)
    snapshot = get_experiment_design_deletion_snapshot(workspace, str(source.design_id))

    def create():
        try:
            return _create(workspace, source)
        except reports.ManagedReportStorageError as error:
            return error.code

    def delete():
        try:
            _delete_design(workspace, snapshot)
            return "deleted"
        except WorkspaceAssetStorageConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        created, deleted = pool.submit(create), pool.submit(delete)
        creation, deletion = created.result(), deleted.result()
    if deletion == "deleted":
        assert creation == "managed_report_source_not_found"
        assert reports.list_managed_reports(workspace) == []
    else:
        assert isinstance(creation, reports.ManagedReportArtifact)
        assert reports.read_managed_report(workspace, creation) == HTML


def test_recovery_restores_rollback_and_cleans_committed_quarantine(workspace):
    source = _lhs(workspace)
    record = _create(workspace, source)
    quarantine = reports.ReportQuarantine(workspace, (record,))
    quarantine.move()
    assert reports.recover_managed_report_files(workspace) == (1, 0, 0)
    assert reports.read_managed_report(workspace, record) == HTML
    quarantine = reports.ReportQuarantine(workspace, (record,))
    quarantine.move()
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute(
            "DELETE FROM managed_report_artifacts WHERE report_id=?", (record.report_id,)
        )
    assert reports.recover_managed_report_files(workspace) == (0, 1, 0)
    assert not (workspace / record.artifact_path).parent.exists()


def test_recovery_creation_marker_and_unknown_files(workspace):
    source = _lhs(workspace)
    record = _create(workspace, source)
    path = reports._safe_path(workspace, record.report_id)
    marker = path.parent / f".create-{record.sha256}-{record.size_bytes}.q"
    marker.write_bytes(b"pending\n")
    unknown = path.parent / ".unknown-file"
    unknown.write_bytes(b"preserve")
    assert reports.recover_managed_report_files(workspace) == (0, 1, 0)
    assert reports.read_managed_report(workspace, record) == HTML
    marker.write_bytes(b"pending\n")
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute(
            "DELETE FROM managed_report_artifacts WHERE report_id=?", (record.report_id,)
        )
    assert reports.recover_managed_report_files(workspace) == (0, 1, 0)
    assert not path.exists() and unknown.read_bytes() == b"preserve"


def test_read_rejects_corruption_wrong_path_and_source_metadata(workspace):
    record = _create(workspace, _lhs(workspace))
    with pytest.raises(reports.ManagedReportStorageError, match="integrity_invalid"):
        reports.read_managed_report(workspace, replace(record, artifact_path="../secret"))
    with pytest.raises(reports.ManagedReportStorageError, match="integrity_invalid"):
        reports.read_managed_report(workspace, replace(record, source_payload_sha256="0" * 64))
    (workspace / record.artifact_path).write_bytes(b"corrupt")
    with pytest.raises(reports.ManagedReportStorageError, match="integrity_invalid"):
        reports.read_managed_report(workspace, record)
    with pytest.raises(reports.ManagedReportStorageError):
        reports.delete_managed_report(
            workspace,
            report_id=record.report_id,
            expected_sha256=record.sha256,
            expected_source_ref_sha256=record.source_ref_sha256,
        )
    assert reports.get_managed_report(workspace, record.report_id) == record


def test_composite_fk_rejects_cross_study_history_even_with_valid_ids(workspace):
    first, second = _bo(workspace), _bo(workspace)
    original = _create(workspace, first)
    invalid = replace(
        original, report_id=str(uuid4()), history_revision_id=str(second.history_revision_id)
    )
    invalid = replace(invalid, artifact_path=f"workspaces/reports/{invalid.report_id}/report.html")
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute("PRAGMA foreign_keys=ON")
        fields = asdict(invalid)
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            connection.execute(
                f"INSERT INTO managed_report_artifacts ({','.join(fields)}) "
                f"VALUES ({','.join('?' for _ in fields)})",
                tuple(fields.values()),
            )


@pytest.mark.parametrize("kind", ["recommendation", "batch"])
def test_attachment_exact_history_json_hash_and_fk(workspace, kind):
    source = _bo(workspace)
    attachment_id = str(uuid4())
    result = json.dumps({"result_sha256": "d" * 64}, separators=(",", ":"))
    digest = hashlib.sha256(result.encode()).hexdigest()
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute("PRAGMA foreign_keys=ON")
        if kind == "recommendation":
            trial_id = str(uuid4())
            connection.execute(
                "INSERT INTO bayesian_trials (trial_id, study_version_id, trial_number, "
                "origin, state, actual_coordinates_json, normalized_coordinates_json, "
                "coordinates_sha256, objective_value, created_at, closed_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    trial_id,
                    str(source.study_version_id),
                    1,
                    "recommendation",
                    "pending",
                    "{}",
                    "{}",
                    "f" * 64,
                    None,
                    NOW,
                    None,
                ),
            )
            connection.execute(
                "INSERT INTO bayesian_recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    attachment_id,
                    str(source.study_version_id),
                    trial_id,
                    str(source.history_revision_id),
                    source.expected_source_sha256,
                    "doe.bayesian_optimization",
                    "0.1.0",
                    1,
                    1,
                    1,
                    "{}",
                    "f" * 64,
                    result,
                    digest,
                    "d" * 64,
                    NOW,
                    "test",
                ),
            )
            attachment = BayesianRecommendationAttachment(
                recommendation_id=attachment_id,
                result_json_sha256=digest,
                result_payload_sha256="d" * 64,
            )
        else:
            connection.execute(
                "INSERT INTO bayesian_recommendation_batches "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    attachment_id,
                    str(source.study_version_id),
                    str(source.history_revision_id),
                    source.expected_source_sha256,
                    "doe.bayesian_optimization",
                    "0.1.0",
                    1,
                    "greedy_posterior_mean_fantasy_ei_v1",
                    1,
                    1,
                    2,
                    1,
                    "{}",
                    "f" * 64,
                    result,
                    digest,
                    NOW,
                    "test",
                ),
            )
            attachment = BayesianBatchAttachment(
                batch_id=attachment_id,
                result_json_sha256=digest,
                result_payload_sha256="d" * 64,
            )
    attached = source.model_copy(update={"attachment": attachment})
    record = _create(workspace, attached)
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection:
        connection.row_factory = sqlite3.Row
        reports.validate_managed_report_record(connection, record)
    other = _bo(workspace).model_copy(update={"attachment": attachment})
    with pytest.raises(reports.ManagedReportStorageError, match="source_conflict"):
        _create(workspace, other)
    table = (
        "bayesian_recommendations"
        if kind == "recommendation"
        else "bayesian_recommendation_batches"
    )
    with closing(sqlite3.connect(metadata_db_path(workspace))) as connection, connection:
        connection.execute(f"UPDATE {table} SET result_json='{{}}'")
    with pytest.raises(reports.ManagedReportStorageError, match="source_conflict"):
        _create(workspace, attached)


def test_source_and_section_json_are_canonical_and_bounded(workspace):
    source = _lhs(workspace)
    with pytest.raises(reports.ManagedReportStorageError, match="source_conflict"):
        _create(workspace, source, expected_source_ref_sha256="0" * 64)
    for value in ["null", '{ "a": 1 }', '{"value":"' + "x" * 65536 + '"}']:
        with pytest.raises(reports.ManagedReportStorageError, match="integrity_invalid"):
            _create(workspace, source, section_manifest_json=value)
    record = _create(workspace, source)
    with pytest.raises(reports.ManagedReportStorageError, match="integrity_invalid"):
        reports.read_managed_report(workspace, replace(record, source_ref_json=None))


def test_server_selected_report_id_is_exact_and_cannot_overwrite(workspace):
    source = _lhs(workspace)
    report_id = str(uuid4())
    record = _create(workspace, source, report_id=report_id)
    assert record.report_id == report_id
    with pytest.raises(reports.ManagedReportStorageError, match="managed_report_conflict"):
        _create(workspace, source, report_id=report_id, content=b"replacement")
    with pytest.raises(reports.ManagedReportStorageError, match="integrity_invalid"):
        _create(workspace, source, report_id="../invalid")
    assert reports.read_managed_report(workspace, record) == HTML


def test_hardlink_file_is_rejected_without_deleting_other_link(workspace):
    record = _create(workspace, _lhs(workspace))
    path = reports._safe_path(workspace, record.report_id)
    duplicate = workspace / "linked-report.html"
    os.link(path, duplicate)
    with pytest.raises(reports.ManagedReportStorageError, match="file_unavailable"):
        reports.read_managed_report(workspace, record)
    assert duplicate.read_bytes() == HTML


def test_parent_symlink_cannot_escape_report_directory(workspace, tmp_path):
    source = _lhs(workspace)
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "workspaces").mkdir()
    try:
        (workspace / "workspaces/reports").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege unavailable; no bypass used")
        raise
    with pytest.raises(reports.ManagedReportStorageError, match="path_invalid"):
        _create(workspace, source)
    assert list(outside.iterdir()) == []


def test_lhs_api_owner_delete_counts_report_and_invalidates_old_preflight(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        response = client.post(
            "/api/v1/doe-designs/latin-hypercube",
            json={
                "name": "Synthetic report owner",
                "factors": [{"name": "x", "low": 0, "high": 1}],
                "run_count": 4,
                "seed": 17,
                "randomize_run_order": False,
                "run_order_seed": 29,
                "optimization": "none",
            },
        )
        assert response.status_code == 201, response.text
        design = response.json()
        source = LhsDesignReportSource(
            design_id=design["design_id"],
            design_version_id=design["design_version_id"],
            expected_source_sha256=design["design_sha256"],
        )
        endpoint = f"/api/v1/doe-designs/{source.design_id}"
        old = client.get(endpoint + "/deletion-preflight").json()
        record = _create(tmp_path, source)
        rejected = client.request(
            "DELETE",
            endpoint,
            json={
                "confirmation_design_id": str(source.design_id),
                "expected_deletion_manifest_sha256": old["deletion_manifest_sha256"],
            },
        )
        assert rejected.status_code == 409
        current = client.get(endpoint + "/deletion-preflight").json()
        assert current["counts"]["report_count"] == 1
        deleted = client.request(
            "DELETE",
            endpoint,
            json={
                "confirmation_design_id": str(source.design_id),
                "expected_deletion_manifest_sha256": current["deletion_manifest_sha256"],
            },
        )
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["deleted_counts"]["report_count"] == 1
        assert reports.get_managed_report(tmp_path, record.report_id) is None
        assert not reports._safe_path(tmp_path, record.report_id).exists()
