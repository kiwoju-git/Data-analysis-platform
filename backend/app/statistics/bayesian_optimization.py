from __future__ import annotations

import math
import time
import warnings
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any, Final, Literal

BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION: Final[Literal[1]] = 1
BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION: Final[Literal[1]] = 1
MIN_COMPLETED_OBSERVATIONS = 2
MAX_COMPLETED_OBSERVATIONS = 200


class BayesianOptimizationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class _SearchBudget:
    started: float
    deadline: float
    max_evaluations: int
    evaluations: int = 0

    def consume(self, count: int = 1) -> _SearchBudget:
        if time.perf_counter() >= self.deadline:
            raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
        if self.evaluations + count > self.max_evaluations:
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
        return _SearchBudget(
            started=self.started,
            deadline=self.deadline,
            max_evaluations=self.max_evaluations,
            evaluations=self.evaluations + count,
        )


def expected_improvement(
    mean: Any,
    standard_deviation: Any,
    incumbent: float,
    xi: float,
) -> Any:
    import numpy as np
    from scipy.special import ndtr  # type: ignore[import-untyped]

    mean_values = np.asarray(mean, dtype=float)
    std_values = np.asarray(standard_deviation, dtype=float)
    result = np.zeros_like(mean_values, dtype=float)
    positive = std_values > 0.0
    if np.any(positive):
        improvement = mean_values[positive] - incumbent - xi
        z_value = improvement / std_values[positive]
        density = np.exp(-0.5 * z_value**2) / math.sqrt(2.0 * math.pi)
        result[positive] = improvement * ndtr(z_value) + std_values[positive] * density
    return result


def calculate_bayesian_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import scipy  # type: ignore[import-untyped]
    import sklearn  # type: ignore[import-untyped]
    from scipy.optimize import minimize  # type: ignore[import-untyped]
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]
    from sklearn.gaussian_process import (  # type: ignore[import-untyped]
        GaussianProcessRegressor,
    )
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        ConstantKernel,
        Matern,
    )
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    started = time.perf_counter()
    factors = _validated_factors(payload.get("factors"))
    constraints = _validated_constraints(payload.get("constraints"), factors)
    observations = _validated_observations(payload.get("observations"), factors)
    excluded = _validated_excluded_points(payload.get("excluded_normalized"), len(factors))
    options = _validated_options(payload.get("search"))
    direction = payload.get("objective_direction")
    if direction not in {"minimize", "maximize"}:
        raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
    if len(observations) < max(MIN_COMPLETED_OBSERVATIONS, len(factors) + 1):
        raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
    if len(observations) > MAX_COMPLETED_OBSERVATIONS:
        raise BayesianOptimizationError("bayesian_optimization_history_incomplete")

    x_train = np.asarray([item[0] for item in observations], dtype=float)
    observed = np.asarray([item[1] for item in observations], dtype=float)
    multiplier = 1.0 if direction == "maximize" else -1.0
    transformed = multiplier * observed
    objective_mean = float(np.mean(transformed))
    objective_scale = float(np.std(transformed))
    warning_codes: list[str] = []
    if objective_scale <= max(1e-12, abs(objective_mean) * 1e-12):
        objective_scale = 1.0
        warning_codes.append("bayesian_optimization_constant_objective")
    y_train = (transformed - objective_mean) / objective_scale
    incumbent_standardized = float(np.max(y_train))

    model_evaluations = 0

    def bounded_optimizer(
        objective: Any,
        initial_theta: Any,
        bounds: Any,
    ) -> tuple[Any, float]:
        nonlocal model_evaluations

        def evaluate(theta: Any) -> tuple[float, Any]:
            nonlocal model_evaluations
            if model_evaluations >= options["model_max_evaluations"]:
                raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
            if time.perf_counter() >= started + options["time_budget_ms"] / 1000.0:
                raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
            model_evaluations += 1
            value, gradient = objective(theta, eval_gradient=True)
            return float(value), gradient

        result = minimize(
            evaluate,
            initial_theta,
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={
                "maxiter": options["model_max_iterations"],
                "maxfun": options["model_max_evaluations"],
                "ftol": 1e-12,
            },
        )
        if not np.all(np.isfinite(result.x)) or not math.isfinite(float(result.fun)):
            raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
        if not result.success:
            warning_codes.append("bayesian_optimization_model_convergence_warning")
        return result.x, float(result.fun)

    kernel = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(
        length_scale=np.ones(len(factors), dtype=float),
        length_scale_bounds=(1e-2, 1e2),
        nu=2.5,
    )
    model = GaussianProcessRegressor(
        kernel=kernel,
        alpha=options["jitter"],
        optimizer=bounded_optimizer,
        n_restarts_optimizer=options["hyperparameter_restart_count"],
        normalize_y=False,
        random_state=options["random_seed"],
        copy_X_train=True,
    )
    fit_started = time.perf_counter()
    try:
        with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model.fit(x_train, y_train)
        if any(issubclass(item.category, ConvergenceWarning) for item in caught):
            warning_codes.append("bayesian_optimization_model_convergence_warning")
    except BayesianOptimizationError:
        raise
    except (ArithmeticError, FloatingPointError, ValueError) as exc:
        raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed") from exc
    fit_elapsed_ms = (time.perf_counter() - fit_started) * 1000.0

    deadline = started + options["time_budget_ms"] / 1000.0
    budget = _SearchBudget(
        started=started,
        deadline=deadline,
        max_evaluations=options["max_evaluations"],
    )
    rng = np.random.default_rng(options["random_seed"])
    candidates = _candidate_pool(rng, len(factors), options["candidate_count"])
    feasible = np.asarray(
        [
            candidate
            for candidate in candidates
            if _constraints_satisfied(_to_actual(candidate, factors), constraints)
            and _novel(candidate, excluded, options["duplicate_tolerance"])
        ],
        dtype=float,
    )
    if feasible.size == 0:
        raise BayesianOptimizationError("bayesian_optimization_no_feasible_candidate")
    try:
        budget = budget.consume(len(feasible))
    except BayesianOptimizationError as exc:
        if exc.code == "bayesian_optimization_budget_exhausted":
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted") from exc
        raise
    mean, std = model.predict(feasible, return_std=True)
    acquisition = expected_improvement(mean, std, incumbent_standardized, options["xi"])
    if not np.all(np.isfinite(acquisition)):
        raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
    order = np.argsort(-acquisition, kind="stable")
    best_x = feasible[int(order[0])].copy()
    best_ei = float(acquisition[int(order[0])])
    local_starts_attempted = 0
    local_success_count = 0
    local_iterations = 0
    termination_reason: Literal["search_completed", "evaluation_budget", "time_budget"] = (
        "search_completed"
    )

    scipy_constraints = _scipy_constraints(factors, constraints)

    def negative_ei(candidate: Any) -> float:
        nonlocal budget
        budget = budget.consume()
        candidate_array = np.asarray(candidate, dtype=float).reshape(1, -1)
        candidate_mean, candidate_std = model.predict(candidate_array, return_std=True)
        value = expected_improvement(
            candidate_mean,
            candidate_std,
            incumbent_standardized,
            options["xi"],
        )
        return -float(value[0])

    for index in order[: options["local_start_count"]]:
        local_starts_attempted += 1
        try:
            local = minimize(
                negative_ei,
                feasible[int(index)],
                method="SLSQP",
                bounds=[(0.0, 1.0)] * len(factors),
                constraints=scipy_constraints,
                options={
                    "maxiter": options["max_iterations"],
                    "ftol": 1e-12,
                    "disp": False,
                },
            )
        except BayesianOptimizationError as exc:
            termination_reason = (
                "time_budget"
                if exc.code == "bayesian_optimization_time_budget_exhausted"
                else "evaluation_budget"
            )
            warning_codes.append(
                "bayesian_optimization_time_budget_exhausted"
                if termination_reason == "time_budget"
                else "bayesian_optimization_budget_exhausted"
            )
            break
        local_iterations += int(getattr(local, "nit", 0))
        local_x = np.asarray(local.x, dtype=float)
        if (
            local.success
            and np.all(np.isfinite(local_x))
            and _constraints_satisfied(_to_actual(local_x, factors), constraints)
            and _novel(local_x, excluded, options["duplicate_tolerance"])
        ):
            local_success_count += 1
            local_ei = -float(local.fun)
            if math.isfinite(local_ei) and local_ei > best_ei:
                best_x = local_x
                best_ei = local_ei

    if not _novel(best_x, excluded, options["duplicate_tolerance"]):
        raise BayesianOptimizationError("bayesian_optimization_duplicate_candidate")
    actual = _to_actual(best_x, factors)
    if not _constraints_satisfied(actual, constraints):
        raise BayesianOptimizationError("bayesian_optimization_no_feasible_candidate")
    final_mean, final_std = model.predict(best_x.reshape(1, -1), return_std=True)
    predicted_transformed = float(final_mean[0]) * objective_scale + objective_mean
    predicted_objective = multiplier * predicted_transformed
    posterior_std = float(final_std[0]) * objective_scale
    incumbent_objective = float(np.max(observed) if direction == "maximize" else np.min(observed))
    fitted_product = model.kernel_
    constant_value = float(fitted_product.k1.constant_value)
    length_scale_array = np.atleast_1d(fitted_product.k2.length_scale)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    warning_codes.extend(
        [
            "bayesian_optimization_confirmation_required",
            "bayesian_optimization_no_global_optimum_guarantee",
        ]
    )
    warning_codes = list(dict.fromkeys(warning_codes))
    constraint_evaluations = _constraint_evaluations(actual, constraints)
    return {
        "schema_version": BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION,
        "recommended_actual_coordinates": actual,
        "recommended_normalized_coordinates": {
            factor["factor_id"]: float(best_x[index]) for index, factor in enumerate(factors)
        },
        "predicted_objective_mean": predicted_objective,
        "posterior_standard_deviation": posterior_std,
        "expected_improvement": max(0.0, best_ei * objective_scale),
        "incumbent_objective": incumbent_objective,
        "objective_direction": direction,
        "constraint_evaluations": constraint_evaluations,
        "model": {
            "schema_version": BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION,
            "kernel_policy": "constant_times_matern_5_2_ard_v1",
            "fitted_kernel": str(model.kernel_),
            "constant_value": constant_value,
            "length_scales": [float(value) for value in length_scale_array],
            "log_marginal_likelihood": float(model.log_marginal_likelihood_value_),
            "objective_direction_multiplier": multiplier,
            "objective_normalization_mean": objective_mean,
            "objective_normalization_scale": objective_scale,
            "jitter": options["jitter"],
            "completed_observation_count": len(observations),
            "hyperparameter_restart_count": options["hyperparameter_restart_count"],
            "model_evaluations": model_evaluations,
            "fit_elapsed_ms": fit_elapsed_ms,
            "package_versions": {
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "scikit-learn": sklearn.__version__,
                "joblib": version("joblib"),
                "threadpoolctl": version("threadpoolctl"),
            },
        },
        "budget": {
            "candidate_count_requested": options["candidate_count"],
            "feasible_candidate_count": int(len(feasible)),
            "local_start_count_requested": options["local_start_count"],
            "local_starts_attempted": local_starts_attempted,
            "local_success_count": local_success_count,
            "local_iterations": local_iterations,
            "max_evaluations": options["max_evaluations"],
            "evaluations_consumed": budget.evaluations,
            "model_max_iterations": options["model_max_iterations"],
            "model_max_evaluations": options["model_max_evaluations"],
            "model_evaluations_consumed": model_evaluations,
            "time_budget_ms": options["time_budget_ms"],
            "elapsed_ms": elapsed_ms,
            "termination_reason": termination_reason,
        },
        "warnings": warning_codes,
        "limitations": [
            "GP posterior uncertainty is model uncertainty, not a process tolerance.",
            "The recommendation requires a separate confirmation run.",
            "Neither acquisition search nor the recommendation guarantees a global optimum.",
        ],
    }


def bayesian_worker_entry(output_queue: Any, payload: dict[str, Any]) -> None:
    try:
        result = calculate_bayesian_recommendation(payload)
    except BayesianOptimizationError as exc:
        output_queue.put({"status": "error", "code": exc.code})
    except Exception:
        output_queue.put({"status": "error", "code": "bayesian_optimization_surrogate_fit_failed"})
    else:
        output_queue.put({"status": "ok", "result": result})


def _validated_factors(value: object) -> list[dict[str, float | str]]:
    if not isinstance(value, list) or not 1 <= len(value) <= 6:
        raise BayesianOptimizationError("bayesian_optimization_factor_space_invalid")
    result: list[dict[str, float | str]] = []
    ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("factor_id"), str):
            raise BayesianOptimizationError("bayesian_optimization_factor_space_invalid")
        factor_id = item["factor_id"]
        low = _finite_float(item.get("low"), "bayesian_optimization_factor_space_invalid")
        high = _finite_float(item.get("high"), "bayesian_optimization_factor_space_invalid")
        if factor_id in ids or not low < high:
            raise BayesianOptimizationError("bayesian_optimization_factor_space_invalid")
        ids.add(factor_id)
        result.append({"factor_id": factor_id, "low": low, "high": high})
    return result


def _validated_constraints(
    value: object,
    factors: list[dict[str, float | str]],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 16:
        raise BayesianOptimizationError("bayesian_optimization_constraint_invalid")
    factor_ids = {str(item["factor_id"]) for item in factors}
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or item.get("relation") not in {
            "less_than_or_equal",
            "greater_than_or_equal",
        }:
            raise BayesianOptimizationError("bayesian_optimization_constraint_invalid")
        terms = item.get("terms")
        if not isinstance(terms, list) or not terms:
            raise BayesianOptimizationError("bayesian_optimization_constraint_invalid")
        coefficients: dict[str, float] = {}
        for term in terms:
            if not isinstance(term, dict) or term.get("factor_id") not in factor_ids:
                raise BayesianOptimizationError("bayesian_optimization_constraint_invalid")
            factor_id = str(term["factor_id"])
            if factor_id in coefficients:
                raise BayesianOptimizationError("bayesian_optimization_constraint_invalid")
            coefficients[factor_id] = _finite_float(
                term.get("coefficient"), "bayesian_optimization_constraint_invalid"
            )
        if all(value == 0.0 for value in coefficients.values()):
            raise BayesianOptimizationError("bayesian_optimization_constraint_invalid")
        result.append(
            {
                "constraint_id": str(item.get("constraint_id", "constraint")),
                "name": str(item.get("name", "Constraint")),
                "relation": item["relation"],
                "bound": _finite_float(
                    item.get("bound"), "bayesian_optimization_constraint_invalid"
                ),
                "coefficients": coefficients,
            }
        )
    return result


def _validated_observations(
    value: object,
    factors: list[dict[str, float | str]],
) -> list[tuple[list[float], float]]:
    if not isinstance(value, list):
        raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
    factor_ids = [str(item["factor_id"]) for item in factors]
    observations: list[tuple[list[float], float]] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("normalized"), dict):
            raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
        normalized = item["normalized"]
        if set(normalized) != set(factor_ids):
            raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
        point = [
            _finite_float(normalized[factor_id], "bayesian_optimization_history_incomplete")
            for factor_id in factor_ids
        ]
        if any(coordinate < 0.0 or coordinate > 1.0 for coordinate in point):
            raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
        objective = _finite_float(
            item.get("objective_value"), "bayesian_optimization_history_incomplete"
        )
        observations.append((point, objective))
    return observations


def _validated_excluded_points(value: object, factor_count: int) -> list[list[float]]:
    if not isinstance(value, list):
        raise BayesianOptimizationError("bayesian_optimization_artifact_mismatch")
    points: list[list[float]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != factor_count:
            raise BayesianOptimizationError("bayesian_optimization_artifact_mismatch")
        point = [
            _finite_float(coordinate, "bayesian_optimization_artifact_mismatch")
            for coordinate in item
        ]
        if any(coordinate < 0.0 or coordinate > 1.0 for coordinate in point):
            raise BayesianOptimizationError("bayesian_optimization_artifact_mismatch")
        points.append(point)
    return points


def _validated_options(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    keys = {
        "random_seed",
        "xi",
        "candidate_count",
        "local_start_count",
        "max_iterations",
        "max_evaluations",
        "model_max_iterations",
        "model_max_evaluations",
        "hyperparameter_restart_count",
        "time_budget_ms",
        "jitter",
        "duplicate_tolerance",
    }
    if set(value) != keys:
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    options = dict(value)
    integer_bounds = {
        "random_seed": (0, 2_147_483_647),
        "candidate_count": (32, 4096),
        "local_start_count": (0, 16),
        "max_iterations": (1, 500),
        "max_evaluations": (32, 20_000),
        "model_max_iterations": (1, 200),
        "model_max_evaluations": (2, 2_000),
        "hyperparameter_restart_count": (0, 3),
        "time_budget_ms": (1_000, 60_000),
    }
    for key, (minimum, maximum) in integer_bounds.items():
        item = options[key]
        if not isinstance(item, int) or isinstance(item, bool) or not minimum <= item <= maximum:
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    options["xi"] = _finite_float(options["xi"], "bayesian_optimization_objective_invalid")
    options["jitter"] = _finite_float(
        options["jitter"], "bayesian_optimization_surrogate_fit_failed"
    )
    options["duplicate_tolerance"] = _finite_float(
        options["duplicate_tolerance"], "bayesian_optimization_duplicate_candidate"
    )
    if (
        not 0.0 <= options["xi"] <= 10.0
        or not 1e-12 <= options["jitter"] <= 1e-3
        or not 1e-12 <= options["duplicate_tolerance"] <= 0.1
        or options["max_evaluations"] < options["candidate_count"]
    ):
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    return options


def _candidate_pool(rng: Any, factor_count: int, count: int) -> Any:
    import numpy as np

    anchors: list[Any] = [np.full(factor_count, 0.5, dtype=float)]
    for index in range(factor_count):
        low = np.full(factor_count, 0.5, dtype=float)
        high = low.copy()
        low[index] = 0.0
        high[index] = 1.0
        anchors.extend([low, high])
    random_count = max(0, count - len(anchors))
    random_points = rng.random((random_count, factor_count))
    return np.vstack([np.asarray(anchors, dtype=float), random_points])[:count]


def _to_actual(
    normalized: Any,
    factors: list[dict[str, float | str]],
) -> dict[str, float]:
    return {
        str(factor["factor_id"]): float(factor["low"])
        + float(normalized[index]) * (float(factor["high"]) - float(factor["low"]))
        for index, factor in enumerate(factors)
    }


def _constraints_satisfied(actual: dict[str, float], constraints: list[dict[str, Any]]) -> bool:
    return all(item["satisfied"] for item in _constraint_evaluations(actual, constraints))


def _constraint_evaluations(
    actual: dict[str, float], constraints: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for constraint in constraints:
        lhs = sum(
            coefficient * actual[factor_id]
            for factor_id, coefficient in constraint["coefficients"].items()
        )
        bound = float(constraint["bound"])
        scale = max(1.0, abs(lhs), abs(bound))
        tolerance = 1e-10 * scale
        if constraint["relation"] == "less_than_or_equal":
            slack = bound - lhs
            satisfied = lhs <= bound + tolerance
        else:
            slack = lhs - bound
            satisfied = lhs >= bound - tolerance
        result.append(
            {
                "constraint_id": constraint["constraint_id"],
                "name": constraint["name"],
                "relation": constraint["relation"],
                "lhs": lhs,
                "bound": bound,
                "slack": slack,
                "satisfied": satisfied,
            }
        )
    return result


def _scipy_constraints(
    factors: list[dict[str, float | str]],
    constraints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for constraint in constraints:
        relation = constraint["relation"]
        bound = float(constraint["bound"])

        def evaluate(
            normalized: Any,
            *,
            constraint: dict[str, Any] = constraint,
            relation: str = relation,
            bound: float = bound,
        ) -> float:
            actual = _to_actual(normalized, factors)
            lhs = sum(
                coefficient * actual[factor_id]
                for factor_id, coefficient in constraint["coefficients"].items()
            )
            return bound - lhs if relation == "less_than_or_equal" else lhs - bound

        result.append({"type": "ineq", "fun": evaluate})
    return result


def _novel(candidate: Any, excluded: list[list[float]], tolerance: float) -> bool:
    if not excluded:
        return True
    import numpy as np

    candidate_array = np.asarray(candidate, dtype=float)
    return all(
        float(np.linalg.norm(candidate_array - np.asarray(point, dtype=float))) > tolerance
        for point in excluded
    )


def _finite_float(value: object, code: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise BayesianOptimizationError(code)
    converted = float(value)
    if not math.isfinite(converted):
        raise BayesianOptimizationError(code)
    return converted
