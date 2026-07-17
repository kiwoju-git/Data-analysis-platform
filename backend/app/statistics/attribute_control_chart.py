from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite, sqrt

DEFAULT_POINT_LIMIT = 1000
MIN_BASELINE_POINT_COUNT = 2
MIN_MONITORING_POINT_COUNT = 1
RECOMMENDED_BASELINE_POINT_COUNT = 20


class AttributeControlChartError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AttributeControlChartColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _AttributePoint:
    position: int
    canonical_position: int
    count: int
    denominator: float | None


@dataclass(frozen=True)
class _CollectedPoints:
    n_total: int
    n_excluded_missing_count: int
    n_excluded_non_numeric_count: int
    n_excluded_missing_denominator: int
    n_excluded_non_numeric_denominator: int
    points: list[_AttributePoint]


def calculate_attribute_control_chart(
    rows: Iterable[Sequence[str | None]],
    count_column: AttributeControlChartColumn,
    denominator_column: AttributeControlChartColumn | None,
    *,
    chart_type: str,
    count_definition: str,
    constant_opportunity_confirmed: bool = False,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    point_limit: int = DEFAULT_POINT_LIMIT,
) -> dict[str, object]:
    _validate_contract(
        chart_type=chart_type,
        count_definition=count_definition,
        denominator_column=denominator_column,
        constant_opportunity_confirmed=constant_opportunity_confirmed,
        missing_policy=missing_policy,
        point_limit=point_limit,
    )

    collected = _collect_attribute_points(
        rows,
        count_column=count_column,
        denominator_column=denominator_column,
        chart_type=chart_type,
        decimal=decimal,
        thousands=thousands,
    )
    points = collected.points

    if len(points) < MIN_BASELINE_POINT_COUNT:
        raise AttributeControlChartError("attribute_control_chart_point_count_too_small")

    if chart_type == "np":
        sample_sizes = {point.denominator for point in points}
        if len(sample_sizes) != 1:
            raise AttributeControlChartError("attribute_control_chart_np_varying_sample_size")

    center_line = _center_line(points, chart_type=chart_type)
    _validate_center_line(center_line, chart_type=chart_type)
    limits = [
        _point_limits(point, chart_type=chart_type, center_line=center_line) for point in points
    ]
    signals = _limit_signals(points, limits=limits, chart_type=chart_type)
    dispersion_ratio = _dispersion_ratio(points, chart_type=chart_type, center_line=center_line)
    warnings = _result_warnings(
        points=points,
        limits=limits,
        signals=signals,
        chart_type=chart_type,
        center_line=center_line,
        dispersion_ratio=dispersion_ratio,
        n_excluded_missing_count=collected.n_excluded_missing_count,
        n_excluded_non_numeric_count=collected.n_excluded_non_numeric_count,
        n_excluded_missing_denominator=collected.n_excluded_missing_denominator,
        n_excluded_non_numeric_denominator=collected.n_excluded_non_numeric_denominator,
        point_limit=point_limit,
    )

    denominators = [point.denominator for point in points if point.denominator is not None]
    limits_vary = len(set(denominators)) > 1 if chart_type in {"p", "u"} else False
    lcl_truncated_count = sum(1 for limit in limits if limit["lcl_truncated"])
    ucl_truncated_count = sum(1 for limit in limits if limit["ucl_truncated"])

    return {
        "schema_version": 1,
        "summary_type": "attribute_control_chart",
        "method": f"{chart_type}_chart",
        "chart_type": chart_type,
        "count_definition": count_definition,
        "distribution_assumption": "binomial" if chart_type in {"p", "np"} else "poisson",
        "control_limit_method": "phase_1_estimated_three_sigma",
        "baseline": "all_filtered_valid_points",
        "order_source": "canonical_row_order",
        "missing_policy": missing_policy,
        "constant_opportunity_confirmed": constant_opportunity_confirmed,
        "control_rules": [
            {
                "code": "attribute_control_chart_point_beyond_control_limits",
                "definition": "one_point_strictly_outside_three_sigma_control_limits",
                "enabled": True,
            }
        ],
        "warnings": warnings,
        "count": _column_payload(count_column),
        "denominator": _column_payload(denominator_column),
        "denominator_role": _denominator_role(chart_type),
        "n_total": collected.n_total,
        "n_used": len(points),
        "n_excluded_missing_count": collected.n_excluded_missing_count,
        "n_excluded_non_numeric_count": collected.n_excluded_non_numeric_count,
        "n_excluded_missing_denominator": collected.n_excluded_missing_denominator,
        "n_excluded_non_numeric_denominator": collected.n_excluded_non_numeric_denominator,
        "total_count": sum(point.count for point in points),
        "total_denominator": sum(denominators) if denominators else None,
        "center_line": center_line,
        "limits_vary": limits_vary,
        "lcl_truncated_count": lcl_truncated_count,
        "ucl_truncated_count": ucl_truncated_count,
        "dispersion": {
            "available": True,
            "method": "pearson_chi_square_over_degrees_of_freedom",
            "degrees_of_freedom": len(points) - 1,
            "ratio": dispersion_ratio,
            "reason_code": None,
            "warning_threshold": 2.0,
            "used_to_adjust_limits": False,
        },
        "chart": {
            "x_axis": "canonical_row_position",
            "y_axis": _y_axis(chart_type),
            "center_line": center_line,
            "limits_vary": limits_vary,
            "point_count": len(points),
            "points_truncated": len(points) > point_limit,
            "point_limit": point_limit,
            "points": _chart_points(
                points,
                limits=limits,
                signals=signals,
                chart_type=chart_type,
                point_limit=point_limit,
            ),
        },
        "signals": signals,
    }


def calculate_attribute_control_chart_phase_2(
    rows: Iterable[Sequence[str | None]],
    count_column: AttributeControlChartColumn,
    denominator_column: AttributeControlChartColumn | None,
    *,
    chart_type: str,
    count_definition: str,
    frozen_center_line: float,
    fixed_sample_size: int | None,
    constant_opportunity_confirmed: bool = False,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    point_limit: int = DEFAULT_POINT_LIMIT,
) -> dict[str, object]:
    _validate_contract(
        chart_type=chart_type,
        count_definition=count_definition,
        denominator_column=denominator_column,
        constant_opportunity_confirmed=(
            constant_opportunity_confirmed if chart_type != "c" else True
        ),
        missing_policy=missing_policy,
        point_limit=point_limit,
    )
    if chart_type == "c" and not constant_opportunity_confirmed:
        raise AttributeControlChartError(
            "attribute_control_chart_phase_2_c_opportunity_confirmation_required"
        )
    _validate_center_line(frozen_center_line, chart_type=chart_type)
    if chart_type == "np":
        if fixed_sample_size is None or frozen_center_line >= fixed_sample_size:
            raise AttributeControlChartError("attribute_control_chart_center_invalid")
    elif fixed_sample_size is not None:
        raise AttributeControlChartError("attribute_control_chart_center_invalid")

    collected = _collect_attribute_points(
        rows,
        count_column=count_column,
        denominator_column=denominator_column,
        chart_type=chart_type,
        decimal=decimal,
        thousands=thousands,
    )
    points = collected.points
    if len(points) < MIN_MONITORING_POINT_COUNT:
        raise AttributeControlChartError("attribute_control_chart_phase_2_no_usable_points")
    if chart_type == "np":
        assert fixed_sample_size is not None
        if any(point.denominator != float(fixed_sample_size) for point in points):
            raise AttributeControlChartError(
                "attribute_control_chart_phase_2_np_sample_size_mismatch"
            )

    limits = [
        _point_limits(point, chart_type=chart_type, center_line=frozen_center_line)
        for point in points
    ]
    signals = _limit_signals(points, limits=limits, chart_type=chart_type)
    dispersion_ratio = (
        None
        if len(points) == 1
        else _dispersion_ratio(
            points,
            chart_type=chart_type,
            center_line=frozen_center_line,
        )
    )
    warnings = _phase_2_warnings(
        points=points,
        limits=limits,
        signals=signals,
        chart_type=chart_type,
        center_line=frozen_center_line,
        dispersion_ratio=dispersion_ratio,
        collected=collected,
        point_limit=point_limit,
    )
    denominators = [point.denominator for point in points if point.denominator is not None]
    limits_vary = len(set(denominators)) > 1 if chart_type in {"p", "u"} else False

    return {
        "schema_version": 3,
        "phase": "phase_2",
        "summary_type": "attribute_control_chart",
        "method": f"{chart_type}_chart",
        "chart_type": chart_type,
        "count_definition": count_definition,
        "distribution_assumption": "binomial" if chart_type in {"p", "np"} else "poisson",
        "control_limit_method": "phase_2_frozen_three_sigma",
        "baseline": "verified_immutable_limit_set",
        "order_source": "canonical_row_order",
        "missing_policy": missing_policy,
        "constant_opportunity_confirmed": constant_opportunity_confirmed,
        "control_rules": [
            {
                "code": "attribute_control_chart_point_beyond_control_limits",
                "definition": "one_point_strictly_outside_three_sigma_control_limits",
                "enabled": True,
            }
        ],
        "warnings": warnings,
        "count": _column_payload(count_column),
        "denominator": _column_payload(denominator_column),
        "denominator_role": _denominator_role(chart_type),
        "n_total": collected.n_total,
        "n_used": len(points),
        "n_excluded_missing_count": collected.n_excluded_missing_count,
        "n_excluded_non_numeric_count": collected.n_excluded_non_numeric_count,
        "n_excluded_missing_denominator": collected.n_excluded_missing_denominator,
        "n_excluded_non_numeric_denominator": collected.n_excluded_non_numeric_denominator,
        "total_count": sum(point.count for point in points),
        "total_denominator": sum(denominators) if denominators else None,
        "center_line": frozen_center_line,
        "limits_vary": limits_vary,
        "lcl_truncated_count": sum(1 for limit in limits if limit["lcl_truncated"]),
        "ucl_truncated_count": sum(1 for limit in limits if limit["ucl_truncated"]),
        "dispersion": {
            "available": dispersion_ratio is not None,
            "method": "pearson_chi_square_over_degrees_of_freedom_against_frozen_center",
            "degrees_of_freedom": len(points) - 1,
            "ratio": dispersion_ratio,
            "reason_code": (
                None
                if dispersion_ratio is not None
                else "attribute_control_chart_dispersion_insufficient_points"
            ),
            "warning_threshold": 2.0,
            "used_to_adjust_limits": False,
        },
        "chart": {
            "x_axis": "canonical_row_position",
            "y_axis": _y_axis(chart_type),
            "center_line": frozen_center_line,
            "limits_vary": limits_vary,
            "point_count": len(points),
            "points_truncated": len(points) > point_limit,
            "point_limit": point_limit,
            "points": _chart_points(
                points,
                limits=limits,
                signals=signals,
                chart_type=chart_type,
                point_limit=point_limit,
            ),
        },
        "signals": signals,
    }


def _collect_attribute_points(
    rows: Iterable[Sequence[str | None]],
    *,
    count_column: AttributeControlChartColumn,
    denominator_column: AttributeControlChartColumn | None,
    chart_type: str,
    decimal: str,
    thousands: str | None,
) -> _CollectedPoints:
    n_total = 0
    n_excluded_missing_count = 0
    n_excluded_non_numeric_count = 0
    n_excluded_missing_denominator = 0
    n_excluded_non_numeric_denominator = 0
    points: list[_AttributePoint] = []
    for row in rows:
        n_total += 1
        raw_count = _row_value(row, count_column.column_index)
        if raw_count is None or raw_count.strip() == "":
            n_excluded_missing_count += 1
            continue
        parsed_count = _parse_decimal(raw_count, decimal=decimal, thousands=thousands)
        if parsed_count is None:
            n_excluded_non_numeric_count += 1
            continue
        count = _validated_count(parsed_count)
        denominator: float | None = None
        if denominator_column is not None:
            raw_denominator = _row_value(row, denominator_column.column_index)
            if raw_denominator is None or raw_denominator.strip() == "":
                n_excluded_missing_denominator += 1
                continue
            parsed_denominator = _parse_decimal(
                raw_denominator,
                decimal=decimal,
                thousands=thousands,
            )
            if parsed_denominator is None:
                n_excluded_non_numeric_denominator += 1
                continue
            denominator = _validated_denominator(parsed_denominator, chart_type=chart_type)
            if chart_type in {"p", "np"} and count > denominator:
                raise AttributeControlChartError(
                    "attribute_control_chart_defectives_exceed_sample_size"
                )
        points.append(
            _AttributePoint(
                position=len(points) + 1,
                canonical_position=n_total,
                count=count,
                denominator=denominator,
            )
        )
    return _CollectedPoints(
        n_total=n_total,
        n_excluded_missing_count=n_excluded_missing_count,
        n_excluded_non_numeric_count=n_excluded_non_numeric_count,
        n_excluded_missing_denominator=n_excluded_missing_denominator,
        n_excluded_non_numeric_denominator=n_excluded_non_numeric_denominator,
        points=points,
    )


def _validate_contract(
    *,
    chart_type: str,
    count_definition: str,
    denominator_column: AttributeControlChartColumn | None,
    constant_opportunity_confirmed: bool,
    missing_policy: str,
    point_limit: int,
) -> None:
    if chart_type not in {"p", "np", "c", "u"}:
        raise AttributeControlChartError("attribute_control_chart_type_unsupported")
    expected_definition = "defectives" if chart_type in {"p", "np"} else "defects"
    if count_definition != expected_definition:
        raise AttributeControlChartError("attribute_control_chart_count_definition_mismatch")
    if chart_type in {"p", "np", "u"} and denominator_column is None:
        raise AttributeControlChartError("attribute_control_chart_denominator_required")
    if chart_type == "c" and denominator_column is not None:
        raise AttributeControlChartError("attribute_control_chart_c_denominator_not_allowed")
    if chart_type == "c" and not constant_opportunity_confirmed:
        raise AttributeControlChartError("attribute_control_chart_c_constant_opportunity_required")
    if missing_policy != "complete_case":
        raise AttributeControlChartError("attribute_control_chart_missing_policy_unsupported")
    if isinstance(point_limit, bool) or not isinstance(point_limit, int) or point_limit <= 0:
        raise AttributeControlChartError("invalid_attribute_control_chart_point_limit")


def _validated_count(value: Decimal) -> int:
    if not value.is_finite() or not isfinite(float(value)):
        raise AttributeControlChartError("attribute_control_chart_count_not_finite")
    if value < 0:
        raise AttributeControlChartError("attribute_control_chart_negative_count")
    if value != value.to_integral_value():
        raise AttributeControlChartError("attribute_control_chart_non_integer_count")
    return int(value)


def _validated_denominator(value: Decimal, *, chart_type: str) -> float:
    if not value.is_finite():
        raise AttributeControlChartError("attribute_control_chart_denominator_not_finite")
    as_float = float(value)
    if not isfinite(as_float):
        raise AttributeControlChartError("attribute_control_chart_denominator_not_finite")
    if value <= 0:
        raise AttributeControlChartError("attribute_control_chart_denominator_not_positive")
    if chart_type in {"p", "np"} and value != value.to_integral_value():
        raise AttributeControlChartError("attribute_control_chart_sample_size_not_integer")
    return as_float


def _center_line(points: Sequence[_AttributePoint], *, chart_type: str) -> float:
    total_count = sum(point.count for point in points)
    if chart_type == "c":
        return total_count / len(points)
    total_denominator = sum(point.denominator for point in points if point.denominator is not None)
    if total_denominator <= 0:
        raise AttributeControlChartError("attribute_control_chart_denominator_not_positive")
    rate = total_count / total_denominator
    if chart_type == "np":
        sample_size = points[0].denominator
        if sample_size is None:
            raise AttributeControlChartError("attribute_control_chart_denominator_required")
        return sample_size * rate
    return rate


def _validate_center_line(center_line: float, *, chart_type: str) -> None:
    if not isfinite(center_line):
        raise AttributeControlChartError("attribute_control_chart_center_invalid")
    if center_line <= 0:
        raise AttributeControlChartError("attribute_control_chart_zero_variation")
    if chart_type == "p" and center_line >= 1:
        raise AttributeControlChartError("attribute_control_chart_zero_variation")


def _point_limits(
    point: _AttributePoint,
    *,
    chart_type: str,
    center_line: float,
) -> dict[str, float | bool]:
    if chart_type == "p":
        denominator = _required_denominator(point)
        sigma = sqrt(center_line * (1.0 - center_line) / denominator)
        raw_lcl = center_line - (3.0 * sigma)
        raw_ucl = center_line + (3.0 * sigma)
        return _bounded_limits(raw_lcl, raw_ucl, upper_bound=1.0)
    if chart_type == "np":
        denominator = _required_denominator(point)
        proportion = center_line / denominator
        if proportion >= 1:
            raise AttributeControlChartError("attribute_control_chart_zero_variation")
        sigma = sqrt(denominator * proportion * (1.0 - proportion))
        raw_lcl = center_line - (3.0 * sigma)
        raw_ucl = center_line + (3.0 * sigma)
        return _bounded_limits(raw_lcl, raw_ucl, upper_bound=denominator)
    if chart_type == "c":
        sigma = sqrt(center_line)
        return _bounded_limits(center_line - (3.0 * sigma), center_line + (3.0 * sigma))
    denominator = _required_denominator(point)
    sigma = sqrt(center_line / denominator)
    return _bounded_limits(center_line - (3.0 * sigma), center_line + (3.0 * sigma))


def _bounded_limits(
    raw_lcl: float,
    raw_ucl: float,
    *,
    upper_bound: float | None = None,
) -> dict[str, float | bool]:
    lcl = max(0.0, raw_lcl)
    ucl = min(raw_ucl, upper_bound) if upper_bound is not None else raw_ucl
    return {
        "lcl": lcl,
        "ucl": ucl,
        "lcl_truncated": raw_lcl < 0.0,
        "ucl_truncated": upper_bound is not None and raw_ucl > upper_bound,
    }


def _limit_signals(
    points: Sequence[_AttributePoint],
    *,
    limits: Sequence[dict[str, float | bool]],
    chart_type: str,
) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for point, limit in zip(points, limits, strict=True):
        value = _point_value(point, chart_type=chart_type)
        lcl = float(limit["lcl"])
        ucl = float(limit["ucl"])
        direction: str | None = None
        if value < lcl:
            direction = "lower"
        elif value > ucl:
            direction = "upper"
        if direction is None:
            continue
        signals.append(
            {
                "signal_id": f"attribute-{chart_type}-{point.position}-limit",
                "code": "attribute_control_chart_point_beyond_control_limits",
                "severity": "warning",
                "position": point.position,
                "canonical_position": point.canonical_position,
                "value": value,
                "limit": direction,
                "definition": "one_point_strictly_outside_three_sigma_control_limits",
            }
        )
    return signals


def _dispersion_ratio(
    points: Sequence[_AttributePoint],
    *,
    chart_type: str,
    center_line: float,
) -> float:
    statistic = 0.0
    for point in points:
        if chart_type in {"p", "np"}:
            denominator = _required_denominator(point)
            proportion = center_line if chart_type == "p" else center_line / denominator
            expected = denominator * proportion
            variance = denominator * proportion * (1.0 - proportion)
        elif chart_type == "c":
            expected = center_line
            variance = center_line
        else:
            denominator = _required_denominator(point)
            expected = denominator * center_line
            variance = expected
        if variance <= 0:
            raise AttributeControlChartError("attribute_control_chart_zero_variation")
        statistic += ((point.count - expected) ** 2) / variance
    return statistic / (len(points) - 1)


def _result_warnings(
    *,
    points: Sequence[_AttributePoint],
    limits: Sequence[dict[str, float | bool]],
    signals: Sequence[dict[str, object]],
    chart_type: str,
    center_line: float,
    dispersion_ratio: float,
    n_excluded_missing_count: int,
    n_excluded_non_numeric_count: int,
    n_excluded_missing_denominator: int,
    n_excluded_non_numeric_denominator: int,
    point_limit: int,
) -> list[str]:
    warnings = [
        "attribute_control_chart_uses_canonical_row_order",
        "attribute_control_chart_phase_1_limits_estimated_from_data",
        "attribute_control_chart_process_assumptions_not_proven",
    ]
    if chart_type == "c":
        warnings.append("attribute_control_chart_c_constant_opportunity_user_confirmed")
    if len(points) < RECOMMENDED_BASELINE_POINT_COUNT:
        warnings.append("attribute_control_chart_baseline_small")
    if _normal_approximation_is_weak(points, chart_type=chart_type, center_line=center_line):
        warnings.append("attribute_control_chart_normal_approximation_weak")
    if dispersion_ratio > 2.0:
        warnings.append("attribute_control_chart_overdispersion_detected")
    if any(bool(limit["lcl_truncated"]) for limit in limits):
        warnings.append("attribute_control_chart_lcl_truncated_to_zero")
    if any(bool(limit["ucl_truncated"]) for limit in limits):
        warnings.append("attribute_control_chart_ucl_truncated_to_natural_bound")
    if n_excluded_missing_count:
        warnings.append("attribute_control_chart_missing_count_excluded")
    if n_excluded_non_numeric_count:
        warnings.append("attribute_control_chart_non_numeric_count_excluded")
    if n_excluded_missing_denominator:
        warnings.append("attribute_control_chart_missing_denominator_excluded")
    if n_excluded_non_numeric_denominator:
        warnings.append("attribute_control_chart_non_numeric_denominator_excluded")
    if signals:
        warnings.append("attribute_control_chart_limit_signal_detected")
    if len(points) > point_limit:
        warnings.append("attribute_control_chart_points_truncated")
    return warnings


def _phase_2_warnings(
    *,
    points: Sequence[_AttributePoint],
    limits: Sequence[dict[str, float | bool]],
    signals: Sequence[dict[str, object]],
    chart_type: str,
    center_line: float,
    dispersion_ratio: float | None,
    collected: _CollectedPoints,
    point_limit: int,
) -> list[str]:
    warnings = [
        "attribute_control_chart_uses_canonical_row_order",
        "attribute_control_chart_phase_2_limits_frozen_from_verified_asset",
        "attribute_control_chart_process_assumptions_not_proven",
    ]
    if chart_type == "c":
        warnings.append("attribute_control_chart_c_constant_opportunity_user_confirmed")
    if _normal_approximation_is_weak(points, chart_type=chart_type, center_line=center_line):
        warnings.append("attribute_control_chart_normal_approximation_weak")
    if dispersion_ratio is None:
        warnings.append("attribute_control_chart_dispersion_insufficient_points")
    elif dispersion_ratio > 2.0:
        warnings.append("attribute_control_chart_overdispersion_detected")
    if any(bool(limit["lcl_truncated"]) for limit in limits):
        warnings.append("attribute_control_chart_lcl_truncated_to_zero")
    if any(bool(limit["ucl_truncated"]) for limit in limits):
        warnings.append("attribute_control_chart_ucl_truncated_to_natural_bound")
    if collected.n_excluded_missing_count:
        warnings.append("attribute_control_chart_missing_count_excluded")
    if collected.n_excluded_non_numeric_count:
        warnings.append("attribute_control_chart_non_numeric_count_excluded")
    if collected.n_excluded_missing_denominator:
        warnings.append("attribute_control_chart_missing_denominator_excluded")
    if collected.n_excluded_non_numeric_denominator:
        warnings.append("attribute_control_chart_non_numeric_denominator_excluded")
    if signals:
        warnings.append("attribute_control_chart_limit_signal_detected")
    if len(points) > point_limit:
        warnings.append("attribute_control_chart_points_truncated")
    return warnings


def _normal_approximation_is_weak(
    points: Sequence[_AttributePoint],
    *,
    chart_type: str,
    center_line: float,
) -> bool:
    if chart_type in {"p", "np"}:
        for point in points:
            denominator = _required_denominator(point)
            proportion = center_line if chart_type == "p" else center_line / denominator
            if min(denominator * proportion, denominator * (1.0 - proportion)) < 5.0:
                return True
        return False
    if chart_type == "c":
        return center_line < 5.0
    return any(_required_denominator(point) * center_line < 5.0 for point in points)


def _chart_points(
    points: Sequence[_AttributePoint],
    *,
    limits: Sequence[dict[str, float | bool]],
    signals: Sequence[dict[str, object]],
    chart_type: str,
    point_limit: int,
) -> list[dict[str, object]]:
    signal_codes_by_position: dict[int, list[str]] = {}
    for signal in signals:
        position = signal.get("position")
        code = signal.get("code")
        if isinstance(position, int) and isinstance(code, str):
            signal_codes_by_position.setdefault(position, []).append(code)
    result: list[dict[str, object]] = []
    for point, limit in zip(points[:point_limit], limits[:point_limit], strict=True):
        result.append(
            {
                "position": point.position,
                "canonical_position": point.canonical_position,
                "count": point.count,
                "denominator": point.denominator,
                "value": _point_value(point, chart_type=chart_type),
                "lcl": limit["lcl"],
                "ucl": limit["ucl"],
                "lcl_truncated": limit["lcl_truncated"],
                "ucl_truncated": limit["ucl_truncated"],
                "signal_codes": signal_codes_by_position.get(point.position, []),
            }
        )
    return result


def _point_value(point: _AttributePoint, *, chart_type: str) -> float:
    if chart_type in {"np", "c"}:
        return float(point.count)
    return point.count / _required_denominator(point)


def _required_denominator(point: _AttributePoint) -> float:
    if point.denominator is None:
        raise AttributeControlChartError("attribute_control_chart_denominator_required")
    return point.denominator


def _denominator_role(chart_type: str) -> str | None:
    if chart_type in {"p", "np"}:
        return "sample_size"
    if chart_type == "u":
        return "inspection_opportunity"
    return None


def _y_axis(chart_type: str) -> str:
    return {
        "p": "proportion_defective",
        "np": "defective_count",
        "c": "defect_count",
        "u": "defects_per_opportunity",
    }[chart_type]


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _parse_decimal(value: str, *, decimal: str, thousands: str | None) -> Decimal | None:
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
    return parsed


def _column_payload(
    column: AttributeControlChartColumn | None,
) -> dict[str, object] | None:
    if column is None:
        return None
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }
