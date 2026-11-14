"""Independent algebra fixtures for the pure, actual-unit mixture contract."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from math import inf, nan, nextafter, sqrt

import pytest

from app.statistics.bo_mixture_domain import (
    BoMixtureComponent,
    BoMixtureDomain,
    mixture_distance,
)


def domain(coding: str = "lower") -> BoMixtureDomain:
    return BoMixtureDomain(
        tuple(
            BoMixtureComponent(k, lo, 1.0, "fraction")
            for k, lo in (("A", 0.3), ("B", 0.4), ("C", 0.1))
        ),
        1.0,
        coding,
    )


@pytest.mark.parametrize(
    ("z", "actual"),
    [
        ((1, 0, 0), (0.5, 0.4, 0.1)),
        ((0, 1, 0), (0.3, 0.6, 0.1)),
        ((0, 0, 1), (0.3, 0.4, 0.3)),
        ((0.5, 0.5, 0), (0.4, 0.5, 0.1)),
    ],
)
def test_nist_table_55_lower_pseudocomponents(z, actual):
    # NIST pri544 Table 5.5; changing the denominator or affine base breaks this.
    d = domain()
    assert tuple(d.decode(z).values()) == pytest.approx(actual, abs=1e-15)
    assert d.encode(dict(zip(("A", "B", "C"), actual, strict=True))) == pytest.approx(z, abs=1e-15)


def test_upper_amount_units_roundtrip_and_fixed_component():
    d = BoMixtureDomain(
        (
            BoMixtureComponent("a", 10, 60, "g"),
            BoMixtureComponent("b", 20, 50, "g"),
            BoMixtureComponent("fixed", 5, 5, "g"),
        ),
        100,
        "upper",
    )
    assert d.denominator == 15
    assert d.encode({"a": 55, "b": 40, "fixed": 5}) == pytest.approx((1 / 3, 2 / 3, 0))
    assert d.decode((1 / 3, 2 / 3, 0)) == pytest.approx({"a": 55, "b": 40, "fixed": 5})
    assert d.metric_coordinates({"a": 55, "b": 40, "fixed": 5}) == pytest.approx((0.9, 2 / 3, 0))
    with pytest.raises(FrozenInstanceError):
        d.total = 10


def test_upper_coding_preserves_exact_declared_boundaries_on_roundtrip():
    d = domain("upper")
    original = {"A": 0.5, "B": 0.4, "C": 0.1}
    restored = d.decode(d.encode(original))
    assert restored == original


def test_representable_small_denominator_avoids_intermediate_sum_cancellation():
    d = BoMixtureDomain(
        (BoMixtureComponent("A", 0.5, 1, "u"), BoMixtureComponent("B", 0.4999999999999, 1, "u")),
        1,
        "lower",
    )
    original = {"A": 0.5, "B": 0.5}
    assert d.decode(d.encode(original)) == original


def test_roundoff_tolerated_actual_closure_is_not_rescaled_in_small_domain():
    d = BoMixtureDomain(
        (BoMixtureComponent("A", 0.5, 1, "u"), BoMixtureComponent("B", 0.4999999999999, 1, "u")),
        1,
        "lower",
    )
    original = {"A": 0.5, "B": nextafter(0.5, 1)}
    assert d.validate_actual(original) == tuple(original.values())
    assert d.decode(d.encode(original)) == original


def test_upper_profile_asymmetric_deficits_intersects_other_lower_bounds():
    d = BoMixtureDomain(tuple(BoMixtureComponent(k, 0, 1, "u") for k in "ABC"), 1, "upper")
    trace = d.profile({"A": 0.5, "B": 0.3, "C": 0.2}, "A", count=3)
    # Other deficits 0.7:0.8; C reaches zero at A=0.875.
    assert trace.feasible_low == 0
    assert trace.feasible_high == pytest.approx(0.875, abs=1e-15)
    assert trace.points[-1] == pytest.approx({"A": 0.875, "B": 0.125, "C": 0}, abs=1e-15)
    for point in trace.points:
        assert (1 - point["B"]) * 0.8 == pytest.approx((1 - point["C"]) * 0.7, abs=1e-15)


def test_auto_coding_tie_and_actual_distance_are_independent_of_model_coding():
    low = domain()
    up = domain("upper")
    assert domain("auto").effective_coding == "lower"
    tie = BoMixtureDomain(
        (BoMixtureComponent("a", 0, 1, "u"), BoMixtureComponent("b", 0, 1, "u")), 1, "auto"
    )
    assert tie.effective_coding == "lower"
    upper = BoMixtureDomain(tie.components, 1.8, "auto")
    assert upper.effective_coding == "upper"
    left, right = {"A": 0.5, "B": 0.4, "C": 0.1}, {"A": 0.3, "B": 0.6, "C": 0.1}
    expected = sqrt((0.2 / 0.7) ** 2 + (0.2 / 0.6) ** 2)
    assert mixture_distance(low, left, right) == pytest.approx(expected, abs=1e-15)
    assert mixture_distance(up, left, right) == pytest.approx(expected, abs=1e-15)


@pytest.mark.parametrize("value", [True, "1", nan, inf, -inf])
def test_non_numeric_or_nonfinite_values_rejected_without_coercion(value):
    with pytest.raises(ValueError):
        BoMixtureComponent("x", value, 2, "u")
    with pytest.raises(ValueError):
        BoMixtureDomain(domain().components, value, "lower")
    with pytest.raises(ValueError):
        domain().validate_actual({"A": value, "B": 0.4, "C": 0.1})
    with pytest.raises(ValueError):
        domain().decode((value, 0, 0))


@pytest.mark.parametrize(
    "point",
    [
        {"A": 0.5, "B": 0.4},
        {"A": 0.5, "B": 0.4, "C": 0.1, "extra": 0},
        {"A": 0.2, "B": 0.7, "C": 0.1},
        {"A": 0.5, "B": 0.5, "C": 0.1},
        {"A": 0.3 - 1e-16, "B": 0.6 + 1e-16, "C": 0.1},
    ],
)
def test_actual_requires_exact_ids_strict_bounds_and_closure(point):
    before = deepcopy(point)
    with pytest.raises(ValueError):
        domain().validate_actual(point)
    assert point == before


def test_valid_actual_keeps_order_and_supplied_values_without_normalization():
    point = {"C": 0.1, "A": 0.4, "B": 0.5}
    before = point.copy()
    assert domain().validate_actual(point) == (0.4, 0.5, 0.1)
    domain().encode(point)
    assert point == before


@pytest.mark.parametrize(
    "components,total,coding",
    [
        ((BoMixtureComponent("x", 0, 1, "u"),), 1, "lower"),
        ((BoMixtureComponent("x", 0, 1, "u"),) * 2, 1, "lower"),
        ((BoMixtureComponent("x", 0, 1, "u"), BoMixtureComponent("y", 0, 1, "v")), 1, "lower"),
        ((BoMixtureComponent("x", 0.5, 1, "u"), BoMixtureComponent("y", 0.5, 1, "u")), 1, "lower"),
        ((BoMixtureComponent("x", 0, 0.5, "u"), BoMixtureComponent("y", 0, 0.5, "u")), 1, "lower"),
        (
            (BoMixtureComponent("x", 0.5, 1, "u"), BoMixtureComponent("y", 0.5 - 1e-16, 1, "u")),
            1,
            "lower",
        ),
        (
            (BoMixtureComponent("x", 0, 1e308, "u"), BoMixtureComponent("y", 0, 1e308, "u")),
            1e308,
            "lower",
        ),
        ((BoMixtureComponent("x", 0, 1, "u"), BoMixtureComponent("y", 0, 1, "u")), 1, "bogus"),
        (
            (BoMixtureComponent("x", 0.2, 0.2, "u"), BoMixtureComponent("y", 0, 1, "u")),
            0.5,
            "lower",
        ),
    ],
)
def test_invalid_or_unrepresentable_domain_rejected(components, total, coding):
    with pytest.raises(ValueError):
        BoMixtureDomain(components, total, coding)


@pytest.mark.parametrize(
    "factor_id,low,high,unit",
    [
        ("", 0, 1, "u"),
        ("a", -1, 1, "u"),
        ("a", 2, 1, "u"),
        ("a", 0, 1, ""),
    ],
)
def test_component_validation(factor_id, low, high, unit):
    with pytest.raises(ValueError):
        BoMixtureComponent(factor_id, low, high, unit)


def test_full_case_sensitive_identifiers_and_snapshot_integrity():
    d = BoMixtureDomain(
        (BoMixtureComponent("A" * 300, 0, 1, "u"), BoMixtureComponent("a" * 300, 0, 1, "u")),
        1,
        "auto",
    )
    payload = d.payload()
    restored = BoMixtureDomain.from_payload(payload)
    assert restored == d
    for key in payload:
        changed = deepcopy(payload)
        del changed[key]
        with pytest.raises(ValueError):
            BoMixtureDomain.from_payload(changed)
    for key, value in [
        ("denominator", 0.5),
        ("effective_coding", "upper"),
        ("affine_basis", [0, 0.1]),
        ("extra", 1),
    ]:
        changed = deepcopy(payload)
        changed[key] = value
        with pytest.raises(ValueError):
            BoMixtureDomain.from_payload(changed)
    altered = deepcopy(payload)
    altered["components"][0]["extra"] = 1
    with pytest.raises(ValueError):
        BoMixtureDomain.from_payload(altered)


@pytest.mark.parametrize("coding", ["lower", "upper"])
def test_profile_preserves_closure_bounds_ratios_and_original_center(coding):
    d = BoMixtureDomain(tuple(BoMixtureComponent(k, 0, 1, "u") for k in "ABC"), 1, coding)
    holds = (
        {"A": 0.5, "B": 0.3, "C": 0.2} if coding == "lower" else {"A": 0.5, "B": 0.25, "C": 0.25}
    )
    before = holds.copy()
    trace = d.profile(holds, "A", count=5)
    assert trace.unavailable_reason is None
    assert trace.balancing_rule == (
        "excess_above_lower" if coding == "lower" else "deficit_below_upper"
    )
    assert trace.feasible_low == pytest.approx(0)
    assert trace.feasible_high == pytest.approx(1)
    assert trace.points[0]["A"] == pytest.approx(0)
    assert trace.points[-1]["A"] == pytest.approx(1)
    assert trace.points[2] == holds
    for point in trace.points:
        assert sum(point.values()) == pytest.approx(1, abs=2e-15)
        assert all(0 <= v <= 1 for v in point.values())
        if coding == "lower":
            assert point["B"] * 0.2 == pytest.approx(point["C"] * 0.3, abs=1e-15)
        else:
            assert 1 - point["B"] == pytest.approx(1 - point["C"], abs=1e-15)
    assert holds == before


def test_profile_intersects_compensating_bounds():
    d = BoMixtureDomain(
        (
            BoMixtureComponent("A", 0, 1, "u"),
            BoMixtureComponent("B", 0.1, 0.4, "u"),
            BoMixtureComponent("C", 0, 1, "u"),
        ),
        1,
        "lower",
    )
    trace = d.profile({"A": 0.5, "B": 0.3, "C": 0.2}, "A", count=3)
    # Excess B:C = .2:.2; B<=.4 means A>=.3.
    assert trace.feasible_low == pytest.approx(0.3, abs=1e-15)
    assert trace.feasible_high == pytest.approx(0.9, abs=1e-15)


def test_profile_unavailable_instead_of_inventing_equal_balance():
    trace = domain().profile({"A": 0.5, "B": 0.4, "C": 0.1}, "A")
    assert trace.unavailable_reason == "zero_balancing_mass"
    assert trace.points == ()
    fixed = BoMixtureDomain(
        (
            BoMixtureComponent("A", 0.2, 0.2, "u"),
            BoMixtureComponent("B", 0, 1, "u"),
            BoMixtureComponent("C", 0, 1, "u"),
        ),
        1,
        "lower",
    )
    assert (
        fixed.profile({"A": 0.2, "B": 0.4, "C": 0.4}, "A").unavailable_reason == "fixed_component"
    )


@pytest.mark.parametrize("count", [True, 2, 101, 3.5])
def test_profile_rejects_invalid_count(count):
    with pytest.raises(ValueError):
        domain().profile({"A": 0.4, "B": 0.45, "C": 0.15}, "A", count)


def test_decode_rejects_nonclosure_wrong_dimension_and_infeasible_encoded_point():
    for encoded in [(0, 0, 0), (1, 0), (1.1, -0.1, 0), "100"]:
        with pytest.raises(ValueError):
            domain().decode(encoded)
    with pytest.raises(ValueError):
        domain().profile({"A": 0.4, "B": 0.45, "C": 0.15}, "process")
