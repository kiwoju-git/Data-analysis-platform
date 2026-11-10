"""Explicit versioned desirability calculations, not JMP runtime emulation.
Responses are independent; Gaussian inputs are raw-unit latent posteriors.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.statistics.bayesian_optimization import BayesianOptimizationError

CURVE_POLICY = "derringer_suich_linear_v1"
MOMENT_POLICY = "independent_latent_gaussian_split_quadrature_v1"
MAX_RESPONSES = 4
_NORMAL_CUTOFF = 12.0


def finite_number(value: Any) -> float:
    import numpy as np

    if isinstance(value, bool | np.bool_) or not isinstance(
        value, int | float | np.integer | np.floating
    ):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid") from exc
    if not math.isfinite(number):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    return number


@dataclass(frozen=True)
class DesirabilityGoal:
    response_id: str
    goal: Literal["maximize", "minimize", "match_target"]
    lower: float | None
    target: float
    upper: float | None
    importance: float = 1.0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.response_id, str)
            or not self.response_id
            or self.goal not in {"maximize", "minimize", "match_target"}
        ):
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        finite_number(self.target)
        if finite_number(self.importance) <= 0:
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        if self.goal == "maximize" and self.upper is not None:
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        if self.goal == "minimize" and self.lower is not None:
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        if self.goal != "minimize":
            lower = finite_number(self.lower)
            if not lower < self.target or not math.isfinite(self.target - lower):
                raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        if self.goal != "maximize":
            upper = finite_number(self.upper)
            if not self.target < upper or not math.isfinite(upper - self.target):
                raise BayesianOptimizationError("bayesian_desirability_input_invalid")


def normalized_importance(goals: Sequence[DesirabilityGoal]) -> tuple[float, ...]:
    if not 1 <= len(goals) <= MAX_RESPONSES or len({g.response_id for g in goals}) != len(goals):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    maximum = max(g.importance for g in goals)
    scaled = [g.importance / maximum for g in goals]
    total = math.fsum(scaled)
    weights = tuple(value / total for value in scaled)
    if any(value <= 0 for value in weights):
        raise BayesianOptimizationError("bayesian_desirability_weight_precision_unsupported")
    return weights


def individual_desirability(values: Any, goal: DesirabilityGoal) -> Any:
    import numpy as np

    from app.statistics.bo_target_curve import GaussianTargetGoal, target_desirability

    try:
        if not isinstance(values, np.ndarray):
            for scalar in np.asarray(values, dtype=object).flat:
                finite_number(scalar)
        raw = np.asarray(values)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        numbers = raw.astype(float, copy=False)
        if not np.all(np.isfinite(numbers)):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid") from exc
    if isinstance(goal, GaussianTargetGoal):
        curve = goal.curve()
        return np.asarray([target_desirability(float(v), curve) for v in numbers.flat]).reshape(
            numbers.shape
        )
    # Clip before subtraction so valid extreme observations cannot overflow.
    if goal.goal == "maximize":
        assert goal.lower is not None
        return (np.clip(numbers, goal.lower, goal.target) - goal.lower) / (goal.target - goal.lower)
    if goal.goal == "minimize":
        assert goal.upper is not None
        return (goal.upper - np.clip(numbers, goal.target, goal.upper)) / (goal.upper - goal.target)
    assert goal.lower is not None and goal.upper is not None
    rising = (np.clip(numbers, goal.lower, goal.target) - goal.lower) / (goal.target - goal.lower)
    falling = (goal.upper - np.clip(numbers, goal.target, goal.upper)) / (goal.upper - goal.target)
    return np.minimum(rising, falling)


def _matching_responses(values: Mapping[str, Any], goals: Sequence[DesirabilityGoal]) -> None:
    if set(values) != {g.response_id for g in goals}:
        raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")


def composite_desirability(values: Mapping[str, float], goals: Sequence[DesirabilityGoal]) -> float:
    from app.statistics.bo_target_curve import (
        PRECISION_ERROR,
        GaussianTargetGoal,
        target_log_desirability,
    )

    weights = normalized_importance(goals)
    _matching_responses(values, goals)
    if any(isinstance(g, GaussianTargetGoal) for g in goals):
        logs = []
        for goal, weight in zip(goals, weights, strict=True):
            value = finite_number(values[goal.response_id])
            if isinstance(goal, GaussianTargetGoal):
                logs.append(target_log_desirability(value, goal.curve(), weight))
            else:
                desirability = float(individual_desirability(value, goal))
                if desirability == 0:
                    return 0.0
                logs.append(weight * math.log(desirability))
        result = math.exp(math.fsum(logs))
        if result == 0:
            raise BayesianOptimizationError(PRECISION_ERROR)
        return result
    individual = [
        float(individual_desirability(finite_number(values[g.response_id]), g)) for g in goals
    ]
    if any(value == 0 for value in individual):
        return 0.0
    return math.exp(math.fsum(w * math.log(d) for w, d in zip(weights, individual, strict=True)))


@dataclass(frozen=True)
class DesirabilityMoments:
    mean: float
    second_moment: float
    variance: float
    estimated_absolute_error: float
    normal_tail_bound: float
    integration_evaluations: int


@dataclass
class _IntegrationBudget:
    maximum: int
    used: int = 0

    def consume(self) -> None:
        self.used += 1
        if self.used > self.maximum:
            raise BayesianOptimizationError("bayesian_desirability_integration_budget_exceeded")


def _standardized(value: float, mean: float, sd: float) -> float:
    difference = value - mean
    if math.isfinite(difference):
        return difference / sd
    scale = max(abs(value), abs(mean), sd)
    denominator = sd / scale
    return (
        (value / scale - mean / scale) / denominator
        if denominator
        else math.copysign(math.inf, difference)
    )


@dataclass(frozen=True)
class _Ramp:
    low: float
    high: float
    rising: bool


def _ramps(goal: DesirabilityGoal) -> tuple[_Ramp, ...]:
    result = []
    if goal.goal != "minimize":
        assert goal.lower is not None
        result.append(_Ramp(goal.lower, goal.target, True))
    if goal.goal != "maximize":
        assert goal.upper is not None
        result.append(_Ramp(goal.target, goal.upper, False))
    return tuple(result)


def gaussian_desirability_moments(
    mean: float,
    standard_deviation: float,
    goal: DesirabilityGoal,
    *,
    power: float = 1.0,
    max_evaluations: int = 20000,
) -> DesirabilityMoments:
    """Moments of d(Y)**power, retaining variance below a squared-mean ULP.

    Integrate every linear segment explicitly, split at the normal center, and
    account for the constant tails analytically. Centered differences use
    log1p/expm1 near d(mean), not rounded d(Y)-rounded d(mean).
    """
    from scipy.integrate import quad  # type: ignore[import-untyped]
    from scipy.special import ndtr  # type: ignore[import-untyped]

    from app.statistics.bo_target_curve import GaussianTargetGoal, target_moments

    if isinstance(goal, GaussianTargetGoal):
        return target_moments(mean, standard_deviation, goal.curve(), power=power)

    mu, sd, exponent = map(finite_number, (mean, standard_deviation, power))
    if (
        sd < 0
        or not 0 < exponent <= 2
        or type(max_evaluations) is not int
        or not 1 <= max_evaluations <= 20000
    ):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    center = float(individual_desirability(mu, goal)) ** exponent
    if sd == 0:
        return DesirabilityMoments(center, center * center, 0.0, 0.0, 0.0, 0)
    budget = _IntegrationBudget(max_evaluations)
    ramps = _ramps(goal)
    # Separate mass at d=0/1, retaining survival tails instead of 1-CDF.
    if goal.goal == "maximize":
        assert goal.lower is not None
        zero_mass = float(ndtr(_standardized(goal.lower, mu, sd)))
        one_mass = float(ndtr(-_standardized(goal.target, mu, sd)))
    elif goal.goal == "minimize":
        assert goal.upper is not None
        zero_mass = float(ndtr(-_standardized(goal.upper, mu, sd)))
        one_mass = float(ndtr(_standardized(goal.target, mu, sd)))
    else:
        assert goal.lower is not None and goal.upper is not None
        zero_mass = float(ndtr(_standardized(goal.lower, mu, sd))) + float(
            ndtr(-_standardized(goal.upper, mu, sd))
        )
        one_mass = 0.0

    def integrate(kind: str, delta_mean: float = 0.0) -> tuple[float, float]:
        def transform(value: float, delta: float) -> float:
            if kind == "mean":
                return value
            if kind == "delta":
                return delta
            return (delta - delta_mean) ** 2

        parts = [zero_mass * transform(0.0, -center), one_mass * transform(1.0, 1 - center)]
        errors = []
        for ramp in ramps:
            z_low, z_high = _standardized(ramp.low, mu, sd), _standardized(ramp.high, mu, sd)
            width = ramp.high - ramp.low
            base = (mu - ramp.low) / width if ramp.rising else (ramp.high - mu) / width
            slope = sd / width * (1 if ramp.rising else -1)
            span = width / sd
            narrow = span <= 1
            if narrow:
                # Preserve the original ramp width, not z_high-z_low: the
                # latter can round to zero for a narrow off-center target.
                low, high = 0.0, 1.0
                split = -z_low / span if span else math.inf
            else:
                low, high = max(z_low, -_NORMAL_CUTOFF), min(z_high, _NORMAL_CUTOFF)
                split = 0.0
            if low >= high:
                continue

            def density_value(
                coordinate: float,
                *,
                z_low: float = z_low,
                z_high: float = z_high,
                span: float = span,
                narrow: bool = narrow,
                ramp: _Ramp = ramp,
                base: float = base,
                slope: float = slope,
            ) -> float:
                budget.consume()
                z = z_low + span * coordinate if narrow else coordinate
                if narrow:
                    d = coordinate if ramp.rising else 1 - coordinate
                elif math.isfinite(z_high - z_low):
                    d = (
                        (z - z_low) / (z_high - z_low)
                        if ramp.rising
                        else (z_high - z) / (z_high - z_low)
                    )
                else:
                    d = base + slope * z
                tolerance = 64 * math.ulp(1.0)
                if not math.isfinite(d) or not -tolerance <= d <= 1 + tolerance:
                    raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
                d = min(1.0, max(0.0, d))
                powered = d**exponent
                change = d - base if narrow else slope * z
                if 0 < base <= 1 and d > 0:
                    ratio_log = (
                        math.log1p(change / base)
                        if math.isfinite(change) and abs(change) < 0.5 * base
                        else math.log(d) - math.log(base)
                    )
                    delta = (base**exponent - center) + base**exponent * math.expm1(
                        exponent * ratio_log
                    )
                elif center == 1 and d > 0:
                    delta = math.expm1(exponent * math.log(d))
                else:
                    delta = powered - center
                return (
                    transform(powered, delta)
                    * math.exp(-z * z / 2)
                    / math.sqrt(2 * math.pi)
                    * (span if narrow else 1.0)
                )

            breaks = [low] + ([split] if low < split < high else []) + [high]
            for left, right in zip(breaks, breaks[1:], strict=False):
                result = quad(
                    density_value,
                    left,
                    right,
                    epsabs=1e-300,
                    epsrel=2e-10,
                    limit=128,
                    full_output=1,
                )
                if len(result) != 3:
                    raise BayesianOptimizationError(
                        "bayesian_desirability_quadrature_not_converged"
                    )
                value, error, _ = result
                if not math.isfinite(value) or not math.isfinite(error):
                    raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
                parts.append(float(value))
                errors.append(float(error))
        return math.fsum(parts), math.fsum(errors)

    first, first_error = integrate("mean")
    delta, delta_error = integrate("delta")
    variance, variance_error = integrate("variance", delta)
    error = first_error + delta_error + variance_error
    tolerance = 128 * math.ulp(1.0) + error
    if (
        not -tolerance <= first <= 1 + tolerance
        or variance < 0
        or variance > first * (1 - first) + tolerance
    ):
        raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
    first = min(1.0, max(0.0, first))
    return DesirabilityMoments(
        first,
        first * first + variance,
        variance,
        error,
        2 * float(ndtr(-_NORMAL_CUTOFF)),
        budget.used,
    )


def independent_desirability_moments(
    posteriors: Mapping[str, tuple[float, float]], goals: Sequence[DesirabilityGoal]
) -> DesirabilityMoments:
    from app.statistics.bo_target_curve import PRECISION_ERROR, GaussianTargetGoal

    weights = normalized_importance(goals)
    versioned = any(isinstance(g, GaussianTargetGoal) for g in goals)
    _matching_responses(posteriors, goals)
    moments = []
    for goal, weight in zip(goals, weights, strict=True):
        pair = posteriors[goal.response_id]
        if not isinstance(pair, tuple | list) or len(pair) != 2:
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        moments.append(gaussian_desirability_moments(pair[0], pair[1], goal, power=weight))
    mean, variance = 1.0, 0.0
    if versioned and any(m.mean == 0 and m.second_moment == 0 and m.variance == 0 for m in moments):
        # An exact DS hard zero is absorbing, independent of response order.
        mean = 0.0
        product_moments = []
    else:
        product_moments = moments
    for moment in product_moments:
        # Var(XY) = Var(X) E[Y^2] + E[X]^2 Var(Y), no subtraction.
        new_variance = variance * moment.second_moment + mean * mean * moment.variance
        new_mean = mean * moment.mean
        if versioned and (
            (mean > 0 and moment.mean > 0 and new_mean == 0)
            or (
                new_variance == 0
                and (
                    (variance > 0 and moment.second_moment > 0)
                    or (mean > 0 and moment.variance > 0)
                )
            )
        ):
            raise BayesianOptimizationError(PRECISION_ERROR)
        mean, variance = new_mean, new_variance
    return DesirabilityMoments(
        mean,
        mean * mean + variance,
        variance,
        math.fsum(m.estimated_absolute_error for m in moments),
        math.fsum(m.normal_tail_bound for m in moments),
        sum(m.integration_evaluations for m in moments),
    )
