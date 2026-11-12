"""Independent Decimal-density reference for bounded synthetic Beta EI cases.

Run with ``python -m tests.reference.bo_beta_reference`` and backend on PYTHONPATH.
This prints regenerated values; it does not modify the fixture or use production
centering, log1pmx, survival functions, reflection, or Gaussian approximations.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from pathlib import Path

import scipy
from scipy.integrate import quad

_PI = Decimal("3.14159265358979323846264338327950288419716939937510582097494459230781640628620899")
_COEFFICIENTS = ((1, 12), (-1, 360), (1, 1260), (-1, 1680), (1, 1188), (-691, 360360), (1, 156))


@dataclass(frozen=True)
class BetaReference:
    value: float
    log_value: str
    log_tangent_upper_bound: str | None
    quadrature_relative_error: float
    tail_relative_bound: float
    log_gamma_remainder_bound: str
    alpha_hex: str
    beta_hex: str
    threshold_hex: str


def _decimal_log_gamma(x: Decimal) -> Decimal:
    correction = sum(
        (
            Decimal(numerator) / Decimal(denominator) / x ** (2 * index + 1)
            for index, (numerator, denominator) in enumerate(_COEFFICIENTS)
        ),
        Decimal(0),
    )
    return (x - Decimal("0.5")) * x.ln() - x + (2 * _PI).ln() / 2 + correction


def decimal_beta_stop_loss(alpha: float, beta: float, threshold: float) -> BetaReference:
    """Integrate the positive payoff using exact binary64 inputs at 80 digits.

    Validated reference scope: shapes >= 100, sum <= 1e40, an interior threshold,
    and a threshold no farther than eight SD below the exact shape-derived mean.
    The integrand uses direct Decimal logarithms, not production's rearrangement.
    QUADPACK integrates the resulting dimensionless positive float values.
    """
    if not all(math.isfinite(value) for value in (alpha, beta, threshold)):
        raise ValueError("reference inputs must be finite")
    if min(alpha, beta) < 100 or alpha + beta > 1e40:
        raise ValueError("reference shape scope exceeded")
    if not 0 < threshold < 1:
        raise ValueError("reference threshold must be interior")
    with localcontext() as context:
        context.prec = 80
        a, b, t = (Decimal.from_float(float(value)) for value in (alpha, beta, threshold))
        total = a + b
        mean = a / total
        sd = (mean * (1 - mean) / (total + 1)).sqrt()
        if t < mean - 8 * sd:
            raise ValueError("reference threshold is outside the validated lower-tail scope")
        log_density = (
            (a - 1) * t.ln()
            + (b - 1) * (1 - t).ln()
            - _decimal_log_gamma(a)
            - _decimal_log_gamma(b)
            + _decimal_log_gamma(total)
        )
        slope = (a - 1) / t - (b - 1) / (1 - t)
        width = min(sd, 1 / -slope) if slope < 0 else sd
        upper = min(Decimal(64), (1 - t) / width)

        def log_density_ratio(u: Decimal) -> Decimal:
            x = t + width * u
            return (a - 1) * (x / t).ln() + (b - 1) * ((1 - x) / (1 - t)).ln()

        def integrand(u: float) -> float:
            coordinate = Decimal.from_float(u)
            x = t + width * coordinate
            if not 0 < x < 1:
                return 0.0
            return float(coordinate * log_density_ratio(coordinate).exp())

        integrated = quad(
            integrand, 0, float(upper), epsabs=0, epsrel=2e-12, limit=100, full_output=1
        )
        if len(integrated) != 3:
            raise ArithmeticError("reference quadrature did not converge")
        integral, error, _ = integrated
        if not math.isfinite(integral) or integral <= 0 or error / integral > 2e-11:
            raise ArithmeticError("reference quadrature error exceeded its budget")
        integral_decimal = Decimal.from_float(integral)
        end = t + width * upper
        tail_relative_bound = Decimal(0)
        if end < 1:
            rate = ((b - 1) / (1 - end) - (a - 1) / end) * width
            if rate <= 0:
                raise ArithmeticError("reference tail tangent must have negative slope")
            tail_relative_bound = (
                log_density_ratio(upper).exp() * (upper / rate + 1 / rate**2) / integral_decimal
            )
            if tail_relative_bound > Decimal("2e-12"):
                raise ArithmeticError("reference tail bound exceeded its budget")
        log_value = log_density + 2 * width.ln() + integral_decimal.ln()
        gamma_remainder = Decimal(3617) / Decimal(122400) * (1 / a**15 + 1 / b**15 + 1 / total**15)
        return BetaReference(
            value=float(log_value.exp()),
            log_value=str(log_value),
            log_tangent_upper_bound=str(log_density - 2 * (-slope).ln()) if slope < 0 else None,
            quadrature_relative_error=error / integral,
            tail_relative_bound=float(tail_relative_bound),
            log_gamma_remainder_bound=str(gamma_remainder),
            alpha_hex=float(alpha).hex(),
            beta_hex=float(beta).hex(),
            threshold_hex=float(threshold).hex(),
        )


def moment_matched_reference(mean: float, variance: float, threshold: float) -> BetaReference:
    """Use the API's binary64 moment-to-shape definition, then independent density."""
    if not 0 < mean < 1 or not 0 < variance < mean * (1 - mean):
        raise ValueError("a proper moment-matched Beta is required")
    concentration = mean * (1 - mean) / variance - 1
    return decimal_beta_stop_loss(mean * concentration, (1 - mean) * concentration, threshold)


def main() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "bo_beta_decimal_reference.json").read_text(
            encoding="utf-8"
        )
    )
    results = [
        {
            "id": case["id"],
            **asdict(moment_matched_reference(case["mean"], case["variance"], case["threshold"])),
        }
        for case in fixture["cases"]
    ]
    print(
        json.dumps(
            {
                "reference_schema_version": 1,
                "decimal_precision": 80,
                "python_version": sys.version.split()[0],
                "scipy_version": scipy.__version__,
                "results": results,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
