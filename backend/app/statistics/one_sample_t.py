from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}
MIN_N = 2


class OneSampleTError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OneSampleTColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_one_sample_t(
    rows: Iterable[Sequence[str | None]],
    response_column: OneSampleTColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    alternative: str = "two_sided",
    null_mean: float = 0.0,
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise OneSampleTError("invalid_one_sample_t_alternative")

    values: list[float] = []
    n_total = 0
    n_missing = 0
    n_non_numeric = 0

    for row in rows:
        n_total += 1
        raw_value = _row_value(row, response_column.column_index)
        if raw_value is None or raw_value.strip() == "":
            n_missing += 1
            continue
        parsed = _parse_number(raw_value, decimal=decimal, thousands=thousands)
        if parsed is None:
            n_non_numeric += 1
            continue
        values.append(parsed)

    if len(values) < MIN_N:
        raise OneSampleTError("one_sample_t_n_too_small")

    sample = _sample_summary(values)
    contrast = _test_result(
        values,
        null_mean=null_mean,
        alpha=alpha,
        confidence_level=confidence_level,
        alternative=alternative,
    )
    return {
        "schema_version": 1,
        "summary_type": "one_sample_t_test",
        "method": "one_sample_t",
        "missing_policy": "complete_case",
        "alternative": alternative,
        "alpha": alpha,
        "confidence_level": confidence_level,
        "null_mean": null_mean,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            n_missing=n_missing,
            n_non_numeric=n_non_numeric,
        ),
        "response": _column_payload(response_column),
        "n_total": n_total,
        "n_used": len(values),
        "n_missing": n_missing,
        "n_non_numeric": n_non_numeric,
        "sample": sample,
        "contrast": contrast,
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


def _column_payload(column: OneSampleTColumn) -> dict[str, object]:
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
    sorted_values = sorted(values)
    return {
        "n": len(sorted_values),
        "mean": _mean(sorted_values),
        "median": median(sorted_values),
        "variance": _sample_variance(sorted_values),
        "std": _sample_std(sorted_values),
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "warnings": ["constant_column"] if sorted_values[0] == sorted_values[-1] else [],
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _sample_variance(values: Sequence[float]) -> float:
    mean = _mean(values)
    return fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values: Sequence[float]) -> float:
    return sqrt(_sample_variance(values))


def _test_result(
    values: Sequence[float],
    *,
    null_mean: float,
    alpha: float,
    confidence_level: float,
    alternative: str,
) -> dict[str, object]:
    n = len(values)
    mean = _mean(values)
    std = _sample_std(values)
    standard_error = std / sqrt(n)
    df = float(n - 1)
    if standard_error <= 0.0 or not isfinite(standard_error):
        raise OneSampleTError("one_sample_t_standard_error_zero")

    estimate = mean - null_mean
    statistic = estimate / standard_error
    p_value = _p_value(statistic, df=df, alternative=alternative)
    return {
        "estimate": estimate,
        "estimate_definition": "mean_minus_null_mean",
        "null_mean": null_mean,
        "standard_error": standard_error,
        "statistic": statistic,
        "df": df,
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "confidence_interval": _confidence_interval(
            estimate,
            standard_error=standard_error,
            df=df,
            confidence_level=confidence_level,
            alternative=alternative,
        ),
        "effect_size": _effect_size(estimate, std=std, df=df),
    }


def _p_value(statistic: float, *, df: float, alternative: str) -> float:
    if alternative == "greater":
        return _clamp_probability(float(stats.t.sf(statistic, df)))
    if alternative == "less":
        return _clamp_probability(float(stats.t.cdf(statistic, df)))
    return _clamp_probability(float(2.0 * stats.t.sf(abs(statistic), df)))


def _confidence_interval(
    estimate: float,
    *,
    standard_error: float,
    df: float,
    confidence_level: float,
    alternative: str,
) -> dict[str, object]:
    if alternative == "greater":
        critical = float(stats.t.ppf(confidence_level, df))
        return {
            "level": confidence_level,
            "alternative": alternative,
            "lower": estimate - critical * standard_error,
            "upper": None,
        }
    if alternative == "less":
        critical = float(stats.t.ppf(confidence_level, df))
        return {
            "level": confidence_level,
            "alternative": alternative,
            "lower": None,
            "upper": estimate + critical * standard_error,
        }
    critical = float(stats.t.ppf(1.0 - ((1.0 - confidence_level) / 2.0), df))
    return {
        "level": confidence_level,
        "alternative": alternative,
        "lower": estimate - critical * standard_error,
        "upper": estimate + critical * standard_error,
    }


def _effect_size(estimate: float, *, std: float, df: float) -> dict[str, object]:
    if std <= 0.0 or df <= 1:
        return {
            "standardizer": "sample_sd",
            "cohen_dz": None,
            "hedges_g": None,
            "hedges_correction": None,
        }
    cohen_dz = estimate / std
    correction = 1.0 - (3.0 / ((4.0 * df) - 1.0))
    return {
        "standardizer": "sample_sd",
        "cohen_dz": cohen_dz,
        "hedges_g": cohen_dz * correction,
        "hedges_correction": correction,
    }


def _clamp_probability(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _result_warnings(*, n_missing: int, n_non_numeric: int) -> list[str]:
    warnings = [
        "one_sample_t_design_assumption",
        "one_sample_t_not_auto_switched",
    ]
    if n_missing > 0:
        warnings.append("missing_values_excluded")
    if n_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    return warnings
