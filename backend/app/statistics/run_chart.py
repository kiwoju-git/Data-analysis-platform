from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import exp, fsum, isfinite, lgamma, log
from statistics import NormalDist

MIN_N = 3
DEFAULT_POINT_LIMIT = 1000
DEFAULT_TREND_MIN_LENGTH = 6
DEFAULT_OSCILLATION_MIN_LENGTH = 14
DEFAULT_RUNS_TEST_ALPHA = 0.05
MAX_EXACT_RUNS_TEST_N = 5000
NUMERIC_ORDER_TYPES = {"integer", "decimal"}
DATETIME_ORDER_TYPES = {"datetime"}
DATETIME_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
)


class RunChartError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RunChartColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _RunChartPoint:
    position: int
    canonical_position: int
    value: float
    relative_to_center: str


@dataclass(frozen=True)
class _RunChartCandidate:
    canonical_position: int
    value: float
    order_value: float | datetime | None


@dataclass(frozen=True)
class _ParsedDateTimeOrder:
    value: datetime
    timezone_aware: bool


def calculate_run_chart(
    rows: Iterable[Sequence[str | None]],
    value_column: RunChartColumn,
    *,
    order_column: RunChartColumn | None = None,
    decimal: str = ".",
    thousands: str | None = None,
    center_method: str = "median",
    missing_policy: str = "complete_case",
    tie_policy: str = "exclude_from_runs",
    trend_min_length: int = DEFAULT_TREND_MIN_LENGTH,
    oscillation_min_length: int = DEFAULT_OSCILLATION_MIN_LENGTH,
    runs_test_alpha: float = DEFAULT_RUNS_TEST_ALPHA,
    point_limit: int = DEFAULT_POINT_LIMIT,
) -> dict[str, object]:
    if center_method != "median":
        raise RunChartError("invalid_run_chart_center_method")
    if missing_policy != "complete_case":
        raise RunChartError("run_chart_missing_policy_unsupported")
    if tie_policy != "exclude_from_runs":
        raise RunChartError("invalid_run_chart_tie_policy")
    if trend_min_length < 3:
        raise RunChartError("invalid_run_chart_trend_min_length")
    if oscillation_min_length < 4:
        raise RunChartError("invalid_run_chart_oscillation_min_length")
    if not isfinite(runs_test_alpha) or runs_test_alpha <= 0 or runs_test_alpha >= 0.5:
        raise RunChartError("invalid_run_chart_runs_test_alpha")
    if point_limit <= 0:
        raise RunChartError("invalid_run_chart_point_limit")

    n_total = 0
    n_excluded_missing_value = 0
    n_excluded_non_numeric_value = 0
    n_excluded_missing_order = 0
    n_excluded_non_numeric_order = 0
    order_timezone_aware: bool | None = None
    values: list[_RunChartCandidate] = []

    for row in rows:
        n_total += 1
        raw_value = _row_value(row, value_column.column_index)
        if raw_value is None or raw_value.strip() == "":
            n_excluded_missing_value += 1
            continue

        parsed_value = _parse_number(raw_value, decimal=decimal, thousands=thousands)
        if parsed_value is None:
            n_excluded_non_numeric_value += 1
            continue

        order_value: float | datetime | None = None
        if order_column is not None:
            raw_order = _row_value(row, order_column.column_index)
            if raw_order is None or raw_order.strip() == "":
                n_excluded_missing_order += 1
                continue

            parsed_order = _parse_order_value(
                raw_order,
                order_column,
                decimal=decimal,
                thousands=thousands,
            )
            if parsed_order is None:
                n_excluded_non_numeric_order += 1
                continue
            if isinstance(parsed_order, _ParsedDateTimeOrder):
                if order_timezone_aware is None:
                    order_timezone_aware = parsed_order.timezone_aware
                elif order_timezone_aware != parsed_order.timezone_aware:
                    raise RunChartError("run_chart_order_mixed_timezone_awareness")
                order_value = parsed_order.value
            else:
                order_value = parsed_order

        values.append(
            _RunChartCandidate(
                canonical_position=n_total,
                value=parsed_value,
                order_value=order_value,
            ),
        )

    n_used = len(values)
    if n_used < MIN_N:
        raise RunChartError("run_chart_n_too_small")

    order_source = "canonical_row_order"
    x_axis = "canonical_row_position"
    order_duplicate_count = 0
    has_datetime_order_column = False
    if order_column is not None:
        values.sort(key=_order_sort_key)
        if order_column.data_type in DATETIME_ORDER_TYPES:
            has_datetime_order_column = True
            order_source = "datetime_order_column_ascending"
        else:
            order_source = "numeric_order_column_ascending"
        x_axis = "order_rank"
        order_duplicate_count = _duplicate_count(
            [candidate.order_value for candidate in values if candidate.order_value is not None],
        )

    numeric_values = [candidate.value for candidate in values]
    center_line = _median(sorted(numeric_values))
    points = [
        _RunChartPoint(
            position=index if order_column is not None else candidate.canonical_position,
            canonical_position=candidate.canonical_position,
            value=candidate.value,
            relative_to_center=_relative_to_center(candidate.value, center_line),
        )
        for index, candidate in enumerate(values, start=1)
    ]
    run_summary = _run_summary(points)
    n_ties = _int_summary_value(run_summary, "n_ties")
    runs_test = _runs_test(points, run_summary, alpha=runs_test_alpha)
    approximate_randomness_tests = _approximate_randomness_tests(
        points,
        center_line=center_line,
        alpha=runs_test_alpha,
    )
    signals = [
        *_trend_signals(points, min_length=trend_min_length),
        *_oscillation_signals(points, min_length=oscillation_min_length),
        *_runs_test_signals(points, runs_test),
    ]
    warnings = _result_warnings(
        n_excluded_missing_value=n_excluded_missing_value,
        n_excluded_non_numeric_value=n_excluded_non_numeric_value,
        n_excluded_missing_order=n_excluded_missing_order,
        n_excluded_non_numeric_order=n_excluded_non_numeric_order,
        n_ties=n_ties,
        has_order_column=order_column is not None,
        has_datetime_order_column=has_datetime_order_column,
        order_duplicate_count=order_duplicate_count,
        runs_test=runs_test,
        signals=signals,
        point_count=n_used,
        point_limit=point_limit,
    )

    return {
        "schema_version": 2,
        "summary_type": "run_chart",
        "method": "median_run_chart",
        "center_method": center_method,
        "order_source": order_source,
        "order_tie_breaker": "canonical_row_position" if order_column is not None else None,
        "order_timezone": _order_timezone_policy(order_column, order_timezone_aware),
        "missing_policy": missing_policy,
        "tie_policy": tie_policy,
        "trend_rule": {
            "code": "run_chart_trend",
            "definition": "strictly_monotonic_consecutive_points",
            "minimum_length": trend_min_length,
        },
        "oscillation_rule": {
            "code": "run_chart_oscillation",
            "definition": "strictly_alternating_consecutive_point_directions",
            "minimum_length": oscillation_min_length,
        },
        "runs_test": runs_test,
        "approximate_randomness_tests": approximate_randomness_tests,
        "warnings": warnings,
        "value": _column_payload(value_column),
        "order": _column_payload(order_column) if order_column is not None else None,
        "n_total": n_total,
        "n_used": n_used,
        "n_excluded_missing_value": n_excluded_missing_value,
        "n_excluded_non_numeric_value": n_excluded_non_numeric_value,
        "n_excluded_missing_order": n_excluded_missing_order,
        "n_excluded_non_numeric_order": n_excluded_non_numeric_order,
        "order_duplicate_count": order_duplicate_count,
        "center_line": center_line,
        "runs": run_summary,
        "signals": signals,
        "chart": _chart_payload(
            points,
            signals=signals,
            point_limit=point_limit,
            x_axis=x_axis,
        ),
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


def _parse_order_value(
    value: str,
    order_column: RunChartColumn,
    *,
    decimal: str,
    thousands: str | None,
) -> float | _ParsedDateTimeOrder | None:
    if order_column.data_type in DATETIME_ORDER_TYPES:
        return _parse_datetime_order(value.strip())
    return _parse_number(value, decimal=decimal, thousands=thousands)


def _parse_datetime_order(value: str) -> _ParsedDateTimeOrder | None:
    if not _looks_datetime_candidate(value):
        return None

    for format_pattern in DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(value, format_pattern)
        except ValueError:
            continue
        return _ParsedDateTimeOrder(value=parsed, timezone_aware=False)

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    timezone_aware = _datetime_has_timezone(parsed)
    return _ParsedDateTimeOrder(
        value=_datetime_order_value(parsed),
        timezone_aware=timezone_aware,
    )


def _looks_datetime_candidate(value: str) -> bool:
    if len(value) < 8:
        return False
    if not value[0].isdigit():
        return False
    return "-" in value or "/" in value or "." in value or "T" in value


def _datetime_has_timezone(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _datetime_order_value(value: datetime) -> datetime:
    if _datetime_has_timezone(value):
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _order_sort_key(candidate: _RunChartCandidate) -> tuple[float | datetime, int]:
    if candidate.order_value is None:
        raise RunChartError("run_chart_internal_order_invalid")
    return candidate.order_value, candidate.canonical_position


def _order_timezone_policy(
    order_column: RunChartColumn | None,
    timezone_aware: bool | None,
) -> str | None:
    if order_column is None or order_column.data_type not in DATETIME_ORDER_TYPES:
        return None
    return "timezone_aware_utc" if timezone_aware else "timezone_naive"


def _median(sorted_values: Sequence[float]) -> float:
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2


def _duplicate_count(values: Sequence[float | datetime]) -> int:
    seen: set[float | datetime] = set()
    duplicate_count = 0
    for value in values:
        if value in seen:
            duplicate_count += 1
        else:
            seen.add(value)
    return duplicate_count


def _relative_to_center(value: float, center_line: float) -> str:
    if value > center_line:
        return "above"
    if value < center_line:
        return "below"
    return "tie"


def _run_summary(points: Sequence[_RunChartPoint]) -> dict[str, object]:
    signs = [point.relative_to_center for point in points if point.relative_to_center != "tie"]
    n_above = signs.count("above")
    n_below = signs.count("below")
    n_ties = len(points) - len(signs)
    if not signs:
        return {
            "run_count": 0,
            "n_above": 0,
            "n_below": 0,
            "n_ties": n_ties,
            "longest_run_length": 0,
            "run_count_definition": "consecutive above/below median groups excluding ties",
        }

    run_count = 1
    longest_run_length = 1
    current_run_length = 1
    previous = signs[0]
    for sign in signs[1:]:
        if sign == previous:
            current_run_length += 1
        else:
            run_count += 1
            longest_run_length = max(longest_run_length, current_run_length)
            current_run_length = 1
            previous = sign
    longest_run_length = max(longest_run_length, current_run_length)
    return {
        "run_count": run_count,
        "n_above": n_above,
        "n_below": n_below,
        "n_ties": n_ties,
        "longest_run_length": longest_run_length,
        "run_count_definition": "consecutive above/below median groups excluding ties",
    }


def _int_summary_value(summary: dict[str, object], key: str) -> int:
    value = summary[key]
    if not isinstance(value, int):
        raise RunChartError("run_chart_internal_summary_invalid")
    return value


def _runs_test(
    points: Sequence[_RunChartPoint],
    run_summary: dict[str, object],
    *,
    alpha: float,
) -> dict[str, object]:
    run_count = _int_summary_value(run_summary, "run_count")
    n_above = _int_summary_value(run_summary, "n_above")
    n_below = _int_summary_value(run_summary, "n_below")
    n_ties = _int_summary_value(run_summary, "n_ties")
    n_non_tie = n_above + n_below
    payload: dict[str, object] = {
        "method": "exact_conditional_run_count_distribution",
        "alpha": alpha,
        "available": False,
        "observed_run_count": run_count,
        "n_above": n_above,
        "n_below": n_below,
        "n_ties": n_ties,
        "n_non_tie": n_non_tie,
        "expected_run_count": None,
        "variance": None,
        "p_value_low": None,
        "p_value_high": None,
        "interpretation": "not_available",
        "skipped_reason": None,
        "max_exact_n": MAX_EXACT_RUNS_TEST_N,
    }

    if n_above == 0 or n_below == 0:
        payload["skipped_reason"] = "one_side_absent"
        return payload
    if n_non_tie > MAX_EXACT_RUNS_TEST_N:
        payload["skipped_reason"] = "non_tie_count_exceeds_exact_limit"
        return payload

    p_value_low, p_value_high = _run_count_tail_probabilities(
        n_above=n_above,
        n_below=n_below,
        observed_run_count=run_count,
    )
    interpretation = "not_extreme"
    if p_value_low <= alpha:
        interpretation = "clustering"
    elif p_value_high <= alpha:
        interpretation = "mixture"

    payload.update(
        {
            "available": True,
            "expected_run_count": 1 + (2 * n_above * n_below / n_non_tie),
            "variance": (
                2
                * n_above
                * n_below
                * ((2 * n_above * n_below) - n_above - n_below)
                / ((n_non_tie**2) * (n_non_tie - 1))
            ),
            "p_value_low": p_value_low,
            "p_value_high": p_value_high,
            "interpretation": interpretation,
        },
    )
    return payload


def _approximate_randomness_tests(
    points: Sequence[_RunChartPoint],
    *,
    center_line: float,
    alpha: float,
) -> dict[str, object]:
    return {
        "alpha": alpha,
        "about_median": _approximate_runs_about_median(points, center_line=center_line),
        "up_down": _approximate_runs_up_down(points),
    }


def _approximate_runs_about_median(
    points: Sequence[_RunChartPoint],
    *,
    center_line: float,
) -> dict[str, object]:
    sides = [1 if point.value > center_line else -1 for point in points]
    n_above = sides.count(1)
    n_at_or_below = len(sides) - n_above
    observed_runs = _direction_run_count(sides)
    payload: dict[str, object] = {
        "method": "normal_approximation_runs_about_median",
        "available": False,
        "skipped_reason": None,
        "observed_runs": observed_runs,
        "expected_runs": None,
        "variance": None,
        "z": None,
        "n_above": n_above,
        "n_at_or_below": n_at_or_below,
        "tie_policy": "center_is_below",
        "p_value_clustering": None,
        "p_value_mixture": None,
    }
    total = len(sides)
    if total < MIN_N:
        payload["skipped_reason"] = "insufficient_points"
        return payload
    if n_above == 0 or n_at_or_below == 0:
        payload["skipped_reason"] = "one_side_absent"
        return payload

    expected_runs = 1 + (2 * n_above * n_at_or_below / total)
    variance = (
        2
        * n_above
        * n_at_or_below
        * ((2 * n_above * n_at_or_below) - total)
        / ((total**2) * (total - 1))
    )
    if not isfinite(variance) or variance <= 0:
        payload["skipped_reason"] = "non_positive_variance"
        return payload
    z = (observed_runs - expected_runs) / variance**0.5
    if not isfinite(z):
        payload["skipped_reason"] = "non_finite_standardized_statistic"
        return payload
    p_value_clustering = _clamp_probability(NormalDist().cdf(z))
    payload.update(
        {
            "available": True,
            "expected_runs": expected_runs,
            "variance": variance,
            "z": z,
            "p_value_clustering": p_value_clustering,
            "p_value_mixture": 1.0 - p_value_clustering,
        },
    )
    return payload


def _approximate_runs_up_down(points: Sequence[_RunChartPoint]) -> dict[str, object]:
    directions = [
        1 if points[index].value > points[index - 1].value else -1
        for index in range(1, len(points))
    ]
    observed_runs = _direction_run_count(directions)
    total = len(points)
    payload: dict[str, object] = {
        "method": "normal_approximation_runs_up_down",
        "available": False,
        "skipped_reason": None,
        "observed_runs": observed_runs,
        "expected_runs": None,
        "variance": None,
        "z": None,
        "n_points": total,
        "flat_policy": "flat_as_down",
        "p_value_trend": None,
        "p_value_oscillation": None,
    }
    if total < MIN_N:
        payload["skipped_reason"] = "insufficient_points"
        return payload
    if len({point.value for point in points}) == 1:
        payload["skipped_reason"] = "all_values_equal"
        return payload

    expected_runs = (2 * total - 1) / 3
    variance = (16 * total - 29) / 90
    if not isfinite(variance) or variance <= 0:
        payload["skipped_reason"] = "non_positive_variance"
        return payload
    z = (observed_runs - expected_runs) / variance**0.5
    if not isfinite(z):
        payload["skipped_reason"] = "non_finite_standardized_statistic"
        return payload
    p_value_trend = _clamp_probability(NormalDist().cdf(z))
    payload.update(
        {
            "available": True,
            "expected_runs": expected_runs,
            "variance": variance,
            "z": z,
            "p_value_trend": p_value_trend,
            "p_value_oscillation": 1.0 - p_value_trend,
        },
    )
    return payload


def _direction_run_count(directions: Sequence[int]) -> int:
    if not directions:
        return 0
    return 1 + sum(
        directions[index] != directions[index - 1] for index in range(1, len(directions))
    )


def _run_count_tail_probabilities(
    *,
    n_above: int,
    n_below: int,
    observed_run_count: int,
) -> tuple[float, float]:
    n = n_above + n_below
    log_total = _log_comb(n, n_above)
    low_terms: list[float] = []
    high_terms: list[float] = []
    for run_count in range(1, n + 1):
        log_count = _run_count_log_sequence_count(n_above, n_below, run_count)
        if log_count == float("-inf"):
            continue
        probability = exp(log_count - log_total)
        if run_count <= observed_run_count:
            low_terms.append(probability)
        if run_count >= observed_run_count:
            high_terms.append(probability)
    return _clamp_probability(fsum(low_terms)), _clamp_probability(fsum(high_terms))


def _run_count_log_sequence_count(n_above: int, n_below: int, run_count: int) -> float:
    if run_count <= 0:
        return float("-inf")
    if run_count % 2 == 0:
        groups_per_side = run_count // 2
        return (
            log(2)
            + _log_comb(n_above - 1, groups_per_side - 1)
            + _log_comb(n_below - 1, groups_per_side - 1)
        )

    above_groups = (run_count + 1) // 2
    below_groups = run_count // 2
    above_start_log_count = _safe_log_product(
        _log_comb(n_above - 1, above_groups - 1),
        _log_comb(n_below - 1, below_groups - 1),
    )
    below_start_log_count = _safe_log_product(
        _log_comb(n_above - 1, below_groups - 1),
        _log_comb(n_below - 1, above_groups - 1),
    )
    return _log_add(above_start_log_count, below_start_log_count)


def _safe_log_product(left: float, right: float) -> float:
    if left == float("-inf") or right == float("-inf"):
        return float("-inf")
    return left + right


def _log_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)


def _log_add(left: float, right: float) -> float:
    if left == float("-inf"):
        return right
    if right == float("-inf"):
        return left
    high = max(left, right)
    low = min(left, right)
    return high + log(1 + exp(low - high))


def _clamp_probability(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def _runs_test_signals(
    points: Sequence[_RunChartPoint],
    runs_test: dict[str, object],
) -> list[dict[str, object]]:
    if runs_test.get("available") is not True:
        return []

    alpha = runs_test.get("alpha")
    p_value_low = runs_test.get("p_value_low")
    p_value_high = runs_test.get("p_value_high")
    if not (
        isinstance(alpha, float)
        and isinstance(p_value_low, float)
        and isinstance(p_value_high, float)
    ):
        raise RunChartError("run_chart_internal_runs_test_invalid")

    non_tie_points = [point for point in points if point.relative_to_center != "tie"]
    if not non_tie_points:
        return []

    signals: list[dict[str, object]] = []
    if p_value_low <= alpha:
        signals.append(
            _runs_test_signal(
                "clustering-1",
                "run_chart_clustering",
                "low_runs",
                "exact_low_run_count_given_above_below_counts",
                non_tie_points,
            ),
        )
    if p_value_high <= alpha:
        signals.append(
            _runs_test_signal(
                "mixture-1",
                "run_chart_mixture",
                "high_runs",
                "exact_high_run_count_given_above_below_counts",
                non_tie_points,
            ),
        )
    return signals


def _runs_test_signal(
    signal_id: str,
    code: str,
    direction: str,
    definition: str,
    non_tie_points: Sequence[_RunChartPoint],
) -> dict[str, object]:
    return {
        "signal_id": signal_id,
        "code": code,
        "severity": "warning",
        "direction": direction,
        "length": len(non_tie_points),
        "start_position": non_tie_points[0].position,
        "end_position": non_tie_points[-1].position,
        "definition": definition,
    }


def _trend_signals(
    points: Sequence[_RunChartPoint],
    *,
    min_length: int,
) -> list[dict[str, object]]:
    if len(points) < min_length:
        return []

    signals: list[dict[str, object]] = []
    start_index = 0
    direction: str | None = None

    for index in range(1, len(points)):
        next_direction = _point_direction(points[index - 1], points[index])
        if next_direction is None:
            _append_trend_signal(signals, points, start_index, index - 1, direction, min_length)
            start_index = index
            direction = None
            continue

        if direction is None:
            start_index = index - 1
            direction = next_direction
            continue

        if next_direction != direction:
            _append_trend_signal(signals, points, start_index, index - 1, direction, min_length)
            start_index = index - 1
            direction = next_direction

    _append_trend_signal(signals, points, start_index, len(points) - 1, direction, min_length)
    return signals


def _point_direction(left: _RunChartPoint, right: _RunChartPoint) -> str | None:
    if right.value > left.value:
        return "increasing"
    if right.value < left.value:
        return "decreasing"
    return None


def _append_trend_signal(
    signals: list[dict[str, object]],
    points: Sequence[_RunChartPoint],
    start_index: int,
    end_index: int,
    direction: str | None,
    min_length: int,
) -> None:
    length = end_index - start_index + 1
    if direction is None or length < min_length:
        return
    signal_number = len(signals) + 1
    signals.append(
        {
            "signal_id": f"trend-{signal_number}",
            "code": "run_chart_trend",
            "severity": "warning",
            "direction": direction,
            "length": length,
            "start_position": points[start_index].position,
            "end_position": points[end_index].position,
            "definition": "strictly_monotonic_consecutive_points",
        },
    )


def _oscillation_signals(
    points: Sequence[_RunChartPoint],
    *,
    min_length: int,
) -> list[dict[str, object]]:
    if len(points) < min_length:
        return []

    signals: list[dict[str, object]] = []
    start_index = 0
    previous_direction: str | None = None

    for index in range(1, len(points)):
        direction = _point_direction(points[index - 1], points[index])
        if direction is None:
            _append_oscillation_signal(signals, points, start_index, index - 1, min_length)
            start_index = index
            previous_direction = None
            continue

        if previous_direction is None:
            start_index = index - 1
            previous_direction = direction
            continue

        if direction == previous_direction:
            _append_oscillation_signal(signals, points, start_index, index - 1, min_length)
            start_index = index - 1
        previous_direction = direction

    _append_oscillation_signal(signals, points, start_index, len(points) - 1, min_length)
    return signals


def _append_oscillation_signal(
    signals: list[dict[str, object]],
    points: Sequence[_RunChartPoint],
    start_index: int,
    end_index: int,
    min_length: int,
) -> None:
    length = end_index - start_index + 1
    if length < min_length:
        return
    signal_number = len(signals) + 1
    signals.append(
        {
            "signal_id": f"oscillation-{signal_number}",
            "code": "run_chart_oscillation",
            "severity": "warning",
            "direction": "alternating",
            "length": length,
            "start_position": points[start_index].position,
            "end_position": points[end_index].position,
            "definition": "strictly_alternating_consecutive_point_directions",
        },
    )


def _chart_payload(
    points: Sequence[_RunChartPoint],
    *,
    signals: Sequence[dict[str, object]],
    point_limit: int,
    x_axis: str,
) -> dict[str, object]:
    selected_indices, truncated = _selected_point_indices(len(points), point_limit)
    return {
        "x_axis": x_axis,
        "point_count": len(points),
        "points_truncated": truncated,
        "point_limit": point_limit,
        "points": [_point_payload(points[index], signals, x_axis) for index in selected_indices],
    }


def _point_payload(
    point: _RunChartPoint,
    signals: Sequence[dict[str, object]],
    x_axis: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "position": point.position,
        "value": point.value,
        "relative_to_center": point.relative_to_center,
        "signal_codes": _signal_codes_for_position(point.position, signals),
    }
    if x_axis == "order_rank":
        payload["canonical_position"] = point.canonical_position
    return payload


def _selected_point_indices(n: int, point_limit: int) -> tuple[list[int], bool]:
    if n <= point_limit:
        return list(range(n)), False
    if point_limit <= 1:
        return [0], True

    indices = {round(position * (n - 1) / (point_limit - 1)) for position in range(point_limit)}
    return sorted(indices), True


def _signal_codes_for_position(
    position: int,
    signals: Sequence[dict[str, object]],
) -> list[str]:
    codes: list[str] = []
    for signal in signals:
        start_position = signal.get("start_position")
        end_position = signal.get("end_position")
        code = signal.get("code")
        if (
            isinstance(start_position, int)
            and isinstance(end_position, int)
            and isinstance(code, str)
            and start_position <= position <= end_position
        ):
            codes.append(code)
    return codes


def _result_warnings(
    *,
    n_excluded_missing_value: int,
    n_excluded_non_numeric_value: int,
    n_excluded_missing_order: int,
    n_excluded_non_numeric_order: int,
    n_ties: int,
    has_order_column: bool,
    has_datetime_order_column: bool,
    order_duplicate_count: int,
    runs_test: dict[str, object],
    signals: Sequence[dict[str, object]],
    point_count: int,
    point_limit: int,
) -> list[str]:
    warnings = [
        "run_chart_not_control_chart",
        _order_warning_code(has_order_column, has_datetime_order_column),
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
    ]
    if runs_test.get("available") is not True:
        warnings.append("run_chart_runs_test_unavailable")
    if n_excluded_missing_value > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_value > 0:
        warnings.append("non_numeric_values_excluded")
    if n_excluded_missing_order > 0:
        warnings.append("run_chart_order_missing_excluded")
    if n_excluded_non_numeric_order > 0:
        warnings.append(
            "run_chart_order_invalid_datetime_excluded"
            if has_datetime_order_column
            else "run_chart_order_non_numeric_excluded",
        )
    if order_duplicate_count > 0:
        warnings.append("run_chart_order_ties_stable_sorted")
    if n_ties > 0:
        warnings.append("run_chart_ties_excluded_from_runs")
    if _has_signal(signals, "run_chart_trend"):
        warnings.append("run_chart_trend_signal_detected")
    if _has_signal(signals, "run_chart_oscillation"):
        warnings.append("run_chart_oscillation_signal_detected")
    if _has_signal(signals, "run_chart_clustering"):
        warnings.append("run_chart_clustering_signal_detected")
    if _has_signal(signals, "run_chart_mixture"):
        warnings.append("run_chart_mixture_signal_detected")
    if point_count > point_limit:
        warnings.append("run_chart_points_truncated")
    return warnings


def _has_signal(signals: Sequence[dict[str, object]], code: str) -> bool:
    return any(signal.get("code") == code for signal in signals)


def _order_warning_code(has_order_column: bool, has_datetime_order_column: bool) -> str:
    if not has_order_column:
        return "run_chart_uses_canonical_row_order"
    if has_datetime_order_column:
        return "run_chart_uses_datetime_order_column"
    return "run_chart_uses_numeric_order_column"


def _column_payload(column: RunChartColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }
