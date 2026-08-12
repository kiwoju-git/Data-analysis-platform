import { ApiRequestError } from "../api/client";
import { t, type TranslationKey } from "./translate";
import type { AppLocale } from "./types";

export interface LocalizedErrorDisplay {
  code: string;
  correlationId: string | null;
  message: string;
}

const errorKeys: Readonly<Record<string, TranslationKey>> = {
  api_unreachable: "errors.apiUnreachable",
};

export function localizedErrorDisplay(
  error: unknown,
  locale: AppLocale,
): LocalizedErrorDisplay {
  const code = error instanceof ApiRequestError
    ? error.code
    : error instanceof Error && /^[a-z][a-z0-9_]+$/u.test(error.message)
      ? error.message
      : "unknown_error";
  return {
    code,
    correlationId: error instanceof ApiRequestError ? error.correlationId : null,
    message: t(errorKeys[code] ?? "errors.generic", {}, locale),
  };
}
