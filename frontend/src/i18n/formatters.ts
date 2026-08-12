import type { AppLocale } from "./types";

const localeTag = (locale: AppLocale) => (locale === "ko" ? "ko-KR" : "en-US");

export function formatLocaleNumber(
  value: number,
  locale: AppLocale,
  options: Intl.NumberFormatOptions = {},
): string {
  return new Intl.NumberFormat(localeTag(locale), options).format(value);
}

export function formatLocalePercent(
  value: number,
  locale: AppLocale,
  maximumFractionDigits = 2,
): string {
  return new Intl.NumberFormat(localeTag(locale), {
    style: "percent",
    maximumFractionDigits,
  }).format(value);
}

export function formatLocaleDateTime(value: string, locale: AppLocale): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(localeTag(locale), {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: locale === "ko" ? "2-digit" : "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

export function formatCount(
  count: number,
  singular: string,
  plural: string,
  locale: AppLocale,
): string {
  const label = locale === "ko" || new Intl.PluralRules("en").select(count) === "one"
    ? singular
    : plural;
  return `${formatLocaleNumber(count, locale)} ${label}`.trim();
}
