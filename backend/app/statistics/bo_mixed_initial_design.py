"""Bounded deterministic mixed initial conditions, explicitly not Latin hypercube."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoFactorDomain,
    BoFactorValue,
    BoNumericFactorDomain,
    encode_bo_point,
    validate_bo_factor_domains,
)

INITIAL_POLICY = "sha256_counter_mixed_uniform_feasible_v1"
ATTEMPTS_PER_TRIAL = 1000


@dataclass(frozen=True)
class MixedLinearConstraint:
    constraint_id: str
    terms: tuple[tuple[str, float], ...]
    relation: Literal["less_than_or_equal", "greater_than_or_equal"]
    bound: float


def validate_mixed_constraints(
    domains: Sequence[BoFactorDomain], constraints: Sequence[MixedLinearConstraint]
) -> None:
    validate_bo_factor_domains(domains)
    numeric = {item.factor_id for item in domains if isinstance(item, BoNumericFactorDomain)}
    if len(constraints) > 16 or len({item.constraint_id for item in constraints}) != len(
        constraints
    ):
        raise ValueError("bayesian_constraint_invalid")
    for item in constraints:
        if (
            not item.constraint_id
            or not 1 <= len(item.terms) <= len(domains)
            or len({key for key, _ in item.terms}) != len(item.terms)
            or any(key not in numeric for key, _ in item.terms)
        ):
            raise ValueError("bayesian_mixed_constraint_requires_numeric_factor")
        values = [item.bound, *(value for _, value in item.terms)]
        if (
            item.relation not in {"less_than_or_equal", "greater_than_or_equal"}
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                for value in values
            )
            or not any(value != 0 for _, value in item.terms)
        ):
            raise ValueError("bayesian_constraint_invalid")


def mixed_constraints_satisfied(
    point: Mapping[str, BoFactorValue], constraints: Sequence[MixedLinearConstraint]
) -> bool:
    for item in constraints:
        terms = []
        for key, coefficient in item.terms:
            value = point[key]
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError("bayesian_mixed_constraint_requires_numeric_factor")
            terms.append(coefficient * value)
        try:
            lhs = math.fsum(terms)
        except (ValueError, OverflowError) as exc:
            raise ValueError("bayesian_constraint_numeric_invalid") from exc
        if not math.isfinite(lhs):
            raise ValueError("bayesian_constraint_numeric_invalid")
        tolerance = 1e-12 * max(1, abs(lhs), abs(item.bound))
        if item.relation == "less_than_or_equal" and lhs > item.bound + tolerance:
            return False
        if item.relation == "greater_than_or_equal" and lhs < item.bound - tolerance:
            return False
    return True


@dataclass(frozen=True)
class MixedInitialDesign:
    actual_points: tuple[dict[str, BoFactorValue], ...]
    encoded_points: tuple[dict[str, float], ...]
    metadata: dict[str, Any]


def _counter(seed: int, attempt: int, index: int) -> int:
    digest = hashlib.sha256(f"{INITIAL_POLICY}:{seed}:{attempt}:{index}".encode("ascii")).digest()
    return int.from_bytes(digest, "big")


def generate_mixed_initial_design(
    domains: Sequence[BoFactorDomain],
    constraints: Sequence[MixedLinearConstraint],
    *,
    seed: int,
    size: int,
) -> MixedInitialDesign:
    validate_mixed_constraints(domains, constraints)
    if not any(isinstance(item, BoCategoricalFactorDomain) for item in domains):
        raise ValueError("bayesian_mixed_factor_required")
    if (
        type(seed) is not int
        or not 0 <= seed <= 2**31 - 1
        or type(size) is not int
        or not max(2, len(domains) + 1) <= size <= 64
    ):
        raise ValueError("bayesian_study_initial_design_too_small")
    discrete_size = 1
    for domain in domains:
        if isinstance(domain, BoCategoricalFactorDomain):
            discrete_size *= len(domain.levels)
        elif domain.domain.level_count is None:
            discrete_size = 0
            break
        else:
            discrete_size *= domain.domain.level_count
    if discrete_size and size > discrete_size:
        raise ValueError("bayesian_initial_design_unique_space_exhausted")
    actual, encoded, seen = [], [], set()
    attempt_limit = size * ATTEMPTS_PER_TRIAL
    duplicates, infeasible = 0, 0
    for attempt in range(attempt_limit):
        point: dict[str, BoFactorValue] = {}
        for index, domain in enumerate(domains):
            integer = _counter(seed, attempt, index)
            if isinstance(domain, BoCategoricalFactorDomain):
                point[domain.factor_id] = domain.levels[(integer * len(domain.levels)) >> 256]
            elif domain.domain.domain_kind == "discrete_numeric":
                count = domain.domain.level_count
                assert count is not None and domain.domain.step is not None
                level = (integer * count) >> 256
                point[domain.factor_id] = float(
                    Decimal(str(domain.domain.low)) + level * Decimal(str(domain.domain.step))
                )
            else:
                fraction = (integer >> 203) / 2**53
                point[domain.factor_id] = domain.domain.low + fraction * (
                    domain.domain.high - domain.domain.low
                )
        coordinates = encode_bo_point(domains, point)
        identity = tuple(point[item.factor_id] for item in domains)
        if identity in seen:
            duplicates += 1
            continue
        if not mixed_constraints_satisfied(point, constraints):
            infeasible += 1
            continue
        seen.add(identity)
        actual.append(point)
        encoded.append(dict(zip((item.factor_id for item in domains), coordinates, strict=True)))
        if len(actual) == size:
            counts = {
                item.factor_id: [
                    sum(row[item.factor_id] == level for row in actual) for level in item.levels
                ]
                for item in domains
                if isinstance(item, BoCategoricalFactorDomain)
            }
            missing = {
                key: [index for index, count in enumerate(values) if count == 0]
                for key, values in counts.items()
                if any(count == 0 for count in values)
            }
            return MixedInitialDesign(
                tuple(actual),
                tuple(encoded),
                {
                    "policy": INITIAL_POLICY,
                    "seed": seed,
                    "requested_size": size,
                    "generated_size": size,
                    "attempt_limit": attempt_limit,
                    "attempts_consumed": attempt + 1,
                    "rejected_duplicate_count": duplicates,
                    "rejected_infeasible_count": infeasible,
                    "coordinate_encoding": "numeric_normalized_category_index_v1",
                    "category_level_counts": counts,
                    "unobserved_level_indices": missing,
                    "warnings": ["bayesian_initial_category_levels_uncovered"] if missing else [],
                },
            )
    raise ValueError("bayesian_initial_design_feasible_budget_exhausted")
