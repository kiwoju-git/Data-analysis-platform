import copy

import pytest

from app.statistics.bo_factor_domains import BoCategoricalFactorDomain, BoNumericFactorDomain
from app.statistics.bo_mixed_initial_design import (
    MixedLinearConstraint,
    generate_mixed_initial_design,
    mixed_constraints_satisfied,
)
from app.statistics.doe_factor_domain import DoeFactorDomain


def domains():
    return (
        BoNumericFactorDomain("x", DoeFactorDomain(1000.1, 1000.3, "discrete_numeric", 0.1, 1)),
        BoCategoricalFactorDomain(
            "material", "nominal", ("1", "10", "한글 긴 이름"), "equal_positive_correlation_v1"
        ),
        BoCategoricalFactorDomain(
            "grade", "ordinal", ("low", "medium", "high"), "ordinal_monotone_latent_rbf_v1"
        ),
    )


def test_uniform_design_is_reproducible_executable_and_preserves_full_labels():
    left = generate_mixed_initial_design(domains(), [], seed=31, size=12)
    right = generate_mixed_initial_design(domains(), [], seed=31, size=12)
    assert left == right
    assert left.metadata["policy"] == "sha256_counter_mixed_uniform_feasible_v1"
    assert len({tuple(point.values()) for point in left.actual_points}) == 12
    assert {point["x"] for point in left.actual_points} <= {1000.1, 1000.2, 1000.3}
    for actual, encoded in zip(left.actual_points, left.encoded_points, strict=True):
        assert domains()[1].levels[int(encoded["material"])] == actual["material"]
        assert domains()[2].levels[int(encoded["grade"])] == actual["grade"]
        assert 0 <= encoded["x"] <= 1
    assert sum(left.metadata["category_level_counts"]["material"]) == 12
    assert left.metadata["attempts_consumed"] <= 12_000


def test_constraints_never_treat_category_index_as_numeric_coefficient():
    constraint = MixedLinearConstraint("cap", (("x", 1.0),), "less_than_or_equal", 1000.2)
    design = generate_mixed_initial_design(domains(), [constraint], seed=3, size=10)
    assert all(point["x"] <= 1000.2 for point in design.actual_points)
    assert all(mixed_constraints_satisfied(point, [constraint]) for point in design.actual_points)
    with pytest.raises(ValueError, match="requires_numeric_factor"):
        generate_mixed_initial_design(
            domains(),
            [MixedLinearConstraint("bad", (("material", 1.0),), "less_than_or_equal", 1.0)],
            seed=3,
            size=10,
        )


def test_all_categorical_bounded_uniqueness_and_explicit_incomplete_coverage():
    one = (
        BoCategoricalFactorDomain(
            "category",
            "nominal",
            tuple(f"level {i}" for i in range(32)),
            "equal_positive_correlation_v1",
        ),
    )
    result = generate_mixed_initial_design(one, [], seed=1, size=2)
    assert result.metadata["warnings"] == ["bayesian_initial_category_levels_uncovered"]
    assert len(result.metadata["unobserved_level_indices"]["category"]) == 30
    with pytest.raises(ValueError, match="unique_space_exhausted"):
        generate_mixed_initial_design(domains()[1:2], [], seed=1, size=4)


def test_infeasible_design_does_not_return_partial_conditions():
    impossible = MixedLinearConstraint("cap", (("x", 1.0),), "less_than_or_equal", 0.0)
    with pytest.raises(ValueError, match="feasible_budget_exhausted"):
        generate_mixed_initial_design(domains(), [impossible], seed=1, size=4)


def test_continuous_sampling_and_input_immutability():
    factors = (BoNumericFactorDomain("x", DoeFactorDomain(-5.0, 5.0)), domains()[1])
    before = copy.deepcopy(factors)
    design = generate_mixed_initial_design(factors, [], seed=5, size=8)
    assert factors == before
    assert all(-5 <= row["x"] <= 5 for row in design.actual_points)
    assert (
        generate_mixed_initial_design(factors, [], seed=6, size=8).actual_points
        != design.actual_points
    )


@pytest.mark.parametrize(
    "seed,size", [(True, 8), (1.5, 8), (-1, 8), (2**31, 8), (0, 3), (0, 65), (0, 4.5)]
)
def test_invalid_size_and_seed_rejected(seed, size):
    with pytest.raises(ValueError):
        generate_mixed_initial_design(domains(), [], seed=seed, size=size)
