"""Bounded synthetic optimizer-start benchmark; run with a declared PYTHONPATH checkout."""

import argparse
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from itertools import product
from pathlib import Path


def peak_memory():
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    get_memory.restype = wintypes.BOOL
    if not get_memory(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return counters.PeakWorkingSetSize


def case_worker(case):
    import numpy as np
    from sklearn.model_selection import KFold
    from threadpoolctl import threadpool_limits
    from app.statistics.gaussian_process_regression import GaussianProcessOptions, _fit_model
    n, d, k, folds, restarts = case
    rng = np.random.default_rng(929)
    x = rng.uniform(-1, 1, (n, d))
    y = np.sin(x[:, 0] * 3) + 0.2 * np.sum(x[:, 1:] ** 2, axis=1) + rng.normal(0, 0.1, n)
    presets = ("matern_5_2_ard", "rbf_ard") if k == 2 else ("matern_5_2_ard", "matern_3_2_ard", "rbf_ard", "rational_quadratic")
    splits = list(KFold(folds, shuffle=True, random_state=41).split(x))
    started = time.monotonic()
    completed = 0
    converged = 0
    with threadpool_limits(limits=1):
        for preset in presets:
            for training, _ in splits:
                fit = _fit_model(x[training], y[training], GaussianProcessOptions(kernel_preset=preset, optimizer_restarts=restarts, random_seed=41))
                completed += restarts + 1
                converged += int(fit.state.converged)
                print(json.dumps({"completed_starts": completed, "converged_folds": converged,
                    "elapsed_seconds": time.monotonic() - started, "peak_working_set_bytes": peak_memory()}), flush=True)
        _fit_model(x, y, GaussianProcessOptions(kernel_preset=presets[0], optimizer_restarts=3, random_seed=41))
    print(json.dumps({"completed_starts": completed + 4, "converged_folds": converged,
        "elapsed_seconds": time.monotonic() - started, "peak_working_set_bytes": peak_memory(), "complete": True}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if args.case:
        case_worker(json.loads(args.case))
        return
    records = []
    for (n, d), k, folds, restarts in product([(50, 2), (200, 5), (500, 12)], [2, 4], [5, 10], [0, 1, 5]):
        case = [n, d, k, folds, restarts]
        started = time.monotonic()
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--case", json.dumps(case)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        timeout = False
        try:
            output, _ = process.communicate(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            timeout = True
            process.kill()
            output, _ = process.communicate()
        lines = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        record = {"case": case, "planned_starts": k * folds * (1 + restarts) + 4,
            "wall_seconds": time.monotonic() - started, "timeout": timeout,
            "status": "timeout" if timeout else "succeeded" if process.returncode == 0 else "failed",
            "last_progress": lines[-1] if lines else None}
        records.append(record)
        print(json.dumps(record), flush=True)
        args.output.write_text(json.dumps({"case_timeout_seconds": args.timeout, "records": records}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
