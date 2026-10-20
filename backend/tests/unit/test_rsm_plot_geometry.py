import json

import numpy as np
import pytest

from app.api.v1.schemas.rsm_plots import RsmContourGeometry, RsmPlotSettings
from app.statistics.rsm_plot_geometry import (
    contour_geometry,
    design_hull_equations,
    hull_slice_polygon,
    outside_design_hull,
)


def test_plane_coordinates_axis_swap_and_finite_json():
    x, y = np.linspace(10, 20, 21), np.linspace(-2, 4, 21)
    z = 2 * x[None, :] + 3 * y[:, None]
    result = contour_geometry(x, y, z, thresholds=[25, 35, 45])
    RsmContourGeometry.model_validate(result)
    json.dumps(result, allow_nan=False)
    assert result["levels"] == [25, 35, 45]
    for line in result["lines"]:
        for path in line["paths"]:
            for px, py in path:
                assert 2 * px + 3 * py == pytest.approx(line["level"], abs=2e-13)
    swapped = contour_geometry(y, x, z.T, thresholds=[25, 35, 45])
    for line in swapped["lines"]:
        for path in line["paths"]:
            for py, px in path:
                assert 2 * px + 3 * py == pytest.approx(line["level"], abs=2e-13)


def test_quadratic_filled_annulus_preserves_holes():
    coordinates = np.linspace(-2, 2, 51)
    z = coordinates[None, :] ** 2 + coordinates[:, None] ** 2
    result = contour_geometry(coordinates, coordinates, z, thresholds=[0.5, 1.5])
    band = next(item for item in result["bands"] if item["lower"] == 0.5)
    assert band["upper"] == 1.5
    assert any(len(polygon["rings"]) == 2 for polygon in band["polygons"])
    for polygon in band["polygons"]:
        for ring in polygon["rings"]:
            assert ring[0] == ring[-1]


def test_saddle_constant_and_invalid_levels():
    coordinates = np.linspace(-1, 1, 21)
    saddle = contour_geometry(
        coordinates,
        coordinates,
        coordinates[None, :] * coordinates[:, None],
        thresholds=[-0.5, 0, 0.5],
    )
    assert len(next(line for line in saddle["lines"] if line["level"] == 0)["paths"]) == 2
    constant = contour_geometry(coordinates, coordinates, np.full((21, 21), 3.5))
    assert constant["constant"]
    assert constant["levels"] == constant["lines"] == []
    assert len(constant["bands"]) == 1
    assert constant["minimum"] == constant["maximum"] == 3.5
    for levels in ([1, 1], [2, 1], [float("nan"), 1]):
        with pytest.raises(ValueError, match="levels_invalid"):
            contour_geometry(coordinates, coordinates, np.full((21, 21), 3.5), thresholds=levels)


def test_full_dimensional_hull_slice_is_not_projected_bounding_box():
    # Octahedron: |x|+|y|+|z|<=1. At z=.5 the exact slice has radius .5.
    design = np.concatenate([np.eye(3), -np.eye(3)])
    equations = design_hull_equations(design)
    polygon = hull_slice_polygon(equations, np.array([0, 0, 0.5]), 0, 1, (-1, 1), (-1, 1))
    assert len(polygon) == 4
    assert all(abs(x) + abs(y) == pytest.approx(0.5, abs=1e-12) for x, y in polygon)
    assert outside_design_hull(
        np.array([[0.4, 0.4, 0.5], [0.1, 0.1, 0.5]]), equations
    ).tolist() == [True, False]


def test_plot_settings_reject_false_dimensions_and_even_grid():
    for values in (
        {"x_factor_id": "factor_1", "y_factor_id": "factor_1"},
        {"x_factor_id": "factor_1", "y_factor_id": "factor_2", "grid_size": 20},
        {"x_factor_id": "factor_1", "plot_kind": "main_effect", "y_factor_id": "factor_2"},
    ):
        with pytest.raises(ValueError):
            RsmPlotSettings.model_validate(values)
