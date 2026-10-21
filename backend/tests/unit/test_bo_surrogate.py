from __future__ import annotations

import math
import time

import numpy as np
import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_surrogate import (
    BoSurrogatePolicy,
    _kernel,
    _likelihood,
    checked_variance,
    fit_bo_surrogate,
    split_signal_noise,
)


def search_options():
    return {
        "random_seed": 123,
        "jitter": 1e-8,
        "hyperparameter_restart_count": 0,
        "model_max_iterations": 80,
        "model_max_evaluations": 300,
    }


def matern(x, y):
    distance = np.sqrt(np.sum((x[:, None, :] - y[None, :, :]) ** 2, axis=2))
    scaled = math.sqrt(5) * distance
    return (1 + scaled + scaled**2 / 3) * np.exp(-scaled)


@pytest.mark.parametrize("mode", ["estimate", "fixed", "near_noiseless"])
def test_fixed_hyperparameters_match_independent_cholesky(mode):
    x = np.array([[0.0], [0.2], [0.2], [0.8], [1.0]])
    y = np.array([1.0, 1.7, 2.1, 1.2, 0.9])
    q = np.array([[0.2], [0.3], [0.9]])
    policy = BoSurrogatePolicy(noise_mode=mode, fixed_noise_sd=0.12 if mode == "fixed" else None)
    model = fit_bo_surrogate(
        x, y, policy, search_options(), deadline=time.perf_counter() + 30, optimize=False
    )
    prediction = model.predict(q, joint=True)
    scale = float(np.std(y, ddof=0))
    noise = {"estimate": 1e-2, "fixed": (0.12 / scale) ** 2, "near_noiseless": 0.0}[mode]
    ky = matern(x, x) + np.eye(len(x)) * (noise + 1e-8)
    lower = np.linalg.cholesky(ky)
    cross = matern(x, q)
    alpha = np.linalg.solve(lower.T, np.linalg.solve(lower, (y - np.mean(y)) / scale))
    v = np.linalg.solve(lower, cross)
    covariance = matern(q, q) - v.T @ v
    np.testing.assert_allclose(prediction.mean_scaled, cross.T @ alpha, rtol=1e-9, atol=1e-10)
    np.testing.assert_allclose(
        prediction.latent_covariance_scaled, covariance, rtol=1e-8, atol=2e-10
    )
    np.testing.assert_allclose(
        prediction.predictive_variance_scaled - prediction.latent_variance_scaled, noise, atol=2e-15
    )
    assert model.metadata()["normalization"]["ddof"] == 0
    assert model.metadata()["observation_noise_sd_raw"] == pytest.approx(math.sqrt(noise) * scale)
    assert model.metadata()["jitter"] == 1e-8


def test_same_location_future_observations_have_independent_noise():
    model = fit_bo_surrogate(
        np.array([[0.0], [0.5], [1.0]]),
        np.array([0.0, 2.0, 1.0]),
        BoSurrogatePolicy(),
        search_options(),
        deadline=time.perf_counter() + 30,
        optimize=False,
    )
    prediction = model.predict(np.array([[0.3], [0.3]]), joint=True)
    cov = prediction.latent_covariance_scaled
    assert cov[0, 0] == pytest.approx(cov[0, 1])
    assert prediction.predictive_variance_scaled[0] > cov[0, 1]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lower_noise_variance_scaled": 1},
        {"upper_noise_variance_scaled": float("inf")},
        {"initial_noise_variance_scaled": 0},
        {"initial_noise_variance_scaled": 2},
        {"noise_mode": "fixed"},
        {"noise_mode": "fixed", "fixed_noise_sd": -1},
        {"noise_mode": "near_noiseless", "fixed_noise_sd": 1},
    ],
)
def test_invalid_noise_policy_is_not_reordered_or_clipped(kwargs):
    with pytest.raises(ValueError):
        BoSurrogatePolicy(**kwargs)


@pytest.mark.parametrize("noise_sd", [1e308, 1e-308])
def test_unrepresentable_fixed_noise_variance_has_stable_error(noise_sd):
    with pytest.raises(BayesianOptimizationError, match="bayesian_surrogate_noise_invalid"):
        _kernel(1, BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=noise_sd), 1.0)


def test_kernel_tree_is_typed_not_string_parsed():
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern, WhiteKernel

    signal, noise = split_signal_noise(
        ConstantKernel(2.0) * Matern([0.3, 0.7], nu=2.5) + WhiteKernel(0.04)
    )
    assert signal.k1.constant_value == 2.0
    assert noise == 0.04
    with pytest.raises(ValueError):
        split_signal_noise(RBF() + WhiteKernel())


def test_noise_estimation_records_real_optimizer_status_and_is_seeded():
    x = np.linspace(0, 1, 20).reshape(-1, 1)
    y = np.sin(x[:, 0] * 4) + np.random.default_rng(34).normal(0, 0.15, len(x))
    models = [
        fit_bo_surrogate(
            x, y, BoSurrogatePolicy(), search_options(), deadline=time.perf_counter() + 30
        )
        for _ in range(2)
    ]
    np.testing.assert_allclose(
        models[0].predict(x).mean_scaled, models[1].predict(x).mean_scaled, rtol=1e-12, atol=1e-12
    )
    details = models[0].metadata()
    assert details["noise"]["fitted_variance_scaled"] >= 1e-6
    assert details["noise"]["fitted_variance_scaled"] <= 1.0
    assert details["optimizer"]["name"] == "L-BFGS-B"
    assert details["optimizer"]["evaluations"] > 0
    assert isinstance(details["optimizer"]["starts"][0]["success"], bool)


def test_likelihood_gradient_matches_central_difference():
    x = np.array([[0.0, 0.1], [0.4, 0.6], [0.4, 0.6], [0.9, 0.2]])
    y = np.array([-1.0, 0.3, 0.8, -0.1])
    kernel = _kernel(2, BoSurrogatePolicy(), 1.0)
    theta = kernel.theta
    value, gradient, _, _ = _likelihood(theta, kernel, x, y, 1e-8)
    step = 1e-5
    differences = []
    for index in range(len(theta)):
        delta = np.zeros(len(theta))
        delta[index] = step
        upper = _likelihood(theta + delta, kernel, x, y, 1e-8)[0]
        lower = _likelihood(theta - delta, kernel, x, y, 1e-8)[0]
        differences.append((upper - lower) / (2 * step))
    assert math.isfinite(value)
    np.testing.assert_allclose(gradient, differences, atol=2e-7, rtol=2e-6)


def test_bounded_cross_covariance_matches_joint_block():
    model = fit_bo_surrogate(
        [[0.0], [0.5], [1.0]],
        [0.0, 2.0, 1.0],
        BoSurrogatePolicy(),
        search_options(),
        deadline=time.perf_counter() + 30,
        optimize=False,
    )
    left, right = np.array([[0.1], [0.3]]), np.array([[0.6], [0.9]])
    covariance = model.predict(np.concatenate([left, right]), joint=True).latent_covariance_scaled
    np.testing.assert_allclose(
        model.latent_cross_covariance(left, right), covariance[:2, 2:], atol=1e-14
    )
    with pytest.raises(BayesianOptimizationError, match="prediction_invalid"):
        model.latent_cross_covariance(left, np.zeros((9, 1)))


def test_substantial_negative_covariance_is_not_silently_clipped():
    np.testing.assert_array_equal(checked_variance([-1e-15, 0, 0.1], 1.0), [0, 0, 0.1])
    for invalid in ([-1e-5], [float("nan")], [float("inf")]):
        with pytest.raises(BayesianOptimizationError, match="covariance_invalid"):
            checked_variance(invalid, 1.0)


@pytest.mark.parametrize("budget", ["deadline", "evaluations"])
def test_fit_budget_failure_does_not_return_partial_model(budget):
    options = search_options()
    options["model_max_evaluations"] = 1
    deadline = time.perf_counter() + (30 if budget == "evaluations" else -1)
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        fit_bo_surrogate(
            [[0], [0.4], [1]], [0, 1, 0.1], BoSurrogatePolicy(), options, deadline=deadline
        )


@pytest.mark.parametrize("mode", ["estimate", "fixed", "near_noiseless"])
def test_unequal_exact_replicates_preserve_full_raw_likelihood_and_posterior(mode):
    x = np.array([[0.0], [0.0], [0.0], [0.4], [0.9], [0.9]])
    y = np.array([0.1, 0.4, -0.2, 0.8, 1.2, 1.2])
    members = ((0, 1, 2), (3,), (4, 5))
    policy = BoSurrogatePolicy(noise_mode=mode, fixed_noise_sd=0.2 if mode == "fixed" else None)
    options = search_options()
    # Avoid ill-conditioned raw replicate subtraction dominating this equivalence check.
    options["jitter"] = 1e-4
    raw = fit_bo_surrogate(x, y, policy, options, deadline=time.perf_counter() + 30, optimize=False)
    compressed = fit_bo_surrogate(
        x,
        y,
        policy,
        options,
        deadline=time.perf_counter() + 30,
        optimize=False,
        group_member_indices=members,
    )
    q = np.array([[0.1], [0.7], [0.9]])
    raw_prediction, compressed_prediction = (
        raw.predict(q, joint=True),
        compressed.predict(q, joint=True),
    )
    np.testing.assert_allclose(
        raw_prediction.mean_scaled, compressed_prediction.mean_scaled, atol=2e-10
    )
    np.testing.assert_allclose(
        raw_prediction.latent_covariance_scaled,
        compressed_prediction.latent_covariance_scaled,
        atol=2e-12,
    )
    assert raw.log_marginal_likelihood == pytest.approx(
        compressed.log_marginal_likelihood, rel=2e-10, abs=2e-9
    )
    assert raw.normalization_mean == compressed.normalization_mean
    assert raw.normalization_scale == compressed.normalization_scale
    assert compressed.metadata()["raw_observation_count"] == 6
    assert compressed.metadata()["effective_training_count"] == 3
    np.testing.assert_allclose(
        raw_prediction.predictive_variance_scaled,
        compressed_prediction.predictive_variance_scaled,
        atol=2e-12,
    )


def test_compressed_likelihood_gradient_includes_within_group_noise_correction():
    x = np.array([[0.0], [0.0], [0.0], [0.4], [0.9], [0.9]])
    y = np.array([0.1, 0.4, -0.2, 0.8, 1.2, 1.2])
    groups = ([0, 1, 2], [3], [4, 5])
    counts = np.array([3, 1, 2])
    means = np.array([y[group].mean() for group in groups])
    within = np.array([np.sum((y[group] - means[i]) ** 2) for i, group in enumerate(groups)])
    unique = x[[0, 3, 4]]
    kernel = _kernel(1, BoSurrogatePolicy(), 1)
    raw = _likelihood(kernel.theta, kernel, x, y, 1e-8)
    compressed = _likelihood(kernel.theta, kernel, unique, means, 1e-8, counts, within)
    np.testing.assert_allclose(raw[0], compressed[0], atol=1e-10)
    np.testing.assert_allclose(raw[1], compressed[1], atol=1e-10)
    step = 1e-5
    differences = []
    for i in range(len(kernel.theta)):
        delta = np.zeros(len(kernel.theta))
        delta[i] = step
        upper = _likelihood(kernel.theta + delta, kernel, unique, means, 1e-8, counts, within)[0]
        lower = _likelihood(kernel.theta - delta, kernel, unique, means, 1e-8, counts, within)[0]
        differences.append((upper - lower) / (2 * step))
    np.testing.assert_allclose(compressed[1], differences, atol=2e-7, rtol=2e-6)


def test_nonidentical_or_incomplete_compression_groups_are_rejected():
    for members in (((0, 1), (2,)), ((0,), (1,)), ((0,), (1,), (1, 2))):
        with pytest.raises(BayesianOptimizationError, match="observation_group_invalid"):
            fit_bo_surrogate(
                [[0], [0.4], [1]],
                [0, 1, 0.1],
                BoSurrogatePolicy(),
                search_options(),
                deadline=time.perf_counter() + 30,
                optimize=False,
                group_member_indices=members,
            )
