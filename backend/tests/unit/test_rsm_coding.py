import pytest

from app.statistics.ccd_recommendations import recommend_ccd_centers
from app.statistics.rsm_coding import (
    RsmCodingError,
    actual_to_coded,
    coded_to_actual,
    factor_coding,
    resolve_ccd_type,
    rotatable_alpha,
)


@pytest.mark.parametrize(
    "count,mode,factorial_reps,axial_reps,expected",
    [
        (2, "rotatable", 1, 1, "06117b4809d1ebf66cc6026e0912de0ec88da2e904c3431667c75eeb89dc8fa4"),
        (4, "rotatable", 1, 1, "a3b83737bc38165b63748473c59ceb8b9191dbea09036f0e7281ac09c680926a"),
        (
            3,
            "face_centered",
            2,
            1,
            "2b2818440a908ebb230abcd606976f89680b511ee1df9650b845bccbdfd47769",
        ),
    ],
)
def test_literal_pre_expansion_design_hash(count, mode, factorial_reps, axial_reps, expected):
    from app.statistics.response_surface import (
        ResponseSurfaceDesignOptions,
        ResponseSurfaceFactor,
        generate_central_composite_design,
    )

    # Captured from fecaa16, before any CCC/coding changes, by a separate read-only probe.
    design = generate_central_composite_design(
        [
            ResponseSurfaceFactor(f"factor {index}", 0.123 + index, 3.789 + index, "unit")
            for index in range(count)
        ],
        ResponseSurfaceDesignOptions(mode, factorial_reps, axial_reps, 5, True, 42),
    )
    assert design.design_sha256 == expected


@pytest.mark.parametrize(
    "kind,alpha,cube,axial",
    [
        ("circumscribed", 2, (10, 20), (5, 25)),
        ("inscribed", 2, (12.5, 17.5), (10, 20)),
        ("face_centered", 1, (10, 20), (10, 20)),
    ],
)
def test_four_factor_hand_calculated_coordinates(kind, alpha, cube, axial):
    coding = factor_coding(10, 20, alpha, kind)
    assert coding.center == 15
    assert (coded_to_actual(coding, -1), coded_to_actual(coding, 1)) == cube
    assert (coded_to_actual(coding, -alpha), coded_to_actual(coding, alpha)) == axial
    for value in [-alpha, -0.123, 0, 0.7, alpha]:
        assert actual_to_coded(coding, coded_to_actual(coding, value)) == pytest.approx(
            value, abs=1e-14
        )


def test_legacy_rotatable_means_inscribed_and_conflicting_modes_fail():
    assert resolve_ccd_type("rotatable") == "inscribed"
    with pytest.raises(RsmCodingError, match="mismatch"):
        resolve_ccd_type("rotatable", "face_centered")


def test_replicate_weighted_fourth_moment_condition():
    assert rotatable_alpha(4, 1, 1) == 2
    assert rotatable_alpha(4, 2, 1) ** 4 == pytest.approx(32, abs=1e-12)
    assert rotatable_alpha(4, 1, 2) ** 4 == pytest.approx(8, abs=1e-12)


def test_center_recommendation_scope_and_literal_run_totals():
    assert [recommend_ccd_centers(k).center_points for k in range(2, 6)] == [5, 6, 7, 10]
    assert recommend_ccd_centers(4).total_runs == 31
    assert recommend_ccd_centers(4, block_count=2).center_points is None
    assert recommend_ccd_centers(4, factorial_replicates=2).center_points is None
    assert recommend_ccd_centers(4, full_cube=False).center_points is None
