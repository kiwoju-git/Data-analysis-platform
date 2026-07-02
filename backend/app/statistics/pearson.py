from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import atanh, fsum, isfinite, sqrt, tanh

from scipy import stats  # type: ignore[import-untyped]

MIN_N = 4
DEFAULT_SCATTER_POINT_LIMIT = 500


class PearsonCorrelationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PearsonCorrelationColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_pearson_correlation(
    rows: Iterable[Sequence[str | None]],
    x_column: PearsonCorrelationColumn,
    y_column: PearsonCorrelationColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    scatter_point_limit: int = DEFAULT_SCATTER_POINT_LIMIT,
) -> dict[str, object]:
    if alpha <= 0.0 or alpha >= 1.0:
        raise PearsonCorrelationError("invalid_pearson_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise PearsonCorrelationError("invalid_pearson_confidence_level")
    if scatter_point_limit <= 0:
        raise PearsonCorrelationError("invalid_pearson_scatter_point_limit")

    x_values: list[float] = []
    y_values: list[float] = []
    n_total = 0
    n_excluded_missing_x = 0
    n_excluded_missing_y = 0
    n_excluded_non_numeric_x = 0
    n_excluded_non_numeric_y = 0

    for row in rows:
        n_total += 1
        raw_x = _row_value(row, x_column.column_index)
        raw_y = _row_value(row, y_column.column_index)
        x_missing = raw_x is None or raw_x.strip() == ""
        y_missing = raw_y is None or raw_y.strip() == ""
        if x_missing:
            n_excluded_missing_x += 1
        if y_missing:
            n_excluded_missing_y += 1
        if x_missing or y_missing:
            continue

        assert raw_x is not None
        assert raw_y is not None
        parsed_x = _parse_number(raw_x, decimal=decimal, thousands=thousands)
        parsed_y = _parse_number(raw_y, decimal=decimal, thousands=thousands)
        if parsed_x is None:
            n_excluded_non_numeric_x += 1
        if parsed_y is None:
            n_excluded_non_numeric_y += 1
        if parsed_x is None or parsed_y is None:
            continue

        x_values.append(parsed_x)
        y_values.append(parsed_y)

    n_used = len(x_values)
    if n_used < MIN_N:
        raise PearsonCorrelationError("pearson_n_too_small")
    if min(x_values) == max(x_values):
        raise PearsonCorrelationError("pearson_x_constant")
    if min(y_values) == max(y_values):
        raise PearsonCorrelationError("pearson_y_constant")

    scipy_result = stats.pearsonr(x_values, y_values)
    correlation = float(scipy_result.statistic)
    p_value = float(scipy_result.pvalue)
    if not isfinite(correlation) or not isfinite(p_value):
        raise PearsonCorrelationError("pearson_result_not_finite")

    covariance = _sample_covariance(x_values, y_values)
    confidence_interval, ci_warning = _confidence_interval(
        correlation,
        n_used=n_used,
        confidence_level=confidence_level,
    )
    warnings = _result_warnings(
        n_excluded_missing_x=n_excluded_missing_x,
        n_excluded_missing_y=n_excluded_missing_y,
        n_excluded_non_numeric_x=n_excluded_non_numeric_x,
        n_excluded_non_numeric_y=n_excluded_non_numeric_y,
    )
    if ci_warning is not None:
        warnings.append(ci_warning)

    return {
        "schema_version": 1,
        "summary_type": "pearson_correlation",
        "method": "pearson_product_moment_correlation",
        "missing_policy": "complete_case",
        "alternative": "two_sided",
        "alpha": alpha,
        "confidence_level": confidence_level,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": warnings,
        "x": _column_payload(x_column),
        "y": _column_payload(y_column),
        "n_total": n_total,
        "n_used": n_used,
        "n_excluded_missing_x": n_excluded_missing_x,
        "n_excluded_missing_y": n_excluded_missing_y,
        "n_excluded_non_numeric_x": n_excluded_non_numeric_x,
        "n_excluded_non_numeric_y": n_excluded_non_numeric_y,
        "x_summary": _sample_summary(x_values),
        "y_summary": _sample_summary(y_values),
        "scatterplot": _scatterplot_payload(
            x_values,
            y_values,
            x_column=x_column,
            y_column=y_column,
            point_limit=scatter_point_limit,
        ),
        "association": {
            "correlation": correlation,
            "r_squared": correlation * correlation,
            "covariance": covariance,
            "correlation_definition": "pearson_product_moment",
        },
        "test": {
            "statistic": correlation,
            "statistic_name": "r",
            "p_value": p_value,
            "reject_null": p_value < alpha,
            "null_hypothesis": "population_correlation_equals_0",
            "alternative": "two_sided",
        },
        "confidence_interval": confidence_interval,
    }


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _parse_number(value: str, *, decimal: str, thousands: str | None) -> float | None:
    normalized = value.strip()
    if normalized == "":
        return None
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")

    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    as_float = float(parsed)
    if not isfinite(as_float):
        return None
    return as_float


def _column_payload(column: PearsonCorrelationColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _sample_summary(values: Sequence[float]) -> dict[str, object]:
    return {
        "n": len(values),
        "mean": _mean(values),
        "std": _sample_std(values),
        "min": min(values),
        "max": max(values),
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _sample_variance(values: Sequence[float]) -> float:
    mean = _mean(values)
    return fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values: Sequence[float]) -> float:
    return sqrt(_sample_variance(values))


def _sample_covariance(x_values: Sequence[float], y_values: Sequence[float]) -> float:
    x_mean = _mean(x_values)
    y_mean = _mean(y_values)
    return fsum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values, strict=True)
    ) / (len(x_values) - 1)


def _scatterplot_payload(
    x_values: Sequence[float],
    y_values: Sequence[float],
    *,
    x_column: PearsonCorrelationColumn,
    y_column: PearsonCorrelationColumn,
    point_limit: int,
) -> dict[str, object]:
    selected_indices, truncated = _selected_point_indices(len(x_values), point_limit)
    return {
        "x_column_id": x_column.column_id,
        "y_column_id": y_column.column_id,
        "point_count": len(x_values),
        "points_truncated": truncated,
        "point_limit": point_limit,
        "points": [
            {
                "x": x_values[index],
                "y": y_values[index],
            }
            for index in selected_indices
        ],
    }


def _selected_point_indices(n: int, point_limit: int) -> tuple[list[int], bool]:
    if n <= point_limit:
        return list(range(n)), False
    if point_limit <= 1:
        return [0], True

    indices = {round(position * (n - 1) / (point_limit - 1)) for position in range(point_limit)}
    return sorted(indices), True


def _confidence_interval(
    correlation: float,
    *,
    n_used: int,
    confidence_level: float,
) -> tuple[dict[str, object], str | None]:
    if abs(correlation) >= 1.0:
        return (
            {
                "method": "fisher_z",
                "level": confidence_level,
                "lower": None,
                "upper": None,
            },
            "pearson_perfect_sample_correlation_ci_unavailable",
        )

    z_value = atanh(correlation)
    standard_error = 1.0 / sqrt(n_used - 3)
    z_critical = float(stats.norm.ppf(1.0 - ((1.0 - confidence_level) / 2.0)))
    return (
        {
            "method": "fisher_z",
            "level": confidence_level,
            "lower": tanh(z_value - (z_critical * standard_error)),
            "upper": tanh(z_value + (z_critical * standard_error)),
        },
        None,
    )


def _result_warnings(
    *,
    n_excluded_missing_x: int,
    n_excluded_missing_y: int,
    n_excluded_non_numeric_x: int,
    n_excluded_non_numeric_y: int,
) -> list[str]:
    warnings = [
        "pearson_correlation_not_causation",
        "pearson_linear_relationship_assumption",
        "pearson_outlier_sensitive",
    ]
    if n_excluded_missing_x > 0 or n_excluded_missing_y > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_x > 0 or n_excluded_non_numeric_y > 0:
        warnings.append("non_numeric_values_excluded")
    return warnings
