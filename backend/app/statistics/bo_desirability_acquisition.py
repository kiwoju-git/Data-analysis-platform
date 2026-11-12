"""Moment-matched Beta improvement; not exact transformed-Gaussian EI/qNEI."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_beta_legacy import DesirabilityImprovement as LegacyDesirabilityImprovement
from app.statistics.bo_beta_policy import BETA_NUMERICAL_POLICY
from app.statistics.bo_desirability import finite_number

ACQUISITION_POLICY = "independent_desirability_beta_ei_v1"


@dataclass(frozen=True)
class DesirabilityImprovement(LegacyDesirabilityImprovement):
    numerical_policy: str = BETA_NUMERICAL_POLICY


def beta_expected_improvement(
    mean: float, variance: float, incumbent: float, *, xi: float = 0.0
) -> DesirabilityImprovement:
    """EI in dimensionless desirability units with explicit numerical limits.

    Unresolved concentrated distributions are rejected, not replaced by point
    masses. A proven far-tail underflow is an ordinary rounded Beta EI of zero.
    """
    from scipy.special import betaincc  # type: ignore[import-untyped]

    mu, var, baseline, exploration = map(finite_number, (mean, variance, incumbent, xi))
    if not 0 <= mu <= 1 or var < 0 or not 0 <= baseline <= 1 or exploration < 0:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    maximum_variance = mu * (1 - mu)
    if var > maximum_variance:
        raise BayesianOptimizationError("bayesian_desirability_moments_invalid")
    threshold = baseline + exploration
    if not math.isfinite(threshold):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    if var == 0:
        return DesirabilityImprovement(
            max(mu - threshold, 0.0), threshold, "point_mass", None, None
        )
    if var == maximum_variance:
        return DesirabilityImprovement(
            mu * max(1 - threshold, 0.0), threshold, "bernoulli_limit", None, None
        )
    concentration = maximum_variance / var - 1
    a, b = mu * concentration, (1 - mu) * concentration
    if not all(math.isfinite(v) and v > 0 for v in (a, b)):
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
    if concentration > 1e8 or (concentration > 1e6 and min(a, b) >= 100):
        from app.statistics.bo_beta_tail import concentrated_beta_improvement

        if _tail_improvement_rounds_to_zero(a, b, threshold):
            return DesirabilityImprovement(0.0, threshold, "beta_moment_match", a, b)
        value = concentrated_beta_improvement(a, b, threshold)
        return DesirabilityImprovement(value, threshold, "beta_moment_match", a, b)
    if threshold >= 1:
        return DesirabilityImprovement(0.0, threshold, "beta_moment_match", a, b)
    if threshold == 0:
        return DesirabilityImprovement(mu, threshold, "beta_moment_match", a, b)
    left = mu * float(betaincc(a + 1, b, threshold))
    right = threshold * float(betaincc(a, b, threshold))
    value = left - right
    tolerance = 64 * math.ulp(1.0) * max(left, right)
    if not math.isfinite(value) or value < -tolerance or value > mu + tolerance:
        raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
    if value <= tolerance and max(left, right) > 0:
        if _tail_improvement_rounds_to_zero(a, b, threshold):
            value = 0.0
        else:
            raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
    return DesirabilityImprovement(value, threshold, "beta_moment_match", a, b)


def _tail_improvement_rounds_to_zero(a: float, b: float, threshold: float) -> bool:
    """Bound EI, not its two cancelling survival-probability terms.

    For a,b >= 1 the log density is concave. Beyond its mode the tangent
    bounds f(t+u) <= f(t)*exp(-rate*u), hence EI <= f(t)/rate**2.
    Only a bound strictly below half the smallest subnormal permits zero.
    This does not replace a concentrated Beta with a deterministic response.
    """
    from scipy.special import betaln  # type: ignore[import-untyped]

    if a < 1 or b < 1 or not 0 < threshold < 1:
        return False
    left_rate, right_rate = (a - 1) / threshold, (b - 1) / (1 - threshold)
    # Subtract a conservative floating-point margin to keep the bound upward.
    rate = right_rate - left_rate - 64 * math.ulp(1.0) * (right_rate + left_rate)
    if not math.isfinite(rate) or rate <= 0:
        return False
    terms = (
        (a - 1) * math.log(threshold),
        (b - 1) * math.log1p(-threshold),
        -float(betaln(a, b)),
        -2 * math.log(rate),
    )
    if not all(math.isfinite(term) for term in terms):
        return False
    log_bound = math.fsum(terms)
    rounding_margin = 128 * math.ulp(1.0) * math.fsum(abs(term) for term in terms)
    return log_bound + rounding_margin < math.log(math.ulp(0.0)) - math.log(2)
