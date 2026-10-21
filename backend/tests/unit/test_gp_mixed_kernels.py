from __future__ import annotations

import json

import numpy as np
import pytest
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, Matern, RationalQuadratic

from app.statistics.gp_mixed_kernels import (
    MixedPredictorKernel,
    mixed_kernel_from_payload,
    mixed_kernel_to_payload,
    mixed_kernel_warning_codes,
)


def kernel(base=None, *, theta=(0.7, 1.2)):
    return MixedPredictorKernel(
        ConstantKernel(1.3, (1e-3, 1e3)) * (Matern(0.8, nu=2.5) if base is None else base),
        (0,),
        (1, 2),
        categorical_theta=theta,
    )


def points():
    return np.array([[0, 0, 0], [0.5, 1, 0], [1, 0, 1], [0.8, 1, 1]], dtype=float)


@pytest.mark.parametrize(
    "base", [Matern(0.8, nu=2.5), Matern(0.8, nu=1.5), RBF(0.8), RationalQuadratic(0.8, 1.2)]
)
def test_covariance_is_psd_and_log_gradient_matches_finite_difference(base):
    model = kernel(base)
    x = points()
    value, gradient = model(x, eval_gradient=True)
    assert np.linalg.eigvalsh(value).min() >= -1e-12
    for index in range(model.n_dims):
        step = np.zeros(model.n_dims)
        step[index] = 1e-6
        difference = (
            model.clone_with_theta(model.theta + step)(x)
            - model.clone_with_theta(model.theta - step)(x)
        ) / (2e-6)
        np.testing.assert_allclose(gradient[:, :, index], difference, rtol=2e-6, atol=2e-9)


def test_category_codes_only_use_equality_not_numeric_distance():
    x = points()
    renamed = x.copy()
    renamed[:, 1] = np.where(x[:, 1] == 0, 31, 5)
    renamed[:, 2] = 12 - x[:, 2]
    np.testing.assert_array_equal(kernel()(x), kernel()(renamed))
    np.testing.assert_array_equal(kernel().diag(x), np.full(len(x), 1.3))


def test_single_category_can_be_omitted_without_numeric_constant_error():
    model = MixedPredictorKernel(ConstantKernel(2.0), (), (), categorical_theta=())
    x = np.zeros((3, 1))
    np.testing.assert_array_equal(model(x), np.full((3, 3), 2.0))
    value, gradient = model(x, eval_gradient=True)
    assert gradient.shape == (3, 3, 1)
    np.testing.assert_array_equal(gradient[:, :, 0], value)


def test_category_only_uses_amplitude_and_equality_kernel():
    model = MixedPredictorKernel(ConstantKernel(2.0), (), (0,), categorical_theta=0.7)
    x = np.array([[0], [1], [0]])
    expected = 2 * np.exp(-0.7 * (x[:, 0, None] != x[None, :, 0]))
    np.testing.assert_allclose(model(x), expected, rtol=1e-14)


def test_sklearn_clone_optimizer_and_json_numeric_array_restore_work():
    signal = kernel()
    copied = clone(signal)
    np.testing.assert_array_equal(copied.theta, signal.theta)
    np.testing.assert_array_equal(copied(points()), signal(points()))
    gp = GaussianProcessRegressor(kernel=signal, alpha=0.01, n_restarts_optimizer=0)
    with pytest.warns(ConvergenceWarning, match="categorical_theta"):
        gp.fit(points(), [0.1, 0.7, 1.0, 0.4])
    assert "gp_category_theta_bound" in mixed_kernel_warning_codes(gp.kernel_)
    payload = json.loads(json.dumps(mixed_kernel_to_payload(gp.kernel_), allow_nan=False))
    restored = mixed_kernel_from_payload(payload)
    np.testing.assert_allclose(restored(points()), gp.kernel_(points()), rtol=1e-14)
    assert restored.theta.size == 0
    assert restored.bounds.shape == (0, 2)
    assert all(value.dtype.kind != "O" for value in [gp.X_train_, gp.L_, gp.alpha_])


def test_invalid_mapping_bounds_codes_and_payload_are_rejected():
    with pytest.raises(ValueError, match="gp_mixed_kernel_invalid"):
        MixedPredictorKernel(ConstantKernel(), (0,), (0,))(points())
    with pytest.raises(ValueError, match="gp_mixed_kernel_invalid"):
        kernel(theta=(-1, 1))(points())
    with pytest.raises(ValueError, match="gp_mixed_kernel_invalid"):
        kernel(theta=(True, 1))(points())
    bad = points()
    bad[0, 1] = 0.5
    with pytest.raises(ValueError, match="gp_mixed_kernel_invalid"):
        kernel()(bad)
    with pytest.raises(ValueError, match="gp_mixed_kernel_invalid"):
        kernel()(points(), points(), eval_gradient=True)
    payload = mixed_kernel_to_payload(kernel())
    payload["unknown"] = True
    with pytest.raises(ValueError, match="gp_mixed_kernel_payload_invalid"):
        mixed_kernel_from_payload(payload)


def test_log_parameter_boundary_round_trip_is_not_a_policy_change():
    model = kernel(theta=(1e-4, 1e2))
    restored = model.clone_with_theta(model.theta)
    np.testing.assert_allclose(restored(points()), model(points()), rtol=1e-14)
    assert restored.categorical_theta[1] <= 1e2
    assert mixed_kernel_warning_codes(restored) == ("gp_category_theta_bound",)
    with pytest.raises(ValueError, match="gp_mixed_kernel_invalid"):
        kernel(theta=(1e-4, 101))(points())


def test_fixed_restored_kernel_prediction_matches_independent_cholesky():
    signal = kernel()
    x, y = points(), np.array([0.1, 0.7, 1.0, 0.4])
    restored = mixed_kernel_from_payload(mixed_kernel_to_payload(signal))
    query = np.array([[0.2, 1, 0], [0.9, 0, 1]])
    fitted = GaussianProcessRegressor(kernel=restored, alpha=0.01, optimizer=None).fit(x, y)
    predicted, sd = fitted.predict(query, return_std=True)

    # Independent dense covariance, using only the stated scalar kernel formula.
    def covariance(left, right):
        distance = np.abs(left[:, 0, None] - right[None, :, 0]) / 0.8
        scaled = np.sqrt(5) * distance
        numeric = 1.3 * (1 + scaled + scaled**2 / 3) * np.exp(-scaled)
        mismatch = sum(
            theta * (left[:, j, None] != right[None, :, j]) for j, theta in [(1, 0.7), (2, 1.2)]
        )
        return numeric * np.exp(-mismatch)

    lower = np.linalg.cholesky(covariance(x, x) + np.eye(len(x)) * 0.01)
    cross = covariance(query, x)
    alpha = np.linalg.solve(lower.T, np.linalg.solve(lower, y))
    solved = np.linalg.solve(lower, cross.T)
    np.testing.assert_allclose(predicted, cross @ alpha, atol=1e-13, rtol=1e-13)
    np.testing.assert_allclose(sd**2, 1.3 - (solved**2).sum(axis=0), atol=1e-13, rtol=1e-13)
