from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}
VARIANCE_ASSUMPTIONS = {"welch", "pooled"}
GROUP_LABEL_MAX_LENGTH = 120
MIN_GROUP_N = 2


class TwoSampleTError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TwoSampleTResponseColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class TwoSampleTGroupColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass
class _GroupAccumulator:
    group_label: str
    group_index: int
    values: list[float] = field(default_factory=list)


def calculate_two_sample_t(
    rows: Iterable[Sequence[str | None]],
    response_column: TwoSampleTResponseColumn,
    group_column: TwoSampleTGroupColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    alternative: str = "two_sided",
    variance_assumption: str = "welch",
    null_difference: float = 0.0,
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise TwoSampleTError("invalid_two_sample_t_alternative")
    if variance_assumption not in VARIANCE_ASSUMPTIONS:
        raise TwoSampleTError("invalid_two_sample_t_variance_assumption")

    groups: dict[str, _GroupAccumulator] = {}
    n_total = 0
    n_excluded_missing_response = 0
    n_excluded_missing_group = 0
    n_excluded_non_numeric_response = 0

    for row in rows:
        n_total += 1
        response_value = _row_value(row, response_column.column_index)
        group_value = _row_value(row, group_column.column_index)
        if response_value is None or response_value.strip() == "":
            n_excluded_missing_response += 1
            continue
        if group_value is None or group_value.strip() == "":
            n_excluded_missing_group += 1
            continue

        response_number = _parse_number(
            response_value,
            decimal=decimal,
            thousands=thousands,
        )
        if response_number is None:
            n_excluded_non_numeric_response += 1
            continue

        group_label = _safe_group_label(group_value)
        group = groups.get(group_label)
        if group is None:
            group = _GroupAccumulator(
                group_label=group_label,
                group_index=len(groups),
            )
            groups[group_label] = group
        group.values.append(response_number)

    group_list = list(groups.values())
    if len(group_list) != 2:
        raise TwoSampleTError("two_sample_t_requires_exactly_two_groups")
    if any(len(group.values) < MIN_GROUP_N for group in group_list):
        raise TwoSampleTError("two_sample_t_group_n_too_small")

    result = _test_result(
        group_list[0],
        group_list[1],
        alpha=alpha,
        confidence_level=confidence_level,
        alternative=alternative,
        variance_assumption=variance_assumption,
        null_difference=null_difference,
    )
    return {
        "schema_version": 1,
        "summary_type": "two_sample_t_test",
        "method": "welch_two_sample_t" if variance_assumption == "welch" else "student_t_test",
        "variance_assumption": variance_assumption,
        "missing_policy": "complete_case",
        "alternative": alternative,
        "alpha": alpha,
        "confidence_level": confidence_level,
        "null_difference": null_difference,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            groups=group_list,
            variance_assumption=variance_assumption,
            n_excluded_missing_response=n_excluded_missing_response,
            n_excluded_missing_group=n_excluded_missing_group,
            n_excluded_non_numeric_response=n_excluded_non_numeric_response,
        ),
        "response": _column_payload(response_column),
        "group": _column_payload(group_column),
        "n_total": n_total,
        "n_used": sum(len(group.values) for group in group_list),
        "n_excluded_missing_response": n_excluded_missing_response,
        "n_excluded_missing_group": n_excluded_missing_group,
        "n_excluded_non_numeric_response": n_excluded_non_numeric_response,
        "group_count": len(group_list),
        "groups": [_group_summary(group) for group in group_list],
        "contrast": result,
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


def _safe_group_label(value: str) -> str:
    stripped = value.strip()
    if len(stripped) <= GROUP_LABEL_MAX_LENGTH:
        return stripped
    return f"{stripped[: GROUP_LABEL_MAX_LENGTH - 3]}..."


def _column_payload(
    column: TwoSampleTResponseColumn | TwoSampleTGroupColumn,
) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _group_summary(group: _GroupAccumulator) -> dict[str, object]:
    values = sorted(group.values)
    return {
        "group_label": group.group_label,
        "group_index": group.group_index,
        "n": len(values),
        "mean": _mean(values),
        "median": median(values),
        "variance": _sample_variance(values),
        "std": _sample_std(values),
        "min": values[0],
        "max": values[-1],
        "warnings": ["constant_group"] if values[0] == values[-1] else [],
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _sample_variance(values: Sequence[float]) -> float:
    mean = _mean(values)
    return fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values: Sequence[float]) -> float:
    return sqrt(_sample_variance(values))


def _test_result(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    *,
    alpha: float,
    confidence_level: float,
    alternative: str,
    variance_assumption: str,
    null_difference: float,
) -> dict[str, object]:
    values_1 = group_1.values
    values_2 = group_2.values
    n_1 = len(values_1)
    n_2 = len(values_2)
    mean_1 = _mean(values_1)
    mean_2 = _mean(values_2)
    variance_1 = _sample_variance(values_1)
    variance_2 = _sample_variance(values_2)
    estimate = mean_1 - mean_2
    pooled_variance = _pooled_variance(variance_1, variance_2, n_1=n_1, n_2=n_2)

    if variance_assumption == "welch":
        standard_error = sqrt((variance_1 / n_1) + (variance_2 / n_2))
        df = _welch_df(variance_1, variance_2, n_1=n_1, n_2=n_2)
    else:
        standard_error = sqrt(pooled_variance * ((1.0 / n_1) + (1.0 / n_2)))
        df = float(n_1 + n_2 - 2)

    if standard_error <= 0.0 or df <= 0.0 or not isfinite(standard_error) or not isfinite(df):
        raise TwoSampleTError("two_sample_t_standard_error_zero")

    statistic = (estimate - null_difference) / standard_error
    p_value = _p_value(statistic, df=df, alternative=alternative)
    ci = _confidence_interval(
        estimate,
        standard_error=standard_error,
        df=df,
        confidence_level=confidence_level,
        alternative=alternative,
    )
    effect_size = _effect_size(
        estimate,
        pooled_variance=pooled_variance,
        n_1=n_1,
        n_2=n_2,
    )
    return {
        "group_1_label": group_1.group_label,
        "group_2_label": group_2.group_label,
        "estimate": estimate,
        "estimate_definition": "group_1_mean_minus_group_2_mean",
        "null_difference": null_difference,
        "standard_error": standard_error,
        "statistic": statistic,
        "df": df,
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "confidence_interval": ci,
        "effect_size": effect_size,
    }


def _pooled_variance(variance_1: float, variance_2: float, *, n_1: int, n_2: int) -> float:
    return (((n_1 - 1) * variance_1) + ((n_2 - 1) * variance_2)) / (n_1 + n_2 - 2)


def _welch_df(variance_1: float, variance_2: float, *, n_1: int, n_2: int) -> float:
    term_1 = variance_1 / n_1
    term_2 = variance_2 / n_2
    numerator = (term_1 + term_2) ** 2
    denominator = (term_1**2 / (n_1 - 1)) + (term_2**2 / (n_2 - 1))
    if denominator <= 0.0:
        raise TwoSampleTError("two_sample_t_standard_error_zero")
    return numerator / denominator


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


def _effect_size(
    estimate: float,
    *,
    pooled_variance: float,
    n_1: int,
    n_2: int,
) -> dict[str, object]:
    pooled_std = sqrt(pooled_variance) if pooled_variance > 0.0 else 0.0
    df = n_1 + n_2 - 2
    if pooled_std <= 0.0 or df <= 1:
        return {
            "standardizer": "pooled_sample_sd",
            "cohen_d": None,
            "hedges_g": None,
            "hedges_correction": None,
        }
    cohen_d = estimate / pooled_std
    correction = 1.0 - (3.0 / ((4.0 * df) - 1.0))
    return {
        "standardizer": "pooled_sample_sd",
        "cohen_d": cohen_d,
        "hedges_g": cohen_d * correction,
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
    groups: Sequence[_GroupAccumulator],
    variance_assumption: str,
    n_excluded_missing_response: int,
    n_excluded_missing_group: int,
    n_excluded_non_numeric_response: int,
) -> list[str]:
    warnings = [
        "two_sample_t_independence_assumption",
        "two_sample_t_not_auto_switched",
    ]
    if variance_assumption == "pooled":
        warnings.append("pooled_variance_assumption_selected")
    if n_excluded_missing_response > 0 or n_excluded_missing_group > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_response > 0:
        warnings.append("non_numeric_values_excluded")
    if any(min(group.values) == max(group.values) for group in groups):
        warnings.append("constant_group")
    group_sizes = [len(group.values) for group in groups]
    if max(group_sizes) / min(group_sizes) >= 4.0:
        warnings.append("group_size_imbalance")
    return warnings
