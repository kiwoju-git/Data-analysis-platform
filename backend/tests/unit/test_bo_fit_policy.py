from __future__ import annotations

import math
import time

import numpy as np
import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_fit_policy import BoFitPolicy, screened_starts
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate

X = np.array([[0.0], [0.09], [0.27], [0.43], [0.6], [0.78], [0.91], [1.0]])
Y = 3 + np.sin(12 * X[:, 0]) + 0.15 * np.cos(21 * X[:, 0])
SEARCH = dict(
    random_seed=42,
    jitter=1e-8,
    hyperparameter_restart_count=0,
    model_max_iterations=80,
    model_max_evaluations=1000,
)


def independent_lml(x, y, amplitude, lengths, noise, kind):
    r = np.linalg.norm((x[:, None] - x[None, :]) / lengths, axis=2)
    if kind == "gaussian":
        k = np.exp(-0.5 * r**2)
    elif kind == "exponential":
        k = np.exp(-r)
    else:
        u = np.sqrt(3 if kind == "matern_3_2" else 5) * r
        k = (1 + u + (u**2 / 3 if kind == "matern_5_2" else 0)) * np.exp(-u)
    lower = np.linalg.cholesky(amplitude * k + np.eye(len(x)) * (noise + SEARCH["jitter"]))
    solved = np.linalg.solve(lower, (y - y.mean()) / y.std(ddof=0))
    return float(
        -0.5 * solved @ solved - np.log(np.diag(lower)).sum() - len(y) * math.log(2 * math.pi) / 2
    )


def test_screen_is_bounded_deterministic_and_includes_original_start():
    theta = np.log([1.0, 1.0, 1.0, 0.01])
    bounds = np.log([[1e-3, 1e3], [1e-2, 1e2], [1e-2, 1e2], [1e-6, 1]])
    starts = screened_starts(theta, bounds, 2)
    assert len(starts) == 9
    np.testing.assert_array_equal(starts[0], theta)
    assert all(np.all(s >= bounds[:, 0]) and np.all(s <= bounds[:, 1]) for s in starts)
    assert len({tuple(s) for s in starts}) == 9
    assert all(s[0] == theta[0] and s[-1] == theta[-1] for s in starts)


@pytest.mark.parametrize("kind", ["matern_5_2", "matern_3_2", "gaussian", "exponential"])
@pytest.mark.parametrize("mode", ["estimate", "fixed", "near_noiseless"])
def test_fit_is_no_worse_than_screen_and_matches_independent_likelihood(kind, mode):
    policy = BoSurrogatePolicy(noise_mode=mode, fixed_noise_sd=0.05 if mode == "fixed" else None)
    model = fit_bo_surrogate(
        X,
        Y,
        policy,
        SEARCH,
        deadline=time.perf_counter() + 30,
        kernel_spec=BoKernelSpec(kind),
        fit_policy=BoFitPolicy(1),
    )
    metadata = model.metadata()
    assert metadata["schema_version"] == 5
    diagnostics = metadata["fit_diagnostics"]
    assert diagnostics["policy"] == "bounded_multiscale_starts_v1"
    assert (
        model.log_marginal_likelihood
        >= max(-s["negative_log_likelihood"] for s in diagnostics["screening"]) - 1e-11
    )
    signal, noise = metadata["signal_kernel"], metadata["noise"]["fitted_variance_scaled"]
    reference = independent_lml(
        X, Y, signal["amplitude"], np.array(signal["length_scales"]), noise, kind
    )
    assert model.log_marginal_likelihood == pytest.approx(reference, abs=2e-8, rel=2e-9)
    assert metadata["optimizer"]["evaluations"] == len(diagnostics["screening"]) + sum(
        s["evaluations"] for s in metadata["optimizer"]["starts"]
    )
    assert diagnostics["global_optimum_guaranteed"] is False
    assert metadata["optimizer"]["restarts"] == 0


def test_old_path_and_seed_are_unchanged_and_new_option_is_explicit():
    original = fit_bo_surrogate(
        X,
        Y,
        BoSurrogatePolicy(),
        SEARCH,
        deadline=time.perf_counter() + 30,
        kernel_spec=BoKernelSpec(),
    )
    explicit = fit_bo_surrogate(
        X,
        Y,
        BoSurrogatePolicy(),
        SEARCH,
        deadline=time.perf_counter() + 30,
        kernel_spec=BoKernelSpec(),
        fit_policy=None,
    )
    a, b = original.metadata(), explicit.metadata()
    a.pop("fit_elapsed_ms")
    b.pop("fit_elapsed_ms")
    assert a == b
    assert a["schema_version"] == 4 and "fit_diagnostics" not in a


@pytest.mark.parametrize("count", [1, 2, 3])
def test_deterministic_and_random_starts_are_separate_and_reproducible(count):
    search = {**SEARCH, "hyperparameter_restart_count": 2}

    def run():
        metadata = fit_bo_surrogate(
            X,
            Y,
            BoSurrogatePolicy(),
            search,
            deadline=time.perf_counter() + 30,
            kernel_spec=BoKernelSpec(),
            fit_policy=BoFitPolicy(count),
        ).metadata()
        metadata.pop("fit_elapsed_ms")
        return metadata

    first, repeated = run(), run()
    assert first == repeated
    evidence = first["fit_diagnostics"]
    starts = first["optimizer"]["starts"]
    assert first["optimizer"]["restarts"] == 2
    assert len(starts) == count + 2
    expected_order = sorted(
        range(len(evidence["screening"])),
        key=lambda index: (evidence["screening"][index]["negative_log_likelihood"], index),
    )[:count]
    assert evidence["refined_screen_indices"] == expected_order
    for index, screen_index in enumerate(expected_order):
        assert (
            starts[index]["initial_log_parameters"]
            == evidence["screening"][screen_index]["log_parameters"]
        )
    assert first["optimizer"]["evaluations"] == 9 + sum(s["evaluations"] for s in starts)


def test_screen_evaluations_obey_the_same_budget():
    with pytest.raises(BayesianOptimizationError) as caught:
        fit_bo_surrogate(
            X,
            Y,
            BoSurrogatePolicy(),
            {**SEARCH, "model_max_evaluations": 8},
            deadline=time.perf_counter() + 30,
            kernel_spec=BoKernelSpec(),
            fit_policy=BoFitPolicy(1),
        )
    assert caught.value.code == "bayesian_optimization_budget_exhausted"


@pytest.mark.parametrize("count", [0, 4, True, 1.5])
def test_policy_rejects_invalid_start_counts(count):
    with pytest.raises(ValueError):
        BoFitPolicy(count)


def test_regenerated_parameter_roundoff_is_bounded_not_statistical_tolerance():
    from app.services.bo_fit_quality_contract import _same_regenerated_numbers

    values = np.array([-13.815510557964274, 0.0, 4.605170185988092])
    assert _same_regenerated_numbers(np.nextafter(values, np.inf), values)
    assert not _same_regenerated_numbers(values + 1e-10, values)
    assert _same_regenerated_numbers([np.nextafter(1e-6, np.inf)], [1e-6], log_space=False)
    assert not _same_regenerated_numbers([1e-6 + 1e-14], [1e-6], log_space=False)
    assert not _same_regenerated_numbers([float("nan")], [0])


@pytest.mark.parametrize("compressed", [False, True])
def test_unequal_exact_replicates_match_independent_raw_likelihood(compressed):
    xs = np.array([[0], [0], [0.4], [0.8], [0.8], [0.8], [1.0]])
    ys = np.array([1.1, 1.3, 2.5, 1.0, 1.4, 1.2, 2.0])
    groups = ((0, 1), (2,), (3, 4, 5), (6,)) if compressed else None
    model = fit_bo_surrogate(
        xs,
        ys,
        BoSurrogatePolicy(),
        SEARCH,
        deadline=time.perf_counter() + 30,
        kernel_spec=BoKernelSpec(),
        fit_policy=BoFitPolicy(1),
        group_member_indices=groups,
    )
    meta = model.metadata()
    signal = meta["signal_kernel"]
    expected = independent_lml(
        xs,
        ys,
        signal["amplitude"],
        np.array(signal["length_scales"]),
        meta["noise"]["fitted_variance_scaled"],
        "matern_5_2",
    )
    assert model.log_marginal_likelihood == pytest.approx(expected, abs=2e-8, rel=2e-9)
    assert meta["raw_observation_count"] == 7
    assert meta["effective_training_count"] == (4 if compressed else 7)


def test_keeps_better_intermediate_and_receipt_when_solver_returns_worse(monkeypatch):
    from types import SimpleNamespace

    from app.statistics.bo_fit_policy import bounded_multiscale_optimize

    theta = np.array([0.0, 0.0])
    bounds = np.array([[-3.0, 3.0], [-4.0, 4.0]])

    def objective(point):
        delta = point - np.array([1.0, 0.37])
        return float(delta @ delta), 2 * delta

    def solver(fun, initial, **kwargs):
        fun(initial)
        fun(np.array([1.0, 0.37]))
        value, _ = fun(initial)
        return SimpleNamespace(
            x=initial, fun=value, success=False, status=1, message="synthetic limit", nit=2
        )

    monkeypatch.setattr("scipy.optimize.minimize", solver)
    fitted, traces, evidence = bounded_multiscale_optimize(
        theta, bounds, 1, BoFitPolicy(1), SEARCH, objective
    )
    np.testing.assert_array_equal(fitted, [1.0, 0.37])
    assert evidence["selected"]["stage"] == "local_evaluation"
    assert evidence["start_best_evaluations"][0]["evaluation_index"] == 1
    assert traces[0]["negative_log_likelihood"] > evidence["selected"]["negative_log_likelihood"]


def test_new_batch_contract_roundtrip_and_no_refit_validation(monkeypatch):
    import json

    from test_bo_desirability_batch_core import batch_request

    from app.api.v1.schemas.bo_fit_quality import (
        DesirabilityFitCalculationRequest,
        DesirabilityFitCalculationResult,
    )
    from app.services.bo_desirability_batch_contract import validate_batch_calculation_result
    from app.statistics.bo_desirability_batch_core import calculate_desirability_batch

    raw = batch_request(2)
    raw.update(
        schema_version=6,
        fit_policy={"kind": "bounded_multiscale_starts_v1", "deterministic_start_count": 2},
    )
    raw["search"]["model_max_evaluations"] = 1500
    request = DesirabilityFitCalculationRequest.model_validate(raw)
    result = calculate_desirability_batch(request.worker_payload())
    parsed = DesirabilityFitCalculationResult.model_validate_json(json.dumps(result))

    def forbidden(*args, **kwargs):
        pytest.fail("stored evidence validation must not fit/evaluate likelihood")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    monkeypatch.setattr("app.statistics.bo_surrogate._likelihood", forbidden)
    validate_batch_calculation_result(request, parsed)
    evidence = parsed.shared_model.response_models[0].model.fit_diagnostics
    if evidence.selected.stage == "local_evaluation":
        original_index = evidence.selected.start_index
        evidence.selected.start_index = 1 - original_index
        with pytest.raises(BayesianOptimizationError):
            validate_batch_calculation_result(request, parsed)
        evidence.selected.start_index = original_index
    assert result["shared_model"]["schema_version"] == 6
    assert result["search_budget"]["model_evaluations_consumed"] == sum(
        m["model"]["optimizer"]["evaluations"] for m in result["shared_model"]["response_models"]
    )
    parsed.shared_model.response_models[0].model.fit_diagnostics.refined_screen_indices = [8]
    with pytest.raises(BayesianOptimizationError):
        validate_batch_calculation_result(request, parsed)
