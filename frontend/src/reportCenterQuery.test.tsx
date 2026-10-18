import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { ReportCenterFeedback } from "./ReportCenterFeedback";
import { setCurrentLocale } from "./i18n/store";
import {
  readReportSelectionQuery,
  reportRequestErrorCode,
  reportSelectionLocation,
} from "./reportCenterQuery";

const id = "10000000-0000-4000-8000-000000000001";
afterEach(() => setCurrentLocale("ko"));

describe("Report Center query boundary", () => {
  it("validates UUIDs and rejects ambiguous duplicate IDs", () => {
    expect(readReportSelectionQuery("http://localhost/reports")).toEqual({ kind: "absent" });
    expect(readReportSelectionQuery(`http://localhost/reports?analysis_id=${id}`)).toEqual({
      kind: "valid", analysisId: id,
    });
    for (const query of ["analysis_id=", "analysis_id=../other", "analysis_id=%EE%80%80name",
      `analysis_id=${id}&analysis_id=${id}`]) {
      expect(readReportSelectionQuery(`http://localhost/reports?${query}`).kind).toBe("invalid");
    }
  });

  it("updates only selection while preserving unrelated parameters and hash", () => {
    const source = "http://localhost/reports?tab=reports&method_id=eda.descriptive#saved";
    const next = reportSelectionLocation(source, id);
    expect(next).toBe(`/reports?tab=reports&method_id=eda.descriptive&analysis_id=${id}#saved`);
    expect(reportSelectionLocation(`http://localhost${next}`, null)).toBe(
      "/reports?tab=reports&method_id=eda.descriptive#saved",
    );
  });

  it("retains machine error codes but not raw exception text", () => {
    expect(reportRequestErrorCode(new Error("api_unreachable"), "safe_failed")).toBe("api_unreachable");
    expect(reportRequestErrorCode(new Error("User \ue000private & <column>"), "safe_failed")).toBe("safe_failed");
  });

  it("renders recovery guidance in both locales from the same stable code", () => {
    for (const [locale, expected] of [["en", "Retry"], ["ko", "다시 시도"]] as const) {
      setCurrentLocale(locale);
      const markup = renderToStaticMarkup(
        <ReportCenterFeedback code="report_center_result_identity_mismatch" onRetry={() => undefined} />,
      );
      expect(markup).toContain('role="alert"');
      expect(markup).toContain(expected);
      expect(markup).toContain("report_center_result_identity_mismatch");
      const blocked = renderToStaticMarkup(<ReportCenterFeedback code="report_center_current_dataset_required" />);
      expect(blocked).toContain('role="status"');
      expect(blocked).toContain(locale === "en" ? "explicitly view all" : "명시적으로 선택");
    }
  });
});
