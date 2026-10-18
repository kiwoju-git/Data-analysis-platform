import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiNoticeText } from "./ApiNoticeText";
import { LocaleProvider } from "./LocaleProvider";
import { presentApiNotice, type ApiNotice } from "./apiNoticePresentation";
import { setCurrentLocale } from "./store";
import { t } from "./translate";
import type { AppLocale } from "./types";

function renderNotice(notice: ApiNotice, locale: AppLocale, showCode?: boolean) {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  return renderToStaticMarkup(
    <LocaleProvider><ApiNoticeText notice={notice} showCode={showCode} /></LocaleProvider>,
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  setCurrentLocale("en");
});

describe("explicit API notice presentation", () => {
  it("uses the render locale for a stored DTO without mutating its original message", () => {
    const notice = Object.freeze({
      code: "regularized_model_convergence_warning",
      message: "Some solver fits did not converge. Review iterations, tolerance and alpha.",
    });
    const snapshot = JSON.stringify(notice);
    for (const locale of ["en", "ko", "en"] as const) {
      expect(renderNotice(notice, locale)).toBe(t("reg.warning.convergence", {}, locale));
      expect(JSON.stringify(notice)).toBe(snapshot);
    }
  });

  it("translates only an exact known static message and retains the machine code", () => {
    const notice = Object.freeze({ code: "api_connection_failed", message: "API \uC5F0\uACB0 \uC2E4\uD328" });
    expect(renderNotice(notice, "en")).toContain("API connection failure");
    expect(renderNotice(notice, "ko")).toContain(notice.message);
    expect(renderNotice(notice, "en")).toContain(notice.code);
  });

  it("preserves an unknown code and its complete original message in both locales", () => {
    const notice = Object.freeze({ code: "future_warning_v9", message: "Column Alpha has 7 excluded rows; keep this diagnostic." });
    for (const locale of ["en", "ko"] as const) {
      expect(presentApiNotice(notice, locale)).toEqual({ ...notice, knownCode: false });
      const html = renderNotice(notice, locale);
      expect(html).toContain(notice.message);
      expect(html).toContain(notice.code);
      expect(html).not.toContain(t("warnings.generic", {}, locale));
    }
  });

  it("does not interpret user-containing message text as translation tokens", () => {
    const notice = Object.freeze({ code: "column_warning", message: "Column \uE000startup.failed\uE001 / \uC0AC\uC6A9\uC790: exact stored value" });
    for (const locale of ["en", "ko"] as const) {
      expect(renderNotice(notice, locale)).toContain(notice.message);
      expect(presentApiNotice(notice, locale).message).toBe(notice.message);
    }
  });

  it("escapes both code and message instead of creating HTML", () => {
    const notice = { code: '<img src=x onerror="alert(1)">', message: '<script>alert("synthetic")</script>' };
    const html = renderNotice(notice, "en");
    expect(html).toContain("&lt;img");
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
  });

  it("does not treat prototype properties as translations or warning mappings", () => {
    for (const value of ["constructor", "toString", "__proto__"]) {
      expect(presentApiNotice({ code: value, message: value }, "en"))
        .toEqual({ code: value, message: value, knownCode: false });
    }
  });

  it("can keep an already-rendered code separate without changing the message", () => {
    const notice = { code: "future_warning", message: "Original detail" };
    expect(renderNotice(notice, "en", false)).toBe(notice.message);
    expect(renderNotice(notice, "en", true)).toContain(notice.code);
  });
});
