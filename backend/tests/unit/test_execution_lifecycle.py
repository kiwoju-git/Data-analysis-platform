import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.analyses.registry import METHODS
from app.core.config import Settings
from app.main import create_app
from app.services.analysis_run_history import list_analysis_runs
from app.storage import metadata
from app.storage.workspace_lease import acquire_workspace_lease

BEFORE = "2026-10-01T00:00:00.000Z"
AFTER = "2026-10-02T00:00:00.000Z"
REASON = "execution_interrupted_on_restart"


def _run(state="running"):
    return metadata.AnalysisRunRecord(
        analysis_id=str(uuid4()),
        method_id="eda.descriptive",
        method_version="0.1.0",
        dataset_version_id=None,
        config_json='{"schema_version":1,"options":{}}',
        status=state,
        result_path=None,
        result_sha256=None,
        stale=False,
        created_at=BEFORE,
        updated_at=BEFORE,
        completed_at=None,
        app_version="0.1.0",
    )


def _job(state="running"):
    return metadata.JobRecord(
        job_id=str(uuid4()),
        analysis_id=None,
        job_type="analysis",
        state=state,
        progress=0.25,
        cancel_requested=state == "cancel_requested",
        error_code=None,
        created_at=BEFORE,
        updated_at=BEFORE,
        completed_at=None,
    )


def _seed(root, kind, state="running"):
    if kind == "run":
        record = _run(state)
        metadata.insert_analysis_run_record(root, record)
        return record.analysis_id
    record = _job(state)
    metadata.insert_job_record(root, record)
    return record.job_id


def _get(root, kind, identifier):
    return (metadata.get_analysis_run_record if kind == "run" else metadata.get_job_record)(
        root, identifier
    )


def _cancel(root, kind, identifier, timestamp=AFTER):
    return (
        metadata.request_analysis_run_cancellation_record
        if kind == "run"
        else metadata.request_job_cancellation_record
    )(root, identifier, timestamp)


@pytest.mark.parametrize("kind", ["run", "job"])
@pytest.mark.parametrize("terminal", ["succeeded", "failed", "cancelled"])
def test_cancellation_cas_waits_for_other_connection_and_preserves_terminal_record(
    tmp_path, kind, terminal
):
    metadata.initialize_metadata_store(tmp_path)
    identifier = _seed(tmp_path, kind)
    stale_preread = _get(tmp_path, kind, identifier)
    table, state_column, id_column = (
        ("analysis_runs", "status", "analysis_id") if kind == "run" else ("jobs", "state", "job_id")
    )
    attempted = Event()
    with closing(sqlite3.connect(metadata.metadata_db_path(tmp_path))) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute(
            f"UPDATE {table} SET {state_column}=?, completed_at=?, updated_at=? "
            f"WHERE {id_column}=?",
            (terminal, AFTER, AFTER, identifier),
        )

        def request():
            attempted.set()
            return _cancel(tmp_path, kind, identifier)

        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(request)
            assert attempted.wait(5)
            writer.commit()
            result = pending.result(timeout=10)
    assert stale_preread != result.record
    assert result.outcome == "terminal"
    assert result.record == _get(tmp_path, kind, identifier)
    assert result.record.completed_at == AFTER
    assert result.record.updated_at == AFTER
    if kind == "job":
        assert result.record.cancel_requested is False
        assert result.record.progress == 0.25


@pytest.mark.parametrize("kind", ["run", "job"])
@pytest.mark.parametrize("state", ["queued", "running"])
def test_cancellation_cas_is_idempotent_and_does_not_change_other_owner(tmp_path, kind, state):
    metadata.initialize_metadata_store(tmp_path)
    identifier = _seed(tmp_path, kind, state)
    other = _seed(tmp_path, kind, state)
    other_before = _get(tmp_path, kind, other)
    result = _cancel(tmp_path, kind, identifier)
    again = _cancel(tmp_path, kind, identifier, "2026-10-03T00:00:00.000Z")
    assert result.outcome == "requested"
    assert again.outcome == "already_requested"
    assert again.record == result.record
    assert _get(tmp_path, kind, other) == other_before


@pytest.mark.parametrize("kind", ["run", "job"])
def test_cancellation_cas_missing_after_stale_preread(tmp_path, kind):
    metadata.initialize_metadata_store(tmp_path)
    assert _cancel(tmp_path, kind, str(uuid4())).outcome == "missing"
    identifier = _seed(tmp_path, kind)
    assert _get(tmp_path, kind, identifier) is not None
    table, id_column = ("analysis_runs", "analysis_id") if kind == "run" else ("jobs", "job_id")
    with closing(sqlite3.connect(metadata.metadata_db_path(tmp_path))) as writer, writer:
        writer.execute(f"DELETE FROM {table} WHERE {id_column}=?", (identifier,))
    result = _cancel(tmp_path, kind, identifier)
    assert result.outcome == "missing"
    assert result.record is None


@pytest.mark.parametrize("kind", ["run", "job"])
@pytest.mark.parametrize(
    "state", ["queued", "running", "cancel_requested", "succeeded", "failed", "cancelled"]
)
def test_public_cancellation_is_honestly_unsupported_without_mutation(tmp_path, kind, state):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        identifier = _seed(tmp_path, kind, state)
        before = _get(tmp_path, kind, identifier)
        endpoint = "analysis-runs" if kind == "run" else "jobs"
        response = client.delete(f"/api/v1/{endpoint}/{identifier}")
        assert response.status_code == 409
        expected = "analysis_run" if kind == "run" else "job"
        assert response.json()["error"]["code"] == f"{expected}_cancellation_unsupported"
        assert _get(tmp_path, kind, identifier) == before
        missing = client.delete(f"/api/v1/{endpoint}/{uuid4()}")
        assert missing.status_code == 404


def test_all_descriptors_report_actual_execution_not_worker_cancellation():
    for method in METHODS:
        capability = method.execution_capability
        assert capability.cancellation_support == "none"
        assert capability.progress_support == "none"
        assert capability.lifecycle == (
            "synchronous_request" if method.availability.value == "available" else "unavailable"
        )
    assert (
        next(
            item for item in METHODS if item.method_id == "regression.linear_model"
        ).execution_capability.cancellation_support
        == "none"
    )


def test_resource_limits_match_enforced_constants_and_option_bounds():
    from app.api.v1.schemas.analyses import (
        GaussianProcessRegressionOptions,
        RegularizationCvOptions,
    )
    from app.services import regularized_model_worker
    from app.statistics import gaussian_process_regression as gp
    from app.statistics import pls_regression as pls
    from app.statistics import two_variances

    actual = {
        method.method_id: {
            (limit.name, limit.variant): limit.value for limit in method.resource_limits
        }
        for method in METHODS
        if method.resource_limits is not None
    }

    def upper_bound(model, field):
        return next(item.le for item in model.model_fields[field].metadata if hasattr(item, "le"))

    assert actual["regression.gaussian_process"] == {
        ("max_predictors", None): gp.MAX_GP_PREDICTORS,
        ("max_usable_rows", "standard_exact"): gp.MAX_GP_USABLE_ROWS,
        ("max_usable_rows", "extended_exact"): 2000,
        ("max_nominal_predictors", None): 4,
        ("max_nominal_levels", None): 32,
        ("max_estimated_working_memory", None): 512 * 1024**2,
        ("max_usable_rows", "leave_one_out"): gp.MAX_GP_LOO_ROWS,
        ("max_optimizer_starts", None): gp.MAX_GP_OPTIMIZER_STARTS,
        ("max_optimizer_restarts", "final_refit"): upper_bound(
            GaussianProcessRegressionOptions, "optimizer_restarts"
        ),
        ("max_optimizer_restarts", "cross_validation"): upper_bound(
            GaussianProcessRegressionOptions, "cv_optimizer_restarts"
        ),
        ("max_time_budget", None): upper_bound(
            GaussianProcessRegressionOptions, "time_budget_seconds"
        ),
    }
    assert actual["regression.partial_least_squares"] == {
        ("max_predictors", None): pls.MAX_PLS_PREDICTORS,
        ("max_components", None): pls.MAX_PLS_COMPONENTS,
        ("max_usable_rows", None): pls.MAX_PLS_USABLE_ROWS,
        ("max_usable_rows", "leave_one_out"): pls.MAX_PLS_LOO_ROWS,
    }
    assert actual["quality.two_variances"] == {
        ("max_usable_rows", None): two_variances.MAX_ROWS,
        ("max_plot_points", None): two_variances.MAX_PLOT_POINTS,
    }
    assert actual["regression.linear_model"] == {
        ("max_time_budget", "regularized"): upper_bound(
            RegularizationCvOptions, "time_budget_seconds"
        ),
        ("max_worker_slots", "regularized"): regularized_model_worker._WORKER_SLOT._initial_value,
    }
    assert (
        next(method for method in METHODS if method.method_id == "eda.descriptive").resource_limits
        is None
    )


def test_startup_recovers_nonterminal_metadata_only_once_and_preserves_files(tmp_path):
    metadata.initialize_metadata_store(tmp_path)
    states = ["queued", "running", "cancel_requested", "succeeded", "failed", "cancelled"]
    runs = []
    jobs = []
    files = {}
    for state in states:
        record = _run(state)
        path = tmp_path / "analyses" / record.analysis_id / "result.json"
        path.parent.mkdir(parents=True)
        payload = json.dumps({"status": state, "stored": True}).encode()
        path.write_bytes(payload)
        files[path] = payload
        record = replace(
            record,
            result_path=path.relative_to(tmp_path).as_posix(),
            result_sha256="a" * 64,
            stale=True,
            completed_at=BEFORE if state in states[3:] else None,
        )
        metadata.insert_analysis_run_record(tmp_path, record)
        runs.append(record)
        job = _job(state)
        metadata.insert_job_record(tmp_path, job)
        jobs.append(job)
    app = create_app(Settings(workspace_root=tmp_path))
    with TestClient(app):
        assert app.state.interrupted_execution_recovery == metadata.InterruptedExecutionRecovery(
            3, 3
        )
        for index, run in enumerate(runs):
            current = metadata.get_analysis_run_record(tmp_path, run.analysis_id)
            job = metadata.get_job_record(tmp_path, jobs[index].job_id)
            if index < 3:
                assert current.status == "failed" and current.failure_code == REASON
                assert current.completed_at == current.updated_at
                assert current.stale is True
                assert current.config_json == run.config_json
                assert current.result_sha256 == run.result_sha256
                assert job.state == "failed" and job.error_code == REASON
                assert job.progress == jobs[index].progress
            else:
                assert current == run
                assert job == jobs[index]
        snapshot = [metadata.get_analysis_run_record(tmp_path, run.analysis_id) for run in runs]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        assert (
            client.app.state.interrupted_execution_recovery
            == metadata.InterruptedExecutionRecovery(0, 0)
        )
        assert [
            metadata.get_analysis_run_record(tmp_path, run.analysis_id) for run in runs
        ] == snapshot
        response = client.get(f"/api/v1/analysis-runs/{runs[0].analysis_id}")
        assert response.json()["failure_code"] == REASON
    assert {path: path.read_bytes() for path in files} == files


def test_recovery_transaction_rolls_back_both_tables_on_failure(tmp_path):
    metadata.initialize_metadata_store(tmp_path)
    run_id = _seed(tmp_path, "run")
    job_id = _seed(tmp_path, "job")
    with closing(sqlite3.connect(metadata.metadata_db_path(tmp_path))) as connection, connection:
        connection.execute(
            "CREATE TRIGGER fail_recovery BEFORE UPDATE ON jobs "
            "BEGIN SELECT RAISE(ABORT, 'synthetic'); END"
        )
    with (
        acquire_workspace_lease(tmp_path),
        pytest.raises(sqlite3.IntegrityError, match="synthetic"),
    ):
        metadata.recover_interrupted_executions(tmp_path, updated_at=AFTER)
    assert metadata.get_analysis_run_record(tmp_path, run_id).status == "running"
    assert metadata.get_job_record(tmp_path, job_id).state == "running"


@pytest.mark.parametrize("count", [0, 1, 50, 101])
def test_history_page_has_one_connection_and_one_grouped_count_query(tmp_path, monkeypatch, count):
    metadata.initialize_metadata_store(tmp_path)
    expected = {}
    for index in range(count):
        run = _run("succeeded")
        metadata.insert_analysis_run_record(tmp_path, run)
        expected[run.analysis_id] = index % 3
        for artifact_index in range(index % 3):
            metadata.insert_analysis_artifact_record(
                tmp_path,
                metadata.AnalysisArtifactRecord(
                    artifact_id=str(uuid4()),
                    analysis_id=run.analysis_id,
                    kind="test",
                    path=f"unused-{artifact_index}",
                    sha256="b" * 64,
                    media_type="application/json",
                    created_at=BEFORE,
                ),
            )
    original_connect = sqlite3.connect
    statements = []
    connections = []

    def connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        connections.append(connection)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(metadata.sqlite3, "connect", connect)
    response = list_analysis_runs(
        tmp_path,
        dataset_version_id=None,
        method_id="eda.descriptive",
        run_status=None,
        stale=False,
        result_available=False,
        limit=100,
        offset=0,
    )
    assert len(connections) == 1
    grouped = [sql for sql in statements if "GROUP BY analysis_id" in sql]
    assert len(grouped) == (1 if count else 0)
    assert not any("SELECT COUNT(*)" in sql for sql in statements)
    assert response.returned_count == min(100, count)
    assert response.has_more == (count > 100)
    assert all(item.artifact_count == expected[str(item.analysis_id)] for item in response.runs)
    assert all(item.failure_code is None for item in response.runs)


def test_migration22_preserves_legacy_run_payload_and_default_reason(tmp_path):
    path = metadata.metadata_db_path(tmp_path)
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        for migration in metadata.MIGRATIONS:
            if migration.version > 21:
                break
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version=21")
        run = _run("succeeded")
        connection.execute(
            "INSERT INTO analysis_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                run.analysis_id,
                run.method_id,
                run.method_version,
                None,
                run.config_json,
                run.status,
                None,
                None,
                0,
                BEFORE,
                BEFORE,
                None,
                run.app_version,
            ),
        )
        before = connection.execute("SELECT * FROM analysis_runs").fetchone()
    metadata.initialize_metadata_store(tmp_path)
    assert metadata.get_analysis_run_record(tmp_path, run.analysis_id) == run
    with closing(sqlite3.connect(path)) as connection:
        after = connection.execute("SELECT * FROM analysis_runs").fetchone()
        assert after[:-1] == before
        assert after[-1] is None
    metadata.initialize_metadata_store(tmp_path)
    assert metadata.get_analysis_run_record(tmp_path, run.analysis_id) == run


def test_migration22_rolls_back_column_if_migration_record_cannot_be_written(tmp_path, monkeypatch):
    path = metadata.metadata_db_path(tmp_path)
    path.parent.mkdir(parents=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        for migration in metadata.MIGRATIONS:
            if migration.version > 21:
                break
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations(version,name) VALUES (?,?)",
                (migration.version, migration.name),
            )
        connection.execute("PRAGMA user_version=21")
    original = sqlite3.connect

    def connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connection.set_authorizer(
            lambda action, table, *unused: sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_INSERT and table == "schema_migrations"
            else sqlite3.SQLITE_OK
        )
        return connection

    with monkeypatch.context() as patch:
        patch.setattr(metadata.sqlite3, "connect", connect)
        with pytest.raises(sqlite3.DatabaseError, match="authorized"):
            metadata.initialize_metadata_store(tmp_path)
    with closing(original(path)) as connection:
        assert "failure_code" not in {
            row[1] for row in connection.execute("PRAGMA table_info(analysis_runs)")
        }
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 21
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 21
    metadata.initialize_metadata_store(tmp_path)
    with closing(original(path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == metadata.SCHEMA_VERSION


def test_history_count_shares_page_read_snapshot_during_concurrent_delete(tmp_path, monkeypatch):
    metadata.initialize_metadata_store(tmp_path)
    run = _run("succeeded")
    metadata.insert_analysis_run_record(tmp_path, run)
    artifact = metadata.AnalysisArtifactRecord(
        artifact_id=str(uuid4()),
        analysis_id=run.analysis_id,
        kind="test",
        path="unused",
        sha256="b" * 64,
        media_type="application/json",
        created_at=BEFORE,
    )
    metadata.insert_analysis_artifact_record(tmp_path, artifact)
    with closing(sqlite3.connect(metadata.metadata_db_path(tmp_path))) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    original_mapper = metadata._analysis_run_from_row

    def remove_after_page_read(row):
        with closing(sqlite3.connect(metadata.metadata_db_path(tmp_path))) as writer, writer:
            writer.execute(
                "DELETE FROM analysis_artifacts WHERE artifact_id=?", (artifact.artifact_id,)
            )
        return original_mapper(row)

    monkeypatch.setattr(metadata, "_analysis_run_from_row", remove_after_page_read)
    response = list_analysis_runs(
        tmp_path,
        dataset_version_id=None,
        method_id=None,
        run_status=None,
        stale=None,
        result_available=None,
        limit=1,
        offset=0,
    )
    assert response.runs[0].artifact_count == 1
    assert metadata.count_analysis_artifact_records(tmp_path, run.analysis_id) == 0
