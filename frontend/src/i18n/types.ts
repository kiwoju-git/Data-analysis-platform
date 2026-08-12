export const SUPPORTED_LOCALES = ["en", "ko"] as const;

export type AppLocale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: AppLocale = "en";
export const LOCALE_STORAGE_KEY = "statistical-twin.locale";

export function isAppLocale(value: unknown): value is AppLocale {
  return value === "en" || value === "ko";
}
