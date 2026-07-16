from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import exp, isfinite, log
from time import perf_counter
from typing import Any, Final, Literal, TypedDict

import numpy as np
from scipy.optimize import minimize  # type: ignore[import-untyped]

RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION: Final[Literal[2]] = 2
MIN_OPTIMIZER_OBJECTIVES = 1
MAX_OPTIMIZER_OBJECTIVES = 8
MAX_OPTIMIZER_FACTORS = 5
CONSTRAINT_TOLERANCE = 1e-8


class ResponseOptimizerError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OptimizerFactor:
    name: str
    low: float
    high: float
    alpha: float
    unit: str | None = None


@dataclass(frozen=True)
class OptimizerTerm:
    kind: Literal["intercept", "main_effect", "interaction", "quadratic"]
    factor_names: tuple[str, ...]
    coefficient: float


@dataclass(frozen=True)
class OptimizerModel:
    analysis_id: str
    response_name: str
    response_unit: str | None
    factors: tuple[OptimizerFactor, ...]
    terms: tuple[OptimizerTerm, ...]
    source_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class OptimizerObjective:
    model: OptimizerModel
    goal: Literal["maximize", "minimize", "target", "range"]
    lower: float | None
    target: float | None
    upper: float | None
    lower_weight: float
    upper_weight: float
    importance: float


@dataclass(frozen=True)
class OptimizerFactorBound:
    factor_name: str
    lower: float
    upper: float


@dataclass(frozen=True)
class OptimizerLinearConstraint:
    name: str
    coefficients: dict[str, float]
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: float


@dataclass(frozen=True)
class OptimizerSearchOptions:
    random_seed: int
    random_candidate_count: int
    multi_start_count: int
    max_iterations: int
    max_evaluations: int
    time_budget_ms: int


@dataclass(frozen=True)
class OptimizerEligibilityIssue:
    source_analysis_id: str | None
    code: str
    severity: Literal["blocking", "acknowledgment_required", "informational"]
    source_warning_code: str | None = None


@dataclass(frozen=True)
class OptimizerSourceEligibility:
    eligible: bool
    acknowledgment_required: bool
    issues: tuple[OptimizerEligibilityIssue, ...]
    acknowledged_source_warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Evaluation:
    actual: tuple[float, ...]
    predicted: tuple[float, ...]
    individual: tuple[float, ...]
    composite: float


class _ConstraintResult(TypedDict):
    name: str
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    lhs: float
    bound: float
    slack: float
    satisfied: bool


class _BudgetReached(RuntimeError):
    def __init__(self, reason: Literal["evaluation_budget", "time_budget"]) -> None:
        super().__init__(reason)
        self.reason = reason


class _EvaluationState:
    def __init__(
        self,
        objectives: tuple[OptimizerObjective, ...],
        factor_names: tuple[str, ...],
        constraints: tuple[OptimizerLinearConstraint, ...],
        options: OptimizerSearchOptions,
    ) -> None:
        self.objectives = objectives
        self.factor_names = factor_names
        self.constraints = constraints
        self.options = options
        self.started = perf_counter()
        self.deadline = self.started + options.time_budget_ms / 1000.0
        self.evaluation_count = 0
        self.best: _Evaluation | None = None

    def evaluate(self, actual: np.ndarray) -> _Evaluation:
        if self.evaluation_count >= self.options.max_evaluations:
            raise _BudgetReached("evaluation_budget")
        if perf_counter() >= self.deadline:
            raise _BudgetReached("time_budget")
        self.evaluation_count += 1
        actual_tuple = tuple(float(value) for value in actual)
        actual_by_name = dict(zip(self.factor_names, actual_tuple, strict=True))
        predicted = tuple(
            _predict(objective.model, actual_by_name) for objective in self.objectives
        )
        individual = tuple(
            individual_desirability(value, objective)
            for value, objective in zip(predicted, self.objectives, strict=True)
        )
        composite = composite_desirability(individual, self.objectives)
        evaluation = _Evaluation(actual_tuple, predicted, individual, composite)
        if _constraints_satisfied(actual_by_name, self.constraints) and (
            self.best is None or evaluation.composite > self.best.composite
        ):
            self.best = evaluation
        return evaluation


def individual_desirability(value: float, objective: OptimizerObjective) -> float:
    if not isfinite(value):
        raise ResponseOptimizerError("response_optimizer_prediction_not_finite")
    lower = objective.lower
    target = objective.target
    upper = objective.upper
    if objective.goal == "maximize":
        assert lower is not None and target is not None
        if value <= lower:
            return 0.0
        if value >= target:
            return 1.0
        return float(((value - lower) / (target - lower)) ** objective.lower_weight)
    if objective.goal == "minimize":
        assert target is not None and upper is not None
        if value <= target:
            return 1.0
        if value >= upper:
            return 0.0
        return float(((upper - value) / (upper - target)) ** objective.upper_weight)
    if objective.goal == "target":
        assert lower is not None and target is not None and upper is not None
        if value <= lower or value >= upper:
            return 0.0
        if value == target:
            return 1.0
        if value < target:
            return float(((value - lower) / (target - lower)) ** objective.lower_weight)
        return float(((upper - value) / (upper - target)) ** objective.upper_weight)
    assert lower is not None and upper is not None
    return 1.0 if lower <= value <= upper else 0.0


def composite_desirability(
    individual: tuple[float, ...], objectives: tuple[OptimizerObjective, ...]
) -> float:
    if any(value <= 0.0 for value in individual):
        return 0.0
    importance_total = sum(objective.importance for objective in objectives)
    return float(
        exp(
            sum(
                objective.importance * log(value)
                for value, objective in zip(individual, objectives, strict=True)
            )
            / importance_total
        )
    )


def calculate_response_optimizer(
    objectives: list[OptimizerObjective],
    *,
    factor_bounds: list[OptimizerFactorBound],
    linear_constraints: list[OptimizerLinearConstraint],
    search_options: OptimizerSearchOptions,
    source_model_eligibility: OptimizerSourceEligibility | None = None,
) -> dict[str, object]:
    objective_tuple = tuple(objectives)
    constraint_tuple = tuple(linear_constraints)
    factors = _validate_inputs(
        objective_tuple,
        factor_bounds,
        constraint_tuple,
        search_options,
    )
    factor_names = tuple(factor.name for factor in factors)
    eligibility = source_model_eligibility or OptimizerSourceEligibility(
        eligible=True,
        acknowledgment_required=False,
        issues=(),
    )
    search_bounds = _search_bounds(factors, factor_bounds)
    scipy_bounds = [(bound.lower, bound.upper) for bound in search_bounds]
    state = _EvaluationState(objective_tuple, factor_names, constraint_tuple, search_options)
    candidates = _initial_candidates(
        factors,
        search_bounds,
        constraint_tuple,
        search_options,
    )
    evaluated: list[_Evaluation] = []
    termination_reason: Literal["search_completed", "evaluation_budget", "time_budget"] = (
        "search_completed"
    )
    for candidate in candidates:
        try:
            evaluation = state.evaluate(candidate)
        except _BudgetReached as exc:
            termination_reason = exc.reason
            break
        actual_by_name = dict(zip(factor_names, evaluation.actual, strict=True))
        if _constraints_satisfied(actual_by_name, constraint_tuple):
            evaluated.append(evaluation)
    if not evaluated:
        feasible = _find_feasible_candidate(
            search_bounds,
            factor_names,
            constraint_tuple,
            search_options.max_iterations,
        )
        if feasible is None:
            raise ResponseOptimizerError("response_optimizer_no_feasible_point")
        try:
            evaluated.append(state.evaluate(feasible))
        except _BudgetReached as exc:
            raise ResponseOptimizerError(
                f"response_optimizer_{exc.reason}_before_feasible"
            ) from exc

    local_starts_attempted = 0
    local_iterations = 0
    local_success_count = 0
    scipy_constraints = _scipy_constraints(factor_names, constraint_tuple)
    starts = sorted(evaluated, key=lambda item: item.composite, reverse=True)[
        : search_options.multi_start_count
    ]
    if termination_reason == "search_completed":
        for start in starts:
            local_starts_attempted += 1
            try:
                optimized = minimize(
                    lambda values: -state.evaluate(np.asarray(values, dtype=float)).composite,
                    np.asarray(start.actual, dtype=float),
                    method="SLSQP",
                    bounds=scipy_bounds,
                    constraints=scipy_constraints,
                    options={
                        "maxiter": search_options.max_iterations,
                        "ftol": 1e-12,
                        "disp": False,
                    },
                )
            except _BudgetReached as exc:
                termination_reason = exc.reason
                break
            local_iterations += int(optimized.nit)
            if bool(optimized.success):
                local_success_count += 1
            optimized_values = np.asarray(optimized.x, dtype=float)
            optimized_by_name = dict(zip(factor_names, optimized_values, strict=True))
            if _constraints_satisfied(optimized_by_name, constraint_tuple):
                try:
                    state.evaluate(optimized_values)
                except _BudgetReached as exc:
                    termination_reason = exc.reason
                    break

    best = state.best
    if best is None:
        raise ResponseOptimizerError("response_optimizer_no_feasible_point")
    actual_by_name = dict(zip(factor_names, best.actual, strict=True))
    first_model = objective_tuple[0].model
    coded_by_name = {
        factor.name: _actual_to_coded(factor, actual_by_name[factor.name])
        for factor in first_model.factors
    }
    constraint_results = _constraint_results(actual_by_name, constraint_tuple)
    elapsed_ms = (perf_counter() - state.started) * 1000.0
    warnings = [
        "response_optimizer_global_optimum_not_guaranteed",
        "response_optimizer_confirmation_run_required",
        "response_optimizer_uses_point_predictions_without_uncertainty",
        "response_optimizer_model_adequacy_must_be_reviewed",
    ]
    if any(objective.model.source_warnings for objective in objective_tuple):
        warnings.append("response_optimizer_source_model_has_warnings")
    if termination_reason != "search_completed":
        warnings.append(f"response_optimizer_{termination_reason}_reached")
    if best.composite <= 0.0:
        warnings.append("response_optimizer_no_jointly_desirable_solution")
    if any(
        abs(actual_by_name[bound.factor_name] - bound.lower) <= CONSTRAINT_TOLERANCE
        or abs(actual_by_name[bound.factor_name] - bound.upper) <= CONSTRAINT_TOLERANCE
        for bound in search_bounds
    ):
        warnings.append("response_optimizer_recommendation_on_factor_bound")
    return {
        "schema_version": RESPONSE_OPTIMIZER_RESULT_SCHEMA_VERSION,
        "summary_type": "response_optimizer",
        "method": "derringer_suich_bounded_multistart_slsqp",
        "model_policy": {
            "individual_desirability": "derringer_suich",
            "composite_desirability": "importance_weighted_geometric_mean",
            "bounded_to_declared_design_region": True,
            "linear_constraints_supported": True,
            "global_optimum_guaranteed": False,
            "point_predictions_only": True,
        },
        "factor_region": {
            "design_bounds": [
                {
                    "factor_name": factor.name,
                    "lower": factor.low,
                    "upper": factor.high,
                    "unit": factor.unit,
                }
                for factor in factors
            ],
            "search_bounds": [
                {
                    "factor_name": bound.factor_name,
                    "lower": bound.lower,
                    "upper": bound.upper,
                }
                for bound in search_bounds
            ],
            "linear_constraints": [
                {
                    "name": constraint.name,
                    "coefficients": constraint.coefficients,
                    "relation": constraint.relation,
                    "bound": constraint.bound,
                }
                for constraint in constraint_tuple
            ],
        },
        "objectives": [
            {
                "source_analysis_id": objective.model.analysis_id,
                "response_name": objective.model.response_name,
                "response_unit": objective.model.response_unit,
                "goal": objective.goal,
                "lower": objective.lower,
                "target": objective.target,
                "upper": objective.upper,
                "lower_weight": objective.lower_weight,
                "upper_weight": objective.upper_weight,
                "importance": objective.importance,
            }
            for objective in objective_tuple
        ],
        "recommendation": {
            "actual_coordinates": actual_by_name,
            "coded_coordinates": coded_by_name,
            "composite_desirability": best.composite,
            "objectives": [
                {
                    "source_analysis_id": objective.model.analysis_id,
                    "response_name": objective.model.response_name,
                    "goal": objective.goal,
                    "predicted_response": predicted,
                    "individual_desirability": desirability,
                    "importance": objective.importance,
                }
                for objective, predicted, desirability in zip(
                    objective_tuple,
                    best.predicted,
                    best.individual,
                    strict=True,
                )
            ],
            "constraints": constraint_results,
            "all_constraints_satisfied": all(
                bool(result["satisfied"]) for result in constraint_results
            ),
        },
        "search": {
            "algorithm": "seeded_candidates_plus_slsqp_multistart",
            "random_seed": search_options.random_seed,
            "random_candidate_count": search_options.random_candidate_count,
            "multi_start_count": search_options.multi_start_count,
            "max_iterations": search_options.max_iterations,
            "max_evaluations": search_options.max_evaluations,
            "time_budget_ms": search_options.time_budget_ms,
            "evaluation_count": state.evaluation_count,
            "local_starts_attempted": local_starts_attempted,
            "local_success_count": local_success_count,
            "local_iterations": local_iterations,
            "elapsed_ms": elapsed_ms,
            "termination_reason": termination_reason,
            "global_optimum_guaranteed": False,
        },
        "source_model_eligibility": {
            "eligible": eligibility.eligible,
            "acknowledgment_required": eligibility.acknowledgment_required,
            "issues": [
                {
                    "source_analysis_id": issue.source_analysis_id,
                    "code": issue.code,
                    "severity": issue.severity,
                    "source_warning_code": issue.source_warning_code,
                }
                for issue in eligibility.issues
            ],
            "acknowledged_source_warning_codes": list(
                eligibility.acknowledged_source_warning_codes
            ),
        },
        "acknowledged_source_warning_codes": list(eligibility.acknowledged_source_warning_codes),
        "warnings": warnings,
    }


def _validate_inputs(
    objectives: tuple[OptimizerObjective, ...],
    factor_bounds: list[OptimizerFactorBound],
    constraints: tuple[OptimizerLinearConstraint, ...],
    options: OptimizerSearchOptions,
) -> tuple[OptimizerFactor, ...]:
    if not MIN_OPTIMIZER_OBJECTIVES <= len(objectives) <= MAX_OPTIMIZER_OBJECTIVES:
        raise ResponseOptimizerError("response_optimizer_objective_count_invalid")
    factors = objectives[0].model.factors
    if not 1 <= len(factors) <= MAX_OPTIMIZER_FACTORS:
        raise ResponseOptimizerError("response_optimizer_factor_count_invalid")
    expected_names = tuple(factor.name for factor in factors)
    if len(set(expected_names)) != len(expected_names):
        raise ResponseOptimizerError("response_optimizer_factor_space_invalid")
    for factor in factors:
        if (
            not factor.name.strip()
            or not isfinite(factor.low)
            or not isfinite(factor.high)
            or factor.low >= factor.high
            or not isfinite(factor.alpha)
            or factor.alpha < 1.0
        ):
            raise ResponseOptimizerError("response_optimizer_factor_space_invalid")
    seen_analyses: set[str] = set()
    for objective in objectives:
        if objective.model.analysis_id in seen_analyses:
            raise ResponseOptimizerError("response_optimizer_source_analysis_duplicate")
        seen_analyses.add(objective.model.analysis_id)
        if tuple(factor.name for factor in objective.model.factors) != expected_names or any(
            source.low != expected.low
            or source.high != expected.high
            or source.alpha != expected.alpha
            for source, expected in zip(objective.model.factors, factors, strict=True)
        ):
            raise ResponseOptimizerError("response_optimizer_factor_space_mismatch")
        _validate_objective(objective)
        _validate_model(objective.model, expected_names)
    names = set(expected_names)
    if len({bound.factor_name for bound in factor_bounds}) != len(factor_bounds):
        raise ResponseOptimizerError("response_optimizer_factor_bound_duplicate")
    if any(bound.factor_name not in names for bound in factor_bounds):
        raise ResponseOptimizerError("response_optimizer_factor_bound_unknown")
    for constraint in constraints:
        if (
            not constraint.name.strip()
            or constraint.relation not in {"less_than_or_equal", "greater_than_or_equal"}
            or not isfinite(constraint.bound)
            or not constraint.coefficients
            or any(name not in names for name in constraint.coefficients)
            or any(not isfinite(value) for value in constraint.coefficients.values())
            or all(abs(value) <= np.finfo(float).eps for value in constraint.coefficients.values())
        ):
            raise ResponseOptimizerError("response_optimizer_linear_constraint_invalid")
    if (
        options.random_seed < 0
        or not 0 <= options.random_candidate_count <= 4096
        or not 1 <= options.multi_start_count <= 32
        or not 1 <= options.max_iterations <= 500
        or not 32 <= options.max_evaluations <= 100_000
        or not 100 <= options.time_budget_ms <= 30_000
    ):
        raise ResponseOptimizerError("response_optimizer_search_budget_invalid")
    return factors


def _validate_objective(objective: OptimizerObjective) -> None:
    values = (objective.lower, objective.target, objective.upper)
    if any(value is not None and not isfinite(value) for value in values) or any(
        not isfinite(value) or value <= 0
        for value in (objective.lower_weight, objective.upper_weight, objective.importance)
    ):
        raise ResponseOptimizerError("response_optimizer_objective_invalid")
    if objective.goal == "maximize":
        valid = (
            objective.lower is not None
            and objective.target is not None
            and objective.upper is None
            and objective.lower < objective.target
        )
    elif objective.goal == "minimize":
        valid = (
            objective.lower is None
            and objective.target is not None
            and objective.upper is not None
            and objective.target < objective.upper
        )
    elif objective.goal == "target":
        valid = (
            objective.lower is not None
            and objective.target is not None
            and objective.upper is not None
            and objective.lower < objective.target < objective.upper
        )
    else:
        valid = (
            objective.lower is not None
            and objective.target is None
            and objective.upper is not None
            and objective.lower < objective.upper
        )
    if not valid:
        raise ResponseOptimizerError("response_optimizer_objective_thresholds_invalid")


def _validate_model(model: OptimizerModel, factor_names: tuple[str, ...]) -> None:
    if not model.analysis_id or not model.response_name.strip() or not model.terms:
        raise ResponseOptimizerError("response_optimizer_source_model_invalid")
    intercept_count = sum(term.kind == "intercept" for term in model.terms)
    if intercept_count != 1:
        raise ResponseOptimizerError("response_optimizer_source_model_invalid")
    names = set(factor_names)
    for term in model.terms:
        expected_count = {
            "intercept": 0,
            "main_effect": 1,
            "interaction": 2,
            "quadratic": 1,
        }[term.kind]
        if (
            len(term.factor_names) != expected_count
            or any(name not in names for name in term.factor_names)
            or not isfinite(term.coefficient)
        ):
            raise ResponseOptimizerError("response_optimizer_source_model_invalid")


def _search_bounds(
    factors: tuple[OptimizerFactor, ...], requested: list[OptimizerFactorBound]
) -> tuple[OptimizerFactorBound, ...]:
    by_name = {bound.factor_name: bound for bound in requested}
    resolved = []
    for factor in factors:
        bound = by_name.get(
            factor.name,
            OptimizerFactorBound(factor.name, factor.low, factor.high),
        )
        if (
            not isfinite(bound.lower)
            or not isfinite(bound.upper)
            or bound.lower >= bound.upper
            or bound.lower < factor.low - CONSTRAINT_TOLERANCE
            or bound.upper > factor.high + CONSTRAINT_TOLERANCE
        ):
            raise ResponseOptimizerError("response_optimizer_factor_bound_invalid")
        resolved.append(bound)
    return tuple(resolved)


def _initial_candidates(
    factors: tuple[OptimizerFactor, ...],
    bounds: tuple[OptimizerFactorBound, ...],
    constraints: tuple[OptimizerLinearConstraint, ...],
    options: OptimizerSearchOptions,
) -> list[np.ndarray]:
    candidates = [np.asarray([(bound.lower + bound.upper) / 2.0 for bound in bounds], dtype=float)]
    candidates.extend(
        np.asarray(values, dtype=float)
        for values in product(*((bound.lower, bound.upper) for bound in bounds))
    )
    generator = np.random.default_rng(options.random_seed)
    if options.random_candidate_count:
        lows = np.asarray([bound.lower for bound in bounds], dtype=float)
        highs = np.asarray([bound.upper for bound in bounds], dtype=float)
        candidates.extend(
            generator.uniform(lows, highs) for _ in range(options.random_candidate_count)
        )
    names = tuple(factor.name for factor in factors)
    deduplicated: list[np.ndarray] = []
    seen: set[tuple[float, ...]] = set()
    for candidate in candidates:
        key = tuple(float(value) for value in candidate)
        if key in seen:
            continue
        seen.add(key)
        actual = dict(zip(names, key, strict=True))
        if _constraints_satisfied(actual, constraints):
            deduplicated.append(candidate)
    return deduplicated


def _find_feasible_candidate(
    bounds: tuple[OptimizerFactorBound, ...],
    factor_names: tuple[str, ...],
    constraints: tuple[OptimizerLinearConstraint, ...],
    max_iterations: int,
) -> np.ndarray | None:
    center = np.asarray([(bound.lower + bound.upper) / 2.0 for bound in bounds], dtype=float)
    optimized = minimize(
        lambda values: _constraint_violation(
            dict(zip(factor_names, (float(value) for value in values), strict=True)),
            constraints,
        ),
        center,
        method="SLSQP",
        bounds=[(bound.lower, bound.upper) for bound in bounds],
        constraints=_scipy_constraints(factor_names, constraints),
        options={"maxiter": max_iterations, "ftol": 1e-12, "disp": False},
    )
    candidate = np.asarray(optimized.x, dtype=float)
    actual = dict(zip(factor_names, (float(value) for value in candidate), strict=True))
    return candidate if _constraints_satisfied(actual, constraints) else None


def _scipy_constraints(
    factor_names: tuple[str, ...], constraints: tuple[OptimizerLinearConstraint, ...]
) -> list[dict[str, Any]]:
    indexes = {name: index for index, name in enumerate(factor_names)}
    result: list[dict[str, Any]] = []
    for constraint in constraints:
        coefficients = np.zeros(len(factor_names), dtype=float)
        for name, value in constraint.coefficients.items():
            coefficients[indexes[name]] = value
        if constraint.relation == "less_than_or_equal":
            result.append(
                {
                    "type": "ineq",
                    "fun": lambda values, c=coefficients, b=constraint.bound: float(
                        b - np.dot(c, values)
                    ),
                }
            )
        else:
            result.append(
                {
                    "type": "ineq",
                    "fun": lambda values, c=coefficients, b=constraint.bound: float(
                        np.dot(c, values) - b
                    ),
                }
            )
    return result


def _constraints_satisfied(
    actual: dict[str, float], constraints: tuple[OptimizerLinearConstraint, ...]
) -> bool:
    return all(bool(result["satisfied"]) for result in _constraint_results(actual, constraints))


def _constraint_results(
    actual: dict[str, float], constraints: tuple[OptimizerLinearConstraint, ...]
) -> list[_ConstraintResult]:
    results: list[_ConstraintResult] = []
    for constraint in constraints:
        lhs = sum(
            actual[name] * coefficient for name, coefficient in constraint.coefficients.items()
        )
        if constraint.relation == "less_than_or_equal":
            slack = constraint.bound - lhs
        else:
            slack = lhs - constraint.bound
        results.append(
            {
                "name": constraint.name,
                "relation": constraint.relation,
                "lhs": lhs,
                "bound": constraint.bound,
                "slack": slack,
                "satisfied": slack >= -CONSTRAINT_TOLERANCE,
            }
        )
    return results


def _constraint_violation(
    actual: dict[str, float], constraints: tuple[OptimizerLinearConstraint, ...]
) -> float:
    return float(
        sum(max(0.0, -result["slack"]) ** 2 for result in _constraint_results(actual, constraints))
    )


def _predict(model: OptimizerModel, actual: dict[str, float]) -> float:
    coded = {factor.name: _actual_to_coded(factor, actual[factor.name]) for factor in model.factors}
    prediction = 0.0
    for term in model.terms:
        if term.kind == "intercept":
            value = 1.0
        elif term.kind == "main_effect":
            value = coded[term.factor_names[0]]
        elif term.kind == "interaction":
            value = coded[term.factor_names[0]] * coded[term.factor_names[1]]
        else:
            value = coded[term.factor_names[0]] ** 2
        prediction += term.coefficient * value
    if not isfinite(prediction):
        raise ResponseOptimizerError("response_optimizer_prediction_not_finite")
    return float(prediction)


def _actual_to_coded(factor: OptimizerFactor, actual: float) -> float:
    midpoint = (factor.low + factor.high) / 2.0
    half_range = (factor.high - factor.low) / 2.0
    return float(factor.alpha * (actual - midpoint) / half_range)
