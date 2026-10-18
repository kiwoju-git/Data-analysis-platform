import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { AnalysisReportCapability } from "./api";
import { AnalysisReportCapabilityPanel } from "./AnalysisReportCapabilityPanel";
import { canCreateHtmlReport } from "./reportCenterCapabilities";
import { getCurrentLocale, setCurrentLocale } from "./i18n/store";

const capability: AnalysisReportCapability = {
  capability_schema_version: 1, analysis_id: "analysis-a", method_id: "legacy.unknown",
  summary_type: "legacy", result_schema_version: 1, source_result_sha256: "a".repeat(64),
  stale: true, locale: "en", renderer_id: "summary", renderer_version: "1", variant_id: "legacy",
  report_level: "summary", html_available: true, reason: "partial_stored_payload",
  source_validation: "stored_dependencies_only",
  sections: [
    { section_id: "data", title: "User <name> \uE000[untranslated]", status: "rendered", reason: null },
    { section_id: "plot", title: "Plot", status: "missing", reason: "stored_plot_unavailable" },
  ],
};

describe("backend-authoritative report capability", () => {
  const initialLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(initialLocale));

  it("requires the exact owner, locale, available level and hash rather than a method allowlist", () => {
    expect(canCreateHtmlReport(null, "analysis-a", "en")).toBe(false);
    expect(canCreateHtmlReport(capability, "analysis-b", "en")).toBe(false);
    expect(canCreateHtmlReport(capability, "analysis-a", "ko")).toBe(false);
    expect(canCreateHtmlReport({ ...capability, report_level: "unsupported" }, "analysis-a", "en")).toBe(false);
    expect(canCreateHtmlReport({ ...capability, source_result_sha256: "bad" }, "analysis-a", "en")).toBe(false);
    expect(canCreateHtmlReport(capability, "analysis-a", "en")).toBe(true);
  });

  it("preserves localized coverage, missing reasons, stale provenance and literal user text", () => {
    const before = JSON.stringify(capability);
    setCurrentLocale("en");
    const english = renderToStaticMarkup(<AnalysisReportCapabilityPanel capability={capability} error={null} loading={false} />);
    expect(english).toContain("Summary report");
    expect(english).toContain("stored dependencies only");
    expect(english).toContain("stored_plot_unavailable");
    expect(english).toContain("User &lt;name&gt; \uE000[untranslated]");
    expect(english).toContain("stored analysis is stale");
    setCurrentLocale("ko");
    const korean = renderToStaticMarkup(<AnalysisReportCapabilityPanel capability={capability} error={null} loading={false} />);
    expect(korean).toContain("요약 보고서");
    expect(korean).toContain("제공 불가");
    expect(korean).toContain("User &lt;name&gt; \uE000[untranslated]");
    expect(JSON.stringify(capability)).toBe(before);
  });

  it("does not describe unknown or unsupported results as complete reports", () => {
    setCurrentLocale("en");
    const unknown = renderToStaticMarkup(<AnalysisReportCapabilityPanel capability={null} error="network_error" loading={false} onRetry={() => undefined} />);
    expect(unknown).toContain('role="alert"');
    expect(unknown).toContain("JSON remains available");
    expect(unknown).toContain("Retry");
    const unsupported = renderToStaticMarkup(<AnalysisReportCapabilityPanel capability={{ ...capability, html_available: false, report_level: "unsupported" }} error={null} loading={false} />);
    expect(unsupported).toContain("HTML is unavailable");
    expect(unsupported).not.toContain("Full report:");
  });
});
