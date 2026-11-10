from __future__ import annotations

import copy
import math
import time

import numpy as np
import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_factor_domains import BoCategoricalFactorDomain, BoNumericFactorDomain
from app.statistics.bo_factor_kernels import bo_factor_kernel_to_payload, build_bo_factor_kernel
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_mixed_surrogate import (
    fit_bo_mixed_surrogate,
    mixed_likelihood,
    mixed_parameter_descriptors,
    split_mixed_signal_noise,
    validate_mixed_coordinates,
)
from app.statistics.bo_surrogate import BoSurrogatePolicy
from app.statistics.doe_factor_domain import DoeFactorDomain

EQUAL = "equal_positive_correlation_v1"
UNEQUAL = "unequal_hyperspherical_correlation_v1"
LATENT = "ordinal_monotone_latent_rbf_v1"


def factors(policy=EQUAL, levels=("a", "b", "c")):
    return (
        BoNumericFactorDomain("x", DoeFactorDomain(10.0, 20.0)),
        BoCategoricalFactorDomain(
            "c", "ordinal" if policy == LATENT else "nominal", levels, policy
        ),
    )


def search(**changes):
    return {
        "jitter": 1e-6,
        "random_seed": 31,
        "hyperparameter_restart_count": 0,
        "model_max_iterations": 20,
        "model_max_evaluations": 200,
        **changes,
    }


def fitted(x=None, y=None, domains=None, policy=None, **options):
    return fit_bo_mixed_surrogate(
        np.array([[0.0, 0], [0.2, 1], [0.7, 2], [1.0, 0]]) if x is None else x,
        np.array([-1.0, 0.2, 0.1, 0.7]) if y is None else y,
        factors() if domains is None else domains,
        policy or BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.4),
        options.pop("search", search()),
        deadline=options.pop("deadline", time.perf_counter() + 60),
        normalization_mean=options.pop("normalization_mean", 3.0),
        normalization_scale=options.pop("normalization_scale", 2.0),
        optimize=options.pop("optimize", False),
        **options,
    )


def independent_signal(left, right, kind="gaussian", category_policy=EQUAL):
    distance = np.abs(left[:, None, 0] - right[None, :, 0])
    if kind == "gaussian":
        numeric = np.exp(-0.5 * distance**2)
    elif kind == "exponential":
        numeric = np.exp(-distance)
    elif kind == "matern_3_2":
        r = math.sqrt(3) * distance
        numeric = (1 + r) * np.exp(-r)
    else:
        r = math.sqrt(5) * distance
        numeric = (1 + r + r**2 / 3) * np.exp(-r)
    a, b = left[:, 1].astype(int), right[:, 1].astype(int)
    if category_policy == EQUAL:
        categorical = np.exp(-(a[:, None] != b[None, :]).astype(float))
    elif category_policy == LATENT:
        positions = np.array([0.0, 0.5, 1.0])
        categorical = np.exp(-0.5 * (positions[a, None] - positions[None, b]) ** 2)
    else:
        angle = math.pi / 2
        vectors = np.array(
            [
                [1, 0, 0],
                [math.cos(angle), math.sin(angle), 0],
                [math.cos(angle), math.sin(angle) * math.cos(angle), math.sin(angle) ** 2],
            ]
        )
        categorical = (vectors @ vectors.T)[a[:, None], b[None, :]]
    return numeric * categorical


@pytest.mark.parametrize("kind", ["matern_5_2", "matern_3_2", "gaussian", "exponential"])
@pytest.mark.parametrize("category_policy", [EQUAL, UNEQUAL, LATENT])
@pytest.mark.parametrize(
    "noise_policy,noise",
    [
        (BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.4), 0.04),
        (BoSurrogatePolicy(), 0.01),
        (BoSurrogatePolicy(noise_mode="near_noiseless"), 0.0),
    ],
)
def test_fixed_hyperparameters_against_independent_dense_cholesky(
    kind, category_policy, noise_policy, noise
):
    model = fitted(
        domains=factors(category_policy), policy=noise_policy, kernel_spec=BoKernelSpec(kind)
    )
    query = np.array([[0.1, 0], [0.6, 2], [0.9, 1]])
    covariance = independent_signal(model.x_train, model.x_train, kind, category_policy) + np.eye(
        4
    ) * (noise + model.jitter)
    lower = np.linalg.cholesky(covariance)
    alpha = np.linalg.solve(covariance, model.training_targets_scaled)
    cross = independent_signal(model.x_train, query, kind, category_policy)
    reference = independent_signal(query, query, kind, category_policy) - cross.T @ np.linalg.solve(
        covariance, cross
    )
    expected_mean = cross.T @ alpha
    expected_lml = (
        -0.5 * model.training_targets_scaled @ alpha
        - np.log(np.diag(lower)).sum()
        - 2 * math.log(2 * math.pi)
    )
    posterior = model.predict(query, joint=True)
    # Dense independent solve and triangular solve differ at cancellation scale.
    np.testing.assert_allclose(posterior.mean_scaled, expected_mean, rtol=2e-11, atol=2e-13)
    np.testing.assert_allclose(
        posterior.latent_covariance_scaled, reference, rtol=2e-11, atol=2e-13
    )
    np.testing.assert_allclose(
        posterior.predictive_variance_scaled - posterior.latent_variance_scaled,
        noise,
        rtol=0,
        atol=2e-16,
    )
    assert model.log_marginal_likelihood == pytest.approx(expected_lml, rel=2e-12, abs=2e-12)
    np.testing.assert_allclose(
        model.latent_cross_covariance(query[:2], query[2:]),
        reference[:2, 2:],
        rtol=2e-11,
        atol=2e-13,
    )
    assert model.metadata()["schema_version"] == 6
    assert model.metadata()["normalization"]["ddof"] == 0


def test_exact_repeats_keep_raw_normalization_likelihood_and_noise_gradient():
    unique = np.array([[0.0, 0], [0.5, 1], [1.0, 2]])
    counts = (3, 1, 2)
    raw_x = np.repeat(unique, counts, axis=0)
    raw_y = np.array([1.0, 1.2, 0.7, 2.0, 4.0, 4.4])
    center, scale = float(raw_y.mean()), float(raw_y.std(ddof=0))
    raw_scaled = (raw_y - center) / scale
    groups = (raw_scaled[:3], raw_scaled[3:4], raw_scaled[4:])
    means = np.array([row.mean() for row in groups])
    within = np.array([np.sum((row - row.mean()) ** 2) for row in groups])
    options = {
        "policy": BoSurrogatePolicy(),
        "kernel_spec": BoKernelSpec("gaussian"),
        "normalization_mean": center,
        "normalization_scale": scale,
    }
    raw = fitted(x=raw_x, y=raw_scaled, **options)
    compressed = fitted(
        x=unique,
        y=means,
        group_counts=counts,
        within_ss_scaled=within,
        raw_observation_count=6,
        **options,
    )
    query = np.array([[0.3, 1], [0.8, 2]])
    np.testing.assert_allclose(
        raw.predict(query, joint=True).latent_covariance_scaled,
        compressed.predict(query, joint=True).latent_covariance_scaled,
        rtol=2e-12,
        atol=2e-14,
    )
    np.testing.assert_allclose(
        raw.predict(query).mean_scaled,
        compressed.predict(query).mean_scaled,
        rtol=2e-12,
        atol=2e-14,
    )
    assert raw.log_marginal_likelihood == pytest.approx(
        compressed.log_marginal_likelihood, rel=2e-12, abs=2e-12
    )
    left = mixed_likelihood(
        raw.kernel.theta, raw.kernel, raw_x, raw_scaled, raw.jitter, (1,) * 6, np.zeros(6)
    )
    right = mixed_likelihood(
        compressed.kernel.theta, compressed.kernel, unique, means, raw.jitter, counts, within
    )
    np.testing.assert_allclose(left[1], right[1], rtol=2e-11, atol=2e-11)
    # Finite differences of the independently assembled raw Gaussian likelihood.
    theta = compressed.kernel.theta

    def independent_lml(point):
        amplitude, length, mismatch, noise = np.exp(point)
        distance = (raw_x[:, None, 0] - raw_x[None, :, 0]) / length
        matrix = amplitude * np.exp(
            -0.5 * distance**2 - mismatch * (raw_x[:, None, 1] != raw_x[None, :, 1])
        )
        matrix += np.eye(6) * (noise + raw.jitter)
        root = np.linalg.cholesky(matrix)
        return (
            -0.5 * raw_scaled @ np.linalg.solve(matrix, raw_scaled)
            - np.log(np.diag(root)).sum()
            - 3 * math.log(2 * math.pi)
        )

    delta = 1e-5
    numeric = np.array(
        [
            (
                independent_lml(theta + np.eye(len(theta))[i] * delta)
                - independent_lml(theta - np.eye(len(theta))[i] * delta)
            )
            / (2 * delta)
            for i in range(len(theta))
        ]
    )
    np.testing.assert_allclose(right[1], numeric, rtol=2e-7, atol=2e-8)
    np.testing.assert_allclose(
        compressed.predict(query).predictive_variance_scaled
        - compressed.predict(query).latent_variance_scaled,
        0.01,
        rtol=0,
        atol=1e-16,
    )
    assert compressed.metadata()["raw_observation_count"] == 6
    assert compressed.metadata()["effective_training_count"] == 3


def test_label_rename_and_equality_code_permutation_leave_posterior_unchanged():
    original = fitted(kernel_spec=BoKernelSpec("gaussian"))
    renamed = fitted(
        domains=factors(levels=("한글", "001", " long full identity ")),
        kernel_spec=BoKernelSpec("gaussian"),
    )
    x = original.x_train.copy()
    x[:, 1] = np.array([2, 0, 1])[x[:, 1].astype(int)]
    permuted = fitted(x=x, kernel_spec=BoKernelSpec("gaussian"))
    query = np.array([[0.1, 0], [0.5, 1], [0.9, 2]])
    alternate = query.copy()
    alternate[:, 1] = np.array([2, 0, 1])[alternate[:, 1].astype(int)]
    np.testing.assert_array_equal(
        original.predict(query).mean_scaled, renamed.predict(query).mean_scaled
    )
    np.testing.assert_array_equal(
        original.predict(query).mean_scaled, permuted.predict(alternate).mean_scaled
    )


def test_descriptors_and_coverage_do_not_mislabel_category_parameters_as_lengths():
    model = fitted(domains=factors(UNEQUAL), x=np.array([[0.0, 0], [1.0, 0]]), y=np.array([-1, 1]))
    descriptors = mixed_parameter_descriptors(model.kernel, model.factor_domains)
    assert [item.role for item in descriptors] == [
        "signal_amplitude",
        "numeric_length_scale",
        *(["category_hyperspherical_angle"] * 3),
    ]
    assert [item.level_indices for item in descriptors[2:]] == [(1, 0), (2, 0), (2, 1)]
    assert "bayesian_category_unobserved_level_prior_dependent" in model.warning_codes
    assert "bayesian_category_correlation_unidentified" in model.warning_codes
    assert model.metadata()["training_level_coverage"][0]["unobserved_level_indices"] == [1, 2]
    assert np.isfinite(model.predict([[0.5, 2]]).mean_scaled).all()


def test_all_categorical_model_and_model_state_inputs_remain_unchanged():
    domains = factors()[1:]
    x, y = np.array([[0], [1], [2]]), np.array([-1.0, 0, 1.0])
    before = x.copy(), y.copy()
    model = fitted(x=x, y=y, domains=domains)
    assert [item.role for item in mixed_parameter_descriptors(model.kernel, domains)] == [
        "signal_amplitude",
        "category_mismatch",
    ]
    assert model.predict([[0], [2]], joint=True).latent_covariance_scaled.shape == (2, 2)
    np.testing.assert_array_equal(x, before[0])
    np.testing.assert_array_equal(y, before[1])


@pytest.mark.parametrize(
    "points",
    [
        [[0.5, 0.5]],
        [[0.5, 3]],
        [[1.1, 0]],
        [[True, 0]],
        [["0.5", 0]],
        [[0.5, float("nan")]],
        np.array([[0.5, 0]], dtype=object),
    ],
)
def test_invalid_encoded_coordinates_are_not_coerced(points):
    with pytest.raises((ValueError, BayesianOptimizationError)):
        validate_mixed_coordinates(points, factors())


@pytest.mark.parametrize(
    "changes",
    [
        {"group_counts": (1, 1, 1, 2)},
        {"group_counts": (1, 1, 1, 1), "within_ss_scaled": [0, 0, 0, 1]},
        {"raw_observation_count": 5},
        {"normalization_scale": 0},
        {"search": search(model_max_evaluations=1)},
        {"search": search(random_seed=True)},
    ],
)
def test_invalid_fit_contract_is_rejected(changes):
    with pytest.raises((ValueError, BayesianOptimizationError)):
        fitted(**changes)


def test_time_and_evaluation_budgets_are_explicit():
    with pytest.raises(BayesianOptimizationError, match="time_budget_exhausted"):
        fitted(deadline=time.perf_counter() - 1)
    with pytest.raises(BayesianOptimizationError, match="budget_exhausted"):
        fitted(optimize=True, fit_policy=BoFitPolicy(), search=search(model_max_evaluations=2))


def test_bounded_fit_receipt_reproducibility_and_restore_initial_payload_immutability():
    signal = build_bo_factor_kernel(factors(), BoKernelSpec("gaussian"))
    payload = bo_factor_kernel_to_payload(signal)
    before = copy.deepcopy(payload)
    options = {
        "optimize": True,
        "kernel_spec": BoKernelSpec("gaussian"),
        "fit_policy": BoFitPolicy(1),
        "initial_signal_payload": payload,
        "search": search(model_max_iterations=4),
    }
    left, right = fitted(**options), fitted(**options)
    np.testing.assert_array_equal(left.kernel.theta, right.kernel.theta)
    assert payload == before
    assert left.fit_diagnostics == right.fit_diagnostics
    assert left.optimizer["evaluations"] <= 200
    assert left.fit_diagnostics["policy"] == "bounded_typed_factor_starts_v1"
    assert left.fit_diagnostics["global_optimum_guaranteed"] is False
    assert left.optimizer["evaluations"] == 1 + len(left.fit_diagnostics["screening"]) + sum(
        item["evaluations"] for item in left.optimizer["starts"]
    )
    assert split_mixed_signal_noise(left.kernel)[1] == pytest.approx(0.04)
