"""Explicit composition of stored mixture transforms and executable process factors."""

from __future__ import annotations

import itertools
import math
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any

from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoFactorDomain,
    BoNumericFactorDomain,
    bo_factor_domains_from_payload,
    bo_factor_domains_to_payload,
    decode_bo_point,
    encode_bo_point,
    validate_bo_factor_domains,
)
from app.statistics.bo_mixed_initial_design import (
    MixedLinearConstraint,
    mixed_constraints_satisfied,
)
from app.statistics.bo_mixture_domain import BoMixtureDomain

POLICY = "mixture_pseudocomponents_process_v1"
METRIC = "mixture_actual_bound_width_process_v1"
SAMPLER = "bounded_seeded_mixture_polytope_v1"


@dataclass(frozen=True)
class BoMixtureDesign:
    mixture: BoMixtureDomain
    process_factors: tuple[BoFactorDomain, ...] = ()
    constraints: tuple[MixedLinearConstraint, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.mixture, BoMixtureDomain):
            raise ValueError("mixture_design_invalid")
        if not isinstance(self.process_factors, tuple) or not isinstance(self.constraints, tuple):
            raise ValueError("mixture_design_invalid")
        if self.process_factors:
            validate_bo_factor_domains(self.process_factors)
        keys = self.keys
        if len(keys) > 10 or len(set(keys)) != len(keys):
            raise ValueError("mixture_design_factor_identity_invalid")
        numeric = {c.factor_id for c in self.mixture.components} | {
            f.factor_id for f in self.process_factors if isinstance(f, BoNumericFactorDomain)
        }
        if len(self.constraints) > 16 or len({c.constraint_id for c in self.constraints}) != len(
            self.constraints
        ):
            raise ValueError("bayesian_constraint_invalid")
        for constraint in self.constraints:
            values = [constraint.bound, *(v for _, v in constraint.terms)]
            if (
                not constraint.constraint_id
                or not constraint.terms
                or len({k for k, _ in constraint.terms}) != len(constraint.terms)
                or any(k not in numeric for k, _ in constraint.terms)
                or constraint.relation not in {"less_than_or_equal", "greater_than_or_equal"}
                or any(type(v) not in {int, float} or not math.isfinite(v) for v in values)
                or not any(v != 0 for _, v in constraint.terms)
            ):
                raise ValueError("bayesian_constraint_invalid")

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(c.factor_id for c in self.mixture.components) + tuple(
            f.factor_id for f in self.process_factors
        )

    def canonical(self, point: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[float, ...]]:
        if not isinstance(point, Mapping) or set(point) != set(self.keys):
            raise ValueError("bayesian_point_factor_identity_mismatch")
        component = {c.factor_id: point[c.factor_id] for c in self.mixture.components}
        actual: dict[str, float | str] = dict(
            zip(component, self.mixture.validate_actual(component), strict=True)
        )
        process = {f.factor_id: point[f.factor_id] for f in self.process_factors}
        encoded_process = encode_bo_point(self.process_factors, process) if process else ()
        # Existing discrete canonicalization is allowed only after executable-grid
        # validation; mixture amounts themselves are preserved, never repaired.
        actual.update(
            decode_bo_point(self.process_factors, list(encoded_process)) if process else {}
        )
        for factor in self.process_factors:
            if (
                isinstance(factor, BoNumericFactorDomain)
                and factor.domain.domain_kind == "continuous"
            ):
                actual[factor.factor_id] = float(point[factor.factor_id])
        return actual, (*self.mixture.encode(component), *encoded_process)

    def decode(self, encoded: Sequence[float]) -> dict[str, Any]:
        n = len(self.mixture.components)
        if len(encoded) != len(self.keys):
            raise ValueError("bayesian_point_shape_invalid")
        result: dict[str, Any] = self.mixture.decode(encoded[:n])
        if self.process_factors:
            result.update(decode_bo_point(self.process_factors, list(encoded[n:])))
        return result

    def metric_coordinates(self, point: Mapping[str, Any]) -> tuple[float, ...]:
        actual, encoded = self.canonical(point)
        component = {c.factor_id: actual[c.factor_id] for c in self.mixture.components}
        return (*self.mixture.metric_coordinates(component), *encoded[len(component) :])

    def distance(
        self,
        left: Mapping[str, Any],
        right: Mapping[str, Any],
        *,
        ordinal_rank_distance: bool = True,
    ) -> float:
        if type(ordinal_rank_distance) is not bool:
            raise ValueError("mixture_design_metric_invalid")
        if not ordinal_rank_distance and any(
            isinstance(f, BoCategoricalFactorDomain) and f.kind == "ordinal"
            for f in self.process_factors
        ):
            raise ValueError("mixture_design_ordinal_rank_required")
        a, b = self.metric_coordinates(left), self.metric_coordinates(right)
        terms = [x - y for x, y in zip(a, b, strict=True)]
        for index, factor in enumerate(self.process_factors, len(self.mixture.components)):
            if isinstance(factor, BoCategoricalFactorDomain):
                terms[index] = (
                    (a[index] - b[index]) / (len(factor.levels) - 1)
                    if factor.kind == "ordinal" and ordinal_rank_distance
                    else float(a[index] != b[index])
                )
        return math.hypot(*terms)

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "policy": POLICY,
            "metric_policy": METRIC,
            "mixture": self.mixture.payload(),
            "process_factors": bo_factor_domains_to_payload(self.process_factors)
            if self.process_factors
            else None,
            "constraints": [
                {
                    "constraint_id": c.constraint_id,
                    "terms": [[k, v] for k, v in c.terms],
                    "relation": c.relation,
                    "bound": c.bound,
                }
                for c in self.constraints
            ],
        }

    @classmethod
    def from_payload(cls, payload: Any) -> BoMixtureDesign:
        if (
            type(payload) is not dict
            or set(payload)
            != {
                "schema_version",
                "policy",
                "metric_policy",
                "mixture",
                "process_factors",
                "constraints",
            }
            or type(payload["schema_version"]) is not int
            or payload["schema_version"] != 1
            or payload["policy"] != POLICY
            or payload["metric_policy"] != METRIC
            or type(payload["constraints"]) is not list
        ):
            raise ValueError("mixture_design_payload_invalid")
        constraints = []
        for row in payload["constraints"]:
            if type(row) is not dict or set(row) != {"constraint_id", "terms", "relation", "bound"}:
                raise ValueError("mixture_design_payload_invalid")
            constraints.append(
                MixedLinearConstraint(
                    row["constraint_id"],
                    tuple(tuple(t) for t in row["terms"]),
                    row["relation"],
                    row["bound"],
                )
            )
        result = cls(
            BoMixtureDomain.from_payload(payload["mixture"]),
            ()
            if payload["process_factors"] is None
            else bo_factor_domains_from_payload(payload["process_factors"]),
            tuple(constraints),
        )
        if result.payload() != payload:
            raise ValueError("mixture_design_payload_invalid")
        return result

    def _feasible_point(self, check: Callable[[], None]) -> dict[str, Any]:
        from scipy.optimize import linprog  # type: ignore[import-untyped]

        components = self.mixture.components
        numeric = [f for f in self.process_factors if isinstance(f, BoNumericFactorDomain)]
        discrete = [f for f in numeric if f.domain.domain_kind == "discrete_numeric"]
        size = math.prod(f.domain.level_count or 0 for f in discrete)
        keys = [c.factor_id for c in components] + [f.factor_id for f in numeric]
        bounds = [(c.low, c.high) for c in components] + [
            (f.domain.low, f.domain.high) for f in numeric
        ]
        a, b = [], []
        for c in self.constraints:
            coefficients = dict(c.terms)
            sign = 1 if c.relation == "less_than_or_equal" else -1
            a.append([sign * coefficients.get(k, 0) for k in keys])
            b.append(sign * c.bound)
        combinations = itertools.product(*(range(f.domain.level_count or 0) for f in discrete))
        for levels in itertools.islice(combinations, 4096):
            check()
            current = list(bounds)
            for factor, level in zip(discrete, levels, strict=True):
                value = float(
                    Decimal(str(factor.domain.low)) + level * Decimal(str(factor.domain.step))
                )
                current[keys.index(factor.factor_id)] = (value, value)
            result = linprog(
                [0.0] * len(keys),
                A_ub=a or None,
                b_ub=b or None,
                A_eq=[[1.0] * len(components) + [0.0] * len(numeric)],
                b_eq=[self.mixture.total],
                bounds=current,
                method="highs",
                options={"time_limit": 1.0},
            )
            check()
            if result.status == 2:
                continue
            if not result.success:
                raise ValueError("mixture_design_feasibility_budget_exhausted")
            point: dict[str, float | str] = dict(zip(keys, map(float, result.x), strict=True))
            point.update(
                {
                    f.factor_id: f.levels[0]
                    for f in self.process_factors
                    if isinstance(f, BoCategoricalFactorDomain)
                }
            )
            try:
                self.canonical(point)
            except ValueError:
                raise ValueError("mixture_design_feasibility_numeric_failure") from None
            if not mixed_constraints_satisfied(point, self.constraints):
                raise ValueError("mixture_design_feasibility_numeric_failure")
            return point
        raise ValueError(
            "mixture_design_feasibility_budget_exhausted"
            if size > 4096
            else "mixture_design_proven_infeasible"
        )

    def sample(
        self,
        *,
        seed: int,
        count: int,
        max_attempts: int = 200000,
        check_budget: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        if (
            type(seed) is not int
            or not 0 <= seed <= 2**31 - 1
            or type(count) is not int
            or not 1 <= count <= 10000
            or type(max_attempts) is not int
            or not 1 <= max_attempts <= 200000
        ):
            raise ValueError("mixture_design_sampling_input_invalid")
        check = check_budget or (lambda: None)
        self._feasible_point(check)
        rng = random.Random(seed)
        points, seen = [], set()
        for attempt in range(1, max_attempts + 1):
            check()
            order = list(self.mixture.components)
            rng.shuffle(order)
            point: dict[str, Any] = {}
            for index, component in enumerate(order):
                remaining = order[index + 1 :]
                mass = math.fsum([self.mixture.total, *(-v for v in point.values())])
                low = max(component.low, math.fsum([mass, *(-c.high for c in remaining)]))
                high = min(component.high, math.fsum([mass, *(-c.low for c in remaining)]))
                if low > high:
                    break
                point[component.factor_id] = (
                    low if low == high else low + rng.random() * (high - low)
                )
            if len(point) != len(order):
                continue
            for factor in self.process_factors:
                if isinstance(factor, BoCategoricalFactorDomain):
                    point[factor.factor_id] = factor.levels[rng.randrange(len(factor.levels))]
                elif factor.domain.domain_kind == "discrete_numeric":
                    level = rng.randrange(factor.domain.level_count or 0)
                    point[factor.factor_id] = float(
                        Decimal(str(factor.domain.low)) + level * Decimal(str(factor.domain.step))
                    )
                else:
                    point[factor.factor_id] = factor.domain.low + rng.random() * (
                        factor.domain.high - factor.domain.low
                    )
            try:
                actual, _ = self.canonical(point)
            except ValueError:
                continue
            identity = tuple(actual[k] for k in self.keys)
            if identity in seen or not mixed_constraints_satisfied(actual, self.constraints):
                continue
            seen.add(identity)
            points.append(actual)
            if len(points) == count:
                return {
                    "points": points,
                    "generation": {
                        "policy": SAMPLER,
                        "seed": seed,
                        "requested_count": count,
                        "attempt_count": attempt,
                        "max_attempts": max_attempts,
                        "stop_reason": "requested_count_reached",
                        "exact_uniform": False,
                    },
                }
        raise ValueError("mixture_design_sampling_budget_exhausted")

    def profile(self, holds: Mapping[str, Any], axis_id: str, *, count: int = 21) -> dict[str, Any]:
        if type(count) is not int or not 2 <= count <= 100:
            raise ValueError("mixture_profile_count_invalid")
        actual, _ = self.canonical(holds)
        component_ids = {c.factor_id for c in self.mixture.components}
        if axis_id not in component_ids:
            return self._process_profile(actual, axis_id, count=count)
        component_holds = {k: actual[k] for k in component_ids}
        trace = self.mixture.profile(component_holds, axis_id, count=max(3, count))
        result: dict[str, Any] = {
            "points": [],
            "feasible_interval": None,
            "policy": trace.balancing_rule,
            "unavailable_reason": trace.unavailable_reason,
        }
        if not trace.points:
            return result
        start, end = trace.points[0], trace.points[-1]
        # Retain the pure helper's validated endpoints. When constraints trim
        # the path, intersect and interpolate in its same high-precision domain.
        with localcontext() as context:
            context.prec = 800
            zero, one = Decimal(0), Decimal(1)
            lo, hi = zero, one
            starts = {k: Decimal.from_float(start[k]) for k in component_ids}
            ends = {k: Decimal.from_float(end[k]) for k in component_ids}
            for constraint in self.constraints:
                lhs0 = sum(
                    (
                        Decimal.from_float(float(coef))
                        * (
                            starts[k]
                            if k in component_ids
                            else Decimal.from_float(float(actual[k]))
                        )
                        for k, coef in constraint.terms
                    ),
                    zero,
                )
                lhs1 = sum(
                    (
                        Decimal.from_float(float(coef))
                        * (ends[k] if k in component_ids else Decimal.from_float(float(actual[k])))
                        for k, coef in constraint.terms
                    ),
                    zero,
                )
                sign = one if constraint.relation == "less_than_or_equal" else -one
                coefficient = sign * (lhs1 - lhs0)
                bound = sign * (Decimal.from_float(float(constraint.bound)) - lhs0)
                if coefficient > 0:
                    hi = min(hi, bound / coefficient)
                elif coefficient < 0:
                    lo = max(lo, bound / coefficient)
                elif bound < 0:
                    lo, hi = one, zero
            if lo >= hi:
                return {
                    **result,
                    "unavailable_reason": "mixture_profile_process_constraints_unavailable",
                }
            if lo == zero and hi == one:
                components = (
                    [trace.points[0], trace.points[-1]] if count == 2 else list(trace.points)
                )
            else:
                components = []
                for i in range(count):
                    t = lo if i == 0 else hi if i == count - 1 else lo + (hi - lo) * i / (count - 1)
                    components.append(
                        {
                            k: start[k]
                            if t == zero
                            else end[k]
                            if t == one
                            else float(starts[k] + t * (ends[k] - starts[k]))
                            for k in component_ids
                        }
                    )
        path = []
        for component_point in components:
            point = {**actual, **component_point}
            self.canonical(point)
            if not mixed_constraints_satisfied(point, self.constraints):
                raise ValueError("mixture_profile_numeric_failure")
            path.append(point)
        return {
            **result,
            "points": path,
            "feasible_interval": [path[0][axis_id], path[-1][axis_id]],
        }

    def _process_profile(
        self, actual: dict[str, Any], axis_id: str, *, count: int
    ) -> dict[str, Any]:
        if type(count) is not int or not 2 <= count <= 100:
            raise ValueError("mixture_profile_count_invalid")
        factor = next((f for f in self.process_factors if f.factor_id == axis_id), None)
        if factor is None:
            raise ValueError("mixture_profile_axis_invalid")
        unavailable: dict[str, Any] = {
            "points": [],
            "feasible_interval": None,
            "policy": "held_mixture_process_axis_v1",
            "unavailable_reason": "mixture_profile_process_constraints_unavailable",
        }
        if isinstance(factor, BoCategoricalFactorDomain):
            return {
                **unavailable,
                "points": [{**actual, axis_id: level} for level in factor.levels],
                "unavailable_reason": None,
            }
        low, high = factor.domain.low, factor.domain.high
        for constraint in self.constraints:
            coefficients = dict(constraint.terms)
            constant = math.fsum(v * actual[k] for k, v in constraint.terms if k != axis_id)
            sign = 1 if constraint.relation == "less_than_or_equal" else -1
            a, b = sign * coefficients.get(axis_id, 0), sign * (constraint.bound - constant)
            if a > 0:
                high = min(high, b / a)
            elif a < 0:
                low = max(low, b / a)
            elif b < 0:
                return unavailable
        if low > high:
            return unavailable
        available = None
        if factor.domain.domain_kind == "discrete_numeric":
            step = Decimal(str(factor.domain.step))
            origin = Decimal(str(factor.domain.low))
            first = max(0, math.ceil((Decimal(str(low)) - origin) / step))
            last = min(
                (factor.domain.level_count or 0) - 1,
                math.floor((Decimal(str(high)) - origin) / step),
            )
            available = max(0, last - first + 1)
            if not available:
                return {**unavailable, "available_level_count": None}
            displayed = min(count, available)
            indices = (
                [first]
                if displayed == 1
                else [first + i * (available - 1) // (displayed - 1) for i in range(displayed)]
            )
            levels = [float(origin + i * step) for i in indices]
        else:
            levels = (
                [low]
                if low == high
                else list(
                    dict.fromkeys(
                        [
                            low,
                            *(low + (high - low) * i / (count - 1) for i in range(1, count - 1)),
                            high,
                        ]
                    )
                )
            )
        points = [{**actual, axis_id: value} for value in levels]
        for point in points:
            self.canonical(point)
            if not mixed_constraints_satisfied(point, self.constraints):
                raise ValueError("mixture_profile_numeric_failure")
        return {
            **unavailable,
            "points": points,
            "feasible_interval": [low, high],
            "unavailable_reason": None if points else unavailable["unavailable_reason"],
            **({"available_level_count": available} if available is not None else {}),
        }
