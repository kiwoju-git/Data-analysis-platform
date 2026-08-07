import numpy as np
import pytest

from app.statistics.sample_quantiles import sample_quantile_hf6, sample_quartiles_hf6


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([2, 3, 5, 7], (2.25, 6.5)),
        ([7, 9, 16, 36, 39, 45, 45, 46, 48, 51], (14.25, 46.5)),
        ([5], (5.0, 5.0)),
        ([1, 2], (1.0, 2.0)),
        ([1, 2, 3], (1.0, 3.0)),
        ([1, 1, 1, 2], (1.0, 1.75)),
    ],
)
def test_hf6_quartiles_match_reference(values: list[float], expected: tuple[float, float]) -> None:
    assert sample_quartiles_hf6(values) == pytest.approx(expected)
    assert sample_quartiles_hf6(values) == pytest.approx(
        np.quantile(values, [0.25, 0.75], method="weibull")
    )


def test_hf6_boundaries_and_invalid_probability() -> None:
    values = [2, 3, 5, 7]
    assert sample_quantile_hf6(values, 0) == 2
    assert sample_quantile_hf6(values, 1) == 7
    assert sample_quantile_hf6([], 0.5) is None
    with pytest.raises(ValueError):
        sample_quantile_hf6(values, -0.1)
