import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { setCurrentLocale } from "./store";
import { getCurrentLocale } from "./store";
import { t, type TranslationKey, type TranslationParams } from "./translate";
import {
  formatCount,
  formatLocaleDateTime,
  formatLocaleNumber,
  formatLocalePercent,
} from "./formatters";
import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  isAppLocale,
  type AppLocale,
} from "./types";

interface LocaleContextValue {
  locale: AppLocale;
  setLocale: (locale: AppLocale) => void;
  t: (key: TranslationKey, params?: TranslationParams) => string;
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
  formatPercent: (value: number, maximumFractionDigits?: number) => string;
  formatDateTime: (value: string) => string;
  formatCount: (count: number, singular: string, plural: string) => string;
}

const LocaleContext = createContext<LocaleContextValue | null>(null);

// Exported for deterministic storage-policy tests; it does not participate in refresh state.
// eslint-disable-next-line react-refresh/only-export-components
export function initialLocale(storage: Pick<Storage, "getItem"> | null): AppLocale {
  if (storage === null) return DEFAULT_LOCALE;
  try {
    const stored = storage.getItem(LOCALE_STORAGE_KEY);
    return isAppLocale(stored) ? stored : DEFAULT_LOCALE;
  } catch {
    return DEFAULT_LOCALE;
  }
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<AppLocale>(() => {
    const resolved = initialLocale(typeof window === "undefined" ? null : window.localStorage);
    setCurrentLocale(resolved);
    return resolved;
  });
  const setLocale = useCallback((nextLocale: AppLocale) => {
    setCurrentLocale(nextLocale);
    setLocaleState(nextLocale);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, nextLocale);
    } catch {
      // A blocked localStorage must not prevent an in-memory language switch.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      setLocale,
      t: (key, params) => t(key, params, locale),
      formatNumber: (number, options) => formatLocaleNumber(number, locale, options),
      formatPercent: (number, maximumFractionDigits) =>
        formatLocalePercent(number, locale, maximumFractionDigits),
      formatDateTime: (date) => formatLocaleDateTime(date, locale),
      formatCount: (count, singular, plural) => formatCount(count, singular, plural, locale),
    }),
    [locale, setLocale],
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

// The provider and its matching hook intentionally share this module.
// eslint-disable-next-line react-refresh/only-export-components
export function useI18n(): LocaleContextValue {
  const value = useContext(LocaleContext);
  if (value !== null) return value;
  const locale = getCurrentLocale();
  return {
    locale,
    setLocale: setCurrentLocale,
    t: (key, params) => t(key, params, locale),
    formatNumber: (number, options) => formatLocaleNumber(number, locale, options),
    formatPercent: (number, maximumFractionDigits) =>
      formatLocalePercent(number, locale, maximumFractionDigits),
    formatDateTime: (date) => formatLocaleDateTime(date, locale),
    formatCount: (count, singular, plural) => formatCount(count, singular, plural, locale),
  };
}
