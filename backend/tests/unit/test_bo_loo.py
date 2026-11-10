"""Fixed-parameter row LOO, independently checked by deleting each covariance row."""

import time
from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest

from app.statistics.bo_loo import conditional_row_loo
from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate


def model(x, y, groups=None, noise_sd=0.2):
    return fit_bo_surrogate(
        np.asarray(x, dtype=float),
        np.asarray(y, dtype=float),
        BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=noise_sd),
        {
            "jitter": 1e-8,
            "random_seed": 42,
            "hyperparameter_restart_count": 0,
            "model_max_iterations": 20,
            "model_max_evaluations": 100,
        },
        deadline=time.perf_counter() + 20,
        optimize=False,
        group_member_indices=groups,
    )


@pytest.mark.parametrize("compressed", [False, True])
def test_row_loo_matches_independent_deleted_cholesky(compressed):
    x = np.asarray([[0.0], [0.0], [0.3], [0.7], [0.7], [0.7], [1.0]])
    y = np.asarray([1.0, 1.4, 1.8, 0.2, 0.5, 1.2, 2.0])
    fitted = model(x, y, [[0, 1], [2], [3, 4, 5], [6]] if compressed else None)
    ids = [f"trial-{i}" for i in range(len(y))]
    result = conditional_row_loo(fitted, x, y, ids)
    # Independent explicit Matern 5/2 covariance, no production kernel/predict helper.
    length = float(np.atleast_1d(fitted.kernel.k1.k2.length_scale)[0])
    amplitude = float(fitted.kernel.k1.k1.constant_value)
    d = np.abs(x - x.T) / length
    signal = amplitude * (1 + np.sqrt(5) * d + 5 * d * d / 3) * np.exp(-np.sqrt(5) * d)
    variance = (0.2 / np.std(y)) ** 2 + fitted.jitter
    targets = (y - np.mean(y)) / np.std(y)
    expected = []
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        chol = np.linalg.cholesky(signal[np.ix_(keep, keep)] + variance * np.eye(keep.sum()))
        alpha = np.linalg.solve(chol.T, np.linalg.solve(chol, targets[keep]))
        expected.append(np.mean(y) + np.std(y) * signal[i, keep] @ alpha)
    actual = [row["predicted"] for row in result["points"]]
    assert actual == pytest.approx(expected, rel=2e-12, abs=2e-12)
    assert [row["trial_id"] for row in result["points"]] == ids
    assert result["n_scored"] == result["raw_observation_count"] == len(y)
    assert result["effective_training_count"] == (4 if compressed else 7)
    errors = y - expected
    assert result["rmse"] == pytest.approx(np.sqrt(np.mean(errors**2)), rel=2e-12)
    assert result["r_squared"] == pytest.approx(
        1 - np.sum(errors**2) / np.sum((y - y.mean()) ** 2), rel=2e-12
    )
    assert result["r_squared_reason"] is None


def test_constant_response_r_squared_unavailable_and_negative_score_not_clamped():
    x = [[0.0], [0.2], [0.7], [1.0]]
    fitted = model(x, [3.0] * 4)
    result = conditional_row_loo(fitted, x, [3.0] * 4, [f"t{i}" for i in range(4)])
    assert result["r_squared"] is None
    assert result["r_squared_reason"] == "constant_observations"
    assert result["rmse"] == 0
    y = [1.0, -1.0, 1.0, -1.0]
    result = conditional_row_loo(model(x, y), x, y, [f"t{i}" for i in range(4)])
    assert result["r_squared"] < 0


def test_duplicate_ids_and_nonfinite_inputs_fail_without_partial_score():
    from app.statistics.bayesian_optimization import BayesianOptimizationError

    x, y = [[0.0], [0.5], [1.0]], [1.0, 2.0, 1.0]
    fitted = model(x, y)
    for values, ids in ((y, ["x"] * 3), ([1.0, float("nan"), 1.0], ["a", "b", "c"])):
        with pytest.raises(BayesianOptimizationError, match="bayesian_loo_diagnostic_invalid"):
            conditional_row_loo(fitted, x, values, ids)
    with pytest.raises(BayesianOptimizationError, match="bayesian_loo_diagnostic_invalid"):
        conditional_row_loo(replace(fitted, raw_observation_count=4), x, y, ["a", "b", "c"])


def test_tiny_distinct_response_is_not_constant_or_zero_error():
    x, y = [[0.0], [0.5], [1.0]], [1e-200, 2e-200, 1e-200]
    result = conditional_row_loo(model(x, y), x, y, ["a", "b", "c"])
    assert result["r_squared"] is not None
    assert result["r_squared_reason"] is None
    assert 0 < result["rmse"] < 1e-199


@pytest.mark.parametrize("mixed", [False, True])
def test_snapshot_diagnostics_preserve_source_and_never_refit(mixed, monkeypatch):
    from app.api.v1.schemas.bo_loo import LooCalculation
    from app.statistics.bo_loo import planning_loo
    from app.statistics.bo_mixed_planning import fit_mixed_planning_model
    from app.statistics.bo_planning_model import fit_planning_model
    from tests.unit.test_bo_mixed_planning import payload
    from tests.unit.test_bo_versioned_curves import curve_request

    snapshot = (
        fit_mixed_planning_model(payload()) if mixed else fit_planning_model(curve_request(1))
    )
    before = deepcopy(snapshot)

    def forbidden(*args, **kwargs):
        pytest.fail("LOO must not refit")

    monkeypatch.setattr("app.statistics.bo_surrogate.fit_bo_surrogate", forbidden)
    monkeypatch.setattr("app.statistics.bo_desirability_core._fit_response_models", forbidden)
    monkeypatch.setattr("app.statistics.bo_mixed_planning.fit_bo_mixed_surrogate", forbidden)
    result = planning_loo(snapshot, mixed=mixed)
    assert LooCalculation.model_validate(result).model_dump(mode="json") == result
    assert result["model_refit"] is result["auto_routing_applied"] is False
    for row in result["responses"]:
        assert row["n_scored"] == len(snapshot["calculation_request"]["observations"])
    assert planning_loo(snapshot, mixed=mixed) == result
    assert snapshot == before


@pytest.mark.parametrize("scale,offset", [(10.0, 20.0), (-2.0, 100.0), (1e-4, 0.0)])
def test_loo_units_and_trial_permutation_preserve_decision(scale, offset):
    """Metamorphic check: unit conversion is not evidence of changed fit quality."""
    from app.statistics.bo_auto_strategy import suggest_augmentation

    x = np.asarray([[0.0], [0.2], [0.5], [0.8], [1.0]])
    y = np.asarray([1.0, 1.4, 2.0, 1.3, 1.1])
    ids = [f"t{i}" for i in range(len(y))]
    base = conditional_row_loo(model(x, y), x, y, ids)
    order = np.asarray([3, 0, 4, 1, 2])
    transformed_y = scale * y[order] + offset
    result = conditional_row_loo(
        model(x[order], transformed_y, noise_sd=abs(scale) * 0.2),
        x[order],
        transformed_y,
        [ids[i] for i in order],
    )
    assert result["r_squared"] == pytest.approx(base["r_squared"], rel=2e-11, abs=2e-11)
    assert result["rmse"] == pytest.approx(abs(scale) * base["rmse"], rel=2e-11)
    expected = {row["trial_id"]: scale * row["predicted"] + offset for row in base["points"]}
    for row in result["points"]:
        assert row["predicted"] == pytest.approx(expected[row["trial_id"]], rel=2e-11, abs=1e-12)

    def decision(score):
        return suggest_augmentation(
            [{"response_id": "response", "r_squared": score}], ["continuous"], 0.25
        )

    assert decision(result["r_squared"]) == decision(base["r_squared"])
