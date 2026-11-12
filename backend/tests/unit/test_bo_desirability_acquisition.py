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


def test_concentrated_symmetric_beta_still_has_positive_improvement():
    result = beta_expected_improvement(0.5, 1e-20, 0.5)
    # Exact symmetric formula is Gamma(a+.5)/(4*a*sqrt(pi)*Gamma(a)).
    # Its first omitted relative term here is < 1e-19.
    assert result.value == pytest.approx(math.sqrt(1e-20 / (2 * math.pi)), rel=1e-12)
    assert result.distribution == "beta_moment_match"


def test_unresolved_extreme_beta_is_not_silently_deterministic():
    with pytest.raises(BayesianOptimizationError, match="precision"):
        beta_expected_improvement(0.5, 1e-28, 0.5)


@pytest.mark.parametrize(
    "mean,variance,threshold,expected",
    [
        (1e-12, 1e-28, 9.9e-13, 1.0825062186803883e-14),
        (0.123456789, 3e-24, 0.1234567890173205, 1.2946222314123248e-36),
        (0.9, 1e-9, 0.9000316227766018, 2.6339494963754832e-6),
    ],
)
def test_independent_decimal_density_reference_near_precision_boundaries(
    mean, variance, threshold, expected
):
    # Independently evaluated with 80-digit Decimal log-density and positive
    # quadrature, not production centering/log1pmx helpers. See validation note.
    result = beta_expected_improvement(mean, variance, threshold)
    assert result.value == pytest.approx(expected, rel=2e-7, abs=0)


@pytest.mark.parametrize("threshold", [0.5755140304746322, 0.575, 0.57])
def test_synthetic_batch_far_tail_uses_correct_float_rounding(threshold):
    # Captured from a synthetic 3-observation, estimated-noise q2 review.
    # Independent positive integral, scaled at the threshold to avoid both
    # cancellation and underflow inside the quadrature integrand.
    mean, variance = 0.5154451791162806, 2.4973594698037663e-6
    concentration = mean * (1 - mean) / variance - 1
    a, b = mean * concentration, (1 - mean) * concentration
    rate = (b - 1) / (1 - threshold) - (a - 1) / threshold
    integral, error = quad(
        lambda u: u
        * math.exp(
            (a - 1) * math.log1p(u / rate / threshold)
            + (b - 1) * math.log1p(-u / rate / (1 - threshold))
        ),
        0,
        100,
        epsabs=1e-12,
        epsrel=1e-12,
    )
    assert error < 1e-11
    expected_log = beta.logpdf(threshold, a, b) - 2 * math.log(rate) + math.log(integral)
    expected = math.exp(expected_log)
    if threshold == 0.5755140304746322:
        assert expected_log == pytest.approx(-746.0088854781693, abs=1e-8)
        assert expected_log < math.log(math.ulp(0.0)) - math.log(2)
        assert expected == 0.0
    else:
        assert expected > 0
    result = beta_expected_improvement(mean, variance, threshold)
    assert result.value == pytest.approx(expected, rel=1e-6, abs=2 * math.ulp(0.0))
    assert result.distribution == "beta_moment_match"
    assert result.alpha == a and result.beta == b


def test_non_tail_cancellation_still_fails_instead_of_inventing_zero(monkeypatch):
    monkeypatch.setattr("scipy.special.betaincc", lambda *args: 0.5)
    with pytest.raises(BayesianOptimizationError, match="precision"):
        beta_expected_improvement(0.5, 0.05, 0.5)


def test_concentrated_synthetic_batch_tail_has_provably_unrepresentable_ei():
    mean, variance, threshold = 0.4992536685725198, 4.3272878739092573e-10, 0.5122227046862013
    n = mean * (1 - mean) / variance - 1
    a, b = mean * n, (1 - mean) * n
    rate = (b - 1) / (1 - threshold) - (a - 1) / threshold
    # A positive density integral is bounded by the log-concave tangent.
    log_upper = beta.logpdf(threshold, a, b) - 2 * math.log(rate)
    assert log_upper < -100_000
    result = beta_expected_improvement(mean, variance, threshold)
    assert result.value == 0
    assert result.distribution == "beta_moment_match"
    assert result.alpha == a and result.beta == b


@pytest.mark.parametrize("z", [0.0, 1.0, -1.0, 10.0, 29.6352391607161])
def test_concentrated_beta_positive_integral_not_point_mass(z):
    mean, variance = 0.5112756891793482, 1.0211694697324158e-9
    n = mean * (1 - mean) / variance - 1
    a, b = mean * n, (1 - mean) * n
    sd = math.sqrt(variance)
    threshold = mean + z * sd
    # Independent Boost density integrated in standardized coordinates.
    expected, error = quad(
        lambda u: u * beta.pdf(threshold + sd * u, a, b) * sd**2,
        0,
        40,
        epsabs=0,
        epsrel=2e-8,
    )
    assert error <= abs(expected) * 2e-8
    result = beta_expected_improvement(mean, variance, threshold)
    assert result.value > 0
    assert result.value == pytest.approx(expected, rel=2e-7, abs=0)
    assert result.distribution == "beta_moment_match"


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
