"""Stored final-model residual views; no model fitting or source-row loading."""

from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy import stats  # type: ignore[import-untyped]


def residual_view(
    values: np.ndarray,
    fitted: np.ndarray,
    orders: Sequence[int],
    limit: int,
    *,
    include_availability: bool = False,
    unavailable_reason: str = "non_finite_residuals",
) -> dict[str, Any]:
    if values.ndim != 1 or fitted.shape != values.shape or len(orders) != len(values):
        raise ValueError("doe_residual_view_shape_invalid")
    if limit < 1 or len(set(orders)) != len(orders) or not np.all(np.isfinite(fitted)):
        raise ValueError("doe_residual_view_identity_invalid")
    valid = [int(index) for index in np.flatnonzero(np.isfinite(values))]
    finite = values[valid]
    bins = []
    qq = []
    reference = None
    if len(finite):
        # Preserve the factorial full-N bin and Blom Q-Q policies.
        counts, edges = np.histogram(
            finite, bins=min(30, max(5, int(np.ceil(np.sqrt(len(finite))))))
        )
        bins = [
            {"lower": float(edges[i]), "upper": float(edges[i + 1]), "count": int(count)}
            for i, count in enumerate(counts)
        ]
        sorted_indices = sorted(valid, key=lambda index: (values[index], orders[index]))
        quantiles = stats.norm.ppf((np.arange(1, len(finite) + 1) - 0.375) / (len(finite) + 0.25))
        ordered_values = values[sorted_indices]
        slope, intercept = (
            np.polyfit(quantiles, ordered_values, 1) if len(finite) > 1 else (0.0, finite[0])
        )
        reference = {"slope": float(slope), "intercept": float(intercept)}
        qq = [
            {
                "run_order": orders[index],
                "theoretical_quantile": float(quantiles[rank]),
                "residual": float(values[index]),
            }
            for rank, index in enumerate(sorted_indices)
        ][:limit]
    result = {
        "n": len(finite),
        "histogram": bins,
        "qq_points": qq,
        "reference_line": reference,
        "points": [
            {
                "run_order": orders[index],
                "fitted": float(fitted[index]),
                "residual": float(values[index]),
            }
            for index in valid[:limit]
        ],
    }
    if include_availability:
        result.update(
            {
                "n_total": len(values),
                "n_available": len(finite),
                "n_displayed": min(len(finite), limit),
                "truncated": len(finite) > limit,
                "unavailable_reason": unavailable_reason if len(finite) < len(values) else None,
            }
        )
    return result


def standardized_residuals(
    residuals: np.ndarray,
    leverage: np.ndarray,
    mse: float | None,
    residual_df: int,
) -> tuple[np.ndarray, str | None]:
    values = np.full(residuals.shape, np.nan)
    if residual_df <= 0:
        return values, "no_residual_degrees_of_freedom"
    if mse is None or not np.isfinite(mse) or mse <= 0:
        return values, "residual_variance_unavailable"
    # A leverage indistinguishable from one has no standardized residual.
    one_minus_hat = 1 - leverage
    valid = np.isfinite(one_minus_hat) & (one_minus_hat > 64 * np.finfo(float).eps)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore", under="ignore"):
        denominator = np.sqrt(mse * one_minus_hat[valid])
        values[valid] = residuals[valid] / denominator
    values[~np.isfinite(values)] = np.nan
    return values, None if np.all(
        np.isfinite(values)
    ) else "standardization_denominator_unavailable"
