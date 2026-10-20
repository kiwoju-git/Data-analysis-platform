from dataclasses import replace

import numpy as np
import pytest

from app.statistics.rsm_model_basis import evaluate_rsm_basis, rsm_basis_terms
from app.statistics.rsm_model_workflow import rsm_term_blocks, select_rsm_terms
from app.statistics.term_block_model_selection import (
    DoeSelectionOptions,
    DoeTermPolicy,
    TermBlockSelectionError,
    resolve_term_policies,
    term_catalog,
    term_dependencies,
    term_is_removable,
)


@pytest.mark.parametrize(
    "preset,count",
    [
        ("linear", 5),
        ("linear_squares", 9),
        ("linear_interactions", 11),
        ("full_quadratic", 15),
    ],
)
def test_preset_matrix_has_exact_exponents(preset, count):
    terms = rsm_basis_terms(["A", "B", "C", "D"], preset)
    assert len(terms) == count
    coordinates = np.array([[2, 3, 5, 7]], dtype=float)
    expected = [1, 2, 3, 5, 7]
    if preset in {"linear_interactions", "full_quadratic"}:
        expected += [6, 10, 14, 15, 21, 35]
    if preset in {"linear_squares", "full_quadratic"}:
        expected += [4, 9, 25, 49]
    np.testing.assert_array_equal(
        evaluate_rsm_basis(coordinates, [t.powers for t in terms]), [expected]
    )


def test_square_dependency_is_used_by_policies_catalog_and_removal():
    blocks = rsm_term_blocks(rsm_basis_terms(["A", "B"], "linear_squares"))
    assert not term_is_removable(blocks[1], blocks)
    assert term_is_removable(blocks[3], blocks)
    assert term_catalog(blocks)[3]["hierarchy_dependencies"] == ["factor_1"]
    with pytest.raises(TermBlockSelectionError, match="hierarchy_invalid"):
        resolve_term_policies(
            blocks,
            DoeSelectionOptions(
                term_policies=(
                    DoeTermPolicy("factor_1", "excluded"),
                    DoeTermPolicy("factor_1^2", "forced"),
                )
            ),
        )


@pytest.mark.parametrize("parents", [("missing",), ("factor_1", "factor_1"), ("factor_1^2",)])
def test_invalid_explicit_dependencies_are_rejected(parents):
    blocks = rsm_term_blocks(rsm_basis_terms(["A", "B"], "linear_squares"))
    blocks[3] = replace(blocks[3], depends_on=parents)
    with pytest.raises(TermBlockSelectionError, match="dependencies_invalid"):
        term_dependencies(blocks)


def test_dependency_cycle_is_rejected():
    blocks = rsm_term_blocks(rsm_basis_terms(["A", "B"], "linear_squares"))
    blocks[1] = replace(blocks[1], depends_on=("factor_1^2",))
    with pytest.raises(TermBlockSelectionError, match="dependencies_invalid"):
        term_dependencies(blocks)


def test_rsm_saturated_backward_does_not_pool():
    terms = rsm_basis_terms(["A", "B"], "linear")
    matrix = evaluate_rsm_basis(np.array([[0, 0], [1, 0], [0, 1]]), [t.powers for t in terms])
    with pytest.raises(TermBlockSelectionError, match="requires_residual_df"):
        select_rsm_terms(
            matrix,
            np.array([1.0, 2.0, 4.0]),
            terms,
            DoeSelectionOptions(method="backward_elimination"),
        )
    columns, result = select_rsm_terms(
        matrix, np.array([1.0, 2.0, 4.0]), terms, DoeSelectionOptions()
    )
    assert columns == [0, 1, 2]
    assert result["initial_residual_df"] == 0
    assert result["pooled_term_ids"] == []


def test_selected_rsm_basis_drives_all_fitted_and_contour_values():
    from app.statistics.response_surface import (
        ResponseSurfaceAnalysisRun,
        ResponseSurfaceDesignOptions,
        ResponseSurfaceFactor,
        calculate_response_surface_analysis,
        generate_central_composite_design,
    )

    design = generate_central_composite_design(
        [ResponseSurfaceFactor(name, 10, 20) for name in "ABCD"],
        ResponseSurfaceDesignOptions("rotatable", 1, 1, 7, False, 7, "circumscribed"),
    )
    errors = iter([-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3])
    runs = []
    for run in design.runs:
        a, b = run.coded_levels["A"], run.coded_levels["B"]
        value = 20 + 3 * a - 2 * b + 4 * a * b + 5 * a * a
        if run.center_point:
            value += next(errors)
        runs.append(
            ResponseSurfaceAnalysisRun(
                run.run_order,
                run.standard_order,
                run.point_type,
                run.coded_levels,
                value,
            )
        )
    result = calculate_response_surface_analysis(
        runs,
        design.factors,
        alpha=design.alpha,
        response_name="Y",
        response_unit="g",
        coding_by_name=design.coding,
        model_selection=DoeSelectionOptions(method="backward_elimination"),
    )
    assert result["model_selection"]["final_term_ids"] == [
        "factor_1",
        "factor_2",
        "factor_1:factor_2",
        "factor_1^2",
    ]
    assert result["model_selection"]["pooled_term_ids"] == []
    assert "doe_rsm_post_selection_inference_exploratory" in result["warnings"]
    assert result["sample"]["rank"] == 5
    assert result["stationary_point"]["available"] is False
    assert result["stationary_point"]["reason"] == "singular_hessian"
    for step in result["model_selection"]["steps"]:
        ids = step["active_term_ids"]
        assert "factor_1^2" not in ids or "factor_1" in ids
        assert "factor_1:factor_2" not in ids or {"factor_1", "factor_2"}.issubset(ids)
    for row in result["contour"]["points"]:
        a, b = row["x_coded"], row["y_coded"]
        assert row["predicted"] == pytest.approx(
            20 + 3 * a - 2 * b + 4 * a * b + 5 * a * a, abs=1e-11
        )
    x = np.array(
        [
            [
                1,
                r.coded_levels["A"],
                r.coded_levels["B"],
                r.coded_levels["A"] * r.coded_levels["B"],
                r.coded_levels["A"] ** 2,
            ]
            for r in runs
        ]
    )
    expected = x @ np.array([20, 3, -2, 4, 5])
    np.testing.assert_allclose(
        [row["fitted"] for row in result["diagnostics"]["points"]], expected, atol=1e-11
    )
    h = np.diag(x @ np.linalg.inv(x.T @ x) @ x.T)
    y = np.array([run.response for run in runs])
    assert result["press"] == pytest.approx(
        float(np.sum(((y - expected) / (1 - h)) ** 2)), abs=1e-11
    )
