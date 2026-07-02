from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from math import isfinite, sqrt

from scipy import stats  # type: ignore[import-untyped]

LEVEL_LABEL_MAX_LENGTH = 120
MAX_LEVELS_PER_AXIS = 100


class ChiSquareAssociationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ChiSquareAssociationColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass
class _AxisLevel:
    label: str
    index: int
    count: int = 0


@dataclass
class _ContingencyAccumulator:
    row_levels: dict[str, _AxisLevel] = field(default_factory=dict)
    column_levels: dict[str, _AxisLevel] = field(default_factory=dict)
    counts: dict[tuple[str, str], int] = field(default_factory=dict)

    def add(self, row_label: str, column_label: str) -> None:
        row_level = self.row_levels.get(row_label)
        if row_level is None:
            if len(self.row_levels) >= MAX_LEVELS_PER_AXIS:
                raise ChiSquareAssociationError("chi_square_too_many_row_levels")
            row_level = _AxisLevel(label=row_label, index=len(self.row_levels))
            self.row_levels[row_label] = row_level

        column_level = self.column_levels.get(column_label)
        if column_level is None:
            if len(self.column_levels) >= MAX_LEVELS_PER_AXIS:
                raise ChiSquareAssociationError("chi_square_too_many_column_levels")
            column_level = _AxisLevel(label=column_label, index=len(self.column_levels))
            self.column_levels[column_label] = column_level

        row_level.count += 1
        column_level.count += 1
        key = (row_label, column_label)
        self.counts[key] = self.counts.get(key, 0) + 1


def calculate_chi_square_association(
    rows: Iterable[Sequence[str | None]],
    row_column: ChiSquareAssociationColumn,
    column_column: ChiSquareAssociationColumn,
    *,
    alpha: float = 0.05,
) -> dict[str, object]:
    if alpha <= 0.0 or alpha >= 1.0 or not isfinite(alpha):
        raise ChiSquareAssociationError("invalid_chi_square_alpha")

    accumulator = _ContingencyAccumulator()
    n_total = 0
    n_excluded_missing_row = 0
    n_excluded_missing_column = 0

    for row in rows:
        n_total += 1
        row_value = _row_value(row, row_column.column_index)
        column_value = _row_value(row, column_column.column_index)
        if row_value is None or row_value.strip() == "":
            n_excluded_missing_row += 1
            continue
        if column_value is None or column_value.strip() == "":
            n_excluded_missing_column += 1
            continue
        accumulator.add(_safe_level_label(row_value), _safe_level_label(column_value))

    row_levels = list(accumulator.row_levels.values())
    column_levels = list(accumulator.column_levels.values())
    if len(row_levels) < 2:
        raise ChiSquareAssociationError("chi_square_requires_at_least_two_row_levels")
    if len(column_levels) < 2:
        raise ChiSquareAssociationError("chi_square_requires_at_least_two_column_levels")

    observed = _observed_counts(accumulator, row_levels, column_levels)
    chi_square = stats.chi2_contingency(observed, correction=False)
    statistic = float(chi_square.statistic)
    p_value = float(chi_square.pvalue)
    if not isfinite(statistic) or not isfinite(p_value):
        raise ChiSquareAssociationError("chi_square_statistic_not_finite")

    expected = [
        [float(value) for value in expected_row] for expected_row in chi_square.expected_freq
    ]
    n_used = sum(sum(row) for row in observed)
    min_dimension = min(len(row_levels) - 1, len(column_levels) - 1)
    cramer_v = sqrt(statistic / (n_used * min_dimension))
    expected_summary = _expected_count_summary(expected)

    return {
        "schema_version": 1,
        "summary_type": "chi_square_association",
        "method": "pearson_chi_square_independence",
        "input_mode": "dataset_two_categorical_columns",
        "missing_policy": "complete_case",
        "alpha": alpha,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            row_count=len(row_levels),
            column_count=len(column_levels),
            expected_summary=expected_summary,
            n_excluded_missing_row=n_excluded_missing_row,
            n_excluded_missing_column=n_excluded_missing_column,
        ),
        "row_variable": _column_payload(row_column),
        "column_variable": _column_payload(column_column),
        "n_total": n_total,
        "n_used": n_used,
        "n_excluded_missing_row": n_excluded_missing_row,
        "n_excluded_missing_column": n_excluded_missing_column,
        "row_levels": [_level_payload(level) for level in row_levels],
        "column_levels": [_level_payload(level) for level in column_levels],
        "contingency_table": _contingency_table(
            row_levels,
            column_levels,
            observed,
            expected,
            n_used,
        ),
        "expected_count_summary": expected_summary,
        "test": {
            "statistic": statistic,
            "statistic_name": "chi_square",
            "df": int(chi_square.dof),
            "p_value": p_value,
            "reject_null": p_value < alpha,
            "continuity_correction": False,
        },
        "effect_size": {
            "cramers_v": cramer_v,
            "definition": "sqrt(chi_square/(n*min(row_count-1,column_count-1)))",
        },
        "recommended_alternative_tests": _recommended_alternatives(
            row_count=len(row_levels),
            column_count=len(column_levels),
            expected_summary=expected_summary,
        ),
    }


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _safe_level_label(value: str) -> str:
    stripped = value.strip()
    if len(stripped) <= LEVEL_LABEL_MAX_LENGTH:
        return stripped
    return f"{stripped[: LEVEL_LABEL_MAX_LENGTH - 3]}..."


def _column_payload(column: ChiSquareAssociationColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _level_payload(level: _AxisLevel) -> dict[str, object]:
    return {
        "level": level.label,
        "index": level.index,
        "count": level.count,
    }


def _observed_counts(
    accumulator: _ContingencyAccumulator,
    row_levels: Sequence[_AxisLevel],
    column_levels: Sequence[_AxisLevel],
) -> list[list[int]]:
    return [
        [
            accumulator.counts.get((row_level.label, column_level.label), 0)
            for column_level in column_levels
        ]
        for row_level in row_levels
    ]


def _contingency_table(
    row_levels: Sequence[_AxisLevel],
    column_levels: Sequence[_AxisLevel],
    observed: Sequence[Sequence[int]],
    expected: Sequence[Sequence[float]],
    n_used: int,
) -> dict[str, object]:
    column_totals = [
        sum(row[column_index] for row in observed) for column_index in range(len(column_levels))
    ]
    rows: list[dict[str, object]] = []
    for row_index, row_level in enumerate(row_levels):
        row_total = sum(observed[row_index])
        cells: list[dict[str, object]] = []
        for column_index, column_level in enumerate(column_levels):
            observed_count = observed[row_index][column_index]
            expected_count = expected[row_index][column_index]
            cells.append(
                {
                    "column_level": column_level.label,
                    "observed": observed_count,
                    "expected": expected_count,
                    "row_percent": observed_count / row_total if row_total else None,
                    "column_percent": (
                        observed_count / column_totals[column_index]
                        if column_totals[column_index]
                        else None
                    ),
                    "total_percent": observed_count / n_used if n_used else None,
                    "standardized_residual": (
                        (observed_count - expected_count) / sqrt(expected_count)
                        if expected_count > 0
                        else None
                    ),
                },
            )
        rows.append(
            {
                "row_level": row_level.label,
                "row_total": row_total,
                "cells": cells,
            },
        )

    return {
        "row_levels": [level.label for level in row_levels],
        "column_levels": [level.label for level in column_levels],
        "rows": rows,
        "column_totals": column_totals,
        "grand_total": n_used,
    }


def _expected_count_summary(expected: Sequence[Sequence[float]]) -> dict[str, object]:
    flat = [value for row in expected for value in row]
    below_1 = sum(1 for value in flat if value < 1.0)
    below_5 = sum(1 for value in flat if value < 5.0)
    total = len(flat)
    return {
        "min_expected": min(flat),
        "cells_below_1": below_1,
        "cells_below_5": below_5,
        "cell_count": total,
        "share_below_5": below_5 / total,
        "rule_of_thumb_passed": below_1 == 0 and (below_5 / total) <= 0.2,
    }


def _recommended_alternatives(
    *,
    row_count: int,
    column_count: int,
    expected_summary: dict[str, object],
) -> list[dict[str, object]]:
    alternatives: list[dict[str, object]] = []
    if (
        row_count == 2
        and column_count == 2
        and bool(expected_summary["rule_of_thumb_passed"]) is False
    ):
        alternatives.append(
            {
                "method": "fisher_exact",
                "reason": "sparse_2x2_expected_counts",
                "implemented": False,
            },
        )
    return alternatives


def _result_warnings(
    *,
    row_count: int,
    column_count: int,
    expected_summary: dict[str, object],
    n_excluded_missing_row: int,
    n_excluded_missing_column: int,
) -> list[str]:
    warnings = [
        "chi_square_independence_assumption",
        "pearson_chi_square_no_continuity_correction",
    ]
    if n_excluded_missing_row > 0 or n_excluded_missing_column > 0:
        warnings.append("missing_values_excluded")
    if bool(expected_summary["rule_of_thumb_passed"]) is False:
        warnings.append("small_expected_counts")
    if row_count == 2 and column_count == 2:
        warnings.append("two_by_two_table")
        if bool(expected_summary["rule_of_thumb_passed"]) is False:
            warnings.append("fisher_exact_recommended_for_sparse_2x2")
    if row_count * column_count > 100:
        warnings.append("large_contingency_table")
    return warnings
