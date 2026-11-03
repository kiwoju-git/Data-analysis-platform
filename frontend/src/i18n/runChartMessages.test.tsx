import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiNoticeText } from "./ApiNoticeText";
import { LocaleProvider } from "./LocaleProvider";
import { presentApiNotice, type ApiNotice } from "./apiNoticePresentation";
import { runChartNoticeKeys } from "./runChartMessages";
import { setCurrentLocale } from "./store";
import type { AppLocale } from "./types";

function renderNotice(notice: ApiNotice, locale: AppLocale) {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  return renderToStaticMarkup(<LocaleProvider>
    <ApiNoticeText notice={notice} messageKeys={runChartNoticeKeys} showCode />
  </LocaleProvider>);
}

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

describe("Run Chart warning display boundary", () => {
  it("translates every explicitly supported warning code without mutating its stored DTO", () => {
    expect(Object.keys(runChartNoticeKeys)).toHaveLength(20);
    for (const code of Object.keys(runChartNoticeKeys)) {
      const stored = Object.freeze({ code, message: "저장된 경고 원문" });
      const before = JSON.stringify(stored);
      for (const locale of ["ko", "en", "ko"] as const) {
        const presentation = presentApiNotice(stored, locale, runChartNoticeKeys);
        expect(presentation.knownCode).toBe(true);
        expect(presentation.code).toBe(code);
        if (locale === "en") expect(presentation.message).not.toMatch(/[\uAC00-\uD7A3]/u);
        else expect(presentation.message).toMatch(/[\uAC00-\uD7A3]/u);
        const html = renderNotice(stored, locale);
        expect(html).toContain(code);
        expect(html).not.toContain(stored.message);
        expect(JSON.stringify(stored)).toBe(before);
      }
    }
  });

  it("preserves exact-run semantics and does not impose a default rule length on saved options", () => {
    const text = (code: string) => presentApiNotice({ code, message: "원문" }, "en", runChartNoticeKeys).message;
    expect(text("run_chart_not_control_chart")).toContain("must not be interpreted as control-chart");
    expect(text("run_chart_runs_test_defined")).toContain("exact conditional distribution");
    expect(text("run_chart_ties_excluded_from_runs")).toContain("exact above/below run calculation");
    expect(text("run_chart_trend_rule_defined")).toContain("specified minimum run length");
    expect(text("run_chart_oscillation_rule_defined")).toContain("specified minimum run length");
  });

  it("keeps unknown escaped warning meaning and code, including prototype-like codes", () => {
    for (const code of ["run_chart_future_warning", "constructor", "__proto__"]) {
      const stored = Object.freeze({ code, message: '<script>synthetic</script> 사용자 원문' });
      const before = JSON.stringify(stored);
      for (const locale of ["en", "ko"] as const) {
        const html = renderNotice(stored, locale);
        expect(html).toContain(code);
        expect(html).toContain("&lt;script&gt;synthetic&lt;/script&gt; 사용자 원문");
        expect(html).not.toContain("<script>");
        expect(presentApiNotice(stored, locale, runChartNoticeKeys).knownCode).toBe(false);
        expect(JSON.stringify(stored)).toBe(before);
      }
    }
  });

  it("does not translate other methods through shared exclusion codes", () => {
    const stored = { code: "missing_values_excluded", message: "Other method details" };
    expect(presentApiNotice(stored, "en").message).toBe(stored.message);
    expect(presentApiNotice(stored, "en", runChartNoticeKeys).message).toBe("Rows with missing measurements were excluded under the complete-case policy.");
  });
});
