from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}
MIN_PAIRS = 2


class PairedTError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PairedTColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_paired_t(
    rows: Iterable[Sequence[str | None]],
    before_column: PairedTColumn,
    after_column: PairedTColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    alternative: str = "two_sided",
    null_difference: float = 0.0,
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise PairedTError("invalid_paired_t_alternative")

    before_values: list[float] = []
    after_values: list[float] = []
    differences: list[float] = []
    n_total = 0
    n_missing_before = 0
    n_missing_after = 0
    n_non_numeric_before = 0
    n_non_numeric_after = 0
    n_incomplete_pairs = 0
    n_non_numeric_pairs = 0

    for row in rows:
        n_total += 1
        before_raw = _row_value(row, before_column.column_index)
        after_raw = _row_value(row, after_column.column_index)
        before_missing = before_raw is None or before_raw.strip() == ""
        after_missing = after_raw is None or after_raw.strip() == ""
        if before_missing or after_missing:
            n_incomplete_pairs += 1
            if before_missing:
                n_missing_before += 1
            if after_missing:
                n_missing_after += 1
            continue

        assert before_raw is not None
        assert after_raw is not None
        before_parsed = _parse_number(before_raw, decimal=decimal, thousands=thousands)
        after_parsed = _parse_number(after_raw, decimal=decimal, thousands=thousands)
        if before_parsed is None or after_parsed is None:
            n_non_numeric_pairs += 1
            if before_parsed is None:
                n_non_numeric_before += 1
            if after_parsed is None:
                n_non_numeric_after += 1
            continue

        before_values.append(before_parsed)
        after_values.append(after_parsed)
        differences.append(after_parsed - before_parsed)

    if len(differences) < MIN_PAIRS:
        raise PairedTError("paired_t_n_too_small")

    paired_sample = _paired_sample_summary(before_values, after_values, differences)
    contrast = _test_result(
        differences,
        null_difference=null_difference,
        alpha=alpha,
        confidence_level=confidence_level,
        alternative=alternative,
    )
    return {
        "schema_version": 1,
        "summary_type": "paired_t_test",
        "method": "paired_t",
        "design": "wide_two_measurement_columns",
        "difference_definition": "after_minus_before",
        "missing_policy": "complete_pair",
        "alternative": alternative,
        "alpha": alpha,
        "confidence_level": confidence_level,
        "null_difference": null_difference,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            n_incomplete_pairs=n_incomplete_pairs,
            n_non_numeric_pairs=n_non_numeric_pairs,
        ),
        "before": _column_payload(before_column),
        "after": _column_payload(after_column),
        "n_total": n_total,
        "n_used": len(differences),
        "n_incomplete_pairs": n_incomplete_pairs,
        "n_missing_before": n_missing_before,
        "n_missing_after": n_missing_after,
        "n_non_numeric_pairs": n_non_numeric_pairs,
        "n_non_numeric_before": n_non_numeric_before,
        "n_non_numeric_after": n_non_numeric_after,
        "paired_sample": paired_sample,
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


def _column_payload(column: PairedTColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _paired_sample_summary(
    before_values: Sequence[float],
    after_values: Sequence[float],
    differences: Sequence[float],
) -> dict[str, object]:
    sorted_differences = sorted(differences)
    return {
        "n": len(differences),
        "before_mean": _mean(before_values),
        "after_mean": _mean(after_values),
        "mean_difference": _mean(differences),
        "median_difference": median(sorted_differences),
        "difference_variance": _sample_variance(sorted_differences),
        "difference_std": _sample_std(sorted_differences),
        "min_difference": sorted_differences[0],
        "max_difference": sorted_differences[-1],
        "positive_difference_count": sum(1 for difference in differences if difference > 0.0),
        "negative_difference_count": sum(1 for difference in differences if difference < 0.0),
        "zero_difference_count": sum(1 for difference in differences if difference == 0.0),
        "warnings": (
            ["constant_difference"] if sorted_differences[0] == sorted_differences[-1] else []
        ),
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _sample_variance(values: Sequence[float]) -> float:
    mean = _mean(values)
    return fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values: Sequence[float]) -> float:
    return sqrt(_sample_variance(values))


def _test_result(
    differences: Sequence[float],
    *,
    null_difference: float,
    alpha: float,
    confidence_level: float,
    alternative: str,
) -> dict[str, object]:
    n = len(differences)
    mean_difference = _mean(differences)
    difference_std = _sample_std(differences)
    standard_error = difference_std / sqrt(n)
    df = float(n - 1)
    if standard_error <= 0.0 or not isfinite(standard_error):
        raise PairedTError("paired_t_standard_error_zero")

    estimate = mean_difference - null_difference
    statistic = estimate / standard_error
    p_value = _p_value(statistic, df=df, alternative=alternative)
    return {
        "estimate": estimate,
        "estimate_definition": "mean_after_minus_before_minus_null_difference",
        "null_difference": null_difference,
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
        "effect_size": _effect_size(estimate, std=difference_std, df=df),
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
            "standardizer": "sd_of_pair_differences",
            "cohen_dz": None,
            "hedges_g": None,
            "hedges_correction": None,
        }
    cohen_dz = estimate / std
    correction = 1.0 - (3.0 / ((4.0 * df) - 1.0))
    return {
        "standardizer": "sd_of_pair_differences",
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


def _result_warnings(
    *,
    n_incomplete_pairs: int,
    n_non_numeric_pairs: int,
) -> list[str]:
    warnings = [
        "paired_t_design_assumption",
        "paired_t_not_auto_switched",
    ]
    if n_incomplete_pairs > 0:
        warnings.append("incomplete_pairs_excluded")
    if n_non_numeric_pairs > 0:
        warnings.append("non_numeric_pairs_excluded")
    return warnings
