from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_acquisition import (
    BoAcquisitionContext,
    acquisition_scores,
    build_acquisition_context,
    expected_improvement,
    expected_target_improvement,
)


@pytest.mark.parametrize("mean,sd", [(0.2, 0.7), (-1.0, 0.15), (2.0, 0.01), (0.0, 1.0)])
def test_ei_matches_independent_payoff_integral(mean, sd):
    threshold = 0.3 + 0.07
    expected = quad(
        lambda z: max(mean + sd * z - threshold, 0.0) * norm.pdf(z),
        -12,
        12,
        points=[(threshold - mean) / sd] if -12 < (threshold - mean) / sd < 12 else None,
        epsabs=1e-12,
    )[0]
    assert float(expected_improvement(mean, sd, 0.3, 0.07)) == pytest.approx(
        expected, abs=1e-11, rel=1e-9
    )


@pytest.mark.parametrize("mean,sd,radius", [(0.2, 0.7, 0.53), (-1.0, 0.15, 0.53), (0.1, 1.0, 1e-8)])
def test_target_ei_matches_independent_payoff_integral(mean, sd, radius):
    target = 0.1
    expected = sum(
        quad(
            lambda y: (radius - abs(y - target)) * norm.pdf((y - mean) / sd) / sd,
            a,
            b,
            epsabs=1e-25 if radius < 1e-6 else 1e-12,
            epsrel=1e-10,
        )[0]
        for a, b in [(target - radius, target), (target, target + radius)]
    )
    assert float(expected_target_improvement(mean, sd, target, radius, 0)) == pytest.approx(
        expected, abs=1e-25 if radius < 1e-6 else 1e-12, rel=1e-7
    )


def test_zero_sd_radius_and_broadcast_have_exact_definitions():
    np.testing.assert_array_equal(expected_improvement([0, 1, 2], 0, 0.5, 0.1), [0, 0.4, 1.4])
    np.testing.assert_allclose(
        expected_target_improvement([0, 1, 2], 0, 1, [0.5, 0.6, 0.7], 0.1), [0, 0.5, 0]
    )
    np.testing.assert_array_equal(expected_target_improvement([0, 1], 1, 0, 0.1, 0.2), [0, 0])
    values = expected_improvement(np.array([[0.0], [0.5]]), 0.2, [0.1, 0.3], 0)
    assert values.shape == (2, 2)


def test_target_symmetry_translation_and_positive_unit_scaling():
    left = expected_target_improvement(-0.4, 0.6, 0.1, 0.8, 0.1)
    right = expected_target_improvement(0.6, 0.6, 0.1, 0.8, 0.1)
    assert float(left) == pytest.approx(float(right), abs=1e-14)
    shifted = expected_target_improvement(1000.6, 0.6, 1000.1, 0.8, 0.1)
    assert float(right) == pytest.approx(float(shifted), abs=1e-12)
    scaled = expected_target_improvement(6, 6, 1, 8, 1)
    assert float(scaled) == pytest.approx(10 * float(right), rel=1e-12)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "1"])
def test_invalid_numeric_input_is_rejected(bad):
    with pytest.raises(BayesianOptimizationError, match="bayesian_acquisition_input_invalid"):
        expected_improvement(bad, 1, 0, 0)
    with pytest.raises(BayesianOptimizationError, match="bayesian_acquisition_input_invalid"):
        expected_target_improvement(0, bad, 0, 1, 0)


def test_negative_sd_xi_and_context_mismatch_are_rejected():
    for args in [(0, -1, 0, 0), (0, 1, 0, -1)]:
        with pytest.raises(BayesianOptimizationError):
            expected_improvement(*args)
    with pytest.raises(BayesianOptimizationError):
        BoAcquisitionContext("match_target", 0.01, 0.3)
    with pytest.raises(BayesianOptimizationError):
        BoAcquisitionContext("maximize", 0.01, 0.3, target_scaled=0)


def test_extreme_ei_is_finite_nonnegative_without_false_improvement():
    result = expected_improvement([-1000.0, -30, -10, 0, 1000], 1, 0, 0)
    assert np.all(np.isfinite(result))
    assert np.all(result >= 0)
    assert result[0] == 0
    assert result[1] > 0
    assert result[-1] == pytest.approx(1000)


def test_target_boundary_tiny_positive_sd_preserves_representable_improvement():
    # At a window endpoint the inward half-normal still has positive gain.
    result = expected_target_improvement(1.0, 1e-20, 0.0, 1.0)
    assert float(result) == pytest.approx(1e-20 / np.sqrt(2 * np.pi), rel=1e-12, abs=0)


def model_stub(means, *, direction=1.0):
    return SimpleNamespace(
        normalization_mean=10.0,
        normalization_scale=2.0,
        direction_multiplier=direction,
        predict=lambda x: SimpleNamespace(mean_scaled=np.array(means)),
    )


def test_incumbent_uses_latent_training_means_not_observed_outlier():
    context, metadata = build_acquisition_context(
        model_stub([0.2, 0.1, 0.6]),
        np.array([[0], [0.5], [1]]),
        np.array([8, 100, 15]),
        ["trial-a", "trial-b", "trial-c"],
        goal_type="maximize",
        xi_standardized=0.07,
    )
    assert context.incumbent_scaled == 0.6
    assert metadata["best_observed_objective"] == 100
    assert metadata["best_observed_trial_id"] == "trial-b"
    assert metadata["latent_incumbent_trial_id"] == "trial-c"
    assert metadata["latent_incumbent_value_raw"] == pytest.approx(11.2)
    assert metadata["xi_raw"] == pytest.approx(0.14)
    np.testing.assert_array_equal(
        acquisition_scores([0.8], [0], context), expected_improvement([0.8], [0], 0.6, 0.07)
    )


def test_target_context_uses_original_response_and_latent_distance():
    context, metadata = build_acquisition_context(
        model_stub([-0.5, 0.25, 0.9]),
        np.array([[0], [0.5], [1]]),
        np.array([8, 11, 15]),
        ["trial-a", "trial-b", "trial-c"],
        goal_type="match_target",
        xi_standardized=0.07,
        target_value=11,
    )
    assert context.target_scaled == 0.5
    assert context.incumbent_scaled == 0.25
    assert metadata["best_observed_target_distance_raw"] == 0
    assert metadata["latent_incumbent_distance_raw"] == 0.5
    assert float(acquisition_scores(0.5, 0, context)) == pytest.approx(0.18)


def test_minimize_direction_and_trial_ids_are_validated():
    context, metadata = build_acquisition_context(
        model_stub([0.2, 0.6, 0.1], direction=-1),
        [[0], [0.5], [1]],
        [8, 11, 15],
        ["a", "b", "c"],
        goal_type="minimize",
        xi_standardized=0,
    )
    assert context.incumbent_scaled == 0.6
    assert metadata["best_observed_trial_id"] == "a"
    assert metadata["latent_incumbent_value_raw"] == pytest.approx(-11.2)
    with pytest.raises(BayesianOptimizationError):
        build_acquisition_context(
            model_stub([0, 1]),
            [[0], [1]],
            [0, 1],
            ["same", "same"],
            goal_type="maximize",
            xi_standardized=0,
        )
