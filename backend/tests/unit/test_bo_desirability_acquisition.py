from __future__ import annotations

import math

import pytest
from scipy.integrate import quad
from scipy.stats import beta

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_acquisition import beta_expected_improvement


def test_beta_two_two_has_hand_checkable_ei():
    result = beta_expected_improvement(0.5, 0.05, 0.5)
    assert result.value == pytest.approx(3 / 32, abs=2e-14)
    assert result.alpha == pytest.approx(2)
    assert result.beta == pytest.approx(2)
    assert result.distribution == "beta_moment_match"


@pytest.mark.parametrize(
    "a,b,t", [(0.2, 3, 0.1), (5, 2, 0.9), (2, 5, 0.1), (10, 10, 0.5), (2, 2, 0.9999)]
)
def test_beta_ei_matches_independent_positive_part_integral(a, b, t):
    mean, variance = a / (a + b), a * b / ((a + b) ** 2 * (a + b + 1))
    expected = quad(lambda x: (x - t) * beta.pdf(x, a, b), t, 1, epsabs=1e-16, epsrel=1e-10)[0]
    result = beta_expected_improvement(mean, variance, t)
    assert result.value == pytest.approx(expected, rel=2e-8, abs=1e-16)
    assert 0 <= result.value <= mean


def test_beta_is_an_approximation_not_exact_product_distribution():
    # Independent Phi(N(0,1)) responses are U(0,1), D=sqrt(U1*U2).
    mean, second = 4 / 9, 1 / 4
    result = beta_expected_improvement(mean, second - mean**2, 0.5)
    reference = quad(lambda x: (x - 0.5) * beta.pdf(x, 28 / 17, 35 / 17), 0.5, 1, epsabs=1e-13)[0]
    exact_product = 1 / 72 + math.log(2) / 12
    assert result.value == pytest.approx(reference, abs=1e-12)
    assert result.value == pytest.approx(0.07153759904846113, abs=1e-12)
    assert abs(result.value - exact_product) > 1e-4


def test_degenerate_and_bernoulli_limits_are_not_invalid_beta_calls():
    assert beta_expected_improvement(0.6, 0, 0.4).value == pytest.approx(0.2)
    assert beta_expected_improvement(0.6, 0, 0.6).value == 0
    result = beta_expected_improvement(0.3, 0.21, 0.4)
    assert result.value == pytest.approx(0.18)
    assert result.distribution == "bernoulli_limit"
    assert result.alpha is None
    assert beta_expected_improvement(0, 0, 0).value == 0
    assert beta_expected_improvement(1, 0, 0.5).value == 0.5


def test_exploration_is_subtracted_once_in_desirability_units():
    first = beta_expected_improvement(0.5, 0.05, 0.4, xi=0.1)
    second = beta_expected_improvement(0.5, 0.05, 0.5)
    assert first.value == second.value
    assert first.threshold == 0.5
    assert beta_expected_improvement(0.5, 0.05, 1).value == 0
    assert beta_expected_improvement(0.5, 0.05, 0.95, xi=0.1).value == 0


def test_unresolved_extreme_beta_is_not_silently_deterministic():
    with pytest.raises(BayesianOptimizationError, match="precision"):
        beta_expected_improvement(0.5, 1e-20, 0.5)


@pytest.mark.parametrize("baseline", [0.0, 0.5, 1.0])
def test_subnormal_variance_never_returns_infinite_beta_parameters(baseline):
    with pytest.raises(BayesianOptimizationError, match="precision"):
        beta_expected_improvement(0.5, math.ulp(0.0), baseline)


@pytest.mark.parametrize(
    "mean,variance,incumbent,xi",
    [
        (math.nan, 0, 0, 0),
        (0.5, math.inf, 0, 0),
        (True, 0, 0, 0),
        ("0.5", 0, 0, 0),
        (0.5, -0.01, 0, 0),
        (0.5, 0.26, 0, 0),
        (0, 0.01, 0, 0),
        (1, 0.01, 0, 0),
        (0.5, 0.1, -0.1, 0),
        (0.5, 0.1, 1.1, 0),
        (0.5, 0.1, 0.5, -0.1),
    ],
)
def test_invalid_moments_and_inputs_fail_explicitly(mean, variance, incumbent, xi):
    with pytest.raises(BayesianOptimizationError):
        beta_expected_improvement(mean, variance, incumbent, xi=xi)
