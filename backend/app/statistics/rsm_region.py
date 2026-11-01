"""Versioned RSM regions, independent of the immutable coding transformation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from decimal import Decimal
from math import isclose, isfinite
from typing import Literal

from app.statistics.doe_factor_domain import GRID_TOLERANCE, MAX_DISCRETE_NUMERIC_LEVELS
from app.statistics.rsm_coding import CcdType, RsmFactorCoding, factor_coding

RsmRegionMode = Literal["axial_bounds", "factorial_cube", "custom", "legacy_input_bounds_v1"]


@dataclass(frozen=True)
class RsmRegionInput:
    name: str
    low: float
    high: float
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: float | None = None


@dataclass(frozen=True)
class RsmRegionFactor:
    factor_name: str
    input_low: float
    input_high: float
    input_bounds_role: str
    factorial_low: float
    factorial_high: float
    axial_low: float
    axial_high: float
    observed_low: float
    observed_high: float
    center: float
    scale: float
    lattice_anchor: float
    step: float | None
    domain_kind: Literal["continuous", "discrete_numeric"]
    lower: float
    upper: float

    def payload(self) -> dict[str, object]:
        return asdict(self)

    def is_executable(self, value: float) -> bool:
        if not isfinite(value) or not self.lower <= value <= self.upper:
            return False
        return on_rsm_lattice(value, self.lattice_anchor, self.step, self.domain_kind)


def on_rsm_lattice(value: float, anchor: float, step: float | None, domain_kind: str) -> bool:
    if not isfinite(value):
        return False
    if domain_kind == "continuous":
        return True
    if step is None or not isfinite(step) or step <= 0:
        return False
    ratio = (Decimal(str(value)) - Decimal(str(anchor))) / Decimal(str(step))
    return abs(ratio - ratio.to_integral_value()) <= GRID_TOLERANCE


def resolve_rsm_region(
    factors: Sequence[RsmRegionInput],
    *,
    alpha: float,
    coding: Mapping[str, RsmFactorCoding] | None,
    actual_runs: Sequence[Mapping[str, float]],
    coded_runs: Sequence[Mapping[str, float]],
    mode: RsmRegionMode = "axial_bounds",
    custom_bounds: Mapping[str, tuple[float, float]] | None = None,
) -> tuple[RsmRegionFactor, ...]:
    if mode not in {"axial_bounds", "factorial_cube", "custom", "legacy_input_bounds_v1"}:
        raise ValueError("doe_rsm_region_mode_invalid")
    names = [factor.name for factor in factors]
    if (
        not factors
        or len(set(names)) != len(names)
        or not actual_runs
        or len(actual_runs) != len(coded_runs)
    ):
        raise ValueError("doe_rsm_region_source_invalid")
    if coding is not None and set(coding) != set(names):
        raise ValueError("doe_rsm_region_coding_mismatch")
    custom = custom_bounds or {}
    if (mode == "custom" and set(custom) != set(names)) or (mode != "custom" and custom):
        raise ValueError("doe_rsm_region_bounds_invalid")
    resolved: list[RsmRegionFactor] = []
    for factor in factors:
        transform = (
            coding[factor.name]
            if coding is not None
            else factor_coding(
                factor.low, factor.high, alpha, "face_centered" if alpha == 1 else "inscribed"
            )
        )
        # The stored coordinate mapping is checked against both the declared
        # geometry and actual runs, never rebuilt from a chosen search region.
        kinds: dict[str, CcdType] = {
            "factorial": "circumscribed",
            "axial": "inscribed",
            "factorial_and_axial": "face_centered",
        }
        kind = kinds.get(transform.input_bounds_role)
        expected = factor_coding(factor.low, factor.high, alpha, kind) if kind else None
        if expected is None or any(
            not isclose(
                getattr(transform, key), getattr(expected, key), rel_tol=1e-12, abs_tol=1e-12
            )
            for key in (
                "center",
                "scale",
                "factorial_low",
                "factorial_high",
                "axial_low",
                "axial_high",
                "alpha",
            )
        ):
            raise ValueError("doe_rsm_region_coding_mismatch")
        values: list[float] = []
        for actual, coded in zip(actual_runs, coded_runs, strict=True):
            if factor.name not in actual or factor.name not in coded:
                raise ValueError("doe_rsm_region_run_mismatch")
            value = actual[factor.name]
            coordinate = coded[factor.name]
            if (
                not isfinite(value)
                or not isfinite(coordinate)
                or not isclose(
                    value,
                    transform.center + transform.scale * coordinate,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise ValueError("doe_rsm_region_run_mismatch")
            values.append(value)
        observed_low, observed_high = min(values), max(values)
        if not isclose(
            observed_low, transform.axial_low, rel_tol=1e-12, abs_tol=1e-12
        ) or not isclose(observed_high, transform.axial_high, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("doe_rsm_region_run_mismatch")
        lower, upper = transform.axial_low, transform.axial_high
        if mode == "factorial_cube":
            lower, upper = transform.factorial_low, transform.factorial_high
        elif mode == "legacy_input_bounds_v1":
            lower, upper = factor.low, factor.high
        elif mode == "custom":
            lower, upper = custom[factor.name]
        if (
            not all(isfinite(value) for value in (lower, upper))
            or lower >= upper
            or lower < transform.axial_low
            or upper > transform.axial_high
        ):
            raise ValueError("doe_rsm_region_bounds_invalid")
        if not all(
            on_rsm_lattice(value, factor.low, factor.step, factor.domain_kind)
            for value in (lower, upper)
        ):
            raise ValueError("doe_rsm_region_bounds_not_executable")
        if (
            factor.domain_kind == "discrete_numeric"
            and factor.step is not None
            and (upper - lower) / factor.step + 1 > MAX_DISCRETE_NUMERIC_LEVELS
        ):
            raise ValueError("doe_rsm_region_level_count_invalid")
        resolved.append(
            RsmRegionFactor(
                factor.name,
                factor.low,
                factor.high,
                transform.input_bounds_role,
                transform.factorial_low,
                transform.factorial_high,
                transform.axial_low,
                transform.axial_high,
                observed_low,
                observed_high,
                transform.center,
                transform.scale,
                factor.low,
                factor.step,
                factor.domain_kind,
                lower,
                upper,
            )
        )
    return tuple(resolved)
