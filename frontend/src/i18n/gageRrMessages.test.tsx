import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiNoticeText } from "./ApiNoticeText";
import { LocaleProvider } from "./LocaleProvider";
import { presentApiNotice, type ApiNotice } from "./apiNoticePresentation";
import { gageRrNoticeKeys } from "./gageRrMessages";
import { setCurrentLocale } from "./store";
import type { AppLocale } from "./types";

function renderNotice(notice: ApiNotice, locale: AppLocale) {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  return renderToStaticMarkup(<LocaleProvider>
    <ApiNoticeText notice={notice} messageKeys={gageRrNoticeKeys} showCode />
  </LocaleProvider>);
}

afterEach(() => {
  vi.unstubAllGlobals();
  setCurrentLocale("en");
});

describe("Gage warning presentation", () => {
  it("switches every known code at the display boundary without rewriting stored messages", () => {
    for (const code of Object.keys(gageRrNoticeKeys)) {
      const stored = Object.freeze({ code, message: "저장된 원문 메시지" });
      const snapshot = JSON.stringify(stored);
      const english = presentApiNotice(stored, "en", gageRrNoticeKeys);
      const korean = presentApiNotice(stored, "ko", gageRrNoticeKeys);
      expect(english.knownCode).toBe(true);
      expect(korean.knownCode).toBe(true);
      expect(english.message).not.toMatch(/[가-힣]/);
      expect(korean.message).toMatch(/[가-힣]/);
      expect(english.message).not.toBe(korean.message);
      for (const locale of ["ko", "en", "ko"] as const) {
        const html = renderNotice(stored, locale);
        expect(html).toContain(code);
        expect(html).not.toContain(stored.message);
        expect(JSON.stringify(stored)).toBe(snapshot);
      }
    }
  });

  it("retains pooling meaning and keeps unknown escaped text and code", () => {
    const pooled = Object.freeze({ code: "gage_rr_interaction_pooled", message: "원래 풀링 경고" });
    expect(renderNotice(pooled, "en")).toContain("pooling interaction into repeatability error");
    expect(renderNotice(pooled, "ko")).toContain("반복성 오차에 풀링");
    const unknown = Object.freeze({ code: "gage_rr_future_warning", message: '<script>synthetic</script> 원문' });
    for (const locale of ["ko", "en"] as const) {
      const html = renderNotice(unknown, locale);
      expect(html).toContain(unknown.code);
      expect(html).toContain("&lt;script&gt;synthetic&lt;/script&gt; 원문");
      expect(html).not.toContain("<script>");
    }
  });

  it("does not change non-Gage consumers of shared exclusion codes", () => {
    const stored = { code: "missing_values_excluded", message: "Other method detail" };
    expect(presentApiNotice(stored, "en").message).toBe(stored.message);
    expect(presentApiNotice(stored, "en", gageRrNoticeKeys).message)
      .toBe("Rows with missing measurements were excluded under the complete-case policy.");
    expect(presentApiNotice({ code: "constructor", message: "Original" }, "en", gageRrNoticeKeys))
      .toEqual({ code: "constructor", message: "Original", knownCode: false });
  });
});
