import type { AnalysisReportCapability } from "./api";

/** Catalog registration does not prove that a particular stored payload is renderable. */
export function canCreateHtmlReport(capability: AnalysisReportCapability | null | undefined, analysisId: string, locale: "en" | "ko"): boolean {
  return capability?.analysis_id === analysisId && capability.locale === locale &&
    capability.html_available && capability.report_level !== "unsupported" &&
    /^[a-f0-9]{64}$/.test(capability.source_result_sha256);
}
