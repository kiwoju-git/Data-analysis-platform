import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { PredictionSaveControl } from "./PredictionSaveControl";
import { getCurrentLocale, setCurrentLocale } from "./i18n/store";
import { StoredReportCapabilityPanel } from "./AnalysisReportCapabilityPanel";
import { StoredSourceSnapshotView } from "./ManagedReportsBrowser";
import type { StoredSourceSnapshot } from "./api/types/reports";

describe("explicit managed prediction save display", () => {
  const locale = getCurrentLocale();
  afterEach(() => setCurrentLocale(locale));
  it.each(["en", "ko"] as const)("offers an unchecked opt-in and distinguishes local JSON in %s", (language) => {
    setCurrentLocale(language);
    const html = renderToStaticMarkup(<PredictionSaveControl checked={false} disabled={false} onChange={() => undefined} />);
    expect(html).toContain('type="checkbox"'); expect(html).not.toContain('checked=""');
    expect(html).toContain(language === "en" ? "Save completed prediction" : "완료된 예측 저장");
    expect(html).toContain("JSON"); expect(html).not.toContain("data-saved-prediction");
  });
  it("does not promise generic JSON export for an unknown dedicated source", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<StoredReportCapabilityPanel capability={null} error="report_source_missing" loading={false} onRetry={() => undefined} />);
    expect(html).toContain("Retry the source check"); expect(html).not.toContain("JSON remains available");
  });
  it.each(["en", "ko"] as const)("shows the exact source as escaped read-only JSON, not an HTML report, in %s", (language) => {
    setCurrentLocale(language);
    const snapshot: StoredSourceSnapshot = { schema_version: 1, source: { kind: "analysis_run", analysis_id: "10000000-0000-4000-8000-000000000001", expected_source_sha256: "a".repeat(64) }, source_ref_sha256: "b".repeat(64), locale: language, title: "Synthetic", created_at: "2026-10-18T00:00:00Z", stale: true, payload: { name: "<script>alert(1)</script>\uE000user\uE001", value: .125 } };
    const html = renderToStaticMarkup(<StoredSourceSnapshotView snapshot={snapshot} />);
    expect(html).toContain(language === "en" ? "not a complete HTML analysis report" : "완전한 HTML 분석 보고서가 아닌");
    expect(html).toContain("&lt;script&gt;"); expect(html).not.toContain("<script>");
    expect(html).toContain("\uE000user\uE001"); expect(html).toContain("0.125");
    expect(html).toContain('tabindex="0"'); expect(html).toContain("b".repeat(64));
  });
});
