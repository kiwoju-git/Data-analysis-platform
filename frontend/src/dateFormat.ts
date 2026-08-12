import { getCurrentLocale } from "./i18n/store";
import { t } from "./i18n/translate";

export function formatLocalDateTime(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) {
    return t("format.invalidDate");
  }
  return new Intl.DateTimeFormat(getCurrentLocale() === "ko" ? "ko-KR" : "en-US", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}
