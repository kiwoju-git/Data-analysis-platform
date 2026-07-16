from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import platform
import queue
import statistics
import sys
import time
from datetime import datetime, timezone
from typing import Any

from app.statistics.bayesian_optimization import bayesian_worker_entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure bounded Bayesian worker startup, fit, and search costs."
    )
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 10:
        raise ValueError("--repetitions must be between 1 and 10")
    if sys.version_info[:2] != (3, 10):
        raise RuntimeError("The product benchmark requires CPython 3.10.x")

    startup_samples = [_measure_empty_spawn() for _ in range(args.repetitions)]
    cases = []
    for case_name, factor_count, observation_count, candidate_count in (
        ("one_factor_8_observations", 1, 8, 256),
        ("two_factor_20_observations", 2, 20, 512),
        ("four_factor_48_observations", 4, 48, 512),
    ):
        samples = [
            _measure_worker(
                _benchmark_payload(
                    case_name=case_name,
                    factor_count=factor_count,
                    observation_count=observation_count,
                    candidate_count=candidate_count,
                    seed=20260715 + repetition,
                )
            )
            for repetition in range(args.repetitions)
        ]
        cases.append(
            {
                "case": case_name,
                "factor_count": factor_count,
                "completed_observation_count": observation_count,
                "candidate_count": candidate_count,
                "repetitions": args.repetitions,
                "worker_round_trip_ms": _summary(samples, "worker_round_trip_ms"),
                "child_calculation_ms": _summary(samples, "child_calculation_ms"),
                "gp_fit_ms": _summary(samples, "gp_fit_ms"),
                "non_fit_calculation_ms": _summary(samples, "non_fit_calculation_ms"),
                "round_trip_overhead_ms": _summary(samples, "round_trip_overhead_ms"),
            }
        )
    print(
        json.dumps(
            {
                "benchmark_schema_version": 1,
                "measured_at": datetime.now(timezone.utc).isoformat(),
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "cpu_only": True,
                "numerical_thread_limit": 1,
                "empty_spawn_round_trip_ms": _numeric_summary(startup_samples),
                "timing_policy": {
                    "worker_round_trip_ms": "parent process start through result receipt",
                    "child_calculation_ms": "worker calculation total from persisted budget timing",
                    "gp_fit_ms": "GaussianProcessRegressor fit timing",
                    "non_fit_calculation_ms": (
                        "child total minus fit; includes imports, validation, candidate generation, "
                        "acquisition search, and final prediction"
                    ),
                    "round_trip_overhead_ms": "parent round trip minus child calculation",
                },
                "cases": cases,
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _empty_worker(output_queue: Any) -> None:
    output_queue.put({"status": "ok"})


def _measure_empty_spawn() -> float:
    context = multiprocessing.get_context("spawn")
    output_queue = context.Queue(maxsize=1)
    process = context.Process(target=_empty_worker, args=(output_queue,))
    started = time.perf_counter()
    process.start()
    process.join(timeout=30.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
        raise RuntimeError("empty spawn benchmark timed out")
    try:
        message = output_queue.get(timeout=2.0)
    except queue.Empty as exc:
        raise RuntimeError("empty spawn benchmark returned no result") from exc
    finally:
        output_queue.close()
        output_queue.join_thread()
        process.close()
    if message != {"status": "ok"}:
        raise RuntimeError("empty spawn benchmark returned an invalid result")
    return (time.perf_counter() - started) * 1000.0


def _measure_worker(payload: dict[str, Any]) -> dict[str, float]:
    context = multiprocessing.get_context("spawn")
    output_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=bayesian_worker_entry, args=(output_queue, payload)
    )
    started = time.perf_counter()
    process.start()
    process.join(timeout=90.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
        raise RuntimeError("Bayesian worker benchmark timed out")
    try:
        message = output_queue.get(timeout=2.0)
    except queue.Empty as exc:
        raise RuntimeError("Bayesian worker benchmark returned no result") from exc
    finally:
        output_queue.close()
        output_queue.join_thread()
        process.close()
    round_trip_ms = (time.perf_counter() - started) * 1000.0
    if not isinstance(message, dict) or message.get("status") != "ok":
        code = message.get("code") if isinstance(message, dict) else "invalid_message"
        raise RuntimeError(f"Bayesian worker benchmark failed with stable code {code}")
    result = message.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Bayesian worker benchmark returned an invalid payload")
    child_ms = float(result["budget"]["elapsed_ms"])
    fit_ms = float(result["model"]["fit_elapsed_ms"])
    return {
        "worker_round_trip_ms": round_trip_ms,
        "child_calculation_ms": child_ms,
        "gp_fit_ms": fit_ms,
        "non_fit_calculation_ms": max(0.0, child_ms - fit_ms),
        "round_trip_overhead_ms": max(0.0, round_trip_ms - child_ms),
    }


def _benchmark_payload(
    *,
    case_name: str,
    factor_count: int,
    observation_count: int,
    candidate_count: int,
    seed: int,
) -> dict[str, Any]:
    factors = [
        {"factor_id": f"x{index + 1}", "low": 0.0, "high": 1.0}
        for index in range(factor_count)
    ]
    points = [
        [_counter_uniform(case_name, row, column) for column in range(factor_count)]
        for row in range(observation_count)
    ]
    observations = [
        {
            "normalized": {
                factor["factor_id"]: point[index]
                for index, factor in enumerate(factors)
            },
            "objective_value": _synthetic_objective(point),
        }
        for point in points
    ]
    return {
        "factors": factors,
        "constraints": [],
        "observations": observations,
        "excluded_normalized": points,
        "objective_direction": "maximize",
        "search": {
            "random_seed": seed,
            "xi": 0.01,
            "candidate_count": candidate_count,
            "local_start_count": 4,
            "max_iterations": 80,
            "max_evaluations": 4096,
            "model_max_iterations": 75,
            "model_max_evaluations": 500,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 30_000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
    }


def _counter_uniform(case_name: str, row: int, column: int) -> float:
    digest = hashlib.sha256(f"{case_name}:{row}:{column}".encode("ascii")).digest()
    integer = int.from_bytes(digest[:8], "big")
    return (integer + 0.5) / 2**64


def _synthetic_objective(point: list[float]) -> float:
    return sum(
        math.sin((index + 1) * math.pi * value) - 0.1 * (value - 0.4) ** 2
        for index, value in enumerate(point)
    )


def _summary(samples: list[dict[str, float]], field: str) -> dict[str, float]:
    return _numeric_summary([sample[field] for sample in samples])


def _numeric_summary(values: list[float]) -> dict[str, float]:
    return {
        "minimum": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "maximum": round(max(values), 3),
    }


if __name__ == "__main__":
    raise SystemExit(main())
