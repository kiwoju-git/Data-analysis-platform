from dataclasses import replace
from itertools import product

import pytest

from app.statistics.response_optimizer import (
    OptimizerFactor,
    OptimizerModel,
    OptimizerObjective,
    OptimizerSearchOptions,
    OptimizerTerm,
    calculate_response_optimizer,
)
from app.statistics.rsm_coding import factor_coding
from app.statistics.rsm_region import RsmRegionInput, resolve_rsm_region


def region_fixture(kind="circumscribed", mode="axial_bounds", custom=None):
    names = [f"x{index}" for index in range(1, 5)]
    alpha = 1 if kind == "face_centered" else 2
    coding = {name: factor_coding(10, 20, alpha, kind) for name in names}
    coded = [dict(zip(names, row, strict=True)) for row in product((-1.0, 1.0), repeat=4)]
    for name in names:
        for value in (-alpha, alpha):
            coded.append({key: float(value if key == name else 0) for key in names})
    coded.extend(dict.fromkeys(names, 0.0) for _ in range(7))
    actual = [
        {name: coding[name].center + coding[name].scale * row[name] for name in names}
        for row in coded
    ]
    inputs = [RsmRegionInput(name, 10, 20) for name in names]
    return (
        resolve_rsm_region(
            inputs,
            alpha=alpha,
            coding=coding,
            actual_runs=actual,
            coded_runs=coded,
            mode=mode,
            custom_bounds=custom,
        ),
        coding,
        actual,
        coded,
    )


@pytest.mark.parametrize(
    "kind,scale,cube,axial",
    [
        ("circumscribed", 5, (10, 20), (5, 25)),
        ("inscribed", 2.5, (12.5, 17.5), (10, 20)),
        ("face_centered", 5, (10, 20), (10, 20)),
    ],
)
def test_saved_geometry_and_coding_are_distinct_from_region(kind, scale, cube, axial):
    regions, _, _, _ = region_fixture(kind)
    for region in regions:
        assert (region.input_low, region.input_high) == (10, 20)
        assert region.center == 15 and region.scale == scale
        assert (region.factorial_low, region.factorial_high) == cube
        assert (region.axial_low, region.axial_high) == axial
        assert (region.observed_low, region.observed_high) == axial
        assert (region.lower, region.upper) == axial
    cube_regions, *_ = region_fixture(kind, "factorial_cube")
    assert cube_regions[0].scale == scale
    assert (cube_regions[0].lower, cube_regions[0].upper) == cube


def test_region_integrity_and_original_discrete_anchor():
    regions, coding, actual, coded = region_fixture()
    inputs = [RsmRegionInput(name, 10, 20) for name in coding]
    actual[0] = {**actual[0], "x1": 11}
    with pytest.raises(ValueError, match="run_mismatch"):
        resolve_rsm_region(inputs, alpha=2, coding=coding, actual_runs=actual, coded_runs=coded)
    discrete = replace(regions[0], domain_kind="discrete_numeric", step=5)
    assert discrete.lattice_anchor == 10
    assert discrete.is_executable(5) and discrete.is_executable(25)
    assert not discrete.is_executable(6)
    with pytest.raises(ValueError, match="bounds_invalid"):
        region_fixture(mode="custom", custom={name: (4, 25) for name in coding})


@pytest.mark.parametrize(
    "mode,expected_x",
    [("axial_bounds", 23), ("factorial_cube", 20), ("legacy_input_bounds_v1", 20)],
)
def test_ccc_optimizer_preserves_coding_and_finds_axial_optimum(mode, expected_x):
    regions, coding, _, coded = region_fixture(mode=mode)
    factors = tuple(
        OptimizerFactor(name, 10, 20, 2, coding=coding[name], region=region)
        for name, region in zip(coding, regions, strict=True)
    )
    # Independent expansion of 100-(actual_x1-23)^2-sum((actual_xj-15)^2).
    terms = (
        OptimizerTerm("intercept", (), 36),
        OptimizerTerm("main_effect", ("x1",), 80),
        *(OptimizerTerm("quadratic", (name,), -25) for name in coding),
    )
    model = OptimizerModel(
        "source",
        "Y",
        "g",
        factors,
        terms,
        observed_coded_coordinates=tuple(tuple(row[name] for name in coding) for row in coded),
    )
    result = calculate_response_optimizer(
        [OptimizerObjective(model, "maximize", -500, 101, None, 1, 1, 1)],
        factor_bounds=[],
        linear_constraints=[],
        search_options=OptimizerSearchOptions(42, 64, 8, 120, 5000, 5000),
        region_mode=mode,
    )
    point = result["recommendation"]["actual_coordinates"]
    assert point["x1"] == pytest.approx(expected_x, abs=2e-4)
    assert [point[name] for name in ("x2", "x3", "x4")] == pytest.approx([15] * 3, abs=2e-4)
    expected = (
        100 - (point["x1"] - 23) ** 2 - sum((point[name] - 15) ** 2 for name in ("x2", "x3", "x4"))
    )
    assert result["recommendation"]["objectives"][0]["predicted_response"] == pytest.approx(
        expected, abs=1e-10
    )
    assert result["recommendation"]["coded_coordinates"]["x1"] == pytest.approx(
        (point["x1"] - 15) / 5
    )
    assert result["recommendation"]["within_requested_bounds"] is True
    assert result["factor_region"]["resolved_bounds"][0]["scale"] == 5


def test_legacy_plot_settings_serialization_does_not_inject_region_fields():
    from app.api.v1.schemas.rsm_plots import RsmPlotSettings

    old = RsmPlotSettings(x_factor_id="factor_1", y_factor_id="factor_2").model_dump(mode="json")
    assert "region_mode" not in old and "custom_bounds" not in old


@pytest.mark.parametrize("locale", ["ko", "en"])
def test_stored_discrete_plot_report_distinguishes_interpolation_from_executable_runs(locale):
    from app.api.v1.schemas.rsm_plots import RsmPlotBundle
    from app.services.rsm_plot_report import rsm_plot_report

    regions, *_ = region_fixture()
    regions = (replace(regions[0], domain_kind="discrete_numeric", step=5), *regions[1:])
    bundle = RsmPlotBundle.model_validate(
        {
            "schema_version": 2,
            "region_policy_version": 1,
            "resolved_region": [region.payload() for region in regions],
            "settings": {
                "region_mode": "axial_bounds",
                "plot_kind": "main_effect",
                "x_factor_id": "factor_1",
                "y_factor_id": None,
            },
            "x_axis": {"factor_id": "factor_1", "name": "x1", "minimum": 5, "maximum": 25},
            "y_axis": None,
            "response_name": "Y",
            "response_unit": "g",
            "held_actual_values": {},
            "points": [],
            "curves": [],
            "geometry": None,
            "design_points": [],
            "hull_slice_polygon": [],
            "final_term_ids": ["Intercept"],
        }
    )
    original = bundle.model_dump(mode="json")
    html = rsm_plot_report(bundle, locale)
    assert 'data-rsm-discrete-interpolation="true"' in html
    assert ("모든 표시 좌표가" if locale == "ko" else "not every displayed coordinate") in html
    assert bundle.model_dump(mode="json") == original


def test_axial_box_recommendation_outside_observed_hull_is_explicit():
    regions, coding, _, coded = region_fixture()
    factors = tuple(
        OptimizerFactor(name, 10, 20, 2, coding=coding[name], region=region)
        for name, region in zip(coding, regions, strict=True)
    )
    terms = (
        OptimizerTerm("intercept", (), -156),
        *(OptimizerTerm("main_effect", (name,), 80) for name in coding),
        *(OptimizerTerm("quadratic", (name,), -25) for name in coding),
    )
    model = OptimizerModel(
        "source",
        "Y",
        "g",
        factors,
        terms,
        observed_coded_coordinates=tuple(tuple(row[name] for name in coding) for row in coded),
    )
    result = calculate_response_optimizer(
        [OptimizerObjective(model, "maximize", -1000, 101, None, 1, 1, 1)],
        factor_bounds=[],
        linear_constraints=[],
        search_options=OptimizerSearchOptions(42, 64, 8, 120, 5000, 5000),
        region_mode="axial_bounds",
    )
    assert list(result["recommendation"]["actual_coordinates"].values()) == pytest.approx(
        [23] * 4, abs=2e-4
    )
    assert result["recommendation"]["within_requested_bounds"] is True
    assert result["recommendation"]["outside_observed_hull"] is True
    assert "response_optimizer_outside_observed_design_hull" in result["warnings"]
