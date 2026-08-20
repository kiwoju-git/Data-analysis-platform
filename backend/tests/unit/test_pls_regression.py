from __future__ import annotations

import numpy as np
import pytest

from app.statistics.pls_regression import (
    PlsColumn,
    PlsOptions,
    PlsRegressionError,
    calculate_pls_regression,
    predict_from_pls_basis,
)


def _column(column_id: str, index: int, *, role: str = "predictor") -> PlsColumn:
    return PlsColumn(
        column_id=column_id,
        column_index=index,
        display_name=column_id,
        data_type="decimal",
        measurement_level="continuous",
        role=role,
        unit=None,
    )


def _rows(x: np.ndarray, y: np.ndarray) -> list[list[str]]:
    return [
        [*(str(value) for value in x_row), str(y_value)]
        for x_row, y_value in zip(x, y, strict=True)
    ]


def _manual_one_component_coefficients(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[np.ndarray, float]:
    x_mean = x.mean(axis=0)
    y_mean = y.mean()
    x_centered = x - x_mean
    y_centered = y - y_mean
    weight = x_centered.T @ y_centered
    weight = weight / np.linalg.norm(weight)
    score = x_centered @ weight
    loading = (x_centered.T @ score) / (score.T @ score)
    response_loading = float((y_centered.T @ score) / (score.T @ score))
    rotation = weight / float(loading.T @ weight)
    coefficient = rotation * response_loading
    intercept = float(y_mean - x_mean @ coefficient)
    return coefficient, intercept


def test_one_component_matches_hand_calculation_without_scaling() -> None:
    x = np.asarray(
        [[1.0, 4.0], [2.0, 1.0], [3.0, 5.0], [4.0, 2.0], [5.0, 7.0], [6.0, 3.0]],
    )
    y = np.asarray([3.0, 2.0, 6.0, 4.0, 9.0, 7.0])
    expected_coefficients, expected_intercept = _manual_one_component_coefficients(x, y)

    result = calculate_pls_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=PlsOptions(
            scale=False,
            component_selection="fixed",
            n_components=1,
            max_components=1,
            cv_folds=3,
            cv_shuffle=False,
            plot_point_limit=100,
        ),
    )

    basis = result["prediction_basis"]
    assert isinstance(basis, dict)
    assert basis["coefficients"] == pytest.approx(expected_coefficients.tolist(), abs=1e-12)
    assert basis["effective_intercept"] == pytest.approx(expected_intercept, abs=1e-12)
    fitted = expected_intercept + x @ expected_coefficients
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert [point["fitted"] for point in diagnostics["points"]] == pytest.approx(fitted)


def test_automatic_selection_is_deterministic_for_collinear_predictors() -> None:
    rng = np.random.default_rng(2408)
    first = np.linspace(-3.0, 3.0, 40)
    second = first * 0.998 + rng.normal(0.0, 0.01, first.size)
    third = rng.normal(0.0, 1.0, first.size)
    x = np.column_stack([first, second, third])
    y = 4.0 * first - 0.2 * third + rng.normal(0.0, 0.03, first.size)
    options = PlsOptions(max_components=3, cv_folds=5, cv_seed=91, plot_point_limit=100)

    left = calculate_pls_regression(
        _rows(x, y),
        _column("response", 3, role="response"),
        [_column("x1", 0), _column("x2", 1), _column("x3", 2)],
        options=options,
    )
    right = calculate_pls_regression(
        _rows(x, y),
        _column("response", 3, role="response"),
        [_column("x1", 0), _column("x2", 1), _column("x3", 2)],
        options=options,
    )

    assert left["component_selection"] == right["component_selection"]
    selection = left["component_selection"]
    assert isinstance(selection, dict)
    predicted = [row["predicted_r_squared"] for row in selection["rows"]]
    selected = int(selection["selected_components"])
    assert predicted[selected - 1] == max(predicted)


def test_predictor_count_can_exceed_observation_count() -> None:
    rng = np.random.default_rng(81)
    x = rng.normal(size=(8, 12))
    y = x[:, 0] * 2.0 - x[:, 4] + rng.normal(0.0, 0.02, 8)

    result = calculate_pls_regression(
        _rows(x, y),
        _column("response", 12, role="response"),
        [_column(f"x{index}", index) for index in range(12)],
        options=PlsOptions(max_components=3, cv_folds=4, plot_point_limit=100),
    )

    assert result["sample"]["predictor_count"] == 12  # type: ignore[index]
    assert result["sample"]["n_used"] == 8  # type: ignore[index]


def test_prediction_basis_matches_model_fitted_values() -> None:
    x = np.asarray([[1.0, 10.0], [2.0, 8.0], [4.0, 7.0], [6.0, 4.0], [8.0, 2.0]])
    y = np.asarray([3.0, 4.0, 8.0, 11.0, 15.0])
    result = calculate_pls_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=PlsOptions(max_components=2, cv_folds=2, plot_point_limit=100),
    )
    basis = result["prediction_basis"]
    assert isinstance(basis, dict)
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)

    predicted = [
        predict_from_pls_basis(
            row,
            coefficients=basis["coefficients"],
            effective_intercept=float(basis["effective_intercept"]),
        )
        for row in x
    ]
    assert predicted == pytest.approx([point["fitted"] for point in diagnostics["points"]])


@pytest.mark.parametrize(
    ("x", "y", "code"),
    [
        (np.ones((6, 2)), np.arange(6, dtype=float), "pls_constant_predictor"),
        (np.column_stack([np.arange(6), np.arange(6) ** 2]), np.ones(6), "pls_constant_response"),
    ],
)
def test_rejects_constant_input(x: np.ndarray, y: np.ndarray, code: str) -> None:
    with pytest.raises(PlsRegressionError, match=code):
        calculate_pls_regression(
            _rows(x, y),
            _column("response", 2, role="response"),
            [_column("x1", 0), _column("x2", 1)],
            options=PlsOptions(max_components=1, cv_folds=3, plot_point_limit=100),
        )


def test_complete_case_counts_missing_and_non_numeric_separately() -> None:
    rows = [
        ["1", "2", "3"],
        ["2", "", "4"],
        ["bad", "4", "5"],
        ["4", "5", "6"],
        ["5", "7", "9"],
        ["6", "8", "11"],
    ]
    result = calculate_pls_regression(
        rows,
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=PlsOptions(max_components=1, cv_folds=2, plot_point_limit=100),
    )
    sample = result["sample"]
    assert isinstance(sample, dict)
    assert sample["n_excluded_missing"] == 1
    assert sample["n_excluded_non_numeric"] == 1
    assert sample["n_used"] == 4


def test_negative_predicted_r_squared_is_not_truncated() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=(24, 2))
    y = rng.normal(size=24)
    result = calculate_pls_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=PlsOptions(max_components=2, cv_folds=6, cv_seed=31, plot_point_limit=100),
    )
    selection = result["component_selection"]
    assert isinstance(selection, dict)
    values = [float(row["predicted_r_squared"]) for row in selection["rows"]]
    assert min(values) < 0.0
    assert "pls_negative_predicted_r_squared" in result["warnings"]


def test_score_payload_obeys_plot_limit_and_preserves_row_indices() -> None:
    x = np.column_stack([np.arange(150, dtype=float), np.arange(150, dtype=float) ** 2])
    y = x[:, 0] * 0.4 + x[:, 1] * 0.01
    result = calculate_pls_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=PlsOptions(max_components=1, cv_folds=5, plot_point_limit=100),
    )

    latent = result["latent_components"]
    diagnostics = result["diagnostics"]
    assert isinstance(latent, dict)
    assert isinstance(diagnostics, dict)
    assert len(latent["score_row_indices"]) == 100
    assert len(latent["x_scores"]) == 100
    assert latent["score_row_indices"] == [point["row_index"] for point in diagnostics["points"]]
