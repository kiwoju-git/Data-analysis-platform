"""Opt-in, bounded initialization search; not a JMP optimizer implementation."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError

FIT_POLICY = "bounded_multiscale_starts_v1"


@dataclass(frozen=True)
class BoFitPolicy:
    deterministic_start_count: int = 1

    def __post_init__(self) -> None:
        if (
            type(self.deterministic_start_count) is not int
            or not 1 <= self.deterministic_start_count <= 3
        ):
            raise ValueError("bayesian_fit_policy_invalid")


def screened_starts(theta: Any, bounds: Any, predictor_count: int) -> list[Any]:
    import numpy as np

    starts = [theta.copy()]
    for fraction in np.linspace(0.0, 1.0, 9):
        candidate = theta.copy()
        candidate[1 : predictor_count + 1] = (
            bounds[1 : predictor_count + 1, 0] * (1 - fraction)
            + bounds[1 : predictor_count + 1, 1] * fraction
        )
        # The log-space midpoint can differ from log(1) by one arithmetic ULP.
        if not any(
            np.allclose(candidate, old, atol=8 * np.finfo(float).eps, rtol=0) for old in starts
        ):
            starts.append(candidate)
    return starts


def bounded_multiscale_optimize(
    theta: Any,
    bounds: Any,
    predictor_count: int,
    policy: BoFitPolicy,
    search: dict[str, Any],
    evaluate: Callable[[Any], tuple[float, Any]],
) -> tuple[Any, list[dict[str, Any]], dict[str, Any]]:
    import numpy as np
    from scipy.optimize import minimize  # type: ignore[import-untyped]

    best_value = math.inf
    best_theta = theta.copy()
    selected: dict[str, Any] = {}
    screening: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    local_best: list[dict[str, Any]] = []

    def consider(point: Any, value: float, **origin: Any) -> None:
        nonlocal best_value, best_theta, selected
        if (
            not math.isfinite(value)
            or not np.all(np.isfinite(point))
            or np.any(point < bounds[:, 0])
            or np.any(point > bounds[:, 1])
        ):
            raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
        if value < best_value:
            best_value, best_theta, selected = float(value), point.copy(), origin

    starts = screened_starts(theta, bounds, predictor_count)
    for index, initial in enumerate(starts):
        value, _ = evaluate(initial)
        consider(initial, value, stage="screen", screen_index=index, start_index=None)
        screening.append({"log_parameters": initial.tolist(), "negative_log_likelihood": value})
    indices = sorted(
        range(len(starts)), key=lambda i: (screening[i]["negative_log_likelihood"], i)
    )[: policy.deterministic_start_count]
    local = [starts[i] for i in indices]
    rng = np.random.default_rng(search["random_seed"])
    local.extend(
        rng.uniform(bounds[:, 0], bounds[:, 1])
        for _ in range(search["hyperparameter_restart_count"])
    )
    initial_values: list[float] = []
    for index, initial in enumerate(local):
        calls = 0
        best_receipt: dict[str, Any] = {}

        def tracked(point: Any, start_index: int = index) -> tuple[float, Any]:
            nonlocal calls, best_receipt
            value, derivative = evaluate(point)
            if calls == 0:
                initial_values.append(value)
            calls += 1
            consider(
                point, value, stage="local_evaluation", screen_index=None, start_index=start_index
            )
            if not best_receipt or value < best_receipt["negative_log_likelihood"]:
                best_receipt = {
                    "log_parameters": point.tolist(),
                    "negative_log_likelihood": float(value),
                    "evaluation_index": calls - 1,
                }
            return value, derivative

        result = minimize(
            tracked,
            initial,
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={
                "maxiter": search["model_max_iterations"],
                "maxfun": search["model_max_evaluations"],
                "ftol": 1e-12,
            },
        )
        if not np.all(np.isfinite(result.x)) or not math.isfinite(float(result.fun)):
            raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
        traces.append(
            {
                "success": bool(result.success),
                "status": int(result.status),
                "termination_reason": str(result.message),
                "iterations": int(result.nit),
                "evaluations": calls,
                "initial_log_parameters": initial.tolist(),
                "final_log_parameters": result.x.tolist(),
                "negative_log_likelihood": float(result.fun),
            }
        )
        local_best.append(best_receipt)
    return (
        best_theta,
        traces,
        {
            "schema_version": 1,
            "policy": FIT_POLICY,
            "deterministic_start_count": policy.deterministic_start_count,
            "screening": screening,
            "refined_screen_indices": indices,
            "start_initial_negative_log_likelihoods": initial_values,
            "start_best_evaluations": local_best,
            "selected": {
                **selected,
                "log_parameters": best_theta.tolist(),
                "negative_log_likelihood": best_value,
            },
            "global_optimum_guaranteed": False,
        },
    )


def parameter_bound_hits(theta: Any, bounds: Any, predictor_count: int) -> list[dict[str, Any]]:
    names = ["signal_amplitude", *(["length_scale"] * predictor_count), "measurement_variance"]
    hits = []
    for index, (log_value, pair) in enumerate(zip(theta, bounds, strict=True)):
        value = math.exp(float(log_value))
        for side, log_bound in zip(("lower", "upper"), pair, strict=True):
            bound = math.exp(float(log_bound))
            if math.isclose(value, bound, rel_tol=1e-5):
                hits.append(
                    {
                        "parameter": names[index],
                        "factor_index": index - 1 if 1 <= index <= predictor_count else None,
                        "side": side,
                        "value": value,
                        "bound": bound,
                    }
                )
    return hits
