"""Actual-unit mixture/process composition contracts."""

import math

import pytest

from app.statistics.bo_factor_domains import BoCategoricalFactorDomain, BoNumericFactorDomain
from app.statistics.bo_mixed_initial_design import MixedLinearConstraint
from app.statistics.bo_mixture_design import BoMixtureDesign
from app.statistics.bo_mixture_domain import BoMixtureComponent, BoMixtureDomain
from app.statistics.doe_factor_domain import DoeFactorDomain


def design(coding="lower", constraints=()):
    return BoMixtureDesign(
        BoMixtureDomain(
            (
                BoMixtureComponent("a", 0.1, 0.8, "g"),
                BoMixtureComponent("b", 0.1, 0.8, "g"),
                BoMixtureComponent("fixed", 0.1, 0.1, "g"),
            ),
            1.0,
            coding,
        ),
        (
            BoNumericFactorDomain("temp", DoeFactorDomain(10, 30, "discrete_numeric", 10)),
            BoCategoricalFactorDomain(
                "lot", "nominal", ("A", "B"), "equal_positive_correlation_v1"
            ),
        ),
        constraints,
    )


def test_actual_closure_and_process_levels_are_not_coerced():
    d = design()
    point = {"a": 0.4, "b": 0.5, "fixed": 0.1, "temp": 20.0, "lot": "A"}
    actual, encoded = d.canonical(point)
    assert actual == point
    assert encoded == pytest.approx((3 / 7, 4 / 7, 0, 0.5, 0))
    assert d.decode(encoded) == pytest.approx(point)
    for change in ({"b": 0.4}, {"temp": 21.0}, {"a": "0.4"}):
        with pytest.raises(ValueError):
            d.canonical({**point, **change})


def test_spacing_is_independent_of_model_coding_and_fixed_component():
    left = {"a": 0.4, "b": 0.5, "fixed": 0.1, "temp": 10.0, "lot": "A"}
    right = {**left, "a": 0.5, "b": 0.4, "temp": 30.0, "lot": "B"}
    assert design().distance(left, right) == pytest.approx(math.sqrt(2 + 2 / 49))
    assert design("upper").distance(left, right) == design().distance(left, right)


def test_seeded_sampler_obeys_closure_bounds_constraints_and_levels():
    constraint = MixedLinearConstraint(
        "bound", (("a", 1), ("temp", 0.01)), "less_than_or_equal", 0.65
    )
    d = design(constraints=(constraint,))
    first = d.sample(seed=7, count=12, max_attempts=200)
    assert first == d.sample(seed=7, count=12, max_attempts=200)
    assert len(first["points"]) == 12
    assert first["generation"]["policy"] == "bounded_seeded_mixture_polytope_v1"
    for point in first["points"]:
        d.canonical(point)
        assert math.fsum(point[k] for k in ("a", "b", "fixed")) == pytest.approx(1, abs=2e-15)
        assert point["temp"] in (10, 20, 30)
        assert point["a"] + point["temp"] * 0.01 <= 0.65 + 1e-12


def test_infeasible_and_sampling_budget_have_distinct_errors():
    d = design(constraints=(MixedLinearConstraint("none", (("a", 1),), "less_than_or_equal", 0),))
    with pytest.raises(ValueError, match="mixture_design_proven_infeasible"):
        d.sample(seed=1, count=2, max_attempts=10)
    with pytest.raises(ValueError, match="mixture_design_sampling_budget_exhausted"):
        design().sample(seed=1, count=12, max_attempts=1)


def test_profile_composes_constraint_interval_without_breaking_closure():
    d = design(
        constraints=(MixedLinearConstraint("bound", (("a", 1),), "less_than_or_equal", 0.6),)
    )
    holds = {"a": 0.4, "b": 0.5, "fixed": 0.1, "temp": 20.0, "lot": "A"}
    trace = d.profile(holds, "a", count=11)
    assert trace["feasible_interval"] == pytest.approx((0.1, 0.6))
    assert trace["unavailable_reason"] is None
    for point in trace["points"]:
        d.canonical(point)
        assert point["temp"] == 20 and point["lot"] == "A"
        assert point["a"] <= 0.6 + 1e-12


def test_stored_design_roundtrip_is_strict():
    d = design()
    assert BoMixtureDesign.from_payload(d.payload()) == d
    with pytest.raises(ValueError):
        BoMixtureDesign.from_payload({**d.payload(), "default": True})


def test_ordinal_process_spacing_uses_declared_rank_not_nominal_equality():
    from dataclasses import replace

    d = replace(
        design(),
        process_factors=(
            BoCategoricalFactorDomain(
                "grade", "ordinal", ("low", "middle", "high"), "ordinal_monotone_latent_rbf_v1"
            ),
        ),
    )
    left = {"a": 0.4, "b": 0.5, "fixed": 0.1, "grade": "low"}
    assert d.distance(left, {**left, "grade": "middle"}) == 0.5
    assert d.distance(left, {**left, "grade": "high"}) == 1.0
    with pytest.raises(ValueError, match="mixture_design_ordinal_rank_required"):
        d.distance(left, {**left, "grade": "high"}, ordinal_rank_distance=False)


@pytest.mark.parametrize("trimmed", [False, True])
def test_profile_preserves_decimal_component_and_trimmed_endpoints(trimmed):
    mixture = BoMixtureDomain(
        (
            BoMixtureComponent("a", 0.17, 0.45, "g"),
            BoMixtureComponent("b", 0.26, 0.93, "g"),
            BoMixtureComponent("c", 0.07, 0.30, "g"),
        ),
        1.0,
        "lower",
    )
    constraints = (
        (MixedLinearConstraint("limit", (("a", 1.0),), "less_than_or_equal", 0.43),)
        if trimmed
        else ()
    )
    d = BoMixtureDesign(mixture, (), constraints)
    holds = {"a": 0.34, "b": 0.52, "c": 0.14}
    pure = mixture.profile(holds, "a", count=21)
    trace = d.profile(holds, "a", count=21)
    assert trace["points"][-1]["a"] == (0.43 if trimmed else 0.45)
    assert trace["points"][0] == pure.points[0]
    if not trimmed:
        assert trace["points"] == list(pure.points)
    for point in trace["points"]:
        d.canonical(point)
        assert point["a"] <= (0.43 if trimmed else 0.45)


def process_design(high=1.0, *, discrete=False, constraints=()):
    return BoMixtureDesign(
        BoMixtureDomain(
            (BoMixtureComponent("a", 0, 1, "g"), BoMixtureComponent("b", 0, 1, "g")), 1, "lower"
        ),
        (
            BoNumericFactorDomain(
                "p",
                DoeFactorDomain(
                    0,
                    high,
                    "discrete_numeric" if discrete else "continuous",
                    1 if discrete else None,
                ),
            ),
        ),
        constraints,
    )


def test_conditionally_fixed_process_returns_one_exact_point():
    d = process_design(
        constraints=(MixedLinearConstraint("cap", (("p", 1), ("a", -1)), "less_than_or_equal", 0),)
    )
    holds = {"a": 0.0, "b": 1.0, "p": 0.0}
    path = d.profile(holds, "p", count=21)
    assert path["points"] == [holds]
    assert path["feasible_interval"] == [0.0, 0.0]
    assert path["unavailable_reason"] is None


@pytest.mark.parametrize(
    "available,count", [(21, 21), (100, 21), (101, 21), (10001, 21), (101, 100), (101, 2)]
)
def test_discrete_process_profiles_honor_count_and_lattice_coverage(available, count):
    d = process_design(available - 1, discrete=True)
    path = d.profile({"a": 0.4, "b": 0.6, "p": 0.0}, "p", count=count)
    values = [p["p"] for p in path["points"]]
    assert len(values) == min(available, count)
    assert len(set(values)) == len(values)
    assert values[0] == 0 and values[-1] == available - 1
    assert path["available_level_count"] == available
    assert path == d.profile({"a": 0.4, "b": 0.6, "p": 0.0}, "p", count=count)
    for point in path["points"]:
        d.canonical(point)


def test_discrete_trimmed_coverage_and_shared_two_point_minimum():
    constraints = (
        MixedLinearConstraint("lo", (("p", 1),), "greater_than_or_equal", 100.2),
        MixedLinearConstraint("hi", (("p", 1),), "less_than_or_equal", 9900.8),
    )
    d = process_design(10000, discrete=True, constraints=constraints)
    holds = {"a": 0.4, "b": 0.6, "p": 5000.0}
    path = d.profile(holds, "p", count=21)
    assert len(path["points"]) == 21
    assert path["available_level_count"] == 9800
    assert path["points"][0]["p"] == 101
    assert path["points"][-1]["p"] == 9900
    for axis in ("a", "p"):
        assert len(d.profile(holds, axis, count=2)["points"]) == 2
