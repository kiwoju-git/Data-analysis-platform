"""Serial contour geometry in data coordinates, shared by SVG and HTML."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import contourpy
import numpy as np
from scipy.spatial import ConvexHull, QhullError  # type: ignore[import-untyped]

MAX_GEOMETRY_VERTICES = 200_000


def contour_geometry(
    x: Sequence[float],
    y: Sequence[float],
    z: Sequence[Sequence[float]],
    *,
    count: int = 6,
    thresholds: Sequence[float] | None = None,
) -> dict[str, Any]:
    xs, ys, values = np.asarray(x, dtype=float), np.asarray(y, dtype=float), np.asarray(z)
    if (
        xs.ndim != 1
        or ys.ndim != 1
        or not 2 <= len(xs) <= 51
        or not 2 <= len(ys) <= 51
        or values.shape != (len(ys), len(xs))
        or not all(bool(np.isfinite(item).all()) for item in (xs, ys, values))
        or not bool(np.all(np.diff(xs) > 0))
        or not bool(np.all(np.diff(ys) > 0))
        or not 2 <= count <= 11
    ):
        raise ValueError("doe_rsm_plot_grid_invalid")
    low, high = float(np.min(values)), float(np.max(values))
    levels = (
        list(thresholds)
        if thresholds is not None
        else [float(value) for value in np.linspace(low, high, count + 2)[1:-1]]
    )
    if thresholds is not None and (
        not 2 <= len(levels) <= 11
        or not bool(np.isfinite(levels).all())
        or any(a >= b for a, b in zip(levels, levels[1:], strict=False))
    ):
        raise ValueError("doe_rsm_contour_levels_invalid")
    payload: dict[str, Any] = {
        "algorithm": "contourpy.serial",
        "algorithm_version": contourpy.__version__,
        "grid_orientation": "z[y_index][x_index]",
        "minimum": low,
        "maximum": high,
        "constant": low == high,
        "levels": [],
        "lines": [],
        "bands": [],
    }
    if low == high:
        payload["bands"] = [
            {
                "lower": low,
                "upper": high,
                "polygons": [
                    {
                        "rings": [
                            [
                                [xs[0], ys[0]],
                                [xs[-1], ys[0]],
                                [xs[-1], ys[-1]],
                                [xs[0], ys[-1]],
                                [xs[0], ys[0]],
                            ]
                        ]
                    }
                ],
            }
        ]
        return payload
    # Auto levels may coincide at float precision; do not invent intermediate values.
    levels = sorted(set(float(level) for level in levels))
    generator = contourpy.contour_generator(
        x=xs, y=ys, z=values, name="serial", line_type="Separate", fill_type="OuterOffset"
    )
    vertex_count = 0
    for level in levels:
        paths = [path.tolist() for path in cast(list[np.ndarray], generator.lines(level))]
        vertex_count += sum(len(path) for path in paths)
        payload["lines"].append({"level": level, "paths": paths})
    edges = [-float("inf"), *levels, float("inf")]
    for lower, upper in zip(edges, edges[1:], strict=False):
        # Separate/OuterOffset above fix the two documented return variants.
        vertices, offsets = cast(
            tuple[list[np.ndarray], list[np.ndarray]], generator.filled(lower, upper)
        )
        polygons = []
        for polygon, ring_offsets in zip(vertices, offsets, strict=True):
            vertex_count += len(polygon)
            polygons.append(
                {
                    "rings": [
                        polygon[start:end].tolist()
                        for start, end in zip(ring_offsets, ring_offsets[1:], strict=False)
                    ]
                }
            )
        payload["bands"].append(
            {
                "lower": lower if np.isfinite(lower) else None,
                "upper": upper if np.isfinite(upper) else None,
                "polygons": polygons,
            }
        )
    if vertex_count > MAX_GEOMETRY_VERTICES:
        raise ValueError("doe_rsm_plot_geometry_limit")
    payload["levels"] = levels
    return payload


def design_hull_equations(coded_design: np.ndarray) -> np.ndarray:
    points = np.unique(np.asarray(coded_design, dtype=float), axis=0)
    if points.ndim != 2 or not bool(np.isfinite(points).all()):
        raise ValueError("doe_rsm_plot_design_invalid")
    try:
        return np.asarray(ConvexHull(points).equations, dtype=float)
    except QhullError as exc:
        raise ValueError("doe_rsm_plot_hull_unavailable") from exc


def outside_design_hull(coded: np.ndarray, equations: np.ndarray) -> np.ndarray:
    # Coded coordinates are bounded CCD values; this tolerance is only a hull-boundary test.
    return np.any(coded @ equations[:, :-1].T + equations[:, -1] > 1e-10, axis=1)


def hull_slice_polygon(
    equations: np.ndarray,
    held_coded: np.ndarray,
    x_index: int,
    y_index: int,
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
) -> list[list[float]]:
    """Clip a rectangle by full-dimensional hull half-spaces at the exact held slice."""
    polygon = [
        [x_bounds[0], y_bounds[0]],
        [x_bounds[1], y_bounds[0]],
        [x_bounds[1], y_bounds[1]],
        [x_bounds[0], y_bounds[1]],
    ]
    held = held_coded.copy()
    held[x_index] = held[y_index] = 0.0
    for equation in equations:
        a, b = equation[x_index], equation[y_index]
        c = float(equation[:-1] @ held + equation[-1])
        output: list[list[float]] = []
        for first, second in zip(polygon, polygon[1:] + polygon[:1], strict=True):
            f = float(a * first[0] + b * first[1] + c)
            s = float(a * second[0] + b * second[1] + c)
            if f <= 1e-10:
                output.append(first)
            if (f <= 1e-10) != (s <= 1e-10):
                fraction = f / (f - s)
                output.append(
                    [float(first[i] + fraction * (second[i] - first[i])) for i in range(2)]
                )
        polygon = output
        if not polygon:
            break
    return polygon
