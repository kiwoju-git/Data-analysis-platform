import catalog from "./catalog.generated.json";
import { regularizedWarningKeys } from "./regularizedMessages";
import { t, translateKnownSource } from "./translate";
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

export function presentApiNotice(notice: ApiNotice, locale: AppLocale): ApiNoticePresentation {
  const knownCode = Object.prototype.hasOwnProperty.call(regularizedWarningKeys, notice.code);
  if (knownCode) {
    return { code: notice.code, message: t(regularizedWarningKeys[notice.code], {}, locale), knownCode };
  }
  // Exact catalog matches are static system prose. Dynamic/user-containing messages stay intact.
  const knownSource = Object.prototype.hasOwnProperty.call(catalog.sourceToKey, notice.message);
  return {
    code: notice.code,
    message: knownSource ? translateKnownSource(notice.message, locale) ?? notice.message : notice.message,
    knownCode,
  };
}
