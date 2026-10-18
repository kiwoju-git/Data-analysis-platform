import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { AnalysisRunFailure } from "./AnalysisHistoryPanel";
import { getCurrentLocale, setCurrentLocale } from "./i18n/store";

describe("persisted execution failure display", () => {
  const locale = getCurrentLocale();
  afterEach(() => setCurrentLocale(locale));

  it.each(["en", "ko"] as const)("explains interrupted execution in %s without promising cancellation", (language) => {
    setCurrentLocale(language);
    const html = renderToStaticMarkup(<AnalysisRunFailure code="execution_interrupted_on_restart" />);
    expect(html).toContain(language === "en" ? "The previous execution was interrupted" : "앱이 재시작되어 이전 실행이 중단되었습니다.");
    expect(html).toContain("execution_interrupted_on_restart");
    expect(html).not.toContain("button");
    expect(html).not.toContain('role="alert"');
  });

  it("does not add a warning to completed historical results", () => {
    expect(renderToStaticMarkup(<AnalysisRunFailure code={null} />)).toBe("");
  });

  it("escapes unknown reason text without translating its identity", () => {
    setCurrentLocale("en");
    const code = "unknown<script>\uE000private\uE001";
    const html = renderToStaticMarkup(<AnalysisRunFailure code={code} />);
    expect(html).toContain("Failure code");
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).toContain("\uE000private\uE001");
  });
});
