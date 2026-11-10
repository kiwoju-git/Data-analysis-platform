from __future__ import annotations

import math
import time
from dataclasses import replace

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import DesirabilityGoal
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_posterior import evaluate_surrogate_desirability
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate


def models():
    x = np.array([[0], [0.2], [0.4], [0.8], [1.0]])
    observations = {"yield": np.array([10, 15, 16, 12, 9.0]), "cost": np.array([5, 4, 3, 2, 4.0])}
    settings = {
        "random_seed": 13,
        "jitter": 1e-8,
        "hyperparameter_restart_count": 0,
        "model_max_iterations": 50,
        "model_max_evaluations": 200,
    }
    fitted = {
        key: fit_bo_surrogate(
            x,
            y,
            BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.2),
            settings,
            deadline=time.perf_counter() + 30,
            optimize=False,
        )
        for key, y in observations.items()
    }
    return x, observations, fitted


def kernel(x, q):
    distance = np.abs(x[:, None, 0] - q[None, :, 0])
    radius = math.sqrt(5) * distance
    return (1 + radius + radius**2 / 3) * np.exp(-radius)


def test_actual_gp_bridge_matches_independent_cholesky_and_raw_payoff_integrals(monkeypatch):
    x, observations, fitted = models()
    before = {
        key: (
            model.x_train.copy(),
            model.alpha.copy(),
            model.lower.copy(),
            model.kernel.theta.copy(),
        )
        for key, model in fitted.items()
    }
    goals = (
        DesirabilityGoal("yield", "maximize", 8, 18, None, 1),
        DesirabilityGoal("cost", "minimize", None, 1, 6, 2),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("desirability evaluation must never refit a model")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    result = evaluate_surrogate_desirability(fitted, goals, [0.6])
    expected_first, expected_second = 1.0, 1.0
    q = np.array([[0.6]])
    for index, response in enumerate(result.responses):
        y = observations[response.response_id]
        scale, average = float(y.std(ddof=0)), float(y.mean())
        ky = kernel(x, x) + np.eye(len(x)) * ((0.2 / scale) ** 2 + 1e-8)
        cross = kernel(x, q)
        mean = (
            float((cross.T @ np.linalg.solve(ky, (y - average) / scale)).item()) * scale + average
        )
        variance = float((1 - cross.T @ np.linalg.solve(ky, cross)).item()) * scale**2
        sd = math.sqrt(variance)
        assert response.mean_raw == pytest.approx(mean, rel=1e-10)
        assert response.latent_standard_deviation_raw == pytest.approx(sd, rel=1e-9)
        assert response.predictive_standard_deviation_raw**2 - variance == pytest.approx(
            0.04, abs=1e-11
        )
        lower, upper, weight = (8, 18, 1 / 3) if index == 0 else (1, 6, 2 / 3)

        def moment(power, lower=lower, upper=upper, mean=mean, sd=sd, index=index):
            def payoff(value):
                d = (
                    (value - lower) / (upper - lower)
                    if index == 0
                    else (upper - value) / (upper - lower)
                )
                return d**power * norm.pdf((value - mean) / sd) / sd

            tail = norm.sf((upper - mean) / sd) if index == 0 else norm.cdf((lower - mean) / sd)
            return quad(payoff, lower, upper, epsabs=1e-12, epsrel=1e-10)[0] + tail

        expected_first *= moment(weight)
        expected_second *= moment(2 * weight)
    assert result.moments.mean == pytest.approx(expected_first, abs=3e-11)
    assert result.moments.variance == pytest.approx(expected_second - expected_first**2, abs=3e-11)
    score = beta_expected_improvement(result.moments.mean, result.moments.variance, 0.5)
    assert score.value > 0
    for key, model in fitted.items():
        for actual, original in zip(
            (model.x_train, model.alpha, model.lower, model.kernel.theta), before[key], strict=True
        ):
            np.testing.assert_array_equal(actual, original)


def test_bridge_preserves_mapping_order_and_rejects_direction_transformed_models():
    _, _, fitted = models()
    goals = (
        DesirabilityGoal("yield", "maximize", 8, 18, None),
        DesirabilityGoal("cost", "minimize", None, 1, 6),
    )
    first = evaluate_surrogate_desirability(fitted, goals, [0.6])
    reordered = evaluate_surrogate_desirability(
        dict(reversed(list(fitted.items()))), goals[::-1], [0.6]
    )
    assert first.moments.mean == pytest.approx(reordered.moments.mean, abs=1e-14)
    fitted["cost"] = replace(fitted["cost"], direction_multiplier=-1)
    with pytest.raises(BayesianOptimizationError, match="model_contract"):
        evaluate_surrogate_desirability(fitted, goals, [0.6])


@pytest.mark.parametrize(
    "coordinates", [[True], [0.5, True], ["0.5"], [math.nan], [-0.1], [1.1], [[0.5]], []]
)
def test_bridge_rejects_invalid_normalized_coordinates(coordinates):
    _, _, fitted = models()
    with pytest.raises(BayesianOptimizationError):
        evaluate_surrogate_desirability(
            {"yield": fitted["yield"]},
            (DesirabilityGoal("yield", "maximize", 8, 18, None),),
            coordinates,
        )
