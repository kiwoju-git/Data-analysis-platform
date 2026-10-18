import { formatLocaleNumber } from "../i18n/formatters";
import { getCurrentLocale } from "../i18n/store";
import type { AppLocale } from "../i18n/types";
import type { NumericRange } from "./chartScale";
import { numericAxisPlan, suggestedDigits, type NumericAxisPlan } from "./numericAxisPlan";

export interface PlotBounds { left: number; top: number; width: number; height: number }
export interface ChartLayout { width: number; height: number; maxWidth: number; plot: PlotBounds }
export interface ChartTickContext { range: NumericRange; step: number | null; offset: number; suggestedSignificantDigits: number }
export type ChartTickFormatter = (value: number, context?: ChartTickContext) => string;
export const STANDARD_CHART_LAYOUT: ChartLayout = {
  width: 480, height: 320, maxWidth: 640,
  plot: { left: 72, top: 24, width: 384, height: 232 },
};
export const SQUARE_CHART_LAYOUT: ChartLayout = {
  width: 480, height: 480, maxWidth: 520,
  plot: { left: 72, top: 24, width: 384, height: 384 },
};

export function axisTitle(label: string, unit?: string | null): string {
  return unit ? `${label} (${unit})` : label;
}

export function wrapAxisTitle(title: string, limit: number): string[] {
  if (title.length <= limit) return [title];
  const boundary = title.lastIndexOf(" ", limit);
  const at = boundary >= limit / 2 ? boundary : limit;
  const rest = title.slice(at).trim();
  return [title.slice(0, at), rest.length > limit ? `${rest.slice(0, limit - 3)}...` : rest];
}

export function formatChartTick(value: number, localeOrContext: AppLocale | ChartTickContext = getCurrentLocale(), context?: ChartTickContext): string {
  const locale = typeof localeOrContext === "string" ? localeOrContext : getCurrentLocale();
  const precision = typeof localeOrContext === "string" ? context : localeOrContext;
  if (!Number.isFinite(value)) return "-";
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  return magnitude >= 1e6 || magnitude < 1e-3
    ? formatLocaleNumber(value, locale, { notation: "scientific", maximumSignificantDigits: precision?.suggestedSignificantDigits ?? 3 }).replace("E", "e")
    : formatLocaleNumber(value, locale, { maximumSignificantDigits: precision?.suggestedSignificantDigits ?? 5 });
}

export function numericChartTickValues(range: NumericRange, target = 5): number[] {
  return [...numericAxisPlan(range, target).values];
}

export function formattedAxisTicks(plan: NumericAxisPlan, locale: AppLocale = getCurrentLocale(), formatTick?: ChartTickFormatter): Array<{ value: number; label: string }> {
  const offset = formatTick ? 0 : plan.offset;
  const context: ChartTickContext = { range: plan.range, step: plan.step, offset,
    suggestedSignificantDigits: suggestedDigits(plan.values.map((value) => value - offset), plan.step) };
  if (formatTick) return plan.values.map((value) => ({ value, label: formatTick(value, context) }));
  for (let digits = context.suggestedSignificantDigits; digits <= 17; digits += 1) {
    const ticks = plan.values.map((value) => ({ value, label: formatChartTick(value - offset, locale, { ...context, suggestedSignificantDigits: digits }) }));
    if (new Set(ticks.map((tick) => tick.label)).size === ticks.length) return ticks;
  }
  return plan.values.map((value) => ({ value, label: String(value - offset) }));
}

export function numericChartTicks(range: NumericRange, target = 5, formatTick?: ChartTickFormatter): Array<{ value: number; label: string }> {
  // Legacy callers receive standalone absolute labels; only ChartAxes displays an offset.
  return formattedAxisTicks({ ...numericAxisPlan(range, target), offset: 0 }, getCurrentLocale(), formatTick);
}

export function integerChartTicks(range: NumericRange): Array<{ value: number; label: string }> {
  return numericChartTickValues(range).filter(Number.isInteger).map((value) => ({
    value, label: formatLocaleNumber(value, getCurrentLocale(), { maximumFractionDigits: 0 }),
  }));
}
