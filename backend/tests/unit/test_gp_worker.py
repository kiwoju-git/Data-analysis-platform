from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest

from app.services import gp_worker
from app.statistics.gaussian_process_regression import GaussianProcessRegressionError


def result():
    return {
        "summary_type": "gaussian_process_regression",
        "prediction_basis": {
            "y_mean": 1.0,
            "artifact_arrays": {
                "cholesky": np.eye(3),
                "dual_coefficients": np.arange(3, dtype=float),
            },
        },
    }


def test_bundle_uses_numeric_npz_and_preserves_json_and_exact_values(tmp_path):
    root = tmp_path / "한글 workspace"
    root.mkdir()
    message = gp_worker._write_result_bundle(root, result())
    assert len(json.dumps(message)) < 4096
    restored = gp_worker._read_result_bundle(root, message)
    np.testing.assert_array_equal(
        restored["prediction_basis"]["artifact_arrays"]["cholesky"], np.eye(3)
    )
    assert restored["prediction_basis"]["y_mean"] == 1
    with np.load(root / "state.npz", allow_pickle=False) as stored:
        assert all(not stored[name].dtype.hasobject for name in stored.files)


@pytest.mark.parametrize("name", ["result.json", "state.npz"])
def test_corrupted_worker_bundle_rejected(tmp_path, name):
    message = gp_worker._write_result_bundle(tmp_path, result())
    with (tmp_path / name).open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_result_invalid"):
        gp_worker._read_result_bundle(tmp_path, message)


def test_non_numeric_or_nonfinite_arrays_not_transported(tmp_path):
    value = result()
    value["prediction_basis"]["artifact_arrays"]["bad"] = np.array([object()], dtype=object)
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_result_invalid"):
        gp_worker._write_result_bundle(tmp_path, value)
    value["prediction_basis"]["artifact_arrays"]["bad"] = np.array([np.nan])
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_result_invalid"):
        gp_worker._write_result_bundle(tmp_path, value)


def test_owned_spawn_timeout_terminates_child_and_releases_slot(tmp_path, monkeypatch):
    processes = []
    runtime = multiprocessing.get_context("spawn")

    class Runtime:
        Pipe = staticmethod(runtime.Pipe)

        @staticmethod
        def Process(**kwargs):
            process = runtime.Process(**kwargs)
            processes.append(process)
            return process

    monkeypatch.setattr(gp_worker, "_runtime", Runtime)
    monkeypatch.setattr(gp_worker, "_temp_parent", lambda: str(tmp_path))
    # The real child imports its worker module, but cannot fit before this deadline.
    with pytest.raises(GaussianProcessRegressionError, match="gp_time_budget_exhausted"):
        gp_worker.run_gp_worker(
            None, None, None, [], SimpleNamespace(time_budget_seconds=0.001), []
        )
    assert len(processes) == 1
    assert processes[0]._closed
    assert not list(tmp_path.iterdir())
    assert gp_worker._WORKER_SLOT.acquire(blocking=False)
    gp_worker._WORKER_SLOT.release()


def test_parent_cancellation_does_not_create_successful_result(tmp_path, monkeypatch):
    monkeypatch.setattr(gp_worker, "_temp_parent", lambda: str(tmp_path))
    cancelled = Event()
    cancelled.set()
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_cancelled"):
        gp_worker.run_gp_worker(
            None, None, None, [], SimpleNamespace(time_budget_seconds=5), [], cancel_event=cancelled
        )
    assert not list(tmp_path.iterdir())


def test_protocol_never_accepts_client_paths(tmp_path):
    message = gp_worker._write_result_bundle(tmp_path, result())
    message["path"] = str(Path("..") / "outside")
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_result_invalid"):
        gp_worker._read_result_bundle(tmp_path, message)
