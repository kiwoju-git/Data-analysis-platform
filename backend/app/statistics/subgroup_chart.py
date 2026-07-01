from collections import OrderedDict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite, sqrt

MIN_SUBGROUP_COUNT = 2
MIN_SUBGROUP_SIZE = 2
DEFAULT_POINT_LIMIT = 1000

# Standard Xbar-R chart constants for fixed subgroup sizes 2-10.
# These are the conventional A2/D3/D4 constants used with average subgroup range.
XBAR_R_CONSTANTS: dict[int, dict[str, float]] = {
    2: {"a2": 1.880, "d3": 0.0, "d4": 3.267},
    3: {"a2": 1.023, "d3": 0.0, "d4": 2.574},
    4: {"a2": 0.729, "d3": 0.0, "d4": 2.282},
    5: {"a2": 0.577, "d3": 0.0, "d4": 2.114},
    6: {"a2": 0.483, "d3": 0.0, "d4": 2.004},
    7: {"a2": 0.419, "d3": 0.076, "d4": 1.924},
    8: {"a2": 0.373, "d3": 0.136, "d4": 1.864},
    9: {"a2": 0.337, "d3": 0.184, "d4": 1.816},
    10: {"a2": 0.308, "d3": 0.223, "d4": 1.777},
}

# Standard Xbar-S chart constants for fixed subgroup sizes 2-10.
# These are the conventional A3/B3/B4 constants used with average subgroup sample SD.
XBAR_S_CONSTANTS: dict[int, dict[str, float]] = {
    2: {"a3": 2.659, "b3": 0.0, "b4": 3.267},
    3: {"a3": 1.954, "b3": 0.0, "b4": 2.568},
    4: {"a3": 1.628, "b3": 0.0, "b4": 2.266},
    5: {"a3": 1.427, "b3": 0.0, "b4": 2.089},
    6: {"a3": 1.287, "b3": 0.030, "b4": 1.970},
    7: {"a3": 1.182, "b3": 0.118, "b4": 1.882},
    8: {"a3": 1.099, "b3": 0.185, "b4": 1.815},
    9: {"a3": 1.032, "b3": 0.239, "b4": 1.761},
    10: {"a3": 0.975, "b3": 0.284, "b4": 1.716},
}


class SubgroupChartError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SubgroupChartColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _SubgroupObservation:
    canonical_position: int
    value: float


@dataclass(frozen=True)
class _SubgroupPoint:
    position: int
    subgroup_label: str
    first_canonical_position: int
    last_canonical_position: int
    n: int
    mean: float
    range_value: float
    stddev: float


def calculate_subgroup_chart(
    rows: Iterable[Sequence[str | None]],
    value_column: SubgroupChartColumn,
    subgroup_column: SubgroupChartColumn,
    *,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    chart_type: str = "xbar_r",
    point_limit: int = DEFAULT_POINT_LIMIT,
) -> dict[str, object]:
    if chart_type not in {"xbar_r", "xbar_s"}:
        raise SubgroupChartError("subgroup_chart_type_unsupported")
    if missing_policy != "complete_case":
        raise SubgroupChartError("subgroup_chart_missing_policy_unsupported")
    if point_limit <= 0:
        raise SubgroupChartError("invalid_subgroup_chart_point_limit")

    n_total = 0
    n_excluded_missing_value = 0
    n_excluded_non_numeric_value = 0
    n_excluded_missing_subgroup = 0
    grouped: OrderedDict[str, list[_SubgroupObservation]] = OrderedDict()

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

        raw_subgroup = _row_value(row, subgroup_column.column_index)
        if raw_subgroup is None or raw_subgroup.strip() == "":
            n_excluded_missing_subgroup += 1
            continue
        subgroup_label = raw_subgroup.strip()
        grouped.setdefault(subgroup_label, []).append(
            _SubgroupObservation(canonical_position=n_total, value=parsed_value),
        )

    subgroup_count = len(grouped)
    if subgroup_count < MIN_SUBGROUP_COUNT:
        raise SubgroupChartError("subgroup_chart_subgroup_count_too_small")

    subgroup_sizes = [len(observations) for observations in grouped.values()]
    if any(size < MIN_SUBGROUP_SIZE for size in subgroup_sizes):
        raise SubgroupChartError("subgroup_chart_subgroup_size_too_small")
    if len(set(subgroup_sizes)) > 1:
        raise SubgroupChartError("subgroup_chart_varying_subgroup_size_unsupported")

    subgroup_size = subgroup_sizes[0]
    constants = _chart_constants(chart_type, subgroup_size)
    if constants is None:
        raise SubgroupChartError("subgroup_chart_subgroup_size_unsupported")

    points = _subgroup_points(grouped)
    grand_mean = sum(point.mean for point in points) / subgroup_count
    if chart_type == "xbar_r":
        average_dispersion = sum(point.range_value for point in points) / subgroup_count
        if average_dispersion <= 0:
            raise SubgroupChartError("subgroup_chart_zero_average_range")
        xbar_lcl = grand_mean - (constants["a2"] * average_dispersion)
        xbar_ucl = grand_mean + (constants["a2"] * average_dispersion)
        dispersion_lcl = constants["d3"] * average_dispersion
        dispersion_ucl = constants["d4"] * average_dispersion
        dispersion_chart = "r"
        dispersion_signal_code = "subgroup_chart_r_beyond_control_limits"
        dispersion_signal_definition = "one_subgroup_range_outside_r_control_limits"
        method = "xbar_r_chart"
        constants_payload = {
            "source": "standard_xbar_r_constants",
            "subgroup_size": subgroup_size,
            "a2": constants["a2"],
            "d3": constants["d3"],
            "d4": constants["d4"],
        }
    else:
        average_dispersion = sum(point.stddev for point in points) / subgroup_count
        if average_dispersion <= 0:
            raise SubgroupChartError("subgroup_chart_zero_average_stddev")
        xbar_lcl = grand_mean - (constants["a3"] * average_dispersion)
        xbar_ucl = grand_mean + (constants["a3"] * average_dispersion)
        dispersion_lcl = constants["b3"] * average_dispersion
        dispersion_ucl = constants["b4"] * average_dispersion
        dispersion_chart = "s"
        dispersion_signal_code = "subgroup_chart_s_beyond_control_limits"
        dispersion_signal_definition = "one_subgroup_stddev_outside_s_control_limits"
        method = "xbar_s_chart"
        constants_payload = {
            "source": "standard_xbar_s_constants",
            "subgroup_size": subgroup_size,
            "a3": constants["a3"],
            "b3": constants["b3"],
            "b4": constants["b4"],
            "stddev_definition": "sample_standard_deviation_n_minus_1",
        }

    signals = [
        *_xbar_limit_signals(points, lcl=xbar_lcl, ucl=xbar_ucl),
        *_dispersion_limit_signals(
            points,
            chart=dispersion_chart,
            code=dispersion_signal_code,
            lcl=dispersion_lcl,
            ucl=dispersion_ucl,
        ),
    ]
    warnings = _result_warnings(
        n_excluded_missing_value=n_excluded_missing_value,
        n_excluded_non_numeric_value=n_excluded_non_numeric_value,
        n_excluded_missing_subgroup=n_excluded_missing_subgroup,
        signals=signals,
        point_count=subgroup_count,
        point_limit=point_limit,
        chart_type=chart_type,
    )

    result = {
        "schema_version": 1,
        "summary_type": "subgroup_chart",
        "method": method,
        "chart_type": chart_type,
        "order_source": "canonical_subgroup_first_seen",
        "missing_policy": missing_policy,
        "subgroup_size": subgroup_size,
        "subgroup_count": subgroup_count,
        "constants": constants_payload,
        "control_rules": [
            {
                "code": "subgroup_chart_xbar_beyond_control_limits",
                "chart": "xbar",
                "definition": "one_subgroup_mean_outside_xbar_control_limits",
                "enabled": True,
            },
            {
                "code": dispersion_signal_code,
                "chart": dispersion_chart,
                "definition": dispersion_signal_definition,
                "enabled": True,
            },
        ],
        "warnings": warnings,
        "value": _column_payload(value_column),
        "subgroup": _column_payload(subgroup_column),
        "n_total": n_total,
        "n_used": sum(subgroup_sizes),
        "n_excluded_missing_value": n_excluded_missing_value,
        "n_excluded_non_numeric_value": n_excluded_non_numeric_value,
        "n_excluded_missing_subgroup": n_excluded_missing_subgroup,
        "subgroup_size_distribution": [
            {"size": size, "count": subgroup_sizes.count(size)}
            for size in sorted(set(subgroup_sizes))
        ],
        "xbar_chart": {
            "x_axis": "subgroup_position",
            "center_line": grand_mean,
            "lcl": xbar_lcl,
            "ucl": xbar_ucl,
            "point_count": subgroup_count,
            "points_truncated": subgroup_count > point_limit,
            "point_limit": point_limit,
            "points": _chart_points(points, signals=signals, chart="xbar", point_limit=point_limit),
        },
        "signals": signals,
    }
    result[f"{dispersion_chart}_chart"] = {
        "x_axis": "subgroup_position",
        "center_line": average_dispersion,
        "lcl": dispersion_lcl,
        "ucl": dispersion_ucl,
        "point_count": subgroup_count,
        "points_truncated": subgroup_count > point_limit,
        "point_limit": point_limit,
        "points": _chart_points(
            points,
            signals=signals,
            chart=dispersion_chart,
            point_limit=point_limit,
        ),
    }
    return result


def _chart_constants(chart_type: str, subgroup_size: int) -> dict[str, float] | None:
    if chart_type == "xbar_r":
        return XBAR_R_CONSTANTS.get(subgroup_size)
    if chart_type == "xbar_s":
        return XBAR_S_CONSTANTS.get(subgroup_size)
    raise SubgroupChartError("subgroup_chart_type_unsupported")


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


def _subgroup_points(
    grouped: OrderedDict[str, list[_SubgroupObservation]],
) -> list[_SubgroupPoint]:
    points: list[_SubgroupPoint] = []
    for index, (label, observations) in enumerate(grouped.items(), start=1):
        values = [observation.value for observation in observations]
        canonical_positions = [observation.canonical_position for observation in observations]
        mean = sum(values) / len(values)
        sample_variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        points.append(
            _SubgroupPoint(
                position=index,
                subgroup_label=label,
                first_canonical_position=min(canonical_positions),
                last_canonical_position=max(canonical_positions),
                n=len(values),
                mean=mean,
                range_value=max(values) - min(values),
                stddev=sqrt(sample_variance),
            ),
        )
    return points


def _xbar_limit_signals(
    points: Sequence[_SubgroupPoint],
    *,
    lcl: float,
    ucl: float,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for point in points:
        if point.mean < lcl or point.mean > ucl:
            signals.append(
                {
                    "signal_id": f"xbar-limit-{len(signals) + 1}",
                    "code": "subgroup_chart_xbar_beyond_control_limits",
                    "severity": "warning",
                    "chart": "xbar",
                    "position": point.position,
                    "subgroup_label": point.subgroup_label,
                    "first_canonical_position": point.first_canonical_position,
                    "last_canonical_position": point.last_canonical_position,
                    "value": point.mean,
                    "limit": "lower" if point.mean < lcl else "upper",
                    "definition": "one_subgroup_mean_outside_xbar_control_limits",
                },
            )
    return signals


def _dispersion_limit_signals(
    points: Sequence[_SubgroupPoint],
    *,
    chart: str,
    code: str,
    lcl: float,
    ucl: float,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for point in points:
        value = point.range_value if chart == "r" else point.stddev
        if value < lcl or value > ucl:
            signals.append(
                {
                    "signal_id": f"{chart}-limit-{len(signals) + 1}",
                    "code": code,
                    "severity": "warning",
                    "chart": chart,
                    "position": point.position,
                    "subgroup_label": point.subgroup_label,
                    "first_canonical_position": point.first_canonical_position,
                    "last_canonical_position": point.last_canonical_position,
                    "value": value,
                    "limit": "lower" if value < lcl else "upper",
                    "definition": (
                        "one_subgroup_range_outside_r_control_limits"
                        if chart == "r"
                        else "one_subgroup_stddev_outside_s_control_limits"
                    ),
                },
            )
    return signals


def _chart_points(
    points: Sequence[_SubgroupPoint],
    *,
    signals: Sequence[dict[str, object]],
    chart: str,
    point_limit: int,
) -> list[dict[str, object]]:
    selected_indices, _truncated = _selected_point_indices(len(points), point_limit)
    chart_points: list[dict[str, object]] = []
    for index in selected_indices:
        point = points[index]
        point_payload = {
            "position": points[index].position,
            "subgroup_label": points[index].subgroup_label,
            "first_canonical_position": points[index].first_canonical_position,
            "last_canonical_position": points[index].last_canonical_position,
            "n": points[index].n,
            "value": _chart_point_value(point, chart),
            "mean": points[index].mean,
            "range": points[index].range_value,
            "signal_codes": _signal_codes_for_position(
                points[index].position, signals, chart=chart
            ),
        }
        if chart == "s":
            point_payload["stddev"] = point.stddev
        chart_points.append(point_payload)
    return chart_points


def _chart_point_value(point: _SubgroupPoint, chart: str) -> float:
    if chart == "xbar":
        return point.mean
    if chart == "r":
        return point.range_value
    if chart == "s":
        return point.stddev
    raise SubgroupChartError("subgroup_chart_type_unsupported")


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
        if signal.get("position") == position:
            codes.append(code)
    return codes


def _result_warnings(
    *,
    n_excluded_missing_value: int,
    n_excluded_non_numeric_value: int,
    n_excluded_missing_subgroup: int,
    signals: Sequence[dict[str, object]],
    point_count: int,
    point_limit: int,
    chart_type: str,
) -> list[str]:
    warnings = [
        "subgroup_chart_uses_canonical_subgroup_order",
        (
            "subgroup_chart_control_limits_estimated_from_xbar_r_constants"
            if chart_type == "xbar_r"
            else "subgroup_chart_control_limits_estimated_from_xbar_s_constants"
        ),
        "subgroup_chart_rational_subgroups_not_proven",
    ]
    if n_excluded_missing_value > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric_value > 0:
        warnings.append("non_numeric_values_excluded")
    if n_excluded_missing_subgroup > 0:
        warnings.append("subgroup_chart_subgroup_missing_excluded")
    if _has_signal(signals, "subgroup_chart_xbar_beyond_control_limits"):
        warnings.append("subgroup_chart_xbar_limit_signal_detected")
    if _has_signal(signals, "subgroup_chart_r_beyond_control_limits"):
        warnings.append("subgroup_chart_r_limit_signal_detected")
    if _has_signal(signals, "subgroup_chart_s_beyond_control_limits"):
        warnings.append("subgroup_chart_s_limit_signal_detected")
    if point_count > point_limit:
        warnings.append("subgroup_chart_points_truncated")
    return warnings


def _has_signal(signals: Sequence[dict[str, object]], code: str) -> bool:
    return any(signal.get("code") == code for signal in signals)


def _column_payload(column: SubgroupChartColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }
