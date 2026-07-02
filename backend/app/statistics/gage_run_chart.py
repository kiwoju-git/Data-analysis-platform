from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import fsum, isfinite

MIN_PART_COUNT = 2
MIN_OPERATOR_COUNT = 2
MIN_REPLICATE_COUNT = 2
DEFAULT_POINT_LIMIT = 1000
ORDER_DATA_TYPES = {"integer", "decimal", "datetime"}


class GageRunChartError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GageRunChartColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _Observation:
    canonical_position: int
    value: float
    part: str
    operator: str
    replicate: str
    order_value: float | str | None


def calculate_gage_run_chart(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRunChartColumn,
    part_column: GageRunChartColumn,
    operator_column: GageRunChartColumn,
    replicate_column: GageRunChartColumn,
    order_column: GageRunChartColumn | None = None,
    decimal: str = ".",
    thousands: str | None = None,
    missing_policy: str = "complete_case",
    point_limit: int = DEFAULT_POINT_LIMIT,
) -> dict[str, object]:
    if missing_policy != "complete_case":
        raise GageRunChartError("gage_run_chart_missing_policy_unsupported")
    if point_limit <= 0:
        raise GageRunChartError("invalid_gage_run_chart_point_limit")

    observations, sample = _collect_observations(
        rows,
        measurement_column=measurement_column,
        part_column=part_column,
        operator_column=operator_column,
        replicate_column=replicate_column,
        order_column=order_column,
        decimal=decimal,
        thousands=thousands,
    )
    design = _design_summary(observations)
    if not design["ready_for_chart"]:
        raise GageRunChartError(str(design["error_code"]))

    sorted_observations = _ordered_observations(observations, order_column=order_column)
    chart = _chart_payload(sorted_observations, design=design, point_limit=point_limit)
    warnings = _warnings(
        sample=sample,
        order_column=order_column,
        point_count=len(sorted_observations),
        point_limit=point_limit,
    )

    return {
        "schema_version": 1,
        "summary_type": "gage_run_chart",
        "method": "measurement_system_run_chart",
        "missing_policy": missing_policy,
        "order_source": _order_source(order_column),
        "order_tie_breaker": "canonical_row_position",
        "columns": {
            "measurement": _column_payload(measurement_column),
            "part": _column_payload(part_column),
            "operator": _column_payload(operator_column),
            "replicate": _column_payload(replicate_column),
            "order": _column_payload(order_column) if order_column is not None else None,
        },
        "sample": sample,
        "design": {
            key: value
            for key, value in design.items()
            if key not in {"error_code", "part_ids", "operator_ids", "replicate_ids"}
        },
        "summary": _measurement_summary(observations),
        "part_summaries": _part_summaries(observations, design),
        "operator_summaries": _operator_summaries(observations, design),
        "chart": chart,
        "warnings": warnings,
        "notes": [
            "diagnostic_chart_not_variance_component_analysis",
            "part_operator_replicate_labels_redacted",
        ],
    }


def _collect_observations(
    rows: Iterable[Sequence[str | None]],
    *,
    measurement_column: GageRunChartColumn,
    part_column: GageRunChartColumn,
    operator_column: GageRunChartColumn,
    replicate_column: GageRunChartColumn,
    order_column: GageRunChartColumn | None,
    decimal: str,
    thousands: str | None,
) -> tuple[list[_Observation], dict[str, int]]:
    n_total = 0
    n_excluded_missing_measurement = 0
    n_excluded_non_numeric_measurement = 0
    n_excluded_missing_part = 0
    n_excluded_missing_operator = 0
    n_excluded_missing_replicate = 0
    n_excluded_missing_identifier = 0
    n_excluded_missing_order = 0
    n_excluded_invalid_order = 0
    observations: list[_Observation] = []

    for row in rows:
        n_total += 1
        raw_measurement = _row_value(row, measurement_column.column_index)
        raw_part = _row_value(row, part_column.column_index)
        raw_operator = _row_value(row, operator_column.column_index)
        raw_replicate = _row_value(row, replicate_column.column_index)

        measurement_missing = _is_missing(raw_measurement)
        part_missing = _is_missing(raw_part)
        operator_missing = _is_missing(raw_operator)
        replicate_missing = _is_missing(raw_replicate)
        if measurement_missing:
            n_excluded_missing_measurement += 1
        if part_missing:
            n_excluded_missing_part += 1
        if operator_missing:
            n_excluded_missing_operator += 1
        if replicate_missing:
            n_excluded_missing_replicate += 1
        if part_missing or operator_missing or replicate_missing:
            n_excluded_missing_identifier += 1
        if measurement_missing or part_missing or operator_missing or replicate_missing:
            continue

        measurement = _parse_number(raw_measurement, decimal=decimal, thousands=thousands)
        if measurement is None:
            n_excluded_non_numeric_measurement += 1
            continue

        order_value: float | str | None = None
        if order_column is not None:
            raw_order = _row_value(row, order_column.column_index)
            if _is_missing(raw_order):
                n_excluded_missing_order += 1
                continue
            parsed_order = _parse_order_value(
                raw_order,
                order_column,
                decimal=decimal,
                thousands=thousands,
            )
            if parsed_order is None:
                n_excluded_invalid_order += 1
                continue
            order_value = parsed_order

        observations.append(
            _Observation(
                canonical_position=n_total,
                value=measurement,
                part=_identifier_value(raw_part),
                operator=_identifier_value(raw_operator),
                replicate=_identifier_value(raw_replicate),
                order_value=order_value,
            ),
        )

    return observations, {
        "n_total": n_total,
        "n_used": len(observations),
        "n_excluded_missing_measurement": n_excluded_missing_measurement,
        "n_excluded_non_numeric_measurement": n_excluded_non_numeric_measurement,
        "n_excluded_missing_part": n_excluded_missing_part,
        "n_excluded_missing_operator": n_excluded_missing_operator,
        "n_excluded_missing_replicate": n_excluded_missing_replicate,
        "n_excluded_missing_identifier": n_excluded_missing_identifier,
        "n_excluded_missing_order": n_excluded_missing_order,
        "n_excluded_invalid_order": n_excluded_invalid_order,
    }


def _design_summary(observations: Sequence[_Observation]) -> dict[str, object]:
    parts = sorted({observation.part for observation in observations})
    operators = sorted({observation.operator for observation in observations})
    replicate_sets: dict[tuple[str, str], set[str]] = defaultdict(set)
    duplicate_replicates_per_cell = 0
    for observation in observations:
        cell_key = (observation.part, observation.operator)
        if observation.replicate in replicate_sets[cell_key]:
            duplicate_replicates_per_cell += 1
        replicate_sets[cell_key].add(observation.replicate)

    expected_cell_count = len(parts) * len(operators)
    missing_cell_count = max(0, expected_cell_count - len(replicate_sets))
    replicate_count_values = [len(replicates) for replicates in replicate_sets.values()]
    min_replicates_per_cell = min(replicate_count_values, default=0)
    max_replicates_per_cell = max(replicate_count_values, default=0)
    unique_replicate_sets = {frozenset(replicates) for replicates in replicate_sets.values()}
    replicate_set_consistent = len(unique_replicate_sets) == 1
    replicate_ids = sorted(next(iter(unique_replicate_sets), frozenset()))

    error_code: str | None = None
    if not observations:
        error_code = "gage_run_chart_no_usable_measurements"
    elif len(parts) < MIN_PART_COUNT:
        error_code = "gage_run_chart_part_count_too_small"
    elif len(operators) < MIN_OPERATOR_COUNT:
        error_code = "gage_run_chart_operator_count_too_small"
    elif min_replicates_per_cell < MIN_REPLICATE_COUNT:
        error_code = "gage_run_chart_replicate_count_too_small"
    elif missing_cell_count > 0:
        error_code = "gage_run_chart_crossed_cells_missing"
    elif min_replicates_per_cell != max_replicates_per_cell or not replicate_set_consistent:
        error_code = "gage_run_chart_unbalanced_crossed_design"
    elif duplicate_replicates_per_cell > 0:
        error_code = "gage_run_chart_duplicate_replicates_per_cell"

    return {
        "ready_for_chart": error_code is None,
        "error_code": error_code,
        "part_count": len(parts),
        "operator_count": len(operators),
        "replicate_count": min_replicates_per_cell if error_code is None else None,
        "expected_cell_count": expected_cell_count,
        "observed_cell_count": len(replicate_sets),
        "missing_cell_count": missing_cell_count,
        "min_replicates_per_cell": min_replicates_per_cell,
        "max_replicates_per_cell": max_replicates_per_cell,
        "replicate_set_consistent": replicate_set_consistent,
        "duplicate_replicates_per_cell": duplicate_replicates_per_cell,
        "part_ids": parts,
        "operator_ids": operators,
        "replicate_ids": replicate_ids,
    }


def _ordered_observations(
    observations: Sequence[_Observation],
    *,
    order_column: GageRunChartColumn | None,
) -> list[_Observation]:
    if order_column is None:
        return sorted(observations, key=lambda observation: observation.canonical_position)
    return sorted(
        observations,
        key=lambda observation: (
            observation.order_value
            if observation.order_value is not None
            else observation.canonical_position,
            observation.canonical_position,
        ),
    )


def _chart_payload(
    observations: Sequence[_Observation],
    *,
    design: dict[str, object],
    point_limit: int,
) -> dict[str, object]:
    part_ids = _string_list(design["part_ids"])
    operator_ids = _string_list(design["operator_ids"])
    replicate_ids = _string_list(design["replicate_ids"])
    point_count = len(observations)
    limited = observations[:point_limit]
    return {
        "point_count": point_count,
        "points_truncated": point_count > point_limit,
        "point_limit": point_limit,
        "x_axis": "run_order",
        "color_role": "operator_index",
        "facet_role": "part_index",
        "symbol_role": "replicate_index",
        "label_policy": "part_operator_replicate_labels_redacted",
        "points": [
            {
                "position": index,
                "canonical_position": observation.canonical_position,
                "value": observation.value,
                "part_index": part_ids.index(observation.part) + 1,
                "operator_index": operator_ids.index(observation.operator) + 1,
                "replicate_index": replicate_ids.index(observation.replicate) + 1,
            }
            for index, observation in enumerate(limited, start=1)
        ],
    }


def _measurement_summary(observations: Sequence[_Observation]) -> dict[str, object]:
    values = [observation.value for observation in observations]
    if not values:
        raise GageRunChartError("gage_run_chart_no_usable_measurements")
    mean = fsum(values) / len(values)
    return {
        "mean": mean,
        "minimum": min(values),
        "maximum": max(values),
        "range": max(values) - min(values),
    }


def _part_summaries(
    observations: Sequence[_Observation],
    design: dict[str, object],
) -> list[dict[str, object]]:
    part_ids = _string_list(design["part_ids"])
    return [
        _summary_row(
            index=index,
            values=[
                observation.value for observation in observations if observation.part == part_id
            ],
        )
        for index, part_id in enumerate(part_ids, start=1)
    ]


def _operator_summaries(
    observations: Sequence[_Observation],
    design: dict[str, object],
) -> list[dict[str, object]]:
    operator_ids = _string_list(design["operator_ids"])
    return [
        _summary_row(
            index=index,
            values=[
                observation.value
                for observation in observations
                if observation.operator == operator_id
            ],
        )
        for index, operator_id in enumerate(operator_ids, start=1)
    ]


def _summary_row(index: int, values: Sequence[float]) -> dict[str, object]:
    if not values:
        raise GageRunChartError("gage_run_chart_internal_summary_invalid")
    return {
        "index": index,
        "n": len(values),
        "mean": fsum(values) / len(values),
        "minimum": min(values),
        "maximum": max(values),
        "range": max(values) - min(values),
    }


def _warnings(
    *,
    sample: dict[str, int],
    order_column: GageRunChartColumn | None,
    point_count: int,
    point_limit: int,
) -> list[str]:
    warnings = [
        "gage_run_chart_diagnostic_only",
        "gage_run_chart_requires_gage_design",
        "gage_run_chart_labels_redacted",
    ]
    if order_column is None:
        warnings.append("gage_run_chart_uses_canonical_row_order")
    else:
        warnings.append("gage_run_chart_uses_order_column")
    if sample["n_excluded_missing_measurement"] > 0:
        warnings.append("missing_values_excluded")
    if sample["n_excluded_non_numeric_measurement"] > 0:
        warnings.append("non_numeric_values_excluded")
    if sample["n_excluded_missing_identifier"] > 0:
        warnings.append("gage_run_chart_identifier_missing_excluded")
    if sample["n_excluded_missing_order"] > 0:
        warnings.append("gage_run_chart_order_missing_excluded")
    if sample["n_excluded_invalid_order"] > 0:
        warnings.append("gage_run_chart_order_invalid_excluded")
    if point_count > point_limit:
        warnings.append("gage_run_chart_points_truncated")
    return warnings


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ""


def _parse_number(value: str | None, *, decimal: str, thousands: str | None) -> float | None:
    if value is None:
        return None
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
    value: str | None,
    order_column: GageRunChartColumn,
    *,
    decimal: str,
    thousands: str | None,
) -> float | str | None:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    if order_column.data_type == "datetime":
        return normalized
    return _parse_number(normalized, decimal=decimal, thousands=thousands)


def _identifier_value(value: str | None) -> str:
    if value is None:
        raise GageRunChartError("gage_run_chart_identifier_missing")
    normalized = value.strip()
    if normalized == "":
        raise GageRunChartError("gage_run_chart_identifier_missing")
    return normalized


def _column_payload(column: GageRunChartColumn | None) -> dict[str, object] | None:
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


def _order_source(order_column: GageRunChartColumn | None) -> str:
    if order_column is None:
        return "canonical_row_order"
    if order_column.data_type == "datetime":
        return "datetime_order_column_ascending"
    return "numeric_order_column_ascending"


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise GageRunChartError("gage_run_chart_internal_design_invalid")
    return value
