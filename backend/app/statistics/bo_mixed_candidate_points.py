"""Mixed executable candidate identities, separate from learned kernel distances."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoFactorDomain,
    BoNumericFactorDomain,
    decode_bo_point,
    encode_bo_point,
    validate_bo_factor_domains,
)
from app.statistics.bo_mixed_initial_design import (
    MixedLinearConstraint,
    mixed_constraints_satisfied,
    validate_mixed_constraints,
)

GENERATION_POLICY = "sha256_counter_mixed_uniform_candidates_v1"
COORDINATE_ENCODING = "numeric_normalized_category_index_v1"


def _error(code: str = "bayesian_mixed_candidate_invalid") -> BayesianOptimizationError:
    return BayesianOptimizationError(code)


def canonical_mixed_point(
    domains: Sequence[BoFactorDomain], point: dict[str, Any]
) -> tuple[dict[str, Any], tuple[float, ...]]:
    encoded = encode_bo_point(domains, point)
    actual: dict[str, float | str] = {}
    for domain, value in zip(domains, encoded, strict=True):
        original = point[domain.factor_id]
        if isinstance(domain, BoNumericFactorDomain) and domain.domain.domain_kind == "continuous":
            actual[domain.factor_id] = float(original) if original != 0 else 0.0
        else:
            actual[domain.factor_id] = domain.decode(value)
    return actual, encoded


def mixed_point_distance(
    left: Sequence[float],
    right: Sequence[float],
    domains: Sequence[BoFactorDomain],
    *,
    ordinal_rank_distance: bool = False,
) -> float:
    if (
        type(ordinal_rank_distance) is not bool
        or len(left) != len(domains)
        or len(right) != len(domains)
    ):
        raise _error()
    terms = []
    for a, b, domain in zip(left, right, domains, strict=True):
        if isinstance(domain, BoCategoricalFactorDomain):
            terms.append(
                (a - b) / (len(domain.levels) - 1)
                if domain.kind == "ordinal" and ordinal_rank_distance
                else float(a != b)
            )
        else:
            terms.append(a - b)
    value = math.hypot(*terms)
    if not math.isfinite(value):
        raise _error()
    return value


def _constraint_evaluations(
    actual: dict[str, Any], constraints: Sequence[MixedLinearConstraint]
) -> list[dict[str, Any]]:
    result = []
    for constraint in constraints:
        lhs = math.fsum(coefficient * actual[key] for key, coefficient in constraint.terms)
        slack = (
            constraint.bound - lhs
            if constraint.relation == "less_than_or_equal"
            else lhs - constraint.bound
        )
        if not math.isfinite(lhs) or not math.isfinite(slack):
            raise _error("bayesian_constraint_numeric_invalid")
        result.append(
            {
                "constraint_id": constraint.constraint_id,
                "relation": constraint.relation,
                "lhs": lhs,
                "bound": constraint.bound,
                "slack": slack,
                "satisfied": mixed_constraints_satisfied(actual, [constraint]),
            }
        )
    return result


def validated_mixed_candidate_rows(
    points: list[dict[str, Any]],
    domains: Sequence[BoFactorDomain],
    constraints: Sequence[MixedLinearConstraint],
    *,
    excluded_encoded: list[list[float]],
    duplicate_tolerance: float,
    include_constraint_violations: bool = False,
    ordinal_rank_distance: bool = False,
    check_budget: Callable[[], None] | None = None,
) -> list[dict[str, Any]]:
    """Keep non-novel rows visible; imports never silently discard or coerce them."""

    def check() -> None:
        if check_budget is not None:
            check_budget()

    check()
    validate_mixed_constraints(domains, constraints)
    if (
        type(points) is not list
        or not 1 <= len(points) <= 10000
        or type(excluded_encoded) is not list
        or len(excluded_encoded) > 400
        or type(duplicate_tolerance) not in {int, float}
        or not math.isfinite(duplicate_tolerance)
        or not 1e-12 <= duplicate_tolerance <= 0.1
        or type(include_constraint_violations) is not bool
        or type(ordinal_rank_distance) is not bool
    ):
        raise _error()
    for prior in excluded_encoded:
        check()
        decode_bo_point(domains, prior)
    seen = set()
    result = []
    keys = [domain.factor_id for domain in domains]
    for index, point in enumerate(points):
        check()
        actual, encoded = canonical_mixed_point(domains, point)
        identity = tuple(actual[key] for key in keys)
        if identity in seen:
            raise _error("bayesian_candidate_duplicate_row")
        seen.add(identity)
        evaluations = _constraint_evaluations(actual, constraints)
        feasible = all(item["satisfied"] for item in evaluations)
        if not feasible and not include_constraint_violations:
            raise _error("bayesian_candidate_constraint_violation")
        nearest = min(
            (
                mixed_point_distance(
                    encoded, old, domains, ordinal_rank_distance=ordinal_rank_distance
                )
                for old in excluded_encoded
            ),
            default=None,
        )
        novel = nearest is None or nearest > duplicate_tolerance
        levels: dict[str, int | None] = {}
        for domain, value in zip(domains, encoded, strict=True):
            if isinstance(domain, BoCategoricalFactorDomain):
                levels[domain.factor_id] = int(value)
            elif domain.domain.domain_kind == "discrete_numeric":
                levels[domain.factor_id] = int(
                    (
                        (Decimal(str(actual[domain.factor_id])) - Decimal(str(domain.domain.low)))
                        / Decimal(str(domain.domain.step))
                    ).to_integral_value()
                )
            else:
                levels[domain.factor_id] = None
        row_id = hashlib.sha256(
            json.dumps(
                actual, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
        result.append(
            {
                "schema_version": 2,
                "row_id": row_id,
                "source_row_number": index + 1,
                "input_coordinates": dict(point),
                "actual_coordinates": actual,
                "encoded_coordinates": dict(zip(keys, encoded, strict=True)),
                "coordinate_encoding": COORDINATE_ENCODING,
                "distance_policy": "numeric_normalized_nominal_hamming_ordinal_rank_v1"
                if ordinal_rank_distance
                else "numeric_normalized_category_hamming_v1",
                "ordinal_rank_distance": ordinal_rank_distance,
                "canonical_level_indices": levels,
                "constraint_evaluations": evaluations,
                "constraints_satisfied": feasible,
                "nearest_existing_distance": nearest,
                "novel": novel,
                "eligible": feasible and novel,
            }
        )
    check()
    return result


def generate_mixed_candidate_points(
    domains: Sequence[BoFactorDomain],
    constraints: Sequence[MixedLinearConstraint],
    *,
    seed: int,
    count: int,
    max_attempts: int = 200000,
    check_budget: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Seeded feasible uniform pool; no claim of LHS, MaxPro, or optimizer optimality."""
    validate_bo_factor_domains(domains)
    validate_mixed_constraints(domains, constraints)
    if (
        type(seed) is not int
        or not 0 <= seed <= 2**31 - 1
        or type(count) is not int
        or not 1 <= count <= 10000
        or type(max_attempts) is not int
        or not count <= max_attempts <= 200000
    ):
        raise _error()
    finite_size = 1
    for domain in domains:
        size = (
            len(domain.levels)
            if isinstance(domain, BoCategoricalFactorDomain)
            else domain.domain.level_count
        )
        if size is None:
            finite_size = 0
            break
        finite_size *= size
    if finite_size and count > finite_size:
        raise _error("bayesian_candidate_space_exhausted")
    seen = set()
    points = []
    for attempt in range(max_attempts):
        if check_budget is not None:
            check_budget()
        point: dict[str, float | str] = {}
        for index, domain in enumerate(domains):
            integer = int.from_bytes(
                hashlib.sha256(
                    f"{GENERATION_POLICY}:{seed}:{attempt}:{index}".encode("ascii")
                ).digest(),
                "big",
            )
            if isinstance(domain, BoCategoricalFactorDomain):
                point[domain.factor_id] = domain.levels[(integer * len(domain.levels)) >> 256]
            elif domain.domain.domain_kind == "discrete_numeric":
                assert domain.domain.level_count is not None and domain.domain.step is not None
                level = (integer * domain.domain.level_count) >> 256
                point[domain.factor_id] = float(
                    Decimal(str(domain.domain.low)) + level * Decimal(str(domain.domain.step))
                )
            else:
                fraction = (integer >> 203) / 2**53
                point[domain.factor_id] = domain.domain.low + fraction * (
                    domain.domain.high - domain.domain.low
                )
        actual, _ = canonical_mixed_point(domains, point)
        identity = tuple(actual[domain.factor_id] for domain in domains)
        if identity in seen or not mixed_constraints_satisfied(actual, constraints):
            continue
        seen.add(identity)
        points.append(actual)
        if len(points) == count:
            if check_budget is not None:
                check_budget()
            return {
                "points": points,
                "generation": {
                    "policy": GENERATION_POLICY,
                    "seed": seed,
                    "requested_count": count,
                    "attempt_count": attempt + 1,
                    "max_attempts": max_attempts,
                },
            }
    raise _error("bayesian_candidate_generation_budget_exhausted")
