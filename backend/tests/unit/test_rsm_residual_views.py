import numpy as np
import pytest

from app.statistics.doe_residual_views import residual_view, standardized_residuals
from app.statistics.response_surface import (
    ResponseSurfaceAnalysisRun,
    ResponseSurfaceDesignOptions,
    ResponseSurfaceFactor,
    calculate_response_surface_analysis,
    generate_central_composite_design,
)
from app.statistics.term_block_model_selection import DoeSelectionOptions


@pytest.mark.parametrize("preset", ["linear", "full_quadratic"])
def test_rsm_residual_views_match_independent_qr_and_use_full_n(preset: str) -> None:
    factors = [ResponseSurfaceFactor("A", -1, 1), ResponseSurfaceFactor("B", -1, 1)]
    design = generate_central_composite_design(
        factors,
        ResponseSurfaceDesignOptions(
            alpha_mode="rotatable",
            factorial_replicates=1,
            axial_replicates=1,
            center_points=5,
            randomize=True,
            randomization_seed=17,
            ccd_type="inscribed",
        ),
    )
    ordered = sorted(design.runs, key=lambda run: run.run_order)
    xy = np.array([[run.coded_levels["A"], run.coded_levels["B"]] for run in ordered])
    x, y = xy.T
    response = 20 + 3 * x - 2 * y + 0.4 * x * y + 0.7 * x * x + np.sin(np.arange(len(x))) * 0.13
    rows = [
        ResponseSurfaceAnalysisRun(
            run.run_order, run.standard_order, run.point_type, run.coded_levels, float(value)
        )
        for run, value in zip(ordered, response, strict=True)
    ]
    result = calculate_response_surface_analysis(
        rows,
        factors,
        alpha=design.alpha,
        response_name="Synthetic",
        response_unit="kg",
        point_limit=5,
        coding_by_name=design.coding,
        term_preset=preset,  # type: ignore[arg-type]
        model_selection=DoeSelectionOptions(),
    )
    # Independent fixed design matrix and QR solve, not the production fit/basis helper.
    matrix = np.column_stack(
        [np.ones(len(x)), x, y] + ([x * y, x * x, y * y] if preset == "full_quadratic" else [])
    )
    q, r = np.linalg.qr(matrix, mode="reduced")
    beta = np.linalg.solve(r, q.T @ response)
    fitted = matrix @ beta
    residual = response - fitted
    leverage = np.sum(q * q, axis=1)
    mse = residual @ residual / (len(response) - matrix.shape[1])
    standardized = residual / np.sqrt(mse * (1 - leverage))
    plots = result["residual_plots"]
    assert result["schema_version"] == 3
    assert result["observed_response_summary"] == {
        "n": 13,
        "minimum": min(response),
        "maximum": max(response),
        "source": "all_used_responses",
    }
    assert plots["n_total"] == 13 and plots["truncated"]
    for name, expected in (("raw", residual), ("standardized", standardized)):
        view = plots[name]
        assert view["n_available"] == 13 and view["n_displayed"] == 5
        assert sum(bin["count"] for bin in view["histogram"]) == 13
        assert [point["run_order"] for point in view["points"]] == [1, 2, 3, 4, 5]
        assert [point["residual"] for point in view["points"]] == pytest.approx(
            expected[:5], abs=1e-10
        )
        assert [point["fitted"] for point in view["points"]] == pytest.approx(fitted[:5], abs=1e-10)
        ordered_indices = sorted(range(13), key=lambda i: (expected[i], i + 1))
        assert [point["run_order"] for point in view["qq_points"]] == [
            i + 1 for i in ordered_indices[:5]
        ]
        assert view["unavailable_reason"] is None


def test_standardization_does_not_invent_zero_for_unavailable_denominators() -> None:
    errors = np.array([0.1, -0.2, 0.0])
    hats = np.array([0.2, 1.0, 1 - np.finfo(float).eps])
    standardized, reason = standardized_residuals(errors, hats, 0.01, 4)
    assert standardized[0] == pytest.approx(0.1 / np.sqrt(0.008))
    assert np.isnan(standardized[1:]).all()
    assert reason == "standardization_denominator_unavailable"
    view = residual_view(
        standardized, np.ones(3), [3, 1, 2], 5, include_availability=True, unavailable_reason=reason
    )
    assert view["n_available"] == 1 and view["points"][0]["run_order"] == 3
    assert view["histogram"] and sum(row["count"] for row in view["histogram"]) == 1
    for mse, df, expected in (
        (0.0, 3, "residual_variance_unavailable"),
        (None, 0, "no_residual_degrees_of_freedom"),
    ):
        values, reason = standardized_residuals(errors, hats, mse, df)
        assert np.isnan(values).all() and reason == expected


def test_identical_residual_ties_have_stable_run_identity_and_full_histogram() -> None:
    view = residual_view(
        np.zeros(8), np.arange(8.0), [8, 4, 7, 2, 6, 5, 3, 1], 3, include_availability=True
    )
    assert [row["run_order"] for row in view["qq_points"]] == [1, 2, 3]
    assert sum(row["count"] for row in view["histogram"]) == 8
    assert view["reference_line"] == {"slope": 0.0, "intercept": 0.0}


def test_factorial_compatibility_projection_has_no_new_contract_fields() -> None:
    from app.statistics.factorial_model_workflow import _residual_view

    values = np.array([-0.2, 0.1, 0.2, -0.1])
    view = _residual_view(values, np.array([1.0, 2.0, 3.0, 4.0]), [4, 1, 3, 2], 2)
    assert set(view) == {"n", "histogram", "qq_points", "reference_line", "points"}
    assert view == residual_view(values, np.array([1.0, 2.0, 3.0, 4.0]), [4, 1, 3, 2], 2)
    counts, edges = np.histogram(values, bins=5)
    assert view["histogram"] == [
        {"lower": float(edges[i]), "upper": float(edges[i + 1]), "count": int(count)}
        for i, count in enumerate(counts)
    ]
