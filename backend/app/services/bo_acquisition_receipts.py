"""Validate legacy receipt metadata without replaying platform-dependent Beta EI."""

import math
from enum import Enum
from typing import Any

from app.api.v1.schemas.bo_desirability_calculation import _Acquisition
from app.statistics.bayesian_optimization import BayesianOptimizationError


class _ValidationBoundary(Enum):
    CALCULATION = "calculation"
    STORED_RECEIPT = "stored_receipt"


def legacy_payoff_roundoff_budget(mean: float) -> float:
    """Bound the frozen subtraction's 64-epsilon range allowance without replay.

    Its survival-weighted left/right operands are mathematically at most mean.
    This is only a payoff-range allowance, not an EI accuracy or match tolerance.
    """
    return 64 * math.ulp(1.0) * mean


def validate_legacy_acquisition_receipt(
    acquisition: dict[str, Any],
    mean: float,
    variance: float,
    incumbent: float,
    *,
    xi: float,
) -> None:
    """Keep source/moment links, not a new special-function evaluation of old EI.

    Only trusted stored-reader wrappers call this after document/source checks.
    Checksums are unchanged; they are integrity checks, not authenticity proofs.
    """
    saved = _Acquisition.model_validate(acquisition)

    def require(condition: bool) -> None:
        if not condition:
            raise BayesianOptimizationError("bayesian_desirability_result_invalid")

    def same(actual: float | None, expected: float | None) -> bool:
        if actual is None or expected is None:
            return actual is expected
        return actual == expected or (
            actual != 0
            and expected != 0
            and abs(actual - expected) <= 16 * max(math.ulp(actual), math.ulp(expected))
        )

    require(saved.numerical_policy is None)
    require(all(math.isfinite(value) for value in (mean, variance, incumbent, xi)))
    require(0 <= mean <= 1 and 0 <= incumbent <= 1 and xi >= 0)
    maximum_variance = mean * (1 - mean)
    require(0 <= variance <= maximum_variance)
    threshold = incumbent + xi
    require(math.isfinite(threshold))
    require(saved.threshold == threshold and saved.xi_desirability == xi)
    roundoff_budget = legacy_payoff_roundoff_budget(mean)
    require(saved.value <= mean + roundoff_budget)
    maximum_payoff = max(1 - threshold, 0.0)
    require(saved.value <= maximum_payoff + roundoff_budget)
    if variance == 0:
        require(saved.distribution == "point_mass" and saved.alpha is saved.beta is None)
        require(same(saved.value, max(mean - threshold, 0.0)))
    elif variance == maximum_variance:
        require(saved.distribution == "bernoulli_limit" and saved.alpha is saved.beta is None)
        require(same(saved.value, mean * max(1 - threshold, 0.0)))
    else:
        concentration = maximum_variance / variance - 1
        alpha, beta = mean * concentration, (1 - mean) * concentration
        require(all(math.isfinite(value) and value > 0 for value in (alpha, beta)))
        require(concentration <= 1e8 and saved.distribution == "beta_moment_match")
        require(same(saved.alpha, alpha) and same(saved.beta, beta))
        if threshold >= 1:
            require(saved.value == 0)
        elif threshold == 0:
            require(saved.value == mean)
