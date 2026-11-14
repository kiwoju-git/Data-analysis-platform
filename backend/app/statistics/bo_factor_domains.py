"""Explicit BO factor identities; categorical codes are lookup indices, not distances."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from app.statistics.doe_factor_domain import DoeFactorDomain, validate_factor_domain

BoCorrelationPolicy = Literal[
    "equal_positive_correlation_v1",
    "unequal_hyperspherical_correlation_v1",
    "ordinal_monotone_latent_rbf_v1",
]
BoFactorValue = float | str
MAX_BO_FACTORS = 10
MAX_BO_CATEGORY_LEVELS = 32
MAX_BO_UNEQUAL_LEVELS = 8
MAX_BO_CATEGORY_PARAMETERS = 64


def _invalid(code: str = "bayesian_factor_domain_invalid") -> ValueError:
    return ValueError(code)


def _identity(value: Any, *, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise _invalid()
    return value


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _invalid()
    try:
        number = float(value)
    except OverflowError as exc:
        raise _invalid() from exc
    if not math.isfinite(number):
        raise _invalid()
    return number


@dataclass(frozen=True)
class BoNumericFactorDomain:
    factor_id: str
    domain: DoeFactorDomain

    def __post_init__(self) -> None:
        _identity(self.factor_id, maximum=128)
        if not isinstance(self.domain, DoeFactorDomain):
            raise _invalid()
        _number(self.domain.low)
        _number(self.domain.high)
        if self.domain.step is not None:
            _number(self.domain.step)
        if (
            self.domain.display_decimals is not None
            and type(self.domain.display_decimals) is not int
        ):
            raise _invalid()
        validate_factor_domain(self.domain)
        if not math.isfinite(self.domain.high - self.domain.low):
            raise _invalid()

    def encode(self, value: Any) -> float:
        number = _number(value)
        if not self.domain.is_executable(number):
            raise _invalid("bayesian_factor_value_not_executable")
        return self.domain.normalized(self._canonical_value(number))

    def decode(self, encoded: Any) -> float:
        number = _number(encoded)
        if not 0 <= number <= 1:
            raise _invalid("bayesian_factor_value_not_executable")
        value = self.domain.low + number * (self.domain.high - self.domain.low)
        if not self.domain.is_executable(value):
            raise _invalid("bayesian_factor_value_not_executable")
        return self._canonical_value(value)

    def _canonical_value(self, value: float) -> float:
        if self.domain.domain_kind == "continuous":
            return value
        assert self.domain.step is not None
        # Called only after grid validation: preserve the executable level's
        # identity, not a reconstruction carrying binary arithmetic residue.
        low, step = Decimal(str(self.domain.low)), Decimal(str(self.domain.step))
        index = ((Decimal(str(value)) - low) / step).to_integral_value()
        return float(low + index * step)


@dataclass(frozen=True)
class BoPseudocomponentFactorDomain(BoNumericFactorDomain):
    """Already-coded affine coordinate, not an independently normalized factor."""

    encoded_high: float
    transform_sha256: str

    def __post_init__(self) -> None:
        super().__post_init__()
        if (
            self.domain != DoeFactorDomain(0.0, 1.0)
            or _number(self.encoded_high) < 0
            or type(self.transform_sha256) is not str
            or len(self.transform_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.transform_sha256)
        ):
            raise _invalid("bayesian_pseudocomponent_domain_invalid")

    def encode(self, value: Any) -> float:
        number = _number(value)
        if not 0 <= number <= self.encoded_high:
            raise _invalid("bayesian_factor_value_not_executable")
        return number

    def decode(self, encoded: Any) -> float:
        return self.encode(encoded)


@dataclass(frozen=True)
class BoCategoricalFactorDomain:
    factor_id: str
    kind: Literal["nominal", "ordinal"]
    levels: tuple[str, ...]
    correlation_policy: BoCorrelationPolicy

    def __post_init__(self) -> None:
        _identity(self.factor_id, maximum=128)
        if (
            not isinstance(self.kind, str)
            or self.kind not in {"nominal", "ordinal"}
            or not isinstance(self.levels, tuple)
        ):
            raise _invalid()
        if not 2 <= len(self.levels) <= MAX_BO_CATEGORY_LEVELS:
            raise _invalid("bayesian_category_level_count_invalid")
        for value in self.levels:
            _identity(value, maximum=1024)
        if len(set(self.levels)) != len(self.levels):
            raise _invalid("bayesian_category_levels_duplicate")
        if not isinstance(self.correlation_policy, str) or self.correlation_policy not in {
            "equal_positive_correlation_v1",
            "unequal_hyperspherical_correlation_v1",
            "ordinal_monotone_latent_rbf_v1",
        }:
            raise _invalid("bayesian_category_correlation_policy_invalid")
        if self.correlation_policy == "unequal_hyperspherical_correlation_v1":
            if len(self.levels) > MAX_BO_UNEQUAL_LEVELS:
                raise _invalid("bayesian_unequal_correlation_level_limit")
        if self.correlation_policy == "ordinal_monotone_latent_rbf_v1" and self.kind != "ordinal":
            raise _invalid("bayesian_ordinal_policy_requires_declared_order")

    @property
    def parameter_count(self) -> int:
        return category_parameter_count(self.correlation_policy, len(self.levels))

    def encode(self, value: Any) -> float:
        if not isinstance(value, str):
            raise _invalid("bayesian_category_value_invalid")
        try:
            return float(self.levels.index(value))
        except ValueError as exc:
            raise _invalid("bayesian_category_level_unknown") from exc

    def decode(self, encoded: Any) -> str:
        number = _number(encoded)
        if not number.is_integer() or not 0 <= number < len(self.levels):
            raise _invalid("bayesian_category_code_invalid")
        return self.levels[int(number)]


BoFactorDomain = BoNumericFactorDomain | BoCategoricalFactorDomain


def category_parameter_count(policy: BoCorrelationPolicy, level_count: int) -> int:
    if type(level_count) is not int or not 2 <= level_count <= MAX_BO_CATEGORY_LEVELS:
        raise _invalid("bayesian_category_level_count_invalid")
    if policy == "equal_positive_correlation_v1":
        return 1
    if policy == "ordinal_monotone_latent_rbf_v1":
        return level_count - 1
    if policy == "unequal_hyperspherical_correlation_v1" and level_count <= MAX_BO_UNEQUAL_LEVELS:
        return level_count * (level_count - 1) // 2
    raise _invalid("bayesian_category_correlation_policy_invalid")


def validate_bo_factor_domains(factors: Sequence[BoFactorDomain]) -> None:
    if not 1 <= len(factors) <= MAX_BO_FACTORS:
        raise _invalid("bayesian_factor_count_invalid")
    if any(
        not isinstance(factor, BoNumericFactorDomain | BoCategoricalFactorDomain)
        for factor in factors
    ):
        raise _invalid()
    if len({factor.factor_id for factor in factors}) != len(factors):
        raise _invalid("bayesian_factor_identity_duplicate")
    if (
        sum(
            factor.parameter_count
            for factor in factors
            if isinstance(factor, BoCategoricalFactorDomain)
        )
        > MAX_BO_CATEGORY_PARAMETERS
    ):
        raise _invalid("bayesian_category_parameter_budget_exceeded")


def encode_bo_point(
    factors: Sequence[BoFactorDomain], point: Mapping[str, Any]
) -> tuple[float, ...]:
    validate_bo_factor_domains(factors)
    if not isinstance(point, Mapping) or set(point) != {factor.factor_id for factor in factors}:
        raise _invalid("bayesian_point_factor_identity_mismatch")
    return tuple(factor.encode(point[factor.factor_id]) for factor in factors)


def decode_bo_point(
    factors: Sequence[BoFactorDomain], encoded: Sequence[Any]
) -> dict[str, BoFactorValue]:
    validate_bo_factor_domains(factors)
    if not isinstance(encoded, list | tuple) or len(encoded) != len(factors):
        raise _invalid("bayesian_point_shape_invalid")
    return {
        factor.factor_id: factor.decode(value)
        for factor, value in zip(factors, encoded, strict=True)
    }


def bo_factor_domains_to_payload(factors: Sequence[BoFactorDomain]) -> dict[str, Any]:
    validate_bo_factor_domains(factors)
    items: list[dict[str, Any]] = []
    for factor in factors:
        if isinstance(factor, BoPseudocomponentFactorDomain):
            items.append(
                {
                    "factor_id": factor.factor_id,
                    "kind": "mixture_pseudocomponent",
                    "encoded_high": factor.encoded_high,
                    "transform_sha256": factor.transform_sha256,
                }
            )
        elif isinstance(factor, BoNumericFactorDomain):
            items.append(
                {
                    "factor_id": factor.factor_id,
                    "kind": factor.domain.domain_kind,
                    "low": factor.domain.low,
                    "high": factor.domain.high,
                    "step": factor.domain.step,
                    "display_decimals": factor.domain.display_decimals,
                }
            )
        else:
            items.append(
                {
                    "factor_id": factor.factor_id,
                    "kind": factor.kind,
                    "levels": list(factor.levels),
                    "correlation_policy": factor.correlation_policy,
                }
            )
    mixture = any(isinstance(f, BoPseudocomponentFactorDomain) for f in factors)
    return {
        "schema_version": 2 if mixture else 1,
        "encoding_policy": "mixture_pseudocomponents_process_v1"
        if mixture
        else "numeric_normalized_category_index_v1",
        "factors": items,
    }


def bo_factor_domains_from_payload(payload: Any) -> tuple[BoFactorDomain, ...]:
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "encoding_policy", "factors"}
        or type(payload["schema_version"]) is not int
        or (payload["schema_version"], payload["encoding_policy"])
        not in {
            (1, "numeric_normalized_category_index_v1"),
            (2, "mixture_pseudocomponents_process_v1"),
        }
        or not isinstance(payload["factors"], list)
        or not 1 <= len(payload["factors"]) <= MAX_BO_FACTORS
    ):
        raise _invalid("bayesian_factor_domain_payload_invalid")
    factors: list[BoFactorDomain] = []
    for item in payload["factors"]:
        if not isinstance(item, dict):
            raise _invalid("bayesian_factor_domain_payload_invalid")
        if not isinstance(item.get("kind"), str):
            raise _invalid("bayesian_factor_domain_payload_invalid")
        if item["kind"] == "mixture_pseudocomponent":
            if payload["schema_version"] != 2 or set(item) != {
                "factor_id",
                "kind",
                "encoded_high",
                "transform_sha256",
            }:
                raise _invalid("bayesian_factor_domain_payload_invalid")
            factors.append(
                BoPseudocomponentFactorDomain(
                    item["factor_id"],
                    DoeFactorDomain(0.0, 1.0),
                    item["encoded_high"],
                    item["transform_sha256"],
                )
            )
        elif item["kind"] in {"nominal", "ordinal"}:
            if set(item) != {"factor_id", "kind", "levels", "correlation_policy"} or not isinstance(
                item["levels"], list
            ):
                raise _invalid("bayesian_factor_domain_payload_invalid")
            factors.append(
                BoCategoricalFactorDomain(
                    item["factor_id"],
                    item["kind"],
                    tuple(item["levels"]),
                    item["correlation_policy"],
                )
            )
        else:
            if set(item) != {"factor_id", "kind", "low", "high", "step", "display_decimals"}:
                raise _invalid("bayesian_factor_domain_payload_invalid")
            factors.append(
                BoNumericFactorDomain(
                    item["factor_id"],
                    DoeFactorDomain(
                        item["low"],
                        item["high"],
                        item["kind"],
                        item["step"],
                        item["display_decimals"],
                    ),
                )
            )
    result = tuple(factors)
    validate_bo_factor_domains(result)
    if bo_factor_domains_to_payload(result) != payload:
        raise _invalid("bayesian_factor_domain_payload_invalid")
    return result
