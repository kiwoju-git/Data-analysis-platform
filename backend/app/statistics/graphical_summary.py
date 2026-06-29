from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import ceil
from statistics import NormalDist

MAX_HISTOGRAM_BINS = 200
DEFAULT_POINT_LIMIT = 1000


@dataclass(frozen=True)
class GraphicalSummaryColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass
class _ColumnAccumulator:
    spec: GraphicalSummaryColumn
    n_total: int = 0
    n_missing: int = 0
    n_non_numeric: int = 0
    values: list[float] = field(default_factory=list)


def summarize_numeric_graphics(
    rows: Iterable[Sequence[str | None]],
    columns: list[GraphicalSummaryColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    histogram_bin_count: int | None = None,
    point_limit: int = DEFAULT_POINT_LIMIT,
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
        "summary_type": "graphical_summary",
        "histogram_method": "freedman_diaconis" if histogram_bin_count is None else "fixed_count",
        "boxplot_method": "tukey_1_5_iqr",
        "qq_plot_distribution": "standard_normal",
        "qq_plotting_position": "rank_minus_half_over_n",
        "ecdf_method": "right_continuous",
        "point_limit": point_limit,
        "columns": [
            _column_summary(
                accumulator,
                histogram_bin_count=histogram_bin_count,
                point_limit=point_limit,
            )
            for accumulator in accumulators
        ],
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


def _column_summary(
    accumulator: _ColumnAccumulator,
    *,
    histogram_bin_count: int | None,
    point_limit: int,
) -> dict[str, object]:
    values = sorted(accumulator.values)
    n_used = len(values)
    q1, q3 = _quartiles(values)
    median = _median(values) if values else None
    warnings: list[str] = []
    if accumulator.n_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    if n_used == 0:
        warnings.append("no_numeric_values")
    elif n_used > 1 and values[0] == values[-1]:
        warnings.append("constant_column")

    qq_points, qq_truncated = _qq_points(values, point_limit=point_limit)
    ecdf_points, ecdf_truncated = _ecdf_points(values, point_limit=point_limit)
    if qq_truncated or ecdf_truncated:
        warnings.append("graphical_points_truncated")

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
        "min": values[0] if values else None,
        "q1": q1,
        "median": median,
        "q3": q3,
        "max": values[-1] if values else None,
        "histogram": _histogram(values, requested_bin_count=histogram_bin_count),
        "boxplot": _boxplot(values),
        "qq_plot": {
            "point_count": len(qq_points),
            "points_truncated": qq_truncated,
            "points": qq_points,
        },
        "ecdf": {
            "point_count": len(ecdf_points),
            "points_truncated": ecdf_truncated,
            "points": ecdf_points,
        },
        "warnings": warnings,
    }


def _histogram(
    sorted_values: Sequence[float],
    *,
    requested_bin_count: int | None,
) -> dict[str, object]:
    if not sorted_values:
        return {
            "binning": "fixed_count" if requested_bin_count is not None else "freedman_diaconis",
            "bin_count": 0,
            "bins": [],
        }

    value_min = sorted_values[0]
    value_max = sorted_values[-1]
    if value_min == value_max:
        return {
            "binning": "constant",
            "bin_count": 1,
            "bins": [
                {
                    "lower": value_min,
                    "upper": value_max,
                    "count": len(sorted_values),
                    "include_lower": True,
                    "include_upper": True,
                },
            ],
        }

    bin_count = (
        requested_bin_count
        if requested_bin_count is not None
        else _freedman_diaconis_bin_count(sorted_values)
    )
    bin_count = max(1, min(MAX_HISTOGRAM_BINS, bin_count))
    width = (value_max - value_min) / bin_count
    counts = [0 for _ in range(bin_count)]
    for value in sorted_values:
        if value == value_max:
            bin_index = bin_count - 1
        else:
            bin_index = int((value - value_min) / width)
            bin_index = max(0, min(bin_count - 1, bin_index))
        counts[bin_index] += 1

    bins = []
    for index, count in enumerate(counts):
        lower = value_min + width * index
        upper = value_max if index == bin_count - 1 else value_min + width * (index + 1)
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "count": count,
                "include_lower": True,
                "include_upper": index == bin_count - 1,
            },
        )
    return {
        "binning": "fixed_count" if requested_bin_count is not None else "freedman_diaconis",
        "bin_count": bin_count,
        "bins": bins,
    }


def _freedman_diaconis_bin_count(sorted_values: Sequence[float]) -> int:
    q1, q3 = _quartiles(sorted_values)
    if q1 is None or q3 is None:
        return 1
    iqr = q3 - q1
    if iqr <= 0:
        return max(1, ceil(len(sorted_values) ** 0.5))
    width = 2 * iqr / (len(sorted_values) ** (1 / 3))
    if width <= 0:
        return 1
    return max(1, ceil((sorted_values[-1] - sorted_values[0]) / width))


def _boxplot(sorted_values: Sequence[float]) -> dict[str, object]:
    if not sorted_values:
        return {
            "lower_whisker": None,
            "q1": None,
            "median": None,
            "q3": None,
            "upper_whisker": None,
            "lower_fence": None,
            "upper_fence": None,
            "outlier_count": 0,
        }

    q1, q3 = _quartiles(sorted_values)
    assert q1 is not None
    assert q3 is not None
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    non_outlier_values = [value for value in sorted_values if lower_fence <= value <= upper_fence]
    outlier_count = len(sorted_values) - len(non_outlier_values)
    return {
        "lower_whisker": non_outlier_values[0] if non_outlier_values else sorted_values[0],
        "q1": q1,
        "median": _median(sorted_values),
        "q3": q3,
        "upper_whisker": non_outlier_values[-1] if non_outlier_values else sorted_values[-1],
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "outlier_count": outlier_count,
    }


def _qq_points(
    sorted_values: Sequence[float],
    *,
    point_limit: int,
) -> tuple[list[dict[str, float]], bool]:
    if not sorted_values:
        return [], False
    selected_indices, truncated = _selected_point_indices(len(sorted_values), point_limit)
    normal = NormalDist()
    points = []
    n = len(sorted_values)
    for index in selected_indices:
        plotting_position = (index + 0.5) / n
        points.append(
            {
                "theoretical": normal.inv_cdf(plotting_position),
                "sample": sorted_values[index],
            },
        )
    return points, truncated


def _ecdf_points(
    sorted_values: Sequence[float],
    *,
    point_limit: int,
) -> tuple[list[dict[str, float]], bool]:
    if not sorted_values:
        return [], False
    selected_indices, truncated = _selected_point_indices(len(sorted_values), point_limit)
    n = len(sorted_values)
    return [
        {
            "x": sorted_values[index],
            "probability": (index + 1) / n,
        }
        for index in selected_indices
    ], truncated


def _selected_point_indices(n: int, point_limit: int) -> tuple[list[int], bool]:
    if n <= point_limit:
        return list(range(n)), False
    if point_limit <= 1:
        return [0], True

    indices = {round(position * (n - 1) / (point_limit - 1)) for position in range(point_limit)}
    return sorted(indices), True


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
