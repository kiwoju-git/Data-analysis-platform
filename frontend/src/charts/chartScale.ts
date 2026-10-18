export interface NumericRange {
  max: number;
  min: number;
}

export function paddedNumericRange(values: number[], paddingRatio = 0.04): NumericRange {
  const finiteValues = values.filter((value) => Number.isFinite(value));
  if (finiteValues.length === 0) return { min: 0, max: 1 };
  const min = Math.min(...finiteValues);
  const max = Math.max(...finiteValues);
  if (min === max) {
    const padding = Math.max(1, Math.abs(min) * 0.1);
    return { min: Math.max(-Number.MAX_VALUE, min - padding), max: Math.min(Number.MAX_VALUE, max + padding) };
  }
  const ratio = Number.isFinite(paddingRatio) && paddingRatio >= 0 ? paddingRatio : 0.04;
  const padding = Number.isFinite(max - min) ? (max - min) * ratio : max * ratio - min * ratio;
  return { min: Math.max(-Number.MAX_VALUE, min - padding), max: Math.min(Number.MAX_VALUE, max + padding) };
}

export function scaleChartValue(
  value: number,
  domain: NumericRange,
  rangeMin: number,
  rangeMax: number,
): number {
  if (domain.min === domain.max) return (rangeMin + rangeMax) / 2;
  const span = domain.max - domain.min;
  const fraction = Number.isFinite(span) ? (value - domain.min) / span
    : (value / 2 - domain.min / 2) / (domain.max / 2 - domain.min / 2);
  return rangeMin + fraction * (rangeMax - rangeMin);
}

export function expandNumericRange(range: NumericRange, values: readonly number[]): NumericRange {
  const finite = values.filter(Number.isFinite);
  if (!Number.isFinite(range.min) || !Number.isFinite(range.max) || range.min > range.max) {
    return paddedNumericRange(finite);
  }
  const min = Math.min(range.min, ...finite);
  const max = Math.max(range.max, ...finite);
  return min === max ? paddedNumericRange([min]) : { min, max };
}
