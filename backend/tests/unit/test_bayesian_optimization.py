import math
import queue

import numpy as np
import pytest

from app.statistics.bayesian_batch import (
    calculate_bayesian_recommendation_batch,
)
from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    _novel,
    _SearchBudget,
    bayesian_worker_entry,
    calculate_bayesian_recommendation,
    expected_target_improvement,
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


@pytest.mark.parametrize(
    ("mean", "sigma", "target", "best_distance", "xi"),
    [
        (0.0, 1.0, 0.0, 1.0, 0.0),
        (0.7, 0.2, 0.0, 1.0, 0.01),
        (-0.8, 0.5, 0.25, 1.5, 0.1),
        (0.1, 1e-4, 0.0, 0.5, 0.0),
    ],
)
def test_expected_target_improvement_matches_numerical_quadrature(
    mean: float,
    sigma: float,
    target: float,
    best_distance: float,
    xi: float,
) -> None:
    from scipy.integrate import quad
    from scipy.stats import norm

    radius = max(best_distance - xi, 0.0)
    lower = max(target - radius, mean - 10.0 * sigma)
    upper = min(target + radius, mean + 10.0 * sigma)
    expected = quad(
        lambda value: max(radius - abs(value - target), 0.0)
        * norm.pdf(value, loc=mean, scale=sigma),
        lower,
        upper,
        epsabs=1e-12,
    )[0]
    actual = expected_target_improvement(
        [mean],
        [sigma],
        target,
        best_distance,
        xi,
    )[0]
    assert actual == pytest.approx(expected, rel=1e-10, abs=1e-12)


def test_expected_target_improvement_handles_deterministic_and_exhausted_radius() -> None:
    deterministic = expected_target_improvement(
        [0.1],
        [0.0],
        0.0,
        0.5,
        0.0,
    )[0]
    exhausted = expected_target_improvement([0.0], [1.0], 0.0, 0.5, 0.5)[0]
    assert deterministic == pytest.approx(0.4)
    assert exhausted == 0.0


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


def test_batch_size_one_preserves_single_recommendation_numerics() -> None:
    single_payload = _payload()
    single = calculate_bayesian_recommendation(single_payload)
    batch = calculate_bayesian_recommendation_batch(
        {
            "factors": single_payload["factors"],
            "constraints": single_payload["constraints"],
            "observations": single_payload["observations"],
            "excluded_normalized": single_payload["excluded_normalized"],
            "objective": {
                "goal_type": "maximize",
                "target_value": None,
            },
            "batch_size": 1,
            "acquisition": {
                "kind": "expected_improvement",
                "exploration_profile": "balanced",
                "xi_standardized": 0.01,
            },
            "search": {
                "random_seed": 7,
                "candidate_count_per_step": 64,
                "local_start_count_per_step": 2,
                "max_iterations_per_step": 40,
                "max_evaluations_total": 512,
                "model_max_iterations": 30,
                "model_max_evaluations": 100,
                "hyperparameter_restart_count": 0,
                "time_budget_ms": 10_000,
                "jitter": 1e-8,
                "duplicate_tolerance": 1e-6,
                "batch_policy": "greedy_posterior_mean_fantasy_ei_v1",
            },
        }
    )
    item = batch["items"][0]

    assert item["actual_coordinates"] == pytest.approx(
        single["recommended_actual_coordinates"],
        abs=1e-12,
    )
    assert item["predicted_objective_mean"] == pytest.approx(
        single["predicted_objective_mean"],
        abs=1e-12,
    )
    assert item["posterior_standard_deviation"] == pytest.approx(
        single["posterior_standard_deviation"],
        abs=1e-12,
    )
    assert item["acquisition_value"] == pytest.approx(
        single["expected_improvement"],
        abs=1e-12,
    )


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


def test_duplicate_tolerance_boundary_is_excluded_without_random_fallback() -> None:
    excluded = [[0.5]]

    assert _novel(np.asarray([0.625]), excluded, 0.125) is False
    assert _novel(np.asarray([0.625001]), excluded, 0.125) is True


def test_model_fit_and_acquisition_time_exhaustion_are_typed(monkeypatch) -> None:
    calls = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(
        "app.statistics.bayesian_optimization.time.perf_counter",
        lambda: next(calls, 2.0),
    )
    payload = _payload()
    payload["search"]["time_budget_ms"] = 1_000
    with pytest.raises(BayesianOptimizationError) as fit_error:
        calculate_bayesian_recommendation(payload)
    assert fit_error.value.code == "bayesian_optimization_time_budget_exhausted"

    budget = _SearchBudget(started=0.0, deadline=1.0, max_evaluations=10)
    with pytest.raises(BayesianOptimizationError) as acquisition_error:
        budget.consume()
    assert acquisition_error.value.code == "bayesian_optimization_time_budget_exhausted"


def test_worker_maps_internal_time_exhaustion_to_public_budget_code(monkeypatch) -> None:
    def exhausted(_payload: dict) -> dict:
        raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")

    monkeypatch.setattr(
        "app.statistics.bayesian_optimization.calculate_bayesian_recommendation",
        exhausted,
    )
    output: queue.Queue = queue.Queue()

    bayesian_worker_entry(output, _payload())

    assert output.get_nowait() == {
        "status": "error",
        "code": "bayesian_optimization_budget_exhausted",
    }
