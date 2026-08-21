from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}
METHODS = {"auto", "exact", "asymptotic"}
GROUP_LABEL_MAX_LENGTH = 120
MIN_GROUP_N = 1


class MannWhitneyError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class MannWhitneyResponseColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class MannWhitneyGroupColumn:
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


@dataclass
class _StackedGroupAccumulator:
    raw_label: str
    display_label: str
    group_index: int
    n_total: int = 0
    n_excluded_missing: int = 0
    n_excluded_non_numeric: int = 0
    values: list[float] = field(default_factory=list)


def calculate_mann_whitney(
    rows: Iterable[Sequence[str | None]],
    response_column: MannWhitneyResponseColumn,
    group_column: MannWhitneyGroupColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    alternative: str = "two_sided",
    method: str = "auto",
    group_1_value: str | None = None,
    group_2_value: str | None = None,
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise MannWhitneyError("invalid_mann_whitney_alternative")
    if method not in METHODS:
        raise MannWhitneyError("invalid_mann_whitney_method")

    if (group_1_value is None) != (group_2_value is None):
        raise MannWhitneyError("mann_whitney_group_selection_incomplete")
    selected_values = None
    if group_1_value is not None and group_2_value is not None:
        selected_values = (group_1_value.strip(), group_2_value.strip())
        if selected_values[0] == selected_values[1]:
            raise MannWhitneyError("mann_whitney_groups_must_differ")

    groups: dict[str, _StackedGroupAccumulator] = {}
    n_total = 0
    n_excluded_missing_group = 0

    for row in rows:
        n_total += 1
        response_value = _row_value(row, response_column.column_index)
        group_value = _row_value(row, group_column.column_index)
        if group_value is None or group_value.strip() == "":
            n_excluded_missing_group += 1
            continue

        raw_group_label = group_value.strip()
        group = groups.get(raw_group_label)
        if group is None:
            group = _StackedGroupAccumulator(
                raw_label=raw_group_label,
                display_label=_safe_group_label(group_value),
                group_index=len(groups),
            )
            groups[raw_group_label] = group
        group.n_total += 1
        if response_value is None or response_value.strip() == "":
            group.n_excluded_missing += 1
            continue

        response_number = _parse_number(
            response_value,
            decimal=decimal,
            thousands=thousands,
        )
        if response_number is None:
            group.n_excluded_non_numeric += 1
            continue
        group.values.append(response_number)

    if selected_values is None:
        if len(groups) != 2:
            raise MannWhitneyError("mann_whitney_requires_exactly_two_groups")
        selected_stacked_groups = list(groups.values())
    else:
        try:
            selected_stacked_groups = [groups[selected_values[0]], groups[selected_values[1]]]
        except KeyError as exc:
            raise MannWhitneyError("mann_whitney_selected_group_not_found") from exc

    if len(selected_stacked_groups) != 2:
        raise MannWhitneyError("mann_whitney_requires_exactly_two_groups")
    if any(len(group.values) < MIN_GROUP_N for group in selected_stacked_groups):
        raise MannWhitneyError("mann_whitney_group_n_too_small")

    sample_groups = [
        _GroupAccumulator(
            group_label=group.display_label,
            group_index=index,
            values=list(group.values),
        )
        for index, group in enumerate(selected_stacked_groups)
    ]
    n_excluded_missing_response = sum(
        group.n_excluded_missing for group in selected_stacked_groups
    )
    n_excluded_non_numeric_response = sum(
        group.n_excluded_non_numeric for group in selected_stacked_groups
    )
    core = calculate_mann_whitney_samples(
        sample_groups[0].values,
        sample_groups[1].values,
        sample_1_label=sample_groups[0].group_label,
        sample_2_label=sample_groups[1].group_label,
        alpha=alpha,
        alternative=alternative,
        method=method,
        n_excluded_missing=n_excluded_missing_response + n_excluded_missing_group,
        n_excluded_non_numeric=n_excluded_non_numeric_response,
    )
    selected_raw_labels = {group.raw_label for group in selected_stacked_groups}
    n_excluded_unselected_groups = sum(
        group.n_total for label, group in groups.items() if label not in selected_raw_labels
    )

    return {
        "schema_version": 2,
        "summary_type": "mann_whitney_u_test",
        "method": "mann_whitney_u",
        "input_layout": "stacked",
        "missing_policy": "complete_case_selected_groups",
        "alternative": alternative,
        "alpha": alpha,
        **core,
        "response": _column_payload(response_column),
        "group": _column_payload(group_column),
        "n_total": n_total,
        "n_used": sum(len(group.values) for group in selected_stacked_groups),
        "n_excluded_missing_response": n_excluded_missing_response,
        "n_excluded_missing_group": n_excluded_missing_group,
        "n_excluded_non_numeric_response": n_excluded_non_numeric_response,
        "n_excluded_unselected_groups": n_excluded_unselected_groups,
        "selected_group_values": [group.raw_label for group in selected_stacked_groups],
        "group_count": len(sample_groups),
        "samples": [
            {
                "sample_index": index + 1,
                "label": group.display_label,
                "source_column": _column_payload(response_column),
                "source_group_value": group.raw_label,
                "n_total": group.n_total,
                "n_used": len(group.values),
                "n_excluded_missing": group.n_excluded_missing,
                "n_excluded_non_numeric": group.n_excluded_non_numeric,
            }
            for index, group in enumerate(selected_stacked_groups)
        ],
    }


def calculate_mann_whitney_unstacked(
    rows: Iterable[Sequence[str | None]],
    sample_1_column: MannWhitneyResponseColumn,
    sample_2_column: MannWhitneyResponseColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    alternative: str = "two_sided",
    method: str = "auto",
) -> dict[str, object]:
    if sample_1_column.column_id == sample_2_column.column_id:
        raise MannWhitneyError("mann_whitney_sample_columns_must_differ")

    sample_values: list[list[float]] = [[], []]
    missing_counts = [0, 0]
    non_numeric_counts = [0, 0]
    n_rows = 0
    for row in rows:
        n_rows += 1
        for index, column in enumerate((sample_1_column, sample_2_column)):
            raw_value = _row_value(row, column.column_index)
            if raw_value is None or raw_value.strip() == "":
                missing_counts[index] += 1
                continue
            parsed = _parse_number(raw_value, decimal=decimal, thousands=thousands)
            if parsed is None:
                non_numeric_counts[index] += 1
                continue
            sample_values[index].append(parsed)

    core = calculate_mann_whitney_samples(
        sample_values[0],
        sample_values[1],
        sample_1_label=sample_1_column.display_name,
        sample_2_label=sample_2_column.display_name,
        alpha=alpha,
        alternative=alternative,
        method=method,
        n_excluded_missing=sum(missing_counts),
        n_excluded_non_numeric=sum(non_numeric_counts),
    )
    columns = (sample_1_column, sample_2_column)
    return {
        "schema_version": 2,
        "summary_type": "mann_whitney_u_test",
        "method": "mann_whitney_u",
        "input_layout": "unstacked",
        "missing_policy": "available_case_by_sample",
        "alternative": alternative,
        "alpha": alpha,
        **core,
        "n_total": n_rows * 2,
        "n_used": len(sample_values[0]) + len(sample_values[1]),
        "n_excluded_missing_response": sum(missing_counts),
        "n_excluded_missing_group": 0,
        "n_excluded_non_numeric_response": sum(non_numeric_counts),
        "n_excluded_unselected_groups": 0,
        "group_count": 2,
        "samples": [
            {
                "sample_index": index + 1,
                "label": column.display_name,
                "source_column": _column_payload(column),
                "source_group_value": None,
                "n_total": n_rows,
                "n_used": len(sample_values[index]),
                "n_excluded_missing": missing_counts[index],
                "n_excluded_non_numeric": non_numeric_counts[index],
            }
            for index, column in enumerate(columns)
        ],
    }


def calculate_mann_whitney_samples(
    sample_1_values: Sequence[float],
    sample_2_values: Sequence[float],
    *,
    sample_1_label: str,
    sample_2_label: str,
    alpha: float = 0.05,
    alternative: str = "two_sided",
    method: str = "auto",
    n_excluded_missing: int = 0,
    n_excluded_non_numeric: int = 0,
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise MannWhitneyError("invalid_mann_whitney_alternative")
    if method not in METHODS:
        raise MannWhitneyError("invalid_mann_whitney_method")
    groups = [
        _GroupAccumulator(_safe_group_label(sample_1_label), 0, list(sample_1_values)),
        _GroupAccumulator(_safe_group_label(sample_2_label), 1, list(sample_2_values)),
    ]
    if any(len(group.values) < MIN_GROUP_N for group in groups):
        raise MannWhitneyError("mann_whitney_group_n_too_small")
    if any(not isfinite(value) for group in groups for value in group.values):
        raise MannWhitneyError("mann_whitney_sample_value_not_finite")

    all_values = [value for group in groups for value in group.values]
    has_ties = len(set(all_values)) != len(all_values)
    resolved_method = _resolved_method(method, group_list=groups, has_ties=has_ties)
    test_result = _test_result(
        groups[0],
        groups[1],
        alpha=alpha,
        alternative=alternative,
        requested_method=method,
        resolved_method=resolved_method,
        has_ties=has_ties,
    )
    ranks_by_group = _rank_summaries(groups)
    return {
        "requested_method": method,
        "resolved_method": resolved_method,
        "use_continuity": resolved_method == "asymptotic",
        "has_ties": has_ties,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            groups=groups,
            requested_method=method,
            resolved_method=resolved_method,
            has_ties=has_ties,
            n_excluded_missing=n_excluded_missing,
            n_excluded_non_numeric=n_excluded_non_numeric,
        ),
        "groups": [
            _group_summary(group, ranks_by_group[group.group_index]) for group in groups
        ],
        "test": test_result,
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
    column: MannWhitneyResponseColumn | MannWhitneyGroupColumn,
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


def _resolved_method(
    requested_method: str,
    *,
    group_list: Sequence[_GroupAccumulator],
    has_ties: bool,
) -> str:
    if requested_method == "exact" and has_ties:
        raise MannWhitneyError("mann_whitney_exact_with_ties")
    if requested_method in {"exact", "asymptotic"}:
        return requested_method
    minimum_group_n = min(len(group.values) for group in group_list)
    if minimum_group_n <= 8 and not has_ties:
        return "exact"
    return "asymptotic"


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
    return {
        "group_label": group.group_label,
        "group_index": group.group_index,
        "n": len(values),
        "mean": _mean(values),
        "median": median(values),
        "min": values[0],
        "max": values[-1],
        "rank_sum": ranks["rank_sum"],
        "mean_rank": ranks["mean_rank"],
        "warnings": ["constant_group"] if values[0] == values[-1] else [],
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _test_result(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    *,
    alpha: float,
    alternative: str,
    requested_method: str,
    resolved_method: str,
    has_ties: bool,
) -> dict[str, object]:
    result = stats.mannwhitneyu(
        group_1.values,
        group_2.values,
        alternative=_scipy_alternative(alternative),
        method=resolved_method,
        use_continuity=resolved_method == "asymptotic",
    )
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    if not isfinite(statistic) or not isfinite(p_value):
        raise MannWhitneyError("mann_whitney_statistic_not_finite")

    n_pairs = len(group_1.values) * len(group_2.values)
    probability_superiority = statistic / n_pairs
    rank_biserial = (2.0 * probability_superiority) - 1.0
    return {
        "group_1_label": group_1.group_label,
        "group_2_label": group_2.group_label,
        "u_statistic": statistic,
        "u_statistic_group": group_1.group_label,
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "alternative": alternative,
        "requested_method": requested_method,
        "resolved_method": resolved_method,
        "has_ties": has_ties,
        "effect_size": {
            "rank_biserial": rank_biserial,
            "common_language_probability": probability_superiority,
            "definition": "group_1_greater_than_group_2_plus_half_ties",
        },
    }


def _scipy_alternative(alternative: str) -> str:
    if alternative == "two_sided":
        return "two-sided"
    return alternative


def _result_warnings(
    *,
    groups: Sequence[_GroupAccumulator],
    requested_method: str,
    resolved_method: str,
    has_ties: bool,
    n_excluded_missing: int,
    n_excluded_non_numeric: int,
) -> list[str]:
    warnings = [
        "mann_whitney_independence_assumption",
        "mann_whitney_not_median_test",
    ]
    if has_ties:
        warnings.append("mann_whitney_ties_detected")
    if requested_method == "auto" and resolved_method == "asymptotic" and has_ties:
        warnings.append("mann_whitney_auto_asymptotic_due_to_ties")
    if _has_group_size_imbalance(groups):
        warnings.append("group_size_imbalance")
    if any(len(group.values) < 5 for group in groups):
        warnings.append("small_group_size")
    if n_excluded_missing > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    if any(len(set(group.values)) == 1 for group in groups):
        warnings.append("constant_group")
    return warnings


def _has_group_size_imbalance(groups: Sequence[_GroupAccumulator]) -> bool:
    sizes = [len(group.values) for group in groups]
    return max(sizes) >= 4 * min(sizes)
