"""Auto advice is a product policy, not an undocumented JMP decision tree."""

import math

import pytest

from app.statistics.bo_auto_strategy import suggest_augmentation


def decide(values, kinds=("continuous",), threshold=0.25):
    return suggest_augmentation(
        [{"response_id": f"r{i}", "r_squared": value} for i, value in enumerate(values)],
        list(kinds),
        threshold,
    )


def test_any_response_below_threshold_not_average_or_weighted():
    result = decide([0.99, 0.24])
    assert result["recommended_policy"] == "greedy_incremental_maxpro_v1"
    assert result["reason"] == "any_response_below_threshold"
    assert result["below_threshold_response_ids"] == ["r1"]
    assert result["threshold"] == 0.25


def test_equality_passes_and_confirm_is_never_inferred():
    for values in ([0.25], [0.25, 1.0], [0.999]):
        result = decide(values)
        assert result["recommended_policy"] == "refine_ei_alternating_desirability_response_sd_v2"
        assert result["reason"] == "all_responses_meet_threshold"
        assert "all_pass_refine_is_product_policy" in result["warnings"]


@pytest.mark.parametrize("kind", ["discrete_numeric", "nominal", "ordinal"])
def test_mixed_exploration_is_explicit_maximin_not_mixed_maxpro(kind):
    result = decide([-2.0], ("continuous", kind))
    assert result["recommended_policy"] == "greedy_mixed_maximin_v1"
    assert "mixed_maximin_is_product_policy" in result["warnings"]
    assert result["ordinal_rank_distance_requires_consent"] == (kind == "ordinal")


def test_unavailable_response_blocks_advice_even_when_another_is_below():
    result = decide([-1, None])
    assert result["recommended_policy"] is None
    assert result["reason"] == "r_squared_unavailable"
    assert result["unavailable_response_ids"] == ["r1"]


@pytest.mark.parametrize("threshold", [-0.01, 1.01, math.nan, math.inf, True, "0.25"])
def test_invalid_threshold_is_not_coerced(threshold):
    with pytest.raises(ValueError, match="bayesian_auto_strategy_invalid"):
        decide([0.5], threshold=threshold)


@pytest.mark.parametrize("values", [[], [0.1] * 5, [math.nan], [math.inf], [1.001], [True]])
def test_all_metrics_validated_before_any_low_branch(values):
    with pytest.raises(ValueError, match="bayesian_auto_strategy_invalid"):
        decide(values)


def test_duplicate_response_and_unknown_domain_rejected():
    with pytest.raises(ValueError):
        suggest_augmentation([{"response_id": "r", "r_squared": 0.1}] * 2, ["continuous"], 0.25)
    with pytest.raises(ValueError):
        decide([0.1], ("unknown",))


def test_threshold_changes_decision_without_changing_metrics():
    assert decide([0.4], threshold=0.3)["reason"] == "all_responses_meet_threshold"
    assert decide([0.4], threshold=0.5)["reason"] == "any_response_below_threshold"
