import math

import pytest
from scipy.integrate import quad
from scipy.stats import norm

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_target_curve import TargetCurve, target_desirability, target_moments


def test_control_points_and_tails_are_not_linear_cutoffs():
    curve = TargetCurve(-2.0, 0.0, 3.0, 0.02, 0.1)
    assert [target_desirability(x, curve) for x in (-2, 0, 3)] == pytest.approx([0.02, 1, 0.1])
    assert 0 < target_desirability(-3, curve) < 0.02
    assert target_desirability(-1, curve) == pytest.approx(0.02**0.25)


def test_hand_check_normal_moments():
    curve = TargetCurve(-1.0, 0.0, 1.0, math.exp(-1), math.exp(-1))
    actual = target_moments(0.0, 1.0, curve)
    assert actual.mean == pytest.approx(1 / math.sqrt(3), abs=2e-14)
    assert actual.second_moment == pytest.approx(1 / math.sqrt(5), abs=2e-14)
    assert actual.variance == pytest.approx(1 / math.sqrt(5) - 1 / 3, abs=2e-14)


def test_training_curve_control_example_and_unit_translation():
    curve = TargetCurve(-2, 0, 2, 0.0183, 0.0183)
    assert target_desirability(1, curve) == pytest.approx(0.0183**0.25, rel=1e-14)
    a = -math.log(0.0183) / 4
    moments = target_moments(0, 1, curve)
    assert moments.mean == pytest.approx(1 / math.sqrt(1 + 2 * a), abs=2e-14)
    assert moments.variance == pytest.approx(1 / math.sqrt(1 + 4 * a) - 1 / (1 + 2 * a), abs=2e-14)
    shifted = target_moments(1000, 0.001, TargetCurve(999.998, 1000, 1000.002, 0.0183, 0.0183))
    # Decimal controls near 1000 are representable to about 1e-13 absolute.
    assert shifted.mean == pytest.approx(moments.mean, rel=2e-11)


@pytest.mark.parametrize("ordinate", [1e-200, math.nextafter(1.0, 0.0)])
def test_side_ordinate_extremes_remain_explicit(ordinate):
    curve = TargetCurve(-1, 0, 1, ordinate, ordinate)
    assert target_desirability(1, curve) == pytest.approx(ordinate, rel=1e-13, abs=0)
    moments = target_moments(0, 1, curve)
    assert 0 < moments.mean <= 1 and moments.variance > 0


@pytest.mark.parametrize("mean,sd", [(0, 1), (-1.7, 0.4), (3, 2), (0, 0.01)])
@pytest.mark.parametrize("power", [0.01, 0.3, 1.0, 2.0])
def test_asymmetric_moments_match_independent_integration(mean, sd, power):
    curve = TargetCurve(-2.0, 0.0, 3.0, 0.02, 0.1)

    def integrate(p):
        def f(z):
            y = mean + sd * z
            a = -math.log(0.02) / 4 if y < 0 else -math.log(0.1) / 9
            return math.exp(-p * a * y * y) * norm.pdf(z)

        split = max(-12, min(12, -mean / sd))
        return sum(
            quad(f, lo, hi, epsabs=1e-13, epsrel=1e-11)[0] for lo, hi in [(-12, split), (split, 12)]
        )

    actual = target_moments(mean, sd, curve, power=power)
    first, second = integrate(power), integrate(2 * power)
    assert actual.mean == pytest.approx(first, abs=2e-12, rel=1e-10)
    assert actual.second_moment == pytest.approx(second, abs=2e-12, rel=1e-10)
    assert actual.variance == pytest.approx(second - first * first, abs=2e-12, rel=1e-8)


def test_tiny_variance_not_lost_by_subtracting_rounded_moments():
    curve = TargetCurve(-1.0, 0.0, 1.0, math.exp(-1), math.exp(-1))
    actual = target_moments(0.0, 1e-8, curve)
    assert actual.variance == pytest.approx(2e-32, rel=1e-10, abs=0)
    off_center = target_moments(0.5, 1e-10, curve)
    assert off_center.variance == pytest.approx(math.exp(-0.5) * 1e-20, rel=1e-8, abs=0)
    assert target_moments(0, 0, curve).variance == 0


def test_narrow_peak_is_not_missed():
    curve = TargetCurve(-1e-12, 0.0, 1e-12, math.exp(-1), math.exp(-1))
    actual = target_moments(0, 1, curve)
    assert actual.mean == pytest.approx(1 / math.sqrt(1 + 2e24), rel=1e-12, abs=0)
    assert actual.second_moment == pytest.approx(1 / math.sqrt(1 + 4e24), rel=1e-12, abs=0)


def test_unrepresentable_positive_variance_is_unavailable_not_zero():
    curve = TargetCurve(-1, 0, 1, math.exp(-1), math.exp(-1))
    with pytest.raises(BayesianOptimizationError, match="precision_unsupported"):
        target_moments(0.5, 1e-200, curve)


def test_finite_coordinates_do_not_overflow_to_false_zero():
    curve = TargetCurve(-1.5e308, -1e308, 0, math.exp(-1), math.exp(-1))
    assert target_desirability(1e308, curve) == pytest.approx(math.exp(-4))


@pytest.mark.parametrize("bad", [True, "1", math.inf, math.nan, complex(1, 0)])
def test_non_numeric_and_nonfinite_rejected(bad):
    with pytest.raises(BayesianOptimizationError):
        TargetCurve(-1, 0, 1, bad, 0.1)


@pytest.mark.parametrize("args", [(0, 0, 1, 0.1, 0.1), (-1, 0, 1, 0, 0.1), (-1, 0, 1, 1, 0.1)])
def test_invalid_controls_not_sorted_or_clamped(args):
    with pytest.raises(BayesianOptimizationError):
        TargetCurve(*args)
