import type { NumericRange } from "./chartScale";

export interface PlotBounds { left: number; top: number; width: number; height: number }
export interface ChartLayout { width: number; height: number; maxWidth: number; plot: PlotBounds }
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

export function formatChartTick(value: number): string {
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  return magnitude >= 1e6 || magnitude < 1e-3
    ? value.toExponential(2).replace(/\.0+(?=e)/, "")
    : Number(value.toPrecision(5)).toString();
}

export function numericChartTicks(range: NumericRange, target = 5): Array<{ value: number; label: string }> {
  if (!Number.isFinite(range.min) || !Number.isFinite(range.max) || range.min >= range.max) return [];
  const raw = (range.max / target - range.min / target);
  if (!(raw > 0) || !Number.isFinite(raw)) return [];
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((multiple) => multiple * magnitude).find((value) => value >= raw);
  if (step === undefined || !Number.isFinite(step) || step <= 0) return [];
  const start = Math.ceil(range.min / step - 1e-10);
  const end = Math.floor(range.max / step + 1e-10);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end - start > 20) return [];
  return Array.from({ length: Math.max(0, end - start + 1) }, (_, index) => {
    const value = Number(((start + index) * step).toPrecision(12));
    return { value, label: formatChartTick(value) };
  });
}
