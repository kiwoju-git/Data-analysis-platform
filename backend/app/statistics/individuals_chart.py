from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from math import isfinite

MIN_N = 3
DEFAULT_POINT_LIMIT = 1000
DEFAULT_I_SAME_SIDE_MIN_LENGTH = 9
DEFAULT_I_TREND_MIN_LENGTH = 6
I_ALTERNATION_MIN_LENGTH = 14
I_TWO_OF_THREE_WINDOW_SIZE = 3
I_TWO_OF_THREE_MIN_COUNT = 2
I_TWO_OF_THREE_SIGMA_MULTIPLE = 2.0
I_FOUR_OF_FIVE_WINDOW_SIZE = 5
I_FOUR_OF_FIVE_MIN_COUNT = 4
I_FOUR_OF_FIVE_SIGMA_MULTIPLE = 1.0
I_FIFTEEN_WITHIN_ONE_SIGMA_MIN_LENGTH = 15
I_EIGHT_OUTSIDE_ONE_SIGMA_MIN_LENGTH = 8
I_ZONE_PATTERN_SIGMA_MULTIPLE = 1.0
INDIVIDUAL_MOVING_RANGE_D2 = 1.128
MOVING_RANGE_D3 = 0.0
MOVING_RANGE_D4 = 3.267
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


class IndividualsChartError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class IndividualsChartColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _IndividualsPoint:
    position: int
    canonical_position: int
    value: float


@dataclass(frozen=True)
class _MovingRangePoint:
    position: int
    previous_position: int
    canonical_position: int
    previous_canonical_position: int
    value: float


@dataclass(frozen=True)
class _IndividualsChartCandidate:
    canonical_position: int
    value: float
    order_value: float | datetime | None


@dataclass(frozen=True)
class _ParsedDateTimeOrder:
    value: datetime
    timezone_aware: bool


def calculate_individuals_chart(
    rows: Iterable[Sequence[str | None]],
    value_column: IndividualsChartColumn,
    *,
    order_column: IndividualsChartColumn | None = None,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    same_side_min_length: int = DEFAULT_I_SAME_SIDE_MIN_LENGTH,
    trend_min_length: int = DEFAULT_I_TREND_MIN_LENGTH,
    point_limit: int = DEFAULT_POINT_LIMIT,
) -> dict[str, object]:
    if missing_policy != "complete_case":
        raise IndividualsChartError("individuals_chart_missing_policy_unsupported")
    if same_side_min_length < 3:
        raise IndividualsChartError("invalid_individuals_chart_same_side_min_length")
    if trend_min_length < 3:
        raise IndividualsChartError("invalid_individuals_chart_trend_min_length")
    if point_limit <= 0:
        raise IndividualsChartError("invalid_individuals_chart_point_limit")

    n_total = 0
    n_excluded_missing_value = 0
    n_excluded_non_numeric_value = 0
    n_excluded_missing_order = 0
    n_excluded_non_numeric_order = 0
    order_timezone_aware: bool | None = None
    values: list[_IndividualsChartCandidate] = []

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
                    raise IndividualsChartError(
                        "individuals_chart_order_mixed_timezone_awareness",
                    )
                order_value = parsed_order.value
            else:
                order_value = parsed_order

        values.append(
            _IndividualsChartCandidate(
                canonical_position=n_total,
                value=parsed_value,
                order_value=order_value,
            ),
        )

    n_used = len(values)
    if n_used < MIN_N:
        raise IndividualsChartError("individuals_chart_n_too_small")

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

    points = [
        _IndividualsPoint(
            position=index if order_column is not None else candidate.canonical_position,
            canonical_position=candidate.canonical_position,
            value=candidate.value,
        )
        for index, candidate in enumerate(values, start=1)
    ]
    moving_ranges = _moving_range_points(points)
    mrbar = sum(point.value for point in moving_ranges) / len(moving_ranges)
    if mrbar <= 0:
        raise IndividualsChartError("individuals_chart_zero_moving_range")

    numeric_values = [point.value for point in points]
    center_line = sum(numeric_values) / n_used
    sigma_estimate = mrbar / INDIVIDUAL_MOVING_RANGE_D2
    individual_lcl = center_line - (3 * sigma_estimate)
    individual_ucl = center_line + (3 * sigma_estimate)
    moving_range_lcl = MOVING_RANGE_D3 * mrbar
    moving_range_ucl = MOVING_RANGE_D4 * mrbar

    signals = [
        *_individual_limit_signals(points, lcl=individual_lcl, ucl=individual_ucl),
        *_moving_range_limit_signals(moving_ranges, ucl=moving_range_ucl),
        *_same_side_centerline_signals(
            points,
            center_line=center_line,
            min_length=same_side_min_length,
        ),
        *_trend_signals(points, min_length=trend_min_length),
        *_alternating_signals(
            points,
            min_length=I_ALTERNATION_MIN_LENGTH,
        ),
        *_zone_rule_signals(
            points,
            center_line=center_line,
            sigma=sigma_estimate,
            sigma_multiple=I_TWO_OF_THREE_SIGMA_MULTIPLE,
            window_size=I_TWO_OF_THREE_WINDOW_SIZE,
            min_count=I_TWO_OF_THREE_MIN_COUNT,
            code="individuals_chart_i_two_of_three_beyond_2_sigma",
            signal_prefix="i-two-of-three",
            definition="two_of_three_consecutive_points_beyond_2_sigma_same_side",
        ),
        *_zone_rule_signals(
            points,
            center_line=center_line,
            sigma=sigma_estimate,
            sigma_multiple=I_FOUR_OF_FIVE_SIGMA_MULTIPLE,
            window_size=I_FOUR_OF_FIVE_WINDOW_SIZE,
            min_count=I_FOUR_OF_FIVE_MIN_COUNT,
            code="individuals_chart_i_four_of_five_beyond_1_sigma",
            signal_prefix="i-four-of-five",
            definition="four_of_five_consecutive_points_beyond_1_sigma_same_side",
        ),
        *_zone_pattern_signals(
            points,
            center_line=center_line,
            sigma=sigma_estimate,
            sigma_multiple=I_ZONE_PATTERN_SIGMA_MULTIPLE,
            min_length=I_FIFTEEN_WITHIN_ONE_SIGMA_MIN_LENGTH,
            mode="within",
            code="individuals_chart_i_fifteen_within_1_sigma",
            signal_prefix="i-fifteen-within-one-sigma",
            definition="fifteen_consecutive_points_within_1_sigma_centerline",
        ),
        *_zone_pattern_signals(
            points,
            center_line=center_line,
            sigma=sigma_estimate,
            sigma_multiple=I_ZONE_PATTERN_SIGMA_MULTIPLE,
            min_length=I_EIGHT_OUTSIDE_ONE_SIGMA_MIN_LENGTH,
            mode="outside",
            code="individuals_chart_i_eight_outside_1_sigma",
            signal_prefix="i-eight-outside-one-sigma",
            definition="eight_consecutive_points_outside_1_sigma_centerline",
        ),
    ]
    warnings = _result_warnings(
        n_excluded_missing_value=n_excluded_missing_value,
        n_excluded_non_numeric_value=n_excluded_non_numeric_value,
        n_excluded_missing_order=n_excluded_missing_order,
        n_excluded_non_numeric_order=n_excluded_non_numeric_order,
        has_order_column=order_column is not None,
        has_datetime_order_column=has_datetime_order_column,
        order_duplicate_count=order_duplicate_count,
        signals=signals,
        point_count=n_used,
        point_limit=point_limit,
    )

    return {
        "schema_version": 1,
        "summary_type": "individuals_chart",
        "method": "i_mr_chart",
        "order_source": order_source,
        "order_tie_breaker": "canonical_row_position" if order_column is not None else None,
        "order_timezone": _order_timezone_policy(order_column, order_timezone_aware),
        "missing_policy": missing_policy,
        "sigma_estimator": {
            "method": "average_moving_range_d2",
            "moving_range_length": 2,
            "d2": INDIVIDUAL_MOVING_RANGE_D2,
            "mrbar": mrbar,
            "sigma": sigma_estimate,
        },
        "control_rules": [
            {
                "code": "individuals_chart_i_beyond_3_sigma",
                "chart": "individuals",
                "definition": "one_point_outside_3_sigma_limits",
                "enabled": True,
            },
            {
                "code": "individuals_chart_mr_beyond_ucl",
                "chart": "moving_range",
                "definition": "one_moving_range_above_upper_control_limit",
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_same_side_centerline",
                "chart": "individuals",
                "definition": "consecutive_points_on_same_side_of_centerline",
                "minimum_length": same_side_min_length,
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_trend",
                "chart": "individuals",
                "definition": "strictly_monotonic_consecutive_points",
                "minimum_length": trend_min_length,
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_alternating",
                "chart": "individuals",
                "definition": "strictly_alternating_consecutive_point_directions",
                "minimum_length": I_ALTERNATION_MIN_LENGTH,
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_two_of_three_beyond_2_sigma",
                "chart": "individuals",
                "definition": "two_of_three_consecutive_points_beyond_2_sigma_same_side",
                "window_size": I_TWO_OF_THREE_WINDOW_SIZE,
                "minimum_count": I_TWO_OF_THREE_MIN_COUNT,
                "sigma_multiple": I_TWO_OF_THREE_SIGMA_MULTIPLE,
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_four_of_five_beyond_1_sigma",
                "chart": "individuals",
                "definition": "four_of_five_consecutive_points_beyond_1_sigma_same_side",
                "window_size": I_FOUR_OF_FIVE_WINDOW_SIZE,
                "minimum_count": I_FOUR_OF_FIVE_MIN_COUNT,
                "sigma_multiple": I_FOUR_OF_FIVE_SIGMA_MULTIPLE,
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_fifteen_within_1_sigma",
                "chart": "individuals",
                "definition": "fifteen_consecutive_points_within_1_sigma_centerline",
                "minimum_length": I_FIFTEEN_WITHIN_ONE_SIGMA_MIN_LENGTH,
                "sigma_multiple": I_ZONE_PATTERN_SIGMA_MULTIPLE,
                "enabled": True,
            },
            {
                "code": "individuals_chart_i_eight_outside_1_sigma",
                "chart": "individuals",
                "definition": "eight_consecutive_points_outside_1_sigma_centerline",
                "minimum_length": I_EIGHT_OUTSIDE_ONE_SIGMA_MIN_LENGTH,
                "sigma_multiple": I_ZONE_PATTERN_SIGMA_MULTIPLE,
                "enabled": True,
            },
        ],
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
        "individuals_chart": {
            "x_axis": x_axis,
            "center_line": center_line,
            "lcl": individual_lcl,
            "ucl": individual_ucl,
            "point_count": n_used,
            "points_truncated": n_used > point_limit,
            "point_limit": point_limit,
            "points": _individual_chart_points(
                points,
                signals=signals,
                point_limit=point_limit,
            ),
        },
        "moving_range_chart": {
            "x_axis": x_axis,
            "center_line": mrbar,
            "lcl": moving_range_lcl,
            "ucl": moving_range_ucl,
            "d3": MOVING_RANGE_D3,
            "d4": MOVING_RANGE_D4,
            "point_count": len(moving_ranges),
            "points_truncated": len(moving_ranges) > point_limit,
            "point_limit": point_limit,
            "points": _moving_range_chart_points(
                moving_ranges,
                signals=signals,
                point_limit=point_limit,
            ),
        },
        "signals": signals,
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
    order_column: IndividualsChartColumn,
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


def _order_sort_key(candidate: _IndividualsChartCandidate) -> tuple[float | datetime, int]:
    if candidate.order_value is None:
        raise IndividualsChartError("individuals_chart_internal_order_invalid")
    return candidate.order_value, candidate.canonical_position


def _order_timezone_policy(
    order_column: IndividualsChartColumn | None,
    timezone_aware: bool | None,
) -> str | None:
    if order_column is None or order_column.data_type not in DATETIME_ORDER_TYPES:
        return None
    return "timezone_aware_utc" if timezone_aware else "timezone_naive"


def _duplicate_count(values: Sequence[float | datetime]) -> int:
    seen: set[float | datetime] = set()
    duplicate_count = 0
    for value in values:
        if value in seen:
            duplicate_count += 1
        else:
            seen.add(value)
    return duplicate_count


def _moving_range_points(points: Sequence[_IndividualsPoint]) -> list[_MovingRangePoint]:
    moving_ranges: list[_MovingRangePoint] = []
    for index in range(1, len(points)):
        previous = points[index - 1]
        current = points[index]
        moving_ranges.append(
            _MovingRangePoint(
                position=current.position,
                previous_position=previous.position,
                canonical_position=current.canonical_position,
                previous_canonical_position=previous.canonical_position,
                value=abs(current.value - previous.value),
            ),
        )
    return moving_ranges


def _individual_limit_signals(
    points: Sequence[_IndividualsPoint],
    *,
    lcl: float,
    ucl: float,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for point in points:
        if point.value < lcl or point.value > ucl:
            signals.append(
                {
                    "signal_id": f"i-limit-{len(signals) + 1}",
                    "code": "individuals_chart_i_beyond_3_sigma",
                    "severity": "warning",
                    "chart": "individuals",
                    "position": point.position,
                    "canonical_position": point.canonical_position,
                    "value": point.value,
                    "limit": "lower" if point.value < lcl else "upper",
                    "definition": "one_point_outside_3_sigma_limits",
                },
            )
    return signals


def _moving_range_limit_signals(
    moving_ranges: Sequence[_MovingRangePoint],
    *,
    ucl: float,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for point in moving_ranges:
        if point.value > ucl:
            signals.append(
                {
                    "signal_id": f"mr-limit-{len(signals) + 1}",
                    "code": "individuals_chart_mr_beyond_ucl",
                    "severity": "warning",
                    "chart": "moving_range",
                    "position": point.position,
                    "previous_position": point.previous_position,
                    "canonical_position": point.canonical_position,
                    "previous_canonical_position": point.previous_canonical_position,
                    "value": point.value,
                    "limit": "upper",
                    "definition": "one_moving_range_above_upper_control_limit",
                },
            )
    return signals


def _same_side_centerline_signals(
    points: Sequence[_IndividualsPoint],
    *,
    center_line: float,
    min_length: int,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    run_start = 0
    run_side: str | None = None
    run_length = 0

    for index, point in enumerate(points):
        side = _centerline_side(point.value, center_line)
        if side is None:
            if run_side is not None and run_length >= min_length:
                signals.append(
                    _same_side_signal(
                        points,
                        start_index=run_start,
                        end_index=index - 1,
                        side=run_side,
                        signal_number=len(signals) + 1,
                    ),
                )
            run_side = None
            run_length = 0
            run_start = index + 1
            continue
        if side != run_side:
            if run_side is not None and run_length >= min_length:
                signals.append(
                    _same_side_signal(
                        points,
                        start_index=run_start,
                        end_index=index - 1,
                        side=run_side,
                        signal_number=len(signals) + 1,
                    ),
                )
            run_start = index
            run_side = side
            run_length = 1
            continue
        run_length += 1

    if run_side is not None and run_length >= min_length:
        signals.append(
            _same_side_signal(
                points,
                start_index=run_start,
                end_index=len(points) - 1,
                side=run_side,
                signal_number=len(signals) + 1,
            ),
        )
    return signals


def _centerline_side(value: float, center_line: float) -> str | None:
    if value > center_line:
        return "above"
    if value < center_line:
        return "below"
    return None


def _same_side_signal(
    points: Sequence[_IndividualsPoint],
    *,
    start_index: int,
    end_index: int,
    side: str,
    signal_number: int,
) -> dict[str, object]:
    start = points[start_index]
    end = points[end_index]
    return {
        "signal_id": f"i-same-side-{signal_number}",
        "code": "individuals_chart_i_same_side_centerline",
        "severity": "warning",
        "chart": "individuals",
        "direction": side,
        "length": end_index - start_index + 1,
        "start_position": start.position,
        "end_position": end.position,
        "position": end.position,
        "start_canonical_position": start.canonical_position,
        "canonical_position": end.canonical_position,
        "value": end.value,
        "definition": "consecutive_points_on_same_side_of_centerline",
    }


def _trend_signals(
    points: Sequence[_IndividualsPoint],
    *,
    min_length: int,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    if len(points) < min_length:
        return signals

    trend_start = 0
    trend_direction: str | None = None
    trend_length = 1
    for index in range(1, len(points)):
        direction = _adjacent_direction(points[index - 1].value, points[index].value)
        if direction is None:
            if trend_direction is not None and trend_length >= min_length:
                signals.append(
                    _trend_signal(
                        points,
                        start_index=trend_start,
                        end_index=index - 1,
                        direction=trend_direction,
                        signal_number=len(signals) + 1,
                    ),
                )
            trend_start = index
            trend_direction = None
            trend_length = 1
            continue
        if trend_direction is None or direction != trend_direction:
            if trend_direction is not None and trend_length >= min_length:
                signals.append(
                    _trend_signal(
                        points,
                        start_index=trend_start,
                        end_index=index - 1,
                        direction=trend_direction,
                        signal_number=len(signals) + 1,
                    ),
                )
            trend_start = index - 1
            trend_direction = direction
            trend_length = 2
            continue
        trend_length += 1

    if trend_direction is not None and trend_length >= min_length:
        signals.append(
            _trend_signal(
                points,
                start_index=trend_start,
                end_index=len(points) - 1,
                direction=trend_direction,
                signal_number=len(signals) + 1,
            ),
        )
    return signals


def _adjacent_direction(previous: float, current: float) -> str | None:
    if current > previous:
        return "increasing"
    if current < previous:
        return "decreasing"
    return None


def _trend_signal(
    points: Sequence[_IndividualsPoint],
    *,
    start_index: int,
    end_index: int,
    direction: str,
    signal_number: int,
) -> dict[str, object]:
    start = points[start_index]
    end = points[end_index]
    return {
        "signal_id": f"i-trend-{signal_number}",
        "code": "individuals_chart_i_trend",
        "severity": "warning",
        "chart": "individuals",
        "direction": direction,
        "length": end_index - start_index + 1,
        "start_position": start.position,
        "end_position": end.position,
        "position": end.position,
        "start_canonical_position": start.canonical_position,
        "canonical_position": end.canonical_position,
        "value": end.value,
        "definition": "strictly_monotonic_consecutive_points",
    }


def _alternating_signals(
    points: Sequence[_IndividualsPoint],
    *,
    min_length: int,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    if len(points) < min_length:
        return signals

    run_start = 0
    previous_direction: str | None = None
    run_length = 1
    for index in range(1, len(points)):
        direction = _adjacent_direction(points[index - 1].value, points[index].value)
        if direction is None:
            if previous_direction is not None and run_length >= min_length:
                signals.append(
                    _alternating_signal(
                        points,
                        start_index=run_start,
                        end_index=index - 1,
                        signal_number=len(signals) + 1,
                    ),
                )
            run_start = index
            previous_direction = None
            run_length = 1
            continue
        if previous_direction is None:
            previous_direction = direction
            run_length = 2
            continue
        if direction == previous_direction:
            if run_length >= min_length:
                signals.append(
                    _alternating_signal(
                        points,
                        start_index=run_start,
                        end_index=index - 1,
                        signal_number=len(signals) + 1,
                    ),
                )
            run_start = index - 1
            previous_direction = direction
            run_length = 2
            continue
        previous_direction = direction
        run_length += 1

    if previous_direction is not None and run_length >= min_length:
        signals.append(
            _alternating_signal(
                points,
                start_index=run_start,
                end_index=len(points) - 1,
                signal_number=len(signals) + 1,
            ),
        )
    return signals


def _alternating_signal(
    points: Sequence[_IndividualsPoint],
    *,
    start_index: int,
    end_index: int,
    signal_number: int,
) -> dict[str, object]:
    start = points[start_index]
    end = points[end_index]
    return {
        "signal_id": f"i-alternating-{signal_number}",
        "code": "individuals_chart_i_alternating",
        "severity": "warning",
        "chart": "individuals",
        "direction": "alternating",
        "length": end_index - start_index + 1,
        "start_position": start.position,
        "end_position": end.position,
        "position": end.position,
        "start_canonical_position": start.canonical_position,
        "canonical_position": end.canonical_position,
        "value": end.value,
        "definition": "strictly_alternating_consecutive_point_directions",
    }


def _zone_rule_signals(
    points: Sequence[_IndividualsPoint],
    *,
    center_line: float,
    sigma: float,
    sigma_multiple: float,
    window_size: int,
    min_count: int,
    code: str,
    signal_prefix: str,
    definition: str,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    start_index = 0
    upper_threshold = center_line + (sigma_multiple * sigma)
    lower_threshold = center_line - (sigma_multiple * sigma)
    while start_index <= len(points) - window_size:
        window = points[start_index : start_index + window_size]
        above_points = [point for point in window if point.value > upper_threshold]
        below_points = [point for point in window if point.value < lower_threshold]
        if len(above_points) >= min_count:
            signals.append(
                _zone_rule_signal(
                    window,
                    qualifying_points=above_points,
                    direction="above",
                    signal_number=len(signals) + 1,
                    code=code,
                    signal_prefix=signal_prefix,
                    definition=definition,
                    sigma_multiple=sigma_multiple,
                ),
            )
            start_index += window_size
            continue
        if len(below_points) >= min_count:
            signals.append(
                _zone_rule_signal(
                    window,
                    qualifying_points=below_points,
                    direction="below",
                    signal_number=len(signals) + 1,
                    code=code,
                    signal_prefix=signal_prefix,
                    definition=definition,
                    sigma_multiple=sigma_multiple,
                ),
            )
            start_index += window_size
            continue
        start_index += 1
    return signals


def _zone_rule_signal(
    window: Sequence[_IndividualsPoint],
    *,
    qualifying_points: Sequence[_IndividualsPoint],
    direction: str,
    signal_number: int,
    code: str,
    signal_prefix: str,
    definition: str,
    sigma_multiple: float,
) -> dict[str, object]:
    start = window[0]
    end = window[-1]
    last_qualifying = qualifying_points[-1]
    return {
        "signal_id": f"{signal_prefix}-{signal_number}",
        "code": code,
        "severity": "warning",
        "chart": "individuals",
        "direction": direction,
        "length": len(window),
        "count": len(qualifying_points),
        "sigma_multiple": sigma_multiple,
        "start_position": start.position,
        "end_position": end.position,
        "position": end.position,
        "positions": [point.position for point in qualifying_points],
        "start_canonical_position": start.canonical_position,
        "canonical_position": end.canonical_position,
        "canonical_positions": [point.canonical_position for point in qualifying_points],
        "value": last_qualifying.value,
        "definition": definition,
    }


def _zone_pattern_signals(
    points: Sequence[_IndividualsPoint],
    *,
    center_line: float,
    sigma: float,
    sigma_multiple: float,
    min_length: int,
    mode: str,
    code: str,
    signal_prefix: str,
    definition: str,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    start_index = 0
    threshold = sigma_multiple * sigma
    while start_index <= len(points) - min_length:
        window = points[start_index : start_index + min_length]
        if _zone_pattern_window_matches(
            window,
            center_line=center_line,
            threshold=threshold,
            mode=mode,
        ):
            signals.append(
                _zone_pattern_signal(
                    window,
                    direction=mode,
                    signal_number=len(signals) + 1,
                    code=code,
                    signal_prefix=signal_prefix,
                    definition=definition,
                    sigma_multiple=sigma_multiple,
                ),
            )
            start_index += min_length
            continue
        start_index += 1
    return signals


def _zone_pattern_window_matches(
    window: Sequence[_IndividualsPoint],
    *,
    center_line: float,
    threshold: float,
    mode: str,
) -> bool:
    distances = [abs(point.value - center_line) for point in window]
    if mode == "within":
        return all(distance <= threshold for distance in distances)
    if mode == "outside":
        return all(distance > threshold for distance in distances)
    raise IndividualsChartError("individuals_chart_internal_zone_pattern_invalid")


def _zone_pattern_signal(
    window: Sequence[_IndividualsPoint],
    *,
    direction: str,
    signal_number: int,
    code: str,
    signal_prefix: str,
    definition: str,
    sigma_multiple: float,
) -> dict[str, object]:
    start = window[0]
    end = window[-1]
    return {
        "signal_id": f"{signal_prefix}-{signal_number}",
        "code": code,
        "severity": "warning",
        "chart": "individuals",
        "direction": direction,
        "length": len(window),
        "count": len(window),
        "sigma_multiple": sigma_multiple,
        "start_position": start.position,
        "end_position": end.position,
        "position": end.position,
        "positions": [point.position for point in window],
        "start_canonical_position": start.canonical_position,
        "canonical_position": end.canonical_position,
        "canonical_positions": [point.canonical_position for point in window],
        "value": end.value,
        "definition": definition,
    }


def _individual_chart_points(
    points: Sequence[_IndividualsPoint],
    *,
    signals: Sequence[dict[str, object]],
    point_limit: int,
) -> list[dict[str, object]]:
    selected_indices, _truncated = _selected_point_indices(len(points), point_limit)
    return [
        {
            "position": points[index].position,
            "canonical_position": points[index].canonical_position,
            "value": points[index].value,
            "signal_codes": _signal_codes_for_position(
                points[index].position,
                signals,
                chart="individuals",
            ),
        }
        for index in selected_indices
    ]


def _moving_range_chart_points(
    points: Sequence[_MovingRangePoint],
    *,
    signals: Sequence[dict[str, object]],
    point_limit: int,
) -> list[dict[str, object]]:
    selected_indices, _truncated = _selected_point_indices(len(points), point_limit)
    return [
        {
            "position": points[index].position,
            "previous_position": points[index].previous_position,
            "canonical_position": points[index].canonical_position,
            "previous_canonical_position": points[index].previous_canonical_position,
            "value": points[index].value,
            "signal_codes": _signal_codes_for_position(
                points[index].position,
                signals,
                chart="moving_range",
            ),
        }
        for index in selected_indices
    ]


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
    *,
    chart: str,
) -> list[str]:
    codes: list[str] = []
    for signal in signals:
        signal_chart = signal.get("chart")
        code = signal.get("code")
        if signal_chart != chart or not isinstance(code, str):
            continue
        signal_positions = signal.get("positions")
        if isinstance(signal_positions, list):
            if position in signal_positions:
                codes.append(code)
            continue
        start_position = signal.get("start_position")
        end_position = signal.get("end_position")
        if isinstance(start_position, int) and isinstance(end_position, int):
            if start_position <= position <= end_position:
                codes.append(code)
            continue
        signal_position = signal.get("position")
        if signal_position == position:
            codes.append(code)
    return codes


def _result_warnings(
    *,
    n_excluded_missing_value: int,
    n_excluded_non_numeric_value: int,
    n_excluded_missing_order: int,
    n_excluded_non_numeric_order: int,
    has_order_column: bool,
    has_datetime_order_column: bool,
    order_duplicate_count: int,
    signals: Sequence[dict[str, object]],
    point_count: int,
    point_limit: int,
) -> list[str]:
    warnings = [
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
    ]
    if has_order_column:
        warnings.insert(
            0,
            (
                "individuals_chart_uses_datetime_order_column"
                if has_datetime_order_column
                else "individuals_chart_uses_numeric_order_column"
            ),
        )
    else:
        warnings.insert(0, "individuals_chart_uses_canonical_row_order")
    if n_excluded_missing_value > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_value > 0:
        warnings.append("non_numeric_values_excluded")
    if n_excluded_missing_order > 0:
        warnings.append("individuals_chart_order_missing_excluded")
    if n_excluded_non_numeric_order > 0:
        warnings.append(
            (
                "individuals_chart_order_invalid_datetime_excluded"
                if has_datetime_order_column
                else "individuals_chart_order_non_numeric_excluded"
            ),
        )
    if order_duplicate_count > 0:
        warnings.append("individuals_chart_order_ties_stable_sorted")
    if _has_signal(signals, "individuals_chart_i_beyond_3_sigma"):
        warnings.append("individuals_chart_i_limit_signal_detected")
    if _has_signal(signals, "individuals_chart_mr_beyond_ucl"):
        warnings.append("individuals_chart_mr_limit_signal_detected")
    if _has_signal(signals, "individuals_chart_i_same_side_centerline"):
        warnings.append("individuals_chart_i_same_side_signal_detected")
    if _has_signal(signals, "individuals_chart_i_trend"):
        warnings.append("individuals_chart_i_trend_signal_detected")
    if _has_signal(signals, "individuals_chart_i_alternating"):
        warnings.append("individuals_chart_i_alternating_signal_detected")
    if _has_signal(signals, "individuals_chart_i_two_of_three_beyond_2_sigma"):
        warnings.append("individuals_chart_i_two_of_three_signal_detected")
    if _has_signal(signals, "individuals_chart_i_four_of_five_beyond_1_sigma"):
        warnings.append("individuals_chart_i_four_of_five_signal_detected")
    if _has_signal(signals, "individuals_chart_i_fifteen_within_1_sigma"):
        warnings.append("individuals_chart_i_fifteen_within_1_sigma_signal_detected")
    if _has_signal(signals, "individuals_chart_i_eight_outside_1_sigma"):
        warnings.append("individuals_chart_i_eight_outside_1_sigma_signal_detected")
    if point_count > point_limit:
        warnings.append("individuals_chart_points_truncated")
    return warnings


def _has_signal(signals: Sequence[dict[str, object]], code: str) -> bool:
    return any(signal.get("code") == code for signal in signals)


def _column_payload(column: IndividualsChartColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }
