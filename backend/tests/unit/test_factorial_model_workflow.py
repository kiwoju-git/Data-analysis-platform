from itertools import product

import numpy as np
import pytest

from app.api.v1.schemas.doe_model_workflow import DoeFinalModelWorkflow
from app.statistics.factorial_model_workflow import (
    FactorialFeature,
    feature_row,
    final_model_workflow,
)


def _workflow(*, replicates=2, point_limit=256, response_offset=None):
    corners = list(product((-1.0, 1.0), repeat=2)) * replicates
    settings = [dict(zip(("A", "B"), row, strict=True)) for row in corners]
    features = [
        FactorialFeature("intercept", "Intercept", "intercept"),
        FactorialFeature("A", "A", "main_effect", ("A",)),
        FactorialFeature("B", "B", "main_effect", ("B",)),
        FactorialFeature("AB", "A * B", "interaction", ("A", "B")),
    ]
    matrix = np.asarray([feature_row(features, row) for row in settings])
    offsets = np.repeat([-0.5, 0.5], 4) if replicates == 2 else np.zeros(4)
    y = matrix @ [10, 2, -3, 0.5] + offsets
    if response_offset is not None:
        y = np.asarray(response_offset, dtype=float)
    coefficients, *_ = np.linalg.lstsq(matrix, y, rcond=None)
    result = final_model_workflow(
        matrix,
        y,
        coefficients,
        features,
        response_name="Yield",
        run_orders=list(range(10, 10 + len(y))),
        factor_levels={"A": [-1, 1], "B": [-1, 1]},
        observed_settings=settings,
        center_points=[False] * len(y),
        block_indices=[None] * len(y),
        coding="coded",
        confidence_level=0.95,
        point_limit=point_limit,
    )
    DoeFinalModelWorkflow.model_validate(result)
    return result, matrix, y


def test_final_coefficients_equation_vif_and_deleted_observation_press():
    result, matrix, y = _workflow()
    rows = result["coded_coefficients"]
    assert rows[0]["effect"] is None
    assert rows[0]["vif"] is None
    assert [row["coefficient"] for row in rows] == pytest.approx([10, 2, -3, 0.5], abs=1e-12)
    assert [row["effect"] for row in rows[1:]] == pytest.approx([4, -6, 1], abs=1e-12)
    assert [row["vif"] for row in rows[1:]] == pytest.approx([1, 1, 1], abs=1e-12)
    assert "+ -" not in result["equation"]["display_equation"]
    press = 0.0
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        coefficient, *_ = np.linalg.lstsq(matrix[mask], y[mask], rcond=None)
        press += (y[i] - matrix[i] @ coefficient) ** 2
    assert result["press"] == pytest.approx(press, abs=1e-10)
    assert result["press"] == pytest.approx(8.0, abs=1e-10)
    linear, interaction = result["anova_groups"]
    assert linear["kind"] == "main_effect" and linear["df"] == 2
    assert linear["adjusted_ss"] == pytest.approx(104, abs=1e-10)
    assert interaction["adjusted_ss"] == pytest.approx(2, abs=1e-10)
    assert [row["adjusted_ss"] for row in linear["terms"]] == pytest.approx([32, 72], abs=1e-10)


def test_histogram_uses_all_rows_and_run_order_is_preserved():
    result, _, _ = _workflow(point_limit=2)
    plots = result["residual_plots"]
    assert plots["truncated"]
    assert plots["n_total"] == 8
    assert len(plots["points"]) == 2
    for kind in ("raw", "standardized"):
        assert sum(bin_["count"] for bin_ in plots[kind]["histogram"]) == 8
        assert [point["run_order"] for point in plots[kind]["points"]] == [10, 11]
        assert len(plots[kind]["qq_points"]) == 2


def test_saturated_model_does_not_invent_inference_or_press():
    result, _, _ = _workflow(replicates=1)
    assert result["press"] is None
    assert result["predicted_r_squared"] is None
    assert "doe_factorial_press_unavailable_high_leverage" in result["warnings"]
    assert result["residual_plots"]["standardized"]["n"] == 0
    for row in result["coded_coefficients"]:
        assert row["standard_error"] is None
        assert row["p_value"] is None


def test_cell_means_and_negative_predicted_r_squared_are_not_clipped():
    result, _, _ = _workflow(response_offset=[1, 1, 1, 1, -1, -1, -1, -1])
    assert result["predicted_r_squared"] == pytest.approx(-3.0, abs=1e-10)
    cells = result["factorial_plots"]["cells"]
    assert len(cells) == 4
    assert all(cell["n"] == 2 for cell in cells)
    assert all(cell["data_mean"] == 0 for cell in cells)
    assert [cell["fitted_mean"] for cell in cells] == pytest.approx([0] * 4, abs=1e-12)


def test_treatment_features_and_structural_features_have_explicit_semantics():
    features = [
        FactorialFeature("intercept", "Constant", "intercept"),
        FactorialFeature("AB:1:2", "A[1] * B[2]", "interaction", ("A", "B"), (1, 2)),
        FactorialFeature("curvature", "Curvature", "center_curvature"),
        FactorialFeature("block", "Block 2", "block", block_index=2),
    ]
    assert feature_row(features, {"A": 1, "B": 2}, center_point=True, block_index=2) == [1, 1, 1, 1]
    assert feature_row(features, {"A": 0, "B": 2}, block_index=1) == [1, 0, 0, 0]
