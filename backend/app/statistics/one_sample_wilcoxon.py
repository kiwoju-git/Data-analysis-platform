from __future__ import annotations

import importlib.metadata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite
from statistics import median

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}
METHODS = {"auto", "exact", "asymptotic"}
ZERO_METHODS = {"wilcox", "pratt", "zsplit"}
MIN_NONZERO_N = 1


class OneSampleWilcoxonError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OneSampleWilcoxonColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_one_sample_wilcoxon(
    rows: Iterable[Sequence[str | None]],
    response_column: OneSampleWilcoxonColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    alternative: str = "two_sided",
    null_location: float = 0.0,
    method: str = "auto",
    zero_method: str = "wilcox",
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise OneSampleWilcoxonError("invalid_one_sample_wilcoxon_alternative")
    if method not in METHODS:
        raise OneSampleWilcoxonError("invalid_one_sample_wilcoxon_method")
    if zero_method not in ZERO_METHODS:
        raise OneSampleWilcoxonError("invalid_one_sample_wilcoxon_zero_method")

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

    differences = [value - null_location for value in values]
    zero_difference_count = sum(1 for difference in differences if difference == 0.0)
    nonzero_differences = [difference for difference in differences if difference != 0.0]
    if len(nonzero_differences) < MIN_NONZERO_N:
        raise OneSampleWilcoxonError("one_sample_wilcoxon_no_nonzero_differences")

    tie_count = _absolute_tie_count(nonzero_differences)
    has_ties = tie_count > 0
    resolved_method = _resolved_method(
        method,
        n_nonzero=len(nonzero_differences),
        zero_difference_count=zero_difference_count,
        has_ties=has_ties,
    )
    rank_summary = _rank_summary(differences, zero_method=zero_method)
    test = _test_result(
        differences,
        rank_summary=rank_summary,
        alpha=alpha,
        alternative=alternative,
        requested_method=method,
        resolved_method=resolved_method,
        zero_method=zero_method,
        zero_difference_count=zero_difference_count,
        tie_count=tie_count,
    )

    return {
        "schema_version": 1,
        "summary_type": "one_sample_wilcoxon_signed_rank_test",
        "method": "one_sample_wilcoxon_signed_rank",
        "missing_policy": "complete_case",
        "alternative": alternative,
        "alpha": alpha,
        "null_location": null_location,
        "requested_method": method,
        "resolved_method": resolved_method,
        "zero_method": zero_method,
        "correction": False,
        "has_ties": has_ties,
        "tie_count": tie_count,
        "zero_difference_count": zero_difference_count,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            requested_method=method,
            resolved_method=resolved_method,
            zero_difference_count=zero_difference_count,
            has_ties=has_ties,
            n_nonzero=len(nonzero_differences),
            n_missing=n_missing,
            n_non_numeric=n_non_numeric,
        ),
        "response": _column_payload(response_column),
        "n_total": n_total,
        "n_used": len(values),
        "n_missing": n_missing,
        "n_non_numeric": n_non_numeric,
        "n_nonzero": len(nonzero_differences),
        "sample": _sample_summary(values, differences=differences),
        "test": test,
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


def _column_payload(column: OneSampleWilcoxonColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _sample_summary(
    values: Sequence[float],
    *,
    differences: Sequence[float],
) -> dict[str, object]:
    sorted_values = sorted(values)
    sorted_differences = sorted(differences)
    return {
        "n": len(sorted_values),
        "mean": _mean(sorted_values),
        "median": median(sorted_values),
        "min": sorted_values[0],
        "max": sorted_values[-1],
        "median_difference": median(sorted_differences),
        "positive_difference_count": sum(1 for difference in differences if difference > 0.0),
        "negative_difference_count": sum(1 for difference in differences if difference < 0.0),
        "zero_difference_count": sum(1 for difference in differences if difference == 0.0),
        "warnings": ["constant_column"] if sorted_values[0] == sorted_values[-1] else [],
    }


def _mean(values: Sequence[float]) -> float:
    return fsum(values) / len(values)


def _absolute_tie_count(differences: Sequence[float]) -> int:
    counts = Counter(abs(difference) for difference in differences if difference != 0.0)
    return sum(count for count in counts.values() if count > 1)


def _resolved_method(
    requested_method: str,
    *,
    n_nonzero: int,
    zero_difference_count: int,
    has_ties: bool,
) -> str:
    if requested_method == "exact" and (zero_difference_count > 0 or has_ties):
        raise OneSampleWilcoxonError("one_sample_wilcoxon_exact_with_zeros_or_ties")
    if requested_method in {"exact", "asymptotic"}:
        return requested_method
    if n_nonzero <= 50 and zero_difference_count == 0 and not has_ties:
        return "exact"
    return "asymptotic"


def _rank_summary(
    differences: Sequence[float],
    *,
    zero_method: str,
) -> dict[str, float]:
    if zero_method == "wilcox":
        ranked_differences = [difference for difference in differences if difference != 0.0]
        ranks = stats.rankdata(
            [abs(difference) for difference in ranked_differences], method="average"
        )
        positive_rank_sum = fsum(
            float(rank)
            for difference, rank in zip(ranked_differences, ranks, strict=True)
            if difference > 0.0
        )
        negative_rank_sum = fsum(
            float(rank)
            for difference, rank in zip(ranked_differences, ranks, strict=True)
            if difference < 0.0
        )
        zero_rank_sum = 0.0
    else:
        ranks = stats.rankdata([abs(difference) for difference in differences], method="average")
        positive_rank_sum = fsum(
            float(rank)
            for difference, rank in zip(differences, ranks, strict=True)
            if difference > 0.0
        )
        negative_rank_sum = fsum(
            float(rank)
            for difference, rank in zip(differences, ranks, strict=True)
            if difference < 0.0
        )
        zero_rank_sum = fsum(
            float(rank)
            for difference, rank in zip(differences, ranks, strict=True)
            if difference == 0.0
        )
        if zero_method == "zsplit":
            positive_rank_sum += zero_rank_sum / 2.0
            negative_rank_sum += zero_rank_sum / 2.0

    return {
        "positive_rank_sum": positive_rank_sum,
        "negative_rank_sum": negative_rank_sum,
        "zero_rank_sum": zero_rank_sum,
        "rank_sum_total": positive_rank_sum + negative_rank_sum,
    }


def _test_result(
    differences: Sequence[float],
    *,
    rank_summary: dict[str, float],
    alpha: float,
    alternative: str,
    requested_method: str,
    resolved_method: str,
    zero_method: str,
    zero_difference_count: int,
    tie_count: int,
) -> dict[str, object]:
    result = stats.wilcoxon(
        differences,
        zero_method=zero_method,
        correction=False,
        alternative=_scipy_alternative(alternative),
        method=resolved_method,
    )
    statistic = float(result.statistic)
    p_value = float(result.pvalue)
    if not isfinite(statistic) or not isfinite(p_value):
        raise OneSampleWilcoxonError("one_sample_wilcoxon_statistic_not_finite")

    return {
        "w_statistic": statistic,
        "p_value": p_value,
        "reject_null": p_value < alpha,
        "alternative": alternative,
        "requested_method": requested_method,
        "resolved_method": resolved_method,
        "zero_method": zero_method,
        "zero_difference_count": zero_difference_count,
        "tie_count": tie_count,
        "positive_rank_sum": rank_summary["positive_rank_sum"],
        "negative_rank_sum": rank_summary["negative_rank_sum"],
        "zero_rank_sum": rank_summary["zero_rank_sum"],
        "rank_sum_total": rank_summary["rank_sum_total"],
        "effect_size": _effect_size(rank_summary),
    }


def _effect_size(rank_summary: dict[str, float]) -> dict[str, object]:
    rank_sum_total = rank_summary["rank_sum_total"]
    if rank_sum_total <= 0.0:
        return {
            "rank_biserial": None,
            "definition": "positive_minus_negative_rank_sum_over_nonzero_rank_sum",
        }
    return {
        "rank_biserial": (
            (rank_summary["positive_rank_sum"] - rank_summary["negative_rank_sum"]) / rank_sum_total
        ),
        "definition": "positive_minus_negative_rank_sum_over_nonzero_rank_sum",
    }


def _scipy_alternative(alternative: str) -> str:
    if alternative == "two_sided":
        return "two-sided"
    return alternative


def _result_warnings(
    *,
    requested_method: str,
    resolved_method: str,
    zero_difference_count: int,
    has_ties: bool,
    n_nonzero: int,
    n_missing: int,
    n_non_numeric: int,
) -> list[str]:
    warnings = [
        "one_sample_wilcoxon_symmetry_assumption",
        "one_sample_wilcoxon_not_median_test",
        "one_sample_wilcoxon_not_auto_switched",
    ]
    if zero_difference_count > 0:
        warnings.append("zero_differences_detected")
    if has_ties:
        warnings.append("signed_rank_ties_detected")
    if (
        requested_method == "auto"
        and resolved_method == "asymptotic"
        and (zero_difference_count > 0 or has_ties)
    ):
        warnings.append("one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties")
    if n_nonzero < 5:
        warnings.append("small_nonzero_n")
    if n_missing > 0:
        warnings.append("missing_values_excluded")
    if n_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    return warnings
