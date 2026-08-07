from __future__ import annotations

from collections.abc import Sequence
from math import fsum, isfinite, sqrt

from scipy import stats  # type: ignore[import-untyped]


def sample_moments(values: Sequence[float]) -> dict[str, float | None]:
    n = len(values)
    if n == 0:
        return {
            "mean": None,
            "standard_deviation": None,
            "variance": None,
            "skewness": None,
            "kurtosis_excess": None,
        }
    mean = fsum(values) / n
    if n < 2:
        return {
            "mean": mean,
            "standard_deviation": None,
            "variance": None,
            "skewness": None,
            "kurtosis_excess": None,
        }
    variance = fsum((value - mean) ** 2 for value in values) / (n - 1)
    standard_deviation = sqrt(variance)
    if standard_deviation <= 0 or not isfinite(standard_deviation):
        skewness = None
        kurtosis = None
    else:
        standardized = [(value - mean) / standard_deviation for value in values]
        skewness = (
            n * fsum(value**3 for value in standardized) / ((n - 1) * (n - 2)) if n >= 3 else None
        )
        kurtosis = (
            n * (n + 1) * fsum(value**4 for value in standardized) / ((n - 1) * (n - 2) * (n - 3))
            - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
            if n >= 4
            else None
        )
    return {
        "mean": mean,
        "standard_deviation": standard_deviation,
        "variance": variance,
        "skewness": skewness,
        "kurtosis_excess": kurtosis,
    }


def mean_confidence_interval(values: Sequence[float], confidence_level: float) -> dict[str, object]:
    payload = _empty_interval("student_t", confidence_level)
    moments = sample_moments(values)
    mean = moments["mean"]
    standard_deviation = moments["standard_deviation"]
    if len(values) < 2 or mean is None or standard_deviation is None:
        return payload
    alpha = 1 - confidence_level
    margin = (
        float(stats.t.ppf(1 - alpha / 2, len(values) - 1)) * standard_deviation / sqrt(len(values))
    )
    payload.update(
        {"computed": True, "estimate": mean, "lower": mean - margin, "upper": mean + margin}
    )
    return payload


def standard_deviation_confidence_interval(
    values: Sequence[float], confidence_level: float
) -> dict[str, object]:
    payload = _empty_interval("chi_square_normal_population", confidence_level)
    variance = sample_moments(values)["variance"]
    if len(values) < 2 or variance is None:
        return payload
    alpha = 1 - confidence_level
    degrees_of_freedom = len(values) - 1
    lower_quantile = float(stats.chi2.ppf(alpha / 2, degrees_of_freedom))
    upper_quantile = float(stats.chi2.ppf(1 - alpha / 2, degrees_of_freedom))
    if lower_quantile <= 0 or upper_quantile <= 0:
        return payload
    payload.update(
        {
            "computed": True,
            "estimate": sqrt(variance),
            "lower": sqrt(degrees_of_freedom * variance / upper_quantile),
            "upper": sqrt(degrees_of_freedom * variance / lower_quantile),
        }
    )
    return payload


def median_confidence_interval(
    sorted_values: Sequence[float], confidence_level: float
) -> dict[str, object]:
    """Hettmansperger-Sheather sign-test interval with nonlinear interpolation."""
    payload = _empty_interval("hettmansperger_sheather_nonlinear", confidence_level)
    n = len(sorted_values)
    if n == 0:
        return payload
    estimate = float(stats.scoreatpercentile(sorted_values, 50, interpolation_method="fraction"))
    if n < 2:
        payload["estimate"] = estimate
        return payload

    beta = (1 + confidence_level) / 2
    probability = 0.5
    w = next(
        (
            candidate
            for candidate in range(1, n)
            if float(stats.binom.cdf(candidate, n, probability)) >= beta
        ),
        n - 1,
    )
    pi_w = float(stats.binom.cdf(w - 1, n, probability))
    pi_w_next = float(stats.binom.cdf(w, n, probability))
    denominator = (n - w) * probability * (beta - pi_w)
    numerator = w * (1 - probability) * (pi_w_next - beta)
    interpolation = 1.0 if denominator <= 0 else 1 / (1 + numerator / denominator)
    interpolation = min(1.0, max(0.0, interpolation))

    upper_left = min(w, n - 1)
    upper_right = min(w + 1, n) - 1
    lower_left = max(0, n - w - 1)
    lower_right = max(0, n - w)
    upper = (1 - interpolation) * sorted_values[upper_left - 1] + interpolation * sorted_values[
        upper_right
    ]
    lower = (1 - interpolation) * sorted_values[lower_right] + interpolation * sorted_values[
        lower_left
    ]
    payload.update(
        {
            "computed": True,
            "estimate": estimate,
            "lower": float(lower),
            "upper": float(upper),
            "order_statistic_index": w,
            "interpolation_weight": interpolation,
        }
    )
    return payload


def _empty_interval(method: str, confidence_level: float) -> dict[str, object]:
    return {
        "computed": False,
        "method": method,
        "confidence_level": confidence_level,
        "estimate": None,
        "lower": None,
        "upper": None,
    }
