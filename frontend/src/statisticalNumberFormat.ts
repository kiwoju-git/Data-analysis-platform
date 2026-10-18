import { formatLocaleNumber } from "./i18n/formatters";
import { getCurrentLocale } from "./i18n/store";
import type { AppLocale } from "./i18n/types";

function significant(value: number, digits: number, locale: AppLocale): string {
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  return formatLocaleNumber(value, locale, { maximumSignificantDigits: digits,
    notation: magnitude < 1e-3 || magnitude >= 1e6 ? "scientific" : "standard" }).replace("E", "e");
}

export function formatExactNumericValue(value: number | null | undefined): string {
  return value == null || !Number.isFinite(value) ? "-" : String(value === 0 ? 0 : value);
}

export function formatMeasurement(value: number | null | undefined, locale: AppLocale = getCurrentLocale()): string {
  return value == null || !Number.isFinite(value) ? "-" : significant(value, 7, locale);
}

export function formatInterval(interval: { lower: number; upper: number } | null | undefined, locale: AppLocale = getCurrentLocale()): string {
  if (interval == null || !Number.isFinite(interval.lower) || !Number.isFinite(interval.upper)) return "-";
  for (let digits = 7; digits <= 17; digits += 1) {
    const lower = significant(interval.lower, digits, locale);
    const upper = significant(interval.upper, digits, locale);
    if (lower !== upper || interval.lower === interval.upper) return `[${lower}, ${upper}]`;
  }
  return `[${formatExactNumericValue(interval.lower)}, ${formatExactNumericValue(interval.upper)}]`;
}

export function formatProbability(value: number | null | undefined, locale: AppLocale = getCurrentLocale()): string {
  return value == null || value < 0 || value > 1 ? "-" : formatMeasurement(value, locale);
}
