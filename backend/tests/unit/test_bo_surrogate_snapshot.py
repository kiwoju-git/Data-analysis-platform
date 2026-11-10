from __future__ import annotations

import copy
import json
import math
import time
from dataclasses import replace

import numpy as np
import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate
from app.statistics.bo_surrogate_snapshot import (
    dump_bo_surrogate,
    load_bo_surrogate,
)

SEARCH = {
    "random_seed": 17,
    "jitter": 1e-8,
    "hyperparameter_restart_count": 0,
    "model_max_iterations": 80,
    "model_max_evaluations": 300,
}
FAMILIES = ["matern_5_2", "matern_3_2", "gaussian", "exponential"]


def _fixture(family="gaussian", noise="fixed", *, grouped=False, goal="maximize", fit=False):
    x = np.array([[0.0], [0.25], [0.25], [0.75], [1.0]])
    y = np.array([1.0, 1.7, 2.1, 1.2, 0.9])
    groups = ((0,), (1, 2), (3,), (4,)) if grouped else None
    policy = BoSurrogatePolicy(noise_mode=noise, fixed_noise_sd=0.12 if noise == "fixed" else None)
    model = fit_bo_surrogate(
        x,
        y,
        policy,
        SEARCH,
        deadline=time.perf_counter() + 30,
        goal_type=goal,
        optimize=fit,
        group_member_indices=groups,
        kernel_spec=BoKernelSpec(family) if family else None,
        fit_policy=BoFitPolicy(1) if fit else None,
    )
    targets = (
        model.direction_multiplier * y - model.normalization_mean
    ) / model.normalization_scale
    if groups is not None:
        targets = np.array([targets[list(group)].mean() for group in groups])
    return model, targets, x, y


def _correlation(x, z, family):
    distance = np.sqrt(np.sum((x[:, None] - z[None, :]) ** 2, axis=2))
    if family == "gaussian":
        return np.exp(-0.5 * distance**2)
    if family == "exponential":
        return np.exp(-distance)
    if family == "matern_3_2":
        scaled = math.sqrt(3) * distance
        return (1 + scaled) * np.exp(-scaled)
    scaled = math.sqrt(5) * distance
    return (1 + scaled + scaled**2 / 3) * np.exp(-scaled)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("noise", ["estimate", "fixed", "near_noiseless"])
@pytest.mark.parametrize("grouped", [False, True])
def test_snapshot_roundtrip_preserves_independent_posterior(family, noise, grouped, monkeypatch):
    model, targets, x, y = _fixture(family, noise, grouped=grouped)
    original_x, original_y = x.copy(), y.copy()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)
    decoded = json.loads(encoded)

    def no_fit(*args, **kwargs):
        pytest.fail("Snapshot restoration must not fit or optimize")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", no_fit)
    monkeypatch.setattr("app.statistics.bo_surrogate._likelihood", no_fit)
    monkeypatch.setattr("scipy.optimize.minimize", no_fit)
    restored = load_bo_surrogate(decoded, expected_training_targets_scaled=targets)
    q = np.array([[0.1], [0.3], [0.9]])
    actual = restored.predict(q, joint=True)
    expected = model.predict(q, joint=True)
    for name in (
        "mean_scaled",
        "latent_variance_scaled",
        "predictive_variance_scaled",
        "latent_covariance_scaled",
    ):
        np.testing.assert_array_equal(getattr(actual, name), getattr(expected, name))
    noise_variance = {
        "estimate": 1e-2,
        "fixed": (0.12 / np.std(y, ddof=0)) ** 2,
        "near_noiseless": 0.0,
    }[noise]
    covariance = _correlation(model.x_train, model.x_train, family)
    covariance[np.diag_indices(len(model.x_train))] += (noise_variance + 1e-8) / np.array(
        model.group_counts
    )
    cross = _correlation(model.x_train, q, family)
    expected_mean = cross.T @ np.linalg.solve(covariance, targets)
    expected_covariance = _correlation(q, q, family) - cross.T @ np.linalg.solve(covariance, cross)
    # Repeated raw rows near zero noise are ill-conditioned; this checks a separate solve.
    np.testing.assert_allclose(actual.mean_scaled, expected_mean, atol=2e-8, rtol=2e-8)
    np.testing.assert_allclose(actual.latent_covariance_scaled, expected_covariance, atol=2e-8)
    np.testing.assert_allclose(
        actual.predictive_variance_scaled - actual.latent_variance_scaled,
        noise_variance,
        atol=2e-15,
    )
    # Separate matrix products subtract signal-scale values; near-zero posterior
    # entries need an absolute roundoff allowance, not a relative-only comparison.
    covariance_roundoff = (
        8
        * np.finfo(float).eps
        * len(model.x_train)
        * float(np.max(np.diag(_correlation(q, q, family))))
    )
    np.testing.assert_allclose(
        restored.latent_cross_covariance(q[:2], q[2:]),
        actual.latent_covariance_scaled[:2, 2:],
        rtol=2e-13,
        atol=covariance_roundoff,
    )
    assert restored.metadata() == model.metadata()
    assert restored.group_counts == ((1, 2, 1, 1) if grouped else (1, 1, 1, 1, 1))
    assert restored.raw_observation_count == 5
    assert json.dumps(decoded, allow_nan=False, sort_keys=True) == encoded
    np.testing.assert_array_equal(x, original_x)
    np.testing.assert_array_equal(y, original_y)
    restored.x_train[0, 0] = 0.05
    assert model.x_train[0, 0] == payload["training"]["x_normalized"][0][0] == 0


def test_two_observation_gaussian_has_hand_checkable_midpoint():
    model = fit_bo_surrogate(
        [[0.0], [1.0]],
        [1.0, 3.0],
        BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=1.0),
        SEARCH,
        deadline=time.perf_counter() + 30,
        optimize=False,
        kernel_spec=BoKernelSpec("gaussian"),
    )
    payload = dump_bo_surrogate(model, training_targets_scaled=[-1.0, 1.0])
    restored = load_bo_surrogate(payload)
    result = restored.predict([[0.5]], joint=True)
    c = math.exp(-0.5)
    denominator = 2 + SEARCH["jitter"] - c
    np.testing.assert_allclose(restored.alpha, [-1 / denominator, 1 / denominator], atol=1e-15)
    assert result.mean_scaled[0] == pytest.approx(0, abs=1e-15)
    variance = 1 - 2 * math.exp(-0.25) / (2 + SEARCH["jitter"] + c)
    assert result.latent_variance_scaled[0] == pytest.approx(variance, abs=1e-15)
    assert result.predictive_variance_scaled[0] == pytest.approx(variance + 1, abs=1e-15)


def test_restore_preserves_cholesky_triangular_solver_layout():
    model, targets, _, _ = _fixture()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    restored = load_bo_surrogate(payload)
    assert model.lower.flags.f_contiguous
    # SciPy selects a different LAPACK transpose path for C-order factors.
    assert restored.lower.flags.f_contiguous
    np.testing.assert_array_equal(restored.lower, model.lower)


@pytest.mark.parametrize("goal", ["maximize", "minimize", "match_target"])
def test_snapshot_retains_direction_normalization_and_legacy_metadata(goal):
    model, targets, _, _ = _fixture(None, goal=goal)
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    restored = load_bo_surrogate(payload)
    assert restored.kernel_spec is None
    assert restored.direction_multiplier == (-1 if goal == "minimize" else 1)
    assert restored.metadata() == model.metadata()
    assert restored.metadata()["schema_version"] == 3


def test_opt_in_fit_diagnostics_and_compression_survive_snapshot():
    model, targets, _, _ = _fixture("matern_3_2", "estimate", grouped=True, fit=True)
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    restored = load_bo_surrogate(json.loads(json.dumps(payload, allow_nan=False)))
    assert restored.fit_diagnostics == model.fit_diagnostics
    assert restored.fit_diagnostics is not model.fit_diagnostics
    assert restored.metadata() == model.metadata()
    assert restored.metadata()["schema_version"] == 5
    np.testing.assert_array_equal(
        restored.predict([[0.4]]).mean_scaled, model.predict([[0.4]]).mean_scaled
    )


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("schema_version",), 2),
        (("schema_version",), True),
        (("policy",), "unrecognized"),
        (("kernel", "family"), "rational_quadratic"),
        (("kernel", "amplitude"), 0),
        (("kernel", "amplitude"), 1e20),
        (("kernel", "length_scales"), [1.0, 2.0]),
        (("kernel", "length_scales"), [0.0]),
        (("kernel", "explicit_family"), "true"),
        (("noise_variance_scaled",), float("nan")),
        (("noise_variance_scaled",), 0.0),
        (("noise_policy", "fixed_noise_sd"), 1e308),
        (("noise_policy", "initial_noise_variance_scaled"), 0.0),
        (("normalization", "scale"), 0.0),
        (("normalization", "direction_multiplier"), 0.0),
        (("normalization", "ddof"), False),
        (("jitter",), 0.0),
        (("training", "x_normalized"), [[0.0], ["0.25"], [0.25], [0.75], [1.0]]),
        (("training", "x_normalized"), [[0.0], [True], [0.25], [0.75], [1.0]]),
        (("training", "x_normalized"), [[0.0], [0.25, 1.0], [0.25], [0.75], [1.0]]),
        (("training", "x_normalized"), [[-0.1], [0.25], [0.25], [0.75], [1.0]]),
        (("training", "x_normalized"), [[0.0]] * 201),
        (("training", "targets_scaled"), [1.0]),
        (("training", "targets_scaled"), [0.0] * 5),
        (("training", "group_counts"), [1, 1, 1, 1, 2]),
        (("training", "group_counts"), [1.0] * 5),
        (("training", "raw_observation_count"), 201),
        (("factorization", "alpha"), [0.0] * 5),
        (("factorization", "alpha"), [float("inf")] * 5),
        (("factorization", "lower"), [[1.0]]),
        (("fit", "package_versions"), {"numpy": "current"}),
        (("fit", "warning_codes"), ["private error text"]),
        (("fit", "optimizer", "optimized"), "false"),
        (("fit", "optimizer", "max_evaluations"), 1),
    ],
)
def test_snapshot_rejects_invalid_state_without_coercion(path, bad_value):
    model, targets, _, _ = _fixture()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    node = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = bad_value
    before = copy.deepcopy(payload)
    with pytest.raises(BayesianOptimizationError, match="bayesian_surrogate_snapshot_invalid"):
        load_bo_surrogate(payload)
    if not any(isinstance(value, float) and math.isnan(value) for value in [bad_value]):
        assert payload == before


@pytest.mark.parametrize("path", [(), ("kernel",), ("training",), ("factorization",), ("fit",)])
def test_unknown_fields_are_not_ignored(path):
    model, targets, _, _ = _fixture()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    node = payload
    for key in path:
        node = node[key]
    node["unknown"] = "not supported"
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_surrogate(payload)


@pytest.mark.parametrize("damage", ["covariance", "upper_triangle", "negative_diagonal"])
def test_factorization_integrity_is_checked(damage):
    model, targets, _, _ = _fixture()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    lower = payload["factorization"]["lower"]
    if damage == "covariance":
        lower[1][0] += 0.01
    elif damage == "upper_triangle":
        lower[0][1] = 1e-20
    else:
        lower[0][0] *= -1
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_surrogate(payload)


def test_compressed_noise_divides_jitter_and_measurement_variance_by_cell_count():
    model, targets, _, _ = _fixture(grouped=True)
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    payload["training"]["group_counts"] = [2, 1, 1, 1]
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_surrogate(payload)


def test_source_targets_are_required_and_independently_checkable():
    model, targets, _, _ = _fixture(grouped=True)
    with pytest.raises(TypeError):
        dump_bo_surrogate(model)
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        dump_bo_surrogate(model, training_targets_scaled=targets + 1)
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_surrogate(payload, expected_training_targets_scaled=targets + 1e-12)
    for invalid in (np.array(targets, dtype=object), np.ones((2, 2)), np.array([True])):
        with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
            dump_bo_surrogate(model, training_targets_scaled=invalid)


def test_kernel_spec_and_fitted_family_must_agree():
    model, targets, _, _ = _fixture()
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        dump_bo_surrogate(
            replace(model, kernel_spec=BoKernelSpec("exponential")), training_targets_scaled=targets
        )


def test_json_boundary_rejects_arrays_objects_and_unbounded_nesting():
    model, targets, _, _ = _fixture()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    variants = []
    numeric_array = copy.deepcopy(payload)
    numeric_array["training"]["targets_scaled"] = np.array(targets)
    variants.append(numeric_array)
    object_value = copy.deepcopy(payload)
    object_value["fit"]["diagnostics"] = object()
    variants.append(object_value)
    nested = copy.deepcopy(payload)
    value = []
    for _ in range(10):
        value = [value]
    nested["unknown"] = value
    variants.append(nested)
    for invalid in variants:
        with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
            load_bo_surrogate(invalid)


def test_targets_cannot_be_inferred_by_omitting_the_stored_vector():
    model, targets, _, _ = _fixture()
    payload = dump_bo_surrogate(model, training_targets_scaled=targets)
    del payload["training"]["targets_scaled"]
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_surrogate(payload)


@pytest.mark.parametrize("field", ["x_train", "lower", "alpha"])
def test_snapshot_writer_rejects_object_arrays(field):
    model, targets, _, _ = _fixture()
    invalid = replace(model, **{field: getattr(model, field).astype(object)})
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        dump_bo_surrogate(invalid, training_targets_scaled=targets)
