import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { localizeApiPayload } from "../api/client";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { initialLocale, LocaleProvider } from "./LocaleProvider";
import {
  formatCount,
  formatLocaleDateTime,
  formatLocaleNumber,
  formatLocalePercent,
} from "./formatters";
import { t } from "./translate";

describe("localization foundation", () => {
  it("uses English when no valid browser preference exists", () => {
    expect(initialLocale(null)).toBe("en");
    expect(initialLocale({ getItem: () => null })).toBe("en");
    expect(initialLocale({ getItem: () => "invalid" })).toBe("en");
    expect(initialLocale({ getItem: () => "ko" })).toBe("ko");
  });

  it("keeps the English and Korean dictionaries distinct", () => {
    expect(t("language.selector", {}, "en")).toBe("Language");
    expect(t("language.selector", {}, "ko")).toBe("언어 선택");
  });

  it("renders an accessible English-default language selector", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider>
        <LanguageSwitcher />
      </LocaleProvider>,
    );
    expect(html).toContain('aria-label="Language"');
    expect(html).toContain('aria-label="English" aria-pressed="true"');
    expect(html).toContain('aria-label="Korean" aria-pressed="false"');
    expect(html).toContain("KOR");
    expect(html).toContain("ENG");
  });

  it("formats numbers, percentages, dates, and English plurals by locale", () => {
    expect(formatLocaleNumber(1234.56, "en")).toBe("1,234.56");
    expect(formatLocaleNumber(1234.56, "ko")).toBe("1,234.56");
    expect(formatLocalePercent(0.125, "en")).toBe("12.5%");
    expect(formatCount(1, "row", "rows", "en")).toBe("1 row");
    expect(formatCount(2, "row", "rows", "en")).toBe("2 rows");
    expect(formatCount(2, "행", "행", "ko")).toBe("2 행");
    expect(formatLocaleDateTime("2026-08-09T00:26:00Z", "en")).toContain("Aug");
    expect(formatLocaleDateTime("2026-08-09T00:26:00Z", "ko")).toContain("2026");
  });

  it("localizes machine warning messages but never translates ordinary user records", () => {
    const warning = localizeApiPayload(
      { warnings: [{ code: "api_connection_failed", message: "API 연결 실패" }] },
      "en",
    ) as { warnings: Array<{ message: string }> };
    expect(warning.warnings[0].message).toBe("API connection failure");

    const userRecord = { code: "A", message: "사용자가 입력한 메모" };
    expect(localizeApiPayload(userRecord, "en")).toEqual(userRecord);
  });
});
