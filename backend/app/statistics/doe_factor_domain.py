from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Final, Literal

MAX_DISCRETE_NUMERIC_LEVELS: Final = 10_001
GRID_TOLERANCE: Final = Decimal("1e-12")


class DoeFactorDomainError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class DoeFactorDomain:
    low: float
    high: float
    domain_kind: Literal["continuous", "discrete_numeric"] = "continuous"
    step: float | None = None
    display_decimals: int | None = None

    @property
    def level_count(self) -> int | None:
        if self.domain_kind == "continuous":
            return None
        low, high, step = _validated_decimals(self.low, self.high, self.step)
        return int((high - low) / step) + 1

    def levels(self) -> tuple[float, ...]:
        count = self.level_count
        if count is None:
            raise DoeFactorDomainError("doe_factor_domain_not_discrete")
        low, _, step = _validated_decimals(self.low, self.high, self.step)
        return tuple(float(low + step * index) for index in range(count))

    def is_executable(self, value: float) -> bool:
        if not isfinite(value) or value < self.low or value > self.high:
            return False
        if self.domain_kind == "continuous":
            return True
        low, _, step = _validated_decimals(self.low, self.high, self.step)
        ratio = (_decimal(value) - low) / step
        return abs(ratio - ratio.to_integral_value()) <= GRID_TOLERANCE

    def normalized(self, value: float) -> float:
        return (value - self.low) / (self.high - self.low)


def validate_factor_domain(domain: DoeFactorDomain) -> None:
    if not isfinite(domain.low) or not isfinite(domain.high) or domain.low >= domain.high:
        raise DoeFactorDomainError("doe_factor_bounds_invalid")
    if domain.display_decimals is not None and not 0 <= domain.display_decimals <= 12:
        raise DoeFactorDomainError("doe_factor_display_decimals_invalid")
    if domain.domain_kind == "continuous":
        if domain.step is not None:
            raise DoeFactorDomainError("doe_continuous_factor_step_not_allowed")
        return
    if domain.domain_kind != "discrete_numeric":
        raise DoeFactorDomainError("doe_factor_domain_kind_invalid")
    low, high, step = _validated_decimals(domain.low, domain.high, domain.step)
    ratio = (high - low) / step
    if abs(ratio - ratio.to_integral_value()) > GRID_TOLERANCE:
        raise DoeFactorDomainError("doe_factor_high_not_on_grid")
    count = int(ratio.to_integral_value()) + 1
    if count < 2 or count > MAX_DISCRETE_NUMERIC_LEVELS:
        raise DoeFactorDomainError("doe_factor_level_count_invalid")


def factor_domain_payload(domain: DoeFactorDomain) -> dict[str, object]:
    return {
        "domain_kind": domain.domain_kind,
        "step": domain.step,
        "display_decimals": domain.display_decimals,
    }


def _validated_decimals(
    low_value: float,
    high_value: float,
    step_value: float | None,
) -> tuple[Decimal, Decimal, Decimal]:
    if step_value is None or not isfinite(step_value) or step_value <= 0:
        raise DoeFactorDomainError("doe_factor_step_invalid")
    low = _decimal(low_value)
    high = _decimal(high_value)
    step = _decimal(step_value)
    return low, high, step


def _decimal(value: float) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise DoeFactorDomainError("doe_factor_decimal_invalid") from exc
