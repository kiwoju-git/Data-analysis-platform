"""Bounded two-independent-group variance inference; no I/O or model selection."""

from __future__ import annotations

import importlib.metadata
import math
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

MAX_ROWS = 20_000
MAX_PLOT_POINTS = 500


class TwoVariancesError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class TwoVariancesOptions:
    method: Literal["brown_forsythe", "normal_f"] = "brown_forsythe"
    ratio_scale: Literal["variance", "standard_deviation"] = "variance"
    hypothesized_ratio: float = 1.0
    alternative: Literal["two_sided", "less", "greater"] = "two_sided"
    confidence_level: float = 0.95


@dataclass
class ParsedGroups:
    values: dict[str, list[float]] = field(default_factory=dict)
    row_indices: dict[str, list[int]] = field(default_factory=dict)
    n_total: int = 0
    missing_response: int = 0
    missing_group: int = 0
    nonnumeric_response: int = 0

    @property
    def n_used(self) -> int:
        return sum(map(len, self.values.values()))

    def sample(self) -> dict[str, Any]:
        return {
            "n_total": self.n_total,
            "n_used": self.n_used,
            "n_excluded": self.n_total - self.n_used,
            "missing_response": self.missing_response,
            "missing_group": self.missing_group,
            "nonnumeric_response": self.nonnumeric_response,
            "missing_policy": "complete_case",
        }


def parse_two_variance_groups(
    rows: Iterable[Sequence[str | None]],
    response_index: int,
    group_index: int,
    *,
    decimal: str = ".",
    thousands: str | None = None,
) -> ParsedGroups:
    parsed = ParsedGroups()
    usable = 0
    for row_index, row in enumerate(rows, start=1):
        parsed.n_total += 1
        raw = row[response_index] if response_index < len(row) else None
        key = row[group_index] if group_index < len(row) else None
        if raw is None or not raw.strip():
            parsed.missing_response += 1
            continue
        if key is None or not key.strip():
            parsed.missing_group += 1
            continue
        normalized = raw.strip()
        if thousands:
            normalized = normalized.replace(thousands, "")
        if decimal != ".":
            normalized = normalized.replace(decimal, ".")
        try:
            value = float(Decimal(normalized))
        except (InvalidOperation, ValueError, OverflowError):
            value = math.nan
        if not math.isfinite(value):
            parsed.nonnumeric_response += 1
            continue
        usable += 1
        if usable > MAX_ROWS:
            raise TwoVariancesError("two_variances_usable_rows_limit")
        canonical_key = key
        parsed.values.setdefault(canonical_key, []).append(value)
        parsed.row_indices.setdefault(canonical_key, []).append(row_index)
    return parsed


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise TwoVariancesError("two_variances_nonfinite_result")
    return value


def _f_quantile(probability: float, df1: int, df2: int) -> float:
    value = float(stats.f.ppf(probability, df1, df2))
    if not math.isfinite(value) or value <= 0:
        raise TwoVariancesError("two_variances_nonfinite_result")
    return value


def calculate_two_variances(
    sample_1: Sequence[float],
    sample_2: Sequence[float],
    options: TwoVariancesOptions,
) -> dict[str, Any]:
    if (
        options.method not in ("brown_forsythe", "normal_f")
        or options.ratio_scale not in ("variance", "standard_deviation")
        or options.alternative not in ("two_sided", "less", "greater")
        or not math.isfinite(options.hypothesized_ratio)
        or options.hypothesized_ratio <= 0
        or not math.isfinite(options.confidence_level)
        or not 0.5 < options.confidence_level < 1
    ):
        raise TwoVariancesError("invalid_two_variances_options")
    if options.method == "brown_forsythe" and (
        options.hypothesized_ratio != 1 or options.alternative != "two_sided"
    ):
        raise TwoVariancesError("two_variances_brown_forsythe_equality_only")
    samples = [np.asarray(sample, dtype=float) for sample in (sample_1, sample_2)]
    if any(sample.ndim != 1 or not np.isfinite(sample).all() for sample in samples):
        raise TwoVariancesError("two_variances_nonfinite_input")
    minimum = 3 if options.method == "brown_forsythe" else 2
    if any(len(sample) < minimum for sample in samples):
        raise TwoVariancesError("two_variances_group_n_too_small")
    if sum(map(len, samples)) > MAX_ROWS:
        raise TwoVariancesError("two_variances_usable_rows_limit")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        variances = [_finite(float(np.var(sample, ddof=1))) for sample in samples]
        means = [_finite(float(np.mean(sample))) for sample in samples]
    if any(variance <= 0 for variance in variances):
        raise TwoVariancesError("two_variances_zero_variance")
    ratio = _finite(variances[0] / variances[1])
    if ratio <= 0:
        raise TwoVariancesError("two_variances_nonfinite_result")
    sd_ratio = math.sqrt(ratio)
    alpha = 1 - options.confidence_level
    interval: dict[str, Any] = {"available": False, "reason": "not_provided_by_selected_method"}
    if options.method == "brown_forsythe":
        deviations = [np.abs(sample - np.median(sample)) for sample in samples]
        if (
            sum(float(np.sum((deviation - np.mean(deviation)) ** 2)) for deviation in deviations)
            <= 0
        ):
            raise TwoVariancesError("two_variances_degenerate_absolute_deviations")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            statistic, p_value = stats.levene(*samples, center="median")
        df1, df2 = 1, sum(map(len, samples)) - 2
    else:
        theta0 = options.hypothesized_ratio
        if options.ratio_scale == "standard_deviation":
            theta0 = _finite(theta0 * theta0)
        if theta0 <= 0:
            raise TwoVariancesError("two_variances_nonfinite_result")
        statistic = _finite(ratio / theta0)
        df1, df2 = len(samples[0]) - 1, len(samples[1]) - 1
        lower_tail = float(stats.f.cdf(statistic, df1, df2))
        upper_tail = float(stats.f.sf(statistic, df1, df2))
        p_value = lower_tail if options.alternative == "less" else upper_tail
        if options.alternative == "two_sided":
            p_value = min(1.0, 2 * min(lower_tail, upper_tail))
        lower = (
            0.0
            if options.alternative == "less"
            else ratio
            / _f_quantile(
                1 - alpha / 2 if options.alternative == "two_sided" else 1 - alpha,
                df1,
                df2,
            )
        )
        upper = (
            None
            if options.alternative == "greater"
            else ratio
            / _f_quantile(
                alpha / 2 if options.alternative == "two_sided" else alpha,
                df1,
                df2,
            )
        )
        if options.ratio_scale == "standard_deviation":
            lower, upper = math.sqrt(lower), None if upper is None else math.sqrt(upper)
        interval = {
            "available": True,
            "reason": None,
            "confidence_level": options.confidence_level,
            "lower": {"kind": "finite", "value": _finite(lower)},
            "upper": {"kind": "unbounded", "value": None}
            if upper is None
            else {
                "kind": "finite",
                "value": _finite(upper),
            },
        }
    statistic, p_value = _finite(float(statistic)), _finite(float(p_value))
    return {
        "schema_version": 1,
        "summary_type": "two_variances_test",
        "method": options.method,
        "groups": [
            {
                "n": len(sample),
                "mean": mean,
                "variance": variance,
                "standard_deviation": math.sqrt(variance),
            }
            for sample, mean, variance in zip(samples, means, variances, strict=False)
        ],
        "ratio_estimate": {
            "variance": ratio,
            "standard_deviation": sd_ratio,
            "scale": options.ratio_scale,
            "value": ratio if options.ratio_scale == "variance" else sd_ratio,
        },
        "hypothesis": {
            "ratio": options.hypothesized_ratio,
            "alternative": options.alternative,
            "confidence_level": options.confidence_level,
        },
        "test": {
            "statistic": statistic,
            "df1": df1,
            "df2": df2,
            "p_value": p_value,
            "alpha": alpha,
            "reject": p_value < alpha,
        },
        "ratio_interval": interval,
        "warnings": [
            "two_variances_independence_required",
            "two_variances_nonrejection_not_equivalence",
        ]
        + (
            ["two_variances_f_normality_sensitive"]
            if options.method == "normal_f"
            else ["two_variances_ratio_ci_unavailable"]
        ),
        "package_versions": {name: importlib.metadata.version(name) for name in ("numpy", "scipy")},
    }
