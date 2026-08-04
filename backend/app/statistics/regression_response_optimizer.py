from __future__ import annotations

from itertools import product
from math import isfinite
from typing import Any, Final, Literal

import numpy as np
from scipy.optimize import minimize  # type: ignore[import-untyped]

REGRESSION_RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION: Final[Literal[1]] = 1
MAX_CATEGORICAL_COMBINATIONS = 256
MAX_PROFILE_POINTS = 101


class RegressionResponseOptimizerError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def calculate_regression_response_optimizer(
    manifest: dict[str, Any],
    *,
    goal: Literal["maximize", "minimize", "target", "range"],
    lower: float | None,
    target: float | None,
    upper: float | None,
    numeric_bounds: dict[str, tuple[float, float]],
    fixed_categorical_levels: dict[str, str],
    linear_constraints: list[dict[str, Any]],
    random_seed: int,
    random_candidate_count: int,
    multi_start_count: int,
    max_iterations: int,
    max_evaluations: int,
    profile_point_count: int = 41,
) -> dict[str, object]:
    predictors = _predictors(manifest)
    domains = _training_domains(manifest)
    coefficients = _coefficients(manifest)
    specification = _model_specification(manifest)
    _validate_goal(goal, lower, target, upper)
    if not 1 <= profile_point_count <= MAX_PROFILE_POINTS:
        raise RegressionResponseOptimizerError("regression_optimizer_profile_count_invalid")
    if not 32 <= random_candidate_count <= 100_000:
        raise RegressionResponseOptimizerError("regression_optimizer_search_budget_invalid")
    if not 1 <= multi_start_count <= 64 or not 1 <= max_iterations <= 5_000:
        raise RegressionResponseOptimizerError("regression_optimizer_search_budget_invalid")
    if max_evaluations < random_candidate_count or max_evaluations > 250_000:
        raise RegressionResponseOptimizerError("regression_optimizer_search_budget_invalid")

    numeric_predictors = [item for item in predictors if item["kind"] == "numeric"]
    categorical_predictors = [item for item in predictors if item["kind"] == "categorical"]
    bounds = _resolved_numeric_bounds(numeric_predictors, domains, numeric_bounds)
    categorical_combinations = _categorical_combinations(
        categorical_predictors,
        domains,
        fixed_categorical_levels,
    )
    constraints = _validated_constraints(
        linear_constraints, {item["column_id"] for item in numeric_predictors}
    )
    rng = np.random.default_rng(random_seed)
    evaluations = 0
    best_values: dict[str, float | str] | None = None
    best_prediction: float | None = None
    best_desirability = -1.0

    numeric_ids = [item["column_id"] for item in numeric_predictors]
    scipy_bounds = [bounds[column_id] for column_id in numeric_ids]

    def evaluate(vector: np.ndarray, categorical: dict[str, str]) -> tuple[float, float]:
        nonlocal evaluations
        if evaluations >= max_evaluations:
            raise _EvaluationBudgetReached
        evaluations += 1
        values: dict[str, float | str] = dict(categorical)
        for index, column_id in enumerate(numeric_ids):
            value = float(vector[index])
            domain = domains[column_id]
            if bool(domain.get("integer_only")):
                value = float(round(value))
            values[column_id] = value
        if not _constraints_satisfied(values, constraints):
            return float("nan"), -1.0
        prediction = _predict(specification, coefficients, values)
        desirability = _desirability(prediction, goal, lower, target, upper)
        nonlocal best_values, best_prediction, best_desirability
        if desirability > best_desirability:
            best_values = values
            best_prediction = prediction
            best_desirability = desirability
        return prediction, desirability

    exhausted = False
    local_starts_attempted = 0
    local_success_count = 0
    for categorical in categorical_combinations:
        if exhausted:
            break
        candidates = _candidate_vectors(rng, scipy_bounds, random_candidate_count)
        ranked: list[tuple[float, np.ndarray]] = []
        for candidate in candidates:
            try:
                _, desirability = evaluate(candidate, categorical)
            except _EvaluationBudgetReached:
                exhausted = True
                break
            if desirability >= 0.0:
                ranked.append((desirability, candidate))
        for _, start in sorted(ranked, key=lambda item: item[0], reverse=True)[:multi_start_count]:
            if exhausted:
                break
            local_starts_attempted += 1
            try:
                optimized = minimize(
                    lambda vector, categorical=categorical: -evaluate(
                        np.asarray(vector, dtype=float), categorical
                    )[1],
                    start,
                    method="SLSQP",
                    bounds=scipy_bounds,
                    constraints=_scipy_constraints(numeric_ids, constraints),
                    options={"maxiter": max_iterations, "ftol": 1e-12, "disp": False},
                )
                if bool(optimized.success):
                    local_success_count += 1
                evaluate(np.asarray(optimized.x, dtype=float), categorical)
            except _EvaluationBudgetReached:
                exhausted = True
                break

    if best_values is None or best_prediction is None:
        raise RegressionResponseOptimizerError("regression_optimizer_no_feasible_point")
    profiles = _profiles(
        specification=specification,
        coefficients=coefficients,
        predictors=predictors,
        domains=domains,
        bounds=bounds,
        optimum=best_values,
        goal=goal,
        lower=lower,
        target=target,
        upper=upper,
        point_count=profile_point_count,
    )
    return {
        "schema_version": REGRESSION_RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION,
        "summary_type": "regression_response_optimizer",
        "method": "bounded_seeded_candidates_plus_slsqp_multistart",
        "goal": {
            "kind": goal,
            "lower": lower,
            "target": target,
            "upper": upper,
            "scale": "response_units",
        },
        "recommendation": {
            "predictor_settings": best_values,
            "predicted_response": best_prediction,
            "individual_desirability": best_desirability,
            "overall_desirability": best_desirability,
            "within_training_domain": True,
            "all_constraints_satisfied": _constraints_satisfied(best_values, constraints),
        },
        "factor_region": {
            "training_domains": list(domains.values()),
            "search_bounds": [
                {"column_id": column_id, "lower": value[0], "upper": value[1]}
                for column_id, value in bounds.items()
            ],
            "fixed_categorical_levels": fixed_categorical_levels,
            "categorical_combination_count": len(categorical_combinations),
            "linear_constraints": constraints,
        },
        "profiles": profiles,
        "search": {
            "random_seed": random_seed,
            "random_candidate_count": random_candidate_count,
            "multi_start_count": multi_start_count,
            "max_iterations": max_iterations,
            "max_evaluations": max_evaluations,
            "evaluation_count": evaluations,
            "local_starts_attempted": local_starts_attempted,
            "local_success_count": local_success_count,
            "termination_reason": "evaluation_budget" if exhausted else "search_completed",
            "global_optimum_guaranteed": False,
        },
        "warnings": [
            "regression_optimizer_global_optimum_not_guaranteed",
            "regression_optimizer_confirmation_experiment_required",
            "regression_optimizer_associational_model_not_causal",
            "regression_optimizer_profiles_are_conditional_slices",
        ],
    }


class _EvaluationBudgetReached(RuntimeError):
    pass


def _predictors(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw = manifest.get("predictors")
    if not isinstance(raw, list) or not raw:
        raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    domains = _training_domains(manifest)
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("column_id"), str):
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        column_id = str(item["column_id"])
        domain = domains.get(column_id)
        if domain is None or domain.get("kind") not in {"numeric", "categorical"}:
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        result.append(
            {
                "column_id": column_id,
                "display_name": str(item.get("display_name", column_id)),
                "kind": domain["kind"],
            }
        )
    return result


def _training_domains(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = manifest.get("training_domain")
    raw = payload.get("predictors") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        raise RegressionResponseOptimizerError("regression_optimizer_training_domain_missing")
    domains: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("column_id"), str):
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        domains[str(item["column_id"])] = dict(item)
    return domains


def _coefficients(manifest: dict[str, Any]) -> list[float]:
    raw = manifest.get("coefficients")
    if not isinstance(raw, list) or not raw:
        raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    coefficients: list[float] = []
    for item in raw:
        value = item.get("estimate") if isinstance(item, dict) else None
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not isfinite(float(value))
        ):
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        coefficients.append(float(value))
    return coefficients


def _model_specification(manifest: dict[str, Any]) -> dict[str, Any]:
    specification = manifest.get("model_specification")
    if not isinstance(specification, dict) or specification.get("intercept") is not True:
        raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    if not isinstance(specification.get("terms"), list):
        raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    return specification


def _resolved_numeric_bounds(
    predictors: list[dict[str, Any]],
    domains: dict[str, dict[str, Any]],
    requested: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    known = {item["column_id"] for item in predictors}
    if set(requested) - known:
        raise RegressionResponseOptimizerError("regression_optimizer_factor_bound_unknown")
    bounds: dict[str, tuple[float, float]] = {}
    for predictor in predictors:
        column_id = predictor["column_id"]
        domain = domains[column_id]
        training_low = domain.get("minimum")
        training_high = domain.get("maximum")
        if not isinstance(training_low, int | float) or not isinstance(training_high, int | float):
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        lower, upper = requested.get(column_id, (float(training_low), float(training_high)))
        if not all(isfinite(value) for value in (lower, upper)) or not (
            float(training_low) <= lower < upper <= float(training_high)
        ):
            raise RegressionResponseOptimizerError("regression_optimizer_factor_bound_invalid")
        bounds[column_id] = (float(lower), float(upper))
    return bounds


def _categorical_combinations(
    predictors: list[dict[str, Any]],
    domains: dict[str, dict[str, Any]],
    fixed: dict[str, str],
) -> list[dict[str, str]]:
    known = {item["column_id"] for item in predictors}
    if set(fixed) - known:
        raise RegressionResponseOptimizerError("regression_optimizer_categorical_factor_unknown")
    ids: list[str] = []
    level_sets: list[list[str]] = []
    for predictor in predictors:
        column_id = predictor["column_id"]
        raw_levels = domains[column_id].get("levels")
        if (
            not isinstance(raw_levels, list)
            or not raw_levels
            or not all(isinstance(level, str) for level in raw_levels)
        ):
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        requested = fixed.get(column_id)
        if requested is not None and requested not in raw_levels:
            raise RegressionResponseOptimizerError("regression_optimizer_unseen_categorical_level")
        ids.append(column_id)
        level_sets.append([requested] if requested is not None else list(raw_levels))
    count = int(np.prod([len(levels) for levels in level_sets])) if level_sets else 1
    if count > MAX_CATEGORICAL_COMBINATIONS:
        raise RegressionResponseOptimizerError("regression_optimizer_categorical_combination_limit")
    return [dict(zip(ids, values, strict=True)) for values in product(*level_sets)] if ids else [{}]


def _validated_constraints(
    constraints: list[dict[str, Any]],
    numeric_ids: set[str],
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    for item in constraints:
        coefficients = item.get("coefficients")
        relation = item.get("relation")
        bound = item.get("bound")
        if (
            not isinstance(item.get("name"), str)
            or not isinstance(coefficients, dict)
            or not coefficients
            or set(coefficients) - numeric_ids
            or relation not in {"less_than_or_equal", "greater_than_or_equal"}
            or isinstance(bound, bool)
            or not isinstance(bound, int | float)
        ):
            raise RegressionResponseOptimizerError("regression_optimizer_linear_constraint_invalid")
        normalized = {str(key): float(value) for key, value in coefficients.items()}
        if not all(isfinite(value) for value in normalized.values()) or not isfinite(float(bound)):
            raise RegressionResponseOptimizerError("regression_optimizer_linear_constraint_invalid")
        validated.append(
            {
                "name": str(item["name"]),
                "coefficients": normalized,
                "relation": relation,
                "bound": float(bound),
            }
        )
    return validated


def _candidate_vectors(
    rng: np.random.Generator,
    bounds: list[tuple[float, float]],
    count: int,
) -> list[np.ndarray]:
    if not bounds:
        return [np.asarray([], dtype=float)]
    candidates = [np.asarray([(low + high) / 2.0 for low, high in bounds], dtype=float)]
    for corner in product(*[(low, high) for low, high in bounds]):
        candidates.append(np.asarray(corner, dtype=float))
        if len(candidates) >= count:
            return candidates
    remaining = count - len(candidates)
    if remaining > 0:
        samples = rng.random((remaining, len(bounds)))
        low = np.asarray([item[0] for item in bounds], dtype=float)
        span = np.asarray([item[1] - item[0] for item in bounds], dtype=float)
        candidates.extend(np.asarray(row, dtype=float) for row in low + samples * span)
    return candidates


def _constraints_satisfied(
    values: dict[str, float | str], constraints: list[dict[str, Any]]
) -> bool:
    for item in constraints:
        lhs = sum(
            float(coefficient) * float(values[column_id])
            for column_id, coefficient in item["coefficients"].items()
        )
        if item["relation"] == "less_than_or_equal" and lhs > float(item["bound"]) + 1e-8:
            return False
        if item["relation"] == "greater_than_or_equal" and lhs < float(item["bound"]) - 1e-8:
            return False
    return True


def _scipy_constraints(
    numeric_ids: list[str], constraints: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    positions = {column_id: index for index, column_id in enumerate(numeric_ids)}
    result: list[dict[str, Any]] = []
    for item in constraints:
        coefficients = item["coefficients"]
        bound = float(item["bound"])
        if item["relation"] == "less_than_or_equal":
            result.append(
                {
                    "type": "ineq",
                    "fun": lambda vector, c=coefficients, b=bound: b
                    - sum(
                        float(value) * float(vector[positions[column_id]])
                        for column_id, value in c.items()
                    ),
                }
            )
        else:
            result.append(
                {
                    "type": "ineq",
                    "fun": lambda vector, c=coefficients, b=bound: sum(
                        float(value) * float(vector[positions[column_id]])
                        for column_id, value in c.items()
                    )
                    - b,
                }
            )
    return result


def _predict(
    specification: dict[str, Any],
    coefficients: list[float],
    values: dict[str, float | str],
) -> float:
    vector = [1.0]
    for term in specification["terms"]:
        if not isinstance(term, dict):
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
        kind = term.get("kind")
        source_ids = term.get("source_column_ids")
        if kind == "numeric_main_effect":
            vector.append(float(values[_one_source_id(source_ids)]))
        elif kind == "numeric_quadratic":
            value = float(values[_one_source_id(source_ids)])
            vector.append(value * value)
        elif kind == "numeric_interaction":
            if not isinstance(source_ids, list) or len(source_ids) != 2:
                raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
            vector.append(float(values[str(source_ids[0])]) * float(values[str(source_ids[1])]))
        elif kind == "categorical_main_effect":
            column_id = term.get("column_id")
            levels = term.get("levels")
            if not isinstance(column_id, str) or not isinstance(levels, list) or len(levels) < 2:
                raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
            category_value = values[column_id]
            vector.extend(1.0 if category_value == level else 0.0 for level in levels[1:])
        else:
            raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    if len(vector) != len(coefficients):
        raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    prediction = float(sum(left * right for left, right in zip(vector, coefficients, strict=True)))
    if not isfinite(prediction):
        raise RegressionResponseOptimizerError("regression_optimizer_prediction_not_finite")
    return prediction


def _one_source_id(value: object) -> str:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], str):
        raise RegressionResponseOptimizerError("regression_optimizer_manifest_invalid")
    return value[0]


def _desirability(
    value: float,
    goal: str,
    lower: float | None,
    target: float | None,
    upper: float | None,
) -> float:
    if goal == "maximize":
        assert lower is not None and target is not None
        return (
            0.0
            if value <= lower
            else 1.0
            if value >= target
            else (value - lower) / (target - lower)
        )
    if goal == "minimize":
        assert target is not None and upper is not None
        return (
            1.0
            if value <= target
            else 0.0
            if value >= upper
            else (upper - value) / (upper - target)
        )
    if goal == "target":
        assert lower is not None and target is not None and upper is not None
        if value <= lower or value >= upper:
            return 0.0
        return (
            (value - lower) / (target - lower)
            if value < target
            else (upper - value) / (upper - target)
        )
    assert lower is not None and upper is not None
    return 1.0 if lower <= value <= upper else 0.0


def _validate_goal(
    goal: str, lower: float | None, target: float | None, upper: float | None
) -> None:
    values = [value for value in (lower, target, upper) if value is not None]
    if not all(isfinite(value) for value in values):
        raise RegressionResponseOptimizerError("regression_optimizer_goal_invalid")
    valid = (
        goal == "maximize"
        and lower is not None
        and target is not None
        and lower < target
        and upper is None
        or goal == "minimize"
        and target is not None
        and upper is not None
        and target < upper
        and lower is None
        or goal == "target"
        and lower is not None
        and target is not None
        and upper is not None
        and lower < target < upper
        or goal == "range"
        and lower is not None
        and upper is not None
        and lower < upper
        and target is None
    )
    if not valid:
        raise RegressionResponseOptimizerError("regression_optimizer_goal_invalid")


def _profiles(
    *,
    specification: dict[str, Any],
    coefficients: list[float],
    predictors: list[dict[str, Any]],
    domains: dict[str, dict[str, Any]],
    bounds: dict[str, tuple[float, float]],
    optimum: dict[str, float | str],
    goal: str,
    lower: float | None,
    target: float | None,
    upper: float | None,
    point_count: int,
) -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []
    for predictor in predictors:
        column_id = predictor["column_id"]
        points: list[dict[str, object]] = []
        if predictor["kind"] == "numeric":
            low, high = bounds[column_id]
            values = np.linspace(low, high, point_count)
            if bool(domains[column_id].get("integer_only")):
                values = np.unique(np.rint(values))
            for raw_value in values:
                candidate = dict(optimum)
                candidate[column_id] = float(raw_value)
                prediction = _predict(specification, coefficients, candidate)
                points.append(
                    {
                        "predictor_value": float(raw_value),
                        "predicted_response": prediction,
                        "desirability": _desirability(prediction, goal, lower, target, upper),
                    }
                )
        else:
            for level in domains[column_id]["levels"]:
                candidate = dict(optimum)
                candidate[column_id] = str(level)
                prediction = _predict(specification, coefficients, candidate)
                points.append(
                    {
                        "predictor_value": str(level),
                        "predicted_response": prediction,
                        "desirability": _desirability(prediction, goal, lower, target, upper),
                    }
                )
        profiles.append(
            {
                "column_id": column_id,
                "display_name": predictor["display_name"],
                "kind": predictor["kind"],
                "fixed_at": optimum[column_id],
                "conditional_on_other_predictors_at_optimum": True,
                "points": points,
            }
        )
    return profiles
