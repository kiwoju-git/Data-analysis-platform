import json
from pathlib import Path

import pytest

from app.statistics.response_surface import (
    ResponseSurfaceAnalysisRun,
    ResponseSurfaceDesignOptions,
    ResponseSurfaceError,
    ResponseSurfaceFactor,
    calculate_response_surface_analysis,
    generate_central_composite_design,
)

FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "reference"
    / "fixtures"
    / "doe_response_surface_nist_reference.json"
)


def _factors() -> list[ResponseSurfaceFactor]:
    return [
        ResponseSurfaceFactor("Temperature", 60.0, 80.0, "C"),
        ResponseSurfaceFactor("Pressure", 5.0, 15.0, "bar"),
    ]


def _options(alpha_mode: str = "rotatable") -> ResponseSurfaceDesignOptions:
    return ResponseSurfaceDesignOptions(
        alpha_mode=alpha_mode,  # type: ignore[arg-type]
        factorial_replicates=1,
        axial_replicates=1,
        center_points=5,
        randomize=False,
        randomization_seed=20260714,
    )


def test_rotatable_central_composite_design_uses_declared_bounds_for_axial_points() -> None:
    design = generate_central_composite_design(_factors(), _options())

    assert design.schema_version == 2
    assert design.family == "central_composite"
    assert design.alpha == pytest.approx(2**0.5)
    assert len(design.runs) == 13
    assert [run.point_type for run in design.runs].count("factorial") == 4
    assert [run.point_type for run in design.runs].count("axial") == 4
    assert [run.point_type for run in design.runs].count("center") == 5
    temperature_levels = [run.factor_levels["Temperature"] for run in design.runs]
    pressure_levels = [run.factor_levels["Pressure"] for run in design.runs]
    assert min(temperature_levels) == pytest.approx(60.0)
    assert max(temperature_levels) == pytest.approx(80.0)
    assert min(pressure_levels) == pytest.approx(5.0)
    assert max(pressure_levels) == pytest.approx(15.0)
    assert len(design.design_sha256) == 64


def test_face_centered_design_and_seeded_randomization_are_reproducible() -> None:
    options = ResponseSurfaceDesignOptions(
        alpha_mode="face_centered",
        factorial_replicates=1,
        axial_replicates=1,
        center_points=3,
        randomize=True,
        randomization_seed=42,
    )
    first = generate_central_composite_design(_factors(), options)
    second = generate_central_composite_design(_factors(), options)

    assert first.alpha == 1.0
    assert first.schema_version == 2
    assert first.family == "central_composite"
    assert first.design_sha256 == second.design_sha256
    assert [run.standard_order for run in first.runs] == [run.standard_order for run in second.runs]


def test_central_composite_design_rejects_duplicate_factors_and_invalid_center_count() -> None:
    with pytest.raises(ResponseSurfaceError, match="doe_rsm_factor_names_not_unique"):
        generate_central_composite_design(
            [ResponseSurfaceFactor("A", 0, 1), ResponseSurfaceFactor("a", 0, 1)],
            _options(),
        )
    with pytest.raises(ResponseSurfaceError, match="doe_rsm_center_points_invalid"):
        generate_central_composite_design(
            _factors(),
            ResponseSurfaceDesignOptions(
                alpha_mode="rotatable",
                factorial_replicates=1,
                axial_replicates=1,
                center_points=0,
                randomize=False,
                randomization_seed=1,
            ),
        )


def test_full_quadratic_surface_recovers_known_stationary_maximum() -> None:
    design = generate_central_composite_design(_factors(), _options())
    runs = []
    for run in design.runs:
        x = run.coded_levels["Temperature"]
        y = run.coded_levels["Pressure"]
        response = 100.0 - (x - 0.2) ** 2 - 2.0 * (y + 0.3) ** 2
        runs.append(
            ResponseSurfaceAnalysisRun(
                run_order=run.run_order,
                standard_order=run.standard_order,
                point_type=run.point_type,
                coded_levels=run.coded_levels,
                response=response,
            )
        )

    result = calculate_response_surface_analysis(
        runs,
        design.factors,
        alpha=design.alpha,
        response_name="Yield",
        response_unit="kg",
    )
    terms = {term["term_id"]: term for term in result["terms"]}  # type: ignore[index]
    stationary = result["stationary_point"]  # type: ignore[index]

    assert terms["factor_1"]["coefficient"] == pytest.approx(0.4)
    assert terms["factor_2"]["coefficient"] == pytest.approx(-1.2)
    assert terms["factor_1^2"]["coefficient"] == pytest.approx(-1.0)
    assert terms["factor_2^2"]["coefficient"] == pytest.approx(-2.0)
    assert stationary["classification"] == "maximum"  # type: ignore[index]
    assert stationary["coded_coordinates"] == pytest.approx(  # type: ignore[index]
        {"Temperature": 0.2, "Pressure": -0.3}
    )
    assert stationary["predicted_response"] == pytest.approx(100.0)  # type: ignore[index]
    assert stationary["within_axial_bounds"] is True  # type: ignore[index]
    assert len(result["contour"]["points"]) == 21 * 21  # type: ignore[index]


def test_nist_response_surface_full_quadratic_reference() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    factor_names = fixture["factor_names"]
    runs = [
        ResponseSurfaceAnalysisRun(
            run_order=row["run_order"],
            standard_order=row["run_order"],
            point_type=row["point_type"],
            coded_levels={factor_names[0]: row["x1"], factor_names[1]: row["x2"]},
            response=row["response"],
        )
        for row in fixture["runs"]
    ]
    result = calculate_response_surface_analysis(
        runs,
        [
            ResponseSurfaceFactor(factor_names[0], -1.0, 1.0),
            ResponseSurfaceFactor(factor_names[1], -1.0, 1.0),
        ],
        alpha=1.0,
        response_name="Uniformity",
        response_unit="percent",
    )
    expected = fixture["expected"]
    coefficient_tolerance = fixture["tolerances"]["coefficient_absolute"]
    fit_tolerance = fixture["tolerances"]["fit_absolute"]
    terms = {term["term_id"]: term for term in result["terms"]}

    for term_id, value in expected["coefficients"].items():
        assert terms[term_id]["coefficient"] == pytest.approx(value, abs=coefficient_tolerance)
    assert result["sample"]["df_residual"] == expected["df_residual"]
    assert result["fit"]["residual_standard_error"] == pytest.approx(
        expected["residual_standard_error"], abs=fit_tolerance
    )
    assert result["fit"]["r_squared"] == pytest.approx(expected["r_squared"], abs=fit_tolerance)
    assert result["fit"]["adjusted_r_squared"] == pytest.approx(
        expected["adjusted_r_squared"], abs=fit_tolerance
    )
    assert result["fit"]["f_statistic"] == pytest.approx(expected["f_statistic"], abs=fit_tolerance)
    assert result["fit"]["f_p_value"] == pytest.approx(expected["f_p_value"], abs=fit_tolerance)


def test_response_surface_analysis_rejects_constant_response_and_rank_deficiency() -> None:
    design = generate_central_composite_design(_factors(), _options())
    constant_runs = [
        ResponseSurfaceAnalysisRun(
            run_order=run.run_order,
            standard_order=run.standard_order,
            point_type=run.point_type,
            coded_levels=run.coded_levels,
            response=4.0,
        )
        for run in design.runs
    ]
    with pytest.raises(ResponseSurfaceError, match="doe_rsm_response_variance_zero"):
        calculate_response_surface_analysis(
            constant_runs,
            design.factors,
            alpha=design.alpha,
            response_name="Y",
            response_unit=None,
        )

    duplicate_runs = [
        ResponseSurfaceAnalysisRun(
            run_order=index,
            standard_order=index,
            point_type="center",
            coded_levels={"Temperature": 0.0, "Pressure": 0.0},
            response=float(index),
        )
        for index in range(1, 7)
    ]
    with pytest.raises(ResponseSurfaceError, match="doe_rsm_model_rank_deficient"):
        calculate_response_surface_analysis(
            duplicate_runs,
            _factors(),
            alpha=1.0,
            response_name="Y",
            response_unit=None,
        )
