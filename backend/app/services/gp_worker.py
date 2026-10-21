from __future__ import annotations

import hashlib
import json
import multiprocessing
import platform
import re
import tempfile
import time
import zipfile
from multiprocessing.connection import Connection
from pathlib import Path
from threading import BoundedSemaphore, Event
from typing import Any, cast

import numpy as np
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

from app.services.analysis_run_execution import RowSnapshotArtifact, iter_rows_for_snapshot
from app.services.dataset_rows import DatasetRowsContext
from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
)

_WORKER_SLOT = BoundedSemaphore(1)
_MAX_JSON_BYTES = 32 * 1024**2
_MAX_NUMERIC_BYTES = 64 * 1024**2
_ERROR_CODE = re.compile(r"[a-z][a-z0-9_]{0,95}\Z")


def _runtime() -> Any:
    return multiprocessing.get_context("spawn")


def _temp_parent() -> str | None:
    return None


def worker_peak_resident_bytes() -> int | None:
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        windows_ctypes = cast(Any, ctypes)
        kernel32 = windows_ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = windows_ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            return None
        return int(counters.PeakWorkingSetSize)
    if platform.system() == "Linux":
        import resource

        linux_resource = cast(Any, resource)
        return int(linux_resource.getrusage(linux_resource.RUSAGE_SELF).ru_maxrss * 1024)
    return None


def _invalid() -> GaussianProcessRegressionError:
    return GaussianProcessRegressionError("gp_worker_result_invalid")


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_result_bundle(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    basis = result.get("prediction_basis")
    if not isinstance(basis, dict) or not isinstance(basis.get("artifact_arrays"), dict):
        raise _invalid()
    arrays = {}
    total_bytes = 0
    for name, value in basis["artifact_arrays"].items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
            raise _invalid()
        array = np.asarray(value)
        if array.dtype.kind not in "fi" or array.ndim > 2 or not np.all(np.isfinite(array)):
            raise _invalid()
        total_bytes += array.nbytes
        if total_bytes > _MAX_NUMERIC_BYTES:
            raise _invalid()
        arrays[name] = array
    payload = {
        **result,
        "prediction_basis": {k: v for k, v in basis.items() if k != "artifact_arrays"},
    }
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > _MAX_JSON_BYTES or not arrays:
        raise _invalid()
    (root / "result.json").write_bytes(encoded)
    # Uncompressed numeric storage avoids a large serialized IPC copy and is local-only.
    np.savez(root / "state.npz", **cast(dict[str, Any], arrays))
    return {
        "result_sha256": _digest(root / "result.json"),
        "numeric_sha256": _digest(root / "state.npz"),
        "worker_peak_rss_bytes": worker_peak_resident_bytes(),
    }


def _read_result_bundle(root: Path, message: dict[str, Any]) -> dict[str, Any]:
    if set(message) != {"result_sha256", "numeric_sha256", "worker_peak_rss_bytes"}:
        raise _invalid()
    peak = message["worker_peak_rss_bytes"]
    if peak is not None and (type(peak) is not int or not 0 <= peak < 2**63):
        raise _invalid()
    for name, key, maximum in (
        ("result.json", "result_sha256", _MAX_JSON_BYTES),
        ("state.npz", "numeric_sha256", _MAX_NUMERIC_BYTES + 64 * 1024),
    ):
        path = root / name
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size > maximum
            or _digest(path) != message[key]
        ):
            raise _invalid()
    try:
        with zipfile.ZipFile(root / "state.npz") as archive:
            entries = archive.infolist()
            if (
                not entries
                or len(entries) > 32
                or len({entry.filename for entry in entries}) != len(entries)
                or sum(entry.file_size for entry in entries) > _MAX_NUMERIC_BYTES + 64 * 1024
                or any(not re.fullmatch(r"[a-z][a-z0-9_]{0,63}\.npy", e.filename) for e in entries)
            ):
                raise _invalid()
            numeric_bytes = 0
            for entry in entries:
                with archive.open(entry) as stream:
                    version = np.lib.format.read_magic(stream)
                    if version == (1, 0):
                        shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                    elif version == (2, 0):
                        shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                    else:
                        raise _invalid()
                    if dtype.kind not in "fi" or len(shape) > 2 or any(n > 2000 for n in shape):
                        raise _invalid()
                    numeric_bytes += dtype.itemsize * int(np.prod(shape))
                    if numeric_bytes > _MAX_NUMERIC_BYTES:
                        raise _invalid()
        result = json.loads((root / "result.json").read_text(encoding="utf-8"))
        if not isinstance(result, dict) or not isinstance(result.get("prediction_basis"), dict):
            raise _invalid()
        with np.load(root / "state.npz", allow_pickle=False) as stored:
            arrays = {name: stored[name] for name in stored.files}
        if any(
            array.dtype.kind not in "fi" or array.ndim > 2 or not np.all(np.isfinite(array))
            for array in arrays.values()
        ):
            raise _invalid()
        result["prediction_basis"]["artifact_arrays"] = arrays
        resource = result.get("resource_budget")
        if isinstance(resource, dict):
            resource["observed_worker_peak_rss_bytes"] = peak
            resource["measurement_scope"] = (
                "worker_process_peak_through_result_serialization_excludes_parent"
            )
        return result
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        raise _invalid() from exc


def _worker_entry(
    output: Connection,
    root: Path,
    context: DatasetRowsContext,
    snapshot: RowSnapshotArtifact,
    response: GaussianProcessColumn,
    predictors: list[GaussianProcessColumn],
    options: GaussianProcessOptions,
    metadata_columns: list[GaussianProcessColumn],
) -> None:
    try:
        from app.statistics.gaussian_process_regression import calculate_gaussian_process_regression

        with threadpool_limits(limits=1):
            result = calculate_gaussian_process_regression(
                iter_rows_for_snapshot(context, snapshot),
                response,
                predictors,
                decimal=context.parsing.decimal,
                thousands=context.parsing.thousands,
                options=options,
                metadata_columns=metadata_columns,
            )
            message = _write_result_bundle(root, result)
    except GaussianProcessRegressionError as exc:
        message = {"error": exc.code}
    except Exception:
        # An unsuccessful child sends a stable failure, never row data or a partial model.
        message = {"error": "gp_fit_failed"}
    try:
        output.send_bytes(json.dumps(message, allow_nan=False).encode("utf-8"))
    finally:
        output.close()


def run_gp_worker(
    context: DatasetRowsContext,
    snapshot: RowSnapshotArtifact,
    response: GaussianProcessColumn,
    predictors: list[GaussianProcessColumn],
    options: GaussianProcessOptions,
    metadata_columns: list[GaussianProcessColumn],
    *,
    cancel_event: Event | None = None,
) -> dict[str, Any]:
    if not _WORKER_SLOT.acquire(blocking=False):
        raise GaussianProcessRegressionError("gp_worker_busy")
    process = None
    incoming = outgoing = None
    try:
        with tempfile.TemporaryDirectory(prefix="datalab-gp-", dir=_temp_parent()) as directory:
            runtime = _runtime()
            incoming, outgoing = runtime.Pipe(duplex=False)
            root = Path(directory)
            process = runtime.Process(
                target=_worker_entry,
                args=(
                    outgoing,
                    root,
                    context,
                    snapshot,
                    response,
                    predictors,
                    options,
                    metadata_columns,
                ),
            )
            try:
                deadline = time.monotonic() + options.time_budget_seconds
                process.start()
                outgoing.close()
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise GaussianProcessRegressionError("gp_worker_cancelled")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise GaussianProcessRegressionError("gp_time_budget_exhausted")
                    if incoming.poll(min(0.1, remaining)):
                        break
                    if not process.is_alive():
                        raise _invalid()
                try:
                    message = json.loads(incoming.recv_bytes(maxlength=4096))
                except (EOFError, OSError, ValueError) as exc:
                    raise _invalid() from exc
                if not isinstance(message, dict):
                    raise _invalid()
                if "error" in message:
                    code = message["error"]
                    if not isinstance(code, str) or not _ERROR_CODE.fullmatch(code):
                        raise _invalid()
                    raise GaussianProcessRegressionError(code)
                return _read_result_bundle(root, message)
            finally:
                # Only this process is owned; close it before deleting its temporary files.
                if process.pid is not None:
                    process.join(timeout=1)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=5)
                    process.close()
    finally:
        if incoming is not None:
            incoming.close()
        if outgoing is not None:
            outgoing.close()
        _WORKER_SLOT.release()
