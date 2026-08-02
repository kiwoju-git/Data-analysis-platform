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
TWO_SAMPLE_DESIGN = "two_sample_independent_mean_difference"
PAIRED_DESIGN = "paired_mean_difference"
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
        "schema_version": 2,
        "summary_type": "equivalence_tost",
        "method": "one_sample_mean_tost",
        "input_mode": "dataset_one_numeric_column",
        "design": DESIGN,
        "estimate_definition": "sample_mean_minus_reference_mean",
        "missing_policy": "complete_case",
        "alpha": alpha,
        "confidence_level": 1.0 - (2.0 * alpha),
        "reference_mean": reference_mean,
        "equivalence_bounds": {
            "lower": lower_bound,
            "upper": upper_bound,
            "scale": "raw_difference_units",
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
        "samples": {"one_sample": sample},
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


def calculate_two_sample_equivalence_tost(
    rows: Iterable[Sequence[str | None]],
    response_column: EquivalenceTostColumn,
    group_column: EquivalenceTostColumn,
    *,
    test_group_label: str,
    reference_group_label: str,
    lower_bound: float,
    upper_bound: float,
    alpha: float = 0.05,
    variance_assumption: str = "welch",
    decimal: str = ".",
    thousands: str | None = None,
) -> dict[str, object]:
    _validate_common_inputs(lower_bound, upper_bound, alpha)
    if variance_assumption not in {"welch", "pooled"}:
        raise EquivalenceTostError("equivalence_tost_variance_assumption_invalid")
    if not test_group_label or not reference_group_label:
        raise EquivalenceTostError("equivalence_tost_groups_required")
    if test_group_label == reference_group_label:
        raise EquivalenceTostError("equivalence_tost_groups_must_differ")

    groups: dict[str, list[float]] = {}
    n_total = 0
    n_missing_response = 0
    n_missing_group = 0
    n_non_numeric = 0
    for row in rows:
        n_total += 1
        raw_group = _row_value(row, group_column.column_index)
        if raw_group is None or raw_group.strip() == "":
            n_missing_group += 1
            continue
        group_label = raw_group.strip()
        groups.setdefault(group_label, [])
        raw_value = _row_value(row, response_column.column_index)
        if raw_value is None or raw_value.strip() == "":
            n_missing_response += 1
            continue
        parsed = _parse_number(raw_value, decimal=decimal, thousands=thousands)
        if parsed is None:
            n_non_numeric += 1
            continue
        groups[group_label].append(parsed)

    if len(groups) != 2:
        raise EquivalenceTostError("equivalence_tost_requires_two_groups")
    if test_group_label not in groups or reference_group_label not in groups:
        raise EquivalenceTostError("equivalence_tost_group_not_found")
    test_values = groups[test_group_label]
    reference_values = groups[reference_group_label]
    if len(test_values) < MIN_N or len(reference_values) < MIN_N:
        raise EquivalenceTostError("equivalence_tost_n_too_small")

    test_sample = _sample_summary(test_values)
    reference_sample = _sample_summary(reference_values)
    test_variance = _sample_variance(test_values)
    reference_variance = _sample_variance(reference_values)
    estimate = _mean(test_values) - _mean(reference_values)
    if variance_assumption == "welch":
        test_component = test_variance / len(test_values)
        reference_component = reference_variance / len(reference_values)
        variance_term = test_component + reference_component
        if variance_term <= 0.0:
            raise EquivalenceTostError("equivalence_tost_standard_error_zero")
        df = (variance_term**2) / (
            ((test_component**2) / (len(test_values) - 1))
            + ((reference_component**2) / (len(reference_values) - 1))
        )
        standard_error = sqrt(variance_term)
    else:
        df = float(len(test_values) + len(reference_values) - 2)
        pooled_variance = (
            ((len(test_values) - 1) * test_variance)
            + ((len(reference_values) - 1) * reference_variance)
        ) / df
        standard_error = sqrt(
            pooled_variance * ((1.0 / len(test_values)) + (1.0 / len(reference_values)))
        )
    core = _tost_core(
        estimate,
        standard_error=standard_error,
        df=df,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        alpha=alpha,
    )
    return {
        "schema_version": 2,
        "summary_type": "equivalence_tost",
        "method": "two_sample_mean_difference_tost",
        "input_mode": "dataset_long_two_group",
        "design": TWO_SAMPLE_DESIGN,
        "estimate_definition": "mean_test_minus_mean_reference",
        "difference_definition": "test_minus_reference",
        "missing_policy": "complete_case",
        "alpha": alpha,
        "confidence_level": 1.0 - (2.0 * alpha),
        "reference_mean": None,
        "variance_assumption": variance_assumption,
        "test_group_label": test_group_label,
        "reference_group_label": reference_group_label,
        "equivalence_bounds": _bounds_payload(
            lower_bound,
            upper_bound,
            "mean_test_minus_mean_reference",
        ),
        "package_versions": _package_versions(),
        "warnings": _result_warnings(
            n_missing=n_missing_response + n_missing_group,
            n_non_numeric=n_non_numeric,
        ),
        "response": _column_payload(response_column),
        "group": _column_payload(group_column),
        "n_total": n_total,
        "n_used": len(test_values) + len(reference_values),
        "n_missing": n_missing_response + n_missing_group,
        "n_missing_response": n_missing_response,
        "n_missing_group": n_missing_group,
        "n_non_numeric": n_non_numeric,
        "sample": test_sample,
        "samples": {
            "test": {"group_label": test_group_label, **test_sample},
            "reference": {"group_label": reference_group_label, **reference_sample},
        },
        "estimate": {
            "value": estimate,
            "definition": "mean_test_minus_mean_reference",
            "standard_error": standard_error,
            "df": df,
        },
        **core,
        "effect_size": None,
    }


def calculate_paired_equivalence_tost(
    rows: Iterable[Sequence[str | None]],
    test_column: EquivalenceTostColumn,
    reference_column: EquivalenceTostColumn,
    *,
    lower_bound: float,
    upper_bound: float,
    alpha: float = 0.05,
    decimal: str = ".",
    thousands: str | None = None,
) -> dict[str, object]:
    _validate_common_inputs(lower_bound, upper_bound, alpha)
    if test_column.column_id == reference_column.column_id:
        raise EquivalenceTostError("equivalence_tost_same_paired_column")
    differences: list[float] = []
    n_total = 0
    n_missing_test = 0
    n_missing_reference = 0
    n_non_numeric = 0
    for row in rows:
        n_total += 1
        raw_test = _row_value(row, test_column.column_index)
        raw_reference = _row_value(row, reference_column.column_index)
        missing_test = raw_test is None or raw_test.strip() == ""
        missing_reference = raw_reference is None or raw_reference.strip() == ""
        if missing_test or missing_reference:
            n_missing_test += int(missing_test)
            n_missing_reference += int(missing_reference)
            continue
        assert raw_test is not None
        assert raw_reference is not None
        test_value = _parse_number(raw_test, decimal=decimal, thousands=thousands)
        reference_value = _parse_number(
            raw_reference,
            decimal=decimal,
            thousands=thousands,
        )
        if test_value is None or reference_value is None:
            n_non_numeric += 1
            continue
        differences.append(test_value - reference_value)
    if len(differences) < MIN_N:
        raise EquivalenceTostError("equivalence_tost_n_too_small")
    difference_sample = _sample_summary(differences)
    estimate = _mean(differences)
    standard_error = _sample_std(differences) / sqrt(len(differences))
    df = float(len(differences) - 1)
    core = _tost_core(
        estimate,
        standard_error=standard_error,
        df=df,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        alpha=alpha,
    )
    return {
        "schema_version": 2,
        "summary_type": "equivalence_tost",
        "method": "paired_mean_difference_tost",
        "input_mode": "dataset_wide_paired_columns",
        "design": PAIRED_DESIGN,
        "estimate_definition": "mean_paired_test_minus_reference",
        "difference_definition": "test_minus_reference",
        "missing_policy": "complete_pair",
        "alpha": alpha,
        "confidence_level": 1.0 - (2.0 * alpha),
        "reference_mean": None,
        "equivalence_bounds": _bounds_payload(
            lower_bound,
            upper_bound,
            "mean_paired_test_minus_reference",
        ),
        "package_versions": _package_versions(),
        "warnings": _result_warnings(
            n_missing=n_total - len(differences) - n_non_numeric,
            n_non_numeric=n_non_numeric,
        ),
        "response": _column_payload(test_column),
        "test_column": _column_payload(test_column),
        "reference_column": _column_payload(reference_column),
        "n_total": n_total,
        "n_used": len(differences),
        "n_complete_pairs": len(differences),
        "n_incomplete_pairs": n_total - len(differences) - n_non_numeric,
        "n_missing": n_total - len(differences) - n_non_numeric,
        "n_missing_test": n_missing_test,
        "n_missing_reference": n_missing_reference,
        "n_non_numeric": n_non_numeric,
        "sample": difference_sample,
        "samples": {"paired_differences": difference_sample},
        "estimate": {
            "value": estimate,
            "definition": "mean_paired_test_minus_reference",
            "standard_error": standard_error,
            "df": df,
        },
        **core,
        "effect_size": _effect_size(estimate, std=_sample_std(differences), df=df),
    }


def _validate_common_inputs(lower_bound: float, upper_bound: float, alpha: float) -> None:
    if not isfinite(lower_bound) or not isfinite(upper_bound):
        raise EquivalenceTostError("invalid_equivalence_tost_bounds")
    if lower_bound >= upper_bound:
        raise EquivalenceTostError("equivalence_tost_bounds_order_invalid")
    if alpha <= 0.0 or alpha >= 0.5 or not isfinite(alpha):
        raise EquivalenceTostError("invalid_equivalence_tost_alpha")


def _tost_core(
    estimate: float,
    *,
    standard_error: float,
    df: float,
    lower_bound: float,
    upper_bound: float,
    alpha: float,
) -> dict[str, object]:
    if standard_error <= 0.0 or not isfinite(standard_error) or not isfinite(df):
        raise EquivalenceTostError("equivalence_tost_standard_error_zero")
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
    return {
        "tests": {"lower": lower_test, "upper": upper_test},
        "tost": {
            "p_value": max(cast(float, lower_test["p_value"]), cast(float, upper_test["p_value"])),
            "equivalent": bool(lower_test["reject_null"] and upper_test["reject_null"]),
            "decision_rule": "both_one_sided_tests_reject_at_alpha",
            "ci_inside_equivalence_bounds": confidence_interval["inside_equivalence_bounds"],
        },
        "confidence_interval": confidence_interval,
    }


def _bounds_payload(lower: float, upper: float, definition: str) -> dict[str, object]:
    return {
        "lower": lower,
        "upper": upper,
        "scale": "raw_difference_units",
        "estimate_definition": definition,
    }


def _package_versions() -> dict[str, str]:
    return {
        "numpy": importlib.metadata.version("numpy"),
        "scipy": importlib.metadata.version("scipy"),
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
        "reject_null": p_value <= alpha,
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
        "reject_null": p_value <= alpha,
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
