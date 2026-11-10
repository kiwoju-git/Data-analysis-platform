from __future__ import annotations

import copy
import json
import math

import numpy as np
import pytest
from sklearn.base import clone
from sklearn.gaussian_process.kernels import ConstantKernel, WhiteKernel

from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoNumericFactorDomain,
    encode_bo_point,
)
from app.statistics.bo_factor_kernels import (
    BoCategoryKernelSpec,
    BoFactorKernel,
    bo_factor_kernel_from_payload,
    bo_factor_kernel_to_payload,
    build_bo_factor_kernel,
    hyperspherical_parameters_from_correlation,
    validate_bo_factor_kernel_domains,
)
from app.statistics.bo_kernels import BoKernelSpec, signal_kernel
from app.statistics.doe_factor_domain import DoeFactorDomain

EQUAL = "equal_positive_correlation_v1"
UNEQUAL = "unequal_hyperspherical_correlation_v1"
LATENT = "ordinal_monotone_latent_rbf_v1"
KINDS = ("matern_5_2", "matern_3_2", "gaussian", "exponential")
POLICIES = (EQUAL, UNEQUAL, LATENT)


def _factors(policy=EQUAL):
    return (
        BoNumericFactorDomain("x", DoeFactorDomain(0.0, 1.0)),
        BoCategoricalFactorDomain(
            "category", "ordinal" if policy == LATENT else "nominal", ("a", "b", "c"), policy
        ),
    )


def _kernel(policy=EQUAL, kind="gaussian"):
    kernel = build_bo_factor_kernel(_factors(policy), BoKernelSpec(kind))
    if policy == UNEQUAL:
        kernel.category_parameters = [0.7, 1.1, 1.9]
    if policy == LATENT:
        kernel.category_parameters = [0.2, 1.3]
    return kernel


@pytest.mark.parametrize("kind", KINDS)
def test_numeric_only_path_is_existing_kernel_unchanged(kind):
    factors = (
        BoNumericFactorDomain("x", DoeFactorDomain(0.0, 1.0)),
        BoNumericFactorDomain("z", DoeFactorDomain(0.0, 1.0)),
    )
    kernel = build_bo_factor_kernel(factors, BoKernelSpec(kind))
    expected = signal_kernel(2, BoKernelSpec(kind))
    points = np.array([[0.1, 0.3], [0.4, 0.8], [1.0, 0.5]])
    assert type(kernel) is type(expected)
    np.testing.assert_array_equal(kernel.theta, expected.theta)
    np.testing.assert_array_equal(kernel.bounds, expected.bounds)
    actual, gradient = kernel(points, eval_gradient=True)
    truth, truth_gradient = expected(points, eval_gradient=True)
    np.testing.assert_array_equal(actual, truth)
    np.testing.assert_array_equal(gradient, truth_gradient)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("policy", POLICIES)
def test_mixed_psd_and_analytic_log_gradient_against_central_difference(kind, policy):
    kernel = _kernel(policy, kind)
    points = np.array([[0.0, 0], [0.2, 1], [0.5, 2], [0.7, 0], [1.0, 2]])
    covariance, gradient = kernel(points, eval_gradient=True)
    assert np.linalg.eigvalsh(covariance).min() >= -1e-12
    np.testing.assert_allclose(kernel.diag(points), np.diag(covariance), rtol=0, atol=1e-14)
    theta = kernel.theta.copy()
    epsilon = 1e-6
    for index in range(len(theta)):
        delta = np.zeros_like(theta)
        delta[index] = epsilon
        plus, minus = clone(kernel), clone(kernel)
        plus.theta = theta + delta
        minus.theta = theta - delta
        numerical = (plus(points) - minus(points)) / (2 * epsilon)
        np.testing.assert_allclose(gradient[:, :, index], numerical, rtol=2e-6, atol=2e-9)


def test_equal_correlation_uses_mismatch_not_code_distance():
    kernel = _kernel()
    points = np.array([[0.2, 0], [0.2, 1], [0.2, 2]])
    expected = np.full((3, 3), math.exp(-1))
    np.fill_diagonal(expected, 1)
    np.testing.assert_allclose(kernel(points), expected, rtol=0, atol=1e-15)
    np.testing.assert_array_equal(kernel(points), kernel(points[[2, 0, 1]]))


def test_hyperspherical_matrix_matches_independent_unit_vectors_and_negative_correlations():
    angles = [0.7, 1.1, 1.9]
    vectors = np.array(
        [
            [1, 0, 0],
            [math.cos(angles[0]), math.sin(angles[0]), 0],
            [
                math.cos(angles[1]),
                math.sin(angles[1]) * math.cos(angles[2]),
                math.sin(angles[1]) * math.sin(angles[2]),
            ],
        ]
    )
    kernel = _kernel(UNEQUAL)
    np.testing.assert_allclose(
        kernel.category_correlation_matrices()[0], vectors @ vectors.T, rtol=0, atol=2e-15
    )
    kernel.category_parameters = [2.0, 1.1, 1.9]
    assert kernel.category_correlation_matrices()[0][0, 1] < 0
    assert np.linalg.eigvalsh(kernel.category_correlation_matrices()[0]).min() > 0


def test_unequal_code_permutation_with_equivalent_level_matrix_preserves_covariance():
    kernel = _kernel(UNEQUAL)
    matrix = kernel.category_correlation_matrices()[0]
    permutation = np.array([2, 0, 1])
    inverse = np.argsort(permutation)
    permuted = clone(kernel)
    permuted.category_parameters = hyperspherical_parameters_from_correlation(
        matrix[np.ix_(permutation, permutation)]
    )
    points = np.array([[0.1, 0], [0.3, 1], [0.4, 2], [0.8, 1]])
    permuted_points = points.copy()
    permuted_points[:, 1] = inverse[points[:, 1].astype(int)]
    np.testing.assert_allclose(kernel(points), permuted(permuted_points), rtol=2e-14, atol=2e-14)


@pytest.mark.parametrize("policy", POLICIES)
def test_category_label_bijection_has_no_numeric_effect(policy):
    original = _factors(policy)
    category = original[1]
    renamed = (
        original[0],
        BoCategoricalFactorDomain(
            "category", category.kind, ("10", " 2 ", "X" * 150), category.correlation_policy
        ),
    )
    original_points = [
        encode_bo_point(original, {"x": x, "category": label})
        for x, label in zip((0.1, 0.4, 0.7), category.levels, strict=True)
    ]
    renamed_points = [
        encode_bo_point(renamed, {"x": x, "category": label})
        for x, label in zip((0.1, 0.4, 0.7), renamed[1].levels, strict=True)
    ]
    np.testing.assert_array_equal(
        build_bo_factor_kernel(original, BoKernelSpec())(original_points),
        build_bo_factor_kernel(renamed, BoKernelSpec())(renamed_points),
    )


def test_ordinal_latent_uses_learned_gaps_not_fixed_rank_distance():
    kernel = _kernel(LATENT)
    positions = np.array([0, 0.2, 1.5])
    expected = np.exp(-0.5 * (positions[:, None] - positions[None, :]) ** 2)
    actual = kernel.category_correlation_matrices()[0]
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-15)
    assert actual[0, 1] != actual[1, 2]
    assert actual[0, 1] > actual[0, 2]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("policy", POLICIES)
def test_strict_json_round_trip_preserves_covariance_gradient_and_source(policy, kind):
    kernel = _kernel(policy, kind)
    payload = bo_factor_kernel_to_payload(kernel)
    original = copy.deepcopy(payload)
    restored = bo_factor_kernel_from_payload(json.loads(json.dumps(payload, allow_nan=False)))
    points = np.array([[0.1, 0], [0.3, 1], [0.8, 2]])
    np.testing.assert_array_equal(restored.theta, kernel.theta)
    np.testing.assert_array_equal(restored.bounds, kernel.bounds)
    np.testing.assert_allclose(restored(points), kernel(points), rtol=0, atol=1e-15)
    np.testing.assert_allclose(
        restored(points, eval_gradient=True)[1],
        kernel(points, eval_gradient=True)[1],
        rtol=0,
        atol=1e-15,
    )
    validate_bo_factor_kernel_domains(restored, _factors(policy))
    assert payload == original
    payload["parameters"][0] = 999
    np.testing.assert_allclose(restored(points), kernel(points), rtol=0, atol=1e-15)


def test_multiple_categories_and_all_categorical_zero_correlation_gradient():
    factors = (
        BoCategoricalFactorDomain("a", "nominal", ("a", "b"), UNEQUAL),
        BoCategoricalFactorDomain("b", "ordinal", ("low", "medium", "high"), LATENT),
    )
    kernel = build_bo_factor_kernel(factors, BoKernelSpec("exponential"))
    points = np.array([[0, 0], [1, 1], [0, 2], [1, 0]])
    covariance, gradient = kernel(points, eval_gradient=True)
    assert np.all(np.isfinite(gradient))
    assert np.linalg.eigvalsh(covariance).min() > 0
    restored = bo_factor_kernel_from_payload(bo_factor_kernel_to_payload(kernel))
    np.testing.assert_allclose(restored(points), covariance, rtol=0, atol=1e-15)


def test_noise_and_jitter_are_not_inside_signal_payload():
    kernel = _kernel()
    points = np.array([[0.1, 0], [0.1, 0]])
    signal = kernel(points)
    observed = (kernel + WhiteKernel(0.2, "fixed"))(points)
    np.testing.assert_allclose(observed - signal, np.eye(2) * 0.2, rtol=0, atol=1e-15)
    assert signal[0, 1] == 1
    assert "noise" not in json.dumps(bo_factor_kernel_to_payload(kernel))


@pytest.mark.parametrize(
    "points",
    [
        [[0.2, 0.5]],
        [[0.2, 3]],
        [[0.2, -1]],
        [[0.2, "a"]],
        [[0.2, True]],
        [[float("nan"), 0]],
        [[1.1, 0]],
        [[-0.1, 0]],
        [[0.2]],
        np.array([[0.2, 0]], dtype=object),
    ],
)
def test_invalid_encoded_points_rejected(points):
    with pytest.raises(ValueError):
        _kernel()(points)


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value.update(schema_version=True),
        lambda value: value.update(unknown=1),
        lambda value: value["categories"][0].update(policy="jmp_equal"),
        lambda value: value["categories"][0].update(level_count=1),
        lambda value: value["categories"][0].update(index=0),
        lambda value: value["parameters"].__setitem__(0, True),
        lambda value: value["parameters"].__setitem__(0, float("nan")),
        lambda value: value["parameters"].__setitem__(0, -1),
        lambda value: value.update(parameter_bounds=[[1e-8, 1e8]]),
        lambda value: value["numeric_signal"].update(kind="arbitrary_python_object"),
    ],
)
def test_payload_rejects_unknown_and_invalid_state(change):
    payload = bo_factor_kernel_to_payload(_kernel())
    change(payload)
    with pytest.raises(ValueError):
        bo_factor_kernel_from_payload(payload)


def test_parameter_bounds_and_domain_binding_rejected_without_state_mutation():
    kernel = _kernel(LATENT)
    original = kernel.theta.copy()
    invalid = original.copy()
    invalid[-1] = math.log(11)
    with pytest.raises(ValueError):
        kernel.theta = invalid
    np.testing.assert_array_equal(kernel.theta, original)
    with pytest.raises(ValueError, match="domain_mismatch"):
        validate_bo_factor_kernel_domains(kernel, _factors(EQUAL))


def test_log_parameter_bound_roundoff_remains_valid_after_restore():
    kernel = _kernel()
    kernel.theta = kernel.bounds[:, 1]
    restored = bo_factor_kernel_from_payload(bo_factor_kernel_to_payload(kernel))
    np.testing.assert_array_equal(restored.theta, kernel.theta)
    assert np.all(np.isfinite(restored([[0.2, 0], [0.8, 2]])))


def test_one_observed_declared_level_has_no_identifiable_category_gradient():
    kernel = _kernel(UNEQUAL)
    points = np.array([[0.1, 1], [0.4, 1], [0.8, 1]])
    covariance, gradient = kernel(points, eval_gradient=True)
    numeric = kernel.numeric_kernel(points[:, [0]])
    np.testing.assert_allclose(covariance, numeric, rtol=0, atol=1e-14)
    np.testing.assert_allclose(gradient[:, :, -3:], 0.0, rtol=0, atol=1e-14)


def test_covariance_to_angles_rejects_non_spd_or_non_correlation():
    for value in ([[1, 2], [2, 1]], [[1, 1], [1, 1]], [[2, 0], [0, 1]], [[1, 0], [0.5, 1]]):
        with pytest.raises(ValueError):
            hyperspherical_parameters_from_correlation(value)


def test_fixed_category_kernel_round_trip_and_no_gradient_parameters():
    kernel = BoFactorKernel(
        ConstantKernel(2.0, "fixed"),
        (),
        (BoCategoryKernelSpec(0, "nominal", 2, EQUAL),),
        [1.0],
        "fixed",
    )
    restored = bo_factor_kernel_from_payload(bo_factor_kernel_to_payload(kernel))
    points = np.array([[0], [1]])
    assert restored.n_dims == 0
    assert restored(points, eval_gradient=True)[1].shape == (2, 2, 0)
    np.testing.assert_array_equal(restored(points), kernel(points))
