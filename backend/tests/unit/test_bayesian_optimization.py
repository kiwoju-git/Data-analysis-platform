import math

import numpy as np
import pytest

from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    calculate_bayesian_recommendation,
)


def _payload(*, direction: str = "maximize") -> dict:
    return {
        "factors": [{"factor_id": "x", "low": 0.0, "high": 1.0}],
        "constraints": [],
        "observations": [
            {"normalized": {"x": 0.0}, "objective_value": 0.0},
            {"normalized": {"x": 0.5}, "objective_value": 1.0},
            {"normalized": {"x": 1.0}, "objective_value": 0.2},
        ],
        "excluded_normalized": [[0.0], [0.5], [1.0]],
        "objective_direction": direction,
        "search": {
            "random_seed": 7,
            "xi": 0.01,
            "candidate_count": 64,
            "local_start_count": 2,
            "max_iterations": 40,
            "max_evaluations": 512,
            "model_max_iterations": 30,
            "model_max_evaluations": 100,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 10_000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
        },
    }


def _matern_five_halves(distance: np.ndarray) -> np.ndarray:
    scaled = math.sqrt(5.0) * distance
    return (1.0 + scaled + scaled**2 / 3.0) * np.exp(-scaled)


def test_gp_recommendation_is_seeded_bounded_and_requires_confirmation() -> None:
    first = calculate_bayesian_recommendation(_payload())
    second = calculate_bayesian_recommendation(_payload())

    assert first["recommended_actual_coordinates"] == pytest.approx(
        second["recommended_actual_coordinates"]
    )
    assert first["predicted_objective_mean"] == pytest.approx(
        second["predicted_objective_mean"], abs=1e-12
    )
    assert first["expected_improvement"] == pytest.approx(second["expected_improvement"], abs=1e-12)
    assert 0.0 <= first["recommended_actual_coordinates"]["x"] <= 1.0
    assert first["expected_improvement"] >= 0.0
    assert first["model"]["kernel_policy"] == "constant_times_matern_5_2_ard_v1"
    assert first["model"]["package_versions"]["scikit-learn"] == "1.7.2"
    assert "bayesian_optimization_confirmation_required" in first["warnings"]
    assert "bayesian_optimization_no_global_optimum_guarantee" in first["warnings"]


def test_gp_posterior_matches_direct_matern_linear_algebra() -> None:
    result = calculate_bayesian_recommendation(_payload())
    model = result["model"]
    x_train = np.asarray([[0.0], [0.5], [1.0]], dtype=float)
    observed = np.asarray([0.0, 1.0, 0.2], dtype=float)
    objective_mean = float(model["objective_normalization_mean"])
    objective_scale = float(model["objective_normalization_scale"])
    y_train = (observed - objective_mean) / objective_scale
    constant = float(model["constant_value"])
    length_scale = float(model["length_scales"][0])
    jitter = float(model["jitter"])
    candidate = np.asarray([[result["recommended_normalized_coordinates"]["x"]]], dtype=float)

    train_distance = np.abs(x_train - x_train.T) / length_scale
    covariance = constant * _matern_five_halves(train_distance)
    covariance = covariance + jitter * np.eye(len(x_train))
    cross_distance = np.abs(x_train[:, 0] - candidate[0, 0]) / length_scale
    cross_covariance = constant * _matern_five_halves(cross_distance)
    weights = np.linalg.solve(covariance, y_train)
    standardized_mean = float(cross_covariance @ weights)
    variance = constant - float(cross_covariance @ np.linalg.solve(covariance, cross_covariance))

    expected_mean = standardized_mean * objective_scale + objective_mean
    expected_std = math.sqrt(max(variance, 0.0)) * objective_scale
    assert result["predicted_objective_mean"] == pytest.approx(expected_mean, abs=1e-9)
    assert result["posterior_standard_deviation"] == pytest.approx(expected_std, abs=1e-9)


def test_minimize_direction_and_actual_unit_constraint_are_preserved() -> None:
    payload = _payload(direction="minimize")
    payload["constraints"] = [
        {
            "constraint_id": "upper",
            "name": "Upper bound",
            "terms": [{"factor_id": "x", "coefficient": 1.0}],
            "relation": "less_than_or_equal",
            "bound": 0.4,
        }
    ]
    result = calculate_bayesian_recommendation(payload)

    assert result["objective_direction"] == "minimize"
    assert result["model"]["objective_direction_multiplier"] == -1.0
    assert result["incumbent_objective"] == 0.0
    assert result["recommended_actual_coordinates"]["x"] <= 0.4 + 1e-10
    assert result["constraint_evaluations"][0]["satisfied"] is True


def test_incomplete_history_and_exhausted_model_budget_fail_explicitly() -> None:
    incomplete = _payload()
    incomplete["observations"] = incomplete["observations"][:1]
    with pytest.raises(BayesianOptimizationError) as incomplete_error:
        calculate_bayesian_recommendation(incomplete)
    assert incomplete_error.value.code == "bayesian_optimization_history_incomplete"

    exhausted = _payload()
    exhausted["search"]["model_max_evaluations"] = 2
    with pytest.raises(BayesianOptimizationError) as budget_error:
        calculate_bayesian_recommendation(exhausted)
    assert budget_error.value.code == "bayesian_optimization_budget_exhausted"


def test_no_feasible_novel_candidate_fails_without_fallback() -> None:
    payload = _payload()
    payload["constraints"] = [
        {
            "constraint_id": "impossible",
            "name": "Impossible",
            "terms": [{"factor_id": "x", "coefficient": 1.0}],
            "relation": "less_than_or_equal",
            "bound": -1.0,
        }
    ]
    with pytest.raises(BayesianOptimizationError) as error:
        calculate_bayesian_recommendation(payload)
    assert error.value.code == "bayesian_optimization_no_feasible_candidate"
