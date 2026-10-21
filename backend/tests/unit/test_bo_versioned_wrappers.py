import pytest
from test_bo_recommendation_core import payload

from app.statistics.bayesian_batch import calculate_bayesian_recommendation_batch
from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    calculate_bayesian_recommendation,
)
from app.statistics.bo_recommendation_core import calculate_noise_aware_batch


@pytest.mark.parametrize("goal", ["maximize", "minimize", "match_target"])
def test_versioned_single_and_batch_wrappers_use_identical_q1_core(goal):
    request = payload(goal, 1)
    direct = calculate_noise_aware_batch(request)
    single = calculate_bayesian_recommendation(request)
    batch = calculate_bayesian_recommendation_batch(request)
    assert single["schema_version"] == batch["schema_version"] == 2
    assert single["items"] == batch["items"] == direct["items"]
    assert single["incumbent"] == direct["incumbent"]


def test_single_wrapper_cannot_silently_drop_requested_batch_members():
    with pytest.raises(BayesianOptimizationError):
        calculate_bayesian_recommendation(payload(size=2))


def test_noise_options_without_version_are_not_ignored_as_legacy():
    request = payload(size=1)
    request["search"]["batch_policy"] = "greedy_posterior_mean_fantasy_ei_v1"
    for function in (calculate_bayesian_recommendation, calculate_bayesian_recommendation_batch):
        with pytest.raises(BayesianOptimizationError):
            function(request)
