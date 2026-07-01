from __future__ import annotations

import importlib.metadata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite, sqrt
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

GROUP_LABEL_MAX_LENGTH = 120
MIN_GROUP_N = 1
POSTHOC_METHODS = {"dunn_holm", "none"}
POSTHOC_POLICIES = {"after_significant"}


class KruskalWallisError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class KruskalWallisResponseColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class KruskalWallisGroupColumn:
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


def calculate_kruskal_wallis(
    rows: Iterable[Sequence[str | None]],
    response_column: KruskalWallisResponseColumn,
    group_column: KruskalWallisGroupColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    posthoc_method: str = "dunn_holm",
    posthoc_policy: str = "after_significant",
) -> dict[str, object]:
    if posthoc_method not in POSTHOC_METHODS:
        raise KruskalWallisError("invalid_kruskal_wallis_posthoc_method")
    if posthoc_policy not in POSTHOC_POLICIES:
        raise KruskalWallisError("invalid_kruskal_wallis_posthoc_policy")

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
    if len(group_list) < 3:
        raise KruskalWallisError("kruskal_wallis_requires_at_least_three_groups")
    if any(len(group.values) < MIN_GROUP_N for group in group_list):
        raise KruskalWallisError("kruskal_wallis_group_n_too_small")

    all_values = [value for group in group_list for value in group.values]
    if len(set(all_values)) == 1:
        raise KruskalWallisError("kruskal_wallis_all_values_identical")
    ranks_by_group = _rank_summaries(group_list)
    has_ties = len(set(all_values)) != len(all_values)
    tie_correction = _tie_correction(all_values)
    test = _test_result(
        group_list,
        alpha=alpha,
        tie_correction=tie_correction,
    )
    posthoc = _posthoc_result(
        group_list,
        ranks_by_group,
        alpha=alpha,
        posthoc_method=posthoc_method,
        posthoc_policy=posthoc_policy,
        overall_reject=bool(test["reject_null"]),
        tie_correction=tie_correction,
    )

    return {
        "schema_version": 1,
        "summary_type": "kruskal_wallis_test",
        "method": "kruskal_wallis",
        "missing_policy": "complete_case",
        "alpha": alpha,
        "posthoc_method": posthoc_method,
        "posthoc_policy": posthoc_policy,
        "tie_correction": tie_correction,
        "has_ties": has_ties,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            groups=group_list,
            has_ties=has_ties,
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
        "groups": [
            _group_summary(group, ranks_by_group[group.group_index]) for group in group_list
        ],
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
    column: KruskalWallisResponseColumn | KruskalWallisGroupColumn,
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


def _rank_summaries(group_list: Sequence[_GroupAccumulator]) -> dict[int, dict[str, float]]:
    values: list[float] = []
    group_indexes: list[int] = []
    for group in group_list:
        values.extend(group.values)
        group_indexes.extend([group.group_index] * len(group.values))

    ranks = stats.rankdata(values, method="average")
    rank_summary: dict[int, dict[str, float]] = {}
    for group in group_list:
        rank_summary[group.group_index] = {"rank_sum": 0.0, "mean_rank": 0.0}
    for group_index, rank in zip(group_indexes, ranks, strict=True):
        rank_summary[group_index]["rank_sum"] += float(rank)
    for group in group_list:
        rank_sum = rank_summary[group.group_index]["rank_sum"]
        rank_summary[group.group_index]["mean_rank"] = rank_sum / len(group.values)
    return rank_summary


def _group_summary(
    group: _GroupAccumulator,
    ranks: dict[str, float],
) -> dict[str, object]:
    values = sorted(group.values)
    q1, q3 = _quartiles(values)
    iqr = None if q1 is None or q3 is None else q3 - q1
    return {
        "group_label": group.group_label,
        "group_index": group.group_index,
        "n": len(values),
        "mean": _mean(values),
        "median": median(values),
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "min": values[0],
        "max": values[-1],
        "rank_sum": ranks["rank_sum"],
        "mean_rank": ranks["mean_rank"],
        "warnings": ["constant_group"] if values[0] == values[-1] else [],
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _quartiles(sorted_values: Sequence[float]) -> tuple[float | None, float | None]:
    if not sorted_values:
        return None, None
    if len(sorted_values) == 1:
        return sorted_values[0], sorted_values[0]

    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        lower_half = sorted_values[:midpoint]
        upper_half = sorted_values[midpoint:]
    else:
        lower_half = sorted_values[:midpoint]
        upper_half = sorted_values[midpoint + 1 :]

    return _median(lower_half), _median(upper_half)


def _median(sorted_values: Sequence[float]) -> float:
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2


def _test_result(
    group_list: Sequence[_GroupAccumulator],
    *,
    alpha: float,
    tie_correction: float,
) -> dict[str, object]:
    try:
        result = stats.kruskal(*(group.values for group in group_list))
    except ValueError as exc:
        if "All numbers are identical" in str(exc):
            raise KruskalWallisError("kruskal_wallis_all_values_identical") from exc
        raise
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    if not isfinite(statistic) or not isfinite(p_value):
        raise KruskalWallisError("kruskal_wallis_statistic_not_finite")

    group_count = len(group_list)
    n_used = sum(len(group.values) for group in group_list)
    df = group_count - 1
    return {
        "h_statistic": statistic,
        "df": df,
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "effect_size": {
            "epsilon_squared": _epsilon_squared(
                statistic,
                group_count=group_count,
                n_used=n_used,
            ),
            "definition": "max(0,min(1,(H-k+1)/(N-k))) using tie-corrected H",
            "tie_correction": tie_correction,
        },
    }


def _epsilon_squared(
    h_statistic: float,
    *,
    group_count: int,
    n_used: int,
) -> float | None:
    denominator = n_used - group_count
    if denominator <= 0:
        return None
    raw = (h_statistic - group_count + 1) / denominator
    return min(1.0, max(0.0, raw))


def _posthoc_result(
    group_list: Sequence[_GroupAccumulator],
    ranks_by_group: dict[int, dict[str, float]],
    *,
    alpha: float,
    posthoc_method: str,
    posthoc_policy: str,
    overall_reject: bool,
    tie_correction: float,
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
            "method": "dunn",
            "multiplicity_method": "holm",
            "policy": posthoc_policy,
            "performed": False,
            "reason": "overall_not_significant",
            "comparisons": [],
        }

    comparisons = _dunn_comparisons(
        group_list,
        ranks_by_group,
        alpha=alpha,
        tie_correction=tie_correction,
    )
    return {
        "method": "dunn",
        "multiplicity_method": "holm",
        "policy": posthoc_policy,
        "performed": True,
        "reason": None,
        "comparisons": comparisons,
    }


def _dunn_comparisons(
    group_list: Sequence[_GroupAccumulator],
    ranks_by_group: dict[int, dict[str, float]],
    *,
    alpha: float,
    tie_correction: float,
) -> list[dict[str, object]]:
    n_used = sum(len(group.values) for group in group_list)
    rank_variance = (n_used * (n_used + 1) / 12.0) * tie_correction
    if rank_variance <= 0.0 or not isfinite(rank_variance):
        raise KruskalWallisError("kruskal_wallis_posthoc_variance_zero")

    raw_comparisons: list[dict[str, object]] = []
    raw_p_values: list[float] = []
    for left_index, left in enumerate(group_list):
        for right in group_list[left_index + 1 :]:
            mean_rank_left = ranks_by_group[left.group_index]["mean_rank"]
            mean_rank_right = ranks_by_group[right.group_index]["mean_rank"]
            standard_error = sqrt(
                rank_variance * ((1.0 / len(left.values)) + (1.0 / len(right.values)))
            )
            if standard_error <= 0.0 or not isfinite(standard_error):
                raise KruskalWallisError("kruskal_wallis_posthoc_variance_zero")
            z_statistic = (mean_rank_left - mean_rank_right) / standard_error
            raw_p_value = float(2.0 * stats.norm.sf(abs(z_statistic)))
            raw_p_values.append(raw_p_value)
            raw_comparisons.append(
                {
                    "group_1_label": left.group_label,
                    "group_2_label": right.group_label,
                    "mean_rank_difference": mean_rank_left - mean_rank_right,
                    "standard_error": standard_error,
                    "z_statistic": z_statistic,
                    "raw_p_value": raw_p_value,
                },
            )

    adjusted = _holm_adjusted_p_values(raw_p_values)
    comparisons: list[dict[str, object]] = []
    for comparison, adjusted_p_value in zip(raw_comparisons, adjusted, strict=True):
        comparisons.append(
            {
                **comparison,
                "adjusted_p_value": adjusted_p_value,
                "reject_holm": adjusted_p_value < alpha,
            },
        )
    return comparisons


def _holm_adjusted_p_values(p_values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0 for _ in p_values]
    running_max = 0.0
    total = len(p_values)
    for rank, (original_index, p_value) in enumerate(indexed):
        candidate = min(1.0, (total - rank) * p_value)
        running_max = max(running_max, candidate)
        adjusted[original_index] = running_max
    return adjusted


def _tie_correction(values: Sequence[float]) -> float:
    n_total = len(values)
    if n_total < 2:
        return 1.0
    tie_sum = fsum((count**3) - count for count in Counter(values).values() if count > 1)
    denominator = (n_total**3) - n_total
    if denominator <= 0:
        return 1.0
    return 1.0 - (tie_sum / denominator)


def _result_warnings(
    *,
    groups: Sequence[_GroupAccumulator],
    has_ties: bool,
    posthoc: dict[str, object],
    n_excluded_missing_response: int,
    n_excluded_missing_group: int,
    n_excluded_non_numeric_response: int,
) -> list[str]:
    warnings = [
        "kruskal_wallis_independence_assumption",
        "kruskal_wallis_not_median_test",
    ]
    if posthoc.get("performed") is True:
        warnings.append("dunn_holm_after_significant")
    if posthoc.get("reason") == "overall_not_significant":
        warnings.append("posthoc_skipped_overall_not_significant")
    if has_ties:
        warnings.append("kruskal_wallis_ties_detected")
    if _has_group_size_imbalance(groups):
        warnings.append("group_size_imbalance")
    if any(len(group.values) < 5 for group in groups):
        warnings.append("small_group_size")
    if n_excluded_missing_response > 0 or n_excluded_missing_group > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_response > 0:
        warnings.append("non_numeric_values_excluded")
    if any(len(set(group.values)) == 1 for group in groups):
        warnings.append("constant_group")
    return warnings


def _has_group_size_imbalance(groups: Sequence[_GroupAccumulator]) -> bool:
    sizes = [len(group.values) for group in groups]
    return max(sizes) >= 4 * min(sizes)
