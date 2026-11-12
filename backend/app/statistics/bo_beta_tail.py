"""Positive, width-scaled Beta stop-loss integral for concentrated shapes.

The integrand is still the Beta density, not a Gaussian approximation.
Stirling's log-Gamma correction has a bounded next term for shapes >= 100.
"""

from __future__ import annotations

import math
from decimal import Decimal, localcontext

from app.statistics.bayesian_optimization import BayesianOptimizationError


def _log1pmx(x: float) -> float:
    if abs(x) >= 0.01:
        return math.log1p(x) - x
    term, result = x * x, -x * x / 2
    for k in range(3, 13):
        term *= -x
        result -= term / k
    return result


def _stirling_correction(x: float) -> float:
    inverse = 1 / x
    square = inverse * inverse
    return inverse * (1 / 12 + square * (-1 / 360 + square * (1 / 1260 - square / 1680)))


def concentrated_beta_improvement(a: float, b: float, threshold: float) -> float:
    with localcontext() as context:
        context.prec = 60
        da, db = Decimal(a), Decimal(b)
        mean = da / (da + db)
        sd = float((mean * (1 - mean) / (da + db + 1)).sqrt())
        if min(a, b) < 100 or sd < 100_000 * math.ulp(float(mean)):
            raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
        # Preserve the exact ratio of stored binary64 shapes and complementary
        # threshold. Rounding either before centering can overwhelm a narrow SD.
        return _integral(a, b, Decimal(threshold))


def _integral(a: float, b: float, threshold_decimal: Decimal) -> float:
    from scipy.integrate import quad  # type: ignore[import-untyped]

    da, db = Decimal(a), Decimal(b)
    total = da + db
    exact_mean = da / total
    mean, complement, n = float(exact_mean), float(db / total), float(total)
    sd = math.sqrt(mean * complement / (n + 1))
    if threshold_decimal >= 1:
        return 0.0
    if threshold_decimal <= 0:
        return mean
    if threshold_decimal < exact_mean:
        return math.fsum(
            [float(exact_mean - threshold_decimal), _integral(b, a, 1 - threshold_decimal)]
        )
    threshold, remaining = float(threshold_decimal), float(1 - threshold_decimal)
    distance = float(threshold_decimal - exact_mean)
    slope = (-n * distance + float(2 * threshold_decimal - 1)) / (threshold * remaining)
    width = min(sd, 1 / -slope) if slope < 0 else sd
    upper = min(64.0, remaining / width)
    log_density = math.fsum(
        [
            a * _log1pmx(distance / mean),
            b * _log1pmx(-distance / complement),
            0.5 * math.log(n * mean * complement / (2 * math.pi)),
            -math.log(threshold),
            -math.log(remaining),
            _stirling_correction(n) - _stirling_correction(a) - _stirling_correction(b),
        ]
    )

    def log_ratio(u: float) -> float:
        d = width * u
        if d >= remaining:
            return -math.inf
        return math.fsum(
            [
                (a - 1) * _log1pmx(d / threshold),
                (b - 1) * _log1pmx(-d / remaining),
                d * slope,
            ]
        )

    integrated = quad(
        lambda u: u * math.exp(log_ratio(u)),
        0,
        upper,
        epsabs=0,
        epsrel=2e-10,
        limit=64,
        full_output=1,
    )
    if len(integrated) != 3:
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
    integral, error, _ = integrated
    if not math.isfinite(integral) or integral <= 0 or error > 2e-9 * integral:
        raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
    if width * upper < remaining:
        delta = width * upper
        end = threshold + delta
        rate = (n * (distance + delta) + 1 - 2 * end) / (end * (remaining - delta)) * width
        if rate <= 0:
            raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
        remainder_bound = math.exp(log_ratio(upper)) * (upper / rate + 1 / rate**2)
        if remainder_bound > 2e-10 * integral:
            raise BayesianOptimizationError("bayesian_desirability_beta_precision_unsupported")
    result = math.exp(log_density + 2 * math.log(width) + math.log(integral))
    if not math.isfinite(result) or not 0 <= result <= mean:
        raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
    return result
