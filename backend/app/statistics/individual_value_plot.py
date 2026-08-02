from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.statistics.graphical_summary import parse_numeric_value

MAX_GROUP_LEVELS = 20


class GraphPointError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GraphPointColumn:
    column_id: str
    column_index: int
    display_name: str
    unit: str | None


def calculate_individual_value_points(
    rows: Iterable[Sequence[str | None]],
    columns: list[GraphPointColumn],
    *,
    decimal: str,
    thousands: str | None,
    point_limit: int,
    group_column_index: int | None = None,
) -> dict[str, object]:
    points: list[dict[str, object]] = []
    series_counts: dict[str, int] = {}
    groups: dict[str, int] = {}
    n_total = 0
    n_missing = 0
    n_non_numeric = 0
    n_missing_group = 0

    for canonical_index, row in enumerate(rows):
        n_total += 1
        group = None
        if group_column_index is not None:
            raw_group = _row_value(row, group_column_index)
            if raw_group is None or raw_group.strip() == "":
                n_missing_group += 1
                continue
            group = raw_group.strip()
            if group not in groups:
                groups[group] = len(groups)
            if len(groups) > MAX_GROUP_LEVELS:
                raise GraphPointError("graph_preview_group_level_limit_exceeded")
        for column in columns:
            raw_value = _row_value(row, column.column_index)
            if raw_value is None or raw_value.strip() == "":
                n_missing += 1
                continue
            value = parse_numeric_value(raw_value, decimal=decimal, thousands=thousands)
            if value is None:
                n_non_numeric += 1
                continue
            if len(points) >= point_limit:
                raise GraphPointError("individual_value_point_limit_exceeded")
            series_key = (
                column.column_id
                if group is None
                else f"{column.column_id}:group:{groups[group]}"
            )
            series_counts[series_key] = series_counts.get(series_key, 0) + 1
            points.append(
                {
                    "series_id": series_key,
                    "series_label": group or column.display_name,
                    "source_column_label": column.display_name,
                    "group": group,
                    "point_index": series_counts[series_key],
                    "canonical_position": canonical_index + 1,
                    "value": value,
                }
            )

    return {
        "point_count": len(points),
        "point_limit": point_limit,
        "sampled": False,
        "n_total": n_total,
        "n_missing": n_missing,
        "n_non_numeric": n_non_numeric,
        "n_missing_group": n_missing_group,
        "groups": [
            {
                "label": label,
                "n": series_counts.get(f"{columns[0].column_id}:group:{index}", 0),
            }
            for label, index in groups.items()
        ],
        "points": points,
    }


def calculate_scatter_points(
    rows: Iterable[Sequence[str | None]],
    x_column: GraphPointColumn,
    y_columns: list[GraphPointColumn],
    *,
    decimal: str,
    thousands: str | None,
    point_limit: int,
    group_column_index: int | None = None,
) -> dict[str, object]:
    points: list[dict[str, object]] = []
    groups: set[str] = set()
    n_total = 0
    n_excluded = 0
    for canonical_index, row in enumerate(rows):
        n_total += 1
        x_raw = _row_value(row, x_column.column_index)
        x_value = (
            None
            if x_raw is None
            else parse_numeric_value(x_raw, decimal=decimal, thousands=thousands)
        )
        group = None
        if group_column_index is not None:
            raw_group = _row_value(row, group_column_index)
            group = "(결측)" if raw_group is None or raw_group.strip() == "" else raw_group
            groups.add(group)
            if len(groups) > MAX_GROUP_LEVELS:
                raise GraphPointError("graph_preview_group_level_limit_exceeded")
        row_used = False
        for y_column in y_columns:
            y_raw = _row_value(row, y_column.column_index)
            y_value = (
                None
                if y_raw is None
                else parse_numeric_value(y_raw, decimal=decimal, thousands=thousands)
            )
            if x_value is None or y_value is None:
                continue
            if len(points) >= point_limit:
                raise GraphPointError("scatter_point_limit_exceeded")
            row_used = True
            points.append(
                {
                    "series_id": y_column.column_id,
                    "series_label": y_column.display_name,
                    "group": group,
                    "canonical_position": canonical_index + 1,
                    "x": x_value,
                    "y": y_value,
                }
            )
        if not row_used:
            n_excluded += 1
    return {
        "point_count": len(points),
        "point_limit": point_limit,
        "sampled": False,
        "n_total": n_total,
        "n_excluded": n_excluded,
        "points": points,
    }


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None
