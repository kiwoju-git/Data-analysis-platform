from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import (
    DesirabilityGoal,
    composite_desirability,
    gaussian_desirability_moments,
    independent_desirability_moments,
    individual_desirability,
    normalized_importance,
)


def maximize(response_id="yield", importance=1.0):
    return DesirabilityGoal(response_id, "maximize", 0.0, 1.0, None, importance)


def target(response_id="quality", lower=-1.0, middle=0.0, upper=1.0, importance=1.0):
    return DesirabilityGoal(response_id, "match_target", lower, middle, upper, importance)


def test_explicit_curves_are_hand_checkable_and_do_not_mutate_values():
    values = np.array([-1, 0, 0.25, 0.5, 0.75, 1, 2.0])
    before = values.copy()
    np.testing.assert_array_equal(
        individual_desirability(values, maximize()), [0, 0, 0.25, 0.5, 0.75, 1, 1]
    )
    minimize = DesirabilityGoal("cost", "minimize", None, 0.0, 1.0)
    np.testing.assert_array_equal(
        individual_desirability(values, minimize), [1, 1, 0.75, 0.5, 0.25, 0, 0]
    )
    np.testing.assert_array_equal(
        individual_desirability([-2, -0.5, 0, 0.5, 2], target()), [0, 0.5, 1, 0.5, 0]
    )
    np.testing.assert_array_equal(values, before)


def test_composite_identity_mapping_weights_and_zero_are_explicit():
    goals = (maximize("a", 1), maximize("b", 3))
    assert composite_desirability({"b": 1.0, "a": 0.25}, goals) == pytest.approx(0.25**0.25)
    assert composite_desirability({"a": 0.0, "b": 1.0}, goals) == 0
    assert composite_desirability({"a": 0.25, "b": 1.0}, goals[::-1]) == pytest.approx(0.25**0.25)
    np.testing.assert_allclose(normalized_importance(goals), [0.25, 0.75])
    np.testing.assert_allclose(
        normalized_importance((maximize("a", 1e300), maximize("b", 1e300))), [0.5, 0.5]
    )
    for values in ({"a": 1}, {"a": 1, "b": 1, "unknown": 1}):
        with pytest.raises(BayesianOptimizationError):
            composite_desirability(values, goals)
    with pytest.raises(BayesianOptimizationError):
        normalized_importance((maximize("a", 1e-300), maximize("b", 1e300)))
    with pytest.raises(BayesianOptimizationError):
        normalized_importance((maximize("a"), maximize("a")))


@pytest.mark.parametrize(
    "bad", [math.nan, math.inf, -math.inf, True, "1", np.complex64(1 + 2j), np.complex128(1 + 2j)]
)
def test_invalid_numeric_input_never_coerces(bad):
    with pytest.raises(BayesianOptimizationError):
        maximize(importance=bad)
    with pytest.raises(BayesianOptimizationError):
        individual_desirability(bad, maximize())
    with pytest.raises(BayesianOptimizationError):
        gaussian_desirability_moments(0, bad, maximize())


def test_mixed_numeric_boolean_list_is_not_coerced_to_zero_one():
    with pytest.raises(BayesianOptimizationError):
        individual_desirability([0.5, True], maximize())


@pytest.mark.parametrize(
    "args",
    [
        ("a", "maximize", 1, 0, None),
        ("a", "maximize", 0, 1, 2),
        ("a", "minimize", 0, 1, 2),
        ("a", "minimize", None, 2, 1),
        ("a", "match_target", 0, 0, 1),
        ("a", "range", 0, 1, 2),
        ("", "maximize", 0, 1, None),
    ],
)
def test_invalid_preferences_rejected_without_sorting_or_filling(args):
    with pytest.raises(BayesianOptimizationError):
        DesirabilityGoal(*args)


def test_normal_linear_moments_match_independent_closed_form():
    moments = gaussian_desirability_moments(0.5, 0.5, maximize())
    second = 0.5 - 0.5 * norm.pdf(1)
    assert moments.mean == pytest.approx(0.5, abs=2e-12)
    assert moments.second_moment == pytest.approx(second, abs=2e-12)
    assert moments.variance == pytest.approx(second - 0.25, abs=2e-12)
    assert moments.integration_evaluations > 0
    assert moments.estimated_absolute_error < 1e-10


@pytest.mark.parametrize("power", [0.01, 0.25, 0.5, 1.0, 2.0])
@pytest.mark.parametrize("mean,sd", [(0.2, 0.7), (2.0, 0.05), (-2.0, 0.1)])
def test_weight_is_inside_expectation_and_matches_independent_raw_integral(power, mean, sd):
    actual = gaussian_desirability_moments(mean, sd, maximize(), power=power)
    expected = quad(
        lambda y: y**power * norm.pdf((y - mean) / sd) / sd, 0, 1, epsabs=1e-13, epsrel=1e-10
    )[0] + norm.sf((1 - mean) / sd)
    assert actual.mean == pytest.approx(expected, abs=2e-11, rel=2e-9)


def test_target_symmetric_and_narrow_windows_are_not_missed():
    regular = gaussian_desirability_moments(0, 1, target())
    expected = 2 * quad(lambda y: (1 - y) * norm.pdf(y), 0, 1, epsabs=1e-13)[0]
    assert regular.mean == pytest.approx(expected, abs=2e-12)
    narrow = gaussian_desirability_moments(0, 1, target(lower=-1e-12, upper=1e-12))
    assert narrow.mean == pytest.approx(norm.pdf(0) * 1e-12, rel=1e-10, abs=0)
    assert narrow.second_moment == pytest.approx(norm.pdf(0) * 2e-12 / 3, rel=1e-10, abs=0)
    left = gaussian_desirability_moments(-0.4, 0.7, target())
    right = gaussian_desirability_moments(0.4, 0.7, target())
    assert left.mean == pytest.approx(right.mean, abs=2e-12)


@pytest.mark.parametrize("width", [1e-12, 1e-16, 1e-20])
@pytest.mark.parametrize("mean", [-1.0, 1.0])
def test_off_center_narrow_target_preserves_original_width(width, mean):
    result = gaussian_desirability_moments(mean, 1, target(lower=-width, upper=width))
    assert result.mean == pytest.approx(norm.pdf(mean) * width, rel=1e-10, abs=0)
    assert result.second_moment == pytest.approx(norm.pdf(mean) * width * 2 / 3, rel=1e-10, abs=0)


def test_small_positive_variance_is_not_lost_to_second_moment_subtraction():
    result = gaussian_desirability_moments(0.5, 1e-10, maximize())
    assert result.variance == pytest.approx(1e-20, rel=1e-7, abs=0)
    assert result.variance > 0
    result = gaussian_desirability_moments(0.5, 1e-20, maximize())
    assert result.variance == pytest.approx(1e-40, rel=1e-7, abs=0)


def test_zero_sd_and_tiny_positive_sd_at_a_limit_have_different_meanings():
    assert gaussian_desirability_moments(0, 0, maximize()).mean == 0
    positive = gaussian_desirability_moments(0, 1e-20, maximize())
    assert positive.mean == pytest.approx(1e-20 / math.sqrt(2 * math.pi), rel=1e-10, abs=0)
    assert positive.variance == pytest.approx((0.5 - 1 / (2 * math.pi)) * 1e-40, rel=1e-8, abs=0)
    for args in [(0, -1, 1), (0, 1, 0), (0, 1, -1)]:
        with pytest.raises(BayesianOptimizationError):
            gaussian_desirability_moments(args[0], args[1], maximize(), power=args[2])


def test_positive_change_of_units_preserves_all_moments():
    original = gaussian_desirability_moments(0.3, 0.2, target(), power=0.3)
    changed = gaussian_desirability_moments(
        1003, 2, target(lower=990, middle=1000, upper=1010), power=0.3
    )
    for name in ("mean", "variance", "second_moment"):
        assert getattr(original, name) == pytest.approx(getattr(changed, name), abs=2e-12)


def test_independent_response_product_uses_moments_not_desirability_of_mean():
    goals = (maximize("a", 1), maximize("b", 3))
    result = independent_desirability_moments({"a": (0.4, 0.3), "b": (0.6, 0.2)}, goals)
    first = gaussian_desirability_moments(0.4, 0.3, goals[0], power=0.25)
    second = gaussian_desirability_moments(0.6, 0.2, goals[1], power=0.75)
    assert result.mean == pytest.approx(first.mean * second.mean, abs=1e-13)
    assert result.second_moment == pytest.approx(
        first.second_moment * second.second_moment, abs=1e-13
    )
    assert result.variance == pytest.approx(result.second_moment - result.mean**2, abs=1e-12)
    assert result.mean != pytest.approx(
        composite_desirability({"a": 0.4, "b": 0.6}, goals), abs=1e-3
    )
    swapped = independent_desirability_moments({"b": (0.6, 0.2), "a": (0.4, 0.3)}, goals[::-1])
    assert swapped.mean == pytest.approx(result.mean, abs=1e-14)
    assert swapped.variance == pytest.approx(result.variance, abs=1e-14)


def test_integration_resource_limit_is_an_error_not_a_partial_success():
    with pytest.raises(BayesianOptimizationError, match="budget"):
        gaussian_desirability_moments(0.2, 0.4, maximize(), max_evaluations=1)


def test_tiny_importance_does_not_erase_zero_desirability_probability_mass():
    result = gaussian_desirability_moments(0.5, 0.5, maximize(), power=1e-10)
    assert result.mean == pytest.approx(norm.cdf(1), abs=2e-10)
    assert result.mean < 0.9
