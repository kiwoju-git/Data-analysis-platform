from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.special import ndtr

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_acquisition import (
    BoAcquisitionContext,
    acquisition_scores,
    build_acquisition_context,
    expected_improvement,
)
from app.statistics.bo_batch_acquisition import BoBatchAcquisition, batch_sample_seed
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate


class PosteriorFixture:
    def __init__(self, covariance=None):
        self.x_train = np.array([[0.0], [1.0]])
        self.means = np.array([0.15, 0.42])
        self.covariance = (
            np.array([[0.25, 0.18], [0.18, 0.49]]) if covariance is None else covariance
        )
        self.query_sizes = []

    def predict(self, x, *, joint=False):
        indices = np.asarray(x)[:, 0].astype(int)
        self.query_sizes.append((len(indices), joint))
        cov = self.covariance[np.ix_(indices, indices)]
        return SimpleNamespace(
            mean_scaled=self.means[indices],
            latent_variance_scaled=np.diag(cov),
            predictive_variance_scaled=np.diag(cov) + 4,
            latent_covariance_scaled=cov if joint else None,
        )

    def latent_cross_covariance(self, x, z):
        a, b = np.asarray(x)[:, 0].astype(int), np.asarray(z)[:, 0].astype(int)
        return self.covariance[np.ix_(a, b)]


def batch(selected=(), *, context=None, sample_count=64, seed=234, model=None):
    return BoBatchAcquisition(
        model or PosteriorFixture(),
        context or BoAcquisitionContext("maximize", 0.07, 0.3),
        np.asarray(selected).reshape(-1, 1),
        sample_count=sample_count,
        root_seed=seed,
        step=len(selected),
        chunk_size=32,
    )


def test_q1_is_exact_analytic_and_base_posterior_not_predictive_noise():
    planner = batch()
    result = planner.score([[1]])
    expected = expected_improvement([0.42], [0.7], 0.3, 0.07)
    np.testing.assert_array_equal(result.scores_scaled, expected)
    np.testing.assert_array_equal(result.latent_variance_scaled, [0.49])
    np.testing.assert_array_equal(result.predictive_variance_scaled, [4.49])
    assert planner.metadata()["effective_sample_count"] == 0


def test_q2_matches_independent_fixed_samples_and_records_base_uncertainty():
    planner = batch([0])
    result = planner.score([[1]])
    seed = int(planner.metadata()["sample_seed"])
    f1 = 0.15 + 0.5 * np.random.default_rng(seed).standard_normal((64, 1))[:, 0]
    mean = 0.42 + 0.18 / 0.25 * (f1 - 0.15)
    sd = np.sqrt(0.49 - 0.18**2 / 0.25)
    threshold = np.maximum(0.3 + 0.07, f1)
    z = (mean - threshold) / sd
    direct = np.mean((mean - threshold) * ndtr(z) + sd * np.exp(-0.5 * z**2) / np.sqrt(2 * np.pi))
    assert result.scores_scaled[0] == pytest.approx(direct, abs=1e-13)
    assert result.mean_scaled[0] == 0.42
    assert result.latent_variance_scaled[0] == 0.49
    assert result.conditional_variance_scaled[0] == pytest.approx(0.3604)
    np.testing.assert_array_equal(planner.score([[1]]).scores_scaled, result.scores_scaled)


def test_target_conditional_radius_is_not_subtracted_twice():
    planner = batch(
        [0], context=BoAcquisitionContext("match_target", 0.07, 0.6, 0.1), sample_count=256
    )
    result = planner.score([[1]])
    seed = int(planner.metadata()["sample_seed"])
    f1 = 0.15 + 0.5 * np.random.default_rng(seed).standard_normal((256, 1))[:, 0]
    means = 0.42 + 0.72 * (f1 - 0.15)
    sd = np.sqrt(0.3604)
    radius = np.minimum(0.53, np.abs(f1 - 0.1))
    nodes, weights = np.polynomial.legendre.leggauss(96)
    u = (nodes + 1) / 2
    locations = radius[:, None] * u
    densities = sum(
        np.exp(-0.5 * ((0.1 + sign * locations - means[:, None]) / sd) ** 2)
        / (sd * np.sqrt(2 * np.pi))
        for sign in [-1, 1]
    )
    direct = np.mean(radius**2 * (densities * (1 - u) * (weights / 2)).sum(axis=1))
    assert result.scores_scaled[0] == pytest.approx(direct, abs=1e-12)
    assert abs(result.scores_scaled[0] - 0.06156206274271664) < 0.02


def test_seed_is_stable_stage_separated_and_mc_samples_are_common():
    assert batch_sample_seed(123, 1) == batch_sample_seed(123, 1)
    assert batch_sample_seed(123, 1) != batch_sample_seed(123, 2)
    assert batch_sample_seed(123, 1) != batch_sample_seed(124, 1)
    planner = batch([0])
    assert isinstance(planner.metadata()["sample_seed"], str)
    assert int(planner.metadata()["sample_seed"]) == planner.sample_seed
    np.testing.assert_array_equal(
        planner.score([[1], [1]]).scores_scaled, planner.score([[1], [1]]).scores_scaled
    )
    np.testing.assert_array_equal(
        planner.score([[1]]).scores_scaled, batch([0]).score([[1]]).scores_scaled
    )


def test_large_pool_uses_bounded_chunks_and_no_candidate_joint_matrix():
    model = PosteriorFixture()
    result = batch([0], model=model).score(np.ones((501, 1)))
    assert result.scores_scaled.shape == (501,)
    assert max(n for n, _ in model.query_sizes) <= 32
    assert all(n <= 7 for n, joint in model.query_sizes if joint)


def test_substantial_negative_covariance_is_not_hidden():
    with pytest.raises(BayesianOptimizationError, match="bayesian_surrogate_covariance_invalid"):
        batch([0, 1], model=PosteriorFixture(np.array([[1.0, 2.0], [2.0, 1.0]])))
    with pytest.raises(BayesianOptimizationError, match="bayesian_surrogate_covariance_invalid"):
        batch([0], model=PosteriorFixture(np.array([[0.25, 0.8], [0.8, 0.49]]))).score([[1]])


def test_singular_latent_covariance_has_recorded_small_numerical_adjustment():
    planner = batch([0, 0])
    result = planner.score([[1]])
    assert planner.metadata()["selected_covariance_adjustment_scaled"] > 0
    assert planner.metadata()["selected_covariance_adjustment_scaled"] < 1e-12
    assert np.isfinite(result.scores_scaled[0])
    assert result.predictive_variance_scaled[0] == 4.49


def test_two_selected_points_use_correlated_joint_draws_not_independent_marginals():
    covariance = np.array([[0.25, 0.18, 0.1], [0.18, 0.49, 0.2], [0.1, 0.2, 0.6]])
    model = PosteriorFixture(covariance)
    model.means = np.array([0.15, 0.42, 0.3])
    model.x_train = np.array([[0.0], [1.0], [2.0]])
    planner = batch([0, 1], model=model)
    result = planner.score([[2]])
    draws = np.random.default_rng(planner.sample_seed).standard_normal((64, 2))
    selected = model.means[:2] + draws @ np.linalg.cholesky(covariance[:2, :2]).T
    weights = np.linalg.solve(covariance[:2, :2], covariance[:2, 2])
    mu = model.means[2] + (selected - model.means[:2]) @ weights
    sd = np.sqrt(covariance[2, 2] - covariance[2, :2] @ weights)
    threshold = np.maximum(0.37, selected.max(axis=1))
    z = (mu - threshold) / sd
    expected = np.mean((mu - threshold) * ndtr(z) + sd * np.exp(-0.5 * z**2) / np.sqrt(2 * np.pi))
    assert result.scores_scaled[0] == pytest.approx(expected, abs=1e-13)
    independent = model.means[:2] + draws * np.sqrt(np.diag(covariance)[:2])
    assert not np.allclose(selected, independent)
    np.testing.assert_array_equal(planner.selected_samples, selected)


def test_conditional_roundoff_is_recorded_and_substantial_error_still_rejected():
    model = PosteriorFixture(np.array([[1e-12, 1.00001e-12], [1.00001e-12, 1e-12]]))
    model.covariance_roundoff_scale = 1.0
    result = batch([0], model=model).score([[1]])
    assert result.conditional_variance_scaled[0] == 0
    assert 0 < result.conditional_variance_adjustment_max_scaled < 1e-14
    assert result.latent_variance_scaled[0] == 1e-12
    model.covariance[0, 1] = model.covariance[1, 0] = 1e-6
    with pytest.raises(BayesianOptimizationError, match="bayesian_surrogate_covariance_invalid"):
        batch([0], model=model).score([[1]])


@pytest.mark.parametrize("count", [0, 15, 257, 16.5, True])
def test_sample_limits_are_not_silently_adjusted(count):
    with pytest.raises(BayesianOptimizationError, match="bayesian_batch_acquisition_input_invalid"):
        batch(sample_count=count)


def fitted_model(*, goal="maximize", near_noiseless=False):
    x = np.array([[0.0], [0.25], [0.5], [0.75], [1.0]])
    y = np.array([1.0, 1.6, 2.0, 1.3, 0.9])
    model = fit_bo_surrogate(
        x,
        y,
        BoSurrogatePolicy(noise_mode="near_noiseless")
        if near_noiseless
        else BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.12),
        {
            "random_seed": 123,
            "jitter": 1e-12 if near_noiseless else 1e-8,
            "hyperparameter_restart_count": 0,
            "model_max_iterations": 80,
            "model_max_evaluations": 300,
        },
        deadline=time.perf_counter() + 30,
        goal_type=goal,
        optimize=False,
    )
    context, metadata = build_acquisition_context(
        model,
        x,
        y,
        [f"trial-{i}" for i in range(len(x))],
        goal_type=goal,
        xi_standardized=0.01,
        target_value=1.8 if goal == "match_target" else None,
    )
    return model, context, metadata


@pytest.mark.parametrize("goal", ["maximize", "minimize", "match_target"])
def test_fitted_surrogate_q1_and_base_posterior_integration(goal):
    model, context, metadata = fitted_model(goal=goal)
    query = np.array([[0.1], [0.4], [0.8]])
    posterior = model.predict(query)
    result = BoBatchAcquisition(model, context, root_seed=12, step=0).score(query)
    np.testing.assert_array_equal(
        result.scores_scaled,
        acquisition_scores(
            posterior.mean_scaled, np.sqrt(posterior.latent_variance_scaled), context
        ),
    )
    np.testing.assert_allclose(
        result.predictive_variance_scaled - result.latent_variance_scaled,
        (0.12 / model.normalization_scale) ** 2,
        rtol=1e-13,
    )
    assert metadata["latent_incumbent_trial_id"].startswith("trial-")
    base = model.predict([[0.65]])
    planned = BoBatchAcquisition(model, context, [[0.4]], root_seed=12, step=1).score([[0.65]])
    np.testing.assert_array_equal(planned.mean_scaled, base.mean_scaled)
    np.testing.assert_array_equal(planned.latent_variance_scaled, base.latent_variance_scaled)
    assert np.isfinite(planned.scores_scaled).all()


@pytest.mark.parametrize("distance", [0.0, 1e-12, 1e-8])
def test_fitted_near_noiseless_covariance_cancellation_is_not_physical_noise(distance):
    model, context, _ = fitted_model(near_noiseless=True)
    planner = BoBatchAcquisition(model, context, [[0.5], [0.5 + distance]], root_seed=12, step=2)
    result = planner.score([[0.5], [0.5 + distance], [0.65]])
    assert np.isfinite(result.scores_scaled).all()
    assert np.all(result.conditional_variance_scaled >= 0)
    np.testing.assert_array_equal(result.predictive_variance_scaled, result.latent_variance_scaled)
    assert planner.metadata()["covariance_adjustment_is_measurement_noise"] is False
