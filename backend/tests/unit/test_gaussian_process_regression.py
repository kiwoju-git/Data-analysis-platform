from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import app.statistics.gaussian_process_regression as gp_module
from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
    build_gaussian_process_state,
    calculate_gaussian_process_regression,
    predict_from_gaussian_process_state,
)


def _column(column_id: str, index: int, *, role: str = "predictor") -> GaussianProcessColumn:
    return GaussianProcessColumn(
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
        [*(str(value) for value in row), str(response)] for row, response in zip(x, y, strict=True)
    ]


def _fixture() -> tuple[np.ndarray, np.ndarray]:
    x = np.linspace(-2.5, 2.5, 18).reshape(-1, 1)
    y = np.sin(x[:, 0]) + 0.12 * x[:, 0]
    return x, y


@pytest.mark.parametrize(
    "kernel",
    ["matern_5_2_ard", "matern_3_2_ard", "rbf_ard", "rational_quadratic"],
)
def test_kernel_presets_fit_with_finite_uncertainty(kernel: str) -> None:
    x, y = _fixture()
    result = calculate_gaussian_process_regression(
        _rows(x, y),
        _column("response", 1, role="response"),
        [_column("x", 0)],
        options=GaussianProcessOptions(
            kernel_preset=kernel,  # type: ignore[arg-type]
            optimizer_restarts=0,
            validation_method="none",
            profile_points=12,
            surface_grid_size=10,
            plot_point_limit=100,
        ),
    )

    assert result["summary_type"] == "gaussian_process_regression"
    assert result["kernel"]["preset"] == kernel  # type: ignore[index]
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert all(point["predictive_standard_deviation"] >= 0 for point in diagnostics["points"])
    assert result["two_predictor_surface"] is None


def test_static_rbf_posterior_matches_gpml_reference_fixture() -> None:
    fixture_path = (
        Path(__file__).parents[1]
        / "reference"
        / "fixtures"
        / "gaussian_process_gpml_rbf_reference.json"
    )
    reference = json.loads(fixture_path.read_text(encoding="utf-8"))
    state = build_gaussian_process_state(
        x_train_scaled=np.asarray(reference["x_train"], dtype=float),
        cholesky=np.asarray(reference["cholesky"], dtype=float),
        dual_coefficients=np.asarray(reference["dual_coefficients"], dtype=float),
        x_mean=np.asarray([0.0]),
        x_scale=np.asarray([1.0]),
        y_mean=0.0,
        y_scale=1.0,
        predictor_medians=np.asarray([0.0]),
        signal_kernel_payload={
            "preset": "rbf_ard",
            "amplitude": reference["amplitude"],
            "length_scales": [reference["length_scale"]],
        },
        observation_noise_variance_scaled=reference["observation_noise_variance"],
    )
    actual = predict_from_gaussian_process_state(
        state,
        np.asarray(reference["query"], dtype=float),
    )
    tolerance = reference["absolute_tolerance"]

    assert actual["mean"] == pytest.approx(reference["expected_mean"], abs=tolerance)
    assert actual["latent_standard_deviation"] == pytest.approx(
        reference["expected_latent_standard_deviation"],
        abs=tolerance,
    )
    assert actual["predictive_standard_deviation"] == pytest.approx(
        reference["expected_predictive_standard_deviation"],
        abs=tolerance,
    )


def test_cross_validation_is_deterministic_and_preserves_negative_r_squared() -> None:
    rng = np.random.default_rng(2908)
    x = rng.normal(size=(20, 2))
    y = rng.normal(size=20)
    options = GaussianProcessOptions(
        optimizer_restarts=0,
        cv_optimizer_restarts=0,
        validation_method="k_fold",
        cv_folds=4,
        random_seed=77,
        profile_points=10,
        surface_grid_size=10,
        plot_point_limit=100,
    )
    left = calculate_gaussian_process_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=options,
    )
    right = calculate_gaussian_process_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=options,
    )
    left_summary = left["model_summary"]
    right_summary = right["model_summary"]
    assert isinstance(left_summary, dict) and isinstance(right_summary, dict)
    assert left_summary["predicted_r_squared"] == pytest.approx(
        right_summary["predicted_r_squared"]
    )
    assert float(left_summary["predicted_r_squared"]) < 0
    assert "gp_negative_cv_r_squared" in left["warnings"]


def test_complete_case_counts_and_noise_modes() -> None:
    rows = [
        ["0", "0"],
        ["1", "1"],
        ["", "2"],
        ["bad", "3"],
        ["4", "4"],
        ["5", "5"],
        ["6", "6"],
    ]
    result = calculate_gaussian_process_regression(
        rows,
        _column("response", 1, role="response"),
        [_column("x", 0)],
        options=GaussianProcessOptions(
            noise_mode="fixed",
            fixed_noise_standard_deviation=0.2,
            optimizer_restarts=0,
            validation_method="none",
            profile_points=10,
            surface_grid_size=10,
            plot_point_limit=100,
        ),
    )
    sample = result["sample"]
    assert isinstance(sample, dict)
    assert sample["n_used"] == 5
    assert sample["n_excluded_missing"] == 1
    assert sample["n_excluded_non_numeric"] == 1
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert all(
        point["predictive_standard_deviation"] > point["latent_standard_deviation"]
        for point in diagnostics["points"]
    )


@pytest.mark.parametrize("noise_mode", ["estimate", "fixed", "near_noiseless"])
def test_noise_modes_and_repeated_coordinates_are_explicit(noise_mode: str) -> None:
    x = np.asarray([[0.0], [0.0], [1.0], [1.0], [2.0], [2.0], [3.0], [3.0]])
    y = np.asarray([0.0, 0.1, 0.8, 0.9, 0.2, 0.3, -0.5, -0.4])
    result = calculate_gaussian_process_regression(
        _rows(x, y),
        _column("response", 1, role="response"),
        [_column("x", 0)],
        options=GaussianProcessOptions(
            noise_mode=noise_mode,  # type: ignore[arg-type]
            fixed_noise_standard_deviation=0.1 if noise_mode == "fixed" else None,
            optimizer_restarts=0,
            validation_method="none",
            profile_points=10,
            surface_grid_size=10,
            plot_point_limit=100,
        ),
    )
    assert result["method"]["noise_mode"] == noise_mode  # type: ignore[index]
    points = result["diagnostics"]["points"]  # type: ignore[index]
    assert all(np.isfinite(point["predictive_standard_deviation"]) for point in points)
    if noise_mode == "near_noiseless":
        assert all(
            point["predictive_standard_deviation"]
            == pytest.approx(point["latent_standard_deviation"])
            for point in points
        )


def test_unscaled_and_unnormalized_fit_preserves_requested_policy() -> None:
    x, y = _fixture()
    result = calculate_gaussian_process_regression(
        _rows(x, y),
        _column("response", 1, role="response"),
        [_column("x", 0)],
        options=GaussianProcessOptions(
            standardize_predictors=False,
            normalize_response=False,
            optimizer_restarts=0,
            validation_method="none",
            profile_points=10,
            surface_grid_size=10,
            plot_point_limit=100,
        ),
    )
    method = result["method"]
    assert method["standardize_predictors"] is False  # type: ignore[index]
    assert method["normalize_response"] is False  # type: ignore[index]


def test_cross_validation_refits_each_training_fold(monkeypatch) -> None:
    rng = np.random.default_rng(920)
    x = rng.normal(size=(18, 2))
    y = np.sin(x[:, 0]) + x[:, 1] ** 2
    observed_training_means: list[tuple[float, ...]] = []
    original = gp_module._fit_model

    def recording_fit(
        training_x: np.ndarray,
        training_y: np.ndarray,
        options: GaussianProcessOptions,
    ):
        observed_training_means.append(tuple(np.mean(training_x, axis=0)))
        return original(training_x, training_y, options)

    monkeypatch.setattr(gp_module, "_fit_model", recording_fit)
    calculate_gaussian_process_regression(
        _rows(x, y),
        _column("response", 2, role="response"),
        [_column("x1", 0), _column("x2", 1)],
        options=GaussianProcessOptions(
            optimizer_restarts=0,
            cv_optimizer_restarts=0,
            validation_method="k_fold",
            cv_folds=3,
            random_seed=31,
            profile_points=10,
            surface_grid_size=10,
            plot_point_limit=100,
        ),
    )
    assert len(observed_training_means) == 4
    assert len(set(observed_training_means[:3])) == 3
    assert observed_training_means[-1] == pytest.approx(tuple(np.mean(x, axis=0)))


@pytest.mark.parametrize(
    ("x", "predictors", "code"),
    [
        (
            np.arange(501, dtype=float).reshape(-1, 1),
            [_column("x", 0)],
            "gp_usable_rows_limit",
        ),
        (
            np.arange(70, dtype=float).reshape(5, 14)[:, :13],
            [_column(f"x{index}", index) for index in range(13)],
            "gp_predictor_count_limit",
        ),
    ],
)
def test_exact_gp_resource_limits_do_not_sample(
    x: np.ndarray,
    predictors: list[GaussianProcessColumn],
    code: str,
) -> None:
    y = np.arange(x.shape[0], dtype=float)
    with pytest.raises(GaussianProcessRegressionError, match=code):
        calculate_gaussian_process_regression(
            _rows(x, y),
            _column("response", x.shape[1], role="response"),
            predictors,
            options=GaussianProcessOptions(
                optimizer_restarts=0,
                validation_method="none",
                profile_points=10,
                surface_grid_size=10,
                plot_point_limit=100,
            ),
        )


@pytest.mark.parametrize(
    ("x", "y", "code"),
    [
        (np.ones((8, 1)), np.arange(8, dtype=float), "gp_constant_predictor"),
        (np.arange(8, dtype=float).reshape(-1, 1), np.ones(8), "gp_constant_response"),
    ],
)
def test_rejects_constant_input(x: np.ndarray, y: np.ndarray, code: str) -> None:
    with pytest.raises(GaussianProcessRegressionError, match=code):
        calculate_gaussian_process_regression(
            _rows(x, y),
            _column("response", 1, role="response"),
            [_column("x", 0)],
            options=GaussianProcessOptions(
                optimizer_restarts=0,
                validation_method="none",
                profile_points=10,
                surface_grid_size=10,
                plot_point_limit=100,
            ),
        )


def test_leave_one_out_limit_is_explicit() -> None:
    x = np.arange(201, dtype=float).reshape(-1, 1)
    y = np.sin(x[:, 0])
    with pytest.raises(GaussianProcessRegressionError, match="gp_leave_one_out_limit"):
        calculate_gaussian_process_regression(
            _rows(x, y),
            _column("response", 1, role="response"),
            [_column("x", 0)],
            options=GaussianProcessOptions(
                optimizer_restarts=0,
                validation_method="leave_one_out",
                profile_points=10,
                surface_grid_size=10,
                plot_point_limit=100,
            ),
        )
