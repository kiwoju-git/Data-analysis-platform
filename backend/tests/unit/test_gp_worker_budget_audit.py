from __future__ import annotations

import io
import json
import multiprocessing
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from gp_worker_probe import running_child

from app.services import gp_worker
from app.statistics.gaussian_process_regression import GaussianProcessRegressionError
from app.statistics.gp_resource_budget import GpResourceError, estimate_gp_resources


def _bundle_result():
    return {
        "resource_budget": {"estimated_peak_bytes": 1000},
        "prediction_basis": {"artifact_arrays": {"cholesky": np.eye(3)}},
    }


def test_worker_peak_is_sampled_after_serialization_and_validated_before_result_use(
    tmp_path, monkeypatch
):
    measured = []

    def peak():
        assert (tmp_path / "result.json").is_file()
        assert (tmp_path / "state.npz").is_file()
        measured.append(True)
        return 123456

    monkeypatch.setattr(gp_worker, "worker_peak_resident_bytes", peak)
    message = gp_worker._write_result_bundle(tmp_path, _bundle_result())
    assert measured == [True]
    assert message["worker_peak_rss_bytes"] == 123456
    stored_json = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert "observed_worker_peak_rss_bytes" not in stored_json["resource_budget"]
    result = gp_worker._read_result_bundle(tmp_path, message)
    assert result["resource_budget"]["observed_worker_peak_rss_bytes"] == 123456
    assert result["resource_budget"]["measurement_scope"] == (
        "worker_process_peak_through_result_serialization_excludes_parent"
    )


@pytest.mark.parametrize("peak", [True, -1, 2**63, 1.5, "1234", {}])
def test_invalid_worker_peak_receipt_is_rejected(tmp_path, peak):
    message = gp_worker._write_result_bundle(tmp_path, _bundle_result())
    message["worker_peak_rss_bytes"] = peak
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_result_invalid"):
        gp_worker._read_result_bundle(tmp_path, message)


@pytest.mark.parametrize(
    "shape,dtype", [((2001, 1), "<f8"), ((2000, 2000, 2), "<f8"), ((3,), "|O")]
)
def test_npz_header_is_rejected_before_array_materialization(tmp_path, monkeypatch, shape, dtype):
    message = gp_worker._write_result_bundle(tmp_path, _bundle_result())
    header = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        header, {"descr": dtype, "fortran_order": False, "shape": shape}
    )
    with zipfile.ZipFile(tmp_path / "state.npz", "w") as archive:
        archive.writestr("cholesky.npy", header.getvalue())
    message["numeric_sha256"] = gp_worker._digest(tmp_path / "state.npz")

    def forbidden_load(*args, **kwargs):
        pytest.fail("Invalid shape/object headers must fail before np.load.")

    monkeypatch.setattr(gp_worker.np, "load", forbidden_load)
    with pytest.raises(GaussianProcessRegressionError, match="gp_worker_result_invalid"):
        gp_worker._read_result_bundle(tmp_path, message)


def test_deadline_terminates_already_running_owned_child_and_removes_only_bundle(
    tmp_path, monkeypatch
):
    runtime = multiprocessing.get_context("spawn")
    processes = []
    sentinel = tmp_path / "unrelated.txt"
    sentinel.write_text("preserve", encoding="utf-8")

    class Runtime:
        Pipe = staticmethod(runtime.Pipe)

        @staticmethod
        def Process(**kwargs):
            process = runtime.Process(target=running_child, args=kwargs["args"])
            processes.append(process)
            return process

    monkeypatch.setattr(gp_worker, "_runtime", Runtime)
    monkeypatch.setattr(gp_worker, "_temp_parent", lambda: str(tmp_path))
    with pytest.raises(GaussianProcessRegressionError, match="gp_time_budget_exhausted"):
        gp_worker.run_gp_worker(None, None, None, [], SimpleNamespace(time_budget_seconds=15), [])
    marker = tmp_path / "child-started.txt"
    assert marker.is_file(), "The deadline must expire after the child enters work."
    assert not Path(marker.read_text(encoding="utf-8")).exists()
    assert len(processes) == 1 and processes[0]._closed
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert gp_worker._WORKER_SLOT.acquire(blocking=False)
    gp_worker._WORKER_SLOT.release()


def _resource(**updates):
    values = {
        "profile": "extended_exact",
        "n_rows": 501,
        "fold_training_sizes": (400,) * 5,
        "kernel_parameter_counts": (2, 2, 2, 2),
        "optimizer_restarts": 3,
        "cv_optimizer_restarts": 11,
        "retained_candidate_count": 3,
        "prediction_query_count": 100,
    }
    values.update(updates)
    return estimate_gp_resources(**values)


def test_all_fold_candidate_and_retained_refit_starts_count_toward_admission():
    exact = _resource()
    assert exact.optimizer_start_count == 256
    with pytest.raises(GpResourceError, match="gp_kernel_search_budget_exceeded"):
        _resource(optimizer_restarts=4)


def test_two_thousand_mixed_parameter_and_retention_cost_cannot_bypass_memory_admission():
    with pytest.raises(GpResourceError, match="gp_memory_budget_exceeded"):
        _resource(
            n_rows=2000,
            fold_training_sizes=(1333,) * 3,
            kernel_parameter_counts=(4, 4),
            optimizer_restarts=0,
            cv_optimizer_restarts=0,
            retained_candidate_count=1,
        )
