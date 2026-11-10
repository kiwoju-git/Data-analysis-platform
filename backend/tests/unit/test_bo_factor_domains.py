from __future__ import annotations

import copy
import json

import pytest

from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoNumericFactorDomain,
    bo_factor_domains_from_payload,
    bo_factor_domains_to_payload,
    decode_bo_point,
    encode_bo_point,
    validate_bo_factor_domains,
)
from app.statistics.doe_factor_domain import DoeFactorDomain

EQUAL = "equal_positive_correlation_v1"
UNEQUAL = "unequal_hyperspherical_correlation_v1"
LATENT = "ordinal_monotone_latent_rbf_v1"


def _factors():
    return (
        BoNumericFactorDomain("temperature", DoeFactorDomain(10.0, 20.0)),
        BoNumericFactorDomain("count", DoeFactorDomain(0.0, 4.0, "discrete_numeric", 2.0)),
        BoCategoricalFactorDomain("material", "nominal", ("01", "1", " 1 "), EQUAL),
        BoCategoricalFactorDomain("grade", "ordinal", ("low", "medium", "high"), LATENT),
    )


def test_exact_level_identities_and_declared_order_round_trip():
    factors = _factors()
    point = {"temperature": 12.5, "count": 2.0, "material": " 1 ", "grade": "medium"}
    encoded = encode_bo_point(factors, point)
    assert encoded == (0.25, 0.5, 2.0, 1.0)
    assert decode_bo_point(factors, encoded) == point
    payload = bo_factor_domains_to_payload(factors)
    original = copy.deepcopy(payload)
    restored = bo_factor_domains_from_payload(json.loads(json.dumps(payload, allow_nan=False)))
    assert restored == factors
    assert payload == original


def test_long_and_non_ascii_category_identity_is_not_truncated_or_normalized():
    prefix = "X" * 121
    levels = (prefix + "-A", prefix + "-B", "\ud55c\uae00", "e\u0301", "\u00e9")
    domain = BoCategoricalFactorDomain("category", "nominal", levels, EQUAL)
    assert [domain.encode(value) for value in levels] == list(range(5))
    assert [domain.decode(float(index)) for index in range(5)] == list(levels)


@pytest.mark.parametrize("value", [1, 1.0, True, None, "unknown"])
def test_category_never_coerces_numeric_value_to_string(value):
    domain = _factors()[2]
    with pytest.raises(ValueError, match="bayesian_category_"):
        domain.encode(value)


@pytest.mark.parametrize("value", ["", " ", "1e", "1", True, float("inf"), float("nan")])
def test_numeric_point_requires_finite_numeric_value(value):
    with pytest.raises(ValueError):
        _factors()[0].encode(value)


def test_discrete_grid_is_not_rounded_to_an_executable_value():
    with pytest.raises(ValueError, match="not_executable"):
        _factors()[1].encode(1.0)
    with pytest.raises(ValueError, match="not_executable"):
        _factors()[1].decode(0.25)


@pytest.mark.parametrize("low,high,value", [(-1.0, 1.0, 0.3), (1000.0, 1001.0, 1000.1)])
def test_discrete_decimal_level_round_trip_preserves_canonical_identity(low, high, value):
    factors = (BoNumericFactorDomain("x", DoeFactorDomain(low, high, "discrete_numeric", 0.1)),)
    restored = bo_factor_domains_from_payload(
        json.loads(json.dumps(bo_factor_domains_to_payload(factors), allow_nan=False))
    )
    decoded = decode_bo_point(restored, encode_bo_point(factors, {"x": value}))
    assert decoded == {"x": value}
    assert json.dumps(decoded) == json.dumps({"x": value})
    assert encode_bo_point(restored, decoded) == encode_bo_point(factors, {"x": value})


@pytest.mark.parametrize("code", [-1, 0.5, 3, True, "1", float("nan")])
def test_category_code_must_be_known_integer(code):
    with pytest.raises(ValueError):
        _factors()[2].decode(code)


@pytest.mark.parametrize(
    "levels", [("only",), ("same", "same"), ("", "a"), tuple(str(i) for i in range(33)), ["a", "b"]]
)
def test_invalid_or_degenerate_declared_levels_rejected(levels):
    with pytest.raises(ValueError):
        BoCategoricalFactorDomain("category", "nominal", levels, EQUAL)


def test_ordinal_latent_requires_explicit_order_not_sorted_from_labels():
    domain = BoCategoricalFactorDomain("grade", "ordinal", ("z", "a", "m"), LATENT)
    assert domain.encode("z") == 0
    assert domain.encode("a") == 1
    with pytest.raises(ValueError, match="declared_order"):
        BoCategoricalFactorDomain("grade", "nominal", ("z", "a", "m"), LATENT)


def test_level_and_parameter_resource_limits_are_explicit():
    with pytest.raises(ValueError, match="level_limit"):
        BoCategoricalFactorDomain("factor", "nominal", tuple(map(str, range(9))), UNEQUAL)
    factors = tuple(
        BoCategoricalFactorDomain(str(index), "nominal", tuple(map(str, range(8))), UNEQUAL)
        for index in range(3)
    )
    with pytest.raises(ValueError, match="parameter_budget"):
        validate_bo_factor_domains(factors)


def test_full_factor_keys_required_and_duplicate_factor_identity_rejected():
    factors = _factors()
    with pytest.raises(ValueError, match="identity_mismatch"):
        encode_bo_point(factors, {"temperature": 12})
    with pytest.raises(ValueError, match="identity_duplicate"):
        validate_bo_factor_domains((factors[0], factors[0]))


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value.update(schema_version=True),
        lambda value: value.update(unexpected="field"),
        lambda value: value["factors"][0].update(unexpected="field"),
        lambda value: value["factors"][2].update(levels=["same", "same"]),
        lambda value: value["factors"][2].update(kind={}),
    ],
)
def test_strict_versioned_domain_payload(change):
    payload = bo_factor_domains_to_payload(_factors())
    change(payload)
    with pytest.raises(ValueError):
        bo_factor_domains_from_payload(payload)
