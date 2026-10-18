"""Bounded display-only numeric axes, shared in meaning with numericAxisPlan.ts."""

from dataclasses import dataclass
from math import ceil, floor, fmod, isfinite, log10
from sys import float_info


def padded_range(low: float, high: float, ratio: float = 0.06) -> tuple[float, float]:
    span = high - low
    padding = (span or max(abs(low), 1.0)) * ratio if isfinite(span) else high * ratio - low * ratio
    return max(-float_info.max, low - padding), min(float_info.max, high + padding)


def numeric_fraction(value: float, low: float, high: float) -> float:
    span = high - low
    return (value - low) / span if isfinite(span) else (value / 2 - low / 2) / (high / 2 - low / 2)


@dataclass(frozen=True)
class NumericAxisPlan:
    values: tuple[float, ...]
    step: float | None
    offset: float
    suggested_significant_digits: int


def suggested_digits(values: tuple[float, ...], step: float | None) -> int:
    magnitude = max((abs(value) for value in values), default=0.0)
    if magnitude == 0 or step is None or step <= 0:
        return 5
    return max(3, min(17, ceil(log10(magnitude) - log10(step)) + 2))


def numeric_axis_plan(low: float, high: float, target: int = 5) -> NumericAxisPlan:
    if not isfinite(low) or not isfinite(high) or low >= high:
        return NumericAxisPlan((), None, 0.0, 5)
    count = max(2, min(12, target))
    raw = high / count - low / count
    magnitude = 10.0 ** floor(log10(raw)) if raw > 0 else 0.0
    step = next(
        (
            value
            for factor in (1, 2, 2.5, 5, 10)
            if isfinite(value := factor * magnitude) and value > 0 and value >= raw
        ),
        None,
    )
    values: list[float] = []
    if step is not None:
        origin = low - fmod(low, step)
        first = ceil((low - origin) / step)
        for index in range(32):
            value = origin + (first + index) * step
            if not isfinite(value) or value > high:
                break
            if value >= low and (not values or value > values[-1]):
                values.append(0.0 if value == 0 else value)
    if len(values) < 2:
        values = [low, high]
    spacing = min(second - first for first, second in zip(values, values[1:], strict=False))
    actual_step = spacing if isfinite(spacing) and spacing > 0 else step
    span = high - low
    offset = low if low * high > 0 and isfinite(span) and abs(low) / span > 1e6 else 0.0
    return NumericAxisPlan(
        tuple(values),
        actual_step,
        offset,
        suggested_digits(tuple(value - offset for value in values), actual_step),
    )


def numeric_axis_ticks(plan: NumericAxisPlan) -> tuple[tuple[float, str], ...]:
    for digits in range(plan.suggested_significant_digits, 18):
        ticks = tuple(
            (value, format(value - plan.offset, f".{digits}g") if value != plan.offset else "0")
            for value in plan.values
        )
        if len({label for _, label in ticks}) == len(ticks):
            return ticks
    return tuple((value, repr(value - plan.offset)) for value in plan.values)
