import catalog from "./catalog.generated.json";
import type { AppLocale } from "./types";
import { getCurrentLocale } from "./store";

export type TranslationKey = keyof typeof catalog.en;
export type TranslationParams = Readonly<Record<string, string | number>>;

const TOKEN_PREFIX = "\uE000";
const TOKEN_SUFFIX = "\uE001";
const tokenPattern = /\uE000([^\uE001]+)\uE001/gu;

export function translationToken(key: TranslationKey): string {
  return `${TOKEN_PREFIX}${key}${TOKEN_SUFFIX}`;
}

export function t(
  key: TranslationKey,
  params: TranslationParams = {},
  locale: AppLocale = getCurrentLocale(),
): string {
  const dictionary = locale === "ko" ? catalog.ko : catalog.en;
  const template = dictionary[key] ?? catalog.en[key];
  if (template === undefined) {
    return import.meta.env.DEV ? `[missing:${key}]` : key;
  }
  return interpolate(template, params);
}

export function resolveLocalizedText(value: string, locale = getCurrentLocale()): string {
  if (!value.includes(TOKEN_PREFIX)) return value;
  const dictionary = locale === "ko" ? catalog.ko : catalog.en;
  return value.replace(tokenPattern, (_match, requestedKey: string) => {
    const key = requestedKey as TranslationKey;
    return dictionary[key] ?? catalog.en[key] ?? (import.meta.env.DEV ? `[missing:${key}]` : key);
  });
}

export function translateKnownSource(
  source: string,
  locale: AppLocale = getCurrentLocale(),
): string | null {
  const key = catalog.sourceToKey[source as keyof typeof catalog.sourceToKey] as
    | TranslationKey
    | undefined;
  return key === undefined ? null : t(key, {}, locale);
}

function interpolate(template: string, params: TranslationParams): string {
  return template.replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/gu, (match, name: string) => {
    const value = params[name];
    return value === undefined ? match : String(value);
  });
}
