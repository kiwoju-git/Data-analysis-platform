"""Executable candidate identities, without fitting or modifying observations."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    _constraint_evaluations,
    _factor_domain,
    _validated_constraints,
    _validated_factors,
)

MAX_CANDIDATE_ROWS = 10_000
GENERATION_POLICY = "seeded_uniform_executable_candidates_v1"


def candidate_factors(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    factors = _validated_factors(payload)
    if any(not math.isfinite(f["high"] - f["low"]) for f in factors):
        raise BayesianOptimizationError("bayesian_candidate_range_precision_unsupported")
    return factors


def _evaluations(
    actual: dict[str, float], constraints: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result = _constraint_evaluations(actual, constraints)
    if any(not math.isfinite(item[key]) for item in result for key in ("lhs", "bound", "slack")):
        raise BayesianOptimizationError("bayesian_candidate_range_precision_unsupported")
    return result


def validated_candidate_rows(
    points: list[dict[str, float]],
    factors_payload: list[dict[str, Any]],
    constraints_payload: list[dict[str, Any]],
    *,
    excluded_normalized: list[list[float]],
    duplicate_tolerance: float,
    include_constraint_violations: bool = False,
    check_budget: Callable[[], None] | None = None,
) -> list[dict[str, Any]]:
    """Reject invalid imports atomically; keep valid but previously used rows visible."""
    if check_budget is not None:
        check_budget()
    factors = candidate_factors(factors_payload)
    constraints = _validated_constraints(constraints_payload, factors)
    if (
        not isinstance(points, list)
        or not 1 <= len(points) <= MAX_CANDIDATE_ROWS
        or type(include_constraint_violations) is not bool
        or type(duplicate_tolerance) not in {float, int}
        or not math.isfinite(duplicate_tolerance)
        or not 1e-12 <= duplicate_tolerance <= 0.1
    ):
        raise BayesianOptimizationError("bayesian_candidate_input_invalid")
    keys = [factor["factor_id"] for factor in factors]
    # A validated 200-trial history may also carry its canonical re-normalized
    # coordinates, which can differ from stored coordinates by one ULP.
    if not isinstance(excluded_normalized, list) or len(excluded_normalized) > 400:
        raise BayesianOptimizationError("bayesian_candidate_input_invalid")
    for excluded_point in excluded_normalized:
        if check_budget is not None:
            check_budget()
        if (
            not isinstance(excluded_point, list)
            or len(excluded_point) != len(keys)
            or any(
                type(value) not in {float, int} or not math.isfinite(value) or not 0 <= value <= 1
                for value in excluded_point
            )
        ):
            raise BayesianOptimizationError("bayesian_candidate_input_invalid")
    seen: set[tuple[float, ...]] = set()
    result: list[dict[str, Any]] = []
    domains = [_factor_domain(factor) for factor in factors]
    level_values = [d.levels() if d.domain_kind == "discrete_numeric" else None for d in domains]
    for index, point in enumerate(points):
        if check_budget is not None:
            check_budget()
        if not isinstance(point, dict) or set(point) != set(keys):
            raise BayesianOptimizationError("bayesian_candidate_coordinates_invalid")
        actual, normalized, level_indices = {}, [], {}
        for factor, domain, levels in zip(factors, domains, level_values, strict=True):
            value = point[factor["factor_id"]]
            if type(value) not in {float, int} or not domain.is_executable(value):
                raise BayesianOptimizationError("bayesian_candidate_coordinates_invalid")
            if levels is not None:
                level = int(
                    (
                        (Decimal(str(value)) - Decimal(str(domain.low))) / Decimal(str(domain.step))
                    ).to_integral_value()
                )
                value = levels[level]
                level_indices[factor["factor_id"]] = level
            actual[factor["factor_id"]] = float(value) if value != 0 else 0.0
            coordinate = domain.normalized(value)
            if not math.isfinite(coordinate) or not 0 <= coordinate <= 1:
                raise BayesianOptimizationError("bayesian_candidate_coordinates_invalid")
            normalized.append(coordinate)
        identity = tuple(actual[key] for key in keys)
        if identity in seen:
            raise BayesianOptimizationError("bayesian_candidate_duplicate_row")
        seen.add(identity)
        evaluations = _evaluations(actual, constraints)
        feasible = all(value["satisfied"] for value in evaluations)
        if not feasible and not include_constraint_violations:
            raise BayesianOptimizationError("bayesian_candidate_constraint_violation")
        nearest = min((math.dist(normalized, old) for old in excluded_normalized), default=None)
        novel = nearest is None or nearest > duplicate_tolerance
        digest = hashlib.sha256(
            json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        result.append(
            {
                "row_id": digest,
                "source_row_number": index + 1,
                "input_coordinates": dict(point),
                "canonical_level_indices": level_indices,
                "actual_coordinates": actual,
                "normalized_coordinates": dict(zip(keys, normalized, strict=True)),
                "constraints_satisfied": feasible,
                "constraint_evaluations": evaluations,
                "nearest_existing_distance": nearest,
                "novel": novel,
                "eligible": feasible and novel,
            }
        )
    if check_budget is not None:
        check_budget()
    return result


def generate_candidate_points(
    factors_payload: list[dict[str, Any]],
    constraints_payload: list[dict[str, Any]],
    *,
    count: int,
    seed: int,
    max_attempts: int = 200_000,
    include_constraint_violations: bool = False,
) -> dict[str, Any]:
    """Sample continuous coordinates and discrete levels; never round a local optimum."""
    import numpy as np

    factors = candidate_factors(factors_payload)
    constraints = _validated_constraints(constraints_payload, factors)
    if (
        type(count) is not int
        or not 1 <= count <= MAX_CANDIDATE_ROWS
        or type(seed) is not int
        or not 0 <= seed <= 2_147_483_647
        or type(max_attempts) is not int
        or not count <= max_attempts <= 200_000
        or type(include_constraint_violations) is not bool
    ):
        raise BayesianOptimizationError("bayesian_candidate_input_invalid")
    domains = [_factor_domain(factor) for factor in factors]
    levels = [
        domain.levels() if domain.domain_kind == "discrete_numeric" else None for domain in domains
    ]
    if (
        all(value is not None for value in levels)
        and math.prod(len(value) for value in levels if value is not None) < count
    ):
        raise BayesianOptimizationError("bayesian_candidate_space_exhausted")
    rng = np.random.default_rng(seed)
    points: list[dict[str, float]] = []
    seen: set[tuple[float, ...]] = set()
    for attempt in range(1, max_attempts + 1):
        values = tuple(
            float(value[int(rng.integers(len(value)))])
            if value is not None
            else float(domain.low + rng.random() * (domain.high - domain.low))
            for domain, value in zip(domains, levels, strict=True)
        )
        if values in seen:
            continue
        actual = dict(zip((f["factor_id"] for f in factors), values, strict=True))
        if not include_constraint_violations and not all(
            item["satisfied"] for item in _evaluations(actual, constraints)
        ):
            continue
        seen.add(values)
        points.append(actual)
        if len(points) == count:
            return {
                "policy": GENERATION_POLICY,
                "seed": seed,
                "requested_count": count,
                "attempt_count": attempt,
                "max_attempts": max_attempts,
                "points": points,
            }
    raise BayesianOptimizationError("bayesian_candidate_generation_budget_exhausted")
