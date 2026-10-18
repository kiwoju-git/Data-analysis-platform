import type { NumericRange } from "./chartScale";

export interface NumericAxisPlan {
  values: readonly number[];
  range: NumericRange;
  step: number | null;
  offset: number;
  suggestedSignificantDigits: number;
}

export function suggestedDigits(values: readonly number[], step: number | null): number {
  const magnitude = Math.max(0, ...values.map(Math.abs));
  if (magnitude === 0 || step === null || !(step > 0)) return 5;
  return Math.max(3, Math.min(17, Math.ceil(Math.log10(magnitude) - Math.log10(step)) + 2));
}

/** Display positions only. Never round absolute coordinates to significant digits. */
export function numericAxisPlan(range: NumericRange, target = 5): NumericAxisPlan {
  const empty: NumericAxisPlan = { values: [], range, step: null, offset: 0, suggestedSignificantDigits: 5 };
  if (!Number.isFinite(range.min) || !Number.isFinite(range.max) || range.min >= range.max) return empty;
  const count = Number.isFinite(target) ? Math.max(2, Math.min(12, Math.floor(target))) : 5;
  const raw = range.max / count - range.min / count;
  const magnitude = raw > 0 ? 10 ** Math.floor(Math.log10(raw)) : 0;
  const step = [1, 2, 2.5, 5, 10].map((multiple) => multiple * magnitude)
    .find((value) => Number.isFinite(value) && value > 0 && value >= raw) ?? null;
  const values: number[] = [];
  if (step !== null) {
    // A nearby origin keeps indices small even for a narrow range around 1e12.
    const origin = range.min - range.min % step;
    const first = Math.ceil((range.min - origin) / step);
    if (Number.isFinite(origin) && Number.isFinite(first)) {
      for (let index = 0; index < 32; index += 1) {
        const value = origin + (first + index) * step;
        if (!Number.isFinite(value) || value > range.max) break;
        if (value >= range.min && (values.length === 0 || value > values[values.length - 1])) values.push(value === 0 ? 0 : value);
      }
    }
  }
  if (values.length < 2) values.splice(0, values.length, range.min, range.max);
  const spacing = values.slice(1).reduce((smallest, value, index) => Math.min(smallest, value - values[index]), Infinity);
  const actualStep = Number.isFinite(spacing) && spacing > 0 ? spacing : step;
  const span = range.max - range.min;
  const offset = range.min * range.max > 0 && Number.isFinite(span) && Math.abs(range.min) / span > 1e6 ? range.min : 0;
  return { values, range, step: actualStep, offset,
    suggestedSignificantDigits: suggestedDigits(values.map((value) => value - offset), actualStep) };
}
