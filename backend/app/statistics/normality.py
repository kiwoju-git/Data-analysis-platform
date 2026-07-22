from __future__ import annotations

import importlib.metadata
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import exp, fsum, isfinite, sqrt
from statistics import NormalDist

from scipy import stats  # type: ignore[import-untyped]

SHAPIRO_MIN_N = 3
SHAPIRO_PVALUE_ACCURACY_MAX_N = 5000
DEFAULT_QQ_POINT_LIMIT = 1000


@dataclass(frozen=True)
class NormalityColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass
class _ColumnAccumulator:
    spec: NormalityColumn
    n_total: int = 0
    n_missing: int = 0
    n_non_numeric: int = 0
    values: list[float] = field(default_factory=list)


def calculate_normality(
    rows: Iterable[Sequence[str | None]],
    columns: list[NormalityColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    include_qq_points: bool = True,
    qq_point_limit: int = DEFAULT_QQ_POINT_LIMIT,
) -> dict[str, object]:
    accumulators = [_ColumnAccumulator(spec=column) for column in columns]

    for row in rows:
        for accumulator in accumulators:
            accumulator.n_total += 1
            value = (
                row[accumulator.spec.column_index]
                if accumulator.spec.column_index < len(row)
                else None
            )
            if value is None or value.strip() == "":
                accumulator.n_missing += 1
                continue

            number = _parse_number(value, decimal=decimal, thousands=thousands)
            if number is None:
                accumulator.n_non_numeric += 1
                continue

            accumulator.values.append(number)

    return {
        "schema_version": 2,
        "summary_type": "normality_test",
        "missing_policy": "available_case_by_column",
        "alpha": alpha,
        "qq_plot_distribution": "standard_normal",
        "qq_plotting_position": "rank_minus_half_over_n",
        "shape_moment_definition": "population_central_moments",
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": ["normality_not_method_switch"],
        "columns": [
            _column_result(
                accumulator,
                alpha=alpha,
                include_qq_points=include_qq_points,
                qq_point_limit=qq_point_limit,
            )
            for accumulator in accumulators
        ],
    }


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


def _column_result(
    accumulator: _ColumnAccumulator,
    *,
    alpha: float,
    include_qq_points: bool,
    qq_point_limit: int,
) -> dict[str, object]:
    values = sorted(accumulator.values)
    n_used = len(values)
    column_warnings: list[str] = []
    if accumulator.n_non_numeric > 0:
        column_warnings.append("non_numeric_values_excluded")
    if n_used == 0:
        column_warnings.append("no_numeric_values")
    elif n_used < SHAPIRO_MIN_N:
        column_warnings.append("normality_insufficient_observations")
    elif values[0] == values[-1]:
        column_warnings.append("constant_column")
    if n_used > SHAPIRO_PVALUE_ACCURACY_MAX_N:
        column_warnings.append("shapiro_large_n_pvalue_limitation")

    qq_points, qq_truncated = _qq_points(
        values,
        include_points=include_qq_points,
        point_limit=qq_point_limit,
    )
    if qq_truncated:
        column_warnings.append("normality_qq_points_truncated")

    return {
        "column_id": accumulator.spec.column_id,
        "column_index": accumulator.spec.column_index,
        "display_name": accumulator.spec.display_name,
        "data_type": accumulator.spec.data_type,
        "measurement_level": accumulator.spec.measurement_level,
        "role": accumulator.spec.role,
        "unit": accumulator.spec.unit,
        "n_total": accumulator.n_total,
        "n_used": n_used,
        "n_missing": accumulator.n_missing,
        "n_non_numeric": accumulator.n_non_numeric,
        "mean": _mean(values),
        "std": _sample_std(values),
        "skewness": _skewness(values),
        "kurtosis_excess": _kurtosis_excess(values),
        "shapiro_wilk": _shapiro_wilk(values),
        "anderson_darling": _anderson_darling(values, alpha=alpha),
        "qq_plot": {
            "point_count": len(qq_points),
            "points_truncated": qq_truncated,
            "points": qq_points,
        },
        "warnings": column_warnings,
    }


def _shapiro_wilk(sorted_values: Sequence[float]) -> dict[str, object]:
    computed = len(sorted_values) >= SHAPIRO_MIN_N and not _is_constant(sorted_values)
    payload: dict[str, object] = {
        "computed": computed,
        "statistic": None,
        "p_value": None,
        "valid_n_min": SHAPIRO_MIN_N,
        "p_value_accuracy_n_max": SHAPIRO_PVALUE_ACCURACY_MAX_N,
    }
    if not computed:
        return payload

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        result = stats.shapiro(sorted_values)
    payload["statistic"] = float(result.statistic)
    payload["p_value"] = float(result.pvalue)
    return payload


def _anderson_darling(sorted_values: Sequence[float], *, alpha: float) -> dict[str, object]:
    computed = len(sorted_values) >= SHAPIRO_MIN_N and not _is_constant(sorted_values)
    payload: dict[str, object] = {
        "computed": computed,
        "statistic": None,
        "adjusted_statistic": None,
        "p_value": None,
        "p_value_method": "stephens_normal_unknown_mean_variance",
        "p_value_is_approximate": True,
        "critical_values": [],
        "decision_at_alpha": None,
    }
    if not computed:
        return payload

    result = stats.anderson(sorted_values, dist="norm")
    statistic = float(result.statistic)
    adjusted_statistic = _anderson_adjusted_statistic(sorted_values)
    p_value = _anderson_pvalue_from_adjusted_statistic(adjusted_statistic)
    critical_values: list[dict[str, object]] = [
        {
            "significance_level": float(level) / 100.0,
            "critical_value": float(critical),
            "reject_normality": statistic > float(critical),
        }
        for critical, level in zip(result.critical_values, result.significance_level, strict=True)
    ]
    payload["statistic"] = statistic
    payload["adjusted_statistic"] = adjusted_statistic
    payload["p_value"] = p_value
    payload["critical_values"] = critical_values
    payload["decision_at_alpha"] = _anderson_decision(critical_values, alpha=alpha)
    return payload


def _anderson_adjusted_statistic(sorted_values: Sequence[float]) -> float:
    n = len(sorted_values)
    mean = fsum(sorted_values) / n
    std = _sample_std(sorted_values)
    if std is None or std <= 0 or not isfinite(std):
        raise ValueError("Anderson-Darling requires finite non-constant values.")

    standardized = [(value - mean) / std for value in sorted_values]
    terms = []
    for index, value in enumerate(standardized, start=1):
        reverse_value = standardized[n - index]
        log_cdf = float(stats.norm.logcdf(value))
        log_sf = float(stats.norm.logsf(reverse_value))
        if not isfinite(log_cdf) or not isfinite(log_sf):
            raise ValueError("Anderson-Darling tail probability is not finite.")
        terms.append((2 * index - 1) * (log_cdf + log_sf))

    statistic = -n - fsum(terms) / n
    adjusted = statistic * (1 + 0.75 / n + 2.25 / (n * n))
    if not isfinite(adjusted) or adjusted < 0:
        raise ValueError("Adjusted Anderson-Darling statistic is not finite.")
    return adjusted


def _anderson_pvalue_from_adjusted_statistic(adjusted_statistic: float) -> float:
    if not isfinite(adjusted_statistic) or adjusted_statistic < 0:
        raise ValueError("Adjusted Anderson-Darling statistic must be finite and non-negative.")
    if adjusted_statistic < 0.2:
        p_value = 1 - exp(
            -13.436 + 101.14 * adjusted_statistic - 223.73 * adjusted_statistic**2,
        )
    elif adjusted_statistic < 0.34:
        p_value = 1 - exp(
            -8.318 + 42.796 * adjusted_statistic - 59.938 * adjusted_statistic**2,
        )
    elif adjusted_statistic < 0.6:
        p_value = exp(
            0.9177 - 4.279 * adjusted_statistic - 1.38 * adjusted_statistic**2,
        )
    elif adjusted_statistic <= 13:
        p_value = exp(
            1.2937 - 5.709 * adjusted_statistic + 0.0186 * adjusted_statistic**2,
        )
    else:
        p_value = 0.0
    if not isfinite(p_value):
        raise ValueError("Approximate Anderson-Darling p-value is not finite.")
    return min(1.0, max(0.0, p_value))


def _anderson_decision(
    critical_values: list[dict[str, object]],
    *,
    alpha: float,
) -> dict[str, object]:
    for item in critical_values:
        level = item["significance_level"]
        if isinstance(level, float) and abs(level - alpha) <= 1e-12:
            return {
                "alpha": alpha,
                "critical_value": item["critical_value"],
                "reject_normality": item["reject_normality"],
                "method": "tabulated_critical_value",
            }
    return {
        "alpha": alpha,
        "critical_value": None,
        "reject_normality": None,
        "method": "alpha_not_tabulated",
    }


def _qq_points(
    sorted_values: Sequence[float],
    *,
    include_points: bool,
    point_limit: int,
) -> tuple[list[dict[str, float]], bool]:
    if not include_points or not sorted_values:
        return [], False
    selected_indices, truncated = _selected_point_indices(len(sorted_values), point_limit)
    normal = NormalDist()
    n = len(sorted_values)
    return [
        {
            "theoretical": normal.inv_cdf((index + 0.5) / n),
            "sample": sorted_values[index],
        }
        for index in selected_indices
    ], truncated


def _selected_point_indices(n: int, point_limit: int) -> tuple[list[int], bool]:
    if n <= point_limit:
        return list(range(n)), False
    if point_limit <= 1:
        return [0], True

    indices = {round(position * (n - 1) / (point_limit - 1)) for position in range(point_limit)}
    return sorted(indices), True


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return fsum(values) / len(values)


def _sample_std(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = fsum(values) / len(values)
    variance = fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return sqrt(variance)


def _skewness(values: Sequence[float]) -> float | None:
    if len(values) < 3 or _is_constant(values):
        return None
    mean = fsum(values) / len(values)
    m2 = fsum((value - mean) ** 2 for value in values) / len(values)
    m3 = fsum((value - mean) ** 3 for value in values) / len(values)
    return m3 / (m2**1.5)


def _kurtosis_excess(values: Sequence[float]) -> float | None:
    if len(values) < 4 or _is_constant(values):
        return None
    mean = fsum(values) / len(values)
    m2 = fsum((value - mean) ** 2 for value in values) / len(values)
    m4 = fsum((value - mean) ** 4 for value in values) / len(values)
    return m4 / (m2**2) - 3.0


def _is_constant(sorted_values: Sequence[float]) -> bool:
    return len(sorted_values) > 0 and sorted_values[0] == sorted_values[-1]
