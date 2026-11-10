"""Peak-one, two-sided Gaussian target curve; separate from the stored DS policy."""

import math
from dataclasses import dataclass

from scipy.integrate import quad  # type: ignore[import-untyped]
from scipy.special import log_ndtr, logsumexp, ndtr  # type: ignore[import-untyped]

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import DesirabilityGoal, DesirabilityMoments, finite_number

TARGET_CURVE_POLICY = "two_sided_gaussian_target_peak_one_v1"
TARGET_MOMENT_POLICY = "gaussian_target_closed_form_centered_variance_v1"
PRECISION_ERROR = "bayesian_target_curve_precision_unsupported"
MIXED_CURVE_POLICY = "per_response_target_gaussian_or_ds_v1"
MIXED_MOMENT_POLICY = "independent_latent_versioned_curve_moments_v1"


@dataclass(frozen=True)
class GaussianTargetGoal(DesirabilityGoal):
    lower_desirability: float = 0.0183
    upper_desirability: float = 0.0183

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.goal != "match_target":
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        self.curve()

    def curve(self) -> "TargetCurve":
        assert self.lower is not None and self.upper is not None
        return TargetCurve(
            self.lower, self.target, self.upper, self.lower_desirability, self.upper_desirability
        )


@dataclass(frozen=True)
class TargetCurve:
    lower: float
    target: float
    upper: float
    lower_desirability: float
    upper_desirability: float

    def __post_init__(self) -> None:
        for value in vars(self).values():
            finite_number(value)
        if not (
            self.lower < self.target < self.upper
            and math.isfinite(self.target - self.lower)
            and math.isfinite(self.upper - self.target)
            and 0 < self.lower_desirability < 1
            and 0 < self.upper_desirability < 1
        ):
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")

    def side(self, delta: float) -> tuple[float, float]:
        return (
            (self.target - self.lower, -math.log(self.lower_desirability))
            if delta < 0
            else (self.upper - self.target, -math.log(self.upper_desirability))
        )


def target_desirability(value: float, curve: TargetCurve) -> float:
    return math.exp(target_log_desirability(value, curve))


def target_log_desirability(value: float, curve: TargetCurve, power: float = 1) -> float:
    value = finite_number(value)
    power = finite_number(power)
    if not 0 < power <= 2:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    delta = value - curve.target
    width, decay = curve.side(delta)
    if power * decay == 0:
        raise BayesianOptimizationError(PRECISION_ERROR)
    ratio = delta / width if math.isfinite(delta) else (value / 2 - curve.target / 2) / (width / 2)
    return -(power * decay * ratio) * ratio


def _log_moment(mean: float, sd: float, curve: TargetCurve, power: float) -> float:
    delta = mean - curve.target
    terms = []
    for sign, width, ordinate in (
        (-1, curve.target - curve.lower, curve.lower_desirability),
        (1, curve.upper - curve.target, curve.upper_desirability),
    ):
        rate = -power * math.log(ordinate)
        if rate == 0:
            raise BayesianOptimizationError(PRECISION_ERROR)
        # hypot avoids squaring the potentially large SD/width ratio.
        scale = math.hypot(1, math.sqrt(2 * rate) * (sd / width))
        relative = (delta / width) / scale
        boundary = sign * (delta / sd) / scale
        term = -math.log(scale) - rate * relative * relative + float(log_ndtr(boundary))
        if math.isnan(term):
            raise BayesianOptimizationError(PRECISION_ERROR)
        terms.append(term)
    result = float(logsumexp(terms))
    if not math.isfinite(result) or result > 64 * math.ulp(1.0):
        raise BayesianOptimizationError(PRECISION_ERROR)
    return min(0.0, result)


def _centered_variance(
    mean: float, sd: float, curve: TargetCurve, power: float
) -> tuple[float, float, int]:
    delta = mean - curve.target
    width, decay = curve.side(delta)
    base_ratio = delta / width
    log_center = -power * decay * base_ratio * base_ratio
    evaluations = 0

    def centered(z: float) -> float:
        nonlocal evaluations
        evaluations += 1
        if evaluations > 20000:
            raise BayesianOptimizationError("bayesian_desirability_integration_budget_exceeded")
        shift = sd * z
        other_width, other_decay = curve.side(delta + shift)
        if other_width == width and other_decay == decay:
            h = shift / width
            log_change = -power * decay * h * (2 * base_ratio + h)
        else:
            ratio = (delta + shift) / other_width
            log_change = -power * other_decay * ratio * ratio - log_center
        if not math.isfinite(log_change) or log_change > 700:
            raise BayesianOptimizationError(PRECISION_ERROR)
        return math.expm1(log_change)

    boundaries = sorted({-12.0, 0.0, 12.0, max(-12.0, min(12.0, -delta / sd))})

    def integrate(center: float | None) -> tuple[float, float]:
        total = error = 0.0
        for lo, hi in zip(boundaries[:-1], boundaries[1:], strict=True):

            def integrand(z: float) -> float:
                value = centered(z)
                if center is not None:
                    value = (value - center) ** 2
                return value * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)

            result = quad(integrand, lo, hi, epsabs=1e-300, epsrel=2e-10, limit=128, full_output=1)
            if len(result) != 3:
                raise BayesianOptimizationError(PRECISION_ERROR)
            total += result[0]
            error += result[1]
        return total, error

    mean_delta, _ = integrate(None)
    variance, error = integrate(mean_delta)
    factor = math.exp(2 * log_center)
    return variance * factor, error * factor, evaluations


def target_moments(
    mean: float, sd: float, curve: TargetCurve, *, power: float = 1.0
) -> DesirabilityMoments:
    mean, sd, power = finite_number(mean), finite_number(sd), finite_number(power)
    if sd < 0 or not 0 < power <= 2:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    if sd == 0:
        value = math.exp(target_log_desirability(mean, curve, power))
        if value == 0:
            raise BayesianOptimizationError(PRECISION_ERROR)
        return DesirabilityMoments(value, value * value, 0.0, 0.0, 0.0, 0)
    first_log = _log_moment(mean, sd, curve, power)
    second_log = _log_moment(mean, sd, curve, 2 * power)
    first, second = math.exp(first_log), math.exp(second_log)
    if first == 0 or second == 0:
        raise BayesianOptimizationError(PRECISION_ERROR)
    relative_log_variance = second_log - 2 * first_log
    error = 0.0
    evaluations = 0
    if relative_log_variance < 1e-7:
        variance, error, evaluations = _centered_variance(mean, sd, curve, power)
    else:
        variance = second * -math.expm1(-relative_log_variance)
    if not math.isfinite(variance) or variance <= 0 or variance > first * (1 - first) + 1e-14:
        raise BayesianOptimizationError(PRECISION_ERROR)
    return DesirabilityMoments(
        first, second, variance, error, 2 * float(ndtr(-12)) if evaluations else 0.0, evaluations
    )
