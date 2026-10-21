"""Explicit one-step, observation-order lag lineage; never recursive forecasting."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite

import numpy as np

from app.statistics.gp_validation import GpValidationError


@dataclass(frozen=True)
class LagObservation:
    row_index: int
    time: float
    series: str
    values: dict[str, float | None]


@dataclass(frozen=True)
class LagFeatureResult:
    values_by_row: dict[int, list[float]]
    source_rows_by_row: dict[int, list[int]]
    source_times_by_row: dict[int, list[float]]
    excluded_row_indices: list[int]
    irregular_intervals: bool


def build_lag_features(
    observations: Sequence[LagObservation],
    *,
    column_ids: Sequence[str],
    lags: Sequence[int],
) -> LagFeatureResult:
    if (
        not column_ids
        or len(set(column_ids)) != len(column_ids)
        or not lags
        or len(set(lags)) != len(lags)
        or any(
            isinstance(lag, bool) or not isinstance(lag, int) or not 1 <= lag <= 100 for lag in lags
        )
    ):
        raise GpValidationError("gp_lag_definition_invalid")
    if len({row.row_index for row in observations}) != len(observations):
        raise GpValidationError("gp_validation_row_identity_invalid")
    series: dict[str, list[LagObservation]] = {}
    for row in observations:
        if not isfinite(row.time):
            raise GpValidationError("gp_validation_time_invalid")
        series.setdefault(row.series, []).append(row)
    values: dict[int, list[float]] = {}
    source_rows: dict[int, list[int]] = {}
    source_times: dict[int, list[float]] = {}
    excluded: list[int] = []
    irregular = False
    for members in series.values():
        ordered = sorted(members, key=lambda row: (row.time, row.row_index))
        if len({row.time for row in ordered}) != len(ordered):
            raise GpValidationError("gp_lag_ambiguous_time")
        intervals = np.diff([row.time for row in ordered])
        if len(intervals) > 1 and not np.allclose(intervals, intervals[0], rtol=1e-9, atol=0):
            irregular = True
        for position, row in enumerate(ordered):
            if position < max(lags):
                excluded.append(row.row_index)
                continue
            parents = [(ordered[position - lag], column) for column in column_ids for lag in lags]
            raw = [parent.values.get(column) for parent, column in parents]
            if any(value is None or not isfinite(value) for value in raw):
                excluded.append(row.row_index)
                continue
            values[row.row_index] = [float(value) for value in raw if value is not None]
            source_rows[row.row_index] = [parent.row_index for parent, _ in parents]
            source_times[row.row_index] = [parent.time for parent, _ in parents]
    return LagFeatureResult(values, source_rows, source_times, sorted(excluded), irregular)
