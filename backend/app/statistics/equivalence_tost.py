from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median
from typing import cast

from scipy import stats  # type: ignore[import-untyped]

DESIGN = "one_sample_mean"
MIN_N = 2


class EquivalenceTostError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class EquivalenceTostColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_equivalence_tost(
    rows: Iterable[Sequence[str | None]],
    response_column: EquivalenceTostColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    design: str = DESIGN,
    reference_mean: float,
    lower_bound: float,
    upper_bound: float,
    alpha: float = 0.05,
) -> dict[str, object]:
    if design != DESIGN:
        raise EquivalenceTostError("equivalence_tost_design_unsupported")
    if not isfinite(reference_mean):
        raise EquivalenceTostError("invalid_equivalence_tost_reference_mean")
    if not isfinite(lower_bound) or not isfinite(upper_bound):
        raise EquivalenceTostError("invalid_equivalence_tost_bounds")
    if lower_bound >= upper_bound:
        raise EquivalenceTostError("equivalence_tost_bounds_order_invalid")
    if alpha <= 0.0 or alpha >= 0.5 or not isfinite(alpha):
        raise EquivalenceTostError("invalid_equivalence_tost_alpha")

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
        raise EquivalenceTostError("equivalence_tost_n_too_small")

    sample = _sample_summary(values)
    estimate_payload = _estimate(values, reference_mean=reference_mean)
    standard_error = cast(float, estimate_payload["standard_error"])
    df = cast(float, estimate_payload["df"])
    if standard_error <= 0.0 or not isfinite(standard_error):
        raise EquivalenceTostError("equivalence_tost_standard_error_zero")

    estimate = cast(float, estimate_payload["value"])
    lower_test = _lower_tost(
        estimate,
        lower_bound=lower_bound,
        standard_error=standard_error,
        df=df,
        alpha=alpha,
    )
    upper_test = _upper_tost(
        estimate,
        upper_bound=upper_bound,
        standard_error=standard_error,
        df=df,
        alpha=alpha,
    )
    confidence_interval = _confidence_interval(
        estimate,
        standard_error=standard_error,
        df=df,
        alpha=alpha,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
    )
    equivalent = bool(lower_test["reject_null"] and upper_test["reject_null"])
    ci_inside_bounds = bool(confidence_interval["inside_equivalence_bounds"])
    lower_p_value = cast(float, lower_test["p_value"])
    upper_p_value = cast(float, upper_test["p_value"])
    sample_std = cast(float, sample["std"])

    return {
        "schema_version": 1,
        "summary_type": "equivalence_tost",
        "method": "one_sample_mean_tost",
        "input_mode": "dataset_one_numeric_column",
        "design": DESIGN,
        "missing_policy": "complete_case",
        "alpha": alpha,
        "confidence_level": 1.0 - (2.0 * alpha),
        "reference_mean": reference_mean,
        "equivalence_bounds": {
            "lower": lower_bound,
            "upper": upper_bound,
            "scale": "raw_units",
            "estimate_definition": "mean_minus_reference_mean",
        },
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
        "estimate": estimate_payload,
        "tests": {
            "lower": lower_test,
            "upper": upper_test,
        },
        "tost": {
            "p_value": max(lower_p_value, upper_p_value),
            "equivalent": equivalent,
            "decision_rule": "both_one_sided_tests_reject_at_alpha",
            "ci_inside_equivalence_bounds": ci_inside_bounds,
        },
        "confidence_interval": confidence_interval,
        "effect_size": _effect_size(estimate, std=sample_std, df=df),
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


def _column_payload(column: EquivalenceTostColumn) -> dict[str, object]:
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


def _estimate(values: Sequence[float], *, reference_mean: float) -> dict[str, object]:
    n = len(values)
    sample_mean = _mean(values)
    std = _sample_std(values)
    return {
        "value": sample_mean - reference_mean,
        "definition": "mean_minus_reference_mean",
        "standard_error": std / sqrt(n),
        "df": float(n - 1),
    }


def _lower_tost(
    estimate: float,
    *,
    lower_bound: float,
    standard_error: float,
    df: float,
    alpha: float,
) -> dict[str, object]:
    statistic = (estimate - lower_bound) / standard_error
    p_value = _clamp_probability(float(stats.t.sf(statistic, df)))
    return {
        "bound": lower_bound,
        "null_hypothesis": "estimate_less_than_or_equal_lower_bound",
        "alternative": "estimate_greater_than_lower_bound",
        "statistic": statistic,
        "df": df,
        "p_value": p_value,
        "reject_null": p_value < alpha,
    }


def _upper_tost(
    estimate: float,
    *,
    upper_bound: float,
    standard_error: float,
    df: float,
    alpha: float,
) -> dict[str, object]:
    statistic = (estimate - upper_bound) / standard_error
    p_value = _clamp_probability(float(stats.t.cdf(statistic, df)))
    return {
        "bound": upper_bound,
        "null_hypothesis": "estimate_greater_than_or_equal_upper_bound",
        "alternative": "estimate_less_than_upper_bound",
        "statistic": statistic,
        "df": df,
        "p_value": p_value,
        "reject_null": p_value < alpha,
    }


def _confidence_interval(
    estimate: float,
    *,
    standard_error: float,
    df: float,
    alpha: float,
    lower_bound: float,
    upper_bound: float,
) -> dict[str, object]:
    confidence_level = 1.0 - (2.0 * alpha)
    critical = float(stats.t.ppf(1.0 - alpha, df))
    lower = estimate - critical * standard_error
    upper = estimate + critical * standard_error
    return {
        "level": confidence_level,
        "lower": lower,
        "upper": upper,
        "inside_equivalence_bounds": lower >= lower_bound and upper <= upper_bound,
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
        "equivalence_tost_design_assumption",
        "equivalence_bounds_user_defined",
        "non_significance_is_not_equivalence",
    ]
    if n_missing > 0:
        warnings.append("missing_values_excluded")
    if n_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    return warnings
