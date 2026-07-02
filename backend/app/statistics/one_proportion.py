from __future__ import annotations

import importlib.metadata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import asin, isfinite, sqrt

from scipy import stats  # type: ignore[import-untyped]

ALTERNATIVES = {"two_sided", "greater", "less"}
CI_METHODS = {"wilson", "clopper_pearson"}


class OneProportionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OneProportionColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


def calculate_one_proportion(
    rows: Iterable[Sequence[str | None]],
    response_column: OneProportionColumn,
    *,
    event_level: str,
    null_proportion: float = 0.5,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    alternative: str = "two_sided",
    ci_method: str = "wilson",
) -> dict[str, object]:
    if alternative not in ALTERNATIVES:
        raise OneProportionError("invalid_one_proportion_alternative")
    if ci_method not in CI_METHODS:
        raise OneProportionError("invalid_one_proportion_ci_method")
    if null_proportion <= 0.0 or null_proportion >= 1.0 or not isfinite(null_proportion):
        raise OneProportionError("invalid_one_proportion_null_proportion")
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise OneProportionError("invalid_one_proportion_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0 or not isfinite(confidence_level):
        raise OneProportionError("invalid_one_proportion_confidence_level")

    normalized_event_level = _safe_level(event_level)
    if normalized_event_level == "":
        raise OneProportionError("one_proportion_event_level_required")

    n_total = 0
    n_missing = 0
    event_count = 0
    observed_levels: Counter[str] = Counter()

    for row in rows:
        n_total += 1
        value = _row_value(row, response_column.column_index)
        if value is None or value.strip() == "":
            n_missing += 1
            continue
        level = _safe_level(value)
        observed_levels[level] += 1
        if level == normalized_event_level:
            event_count += 1

    n_used = sum(observed_levels.values())
    if n_used < 1:
        raise OneProportionError("one_proportion_n_too_small")

    non_event_levels = [level for level in observed_levels if level != normalized_event_level]
    if len(non_event_levels) > 1:
        raise OneProportionError("one_proportion_requires_binary_column")

    sample_proportion = event_count / n_used
    p_value = _binomial_p_value(
        event_count,
        n_used,
        null_proportion=null_proportion,
        alternative=alternative,
    )
    confidence_interval = _confidence_interval(
        event_count,
        n_used,
        confidence_level=confidence_level,
        ci_method=ci_method,
    )

    return {
        "schema_version": 1,
        "summary_type": "one_proportion_test",
        "method": "exact_binomial_test",
        "input_mode": "dataset_binary_column",
        "missing_policy": "complete_case",
        "alternative": alternative,
        "alpha": alpha,
        "confidence_level": confidence_level,
        "ci_method": ci_method,
        "null_proportion": null_proportion,
        "event_level": normalized_event_level,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            event_count=event_count,
            n_used=n_used,
            n_missing=n_missing,
            observed_levels=observed_levels,
            event_level=normalized_event_level,
        ),
        "response": _column_payload(response_column),
        "n_total": n_total,
        "n_used": n_used,
        "n_missing": n_missing,
        "levels": [
            {"level": level, "count": count, "is_event": level == normalized_event_level}
            for level, count in observed_levels.items()
        ],
        "sample": {
            "event_count": event_count,
            "non_event_count": n_used - event_count,
            "total": n_used,
            "sample_proportion": sample_proportion,
            "difference_from_null": sample_proportion - null_proportion,
            "odds": _odds(event_count, n_used),
        },
        "test": {
            "statistic": event_count,
            "statistic_name": "event_count",
            "p_value": p_value,
            "reject_null": p_value < alpha,
            "alternative": alternative,
            "exact": True,
        },
        "confidence_interval": confidence_interval,
        "effect_size": {
            "cohen_h": _cohen_h(sample_proportion, null_proportion),
            "definition": "2*asin(sqrt(p_hat))-2*asin(sqrt(p0))",
        },
    }


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _safe_level(value: str) -> str:
    return value.strip()


def _column_payload(column: OneProportionColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _binomial_p_value(
    event_count: int,
    total: int,
    *,
    null_proportion: float,
    alternative: str,
) -> float:
    result = stats.binomtest(
        event_count,
        total,
        p=null_proportion,
        alternative=_scipy_alternative(alternative),
    )
    p_value = float(result.pvalue)
    if not isfinite(p_value):
        raise OneProportionError("one_proportion_p_value_not_finite")
    return p_value


def _scipy_alternative(alternative: str) -> str:
    if alternative == "two_sided":
        return "two-sided"
    return alternative


def _confidence_interval(
    event_count: int,
    total: int,
    *,
    confidence_level: float,
    ci_method: str,
) -> dict[str, object]:
    if ci_method == "wilson":
        lower, upper = _wilson_interval(event_count, total, confidence_level)
    else:
        lower, upper = _clopper_pearson_interval(event_count, total, confidence_level)
    return {
        "method": ci_method,
        "level": confidence_level,
        "lower": lower,
        "upper": upper,
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


def _clopper_pearson_interval(
    event_count: int,
    total: int,
    confidence_level: float,
) -> tuple[float, float]:
    alpha = 1.0 - confidence_level
    lower = (
        0.0
        if event_count == 0
        else float(stats.beta.ppf(alpha / 2.0, event_count, total - event_count + 1))
    )
    upper = (
        1.0
        if event_count == total
        else float(stats.beta.ppf(1.0 - (alpha / 2.0), event_count + 1, total - event_count))
    )
    if not isfinite(lower) or not isfinite(upper):
        raise OneProportionError("one_proportion_ci_not_finite")
    return lower, upper


def _odds(event_count: int, total: int) -> float | None:
    non_event_count = total - event_count
    if non_event_count == 0:
        return None
    return event_count / non_event_count


def _cohen_h(sample_proportion: float, null_proportion: float) -> float:
    return (2.0 * asin(sqrt(sample_proportion))) - (2.0 * asin(sqrt(null_proportion)))


def _result_warnings(
    *,
    event_count: int,
    n_used: int,
    n_missing: int,
    observed_levels: Counter[str],
    event_level: str,
) -> list[str]:
    warnings = [
        "one_proportion_binary_design_assumption",
        "one_proportion_exact_binomial",
    ]
    if n_missing > 0:
        warnings.append("missing_values_excluded")
    if event_count == 0:
        warnings.append("event_level_not_observed")
    if event_count == 0 or event_count == n_used:
        warnings.append("all_events_or_no_events")
    if len(observed_levels) == 1:
        warnings.append("single_observed_level")
    if event_level not in observed_levels:
        warnings.append("event_level_absent_from_observed_levels")
    return warnings
