import catalog from "./catalog.generated.json";
import { regularizedWarningKeys } from "./regularizedMessages";
import { t, translateKnownSource, type TranslationKey } from "./translate";
import type { AppLocale } from "./types";

export interface ApiNotice {
  readonly code: string;
  readonly message: string;
}

export interface ApiNoticePresentation {
  readonly code: string;
  readonly message: string;
  readonly knownCode: boolean;
}

export type ApiNoticeMessageKeys = Readonly<Record<string, TranslationKey>>;

export function presentApiNotice(
  notice: ApiNotice,
  locale: AppLocale,
  messageKeys?: ApiNoticeMessageKeys,
): ApiNoticePresentation {
  const keys = messageKeys && Object.prototype.hasOwnProperty.call(messageKeys, notice.code)
    ? messageKeys : regularizedWarningKeys;
  const knownCode = Object.prototype.hasOwnProperty.call(keys, notice.code);
  if (knownCode) {
    return { code: notice.code, message: t(keys[notice.code], {}, locale), knownCode };
  }
  // Exact catalog matches are static system prose. Dynamic/user-containing messages stay intact.
  const knownSource = Object.prototype.hasOwnProperty.call(catalog.sourceToKey, notice.message);
  return {
    code: notice.code,
    message: knownSource ? translateKnownSource(notice.message, locale) ?? notice.message : notice.message,
    knownCode,
  };
}
