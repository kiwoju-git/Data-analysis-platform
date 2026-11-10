"""Moment-matched Beta improvement; not exact transformed-Gaussian EI/qNEI."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import finite_number

ACQUISITION_POLICY = "independent_desirability_beta_ei_v1"


@dataclass(frozen=True)
class DesirabilityImprovement:
    value: float
    threshold: float
    distribution: str
    alpha: float | None
    beta: float | None


def beta_expected_improvement(
    mean: float, variance: float, incumbent: float, *, xi: float = 0.0
) -> DesirabilityImprovement:
    """EI in dimensionless desirability units with explicit numerical limits.

    Very concentrated proper Beta distributions are deliberately rejected in
    this foundation stage; do not silently turn them into point masses.
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
    if not all(math.isfinite(v) and v > 0 for v in (a, b)) or concentration > 1e8:
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
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
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
    return DesirabilityImprovement(value, threshold, "beta_moment_match", a, b)
