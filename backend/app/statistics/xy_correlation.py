from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import atanh, isfinite, sqrt, tanh

from scipy import stats  # type: ignore[import-untyped]

MIN_N = 4


class XyCorrelationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class XyCorrelationColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _ParsedCell:
    missing: bool
    non_numeric: bool
    value: float | None


@dataclass
class _PairAccumulator:
    n_total: int = 0
    n_used: int = 0
    n_excluded_missing_x: int = 0
    n_excluded_missing_y: int = 0
    n_excluded_non_numeric_x: int = 0
    n_excluded_non_numeric_y: int = 0
    sum_x: float = 0.0
    sum_y: float = 0.0
    sum_x2: float = 0.0
    sum_y2: float = 0.0
    sum_xy: float = 0.0

    def add(self, x_cell: _ParsedCell, y_cell: _ParsedCell) -> None:
        self.n_total += 1
        if x_cell.missing:
            self.n_excluded_missing_x += 1
        if y_cell.missing:
            self.n_excluded_missing_y += 1
        if x_cell.missing or y_cell.missing:
            return

        if x_cell.non_numeric:
            self.n_excluded_non_numeric_x += 1
        if y_cell.non_numeric:
            self.n_excluded_non_numeric_y += 1
        if x_cell.non_numeric or y_cell.non_numeric:
            return

        assert x_cell.value is not None
        assert y_cell.value is not None
        self.n_used += 1
        self.sum_x += x_cell.value
        self.sum_y += y_cell.value
        self.sum_x2 += x_cell.value * x_cell.value
        self.sum_y2 += y_cell.value * y_cell.value
        self.sum_xy += x_cell.value * y_cell.value


def calculate_xy_correlation(
    rows: Iterable[Sequence[str | None]],
    x_columns: Sequence[XyCorrelationColumn],
    y_columns: Sequence[XyCorrelationColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
) -> dict[str, object]:
    if alpha <= 0.0 or alpha >= 1.0:
        raise XyCorrelationError("invalid_xy_correlation_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise XyCorrelationError("invalid_xy_correlation_confidence_level")
    if not x_columns or not y_columns:
        raise XyCorrelationError("xy_correlation_columns_required")

    unique_columns = _unique_columns([*x_columns, *y_columns])
    accumulators = {
        (x_column.column_id, y_column.column_id): _PairAccumulator()
        for x_column in x_columns
        for y_column in y_columns
    }

    for row in rows:
        parsed_cells = {
            column.column_id: _parse_cell(
                _row_value(row, column.column_index),
                decimal=decimal,
                thousands=thousands,
            )
            for column in unique_columns
        }
        for x_column in x_columns:
            x_cell = parsed_cells[x_column.column_id]
            for y_column in y_columns:
                accumulators[(x_column.column_id, y_column.column_id)].add(
                    x_cell,
                    parsed_cells[y_column.column_id],
                )

    pairs = [
        _pair_payload(
            x_column,
            y_column,
            accumulators[(x_column.column_id, y_column.column_id)],
            alpha=alpha,
            confidence_level=confidence_level,
        )
        for x_column in x_columns
        for y_column in y_columns
    ]
    warnings = _result_warnings(
        pairs,
        has_overlapping_columns=bool(
            {column.column_id for column in x_columns} & {column.column_id for column in y_columns},
        ),
    )

    return {
        "schema_version": 1,
        "summary_type": "xy_correlation_matrix",
        "method": "pairwise_pearson_product_moment_correlation",
        "missing_policy": "pairwise_complete_case",
        "alternative": "two_sided",
        "alpha": alpha,
        "confidence_level": confidence_level,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": warnings,
        "x_columns": [_column_payload(column) for column in x_columns],
        "y_columns": [_column_payload(column) for column in y_columns],
        "x_column_count": len(x_columns),
        "y_column_count": len(y_columns),
        "pair_count": len(pairs),
        "pairs": pairs,
    }


def _unique_columns(columns: Sequence[XyCorrelationColumn]) -> list[XyCorrelationColumn]:
    unique: dict[str, XyCorrelationColumn] = {}
    for column in columns:
        unique.setdefault(column.column_id, column)
    return list(unique.values())


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _parse_cell(
    value: str | None,
    *,
    decimal: str,
    thousands: str | None,
) -> _ParsedCell:
    if value is None or value.strip() == "":
        return _ParsedCell(missing=True, non_numeric=False, value=None)

    normalized = value.strip()
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")

    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return _ParsedCell(missing=False, non_numeric=True, value=None)
    if not parsed.is_finite():
        return _ParsedCell(missing=False, non_numeric=True, value=None)
    as_float = float(parsed)
    if not isfinite(as_float):
        return _ParsedCell(missing=False, non_numeric=True, value=None)
    return _ParsedCell(missing=False, non_numeric=False, value=as_float)


def _pair_payload(
    x_column: XyCorrelationColumn,
    y_column: XyCorrelationColumn,
    accumulator: _PairAccumulator,
    *,
    alpha: float,
    confidence_level: float,
) -> dict[str, object]:
    base_payload: dict[str, object] = {
        "x": _column_payload(x_column),
        "y": _column_payload(y_column),
        "n_total": accumulator.n_total,
        "n_used": accumulator.n_used,
        "n_excluded_missing_x": accumulator.n_excluded_missing_x,
        "n_excluded_missing_y": accumulator.n_excluded_missing_y,
        "n_excluded_non_numeric_x": accumulator.n_excluded_non_numeric_x,
        "n_excluded_non_numeric_y": accumulator.n_excluded_non_numeric_y,
    }
    failure_code = _failure_code(accumulator)
    if failure_code is not None:
        return {
            **base_payload,
            "status": "failed",
            "error_code": failure_code,
            "warnings": _pair_warnings(accumulator),
            "association": None,
            "test": None,
            "confidence_interval": None,
        }

    centered_sum_xx = accumulator.sum_x2 - (
        accumulator.sum_x * accumulator.sum_x / accumulator.n_used
    )
    centered_sum_yy = accumulator.sum_y2 - (
        accumulator.sum_y * accumulator.sum_y / accumulator.n_used
    )
    centered_sum_xy = accumulator.sum_xy - (
        accumulator.sum_x * accumulator.sum_y / accumulator.n_used
    )
    correlation = centered_sum_xy / sqrt(centered_sum_xx * centered_sum_yy)
    correlation = max(min(correlation, 1.0), -1.0)
    covariance = centered_sum_xy / (accumulator.n_used - 1)
    p_value = _p_value(correlation, accumulator.n_used)
    confidence_interval, ci_warning = _confidence_interval(
        correlation,
        n_used=accumulator.n_used,
        confidence_level=confidence_level,
    )
    warnings = _pair_warnings(accumulator)
    if ci_warning is not None:
        warnings.append(ci_warning)

    return {
        **base_payload,
        "status": "ok",
        "error_code": None,
        "warnings": warnings,
        "association": {
            "correlation": correlation,
            "r_squared": correlation * correlation,
            "covariance": covariance,
            "correlation_definition": "pearson_product_moment",
        },
        "test": {
            "statistic": correlation,
            "statistic_name": "r",
            "p_value": p_value,
            "reject_null": p_value < alpha,
            "null_hypothesis": "population_correlation_equals_0",
            "alternative": "two_sided",
        },
        "confidence_interval": confidence_interval,
    }


def _failure_code(accumulator: _PairAccumulator) -> str | None:
    if accumulator.n_used < MIN_N:
        return "xy_correlation_n_too_small"
    centered_sum_xx = accumulator.sum_x2 - (
        accumulator.sum_x * accumulator.sum_x / accumulator.n_used
    )
    centered_sum_yy = accumulator.sum_y2 - (
        accumulator.sum_y * accumulator.sum_y / accumulator.n_used
    )
    if centered_sum_xx <= 0.0:
        return "xy_correlation_x_constant"
    if centered_sum_yy <= 0.0:
        return "xy_correlation_y_constant"
    centered_sum_xy = accumulator.sum_xy - (
        accumulator.sum_x * accumulator.sum_y / accumulator.n_used
    )
    denominator = sqrt(centered_sum_xx * centered_sum_yy)
    correlation = centered_sum_xy / denominator
    if not isfinite(correlation):
        return "xy_correlation_result_not_finite"
    return None


def _p_value(correlation: float, n_used: int) -> float:
    if abs(correlation) >= 1.0:
        return 0.0
    statistic = abs(correlation) * sqrt((n_used - 2) / (1.0 - (correlation * correlation)))
    return float(2.0 * stats.t.sf(statistic, df=n_used - 2))


def _confidence_interval(
    correlation: float,
    *,
    n_used: int,
    confidence_level: float,
) -> tuple[dict[str, object], str | None]:
    if abs(correlation) >= 1.0:
        return (
            {
                "method": "fisher_z",
                "level": confidence_level,
                "lower": None,
                "upper": None,
            },
            "xy_correlation_perfect_sample_correlation_ci_unavailable",
        )

    z_value = atanh(correlation)
    standard_error = 1.0 / sqrt(n_used - 3)
    z_critical = float(stats.norm.ppf(1.0 - ((1.0 - confidence_level) / 2.0)))
    return (
        {
            "method": "fisher_z",
            "level": confidence_level,
            "lower": tanh(z_value - (z_critical * standard_error)),
            "upper": tanh(z_value + (z_critical * standard_error)),
        },
        None,
    )


def _column_payload(column: XyCorrelationColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _pair_warnings(accumulator: _PairAccumulator) -> list[str]:
    warnings: list[str] = []
    if accumulator.n_excluded_missing_x > 0 or accumulator.n_excluded_missing_y > 0:
        warnings.append("missing_values_excluded")
    if accumulator.n_excluded_non_numeric_x > 0 or accumulator.n_excluded_non_numeric_y > 0:
        warnings.append("non_numeric_values_excluded")
    return warnings


def _result_warnings(
    pairs: Sequence[dict[str, object]],
    *,
    has_overlapping_columns: bool,
) -> list[str]:
    warnings = [
        "xy_correlation_not_causation",
        "xy_correlation_linear_relationship_assumption",
        "xy_correlation_outlier_sensitive",
    ]
    if any(pair.get("status") == "failed" for pair in pairs):
        warnings.append("xy_correlation_pair_failed")
    n_used_values = {
        pair.get("n_used")
        for pair in pairs
        if pair.get("status") == "ok" and isinstance(pair.get("n_used"), int)
    }
    if len(n_used_values) > 1:
        warnings.append("xy_correlation_pairwise_n_varies")
    if has_overlapping_columns:
        warnings.append("xy_correlation_overlapping_x_y_columns")
    if any(_pair_has_warning(pair, "missing_values_excluded") for pair in pairs):
        warnings.append("missing_values_excluded")
    if any(_pair_has_warning(pair, "non_numeric_values_excluded") for pair in pairs):
        warnings.append("non_numeric_values_excluded")
    if any(
        _pair_has_warning(pair, "xy_correlation_perfect_sample_correlation_ci_unavailable")
        for pair in pairs
    ):
        warnings.append("xy_correlation_perfect_sample_correlation_ci_unavailable")
    return warnings


def _pair_has_warning(pair: dict[str, object], code: str) -> bool:
    warnings = pair.get("warnings")
    return isinstance(warnings, list) and code in warnings
