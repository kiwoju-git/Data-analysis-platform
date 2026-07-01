from __future__ import annotations

import importlib.metadata
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

MIN_GROUPS = 2
MIN_GROUP_N = 2
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
    group_summaries = [_group_summary(group) for group in groups.values()]
    result_warnings = _result_warnings(
        n_excluded_missing_response=n_excluded_missing_response,
        n_excluded_missing_group=n_excluded_missing_group,
        n_excluded_non_numeric_response=n_excluded_non_numeric_response,
        groups=groups.values(),
    )

    return {
        "schema_version": 1,
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
        "tests": [
            _levene_test(groups.values(), alpha=alpha, method="brown_forsythe", center="median"),
            _levene_test(groups.values(), alpha=alpha, method="levene_mean", center="mean"),
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
