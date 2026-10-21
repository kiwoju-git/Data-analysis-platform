"""Bounded acquisition search with executable discrete levels fixed during SLSQP."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import product
from math import isfinite, prod
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize  # type: ignore[import-untyped]

FloatArray = NDArray[np.float64]
Score = Callable[[FloatArray], FloatArray]
Consume = Callable[[int], object]
ENUMERATION_LIMIT = 256
SCORE_CHUNK_SIZE = 256


@dataclass(frozen=True)
class MixedSearchResult:
    normalized_coordinates: list[float]
    actual_coordinates: dict[str, float]
    acquisition: float
    metadata: dict[str, Any]


def search_mixed_acquisition(
    *,
    factors: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    score: Score,
    seed: int,
    pool_size: int,
    local_start_count: int,
    local_maxiter: int = 100,
    excluded_normalized: Sequence[Sequence[float]] = (),
    selected_normalized: Sequence[Sequence[float]] = (),
    duplicate_tolerance: float = 1e-6,
    min_batch_distance_normalized: float = 0.0,
    consume: Consume | None = None,
) -> MixedSearchResult:
    """Maximize a nonnegative score, charging every scored row to ``consume``.

    Constraints use the existing validated ``coefficients``/``relation`` format.
    The score receives normalized full coordinates and must not charge the same
    evaluations again. Global budget/time errors propagate; only local solver
    nonconvergence retains an already evaluated feasible candidate. The start
    count is a total per-call limit, never a per-discrete-assignment multiplier.
    """
    from app.statistics.bayesian_optimization import (
        BayesianOptimizationError,
        _candidate_pool_for_factors,
        _constraints_satisfied,
        _discrete_normalized_levels,
        _factor_domain,
        _novel,
        _to_actual,
        _validated_factors,
    )

    factors = _validated_factors(factors)
    integer_options = (
        (seed, 0, 2**32 - 1),
        (pool_size, 1, 4096),
        (local_start_count, 0, 16),
        (local_maxiter, 1, 500),
    )
    if any(
        isinstance(x, bool) or not isinstance(x, int) or not low <= x <= high
        for x, low, high in integer_options
    ) or not (
        isfinite(duplicate_tolerance)
        and 0 < duplicate_tolerance <= 0.1
        and isfinite(min_batch_distance_normalized)
        and min_batch_distance_normalized >= 0
    ):
        raise BayesianOptimizationError("bayesian_optimization_search_options_invalid")
    count = len(factors)
    domains = [_factor_domain(factor) for factor in factors]
    levels = [_discrete_normalized_levels(factor) for factor in factors]
    discrete = [i for i, values in enumerate(levels) if values is not None]
    continuous = [i for i, values in enumerate(levels) if values is None]
    level_indices = {i: {value: j for j, value in enumerate(levels[i] or ())} for i in discrete}
    actual_levels = {i: domains[i].levels() for i in discrete}
    assignment_count = prod(len(levels[i] or ()) for i in discrete)
    enumerate_all = bool(discrete) and assignment_count <= ENUMERATION_LIMIT
    excluded = _validated_points(excluded_normalized, count)
    selected = _validated_points(selected_normalized, count)
    visited: set[tuple[int, ...]] = set()
    evaluations = 0

    def charge(n: int) -> None:
        nonlocal evaluations
        if consume is not None:
            consume(n)
        evaluations += n

    def assignment(point: FloatArray) -> tuple[int, ...]:
        return tuple(level_indices[i][float(point[i])] for i in discrete)

    def canonical(point: FloatArray) -> tuple[FloatArray, dict[str, float]] | None:
        if point.shape != (count,) or not np.all(np.isfinite(point)):
            return None
        if np.any(point < 0) or np.any(point > 1):
            return None
        normalized = point.copy()
        actual: dict[str, float] = {}
        for i, domain in enumerate(domains):
            if i in level_indices:
                index = level_indices[i].get(float(point[i]))
                if index is None:
                    return None
                value = actual_levels[i][index]
            else:
                value = domain.low + float(point[i]) * (domain.high - domain.low)
            if not domain.is_executable(value):
                return None
            actual[str(factors[i]["factor_id"])] = value
            normalized[i] = domain.normalized(value)
        return normalized, actual

    def feasible(point: FloatArray, actual: dict[str, float]) -> bool:
        return (
            _constraints_satisfied(actual, constraints)
            and _novel(point, excluded + selected, duplicate_tolerance)
            and all(
                float(np.linalg.norm(point - np.asarray(other))) >= min_batch_distance_normalized
                for other in selected
            )
        )

    def eligible(points: Sequence[FloatArray]) -> list[FloatArray]:
        output: list[FloatArray] = []
        seen: set[tuple[float, ...]] = set()
        for point in points:
            charge(0)
            converted = canonical(point)
            if converted is None:
                continue
            normalized, actual = converted
            visited.add(assignment(normalized))
            key = tuple(float(value) for value in normalized)
            if key not in seen and feasible(normalized, actual):
                output.append(normalized)
                seen.add(key)
        return output

    def evaluate(points: FloatArray) -> FloatArray:
        outputs: list[FloatArray] = []
        for begin in range(0, len(points), SCORE_CHUNK_SIZE):
            batch = points[begin : begin + SCORE_CHUNK_SIZE]
            charge(len(batch))
            values = np.asarray(score(batch), dtype=np.float64)
            if (
                values.shape != (len(batch),)
                or not np.all(np.isfinite(values))
                or np.any(values < 0)
            ):
                raise BayesianOptimizationError("bayesian_optimization_acquisition_invalid")
            outputs.append(values)
        return np.concatenate(outputs)

    charge(0)
    rng = np.random.default_rng(seed)
    raw_pool: list[FloatArray] = []
    if enumerate_all:
        for combination in product(*(levels[i] or () for i in discrete)):
            point: FloatArray = np.full(count, 0.5, dtype=np.float64)
            point[discrete] = combination
            raw_pool.append(point)
    if continuous or not enumerate_all:
        random_pool = _candidate_pool_for_factors(rng, factors, pool_size)
        raw_pool.extend(np.asarray(row, dtype=np.float64) for row in random_pool)
    pool = eligible(raw_pool)
    if not pool:
        raise BayesianOptimizationError("bayesian_optimization_no_feasible_candidate")
    values = evaluate(np.asarray(pool))
    records = [(point, float(value)) for point, value in zip(pool, values, strict=True)]
    neighbor_evaluated = 0

    def ordered() -> list[tuple[FloatArray, float]]:
        return sorted(records, key=lambda item: (-item[1], tuple(item[0])))

    if discrete and not enumerate_all:
        # Neighbors are executable level-index changes, not rounded SLSQP variables.
        neighbors: list[FloatArray] = []
        seen_assignments: set[tuple[int, ...]] = set()
        for point, _ in ordered():
            key = assignment(point)
            if key in seen_assignments:
                continue
            seen_assignments.add(key)
            for position, i in enumerate(discrete):
                values_i = levels[i] or ()
                for change in (-1, 1):
                    index = key[position] + change
                    if 0 <= index < len(values_i):
                        neighbor = point.copy()
                        neighbor[i] = values_i[index]
                        neighbors.append(neighbor)
            if len(seen_assignments) == 16:
                break
        existing = {tuple(point) for point in pool}
        neighbor_pool = [point for point in eligible(neighbors) if tuple(point) not in existing]
        neighbor_evaluated = len({assignment(point) for point in neighbor_pool})
        if neighbor_pool:
            neighbor_scores = evaluate(np.asarray(neighbor_pool))
            records.extend(
                (point, float(value))
                for point, value in zip(neighbor_pool, neighbor_scores, strict=True)
            )

    feasible_pool_size = len(records)
    ranked = ordered()
    best, best_score = ranked[0]
    selected_from = "feasible_pool"
    starts: list[FloatArray] = []
    used_assignments: set[tuple[int, ...]] = set()
    if continuous:
        for point, _ in ranked:
            key = assignment(point)
            if key not in used_assignments:
                starts.append(point)
                used_assignments.add(key)
        used_points = {tuple(point) for point in starts}
        starts.extend(point for point, _ in ranked if tuple(point) not in used_points)
        starts = starts[:local_start_count]
    local_successes = 0
    local_statuses: list[dict[str, object]] = []
    for start in starts:
        charge(0)

        def expand(z: FloatArray, fixed: FloatArray = start) -> FloatArray:
            full = fixed.copy()
            full[continuous] = z
            return full

        def objective(z: FloatArray) -> float:
            return -float(evaluate(expand(z)[None, :])[0])

        solver_constraints = _continuous_constraints(
            factors,
            constraints,
            continuous,
            start,
            excluded,
            selected,
            duplicate_tolerance,
            min_batch_distance_normalized,
        )
        local = minimize(
            objective,
            start[continuous],
            method="SLSQP",
            bounds=[(0.0, 1.0)] * len(continuous),
            constraints=solver_constraints,
            options={"maxiter": local_maxiter, "ftol": 1e-10},
        )
        converted = canonical(expand(np.asarray(local.x, dtype=np.float64)))
        valid = converted is not None and feasible(*converted)
        local_successes += int(bool(local.success) and valid)
        local_statuses.append(
            {
                "success": bool(local.success),
                "status": int(local.status),
                "iterations": int(local.nit),
                "feasible": valid,
            }
        )
        if valid and converted is not None:
            point, _ = converted
            # Never retain local.fun: it can precede executable-coordinate conversion.
            value = float(evaluate(point[None, :])[0])
            if value > best_score or (value == best_score and tuple(point) < tuple(best)):
                best, best_score, selected_from = point, value, "local_refinement"

    converted = canonical(best)
    if converted is None or not feasible(*converted):
        raise BayesianOptimizationError("bayesian_optimization_no_feasible_candidate")
    best, actual = converted
    if actual != _to_actual(best, factors):
        raise BayesianOptimizationError("bayesian_optimization_factor_space_invalid")
    best_score = float(evaluate(best[None, :])[0])
    zero = best_score == 0.0
    termination = (
        "acquisition_numerically_zero"
        if zero
        else "exhaustive_discrete_search"
        if not continuous and enumerate_all
        else "local_solver_incomplete_best_feasible_retained"
        if local_successes < len(starts)
        else "bounded_search_complete"
    )
    return MixedSearchResult(
        normalized_coordinates=[float(value) for value in best],
        actual_coordinates=actual,
        acquisition=best_score,
        metadata={
            "policy": "fixed_discrete_continuous_slsqp_v1",
            "space_kind": "mixed"
            if discrete and continuous
            else "discrete"
            if discrete
            else "continuous",
            "discrete_assignment_count": assignment_count,
            "enumerated_all_discrete_assignments": enumerate_all,
            "visited_discrete_assignments": [
                {
                    "level_indices": {
                        str(factors[i]["factor_id"]): key[j] for j, i in enumerate(discrete)
                    },
                    "actual_coordinates": {
                        str(factors[i]["factor_id"]): actual_levels[i][key[j]]
                        for j, i in enumerate(discrete)
                    },
                }
                for key in sorted(visited)
                if discrete
            ],
            "neighbor_assignments_evaluated": neighbor_evaluated,
            "local_starts": len(starts),
            "local_successes": local_successes,
            "local_statuses": local_statuses,
            "feasible_pool_size": feasible_pool_size,
            "evaluations": evaluations,
            "termination_reason": termination,
            "all_acquisitions_zero": zero,
            "selected_from": selected_from,
            "nearest_existing_distance": _nearest(best, excluded),
            "nearest_selected_distance": _nearest(best, selected),
            "global_optimum_guaranteed": False,
        },
    )


def _validated_points(value: Sequence[Sequence[float]], count: int) -> list[list[float]]:
    from app.statistics.bayesian_optimization import BayesianOptimizationError

    result: list[list[float]] = []
    for row in value:
        point = np.asarray(row, dtype=np.float64)
        if (
            point.shape != (count,)
            or not np.all(np.isfinite(point))
            or np.any((point < 0) | (point > 1))
        ):
            raise BayesianOptimizationError("bayesian_optimization_history_incomplete")
        result.append([float(item) for item in point])
    return result


def _nearest(point: FloatArray, others: list[list[float]]) -> float | None:
    return min((float(np.linalg.norm(point - other)) for other in others), default=None)


def _continuous_constraints(
    factors: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    continuous: list[int],
    fixed: FloatArray,
    excluded: list[list[float]],
    selected: list[list[float]],
    duplicate_tolerance: float,
    minimum_distance: float,
) -> list[dict[str, Any]]:
    from app.statistics.bayesian_optimization import _to_actual

    result: list[dict[str, Any]] = []
    actual = _to_actual(fixed, factors)
    for constraint in constraints:
        coefficients = constraint["coefficients"]
        offset = sum(
            float(coefficients.get(factor["factor_id"], 0.0))
            * (float(factor["low"]) if i in continuous else actual[factor["factor_id"]])
            for i, factor in enumerate(factors)
        )
        weights = np.asarray(
            [
                float(coefficients.get(factors[i]["factor_id"], 0.0))
                * (float(factors[i]["high"]) - float(factors[i]["low"]))
                for i in continuous
            ]
        )
        sign = -1 if constraint["relation"] == "less_than_or_equal" else 1
        constant = sign * (offset - float(constraint["bound"]))
        gradient = sign * weights

        def linear(z: FloatArray, a: FloatArray = gradient, b: float = constant) -> float:
            return float(a @ z + b)

        def linear_jac(z: FloatArray, a: FloatArray = gradient) -> FloatArray:
            return a

        result.append({"type": "ineq", "fun": linear, "jac": linear_jac})
    others = excluded + selected
    if others:
        points = np.asarray(others)
        radii = np.asarray(
            [duplicate_tolerance] * len(excluded)
            + [max(duplicate_tolerance, minimum_distance)] * len(selected)
        )

        def distance(z: FloatArray) -> FloatArray:
            full = fixed.copy()
            full[continuous] = z
            return np.sum((full - points) ** 2, axis=1) - radii**2

        def distance_jac(z: FloatArray) -> FloatArray:
            return 2 * (z - points[:, continuous])

        result.append({"type": "ineq", "fun": distance, "jac": distance_jac})
    return result
