"""Saved presentation summaries from the exact observations used by Gage ANOVA."""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from math import exp, floor, fsum, hypot, isfinite, lgamma, log, sqrt
from typing import Any, cast

from app.statistics.gage_rr_data import GageObservation, GageRrColumn, PreparedGageData
from app.statistics.subgroup_chart import XBAR_R_CONSTANTS

RAW_POINT_LIMIT = 5000
COMPONENTS = ("total_gage_rr", "repeatability", "reproducibility", "part_to_part")


def build_gage_rr_plot_bundle(
    prepared: PreparedGageData,
    *,
    measurement_column: GageRrColumn,
    variance_components: Mapping[str, object],
    interaction_pooled: bool,
    raw_point_limit: int = RAW_POINT_LIMIT,
) -> dict[str, Any]:
    if not 1 <= raw_point_limit <= RAW_POINT_LIMIT:
        raise ValueError("gage_plot_point_limit_invalid")
    parts = cast(list[str], prepared.design["part_ids"])
    operators = cast(list[str], prepared.design["operator_ids"])
    repeats = cast(int, prepared.design["replicate_count"])
    part_indices = {value: index for index, value in enumerate(parts)}
    operator_indices = {value: index for index, value in enumerate(operators)}
    groups: dict[tuple[int, int], list[GageObservation]] = defaultdict(list)
    part_values: dict[int, list[float]] = defaultdict(list)
    operator_values: dict[int, list[float]] = defaultdict(list)
    values = []
    for observation in prepared.observations:
        p, o = part_indices[observation.part], operator_indices[observation.operator]
        groups[p, o].append(observation)
        part_values[p].append(observation.value)
        operator_values[o].append(observation.value)
        values.append(observation.value)
    cells = []
    for (p, o), observations in sorted(groups.items()):
        cell_values = [item.value for item in observations]
        mean = _mean(cell_values)
        sd = (
            None
            if mean is None
            else _finite(
                hypot(*((value - mean) / sqrt(len(cell_values) - 1) for value in cell_values))
            )
        )
        cells.append(
            {
                "part_index": p,
                "operator_index": o,
                "n": len(cell_values),
                "mean": mean,
                "range": _finite(max(cell_values) - min(cell_values)),
                "sample_sd": sd,
            }
        )

    # All summaries are computed from the full observations, never from this display view.
    raw_points = _display_points(groups, min(len(values), raw_point_limit))
    raw_by_operator: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for point in raw_points:
        raw_by_operator[point["operator_index"]].append(point)
    boxes = [
        _operator_box(o, operator_values[o], raw_by_operator[o]) for o in range(len(operators))
    ]
    component_items = []
    for name in COMPONENTS:
        component = cast(Mapping[str, object], variance_components[name])
        component_items.append(
            {
                "component": name,
                **{
                    key: _finite(component.get(key))
                    for key in (
                        "final_variance",
                        "standard_deviation",
                        "percent_contribution",
                        "percent_study_variation",
                    )
                },
            }
        )
    variance = cast(Mapping[str, object], variance_components["repeatability"])
    repeatability_variance = _finite(variance.get("final_variance"))
    repeatability_sd = _finite(variance.get("standard_deviation"))
    grand_mean = _mean(values)
    halfwidth = (
        None if repeatability_sd is None else _finite(3 * (repeatability_sd / sqrt(repeats)))
    )
    lower = None if grand_mean is None or halfwidth is None else _finite(grand_mean - halfwidth)
    upper = None if grand_mean is None or halfwidth is None else _finite(grand_mean + halfwidth)
    xbar_available = all(
        value is not None for value in (grand_mean, lower, upper, repeatability_variance)
    ) and all(cell["mean"] is not None for cell in cells)
    return {
        "schema_version": 1,
        "measurement": {
            "column_id": measurement_column.column_id,
            "display_name": measurement_column.display_name,
            "unit": measurement_column.unit,
        },
        "measurement_range": {"minimum": min(values), "maximum": max(values)},
        "counts": {
            **{key: prepared.sample[key] for key in ("n_total", "n_used", "n_excluded")},
            "part_count": len(parts),
            "operator_count": len(operators),
            "replicate_count": repeats,
            "cell_count": len(cells),
            "raw_point_count": len(values),
            "displayed_raw_point_count": len(raw_points),
            "raw_point_limit": raw_point_limit,
            "raw_point_policy": "deterministic_cell_stratified_source_row",
            "truncated": len(raw_points) < len(values),
        },
        "parts": [
            {"part_index": p, "n": len(part_values[p]), "mean": _mean(part_values[p])}
            for p in range(len(parts))
        ],
        "operators": [
            {"operator_index": o, "n": len(operator_values[o]), "mean": _mean(operator_values[o])}
            for o in range(len(operators))
        ],
        "cells": cells,
        "components": {
            **_state(
                all(
                    item[key] is not None
                    for item in component_items
                    for key in (
                        "final_variance",
                        "standard_deviation",
                        "percent_contribution",
                        "percent_study_variation",
                    )
                )
            ),
            "items": component_items,
        },
        "dispersion": _dispersion(cells, repeats),
        "xbar": {
            **_state(xbar_available),
            "center": grand_mean,
            "lower_limit": lower,
            "upper_limit": upper,
            "repeatability_variance": repeatability_variance,
            "limit_source": "selected_anova_repeatability",
            "points": [
                {
                    "part_index": cell["part_index"],
                    "operator_index": cell["operator_index"],
                    "n": cell["n"],
                    "value": cell["mean"],
                    "outside_repeatability_limits": _outside(cell["mean"], lower, upper),
                }
                for cell in cells
            ],
        },
        "response_by_part": {
            **_state(all(_mean(part_values[p]) is not None for p in part_values)),
            "points": raw_points,
        },
        "response_by_operator": {
            **_state(
                all(
                    box[key] is not None
                    for box in boxes
                    for key in (
                        "mean",
                        "q1",
                        "median",
                        "q3",
                        "lower_fence",
                        "upper_fence",
                        "lower_whisker",
                        "upper_whisker",
                    )
                )
            ),
            "quantile_policy": "type7_linear",
            "whisker_policy": "observed_values_within_1_5_iqr_fences",
            "boxes": boxes,
        },
        "interaction": {
            **_state(all(cell["mean"] is not None for cell in cells)),
            "interaction_pooled": interaction_pooled,
            "points": [
                {key: cell[key] for key in ("part_index", "operator_index", "n", "mean")}
                for cell in cells
            ],
        },
        "calculation_metadata": {
            "policy_version": "gage_rr_six_panel_v1",
            "part_order": "sorted_full_stripped_identity",
            "operator_order": "sorted_full_stripped_identity",
            "identifier_policy": "zero_based_indices_original_labels_redacted",
            "summary_scope": "all_used_observations_before_display_cap",
            "selected_interaction_policy": "pooled" if interaction_pooled else "retain",
            "replicate_mode": prepared.replicate_mode,
            "xbar_interpretation": "part_discrimination_not_process_stability",
            "interaction_interpretation": "observed_cell_means_even_when_pooled",
        },
    }


def _dispersion(cells: list[dict[str, Any]], repeats: int) -> dict[str, Any]:
    use_range = repeats <= 8
    key = "range" if use_range else "sample_sd"
    values = [cell[key] for cell in cells]
    center = _mean(values) if all(value is not None for value in values) else None
    constants: dict[str, float | None] = dict.fromkeys(("D3", "D4", "c4", "B3", "B4"))
    if use_range:
        constants["D3"] = low_factor = XBAR_R_CONSTANTS[repeats]["d3"]
        constants["D4"] = high_factor = XBAR_R_CONSTANTS[repeats]["d4"]
    else:
        c4 = exp(0.5 * log(2 / (repeats - 1)) + lgamma(repeats / 2) - lgamma((repeats - 1) / 2))
        correction = 3 * sqrt(max(0, 1 - c4 * c4)) / c4
        constants["c4"] = c4
        constants["B3"] = low_factor = max(0, 1 - correction)
        constants["B4"] = high_factor = 1 + correction
    lower = None if center is None else _finite(low_factor * center)
    upper = None if center is None else _finite(high_factor * center)
    return {
        **_state(all(value is not None for value in (center, lower, upper))),
        "statistic": key,
        "policy": "within_cell_range_d3_d4_v1"
        if use_range
        else "within_cell_sample_sd_c4_b3_b4_v1",
        "constant_precision": "D3_D4_three_decimal_table"
        if use_range
        else "c4_lgamma_full_precision",
        "warning_codes": ["within_cell_variation_zero"] if center == 0 else [],
        "center": center,
        "lower_limit": lower,
        "upper_limit": upper,
        "constants": constants,
        "points": [
            {
                "part_index": cell["part_index"],
                "operator_index": cell["operator_index"],
                "n": cell["n"],
                "value": cell[key],
                "outside_limits": _outside(cell[key], lower, upper),
            }
            for cell in cells
        ],
    }


def _display_points(
    groups: Mapping[tuple[int, int], Sequence[GageObservation]], limit: int
) -> list[dict[str, Any]]:
    count = len(groups)
    quota, remainder = divmod(limit, count)
    extra_cells = {index * count // remainder for index in range(remainder)} if remainder else set()
    points = []
    for cell_index, ((p, o), observations) in enumerate(sorted(groups.items())):
        ordered = sorted(observations, key=lambda item: item.source_row_number)
        size = quota + int(cell_index in extra_cells)
        for index in range(size):
            item = ordered[index * len(ordered) // size]
            points.append(
                {
                    "part_index": p,
                    "operator_index": o,
                    "source_row_number": item.source_row_number,
                    "value": item.value,
                }
            )
    return points


def _operator_box(index: int, values: list[float], raw: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(values)
    q1, median, q3 = (_quantile(ordered, p) for p in (0.25, 0.5, 0.75))
    iqr = q3 - q1
    lower_fence, upper_fence = _finite(q1 - 1.5 * iqr), _finite(q3 + 1.5 * iqr)
    observed = [
        value
        for value in ordered
        if (lower_fence is None or value >= lower_fence)
        and (upper_fence is None or value <= upper_fence)
    ]

    def is_outlier(value: float) -> bool:
        return (lower_fence is not None and value < lower_fence) or (
            upper_fence is not None and value > upper_fence
        )

    outlier_values = [value for value in ordered if is_outlier(value)]
    outliers = [
        point for point in raw if point["operator_index"] == index and is_outlier(point["value"])
    ]
    return {
        "operator_index": index,
        "n": len(values),
        "mean": _mean(values),
        "q1": q1,
        "median": median,
        "q3": q3,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "lower_whisker": min(observed) if observed else None,
        "upper_whisker": max(observed) if observed else None,
        "outlier_count": len(outlier_values),
        "displayed_outlier_count": len(outliers),
        "outliers": outliers,
    }


def _quantile(ordered: list[float], p: float) -> float:
    index = (len(ordered) - 1) * p
    lower = floor(index)
    fraction = index - lower
    return (1 - fraction) * ordered[lower] + fraction * ordered[min(lower + 1, len(ordered) - 1)]


def _finite(value: object) -> float | None:
    return (
        float(value)
        if isinstance(value, float | int) and not isinstance(value, bool) and isfinite(value)
        else None
    )


def _mean(values: Sequence[float]) -> float | None:
    try:
        return _finite(fsum(value / len(values) for value in values))
    except OverflowError:
        return None


def _state(available: bool) -> dict[str, Any]:
    return {
        "status": "available" if available else "unavailable",
        "unavailable_reason": None if available else "non_finite_plot_summary",
    }


def _outside(value: float | None, lower: float | None, upper: float | None) -> bool | None:
    return (
        None if value is None or lower is None or upper is None else value < lower or value > upper
    )
