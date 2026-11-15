"""Bounded 500-observation capacity, without changing GP or search policies."""

import hashlib
import json
import os
import sqlite3
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.statistics.bo_factor_kernels import build_bo_factor_kernel
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate
from app.statistics.bo_surrogate_snapshot import dump_bo_surrogate, load_bo_surrogate
from app.storage import metadata
from tests.unit.test_bo_dataset_import_api import (
    ROOT,
    commit_request,
    import_request,
    preflight,
)
from tests.unit.test_bo_mixed_surrogate import factors
from tests.unit.test_bo_surrogate_snapshot import SEARCH


def process_peak_bytes():
    """Current test-process lifetime peak, not an aggregate or enforced memory cap."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak",
                "working",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(
        wintypes.HANDLE(-1), ctypes.byref(counters), counters.cb
    ):
        raise ctypes.WinError()
    return counters.peak


@pytest.mark.parametrize("count", [200, 201, 240, 500])
def test_import_capacity_retains_every_repeat(tmp_path, count):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, _ = import_request(client, ("x,y\n" + "5,1\n" * count).encode())
        preview = preflight(client, body)
        assert preview["n_used"] == count
        assert preview["repeated_coordinate_count"] == count - 1
        saved = client.post(f"{ROOT}/from-dataset", json=commit_request(body, preview))
        assert saved.status_code == 201, saved.text
        assert saved.json()["completed_trial_count"] == count
        assert len(saved.json()["trials"]) == count
        assert client.get(f"{ROOT}/{saved.json()['study_id']}").json() == saved.json()


def test_import_501_reports_only_aggregate_limits_and_is_atomic(tmp_path):
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, _ = import_request(client, ("x,y\n" + "5,1\n" * 501).encode())
        response = client.post(f"{ROOT}/import-preflight", json=body)
        assert response.status_code == 409, response.text
        error = response.json()["error"]
        assert error["code"] == "bayesian_import_trial_limit"
        assert error["limits"] == {"observed_count": 501, "maximum_count": 500}
        assert set(error) == {"code", "message", "correlation_id", "developer_detail", "limits"}
        from uuid import uuid4

        committed = client.post(
            ROOT + "/from-dataset",
            json=body | {"request_id": str(uuid4()), "expected_preflight_sha256": "0" * 64},
        )
        assert committed.status_code == 409
        assert committed.json()["error"]["limits"] == error["limits"]
        assert client.get(ROOT).json()["total"] == 0


def test_500_import_reports_all_250_conflicting_conditions(tmp_path):
    rows = [f"{i / 25},{value}" for i in range(250) for value in (1, 2)]
    with TestClient(create_app(Settings(workspace_root=tmp_path))) as client:
        body, _ = import_request(client, ("x,y\n" + "\n".join(rows) + "\n").encode())
        preview = preflight(client, body)
        assert preview["n_used"] == 500
        assert preview["conflicting_coordinate_count"] == 250
        assert preview["repeated_coordinate_count"] == 250


def test_existing_error_body_omits_optional_limits():
    from app.core.errors import error_response

    body = json.loads(error_response("synthetic", "Synthetic", "id", 409).body)
    assert body == {
        "error": {
            "code": "synthetic",
            "message": "Synthetic",
            "correlation_id": "id",
            "developer_detail": None,
        }
    }


@pytest.mark.parametrize("count", [240, 500])
def test_two_response_exact_fit_and_snapshot_prediction(count):
    x = np.linspace(0, 1, count)[:, None]
    for y in (np.sin(4 * x[:, 0]), np.cos(3 * x[:, 0])):
        model = fit_bo_surrogate(
            x,
            y,
            BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.1),
            {**SEARCH, "model_max_iterations": 5},
            deadline=time.perf_counter() + 60,
            optimize=True,
        )
        targets = (y - model.normalization_mean) / model.normalization_scale
        state = dump_bo_surrogate(model, training_targets_scaled=targets)
        restored = load_bo_surrogate(json.loads(json.dumps(state)))
        actual = restored.predict([[0.13], [0.67]])
        expected = model.predict([[0.13], [0.67]])
        np.testing.assert_array_equal(actual.mean_scaled, expected.mean_scaled)
        np.testing.assert_array_equal(
            actual.predictive_variance_scaled, expected.predictive_variance_scaled
        )
        assert restored.raw_observation_count == count
        if count == 500:
            from app.statistics.bo_loo import conditional_row_loo

            loo = conditional_row_loo(restored, x, y, [f"trial-{i}" for i in range(count)])
            assert loo["n_scored"] == 500
            assert loo["points"][-1]["observation_index"] == 500
            assert all(np.isfinite(point["predicted"]) for point in loo["points"])
        print(
            f"capacity_fit n={count} fit_ms={model.fit_elapsed_ms:.3f} "
            f"snapshot_bytes={len(json.dumps(state))} process_peak_bytes={process_peak_bytes()}"
        )


@pytest.mark.parametrize("operation", ["auto_augmentation", "auto_mixed_augmentation"])
@pytest.mark.parametrize("response_count", [4, 6])
def test_response_500_snapshot_stays_inside_bounded_document_budget(
    monkeypatch, operation, response_count
):
    from app.services import bo_desirability_worker as execution
    from app.services import bo_planning_worker as worker
    from app.statistics.bayesian_optimization import BayesianOptimizationError
    from app.storage.bo_planning import _documents
    from tests.unit.test_bo_planning_worker import _Output

    x = np.linspace(0, 1, 500)[:, None]
    y = np.sin(4 * x[:, 0])
    model = fit_bo_surrogate(
        x,
        y,
        BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.1),
        SEARCH,
        deadline=time.perf_counter() + 60,
        optimize=False,
    )
    targets = (y - model.normalization_mean) / model.normalization_scale
    state = dump_bo_surrogate(model, training_targets_scaled=targets)
    text = json.dumps({"response_states": [state] * response_count}, separators=(",", ":"))
    assert 8 * 1024 * 1024 < len(text) < 24 * 1024 * 1024
    _documents(
        {"snapshot_json": text, "snapshot_sha256": hashlib.sha256(text.encode()).hexdigest()},
        (("snapshot_json", "snapshot_sha256"),),
    )
    snapshot = {"response_states": [state] * response_count}
    payload = {"snapshot": snapshot, "routing": {"snapshot": json.loads(text)}}
    assert len(json.dumps({"operation": operation, "payload": payload}).encode()) > 16 * 1024 * 1024
    seen = []

    def stop_after_hydration(kind, received):
        assert kind == operation
        assert received["routing"]["snapshot"] is received["snapshot"]
        assert received["snapshot"] == snapshot
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")

    def transport(encoded, *, entrypoint, **kwargs):
        assert len(encoded) < worker.MAX_PLANNING_BYTES
        assert "snapshot" not in json.loads(encoded)["payload"]["routing"]
        seen.append(len(encoded))
        output = _Output()
        entrypoint(output, encoded)
        return output.data

    monkeypatch.setattr(worker, "_calculate", stop_after_hydration)
    monkeypatch.setattr(execution, "_run_owned_worker", transport)
    with pytest.raises(BayesianOptimizationError, match="bayesian_optimization_budget_exhausted"):
        worker.run_planning_operation(operation, payload, time_budget_ms=1000)
    assert seen
    assert payload["routing"]["snapshot"] == snapshot
    print(
        f"capacity_{response_count}_response_500 snapshot_bytes={len(text)} "
        f"process_peak_bytes={process_peak_bytes()}"
    )


def test_candidate_exclusions_accept_both_encodings_of_500_trials():
    from app.statistics.bo_candidate_points import validated_candidate_rows

    rows = validated_candidate_rows(
        [{"x": 5.0}],
        [{"factor_id": "x", "name": "X", "low": 0.0, "high": 10.0}],
        [],
        excluded_normalized=[[0.0]] * 1000,
        duplicate_tolerance=1e-6,
    )
    assert len(rows) == 1


def test_metadata_37_capacity_upgrade_rebuilds_actual_checks(tmp_path, monkeypatch):
    from app.storage import bo_planning
    from tests.unit.test_bo_planning_storage import _candidate, _model

    with monkeypatch.context() as patch:
        patch.setattr(metadata, "SCHEMA_VERSION", 37)
        patch.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 37)
        )
        metadata.initialize_metadata_store(tmp_path)
    model, _ = _model(tmp_path)
    candidate = _candidate(model)
    bo_planning.insert_candidate_revision(tmp_path, candidate, name="Synthetic", expected_head=None)
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        before = db.execute("SELECT * FROM schema_migrations ORDER BY version").fetchall()
        tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bayesian_%'"
            )
        ]
        records = {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        }
    assert metadata.initialize_metadata_store(tmp_path).schema_version == metadata.SCHEMA_VERSION
    with sqlite3.connect(metadata.metadata_db_path(tmp_path)) as db:
        assert (
            db.execute(
                "SELECT * FROM schema_migrations WHERE version <= 37 ORDER BY version"
            ).fetchall()
            == before
        )
        assert db.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert {
            table: db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in tables
        } == records
        schemas = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name LIKE 'bayesian_%'"
        ).fetchall()
        assert not any("BETWEEN 1 AND 200" in sql or "<= 200" in sql for (sql,) in schemas)
        db.execute("SAVEPOINT capacity_check")
        db.execute("UPDATE bayesian_candidate_revisions SET source_trial_count=500")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE bayesian_candidate_revisions SET source_trial_count=501")
        db.execute("ROLLBACK TO capacity_check")
        db.execute("RELEASE capacity_check")


def test_metadata_38_failure_rolls_back_ddl_records_and_version(tmp_path, monkeypatch):
    from dataclasses import replace

    with monkeypatch.context() as patch:
        patch.setattr(metadata, "SCHEMA_VERSION", 37)
        patch.setattr(
            metadata, "MIGRATIONS", tuple(m for m in metadata.MIGRATIONS if m.version <= 37)
        )
        metadata.initialize_metadata_store(tmp_path)
    path = metadata.metadata_db_path(tmp_path)
    with sqlite3.connect(path) as db:
        before = db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
    broken = tuple(
        replace(m, sql=m.sql + "\nINSERT INTO nonexistent_capacity_table VALUES (1);")
        if m.version == 38
        else m
        for m in metadata.MIGRATIONS
    )
    with monkeypatch.context() as patch:
        patch.setattr(metadata, "MIGRATIONS", broken)
        with pytest.raises(sqlite3.OperationalError, match="nonexistent_capacity_table"):
            metadata.initialize_metadata_store(tmp_path)
    with sqlite3.connect(path) as db:
        assert (
            db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall() == before
        )
        assert db.execute("PRAGMA user_version").fetchone() == (37,)
        assert db.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (37,)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_mixed_500_gradient_is_finite():
    kernel = build_bo_factor_kernel(factors(), BoKernelSpec("gaussian"))
    x = np.column_stack((np.linspace(0, 1, 500), np.arange(500) % 3))
    covariance, gradient = kernel(x, eval_gradient=True)
    assert covariance.shape == (500, 500)
    assert gradient.shape == (500, 500, len(kernel.theta))
    assert np.isfinite(gradient).all()


def test_mixed_500_exact_snapshot_prediction_round_trip():
    from app.statistics.bo_mixed_snapshot import dump_bo_mixed_surrogate, load_bo_mixed_surrogate
    from tests.unit.test_bo_mixed_surrogate import fitted

    x = np.column_stack((np.linspace(0, 1, 500), np.arange(500) % 3))
    model = fitted(
        x=x, y=np.sin(4 * x[:, 0]), optimize=True, search={**SEARCH, "model_max_iterations": 3}
    )
    state = dump_bo_mixed_surrogate(model)
    restored = load_bo_mixed_surrogate(json.loads(json.dumps(state)))
    query = np.array([[0.123, 0], [0.789, 2]])
    np.testing.assert_array_equal(
        restored.predict(query).mean_scaled, model.predict(query).mean_scaled
    )
    assert restored.raw_observation_count == 500


def test_mixed_gradient_memory_preflight_precedes_dense_allocation(monkeypatch):
    from app.statistics import bo_factor_kernels

    kernel = build_bo_factor_kernel(factors(), BoKernelSpec("gaussian"))
    monkeypatch.setattr(bo_factor_kernels, "MAX_GRADIENT_WORKING_BYTES", 1)
    x = np.array([[0.0, 0], [1.0, 1]])
    with pytest.raises(ValueError, match="bayesian_factor_kernel_resource_limit"):
        kernel(x, eval_gradient=True)
    assert kernel(x).shape == (2, 2)
