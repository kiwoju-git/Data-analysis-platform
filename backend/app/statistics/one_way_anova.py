from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median
from typing import cast

from scipy import stats  # type: ignore[import-untyped]

ANOVA_TYPES = {"standard"}
GROUP_LABEL_MAX_LENGTH = 120
MIN_GROUP_N = 2
POSTHOC_METHODS = {"tukey_kramer", "none"}
POSTHOC_POLICIES = {"after_significant"}


class OneWayAnovaError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OneWayAnovaResponseColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class OneWayAnovaGroupColumn:
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


def calculate_one_way_anova(
    rows: Iterable[Sequence[str | None]],
    response_column: OneWayAnovaResponseColumn,
    group_column: OneWayAnovaGroupColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    anova_type: str = "standard",
    posthoc_method: str = "tukey_kramer",
    posthoc_policy: str = "after_significant",
) -> dict[str, object]:
    if anova_type not in ANOVA_TYPES:
        raise OneWayAnovaError("invalid_one_way_anova_type")
    if posthoc_method not in POSTHOC_METHODS:
        raise OneWayAnovaError("invalid_one_way_anova_posthoc_method")
    if posthoc_policy not in POSTHOC_POLICIES:
        raise OneWayAnovaError("invalid_one_way_anova_posthoc_policy")
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise OneWayAnovaError("invalid_one_way_anova_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise OneWayAnovaError("invalid_one_way_anova_confidence_level")

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
    if len(group_list) < 2:
        raise OneWayAnovaError("one_way_anova_requires_at_least_two_groups")
    if any(len(group.values) < MIN_GROUP_N for group in group_list):
        raise OneWayAnovaError("one_way_anova_group_n_too_small")

    anova_table = _anova_table(group_list)
    test = _test_result(anova_table, alpha=alpha)
    posthoc = _posthoc_result(
        group_list,
        anova_table,
        alpha=alpha,
        confidence_level=confidence_level,
        posthoc_method=posthoc_method,
        posthoc_policy=posthoc_policy,
        overall_reject=bool(test["reject_null"]),
    )

    return {
        "schema_version": 1,
        "summary_type": "one_way_anova",
        "method": "standard_one_way_anova",
        "anova_type": anova_type,
        "missing_policy": "complete_case",
        "alpha": alpha,
        "confidence_level": confidence_level,
        "posthoc_method": posthoc_method,
        "posthoc_policy": posthoc_policy,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            groups=group_list,
            test=test,
            posthoc=posthoc,
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
        "groups": [_group_summary(group, confidence_level) for group in group_list],
        "anova_table": anova_table,
        "test": test,
        "posthoc": posthoc,
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
    column: OneWayAnovaResponseColumn | OneWayAnovaGroupColumn,
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


def _group_summary(
    group: _GroupAccumulator,
    confidence_level: float,
) -> dict[str, object]:
    values = sorted(group.values)
    n = len(values)
    mean = _mean(values)
    variance = _sample_variance(values)
    std = sqrt(variance)
    sem = std / sqrt(n)
    confidence_interval = _mean_confidence_interval(
        mean,
        sem,
        df=n - 1,
        confidence_level=confidence_level,
    )
    return {
        "group_label": group.group_label,
        "group_index": group.group_index,
        "n": n,
        "mean": mean,
        "median": median(values),
        "variance": variance,
        "std": std,
        "sem": sem,
        "min": values[0],
        "max": values[-1],
        "mean_confidence_interval": confidence_interval,
        "warnings": ["constant_group"] if values[0] == values[-1] else [],
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _sample_variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = _mean(values)
    return fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _mean_confidence_interval(
    mean: float,
    sem: float,
    *,
    df: int,
    confidence_level: float,
) -> dict[str, object]:
    alpha = 1.0 - confidence_level
    critical = float(stats.t.ppf(1.0 - (alpha / 2.0), df))
    margin = critical * sem
    return {
        "method": "t",
        "level": confidence_level,
        "lower": mean - margin,
        "upper": mean + margin,
    }


def _anova_table(group_list: Sequence[_GroupAccumulator]) -> dict[str, object]:
    all_values = [value for group in group_list for value in group.values]
    grand_mean = _mean(all_values)
    group_count = len(group_list)
    n_used = len(all_values)
    ss_between = fsum(
        len(group.values) * ((_mean(group.values) - grand_mean) ** 2) for group in group_list
    )
    ss_within = fsum(
        fsum((value - _mean(group.values)) ** 2 for value in group.values) for group in group_list
    )
    ss_total = ss_between + ss_within
    if ss_total <= 0.0:
        raise OneWayAnovaError("one_way_anova_all_values_identical")
    df_between = group_count - 1
    df_within = n_used - group_count
    df_total = n_used - 1
    if df_between <= 0 or df_within <= 0:
        raise OneWayAnovaError("one_way_anova_degrees_of_freedom_invalid")
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    if ms_within <= 0.0:
        raise OneWayAnovaError("one_way_anova_zero_residual_variance")
    f_statistic = ms_between / ms_within
    p_value = float(stats.f.sf(f_statistic, df_between, df_within))
    if not isfinite(f_statistic) or not isfinite(p_value):
        raise OneWayAnovaError("one_way_anova_statistic_not_finite")
    eta_squared = ss_between / ss_total
    omega_squared = (ss_between - (df_between * ms_within)) / (ss_total + ms_within)
    return {
        "grand_mean": grand_mean,
        "rows": [
            {
                "source": "between_groups",
                "sum_squares": ss_between,
                "df": df_between,
                "mean_square": ms_between,
            },
            {
                "source": "within_groups",
                "sum_squares": ss_within,
                "df": df_within,
                "mean_square": ms_within,
            },
            {
                "source": "total",
                "sum_squares": ss_total,
                "df": df_total,
                "mean_square": None,
            },
        ],
        "ss_between": ss_between,
        "ss_within": ss_within,
        "ss_total": ss_total,
        "df_between": df_between,
        "df_within": df_within,
        "df_total": df_total,
        "ms_between": ms_between,
        "ms_within": ms_within,
        "f_statistic": f_statistic,
        "p_value": p_value,
        "effect_size": {
            "eta_squared": eta_squared,
            "omega_squared": omega_squared,
            "definition": (
                "eta_squared=SS_between/SS_total; "
                "omega_squared=(SS_between-df_between*MSE)/(SS_total+MSE)"
            ),
        },
    }


def _test_result(
    anova_table: dict[str, object],
    *,
    alpha: float,
) -> dict[str, object]:
    p_value = cast(float, anova_table["p_value"])
    return {
        "f_statistic": cast(float, anova_table["f_statistic"]),
        "df_between": cast(int, anova_table["df_between"]),
        "df_within": cast(int, anova_table["df_within"]),
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "effect_size": anova_table["effect_size"],
    }


def _posthoc_result(
    group_list: Sequence[_GroupAccumulator],
    anova_table: dict[str, object],
    *,
    alpha: float,
    confidence_level: float,
    posthoc_method: str,
    posthoc_policy: str,
    overall_reject: bool,
) -> dict[str, object]:
    if posthoc_method == "none":
        return {
            "method": "none",
            "multiplicity_method": None,
            "policy": posthoc_policy,
            "performed": False,
            "reason": "not_requested",
            "comparisons": [],
        }
    if not overall_reject:
        return {
            "method": "tukey_kramer",
            "multiplicity_method": "tukey_familywise",
            "policy": posthoc_policy,
            "performed": False,
            "reason": "overall_not_significant",
            "comparisons": [],
        }

    df_within = cast(int, anova_table["df_within"])
    ms_within = cast(float, anova_table["ms_within"])
    group_count = len(group_list)
    q_critical = float(stats.studentized_range.ppf(confidence_level, group_count, df_within))
    comparisons: list[dict[str, object]] = []
    for first_index, group_1 in enumerate(group_list):
        for group_2 in group_list[first_index + 1 :]:
            comparisons.append(
                _tukey_comparison(
                    group_1,
                    group_2,
                    ms_within=ms_within,
                    df_within=df_within,
                    group_count=group_count,
                    q_critical=q_critical,
                    alpha=alpha,
                    confidence_level=confidence_level,
                ),
            )
    return {
        "method": "tukey_kramer",
        "multiplicity_method": "tukey_familywise",
        "policy": posthoc_policy,
        "performed": True,
        "reason": None,
        "confidence_level": confidence_level,
        "q_critical": q_critical,
        "comparisons": comparisons,
    }


def _tukey_comparison(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    *,
    ms_within: float,
    df_within: int,
    group_count: int,
    q_critical: float,
    alpha: float,
    confidence_level: float,
) -> dict[str, object]:
    mean_1 = _mean(group_1.values)
    mean_2 = _mean(group_2.values)
    difference = mean_1 - mean_2
    standard_error_tukey = sqrt(
        (ms_within / 2.0) * ((1.0 / len(group_1.values)) + (1.0 / len(group_2.values)))
    )
    if standard_error_tukey <= 0.0:
        raise OneWayAnovaError("one_way_anova_posthoc_standard_error_zero")
    q_statistic = abs(difference) / standard_error_tukey
    adjusted_p_value = float(stats.studentized_range.sf(q_statistic, group_count, df_within))
    standard_error_mean_difference = sqrt(
        ms_within * ((1.0 / len(group_1.values)) + (1.0 / len(group_2.values)))
    )
    t_statistic = abs(difference) / standard_error_mean_difference
    raw_p_value = float(2.0 * stats.t.sf(t_statistic, df_within))
    margin = q_critical * standard_error_tukey
    if not all(isfinite(value) for value in [q_statistic, adjusted_p_value, raw_p_value, margin]):
        raise OneWayAnovaError("one_way_anova_posthoc_not_finite")
    return {
        "group_1_label": group_1.group_label,
        "group_2_label": group_2.group_label,
        "mean_1": mean_1,
        "mean_2": mean_2,
        "mean_difference": difference,
        "standard_error": standard_error_tukey,
        "q_statistic": q_statistic,
        "raw_p_value": raw_p_value,
        "adjusted_p_value": adjusted_p_value,
        "reject_adjusted": adjusted_p_value < alpha,
        "confidence_interval": {
            "method": "tukey_kramer",
            "level": confidence_level,
            "lower": difference - margin,
            "upper": difference + margin,
        },
    }


def _result_warnings(
    *,
    groups: Sequence[_GroupAccumulator],
    test: dict[str, object],
    posthoc: dict[str, object],
    n_excluded_missing_response: int,
    n_excluded_missing_group: int,
    n_excluded_non_numeric_response: int,
) -> list[str]:
    warnings = [
        "one_way_anova_independence_assumption",
        "one_way_anova_normality_assumption",
        "one_way_anova_equal_variance_assumption",
        "one_way_anova_not_auto_switched",
    ]
    if len(groups) == 2:
        warnings.append("two_group_anova_equivalent_to_t_test")
    if n_excluded_missing_response > 0 or n_excluded_missing_group > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_response > 0:
        warnings.append("non_numeric_values_excluded")
    if any(min(group.values) == max(group.values) for group in groups):
        warnings.append("constant_group")
    group_sizes = [len(group.values) for group in groups]
    if min(group_sizes) < 5:
        warnings.append("small_group_size")
    if max(group_sizes) / min(group_sizes) >= 4.0:
        warnings.append("group_size_imbalance")
    if posthoc.get("reason") == "overall_not_significant":
        warnings.append("posthoc_skipped_overall_not_significant")
    if posthoc.get("performed") is True:
        warnings.append("tukey_kramer_after_standard_anova")
    if bool(test["reject_null"]) is False:
        warnings.append("overall_not_significant")
    return warnings
