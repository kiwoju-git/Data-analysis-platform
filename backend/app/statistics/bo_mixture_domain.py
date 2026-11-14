"""Pure single-mixture coordinates; no process factors or model dependencies.

Actual bounds are strict. Closure permits only 16 ULPs at the larger of the
declared total and computed sum, to cover finite floating-point arithmetic.
Denominators within 16 ULPs of their subtraction scale are rejected rather than
amplifying cancellation. Imported points are never clipped or renormalized.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from math import fsum, hypot, isfinite, nextafter, ulp
from numbers import Real

_VERSION = 1
_CLOSURE_POLICY = "actual_sum_16ulp_v1"
_METRIC_POLICY = "actual_bound_width_euclidean_v1"


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("mixture_requires_finite_numeric_values")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError("mixture_requires_finite_numeric_values") from exc
    if not isfinite(result):
        raise ValueError("mixture_requires_finite_numeric_values")
    return result


def _sum(values: Sequence[float]) -> float:
    try:
        result = fsum(values)
    except OverflowError as exc:
        raise ValueError("mixture_sum_overflow") from exc
    if not isfinite(result):
        raise ValueError("mixture_sum_overflow")
    return result


def _tolerance(left: float, right: float) -> float:
    return 16 * ulp(max(abs(left), abs(right)))


def _keys(value: object, expected: set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("mixture_payload_fields_invalid")
    return value


@dataclass(frozen=True)
class BoMixtureComponent:
    factor_id: str
    low: float
    high: float
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.factor_id, str) or not self.factor_id.strip():
            raise ValueError("mixture_component_id_invalid")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("mixture_component_unit_invalid")
        low, high = _number(self.low), _number(self.high)
        if not 0 <= low <= high:
            raise ValueError("mixture_component_bounds_invalid")
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "high", high)

    def payload(self) -> dict[str, object]:
        return {"factor_id": self.factor_id, "low": self.low, "high": self.high, "unit": self.unit}


@dataclass(frozen=True)
class BoMixtureProfileTrace:
    """Actual-unit co-varying trace, not an independent component effect."""

    axis_id: str
    points: tuple[dict[str, float], ...]
    feasible_low: float | None
    feasible_high: float | None
    balancing_rule: str
    unavailable_reason: str | None


@dataclass(frozen=True)
class BoMixtureDomain:
    components: tuple[BoMixtureComponent, ...]
    total: float
    requested_coding: str
    effective_coding: str = field(init=False)
    denominator: float = field(init=False)
    affine_basis: tuple[float, ...] = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.components, tuple | list):
            raise ValueError("mixture_components_invalid")
        components = tuple(self.components)
        if not 2 <= len(components) <= 8 or any(
            not isinstance(c, BoMixtureComponent) for c in components
        ):
            raise ValueError("mixture_components_invalid")
        if len({c.factor_id for c in components}) != len(components):
            raise ValueError("mixture_component_ids_not_unique")
        if len({c.unit for c in components}) != 1:
            raise ValueError("mixture_component_units_differ")
        total = _number(self.total)
        if total <= 0:
            raise ValueError("mixture_total_not_positive")
        if self.requested_coding not in ("lower", "upper", "auto"):
            raise ValueError("mixture_coding_invalid")
        lower = _sum(tuple(c.low for c in components))
        upper = _sum(tuple(c.high for c in components))
        # Sum signed terms once: rounding sum(bounds) before subtraction loses
        # meaningful relative precision in a small but representable region.
        lower_d = _sum((total, *(-c.low for c in components)))
        upper_d = _sum((*tuple(c.high for c in components), -total))
        if (
            sum(c.low < c.high for c in components) < 2
            or lower_d <= _tolerance(total, lower)
            or upper_d <= _tolerance(upper, total)
        ):
            raise ValueError("mixture_region_degenerate_or_unrepresentable")
        effective = self.requested_coding
        if effective == "auto":
            effective = "lower" if lower_d <= upper_d else "upper"
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "total", total)
        object.__setattr__(self, "effective_coding", effective)
        object.__setattr__(self, "denominator", lower_d if effective == "lower" else upper_d)
        object.__setattr__(
            self,
            "affine_basis",
            tuple(c.low if effective == "lower" else c.high for c in components),
        )

    def validate_actual(self, point: Mapping[str, object]) -> tuple[float, ...]:
        if not isinstance(point, Mapping) or set(point) != {c.factor_id for c in self.components}:
            raise ValueError("mixture_actual_ids_invalid")
        values = tuple(_number(point[c.factor_id]) for c in self.components)
        if any(not c.low <= x <= c.high for c, x in zip(self.components, values, strict=True)):
            raise ValueError("mixture_actual_out_of_bounds")
        actual_sum = _sum(values)
        if abs(actual_sum - self.total) > _tolerance(actual_sum, self.total):
            raise ValueError("mixture_actual_not_closed")
        return values

    def encode(self, point: Mapping[str, object]) -> tuple[float, ...]:
        actual = self.validate_actual(point)
        sign = 1 if self.effective_coding == "lower" else -1
        return tuple(
            sign * (x - base) / self.denominator
            for x, base in zip(actual, self.affine_basis, strict=True)
        )

    def decode(self, encoded: Sequence[float]) -> dict[str, float]:
        if (
            not isinstance(encoded, Sequence)
            or isinstance(encoded, str | bytes)
            or len(encoded) != len(self.components)
        ):
            raise ValueError("mixture_encoded_dimension_invalid")
        values = tuple(_number(x) for x in encoded)
        # Check closure in actual units below, not with an independent coded
        # tolerance: a small denominator amplifies permitted actual roundoff.
        sign = 1 if self.effective_coding == "lower" else -1
        actual = {}
        for c, base, x in zip(self.components, self.affine_basis, values, strict=True):
            low_code = sign * (c.low - base) / self.denominator
            high_code = sign * (c.high - base) / self.denominator
            if not min(low_code, high_code) <= x <= max(low_code, high_code):
                raise ValueError("mixture_encoded_out_of_bounds")
            # Evaluate exact declared transform landmarks exactly. This is not
            # clipping: a code even one ULP outside its bound is rejected above.
            actual[c.factor_id] = (
                c.low
                if x == low_code
                else c.high
                if x == high_code
                else base + sign * self.denominator * x
            )
        self.validate_actual(actual)
        return actual

    def metric_coordinates(self, actual: Mapping[str, object]) -> tuple[float, ...]:
        values = self.validate_actual(actual)
        return tuple(
            (x - c.low) / (c.high - c.low) if c.high > c.low else 0.0
            for c, x in zip(self.components, values, strict=True)
        )

    def payload(self) -> dict[str, object]:
        return {
            "version": _VERSION,
            "components": [c.payload() for c in self.components],
            "total": self.total,
            "requested_coding": self.requested_coding,
            "effective_coding": self.effective_coding,
            "denominator": self.denominator,
            "affine_basis": list(self.affine_basis),
            "affine_sign": 1 if self.effective_coding == "lower" else -1,
            "closure_policy": _CLOSURE_POLICY,
            "metric_policy": _METRIC_POLICY,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "BoMixtureDomain":
        value = _keys(
            payload,
            {
                "version",
                "components",
                "total",
                "requested_coding",
                "effective_coding",
                "denominator",
                "affine_basis",
                "affine_sign",
                "closure_policy",
                "metric_policy",
            },
        )
        raw_components = value["components"]
        if not isinstance(raw_components, list):
            raise ValueError("mixture_payload_components_invalid")
        components = []
        for raw in raw_components:
            component = _keys(raw, {"factor_id", "low", "high", "unit"})
            factor_id, unit = component["factor_id"], component["unit"]
            if not isinstance(factor_id, str) or not isinstance(unit, str):
                raise ValueError("mixture_payload_components_invalid")
            components.append(
                BoMixtureComponent(
                    factor_id, _number(component["low"]), _number(component["high"]), unit
                )
            )
        coding = value["requested_coding"]
        if not isinstance(coding, str):
            raise ValueError("mixture_coding_invalid")
        result = cls(tuple(components), _number(value["total"]), coding)
        basis = value["affine_basis"]
        if not isinstance(basis, list):
            raise ValueError("mixture_payload_transform_invalid")
        for number in basis:
            _number(number)
        _number(value["denominator"])
        if (
            type(value["version"]) is not int
            or type(value["affine_sign"]) is not int
            or dict(value) != result.payload()
        ):
            raise ValueError("mixture_payload_transform_or_policy_mismatch")
        return result

    def profile(
        self, holds: Mapping[str, object], axis_id: str, count: int = 21
    ) -> BoMixtureProfileTrace:
        actual = self.validate_actual(holds)
        if type(count) is not int or not 3 <= count <= 100:
            raise ValueError("mixture_profile_count_invalid")
        ids = tuple(c.factor_id for c in self.components)
        if axis_id not in ids:
            raise ValueError("mixture_profile_axis_invalid")
        axis = ids.index(axis_id)
        rule = "excess_above_lower" if self.effective_coding == "lower" else "deficit_below_upper"
        component = self.components[axis]
        if component.low == component.high:
            return BoMixtureProfileTrace(axis_id, (), None, None, rule, "fixed_component")

        # Decimal arithmetic constructs bounded generated coordinates without
        # relaxing imported-point bounds. Convert interval endpoints inward.
        with localcontext() as context:
            context.prec = 800
            total = Decimal.from_float(self.total)
            lower = self.effective_coding == "lower"
            bases = tuple(Decimal.from_float(c.low if lower else c.high) for c in self.components)
            amounts = tuple(Decimal.from_float(x) for x in actual)
            mass = tuple(
                (amounts[i] - bases[i] if lower else bases[i] - amounts[i])
                if i != axis
                else Decimal(0)
                for i in range(len(ids))
            )
            balance = sum(mass, Decimal(0))
            if balance == 0:
                return BoMixtureProfileTrace(axis_id, (), None, None, rule, "zero_balancing_mass")
            ratios = tuple(x / balance for x in mass)
            denominator = total - sum(bases) if lower else sum(bases) - total
            low, high = Decimal.from_float(component.low), Decimal.from_float(component.high)
            if lower:
                high = min(high, bases[axis] + denominator)
            else:
                low = max(low, bases[axis] - denominator)
            for i, c in enumerate(self.components):
                if ratios[i] == 0:
                    continue
                capacity = Decimal.from_float(c.high) - Decimal.from_float(c.low)
                if lower:
                    low = max(low, bases[axis] + denominator - capacity / ratios[i])
                else:
                    high = min(high, bases[axis] - denominator + capacity / ratios[i])
            feasible_low, feasible_high = float(low), float(high)
            if Decimal.from_float(feasible_low) < low:
                feasible_low = nextafter(feasible_low, float("inf"))
            if Decimal.from_float(feasible_high) > high:
                feasible_high = nextafter(feasible_high, float("-inf"))
            if feasible_low >= feasible_high:
                return BoMixtureProfileTrace(
                    axis_id,
                    (),
                    feasible_low,
                    feasible_high,
                    rule,
                    "no_representable_trace_interval",
                )
            points = []
            start, end = Decimal.from_float(feasible_low), Decimal.from_float(feasible_high)
            for j in range(count):
                target = float(start + (end - start) * j / (count - 1))
                if target == actual[axis]:
                    point = dict(zip(ids, actual, strict=True))
                else:
                    t = Decimal.from_float(target)
                    remaining = (
                        denominator - (t - bases[axis])
                        if lower
                        else denominator - (bases[axis] - t)
                    )
                    point = {
                        name: target
                        if i == axis
                        else float(
                            bases[i] + ratios[i] * remaining
                            if lower
                            else bases[i] - ratios[i] * remaining
                        )
                        for i, name in enumerate(ids)
                    }
                self.validate_actual(point)
                points.append(point)
        return BoMixtureProfileTrace(
            axis_id, tuple(points), feasible_low, feasible_high, rule, None
        )


def mixture_distance(
    domain: BoMixtureDomain, left: Mapping[str, object], right: Mapping[str, object]
) -> float:
    """Euclidean actual-bound units, deliberately independent of GP coding."""
    return hypot(
        *(
            a - b
            for a, b in zip(
                domain.metric_coordinates(left), domain.metric_coordinates(right), strict=True
            )
        )
    )
