import numpy as np
import pytest

from app.statistics.latin_hypercube import (
    LatinHypercubeError,
    LatinHypercubeFactor,
    LatinHypercubeOptions,
    generate_latin_hypercube_design,
)


def _options(*, seed: int = 17, randomize: bool = True):
    return LatinHypercubeOptions(
        run_count=10,
        seed=seed,
        randomize_run_order=randomize,
        run_order_seed=29,
        optimization="random_cd",
    )


def test_latin_hypercube_is_reproducible_stratified_and_bounded() -> None:
    factors = [
        LatinHypercubeFactor("temperature", 20.0, 80.0, "C"),
        LatinHypercubeFactor("time", 1.0, 5.0, "min"),
        LatinHypercubeFactor("ratio", 0.1, 0.9),
    ]

    first = generate_latin_hypercube_design(factors, _options())
    second = generate_latin_hypercube_design(factors, _options())

    assert first == second
    assert first.quality.strata_valid is True
    assert first.quality.minimum_pairwise_distance > 0
    assert np.isfinite(first.quality.centered_discrepancy)
    assert sorted(item.run_order for item in first.runs) == list(range(1, 11))
    for run in first.runs:
        assert 20 <= run.factor_levels["temperature"] <= 80
        assert 1 <= run.factor_levels["time"] <= 5
        assert all(0 <= value < 1 for value in run.normalized_levels.values())
    assert all(
        occupancy == tuple(range(10)) for occupancy in first.quality.per_factor_strata_occupancy
    )


def test_latin_hypercube_seed_and_run_order_policies_are_explicit() -> None:
    factors = [LatinHypercubeFactor("x", -1.0, 1.0)]
    first = generate_latin_hypercube_design(factors, _options(seed=1))
    second = generate_latin_hypercube_design(factors, _options(seed=2))
    ordered = generate_latin_hypercube_design(factors, _options(randomize=False))

    assert first.design_sha256 != second.design_sha256
    assert [item.run_order for item in ordered.runs] == list(range(1, 11))


@pytest.mark.parametrize(
    ("factors", "options", "code"),
    [
        ([], _options(), "lhs_factor_count_invalid"),
        (
            [LatinHypercubeFactor("x", 1.0, 1.0)],
            _options(),
            "lhs_factor_bounds_invalid",
        ),
        (
            [LatinHypercubeFactor("x", 0.0, float("inf"))],
            _options(),
            "lhs_factor_bounds_invalid",
        ),
        (
            [LatinHypercubeFactor("x", 0.0, 1.0)],
            LatinHypercubeOptions(1, 1, False, 1),
            "lhs_run_count_invalid",
        ),
    ],
)
def test_latin_hypercube_rejects_invalid_designs(
    factors: list[LatinHypercubeFactor],
    options: LatinHypercubeOptions,
    code: str,
) -> None:
    with pytest.raises(LatinHypercubeError, match=code):
        generate_latin_hypercube_design(factors, options)
