"""Evaluate an explicit final basis for a view; no fit, CV, or response-row reads."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np

from app.api.v1.schemas.doe import ResponseSurfaceDesignResponse, RsmFinalBasisResponse
from app.api.v1.schemas.rsm_plots import RsmPlotBundle, RsmPlotSettings
from app.statistics.doe_factor_domain import DoeFactorDomain
from app.statistics.rsm_model_basis import evaluate_rsm_basis
from app.statistics.rsm_plot_geometry import (
    contour_geometry,
    design_hull_equations,
    hull_slice_polygon,
    outside_design_hull,
)


def default_rsm_plot_settings(design: ResponseSurfaceDesignResponse) -> RsmPlotSettings:
    return RsmPlotSettings(
        x_factor_id="factor_1",
        y_factor_id="factor_2",
        held_actual_values={
            f"factor_{index + 1}": factor.low / 2 + factor.high / 2
            for index, factor in enumerate(design.factors)
            if index >= 2
        },
    )


def default_rsm_overview_settings(design: ResponseSurfaceDesignResponse) -> list[RsmPlotSettings]:
    indices = list(range(len(design.factors)))
    return [
        RsmPlotSettings(
            plot_kind="main_effect" if len(pair) == 1 else "interaction",
            x_factor_id=f"factor_{pair[0] + 1}",
            y_factor_id=None if len(pair) == 1 else f"factor_{pair[1] + 1}",
            held_actual_values={
                f"factor_{index + 1}": factor.low / 2 + factor.high / 2
                for index, factor in enumerate(design.factors)
                if index not in pair
            },
        )
        for pair in [*(tuple([index]) for index in indices), *combinations(indices, 2)]
    ]


def build_rsm_plot_bundle(
    design: ResponseSurfaceDesignResponse,
    basis: RsmFinalBasisResponse,
    settings: RsmPlotSettings,
    *,
    response_name: str,
    response_unit: str | None,
) -> RsmPlotBundle:
    names = [factor.name for factor in design.factors]
    ids = [f"factor_{index + 1}" for index in range(len(names))]
    if names != basis.factor_names or settings.x_factor_id not in ids:
        raise ValueError("doe_rsm_plot_source_invalid")
    x_index = ids.index(settings.x_factor_id)
    y_index = ids.index(settings.y_factor_id) if settings.y_factor_id in ids else None
    if settings.plot_kind != "main_effect" and y_index is None:
        raise ValueError("doe_rsm_plot_axes_invalid")
    varying = {settings.x_factor_id, settings.y_factor_id}
    expected_held = {key for key in ids if key not in varying}
    if set(settings.held_actual_values) != expected_held:
        raise ValueError("doe_rsm_plot_hold_values_invalid")
    centers = np.array([basis.coding[name].center for name in names])
    scales = np.array([basis.coding[name].scale for name in names])
    held = centers.copy()
    for key, value in settings.held_actual_values.items():
        index = ids.index(key)
        factor = design.factors[index]
        if not DoeFactorDomain(
            factor.low, factor.high, factor.domain_kind, factor.step, factor.display_decimals
        ).is_executable(value):
            raise ValueError("doe_rsm_plot_hold_outside_region")
        held[index] = value
    coded_design = np.array([[run.coded_levels[name] for name in names] for run in design.runs])
    equations = design_hull_equations(coded_design)

    def coordinates(index: int) -> np.ndarray:
        factor = design.factors[index]
        return np.linspace(factor.low, factor.high, settings.grid_size)

    def display(index: int, value: float) -> float:
        return float(
            (value - centers[index]) / scales[index] if settings.axis_scale == "coded" else value
        )

    def axis(index: int) -> dict[str, Any]:
        factor = design.factors[index]
        return {
            "factor_id": ids[index],
            "name": names[index],
            "unit": factor.unit if settings.axis_scale == "actual" else None,
            "minimum": display(index, factor.low),
            "maximum": display(index, factor.high),
        }

    x_actual = coordinates(x_index)
    curves: list[dict[str, Any]] = []
    geometry = None
    polygon: list[list[float]] = []
    design_points: list[dict[str, Any]] = []
    if settings.plot_kind == "contour":
        assert y_index is not None
        y_actual = coordinates(y_index)
        actual = np.tile(held, (len(x_actual) * len(y_actual), 1))
        actual[:, x_index] = np.tile(x_actual, len(y_actual))
        actual[:, y_index] = np.repeat(y_actual, len(x_actual))
    else:
        traces: list[float | None] = [None]
        if settings.plot_kind == "interaction":
            assert y_index is not None
            factor = design.factors[y_index]
            traces = list(settings.trace_actual_values or [factor.low, factor.high])
            domain = DoeFactorDomain(
                factor.low, factor.high, factor.domain_kind, factor.step, factor.display_decimals
            )
            if len(set(traces)) != len(traces) or any(
                value is None or not domain.is_executable(value) for value in traces
            ):
                raise ValueError("doe_rsm_plot_trace_invalid")
        actual = np.tile(held, (len(x_actual) * len(traces), 1))
        actual[:, x_index] = np.tile(x_actual, len(traces))
        if y_index is not None:
            actual[:, y_index] = np.repeat(
                [value for value in traces if value is not None], len(x_actual)
            )
    coded = (actual - centers) / scales
    predicted = evaluate_rsm_basis(coded, basis.powers) @ np.asarray(basis.coefficients)
    if not bool(np.isfinite(predicted).all()):
        raise ValueError("doe_rsm_plot_prediction_not_finite")
    outside = outside_design_hull(coded, equations)
    points = [
        {
            "point_id": f"node:{index}",
            "x": display(x_index, row[x_index]),
            "y": (
                display(y_index, row[y_index])
                if settings.plot_kind == "contour" and y_index is not None
                else float(predicted[index])
            ),
            "predicted": float(predicted[index]),
            "outside_design_hull": bool(outside[index]),
        }
        for index, row in enumerate(actual)
    ]
    if settings.plot_kind == "contour":
        assert y_index is not None
        xs = [display(x_index, value) for value in x_actual]
        ys = [display(y_index, value) for value in y_actual]
        geometry = contour_geometry(
            xs,
            ys,
            predicted.reshape((len(ys), len(xs))).tolist(),
            count=settings.contour_levels.count,
            thresholds=settings.contour_levels.thresholds,
        )
        coded_polygon = hull_slice_polygon(
            equations,
            (held - centers) / scales,
            x_index,
            y_index,
            (
                (x_actual[0] - centers[x_index]) / scales[x_index],
                (x_actual[-1] - centers[x_index]) / scales[x_index],
            ),
            (
                (y_actual[0] - centers[y_index]) / scales[y_index],
                (y_actual[-1] - centers[y_index]) / scales[y_index],
            ),
        )
        polygon = [
            [
                display(x_index, centers[x_index] + vertex[0] * scales[x_index]),
                display(y_index, centers[y_index] + vertex[1] * scales[y_index]),
            ]
            for vertex in coded_polygon
        ]
        for run in design.runs:
            design_points.append(
                {
                    "run_order": run.run_order,
                    "x": display(x_index, run.factor_levels[names[x_index]]),
                    "y": display(y_index, run.factor_levels[names[y_index]]),
                    "on_slice": all(
                        abs(
                            run.coded_levels[names[ids.index(key)]]
                            - (held[ids.index(key)] - centers[ids.index(key)])
                            / scales[ids.index(key)]
                        )
                        <= 1e-10
                        for key in expected_held
                    ),
                }
            )
    else:
        for index, trace in enumerate(traces):
            curves.append(
                {
                    "series_id": f"trace:{index}",
                    "trace_actual_value": trace,
                    "points": points[index * len(x_actual) : (index + 1) * len(x_actual)],
                }
            )
    return RsmPlotBundle.model_validate(
        {
            "schema_version": 1,
            "settings": settings,
            "x_axis": axis(x_index),
            "y_axis": axis(y_index) if y_index is not None else None,
            "response_name": response_name,
            "response_unit": response_unit,
            "held_actual_values": {
                names[ids.index(key)]: value for key, value in settings.held_actual_values.items()
            },
            "points": points,
            "curves": curves,
            "geometry": geometry,
            "design_points": design_points,
            "hull_slice_polygon": polygon,
            "final_term_ids": basis.term_ids,
        }
    )
