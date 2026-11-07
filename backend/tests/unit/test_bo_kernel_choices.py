from __future__ import annotations

import math
import time

import numpy as np
import pytest

from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_surrogate import BoSurrogatePolicy, _kernel, _likelihood, fit_bo_surrogate

KINDS = ("matern_5_2", "matern_3_2", "gaussian", "exponential")
X = np.array([[0, 0.1], [0.2, 0.8], [0.2, 0.8], [0.7, 0.3], [1, 1]], dtype=float)
Y = np.array([1, 1.4, 1.8, -0.1, 0.7])
Q = np.array([[0.3, 0.4], [0.8, 0.9]])
SEARCH = dict(
    random_seed=123,
    jitter=1e-6,
    hyperparameter_restart_count=0,
    model_max_iterations=80,
    model_max_evaluations=300,
)


def independent_covariance(x, z, kind, lengths=None, amplitude=1):
    lengths = np.ones(x.shape[1]) if lengths is None else lengths
    r = np.linalg.norm((x[:, None] - z[None, :]) / lengths, axis=2)
    if kind == "gaussian":
        correlation = np.exp(-0.5 * r**2)
    elif kind == "exponential":
        correlation = np.exp(-r)
    elif kind == "matern_3_2":
        u = math.sqrt(3) * r
        correlation = (1 + u) * np.exp(-u)
    else:
        u = math.sqrt(5) * r
        correlation = (1 + u + u**2 / 3) * np.exp(-u)
    return amplitude * correlation


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("mode", ["estimate", "fixed", "near_noiseless"])
def test_selected_kernel_matches_independent_cholesky(kind, mode):
    policy = BoSurrogatePolicy(noise_mode=mode, fixed_noise_sd=0.13 if mode == "fixed" else None)
    model = fit_bo_surrogate(
        X,
        Y,
        policy,
        SEARCH,
        deadline=time.perf_counter() + 30,
        optimize=False,
        kernel_spec=BoKernelSpec(kind),
    )
    scale = np.std(Y)
    noise = {"estimate": 0.01, "fixed": (0.13 / scale) ** 2, "near_noiseless": 0}[mode]
    k = independent_covariance(X, X, kind) + np.eye(len(X)) * (noise + SEARCH["jitter"])
    lower = np.linalg.cholesky(k)
    cross = independent_covariance(X, Q, kind)
    solved = np.linalg.solve(lower, cross)
    mean = cross.T @ np.linalg.solve(lower.T, np.linalg.solve(lower, (Y - Y.mean()) / scale))
    covariance = independent_covariance(Q, Q, kind) - solved.T @ solved
    prediction = model.predict(Q, joint=True)
    np.testing.assert_allclose(prediction.mean_scaled, mean, atol=2e-10, rtol=2e-9)
    np.testing.assert_allclose(prediction.latent_covariance_scaled, covariance, atol=2e-10)
    np.testing.assert_allclose(
        prediction.predictive_variance_scaled - prediction.latent_variance_scaled, noise, atol=2e-15
    )
    assert model.metadata()["schema_version"] == 4
    assert model.metadata()["signal_kernel"]["family"] == kind
    assert model.metadata()["signal_kernel"]["coordinate_system"] == "factor_bounds_normalized_0_1"


@pytest.mark.parametrize("kind", KINDS)
def test_kernel_and_likelihood_gradients_and_compression(kind):
    kernel = _kernel(2, BoSurrogatePolicy(), 1, kernel_spec=BoKernelSpec(kind))
    theta = kernel.theta + np.array([0.2, -0.6, 0.4, -0.3])
    current = kernel.clone_with_theta(theta)
    value, derivative, _, _ = _likelihood(theta, kernel, X, Y, 1e-6)
    expected = independent_covariance(X, X, kind, np.exp(theta[1:3]), np.exp(theta[0]))
    np.testing.assert_allclose(
        current(X), expected + np.eye(len(X)) * np.exp(theta[-1]), atol=2e-15
    )
    step = 1e-5
    for i in range(len(theta)):
        delta = np.eye(len(theta))[i] * step
        numeric = (
            _likelihood(theta + delta, kernel, X, Y, 1e-6)[0]
            - _likelihood(theta - delta, kernel, X, Y, 1e-6)[0]
        ) / (2 * step)
        assert derivative[i] == pytest.approx(numeric, abs=2e-7, rel=2e-6)
    unique = X[[0, 1, 3, 4]]
    means = np.array([Y[0], Y[1:3].mean(), Y[3], Y[4]])
    counts = np.array([1, 2, 1, 1])
    ss = np.array([0, np.sum((Y[1:3] - means[1]) ** 2), 0, 0])
    compressed = _likelihood(theta, kernel, unique, means, 1e-6, counts, ss)
    assert compressed[0] == pytest.approx(value, abs=2e-10)
    np.testing.assert_allclose(compressed[1], derivative, atol=2e-9)
    raw = fit_bo_surrogate(
        X,
        Y,
        BoSurrogatePolicy(),
        SEARCH,
        deadline=time.perf_counter() + 30,
        optimize=False,
        kernel_spec=BoKernelSpec(kind),
    )
    compact = fit_bo_surrogate(
        X,
        Y,
        BoSurrogatePolicy(),
        SEARCH,
        deadline=time.perf_counter() + 30,
        optimize=False,
        kernel_spec=BoKernelSpec(kind),
        group_member_indices=((0,), (1, 2), (3,), (4,)),
    )
    np.testing.assert_allclose(
        raw.predict(Q, joint=True).latent_covariance_scaled,
        compact.predict(Q, joint=True).latent_covariance_scaled,
        atol=2e-12,
    )
    np.testing.assert_allclose(
        raw.predict(Q).mean_scaled, compact.predict(Q).mean_scaled, atol=2e-12
    )


def test_explicit_default_keeps_legacy_numeric_results_and_metadata_separate():
    legacy = fit_bo_surrogate(X, Y, BoSurrogatePolicy(), SEARCH, deadline=time.perf_counter() + 30)
    modern = fit_bo_surrogate(
        X,
        Y,
        BoSurrogatePolicy(),
        SEARCH,
        deadline=time.perf_counter() + 30,
        kernel_spec=BoKernelSpec(),
    )
    np.testing.assert_array_equal(legacy.predict(Q).mean_scaled, modern.predict(Q).mean_scaled)
    np.testing.assert_array_equal(
        legacy.predict(Q).latent_variance_scaled, modern.predict(Q).latent_variance_scaled
    )
    assert legacy.metadata()["schema_version"] == 3
    assert "family" not in legacy.metadata()["signal_kernel"]
    assert modern.metadata()["schema_version"] == 4


@pytest.mark.parametrize("kind", ["cubic", "power_exponential", "", None, 1])
def test_unknown_kernel_is_not_silently_replaced(kind):
    with pytest.raises(ValueError, match="kernel_invalid"):
        BoKernelSpec(kind)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("goal", ["maximize", "minimize", "match_target"])
def test_each_family_preserves_q1_first_batch_identity_and_seed(kind, goal):
    from test_bo_recommendation_core import payload

    from app.statistics.bo_recommendation_core import calculate_noise_aware_batch

    request = payload(goal, 1)
    request.update(schema_version=3, kernel={"kind": kind})
    single = calculate_noise_aware_batch(request)
    request["batch_size"] = 2
    batch = calculate_noise_aware_batch(request)
    replay = calculate_noise_aware_batch(request)
    assert batch["items"] == replay["items"]
    assert single["items"][0] == batch["items"][0]
    assert batch["shared_model"]["signal_kernel"]["family"] == kind
    assert batch["items"][1]["planning"]["effective_sample_count"] == 64


@pytest.mark.parametrize("kind", KINDS)
def test_hand_check_scaled_distance_and_not_separable_matern(kind):
    from app.statistics.bo_kernels import signal_kernel

    signal = signal_kernel(2, BoKernelSpec(kind))
    signal.k2.length_scale = np.array([1.0, 2.0])
    points = np.array([[0.0, 0.0], [1.0, 2.0]])
    actual = signal(points)
    np.testing.assert_allclose(
        actual, independent_covariance(points, points, kind, [1, 2]), atol=2e-15
    )
    np.testing.assert_array_equal(np.diag(actual), [1, 1])
    assert np.linalg.eigvalsh(actual).min() > 0
    if kind == "exponential":
        assert actual[0, 1] == pytest.approx(math.exp(-math.sqrt(2)), abs=1e-15)
        assert abs(actual[0, 1] - math.exp(-2)) > 0.1
