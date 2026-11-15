"""Sequential synthetic BO capacity probe; no user workspace or production limits change."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def synthetic_request(kind: str, rows: int, responses: int) -> dict[str, Any]:
    import numpy as np

    from app.api.v1.schemas.bo_desirability_batch_calculation import (
        DesirabilityBatchCalculationRequest,
    )
    from app.api.v1.schemas.bo_mixed_planning import MixedPlanningCalculationRequest

    if (
        kind not in {"numeric", "mixed"}
        or not 2 <= rows <= 500
        or not 1 <= responses <= 6
    ):
        raise ValueError("Unsupported benchmark case")
    rng = np.random.default_rng(20261115)
    coordinates = rng.uniform(0.0, 1.0, (rows, 4))
    factors = [
        {"factor_id": f"x{i}", "low": 0.0, "high": 1.0, "domain_kind": "continuous"}
        for i in range(4)
    ]
    mixed = kind == "mixed"
    if mixed:
        for factor in factors:
            factor.update(name=factor["factor_id"], unit=None)
        factors.append(
            {
                "factor_id": "material",
                "name": "Material",
                "domain_kind": "nominal",
                "levels": ["A", "B", "C"],
                "correlation_policy": "equal_positive_correlation_v1",
            }
        )
    observations, excluded = [], []
    for index, x in enumerate(coordinates):
        actual = {f"x{i}": float(v) for i, v in enumerate(x)}
        encoded = dict(actual)
        if mixed:
            actual["material"] = ["A", "B", "C"][index % 3]
            encoded["material"] = float(index % 3)
        values = {
            f"y{i}": float(
                50
                + i
                + 3 * np.sin((i + 1) * x[0])
                + 2 * x[1]
                - x[2] * x[3]
                + (index % 3) * 0.2 * mixed
                + rng.normal(0.0, 0.15)
            )
            for i in range(responses)
        }
        observations.append(
            {
                "trial_id": str(UUID(int=index + 1)),
                "actual_coordinates": actual,
                "encoded_coordinates" if mixed else "normalized_coordinates": encoded,
                "response_values": values,
            }
        )
        excluded.append(list(encoded.values()))
    objective = {
        "responses": [
            {
                "response_id": f"y{i}",
                "name": f"Synthetic response{i}",
                "unit": None,
                "goal": "maximize",
                "lower": 40.0,
                "target": 65.0,
                "upper": None,
                "importance": 1.0,
            }
            for i in range(responses)
        ]
    }
    if mixed:
        objective.update(
            name="Synthetic composite",
            goal_type="desirability",
            observation_policy="complete_response_vector",
            curve_policy="derringer_suich_linear_v1",
        )
    payload = {
        "schema_version": 8 if mixed else 5,
        "factors": factors,
        "constraints": [],
        "observations": observations,
        "excluded_encoded" if mixed else "excluded_normalized": excluded,
        "objective": objective,
        "response_models": [
            {
                "response_id": f"y{i}",
                "kernel": {"kind": "matern_5_2"},
                "surrogate": {"noise_mode": "estimate"},
            }
            for i in range(responses)
        ],
        "observation_policy": {"mode": "retain_raw"},
        "xi_desirability": 0.01,
        "search": {
            "random_seed": 20261115,
            "candidate_count_per_step": 32,
            "local_start_count_per_step": 0,
            "max_iterations_per_step": 20,
            "max_evaluations_total": 1024,
            "model_max_iterations": 100,
            "model_max_evaluations": 2000,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 60000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
    }
    if mixed:
        payload.update(
            fit_policy={
                "policy": "bounded_typed_factor_starts_v1",
                "deterministic_start_count": 1,
            },
            max_moment_evaluations=8192,
        )
        return MixedPlanningCalculationRequest.model_validate(payload).worker_payload()
    payload.update(
        batch_size=1,
        batch_options={
            "sample_count": 64,
            "max_moment_evaluations": 8192,
            "min_batch_distance_normalized": 0.0,
        },
    )
    return DesirabilityBatchCalculationRequest.model_validate(payload).worker_payload()


def _bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def run_case(
    kind: str, rows: int, responses: int, directory: Path, iterations: int = 100
) -> dict[str, Any]:
    from threadpoolctl import threadpool_limits

    from app.core.bo_limits import MAX_BO_PLANNING_BYTES
    from app.services.gp_worker import worker_peak_resident_bytes
    from app.statistics.bo_mixed_planning import (
        evaluate_mixed_planning_points,
        fit_mixed_planning_model,
    )
    from app.statistics.bo_planning_model import (
        evaluate_planning_points,
        fit_planning_model,
    )

    request = synthetic_request(kind, rows, responses)
    if not 1 <= iterations <= 200:
        raise ValueError("Invalid explicit optimizer iteration setting")
    request["search"]["model_max_iterations"] = iterations
    original = hashlib.sha256(_bytes(request)).hexdigest()
    fit, evaluate = (
        (fit_mixed_planning_model, evaluate_mixed_planning_points)
        if kind == "mixed"
        else (fit_planning_model, evaluate_planning_points)
    )
    started = time.perf_counter()
    stage = "fit"
    receipt = {
        "synthetic": True,
        "kind": kind,
        "rows": rows,
        "responses": responses,
        "source_sha256": original,
        "search": request["search"],
        "noise_mode": "estimate",
        "kernel": "matern_5_2",
    }
    try:
        with threadpool_limits(limits=1):
            snapshot = fit(request)
            fit_seconds = time.perf_counter() - started
            stage = "snapshot"
            encoded = _bytes(snapshot)
            if len(encoded) > MAX_BO_PLANNING_BYTES:
                raise ValueError("Snapshot exceeds production document limit")
            path = directory / "synthetic-model.json"
            path.write_bytes(encoded)
            points = [{f"x{i}": 0.173 + i * 0.1 for i in range(4)}]
            if kind == "mixed":
                points[0]["material"] = "B"
            stage = "restore_and_predict"
            before = evaluate(snapshot, points)
            loaded = json.loads(path.read_bytes())
            after = evaluate(loaded, points)
            if before != after or path.read_bytes() != encoded:
                raise ValueError("Restore changed predictions or stored bytes")
            if hashlib.sha256(_bytes(request)).hexdigest() != original:
                raise ValueError("Fitting mutated source")
            records = snapshot["response_models"]
            counts = [r["observation_view"]["raw_observation_count"] for r in records]
            optimizers = [r["model"]["optimizer"] for r in records]
            if counts != [rows] * responses or not all(
                r["optimized"] for r in optimizers
            ):
                raise ValueError("Incomplete real-model fitting")
            receipt.update(
                status="passed",
                fit_seconds=fit_seconds,
                snapshot_bytes=len(encoded),
                snapshot_sha256=hashlib.sha256(encoded).hexdigest(),
                raw_observations_per_model=counts,
                optimized_models=len(optimizers),
                optimizer_records=optimizers,
                fit_evaluations=snapshot["fit_evaluations"],
                warnings=snapshot["warnings"],
                restore_predictions_identical=True,
                source_unchanged=True,
            )
    except (ValueError, RuntimeError) as exc:
        receipt.update(status="failed", stage=stage, error_code=str(exc))
    receipt.update(
        elapsed_seconds=time.perf_counter() - started,
        process_peak_rss_bytes=worker_peak_resident_bytes(),
        memory_scope="Single isolated calculation process lifetime peak, not a hard cap",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("numeric", "mixed"), default="numeric")
    parser.add_argument("--rows", type=int, default=500)
    parser.add_argument("--responses", type=int, default=6)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        with tempfile.TemporaryDirectory(prefix="bo-capacity-synthetic-") as temporary:
            receipt = run_case(
                args.kind, args.rows, args.responses, Path(temporary), args.iterations
            )
        args.output.write_bytes(_bytes(receipt) + b"\n")
        return 0 if receipt["status"] == "passed" else 1
    from benchmark_gp_resources import capture_source_identity, source_provenance

    args.output.parent.mkdir(parents=True, exist_ok=True)
    before = capture_source_identity()
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    with tempfile.TemporaryDirectory(prefix="bo-capacity-receipt-") as temporary:
        output = Path(temporary) / "receipt.json"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--child",
            "--kind",
            args.kind,
            "--rows",
            str(args.rows),
            "--responses",
            str(args.responses),
            "--iterations",
            str(args.iterations),
            "--output",
            str(output),
        ]
        # Own the complete child group, including the Windows venv launcher child.
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        try:
            _, stderr = process.communicate(timeout=180)
            receipt = (
                json.loads(output.read_bytes())
                if output.exists()
                else {
                    "status": "failed",
                    "stage": "child",
                    "returncode": process.returncode,
                    "diagnostic": stderr[-2000:],
                }
            )
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    timeout=15,
                )
            else:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.communicate(timeout=15)
            receipt = {
                "status": "failed",
                "stage": "hard_timeout",
                "timeout_seconds": 180,
            }
    receipt.update(
        environment={
            "os": platform.platform(),
            "python": platform.python_version(),
            "cpu_only": True,
            "threads": 1,
        },
        source_provenance=source_provenance(before, capture_source_identity()),
    )
    args.output.write_bytes(_bytes(receipt) + b"\n")
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "stage",
                    "fit_seconds",
                    "elapsed_seconds",
                    "process_peak_rss_bytes",
                    "snapshot_bytes",
                )
                if k in receipt
            }
        )
    )
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
