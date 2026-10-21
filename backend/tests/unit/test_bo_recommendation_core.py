from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_recommendation_core import calculate_noise_aware_batch


def payload(goal="maximize", size=2):
    x = [0, 0.25, 0.5, 0.75, 1]
    y = [0.1, 0.6, 1.0, 0.8, 0.2]
    return {
        "factors": [{"factor_id": "x", "low": 0.0, "high": 1.0}],
        "constraints": [],
        "observations": [
            {
                "trial_id": f"trial-{i}",
                "actual_coordinates": {"x": value},
                "normalized_coordinates": {"x": value},
                "objective_value": y[i],
            }
            for i, value in enumerate(x)
        ],
        "excluded_normalized": [[value] for value in x],
        "objective": {"goal_type": goal, "target_value": 0.7 if goal == "match_target" else None},
        "batch_size": size,
        "acquisition": {
            "kind": "expected_target_improvement"
            if goal == "match_target"
            else "expected_improvement",
            "exploration_profile": "balanced",
            "xi_standardized": 0.01,
        },
        "surrogate": {"noise_mode": "estimate"},
        "observation_policy": {"mode": "retain_raw"},
        "batch_options": {"posterior_sample_count": 64, "min_batch_distance_normalized": 0},
        "search": {
            "random_seed": 123,
            "candidate_count_per_step": 64,
            "local_start_count_per_step": 1,
            "max_iterations_per_step": 30,
            "max_evaluations_total": 2048,
            "model_max_iterations": 50,
            "model_max_evaluations": 200,
            "hyperparameter_restart_count": 0,
            "time_budget_ms": 30000,
            "jitter": 1e-8,
            "duplicate_tolerance": 1e-6,
            "batch_policy": "greedy_mc_joint_latent_improvement_v2",
        },
    }


@pytest.mark.parametrize("goal", ["maximize", "minimize", "match_target"])
def test_q1_and_first_batch_candidate_share_the_same_policy_and_pool(goal):
    single = calculate_noise_aware_batch(payload(goal, 1))
    batch = calculate_noise_aware_batch(payload(goal, 2))
    first = batch["items"][0]
    assert first["actual_coordinates"] == single["items"][0]["actual_coordinates"]
    assert (
        first["acquisition_value_standardized"]
        == single["items"][0]["acquisition_value_standardized"]
    )
    assert batch["items"][1]["planning"]["effective_sample_count"] == 64
    assert first["planning"]["effective_sample_count"] == 0
    assert first["predictive_standard_deviation"] >= first["latent_standard_deviation"]
    assert batch["incumbent"]["best_observed_trial_id"].startswith("trial-")
    assert batch["shared_model"]["noise"]["mode"] == "estimate"
    json.dumps(batch, allow_nan=False)


def test_batch_seed_reproducibility_and_input_immutability():
    request = payload()
    before = copy.deepcopy(request)
    first, second = calculate_noise_aware_batch(request), calculate_noise_aware_batch(request)
    assert request == before
    assert first["items"] == second["items"]
    assert first["observation_view"]["raw_observation_count"] == 5
    assert first["observation_view"]["effective_training_count"] == 5
    assert (
        first["items"][1]["planning"]["representative_prediction_source"]
        == "completed_observations_base_posterior"
    )


def test_exact_replicates_are_a_read_only_training_view():
    request = payload(size=1)
    repeated = copy.deepcopy(request["observations"][1])
    repeated.update({"trial_id": "repeat-1", "objective_value": 0.7})
    request["observations"].append(repeated)
    request["observation_policy"]["mode"] = "exact_replicates"
    result = calculate_noise_aware_batch(request)
    assert result["shared_model"]["raw_observation_count"] == 6
    assert result["shared_model"]["effective_training_count"] == 5
    assert result["observation_view"]["groups"][1]["member_trial_ids"] == ["trial-1", "repeat-1"]
    assert len(request["observations"]) == 6


def test_unsatisfiable_batch_distance_has_no_partial_success():
    request = payload()
    request["batch_options"]["min_batch_distance_normalized"] = 2
    with pytest.raises(BayesianOptimizationError):
        calculate_noise_aware_batch(request)


def test_measurement_noise_not_jitter_is_future_variance_difference():
    result = calculate_noise_aware_batch(payload())
    noise = result["shared_model"]["observation_noise_sd_raw"] ** 2
    for item in result["items"]:
        delta = item["predictive_standard_deviation"] ** 2 - item["latent_standard_deviation"] ** 2
        np.testing.assert_allclose(delta, noise, atol=1e-14)
