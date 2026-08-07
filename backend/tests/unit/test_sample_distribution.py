import pytest
from scipy import stats  # type: ignore[import-untyped]

from app.statistics.sample_distribution import (
    mean_confidence_interval,
    median_confidence_interval,
    sample_moments,
    standard_deviation_confidence_interval,
)


def test_minitab_sample_moment_formulas_match_independent_scipy_reference() -> None:
    values = [7, 9, 16, 36, 39, 45, 45, 46, 48, 51]
    result = sample_moments(values)

    assert result["mean"] == pytest.approx(34.2)
    assert result["standard_deviation"] == pytest.approx(16.923356641044943)
    assert result["variance"] == pytest.approx(286.4)
    assert result["skewness"] == pytest.approx(stats.skew(values, bias=False))
    assert result["kurtosis_excess"] == pytest.approx(
        stats.kurtosis(values, fisher=True, bias=False)
    )


def test_graphical_summary_confidence_intervals_match_reference_values() -> None:
    values = [7, 9, 16, 36, 39, 45, 45, 46, 48, 51]

    mean_interval = mean_confidence_interval(values, 0.95)
    assert mean_interval["method"] == "student_t"
    assert {key: value for key, value in mean_interval.items() if key != "method"} == pytest.approx(
        {
            "computed": True,
            "confidence_level": 0.95,
            "estimate": 34.2,
            "lower": 22.093759954324867,
            "upper": 46.30624004567514,
        }
    )
    median_interval = median_confidence_interval(values, 0.95)
    assert median_interval["method"] == "hettmansperger_sheather_nonlinear"
    assert {
        key: value for key, value in median_interval.items() if key != "method"
    } == pytest.approx(
        {
            "computed": True,
            "confidence_level": 0.95,
            "estimate": 42.0,
            "lower": 13.603603603603608,
            "upper": 46.68468468468468,
            "order_statistic_index": 8,
            "interpolation_weight": 0.34234234234234184,
        }
    )
    standard_deviation_interval = standard_deviation_confidence_interval(values, 0.95)
    assert standard_deviation_interval["method"] == "chi_square_normal_population"
    assert {
        key: value for key, value in standard_deviation_interval.items() if key != "method"
    } == pytest.approx(
        {
            "computed": True,
            "confidence_level": 0.95,
            "estimate": 16.923356641044943,
            "lower": 11.640480514080206,
            "upper": 30.895452206301897,
        }
    )


def test_distribution_summary_handles_small_and_constant_samples_without_nonfinite_values() -> None:
    assert sample_moments([])["mean"] is None
    assert sample_moments([4])["standard_deviation"] is None
    constant = sample_moments([5, 5, 5, 5])
    assert constant["standard_deviation"] == 0
    assert constant["skewness"] is None
    assert constant["kurtosis_excess"] is None
    assert median_confidence_interval([5], 0.95)["computed"] is False
