import { formatLocaleNumber } from "../i18n/formatters";
import { getCurrentLocale } from "../i18n/store";
import type { AppLocale } from "../i18n/types";

export function formatChartDetailValue(value: number, locale: AppLocale = getCurrentLocale()): string {
  if (!Number.isFinite(value)) return "-";
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  return formatLocaleNumber(value, locale, {
    maximumSignificantDigits: 7,
    notation: magnitude < 1e-3 || magnitude >= 1e6 ? "scientific" : "standard",
  }).replace("E", "e");
}

// Preserve a caller's ordinary fixed-decimal policy without rounding tiny values to zero.
export function formatSmallChartValue(
  value: number,
  maximumFractionDigits: number,
  locale: AppLocale = getCurrentLocale(),
): string | null {
  return Number.isFinite(value) && value !== 0 && Math.abs(value) < 10 ** -maximumFractionDigits
    ? formatChartDetailValue(value, locale)
    : null;
}
