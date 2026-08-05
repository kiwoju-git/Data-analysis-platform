from __future__ import annotations

import math
import time
import warnings
from importlib.metadata import version
from typing import Any, Final, Literal

from app.api.v1.schemas.bayesian import MAX_COMPLETED_OBSERVATIONS
from app.statistics.bayesian_optimization import (
    MIN_COMPLETED_OBSERVATIONS,
    BayesianOptimizationError,
    _candidate_pool_for_factors,
    _constraint_evaluations,
    _constraints_satisfied,
    _finite_float,
    _has_discrete_factors,
    _novel,
    _scipy_constraints,
    _SearchBudget,
    _to_actual,
    _validated_constraints,
    _validated_excluded_points,
    _validated_factors,
    _validated_observations,
    expected_improvement,
    expected_target_improvement,
)

BAYESIAN_BATCH_POLICY: Final = "greedy_posterior_mean_fantasy_ei_v1"
BAYESIAN_BATCH_RESULT_SCHEMA_VERSION: Final[Literal[1]] = 1
BAYESIAN_BATCH_ITEM_SCHEMA_VERSION: Final[Literal[1]] = 1
BAYESIAN_BATCH_MODEL_SCHEMA_VERSION: Final[Literal[2]] = 2


def calculate_bayesian_recommendation_batch(payload: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    import scipy  # type: ignore[import-untyped]
    import sklearn  # type: ignore[import-untyped]
    from scipy.optimize import minimize  # type: ignore[import-untyped]
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]
    from sklearn.gaussian_process import GaussianProcessRegressor  # type: ignore[import-untyped]
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        ConstantKernel,
        Matern,
    )
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    started = time.perf_counter()
    factors = _validated_factors(payload.get("factors"))
    constraints = _validated_constraints(payload.get("constraints"), factors)
    observations = _validated_observations(payload.get("observations"), factors)
    excluded = _validated_excluded_points(payload.get("excluded_normalized"), factors)
    options = _validated_batch_options(payload)
    objective = _validated_objective(payload.get("objective"))
    batch_size = options["batch_size"]
    if len(observations) < max(MIN_COMPLETED_OBSERVATIONS, len(factors) + 1):
        raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
    if len(observations) > MAX_COMPLETED_OBSERVATIONS:
        raise BayesianOptimizationError("bayesian_optimization_history_incomplete")

    x_train = np.asarray([item[0] for item in observations], dtype=float)
    observed = np.asarray([item[1] for item in observations], dtype=float)
    goal_type = objective["goal_type"]
    multiplier = -1.0 if goal_type == "minimize" else 1.0
    transformed = multiplier * observed if goal_type != "match_target" else observed.copy()
    objective_mean = float(np.mean(transformed))
    objective_scale = float(np.std(transformed))
    warning_codes: list[str] = []
    if objective_scale <= max(1e-12, abs(objective_mean) * 1e-12):
        objective_scale = 1.0
        warning_codes.append("bayesian_optimization_constant_objective")
    y_train = (transformed - objective_mean) / objective_scale
    incumbent_standardized = float(np.max(y_train))
    target_standardized: float | None = None
    incumbent_distance_standardized: float | None = None
    if goal_type == "match_target":
        target_standardized = (float(objective["target_value"]) - objective_mean) / objective_scale
        incumbent_distance_standardized = float(np.min(np.abs(y_train - target_standardized)))

    model_evaluations = 0

    def bounded_optimizer(
        objective_function: Any,
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
            value, gradient = objective_function(theta, eval_gradient=True)
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
    fitted_kernel = model.kernel_
    fitted_log_likelihood = float(model.log_marginal_likelihood_value_)

    budget = _SearchBudget(
        started=started,
        deadline=started + options["time_budget_ms"] / 1000.0,
        max_evaluations=options["max_evaluations_total"],
    )
    rng = np.random.default_rng(options["random_seed"])
    selected: list[Any] = []
    items: list[dict[str, Any]] = []
    fantasy_x = x_train.copy()
    fantasy_y = y_train.copy()
    current_model = model
    scipy_constraints = _scipy_constraints(factors, constraints)

    completed_points = [item[0] for item in observations]
    existing_points = [*excluded]
    for step in range(batch_size):
        candidates = _candidate_pool_for_factors(
            rng,
            factors,
            options["candidate_count_per_step"],
        )
        all_excluded = [*excluded, *[point.tolist() for point in selected]]
        feasible = np.asarray(
            [
                candidate
                for candidate in candidates
                if _constraints_satisfied(_to_actual(candidate, factors), constraints)
                and _novel(candidate, all_excluded, options["duplicate_tolerance"])
            ],
            dtype=float,
        )
        if feasible.size == 0:
            raise BayesianOptimizationError("bayesian_optimization_batch_incomplete")
        try:
            budget = budget.consume(len(feasible))
        except BayesianOptimizationError as exc:
            raise BayesianOptimizationError("bayesian_optimization_batch_incomplete") from exc
        mean, std = current_model.predict(feasible, return_std=True)
        acquisition = _acquisition(
            mean,
            std,
            goal_type=goal_type,
            incumbent=incumbent_standardized,
            target=target_standardized,
            incumbent_distance=incumbent_distance_standardized,
            xi=options["xi_standardized"],
        )
        if not np.all(np.isfinite(acquisition)):
            raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
        order = np.argsort(-acquisition, kind="stable")
        best_x = feasible[int(order[0])].copy()
        best_acquisition = float(acquisition[int(order[0])])

        def negative_acquisition(
            candidate: Any,
            model: Any = current_model,
        ) -> float:
            nonlocal budget
            budget = budget.consume()
            candidate_array = np.asarray(candidate, dtype=float).reshape(1, -1)
            candidate_mean, candidate_std = model.predict(
                candidate_array,
                return_std=True,
            )
            value = _acquisition(
                candidate_mean,
                candidate_std,
                goal_type=goal_type,
                incumbent=incumbent_standardized,
                target=target_standardized,
                incumbent_distance=incumbent_distance_standardized,
                xi=options["xi_standardized"],
            )
            return -float(value[0])

        local_start_count = (
            0 if _has_discrete_factors(factors) else options["local_start_count_per_step"]
        )
        for index in order[:local_start_count]:
            try:
                local = minimize(
                    negative_acquisition,
                    feasible[int(index)],
                    method="SLSQP",
                    bounds=[(0.0, 1.0)] * len(factors),
                    constraints=scipy_constraints,
                    options={
                        "maxiter": options["max_iterations_per_step"],
                        "ftol": 1e-12,
                        "disp": False,
                    },
                )
            except BayesianOptimizationError as exc:
                raise BayesianOptimizationError("bayesian_optimization_batch_incomplete") from exc
            local_x = np.asarray(local.x, dtype=float)
            if (
                local.success
                and np.all(np.isfinite(local_x))
                and _constraints_satisfied(_to_actual(local_x, factors), constraints)
                and _novel(local_x, all_excluded, options["duplicate_tolerance"])
            ):
                local_value = -float(local.fun)
                if math.isfinite(local_value) and local_value > best_acquisition:
                    best_x = local_x
                    best_acquisition = local_value

        if not _novel(best_x, all_excluded, options["duplicate_tolerance"]):
            raise BayesianOptimizationError("bayesian_optimization_batch_incomplete")
        actual = _to_actual(best_x, factors)
        if not _constraints_satisfied(actual, constraints):
            raise BayesianOptimizationError("bayesian_optimization_batch_incomplete")
        final_mean, final_std = current_model.predict(
            best_x.reshape(1, -1),
            return_std=True,
        )
        standardized_mean = float(final_mean[0])
        standardized_std = float(final_std[0])
        predicted_transformed = standardized_mean * objective_scale + objective_mean
        predicted_objective = (
            multiplier * predicted_transformed
            if goal_type != "match_target"
            else predicted_transformed
        )
        posterior_std = standardized_std * objective_scale
        incumbent_objective = _incumbent_objective(observed, objective)
        breakdown = _acquisition_breakdown(
            standardized_mean,
            standardized_std,
            goal_type=goal_type,
            incumbent=incumbent_standardized,
            target=target_standardized,
            incumbent_distance=incumbent_distance_standardized,
            xi=options["xi_standardized"],
        )
        probability = breakdown["probability_of_improvement"]
        target_value = float(objective["target_value"]) if goal_type == "match_target" else None
        predicted_target_distance = (
            abs(predicted_objective - target_value) if target_value is not None else None
        )
        incumbent_target_distance = (
            float(np.min(np.abs(observed - target_value))) if target_value is not None else None
        )
        if goal_type == "match_target":
            if incumbent_target_distance is None or predicted_target_distance is None:
                raise BayesianOptimizationError("bayesian_optimization_target_invalid")
            predicted_margin = float(incumbent_target_distance - predicted_target_distance)
        else:
            predicted_margin = float(
                incumbent_objective - predicted_objective
                if goal_type == "minimize"
                else predicted_objective - incumbent_objective
            )
        mean_term = breakdown["mean_improvement_term"]
        uncertainty_term = breakdown["uncertainty_term"]
        if mean_term is None or uncertainty_term is None:
            raise BayesianOptimizationError("bayesian_optimization_acquisition_invalid")
        reason = _reason_code(
            step=step,
            goal_type=goal_type,
            predicted_margin=predicted_margin,
            mean_term=float(mean_term),
            uncertainty_term=float(uncertainty_term),
        )
        normalized = {
            str(factor["factor_id"]): float(best_x[index]) for index, factor in enumerate(factors)
        }
        items.append(
            {
                "rank": step + 1,
                "actual_coordinates": actual,
                "normalized_coordinates": normalized,
                "predicted_objective_mean": predicted_objective,
                "posterior_standard_deviation": posterior_std,
                "incumbent_objective": incumbent_objective,
                "acquisition_kind": options["acquisition_kind"],
                "acquisition_value": max(0.0, best_acquisition * objective_scale),
                "predicted_improvement_margin": predicted_margin,
                "probability_of_improvement": probability,
                "target_value": target_value,
                "predicted_target_distance": predicted_target_distance,
                "incumbent_target_distance": incumbent_target_distance,
                "nearest_completed_distance": _nearest_distance(
                    best_x,
                    completed_points,
                ),
                "nearest_existing_trial_distance": _nearest_distance(
                    best_x,
                    existing_points,
                ),
                "nearest_earlier_batch_item_distance": _nearest_distance(
                    best_x,
                    [point.tolist() for point in selected],
                ),
                "constraint_evaluations": _constraint_evaluations(actual, constraints),
                "fantasy_step": step,
                "conditioned_on_ranks": list(range(1, step + 1)),
                "reason_code": reason,
                "acquisition_breakdown": {
                    key: value
                    for key, value in breakdown.items()
                    if key != "probability_of_improvement"
                },
            }
        )
        selected.append(best_x.copy())
        fantasy_x = np.vstack([fantasy_x, best_x.reshape(1, -1)])
        fantasy_y = np.concatenate([fantasy_y, np.asarray([standardized_mean])])
        if step + 1 < batch_size:
            current_model = GaussianProcessRegressor(
                kernel=fitted_kernel,
                alpha=options["jitter"],
                optimizer=None,
                normalize_y=False,
                copy_X_train=True,
            )
            try:
                with threadpool_limits(limits=1):
                    current_model.fit(fantasy_x, fantasy_y)
            except (ArithmeticError, FloatingPointError, ValueError) as exc:
                raise BayesianOptimizationError("bayesian_optimization_batch_incomplete") from exc

    if len(items) != batch_size:
        raise BayesianOptimizationError("bayesian_optimization_batch_incomplete")
    fitted_product = fitted_kernel
    constant_value = float(fitted_product.k1.constant_value)
    length_scale_array = np.atleast_1d(fitted_product.k2.length_scale)
    warning_codes.extend(
        [
            "bayesian_optimization_confirmation_required",
            "bayesian_optimization_no_global_optimum_guarantee",
            "bayesian_optimization_fantasy_is_not_observation",
        ]
    )
    return {
        "schema_version": BAYESIAN_BATCH_RESULT_SCHEMA_VERSION,
        "batch_policy": BAYESIAN_BATCH_POLICY,
        "batch_size": batch_size,
        "acquisition": {
            "kind": options["acquisition_kind"],
            "exploration_profile": options["exploration_profile"],
            "xi_standardized": options["xi_standardized"],
        },
        "shared_model": {
            "schema_version": BAYESIAN_BATCH_MODEL_SCHEMA_VERSION,
            "kernel_policy": "constant_times_matern_5_2_ard_v1",
            "fitted_kernel": str(fitted_product),
            "constant_value": constant_value,
            "length_scales": [float(item) for item in length_scale_array],
            "log_marginal_likelihood": fitted_log_likelihood,
            "objective_goal_type": goal_type,
            "objective_normalization_mean": objective_mean,
            "objective_normalization_scale": objective_scale,
            "target_value_standardized": target_standardized,
            "jitter": options["jitter"],
            "completed_observation_count": len(observations),
            "hyperparameter_restart_count": options["hyperparameter_restart_count"],
            "model_evaluations": model_evaluations,
            "fit_elapsed_ms": fit_elapsed_ms,
            "package_versions": {
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "scikit-learn": sklearn.__version__,
                "threadpoolctl": version("threadpoolctl"),
            },
        },
        "search_budget": {
            "candidate_count_per_step": options["candidate_count_per_step"],
            "local_start_count_per_step": options["local_start_count_per_step"],
            "max_evaluations_total": options["max_evaluations_total"],
            "evaluations_consumed": budget.evaluations,
            "model_max_iterations": options["model_max_iterations"],
            "model_max_evaluations": options["model_max_evaluations"],
            "model_evaluations_consumed": model_evaluations,
            "time_budget_ms": options["time_budget_ms"],
            "elapsed_ms": (time.perf_counter() - started) * 1000.0,
            "termination_reason": "search_completed",
        },
        "items": items,
        "warnings": list(dict.fromkeys(warning_codes)),
        "limitations": [
            "This is deterministic greedy posterior-mean fantasy batch EI, not exact joint qEI.",
            "Fantasy values diversify a batch and are never stored as observations.",
            "GP posterior uncertainty is model uncertainty, not a process tolerance.",
            "Recommendations require real experiments and do not guarantee a global optimum.",
        ],
    }


def bayesian_batch_worker_entry(output_queue: Any, payload: dict[str, Any]) -> None:
    try:
        result = calculate_bayesian_recommendation_batch(payload)
    except BayesianOptimizationError as exc:
        code = (
            "bayesian_optimization_batch_incomplete"
            if exc.code
            in {
                "bayesian_optimization_time_budget_exhausted",
                "bayesian_optimization_budget_exhausted",
            }
            else exc.code
        )
        output_queue.put({"status": "error", "code": code})
    except Exception:
        output_queue.put({"status": "error", "code": "bayesian_optimization_surrogate_fit_failed"})
    else:
        output_queue.put({"status": "ok", "result": result})


def _validated_objective(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
    goal_type = value.get("goal_type")
    if goal_type not in {"minimize", "maximize", "match_target"}:
        raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
    target_value = value.get("target_value")
    if goal_type == "match_target":
        target_value = _finite_float(
            target_value,
            "bayesian_optimization_objective_invalid",
        )
    elif target_value is not None:
        raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
    return {"goal_type": goal_type, "target_value": target_value}


def _validated_batch_options(payload: dict[str, Any]) -> dict[str, Any]:
    search = payload.get("search")
    acquisition = payload.get("acquisition")
    batch_size = payload.get("batch_size")
    if (
        not isinstance(search, dict)
        or not isinstance(acquisition, dict)
        or not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 1 <= batch_size <= 8
    ):
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    required_search = {
        "random_seed",
        "candidate_count_per_step",
        "local_start_count_per_step",
        "max_iterations_per_step",
        "max_evaluations_total",
        "model_max_iterations",
        "model_max_evaluations",
        "hyperparameter_restart_count",
        "time_budget_ms",
        "jitter",
        "duplicate_tolerance",
        "batch_policy",
    }
    if set(search) != required_search or search.get("batch_policy") != BAYESIAN_BATCH_POLICY:
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    profile = acquisition.get("exploration_profile")
    kind = acquisition.get("kind")
    if profile not in {"exploitation", "balanced", "exploration", "custom"}:
        raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
    if kind not in {"expected_improvement", "expected_target_improvement"}:
        raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
    result = dict(search)
    result.update(
        {
            "batch_size": batch_size,
            "acquisition_kind": kind,
            "exploration_profile": profile,
            "xi_standardized": _finite_float(
                acquisition.get("xi_standardized"),
                "bayesian_optimization_objective_invalid",
            ),
        }
    )
    integer_bounds = {
        "random_seed": (0, 2_147_483_647),
        "candidate_count_per_step": (32, 4096),
        "local_start_count_per_step": (0, 16),
        "max_iterations_per_step": (1, 500),
        "max_evaluations_total": (32, 160_000),
        "model_max_iterations": (1, 200),
        "model_max_evaluations": (2, 2_000),
        "hyperparameter_restart_count": (0, 3),
        "time_budget_ms": (1_000, 60_000),
    }
    for key, (minimum, maximum) in integer_bounds.items():
        item = result[key]
        if not isinstance(item, int) or isinstance(item, bool) or not minimum <= item <= maximum:
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    result["jitter"] = _finite_float(
        result["jitter"],
        "bayesian_optimization_surrogate_fit_failed",
    )
    result["duplicate_tolerance"] = _finite_float(
        result["duplicate_tolerance"],
        "bayesian_optimization_duplicate_candidate",
    )
    if (
        not 0.0 <= result["xi_standardized"] <= 10.0
        or not 1e-12 <= result["jitter"] <= 1e-3
        or not 1e-12 <= result["duplicate_tolerance"] <= 0.1
        or result["max_evaluations_total"] < result["candidate_count_per_step"] * batch_size
    ):
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    return result


def _acquisition(
    mean: Any,
    standard_deviation: Any,
    *,
    goal_type: str,
    incumbent: float,
    target: float | None,
    incumbent_distance: float | None,
    xi: float,
) -> Any:
    if goal_type == "match_target":
        if target is None or incumbent_distance is None:
            raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
        return expected_target_improvement(
            mean,
            standard_deviation,
            target,
            incumbent_distance,
            xi,
        )
    return expected_improvement(mean, standard_deviation, incumbent, xi)


def _acquisition_breakdown(
    mean: float,
    standard_deviation: float,
    *,
    goal_type: str,
    incumbent: float,
    target: float | None,
    incumbent_distance: float | None,
    xi: float,
) -> dict[str, float | None]:
    from scipy.special import ndtr  # type: ignore[import-untyped]

    if goal_type == "match_target":
        if target is None or incumbent_distance is None:
            raise BayesianOptimizationError("bayesian_optimization_objective_invalid")
        radius = max(incumbent_distance - xi, 0.0)
        acquisition = float(
            expected_target_improvement(
                [mean],
                [standard_deviation],
                target,
                incumbent_distance,
                xi,
            )[0]
        )
        deterministic = max(radius - abs(mean - target), 0.0)
        if standard_deviation > 0.0 and radius > 0.0:
            probability = float(
                ndtr((target + radius - mean) / standard_deviation)
                - ndtr((target - radius - mean) / standard_deviation)
            )
        else:
            probability = 1.0 if abs(mean - target) < radius else 0.0
        return {
            "xi_standardized": xi,
            "standardized_margin": incumbent_distance - abs(mean - target) - xi,
            "z_value": None,
            "normal_cdf": None,
            "normal_density": None,
            "mean_improvement_term": deterministic,
            "uncertainty_term": max(acquisition - deterministic, 0.0),
            "probability_of_improvement": max(0.0, min(1.0, probability)),
        }
    margin = mean - incumbent - xi
    if standard_deviation > 0.0:
        z_value = margin / standard_deviation
        cdf = float(ndtr(z_value))
        density = math.exp(-0.5 * z_value**2) / math.sqrt(2.0 * math.pi)
        mean_term = margin * cdf
        uncertainty_term = standard_deviation * density
    else:
        z_value = None
        cdf = 1.0 if margin > 0.0 else 0.0
        density = None
        mean_term = max(margin, 0.0)
        uncertainty_term = 0.0
    return {
        "xi_standardized": xi,
        "standardized_margin": margin,
        "z_value": z_value,
        "normal_cdf": cdf,
        "normal_density": density,
        "mean_improvement_term": mean_term,
        "uncertainty_term": uncertainty_term,
        "probability_of_improvement": cdf,
    }


def _incumbent_objective(observed: Any, objective: dict[str, Any]) -> float:
    import numpy as np

    if objective["goal_type"] == "maximize":
        return float(np.max(observed))
    if objective["goal_type"] == "minimize":
        return float(np.min(observed))
    target = float(objective["target_value"])
    return float(observed[int(np.argmin(np.abs(observed - target)))])


def _nearest_distance(candidate: Any, points: list[Any]) -> float | None:
    if not points:
        return None
    import numpy as np

    candidate_array = np.asarray(candidate, dtype=float)
    return min(
        float(np.linalg.norm(candidate_array - np.asarray(point, dtype=float))) for point in points
    )


def _reason_code(
    *,
    step: int,
    goal_type: str,
    predicted_margin: float,
    mean_term: float,
    uncertainty_term: float,
) -> str:
    if step > 0:
        return "batch_diversity_adjusted"
    if goal_type == "match_target":
        return "target_distance_reduction"
    if predicted_margin <= 0.0:
        return "uncertainty_driven"
    if mean_term > uncertainty_term * 1.5:
        return "predicted_improvement_driven"
    return "balanced_improvement_uncertainty"
