from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import fsum, sqrt


@dataclass(frozen=True)
class DescriptiveColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass
class _ColumnAccumulator:
    spec: DescriptiveColumn
    n_total: int = 0
    n_missing: int = 0
    n_non_numeric: int = 0
    values: list[float] = field(default_factory=list)


def describe_numeric_columns(
    rows: Iterable[Sequence[str | None]],
    columns: list[DescriptiveColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
) -> dict[str, object]:
    accumulators = [_ColumnAccumulator(spec=column) for column in columns]

    for row in rows:
        for accumulator in accumulators:
            accumulator.n_total += 1
            value = (
                row[accumulator.spec.column_index]
                if accumulator.spec.column_index < len(row)
                else None
            )
            if value is None or value.strip() == "":
                accumulator.n_missing += 1
                continue

            number = _parse_number(value, decimal=decimal, thousands=thousands)
            if number is None:
                accumulator.n_non_numeric += 1
                continue

            accumulator.values.append(number)

    return {
        "schema_version": 1,
        "summary_type": "descriptive_statistics",
        "missing_policy": "available_case_by_column",
        "quartile_method": "median_of_halves",
        "std_definition": "sample_standard_deviation_ddof_1",
        "columns": [_column_summary(accumulator) for accumulator in accumulators],
    }


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
    return float(parsed)


def _column_summary(accumulator: _ColumnAccumulator) -> dict[str, object]:
    values = sorted(accumulator.values)
    n_used = len(values)
    warnings: list[str] = []
    if accumulator.n_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    if n_used == 0:
        warnings.append("no_numeric_values")
    elif n_used > 1 and values[0] == values[-1]:
        warnings.append("constant_column")

    return {
        "column_id": accumulator.spec.column_id,
        "column_index": accumulator.spec.column_index,
        "display_name": accumulator.spec.display_name,
        "data_type": accumulator.spec.data_type,
        "measurement_level": accumulator.spec.measurement_level,
        "role": accumulator.spec.role,
        "unit": accumulator.spec.unit,
        "n_total": accumulator.n_total,
        "n_used": n_used,
        "n_missing": accumulator.n_missing,
        "n_non_numeric": accumulator.n_non_numeric,
        "mean": _mean(values),
        "std": _sample_std(values),
        "min": values[0] if values else None,
        "q1": _quartiles(values)[0],
        "median": _median(values) if values else None,
        "q3": _quartiles(values)[1],
        "max": values[-1] if values else None,
        "warnings": warnings,
    }


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return fsum(values) / len(values)


def _sample_std(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = fsum(values) / len(values)
    variance = fsum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return sqrt(variance)


def _quartiles(sorted_values: Sequence[float]) -> tuple[float | None, float | None]:
    if not sorted_values:
        return None, None
    if len(sorted_values) == 1:
        return sorted_values[0], sorted_values[0]

    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 0:
        lower_half = sorted_values[:midpoint]
        upper_half = sorted_values[midpoint:]
    else:
        lower_half = sorted_values[:midpoint]
        upper_half = sorted_values[midpoint + 1 :]

    return _median(lower_half), _median(upper_half)


def _median(sorted_values: Sequence[float]) -> float:
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2
