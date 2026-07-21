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
    return { min: min - padding, max: max + padding };
  }
  const padding = (max - min) * paddingRatio;
  return { min: min - padding, max: max + padding };
}

export function scaleChartValue(
  value: number,
  domain: NumericRange,
  rangeMin: number,
  rangeMax: number,
): number {
  if (domain.min === domain.max) return (rangeMin + rangeMax) / 2;
  return rangeMin + ((value - domain.min) / (domain.max - domain.min)) * (rangeMax - rangeMin);
}
