import { DEFAULT_LOCALE, type AppLocale } from "./types";

let currentLocale: AppLocale = DEFAULT_LOCALE;

export function getCurrentLocale(): AppLocale {
  return currentLocale;
}

export function setCurrentLocale(locale: AppLocale): void {
  currentLocale = locale;
}
