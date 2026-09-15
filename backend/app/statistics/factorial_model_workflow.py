"""Final-model diagnostics and explicit, serializable DOE prediction basis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from itertools import product
from math import sqrt
from typing import Any, Literal

import numpy as np
from scipy import stats  # type: ignore[import-untyped]
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

from app.statistics.term_block_model_selection import PRESS_LEVERAGE_TOLERANCE


@dataclass(frozen=True)
class FactorialFeature:
    term_id: str
    label: str
    kind: str
    factor_names: tuple[str, ...] = ()
    level_indices: tuple[int, ...] = ()
    block_index: int | None = None


def feature_row(
    features: Sequence[FactorialFeature],
    settings: dict[str, float],
    *,
    center_point: bool = False,
    block_index: int | None = None,
) -> list[float]:
    values = []
    for feature in features:
        if feature.kind == "intercept":
            value = 1.0
        elif feature.kind == "center_curvature":
            value = float(center_point)
        elif feature.kind == "block":
            value = float(block_index == feature.block_index)
        elif feature.level_indices:
            value = float(
                all(
                    settings[name] == level
                    for name, level in zip(feature.factor_names, feature.level_indices, strict=True)
                )
            )
        else:
            value = float(np.prod([settings[name] for name in feature.factor_names]))
        values.append(value)
    return values


def final_model_workflow(
    matrix: np.ndarray,
    response: np.ndarray,
    coefficients: np.ndarray,
    features: Sequence[FactorialFeature],
    *,
    response_name: str,
    run_orders: Sequence[int],
    factor_levels: dict[str, Sequence[float]],
    observed_settings: Sequence[dict[str, float]],
    center_points: Sequence[bool],
    block_indices: Sequence[int | None],
    coding: Literal["coded", "treatment"],
    confidence_level: float,
    point_limit: int,
) -> dict[str, Any]:
    """Use the supplied final fit, never select terms or refit the response."""
    fitted = matrix @ coefficients
    residuals = response - fitted
    n, p = matrix.shape
    df = n - p
    sse = float(residuals @ residuals)
    mse = sse / df if df > 0 else None
    with threadpool_limits(limits=1):
        inverse = np.linalg.inv(matrix.T @ matrix)
    leverage = np.sum((matrix @ inverse) * matrix, axis=1)
    total_ss = float(np.sum((response - np.mean(response)) ** 2))
    denominator = 1.0 - leverage
    press = (
        float(np.sum((residuals / denominator) ** 2))
        if bool(np.all(denominator > PRESS_LEVERAGE_TOLERANCE))
        else None
    )
    standardized = np.full(n, np.nan)
    cooks = np.full(n, np.nan)
    if mse is not None and mse > 0:
        valid = denominator > PRESS_LEVERAGE_TOLERANCE
        standardized[valid] = residuals[valid] / np.sqrt(mse * denominator[valid])
        cooks[valid] = residuals[valid] ** 2 * leverage[valid] / (p * mse * denominator[valid] ** 2)
    critical = float(stats.t.ppf(0.5 + confidence_level / 2, df)) if df > 0 else None
    coefficient_rows = []
    for index, (feature, coefficient) in enumerate(zip(features, coefficients, strict=True)):
        se = sqrt(max(0.0, mse * inverse[index, index])) if mse is not None and mse > 0 else None
        t_value = float(coefficient / se) if se is not None and se > 0 else None
        p_value = float(2 * stats.t.sf(abs(t_value), df)) if t_value is not None else None
        # Centered auxiliary regression: diagonal inverse times centered column SS.
        column_ss = float(np.sum((matrix[:, index] - np.mean(matrix[:, index])) ** 2))
        vif = float(inverse[index, index] * column_ss) if index > 0 and column_ss > 0 else None
        coefficient_rows.append(
            {
                "term_id": feature.term_id,
                "label": feature.label,
                "kind": feature.kind,
                "factor_names": list(feature.factor_names),
                "coefficient": float(coefficient),
                "effect": float(2 * coefficient)
                if coding == "coded" and feature.kind in {"main_effect", "interaction"}
                else None,
                "standard_error": se,
                "t_statistic": t_value,
                "p_value": p_value,
                "vif": vif,
                "ci_lower": float(coefficient - critical * se)
                if critical is not None and se is not None
                else None,
                "ci_upper": float(coefficient + critical * se)
                if critical is not None and se is not None
                else None,
                "status": "structural" if feature.kind in {"intercept", "block"} else "retained",
            }
        )
    equation = f"{response_name} = {coefficients[0]:.12g}"
    for feature, value in zip(features[1:], coefficients[1:], strict=True):
        sign = "+" if value >= 0 else "-"
        equation += f" {sign} {abs(value):.12g} [{feature.label}]"
    block_levels = sorted(set(block_indices), key=lambda value: -1 if value is None else value)
    basis = {
        "schema_version": 1,
        "coding": coding,
        "features": [asdict(feature) for feature in features],
        "coefficients": coefficients.tolist(),
        "xtx_inverse": inverse.tolist(),
        "residual_mean_square": mse,
        "residual_df": df,
        "confidence_level": confidence_level,
        "block_levels": block_levels,
        "center_settings": [
            settings
            for settings, center in zip(observed_settings, center_points, strict=True)
            if center
        ],
    }
    warnings = []
    if press is None:
        warnings.append("doe_factorial_press_unavailable_high_leverage")
    if any(row["vif"] is None for row in coefficient_rows[1:]):
        warnings.append("doe_factorial_vif_unavailable")
    with threadpool_limits(limits=1):
        anova_groups = _anova_groups(matrix, response, features, sse, mse, df)
    return {
        "equation": {
            "scale": coding,
            "response_name": response_name,
            "intercept": float(coefficients[0]),
            "terms": coefficient_rows[1:],
            "display_equation": equation,
        },
        "coded_coefficients": coefficient_rows,
        "anova_groups": anova_groups,
        "prediction_basis": basis,
        "press": press,
        "predicted_r_squared": 1.0 - press / total_ss if press is not None else None,
        "residual_plots": {
            "raw": _residual_view(residuals, fitted, run_orders, point_limit),
            "standardized": _residual_view(standardized, fitted, run_orders, point_limit),
            "points": [
                {
                    "run_order": order,
                    "observed": float(response[index]),
                    "fitted": float(fitted[index]),
                    "residual": float(residuals[index]),
                    "standardized_residual": float(standardized[index])
                    if np.isfinite(standardized[index])
                    else None,
                    "leverage": float(leverage[index]),
                    "cooks_distance": float(cooks[index]) if np.isfinite(cooks[index]) else None,
                }
                for index, order in enumerate(run_orders)
            ][:point_limit],
            "n_total": n,
            "point_limit": point_limit,
            "truncated": n > point_limit,
        },
        "factorial_plots": _cell_predictions(
            features,
            coefficients,
            factor_levels,
            observed_settings,
            response,
            center_points,
            block_levels,
        ),
        "warnings": warnings,
    }


def _anova_groups(
    matrix: np.ndarray,
    response: np.ndarray,
    features: Sequence[FactorialFeature],
    sse: float,
    mse: float | None,
    residual_df: int,
) -> list[dict[str, Any]]:
    # Joint drop-one groups, not sums of non-additive term partial SS.
    groups: dict[str, dict[tuple[str, ...], list[int]]] = {}
    for index, feature in enumerate(features):
        if feature.kind == "intercept":
            continue
        kind = (
            f"interaction_{len(feature.factor_names)}"
            if feature.kind == "interaction"
            else feature.kind
        )
        key = feature.factor_names or (feature.term_id,)
        groups.setdefault(kind, {}).setdefault(key, []).append(index)

    def row(label: str, removed: list[int]) -> dict[str, Any]:
        reduced = np.delete(matrix, removed, axis=1)
        beta, _, rank, _ = np.linalg.lstsq(reduced, response, rcond=None)
        errors = response - reduced @ beta
        ss = max(0.0, float(errors @ errors) - sse)
        df = matrix.shape[1] - int(rank)
        ms = ss / df if df > 0 else None
        f = ms / mse if ms is not None and mse is not None and mse > 0 else None
        return {
            "label": label,
            "df": df,
            "adjusted_ss": ss,
            "mean_square": ms,
            "f_statistic": f,
            "p_value": float(stats.f.sf(f, df, residual_df)) if f is not None else None,
        }

    return [
        {
            "kind": kind,
            **row(kind, [i for indices in terms.values() for i in indices]),
            "terms": [row(" * ".join(names), indices) for names, indices in terms.items()],
        }
        for kind, terms in groups.items()
    ]


def _residual_view(
    values: np.ndarray, fitted: np.ndarray, orders: Sequence[int], limit: int
) -> dict[str, Any]:
    valid = [int(index) for index in np.flatnonzero(np.isfinite(values))]
    finite = values[valid]
    bins = []
    qq = []
    reference = None
    if len(finite):
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
    return {
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


def _cell_predictions(
    features: Sequence[FactorialFeature],
    coefficients: np.ndarray,
    levels: dict[str, Sequence[float]],
    observed: Sequence[dict[str, float]],
    response: np.ndarray,
    centers: Sequence[bool],
    blocks: Sequence[int | None],
) -> dict[str, Any]:
    names = list(levels)
    cell_count = int(np.prod([len(levels[name]) for name in names]))
    if cell_count > 256:
        return {
            "cells": [],
            "available": False,
            "reason": "doe_factorial_plot_cell_limit",
            "marginalization": "equal_level_and_block_weights",
        }
    cells = []
    for values in product(*(levels[name] for name in names)):
        settings = dict(zip(names, values, strict=True))
        predictions = [
            np.dot(feature_row(features, settings, block_index=block), coefficients)
            for block in blocks
        ]
        observed_values = [
            float(y)
            for row, y, center in zip(observed, response, centers, strict=True)
            if not center and row == settings
        ]
        cells.append(
            {
                "settings": settings,
                "fitted_mean": float(np.mean(predictions)),
                "data_mean": float(np.mean(observed_values)) if observed_values else None,
                "n": len(observed_values),
            }
        )
    return {
        "cells": cells,
        "available": True,
        "reason": None,
        "marginalization": "equal_level_and_block_weights",
    }
