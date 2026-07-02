from __future__ import annotations

import importlib.metadata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from math import exp, isfinite, log, sqrt

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}


class TwoProportionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class TwoProportionResponseColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class TwoProportionGroupColumn:
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
    event_count: int = 0
    non_event_count: int = 0
    observed_levels: Counter[str] = field(default_factory=Counter)

    @property
    def total(self) -> int:
        return self.event_count + self.non_event_count

    @property
    def sample_proportion(self) -> float:
        return self.event_count / self.total

    def add(self, level: str, *, event_level: str) -> None:
        self.observed_levels[level] += 1
        if level == event_level:
            self.event_count += 1
        else:
            self.non_event_count += 1


def calculate_two_proportion(
    rows: Iterable[Sequence[str | None]],
    response_column: TwoProportionResponseColumn,
    group_column: TwoProportionGroupColumn,
    *,
    event_level: str,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    alternative: str = "two_sided",
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise TwoProportionError("invalid_two_proportion_alternative")
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise TwoProportionError("invalid_two_proportion_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise TwoProportionError("invalid_two_proportion_confidence_level")

    normalized_event_level = event_level.strip()
    if normalized_event_level == "":
        raise TwoProportionError("two_proportion_event_level_required")

    groups: dict[str, _GroupAccumulator] = {}
    observed_response_levels: Counter[str] = Counter()
    n_total = 0
    n_excluded_missing_response = 0
    n_excluded_missing_group = 0

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

        level = response_value.strip()
        group_label = group_value.strip()
        observed_response_levels[level] += 1
        group = groups.get(group_label)
        if group is None:
            group = _GroupAccumulator(
                group_label=group_label,
                group_index=len(groups),
            )
            groups[group_label] = group
        group.add(level, event_level=normalized_event_level)

    group_list = list(groups.values())
    if len(group_list) != 2:
        raise TwoProportionError("two_proportion_requires_exactly_two_groups")
    if any(group.total < 1 for group in group_list):
        raise TwoProportionError("two_proportion_group_n_too_small")

    non_event_levels = [
        level for level in observed_response_levels if level != normalized_event_level
    ]
    if len(non_event_levels) > 1:
        raise TwoProportionError("two_proportion_requires_binary_response")

    difference = _difference_result(
        group_list[0],
        group_list[1],
        confidence_level=confidence_level,
    )
    table = _table(group_list[0], group_list[1])
    test = _fisher_result(
        table,
        alpha=alpha,
        alternative=alternative,
    )
    effect_sizes = _effect_sizes(
        group_list[0],
        group_list[1],
        confidence_level=confidence_level,
    )
    expected_counts = _expected_counts(group_list[0], group_list[1])

    return {
        "schema_version": 1,
        "summary_type": "two_proportion_test",
        "method": "fisher_exact_2x2",
        "input_mode": "dataset_binary_response_by_group",
        "missing_policy": "complete_case",
        "alternative": alternative,
        "alpha": alpha,
        "confidence_level": confidence_level,
        "ci_method": "newcombe_wilson",
        "event_level": normalized_event_level,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            groups=group_list,
            observed_response_levels=observed_response_levels,
            event_level=normalized_event_level,
            expected_counts=expected_counts,
            n_excluded_missing_response=n_excluded_missing_response,
            n_excluded_missing_group=n_excluded_missing_group,
        ),
        "response": _column_payload(response_column),
        "group": _column_payload(group_column),
        "n_total": n_total,
        "n_used": sum(group.total for group in group_list),
        "n_excluded_missing_response": n_excluded_missing_response,
        "n_excluded_missing_group": n_excluded_missing_group,
        "group_count": len(group_list),
        "groups": [_group_summary(group) for group in group_list],
        "contingency_table": {
            "columns": ["event", "non_event"],
            "rows": [
                {
                    "group_label": group.group_label,
                    "event_count": group.event_count,
                    "non_event_count": group.non_event_count,
                }
                for group in group_list
            ],
            "expected_counts": expected_counts,
            "min_expected_count": min(min(row) for row in expected_counts),
        },
        "difference": difference,
        "effect_sizes": effect_sizes,
        "test": test,
    }


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _column_payload(
    column: TwoProportionResponseColumn | TwoProportionGroupColumn,
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
    return {
        "group_label": group.group_label,
        "group_index": group.group_index,
        "event_count": group.event_count,
        "non_event_count": group.non_event_count,
        "total": group.total,
        "sample_proportion": group.sample_proportion,
        "levels": [
            {"level": level, "count": count} for level, count in group.observed_levels.items()
        ],
        "warnings": _group_warnings(group),
    }


def _group_warnings(group: _GroupAccumulator) -> list[str]:
    warnings: list[str] = []
    if group.event_count == 0:
        warnings.append("group_has_no_events")
    if group.non_event_count == 0:
        warnings.append("group_has_no_non_events")
    return warnings


def _table(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
) -> list[list[int]]:
    return [
        [group_1.event_count, group_1.non_event_count],
        [group_2.event_count, group_2.non_event_count],
    ]


def _fisher_result(
    table: list[list[int]],
    *,
    alpha: float,
    alternative: str,
) -> dict[str, object]:
    result = stats.fisher_exact(
        table,
        alternative=_scipy_alternative(alternative),
    )
    p_value = float(result.pvalue)
    if not isfinite(p_value):
        raise TwoProportionError("two_proportion_p_value_not_finite")
    statistic = float(result.statistic)
    return {
        "statistic": statistic if isfinite(statistic) else None,
        "statistic_name": "odds_ratio",
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "alternative": alternative,
        "exact": True,
    }


def _scipy_alternative(alternative: str) -> str:
    if alternative == "two_sided":
        return "two-sided"
    return alternative


def _difference_result(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    *,
    confidence_level: float,
) -> dict[str, object]:
    p_1 = group_1.sample_proportion
    p_2 = group_2.sample_proportion
    lower_1, upper_1 = _wilson_interval(
        group_1.event_count,
        group_1.total,
        confidence_level,
    )
    lower_2, upper_2 = _wilson_interval(
        group_2.event_count,
        group_2.total,
        confidence_level,
    )
    lower = (p_1 - p_2) - sqrt(((p_1 - lower_1) ** 2) + ((upper_2 - p_2) ** 2))
    upper = (p_1 - p_2) + sqrt(((upper_1 - p_1) ** 2) + ((p_2 - lower_2) ** 2))
    if not isfinite(lower) or not isfinite(upper):
        raise TwoProportionError("two_proportion_ci_not_finite")
    return {
        "estimate": p_1 - p_2,
        "definition": "group_1_proportion - group_2_proportion",
        "confidence_interval": {
            "method": "newcombe_wilson",
            "level": confidence_level,
            "lower": max(-1.0, lower),
            "upper": min(1.0, upper),
        },
    }


def _wilson_interval(
    event_count: int,
    total: int,
    confidence_level: float,
) -> tuple[float, float]:
    proportion = event_count / total
    alpha = 1.0 - confidence_level
    z_value = float(stats.norm.ppf(1.0 - (alpha / 2.0)))
    denominator = 1.0 + ((z_value**2) / total)
    center = (proportion + ((z_value**2) / (2.0 * total))) / denominator
    half_width = (
        z_value
        * sqrt(
            (proportion * (1.0 - proportion) / total) + ((z_value**2) / (4.0 * total**2)),
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def _effect_sizes(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    *,
    confidence_level: float,
) -> dict[str, object]:
    return {
        "risk_ratio": _risk_ratio(group_1, group_2, confidence_level),
        "odds_ratio": _odds_ratio(group_1, group_2, confidence_level),
    }


def _risk_ratio(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    confidence_level: float,
) -> dict[str, object]:
    if group_2.event_count == 0:
        return {
            "estimate": None,
            "confidence_interval": None,
            "definition": "group_1_event_risk / group_2_event_risk",
        }
    estimate = group_1.sample_proportion / group_2.sample_proportion
    interval = None
    if group_1.event_count > 0:
        standard_error = sqrt(
            (1.0 / group_1.event_count)
            - (1.0 / group_1.total)
            + (1.0 / group_2.event_count)
            - (1.0 / group_2.total),
        )
        interval = _log_interval(estimate, standard_error, confidence_level)
    return {
        "estimate": estimate if isfinite(estimate) else None,
        "confidence_interval": interval,
        "definition": "group_1_event_risk / group_2_event_risk",
    }


def _odds_ratio(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
    confidence_level: float,
) -> dict[str, object]:
    denominator = group_1.non_event_count * group_2.event_count
    estimate = (
        None if denominator == 0 else (group_1.event_count * group_2.non_event_count) / denominator
    )
    interval = None
    if (
        estimate is not None
        and group_1.event_count > 0
        and group_1.non_event_count > 0
        and group_2.event_count > 0
        and group_2.non_event_count > 0
    ):
        standard_error = sqrt(
            (1.0 / group_1.event_count)
            + (1.0 / group_1.non_event_count)
            + (1.0 / group_2.event_count)
            + (1.0 / group_2.non_event_count),
        )
        interval = _log_interval(estimate, standard_error, confidence_level)
    return {
        "estimate": estimate if estimate is not None and isfinite(estimate) else None,
        "confidence_interval": interval,
        "definition": "group_1_event_odds / group_2_event_odds",
    }


def _log_interval(
    estimate: float,
    standard_error: float,
    confidence_level: float,
) -> dict[str, object]:
    alpha = 1.0 - confidence_level
    z_value = float(stats.norm.ppf(1.0 - (alpha / 2.0)))
    lower = exp(log(estimate) - (z_value * standard_error))
    upper = exp(log(estimate) + (z_value * standard_error))
    if not isfinite(lower) or not isfinite(upper):
        raise TwoProportionError("two_proportion_effect_ci_not_finite")
    return {
        "method": "log_wald",
        "level": confidence_level,
        "lower": lower,
        "upper": upper,
    }


def _expected_counts(
    group_1: _GroupAccumulator,
    group_2: _GroupAccumulator,
) -> list[list[float]]:
    row_totals = [group_1.total, group_2.total]
    column_totals = [
        group_1.event_count + group_2.event_count,
        group_1.non_event_count + group_2.non_event_count,
    ]
    grand_total = sum(row_totals)
    return [
        [(row_total * column_total) / grand_total for column_total in column_totals]
        for row_total in row_totals
    ]


def _result_warnings(
    *,
    groups: Sequence[_GroupAccumulator],
    observed_response_levels: Counter[str],
    event_level: str,
    expected_counts: list[list[float]],
    n_excluded_missing_response: int,
    n_excluded_missing_group: int,
) -> list[str]:
    warnings = [
        "two_proportion_binary_design_assumption",
        "two_proportion_independence_assumption",
        "two_proportion_fisher_exact",
    ]
    if n_excluded_missing_response > 0 or n_excluded_missing_group > 0:
        warnings.append("missing_values_excluded")
    if min(min(row) for row in expected_counts) < 5.0:
        warnings.append("small_expected_counts")
    if event_level not in observed_response_levels:
        warnings.append("event_level_not_observed")
    total_event_count = sum(group.event_count for group in groups)
    total_used = sum(group.total for group in groups)
    if total_event_count == 0 or total_event_count == total_used:
        warnings.append("all_events_or_no_events")
    if any(group.event_count == 0 or group.non_event_count == 0 for group in groups):
        warnings.append("zero_cell_effect_ci_unavailable")
    if max(group.total for group in groups) / min(group.total for group in groups) >= 4.0:
        warnings.append("group_size_imbalance")
    return warnings
