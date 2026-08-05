from __future__ import annotations

import pytest

from app.statistics.doe_factor_domain import (
    DoeFactorDomain,
    DoeFactorDomainError,
    validate_factor_domain,
)
from app.statistics.factorial_design import (
    FactorialDesignError,
    FactorialDesignOptions,
    FactorialFactor,
    generate_two_level_full_factorial_design,
)
from app.statistics.latin_hypercube import (
    LatinHypercubeFactor,
    LatinHypercubeOptions,
    generate_latin_hypercube_design,
)


def test_decimal_factor_domain_requires_high_on_grid() -> None:
    domain = DoeFactorDomain(0.0, 1.0, "discrete_numeric", 0.1)
    validate_factor_domain(domain)
    assert domain.level_count == 11
    assert domain.levels()[-1] == pytest.approx(1.0)

    with pytest.raises(DoeFactorDomainError, match="doe_factor_high_not_on_grid"):
        validate_factor_domain(DoeFactorDomain(0.0, 1.0, "discrete_numeric", 0.3))


def test_factorial_rejects_non_executable_center_point() -> None:
    factors = [
        FactorialFactor("day", 1.0, 10.0, "day", "discrete_numeric", 1.0, 0),
        FactorialFactor("temperature", 20.0, 40.0),
    ]
    with pytest.raises(FactorialDesignError) as raised:
        generate_two_level_full_factorial_design(
            factors,
            FactorialDesignOptions(1, 1, False, 1),
        )
    assert raised.value.code == "doe_factorial_center_not_executable"


def test_mixed_lhs_uses_balanced_executable_levels_without_duplicates() -> None:
    factors = [
        LatinHypercubeFactor("day", 1.0, 10.0, "day", "discrete_numeric", 1.0, 0),
        LatinHypercubeFactor("temperature", 20.0, 80.0, "C"),
    ]
    options = LatinHypercubeOptions(17, 20260805, True, 20260806, "random_cd")
    first = generate_latin_hypercube_design(factors, options)
    second = generate_latin_hypercube_design(factors, options)

    assert first.design_sha256 == second.design_sha256
    assert len(first.runs) == 17
    days = [run.factor_levels["day"] for run in first.runs]
    assert all(value == int(value) and 1 <= value <= 10 for value in days)
    counts = first.quality.discrete_level_balance
    assert counts is not None
    assert max(counts["day"]) - min(counts["day"]) <= 1
    assert first.quality.duplicate_count == 0
    assert first.quality.executable_point_count == 17
    assert len({tuple(run.factor_levels.values()) for run in first.runs}) == 17
