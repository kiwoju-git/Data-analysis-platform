"""Numerical provenance dispatch for stored desirability EI calculations."""

from __future__ import annotations

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_beta_legacy import DesirabilityImprovement

BETA_NUMERICAL_POLICY = "positive_beta_integral_v2"


def stored_beta_expected_improvement(
    mean: float,
    variance: float,
    incumbent: float,
    *,
    xi: float = 0.0,
    numerical_policy: str | None,
) -> DesirabilityImprovement:
    if numerical_policy is None:
        from app.statistics.bo_beta_legacy import beta_expected_improvement
    elif numerical_policy == BETA_NUMERICAL_POLICY:
        from app.statistics.bo_desirability_acquisition import beta_expected_improvement
    else:
        raise BayesianOptimizationError("bayesian_desirability_numerical_policy_unsupported")
    return beta_expected_improvement(mean, variance, incumbent, xi=xi)
