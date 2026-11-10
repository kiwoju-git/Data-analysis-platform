from __future__ import annotations

import copy
import json

import numpy as np
import pytest
from test_bo_mixed_surrogate import EQUAL, LATENT, UNEQUAL, factors, fitted

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_factor_domains import bo_factor_domains_to_payload
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_mixed_snapshot import dump_bo_mixed_surrogate, load_bo_mixed_surrogate
from app.statistics.bo_surrogate import BoSurrogatePolicy


@pytest.mark.parametrize("category_policy", [EQUAL, UNEQUAL, LATENT])
@pytest.mark.parametrize(
    "policy",
    [
        BoSurrogatePolicy(),
        BoSurrogatePolicy(noise_mode="fixed", fixed_noise_sd=0.4),
        BoSurrogatePolicy(noise_mode="near_noiseless"),
    ],
)
def test_json_restore_preserves_prediction_without_fit_or_likelihood(
    monkeypatch, category_policy, policy
):
    model = fitted(domains=factors(category_policy), policy=policy)
    payload = dump_bo_mixed_surrogate(model)
    frozen = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    query = np.array([[0.2, 0], [0.6, 1], [0.8, 2]])
    expected = model.predict(query, joint=True)

    def forbidden(*args, **kwargs):
        raise AssertionError("restoration cannot refit or call training likelihood")

    monkeypatch.setattr("app.statistics.bo_mixed_surrogate.fit_bo_mixed_surrogate", forbidden)
    monkeypatch.setattr("app.statistics.bo_mixed_surrogate.mixed_likelihood", forbidden)
    monkeypatch.setattr("scipy.optimize.minimize", forbidden)
    restored = load_bo_mixed_surrogate(
        json.loads(frozen),
        expected_factor_domains=model.factor_domains,
        expected_training_targets_scaled=model.training_targets_scaled,
        expected_within_ss_scaled=model.training_within_ss_scaled,
    )
    actual = restored.predict(query, joint=True)
    np.testing.assert_array_equal(actual.mean_scaled, expected.mean_scaled)
    np.testing.assert_array_equal(
        actual.latent_covariance_scaled, expected.latent_covariance_scaled
    )
    np.testing.assert_array_equal(
        actual.predictive_variance_scaled, expected.predictive_variance_scaled
    )
    assert json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False) == frozen
    assert restored.metadata()["schema_version"] == 6
    assert payload["schema_version"] == 2


def test_compressed_snapshot_retains_within_ss_and_validates_lml():
    model = fitted(
        x=np.array([[0, 0], [0.5, 1], [1, 2]]),
        y=np.array([-1, 0.1, 1]),
        group_counts=(3, 1, 2),
        within_ss_scaled=[0.1, 0, 0.4],
        raw_observation_count=6,
        policy=BoSurrogatePolicy(),
    )
    payload = dump_bo_mixed_surrogate(model)
    restored = load_bo_mixed_surrogate(payload)
    assert restored.group_counts == (3, 1, 2)
    np.testing.assert_array_equal(restored.training_within_ss_scaled, [0.1, 0, 0.4])
    payload["training"]["within_ss_scaled"][0] += 0.2
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_mixed_surrogate(payload)


def test_optimized_typed_receipts_round_trip():
    model = fitted(optimize=True, fit_policy=BoFitPolicy(1))
    payload = dump_bo_mixed_surrogate(model)
    restored = load_bo_mixed_surrogate(payload)
    np.testing.assert_array_equal(restored.kernel.theta, model.kernel.theta)
    assert restored.fit_diagnostics == model.fit_diagnostics
    assert restored.optimizer == model.optimizer


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(schema_version=1),
        lambda value: value.update(schema_version=True),
        lambda value: value.update(unknown="bad"),
        lambda value: value["factor_domains"]["factors"][1].update(unknown=True),
        lambda value: value["signal_kernel"].update(kind="arbitrary.class"),
        lambda value: value["training"]["x_encoded"][0].__setitem__(1, 1.5),
        lambda value: value["training"]["x_encoded"][0].__setitem__(1, 3),
        lambda value: value["training"]["x_encoded"][0].__setitem__(0, "0.0"),
        lambda value: value["factorization"]["lower"][0].__setitem__(1, 0.001),
        lambda value: value["factorization"]["lower"][1].__setitem__(0, 0.123),
        lambda value: value["factorization"]["lower"][0].__setitem__(0, 0),
        lambda value: value["factorization"]["alpha"].__setitem__(0, 100),
        lambda value: value["training"]["targets_scaled"].__setitem__(0, 100),
        lambda value: value["training"]["group_counts"].__setitem__(0, 2),
        lambda value: value["fit"].update(log_marginal_likelihood=1000),
        lambda value: value["fit"]["diagnostics"]["parameter_descriptors"][2].update(
            role="numeric_length_scale"
        ),
        lambda value: value["fit"]["optimizer"].update(evaluations=0),
        lambda value: value["fit"]["warning_codes"].append("C:\\private\\raw-data"),
        lambda value: value.update(noise_variance_scaled=0.9),
        lambda value: value["normalization"].update(direction_multiplier=0),
        lambda value: value["training"]["targets_scaled"].__setitem__(0, float("nan")),
    ],
)
def test_corrupt_or_unknown_state_is_rejected(mutation):
    payload = dump_bo_mixed_surrogate(fitted())
    mutation(payload)
    with pytest.raises((ValueError, BayesianOptimizationError), match="invalid|mismatch"):
        load_bo_mixed_surrogate(payload)


def test_source_binding_detects_vocabulary_order_and_targets_not_recoverable_from_arrays():
    model = fitted()
    payload = dump_bo_mixed_surrogate(model)
    payload["factor_domains"] = bo_factor_domains_to_payload(factors(levels=("b", "a", "c")))
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_mixed_surrogate(payload, expected_factor_domains=model.factor_domains)
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_mixed_surrogate(
            dump_bo_mixed_surrogate(model), expected_training_targets_scaled=[1, 2, 3, 4]
        )


def test_object_arrays_and_prior_warning_loss_are_rejected():
    payload = dump_bo_mixed_surrogate(
        fitted(x=np.array([[0.0, 0], [1.0, 0]]), y=np.array([-1.0, 1]))
    )
    invalid = copy.deepcopy(payload)
    invalid["training"]["x_encoded"] = np.array(invalid["training"]["x_encoded"], dtype=object)
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_mixed_surrogate(invalid)
    payload["fit"]["warning_codes"] = []
    with pytest.raises(BayesianOptimizationError, match="snapshot_invalid"):
        load_bo_mixed_surrogate(payload)
