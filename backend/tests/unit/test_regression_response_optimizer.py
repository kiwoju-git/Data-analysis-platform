from __future__ import annotations

import pytest

from app.statistics.linear_model import LinearModelColumn, calculate_linear_model
from app.statistics.regression_response_optimizer import (
    RegressionResponseOptimizerError,
    calculate_regression_response_optimizer,
)


def test_regression_optimizer_finds_quadratic_interior_optimum_and_profile() -> None:
    rows = [[str(x), str(10.0 - (x - 3.0) ** 2)] for x in range(0, 7)]
    result = calculate_linear_model(
        rows,
        _column("y", 1, "response"),
        [_column("x", 0, "factor")],
        alpha=0.05,
        confidence_level=0.95,
        quadratic_terms=["x"],
    )
    manifest = _manifest(result)

    optimized = calculate_regression_response_optimizer(
        manifest,
        goal="maximize",
        lower=0.0,
        target=10.0,
        upper=None,
        numeric_bounds={},
        fixed_categorical_levels={},
        linear_constraints=[],
        random_seed=19,
        random_candidate_count=128,
        multi_start_count=8,
        max_iterations=200,
        max_evaluations=2_000,
    )

    recommendation = optimized["recommendation"]
    assert recommendation["predictor_settings"]["x"] == pytest.approx(3.0, abs=1e-5)
    assert recommendation["predicted_response"] == pytest.approx(10.0, abs=1e-8)
    assert recommendation["overall_desirability"] == pytest.approx(1.0)
    assert optimized["search"]["global_optimum_guaranteed"] is False
    profile = optimized["profiles"][0]
    assert profile["kind"] == "numeric"
    assert len(profile["points"]) == 41


def test_regression_optimizer_enumerates_observed_categorical_levels() -> None:
    rows = [
        ["0", "A", "1"],
        ["1", "A", "2"],
        ["0", "B", "6"],
        ["1", "B", "7"],
        ["2", "A", "3"],
        ["2", "B", "8"],
    ]
    result = calculate_linear_model(
        rows,
        _column("y", 2, "response"),
        [
            _column("x", 0, "factor"),
            LinearModelColumn(
                column_id="group",
                column_index=1,
                display_name="group",
                data_type="text",
                measurement_level="nominal",
                role="factor",
                unit=None,
            ),
        ],
        alpha=0.05,
        confidence_level=0.95,
    )

    optimized = calculate_regression_response_optimizer(
        _manifest(result),
        goal="maximize",
        lower=0.0,
        target=8.0,
        upper=None,
        numeric_bounds={},
        fixed_categorical_levels={},
        linear_constraints=[],
        random_seed=7,
        random_candidate_count=64,
        multi_start_count=4,
        max_iterations=100,
        max_evaluations=1_000,
    )

    settings = optimized["recommendation"]["predictor_settings"]
    assert settings["group"] == "B"
    categorical_profile = next(
        item for item in optimized["profiles"] if item["column_id"] == "group"
    )
    assert [point["predictor_value"] for point in categorical_profile["points"]] == ["A", "B"]


def test_regression_optimizer_enforces_training_bounds_and_constraints() -> None:
    rows = [[str(x), str(2 * x)] for x in range(8)]
    result = calculate_linear_model(
        rows,
        _column("y", 1, "response"),
        [_column("x", 0, "factor")],
        alpha=0.05,
        confidence_level=0.95,
    )
    manifest = _manifest(result)
    optimized = calculate_regression_response_optimizer(
        manifest,
        goal="maximize",
        lower=0.0,
        target=10.0,
        upper=None,
        numeric_bounds={"x": (1.0, 5.0)},
        fixed_categorical_levels={},
        linear_constraints=[
            {
                "name": "x cap",
                "coefficients": {"x": 1.0},
                "relation": "less_than_or_equal",
                "bound": 4.0,
            }
        ],
        random_seed=5,
        random_candidate_count=64,
        multi_start_count=4,
        max_iterations=100,
        max_evaluations=1_000,
    )
    assert optimized["recommendation"]["predictor_settings"]["x"] <= 4.0 + 1e-7

    with pytest.raises(RegressionResponseOptimizerError) as exc_info:
        calculate_regression_response_optimizer(
            manifest,
            goal="maximize",
            lower=0.0,
            target=10.0,
            upper=None,
            numeric_bounds={"x": (-1.0, 5.0)},
            fixed_categorical_levels={},
            linear_constraints=[],
            random_seed=5,
            random_candidate_count=64,
            multi_start_count=4,
            max_iterations=100,
            max_evaluations=1_000,
        )
    assert exc_info.value.code == "regression_optimizer_factor_bound_invalid"


def _manifest(result: dict[str, object]) -> dict[str, object]:
    return {
        "predictors": result["predictors"],
        "model_specification": result["model_specification"],
        "coefficients": result["coefficients"],
        "training_domain": result["training_domain"],
    }


def _column(column_id: str, index: int, role: str) -> LinearModelColumn:
    return LinearModelColumn(
        column_id=column_id,
        column_index=index,
        display_name=column_id,
        data_type="decimal",
        measurement_level="continuous",
        role=role,
        unit=None,
    )
