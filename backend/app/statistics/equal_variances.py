from __future__ import annotations

import importlib.metadata
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from itertools import combinations
from math import exp, fsum, isfinite, log, sqrt
from statistics import median

from scipy import stats  # type: ignore[import-untyped]
from scipy.optimize import brentq  # type: ignore[import-untyped]

MIN_GROUPS = 2
MIN_GROUP_N = 2
MIN_MULTIPLE_COMPARISON_GROUP_N = 10
GROUP_LABEL_MAX_LENGTH = 120


@dataclass(frozen=True)
class EqualVarianceResponseColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class EqualVarianceGroupColumn:
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


def calculate_equal_variances(
    rows: Iterable[Sequence[str | None]],
    response_column: EqualVarianceResponseColumn,
    group_column: EqualVarianceGroupColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
) -> dict[str, object]:
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

    n_used = sum(len(group.values) for group in groups.values())
    group_list = list(groups.values())
    multiple_comparisons = _multiple_comparisons(group_list, alpha=alpha)
    comparison_groups = multiple_comparisons.get("groups")
    if not isinstance(comparison_groups, list):
        comparison_groups = []
    intervals_by_label = {
        str(group["group_label"]): group.get("comparison_interval")
        for group in comparison_groups
        if isinstance(group, dict)
    }
    group_summaries = [
        {
            **_group_summary(group),
            "comparison_interval": intervals_by_label.get(group.group_label),
        }
        for group in group_list
    ]
    result_warnings = _result_warnings(
        n_excluded_missing_response=n_excluded_missing_response,
        n_excluded_missing_group=n_excluded_missing_group,
        n_excluded_non_numeric_response=n_excluded_non_numeric_response,
        groups=group_list,
    )

    levene = _levene_test(
        group_list,
        alpha=alpha,
        method="levene_brown_forsythe",
        center="median",
    )
    mean_centered = _levene_test(
        group_list,
        alpha=alpha,
        method="classical_levene_mean_centered",
        center="mean",
    )

    return {
        "schema_version": 2,
        "summary_type": "equal_variances_test",
        "missing_policy": "complete_case",
        "alpha": alpha,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": result_warnings,
        "response": _column_payload(response_column),
        "group": _column_payload(group_column),
        "n_total": n_total,
        "n_used": n_used,
        "n_excluded_missing_response": n_excluded_missing_response,
        "n_excluded_missing_group": n_excluded_missing_group,
        "n_excluded_non_numeric_response": n_excluded_non_numeric_response,
        "group_count": len(groups),
        "groups": group_summaries,
        "multiple_comparisons": multiple_comparisons,
        "levene": levene,
        "additional_tests": [mean_centered],
        "tests": [
            {
                "method": "multiple_comparisons",
                "center": "not_applicable",
                "computed": multiple_comparisons["computed"],
                "statistic": None,
                "p_value": multiple_comparisons["p_value"],
                "alpha": alpha,
                "reject_equal_variances": multiple_comparisons["reject_equal_variances"],
                "valid_group_n_min": MIN_MULTIPLE_COMPARISON_GROUP_N,
                "warnings": multiple_comparisons["warnings"],
            },
            levene,
        ],
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
    column: EqualVarianceResponseColumn | EqualVarianceGroupColumn,
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
        "median": median(values) if values else None,
        "variance": _sample_variance(values),
        "std": _sample_std(values),
        "min": values[0] if values else None,
        "max": values[-1] if values else None,
        "warnings": _group_warnings(values),
    }


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return fsum(values) / len(values)


def _sample_variance(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = fsum(values) / len(values)
    return fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def _sample_std(values: Sequence[float]) -> float | None:
    variance = _sample_variance(values)
    if variance is None:
        return None
    return sqrt(variance)


def _group_warnings(values: Sequence[float]) -> list[str]:
    warnings: list[str] = []
    if len(values) < MIN_GROUP_N:
        warnings.append("equal_variances_group_n_too_small")
    elif values[0] == values[-1]:
        warnings.append("constant_group")
    return warnings


def _result_warnings(
    *,
    n_excluded_missing_response: int,
    n_excluded_missing_group: int,
    n_excluded_non_numeric_response: int,
    groups: Iterable[_GroupAccumulator],
) -> list[str]:
    warnings = ["equal_variances_not_method_switch"]
    group_list = list(groups)
    if n_excluded_missing_response > 0 or n_excluded_missing_group > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_response > 0:
        warnings.append("non_numeric_values_excluded")
    if len(group_list) < MIN_GROUPS:
        warnings.append("equal_variances_insufficient_groups")
    if any(len(group.values) < MIN_GROUP_N for group in group_list):
        warnings.append("equal_variances_group_n_too_small")
    if _all_used_values_constant(group_list):
        warnings.append("constant_response")
    return warnings


def _all_used_values_constant(groups: Sequence[_GroupAccumulator]) -> bool:
    values = [value for group in groups for value in group.values]
    return bool(values) and min(values) == max(values)


def _multiple_comparisons(
    groups: Sequence[_GroupAccumulator], *, alpha: float
) -> dict[str, object]:
    payload: dict[str, object] = {
        "computed": False,
        "method": "bonett_nakayama_multiple_comparisons",
        "alpha": alpha,
        "p_value": None,
        "reject_equal_variances": None,
        "groups": [],
        "non_overlapping_pairs": [],
        "pairwise_p_values": [],
        "warnings": [],
    }
    if len(groups) < MIN_GROUPS:
        payload["warnings"] = ["equal_variances_insufficient_groups"]
        return payload
    if _all_used_values_constant(groups):
        payload["warnings"] = ["constant_response"]
        return payload
    if any(len(group.values) < MIN_MULTIPLE_COMPARISON_GROUP_N for group in groups):
        payload["warnings"] = ["multiple_comparisons_group_n_too_small"]
        return payload
    standard_deviations: list[float] = []
    for group in groups:
        standard_deviation = _sample_std(group.values)
        if standard_deviation is None or standard_deviation <= 0:
            payload["warnings"] = ["multiple_comparisons_requires_positive_standard_deviation"]
            return payload
        standard_deviations.append(standard_deviation)

    pair_scales: dict[tuple[int, int], float] = {}
    for left_index, right_index in combinations(range(len(groups)), 2):
        scale = _bonett_pair_scale(groups[left_index].values, groups[right_index].values)
        if scale is None or scale <= 0 or not isfinite(scale):
            payload["warnings"] = ["multiple_comparisons_scale_unavailable"]
            return payload
        pair_scales[(left_index, right_index)] = scale

    two_group_components = (
        _bonett_pair_components(groups[0].values, groups[1].values) if len(groups) == 2 else None
    )
    allocation = _comparison_interval_allocations(
        pair_scales,
        len(groups),
        two_group_components=two_group_components,
    )
    if allocation is None or any(value <= 0 or not isfinite(value) for value in allocation):
        payload["warnings"] = ["multiple_comparisons_interval_allocation_unavailable"]
        return payload

    critical_value = _multiple_comparison_critical_value(alpha, len(groups))
    z_alpha = float(stats.norm.ppf(1 - alpha / 2))
    group_payloads: list[dict[str, object]] = []
    for index, group in enumerate(groups):
        standard_deviation = standard_deviations[index]
        correction = len(group.values) / (len(group.values) - z_alpha)
        exponent = (
            critical_value * allocation[index] / 2
            if len(groups) == 2
            else critical_value * allocation[index] / sqrt(2)
        )
        center = standard_deviation * sqrt(correction)
        group_payloads.append(
            {
                "group_label": group.group_label,
                "group_index": group.group_index,
                "n": len(group.values),
                "sample_standard_deviation": standard_deviation,
                "comparison_interval": {
                    "lower": center * exp(-exponent),
                    "upper": center * exp(exponent),
                },
                "allocation": allocation[index],
            }
        )

    non_overlapping_pairs: list[dict[str, str]] = []
    pairwise_p_values: list[dict[str, object]] = []
    pairwise_p_value_numbers: list[float] = []
    for (left_index, right_index), scale in pair_scales.items():
        left = group_payloads[left_index]
        right = group_payloads[right_index]
        left_interval = left["comparison_interval"]
        right_interval = right["comparison_interval"]
        assert isinstance(left_interval, dict)
        assert isinstance(right_interval, dict)
        if float(left_interval["upper"]) < float(right_interval["lower"]) or float(
            right_interval["upper"]
        ) < float(left_interval["lower"]):
            non_overlapping_pairs.append(
                {
                    "left_group": groups[left_index].group_label,
                    "right_group": groups[right_index].group_label,
                }
            )
        pairwise_p_value = _bonett_pair_adjusted_p_value(
            groups[left_index].values,
            groups[right_index].values,
            scale=scale,
            group_count=len(groups),
        )
        pairwise_p_value_numbers.append(pairwise_p_value)
        pairwise_p_values.append(
            {
                "left_group": groups[left_index].group_label,
                "right_group": groups[right_index].group_label,
                "p_value": pairwise_p_value,
            }
        )
    p_value = min(pairwise_p_value_numbers)
    payload.update(
        {
            "computed": True,
            "p_value": p_value,
            "reject_equal_variances": p_value < alpha,
            "groups": group_payloads,
            "non_overlapping_pairs": non_overlapping_pairs,
            "pairwise_p_values": pairwise_p_values,
            "warnings": [],
        }
    )
    return payload


def _bonett_pair_scale(left_values: Sequence[float], right_values: Sequence[float]) -> float | None:
    components = _bonett_pair_components(left_values, right_values)
    if components is None:
        return None
    return sqrt(components[0] + components[1])


def _bonett_pair_components(
    left_values: Sequence[float], right_values: Sequence[float]
) -> tuple[float, float] | None:
    left_n = len(left_values)
    right_n = len(right_values)
    left_variance = _sample_variance(left_values)
    right_variance = _sample_variance(right_values)
    if left_variance is None or right_variance is None or left_variance <= 0 or right_variance <= 0:
        return None
    left_trim = 1 / (2 * sqrt(left_n) - 4)
    right_trim = 1 / (2 * sqrt(right_n) - 4)
    if not 0 <= left_trim < 0.5 or not 0 <= right_trim < 0.5:
        return None
    left_center = float(stats.trim_mean(left_values, proportiontocut=left_trim))
    right_center = float(stats.trim_mean(right_values, proportiontocut=right_trim))
    fourth_moment = fsum((value - left_center) ** 4 for value in left_values) + fsum(
        (value - right_center) ** 4 for value in right_values
    )
    squared_deviation_sum = (left_n - 1) * left_variance + (right_n - 1) * right_variance
    if squared_deviation_sum <= 0:
        return None
    pooled_kurtosis = (left_n + right_n) * fourth_moment / squared_deviation_sum**2
    left_r = (left_n - 3) / left_n
    right_r = (right_n - 3) / right_n
    left_component = (pooled_kurtosis - left_r) / (left_n - 1)
    right_component = (pooled_kurtosis - right_r) / (right_n - 1)
    if left_component <= 0 or right_component <= 0:
        return None
    return left_component, right_component


def _comparison_interval_allocations(
    pair_scales: dict[tuple[int, int], float],
    group_count: int,
    *,
    two_group_components: tuple[float, float] | None,
) -> list[float] | None:
    if group_count == 2:
        if two_group_components is None:
            return None
        pair_scale = pair_scales[(0, 1)]
        left_root = sqrt(two_group_components[0])
        right_root = sqrt(two_group_components[1])
        root_sum = left_root + right_root
        return [pair_scale * left_root / root_sum, pair_scale * right_root / root_sum]
    pair_total = fsum(pair_scales.values())
    denominator = (group_count - 1) * (group_count - 2)
    if denominator <= 0:
        return None
    allocations = []
    for index in range(group_count):
        incident = fsum(scale for pair, scale in pair_scales.items() if index in pair)
        allocations.append(((group_count - 1) * incident - pair_total) / denominator)
    return allocations


def _multiple_comparison_critical_value(alpha: float, group_count: int) -> float:
    if group_count == 2:
        return float(stats.norm.ppf(1 - alpha / 2))
    return float(stats.studentized_range.ppf(1 - alpha, group_count, float("inf")))


def _bonett_pair_adjusted_p_value(
    left_values: Sequence[float],
    right_values: Sequence[float],
    *,
    scale: float,
    group_count: int,
) -> float:
    left_variance = _sample_variance(left_values)
    right_variance = _sample_variance(right_values)
    assert left_variance is not None and right_variance is not None

    def threshold_difference(candidate_alpha: float) -> float:
        z_value = float(stats.norm.ppf(1 - candidate_alpha / 2))
        left_correction = len(left_values) / (len(left_values) - z_value)
        right_correction = len(right_values) / (len(right_values) - z_value)
        if left_correction <= 0 or right_correction <= 0:
            return float("-inf")
        observed = abs(
            log(left_correction * left_variance) - log(right_correction * right_variance)
        )
        critical = _multiple_comparison_critical_value(candidate_alpha, group_count)
        divisor = 1 if group_count == 2 else sqrt(2)
        return observed - critical * scale / divisor

    lower = 1e-10
    upper = min(
        0.999999, 2 * (1 - float(stats.norm.cdf(4 / min(len(left_values), len(right_values)))))
    )
    upper = max(0.999, upper)
    lower_value = threshold_difference(lower)
    upper_value = threshold_difference(upper)
    if lower_value >= 0:
        return 0.0
    if upper_value <= 0:
        return 1.0
    return float(brentq(threshold_difference, lower, upper, xtol=1e-12, rtol=1e-12))


def _levene_test(
    groups: Iterable[_GroupAccumulator],
    *,
    alpha: float,
    method: str,
    center: str,
) -> dict[str, object]:
    group_list = list(groups)
    payload: dict[str, object] = {
        "method": method,
        "center": center,
        "computed": False,
        "statistic": None,
        "p_value": None,
        "alpha": alpha,
        "reject_equal_variances": None,
        "valid_group_n_min": MIN_GROUP_N,
        "warnings": [],
    }
    warnings_for_test: list[str] = []
    if len(group_list) < MIN_GROUPS:
        warnings_for_test.append("equal_variances_insufficient_groups")
    if any(len(group.values) < MIN_GROUP_N for group in group_list):
        warnings_for_test.append("equal_variances_group_n_too_small")
    if _all_used_values_constant(group_list):
        warnings_for_test.append("constant_response")
    if warnings_for_test:
        payload["warnings"] = warnings_for_test
        return payload

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        statistic, p_value = stats.levene(
            *[group.values for group in group_list],
            center=center,
        )
    statistic_float = float(statistic)
    p_value_float = float(p_value)
    if not isfinite(statistic_float) or not isfinite(p_value_float):
        payload["warnings"] = ["equal_variances_statistic_not_finite"]
        return payload

    payload.update(
        {
            "computed": True,
            "statistic": statistic_float,
            "p_value": p_value_float,
            "reject_equal_variances": p_value_float < alpha,
            "warnings": [],
        },
    )
    return payload
