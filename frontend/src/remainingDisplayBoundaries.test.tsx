import type { ComponentProps, ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AnalysisResultExportPanel } from "./AnalysisResultExportPanel";
import type { AnalysisResultEnvelope, DatasetColumnResponse } from "./api";
import { exportKindLabel } from "./analysisWorkbenchUtils";
import { DoeFactorEditor } from "./doe/DoeFormPrimitives";
import { GraphVariablePicker } from "./GraphVariablePicker";
import {
  generalFactorialDraftIssueLabel,
  validateGeneralDraft,
  type GeneralFactorDraft,
  type GeneralFactorialDraftIssue,
} from "./generalFactorialDraft";
import { LocaleProvider } from "./i18n/LocaleProvider";
import { setCurrentLocale } from "./i18n/store";
import { translateSystemText } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

const rawText = "선택 \uE000startup.failed\uE001";

function markup(node: ReactNode, locale: AppLocale): string {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  return renderToStaticMarkup(<LocaleProvider>{node}</LocaleProvider>);
}

function factor(id: string, levels = ["1", "2"]): GeneralFactorDraft {
  return { id, name: id, levelType: "categorical", levels, unit: rawText, expanded: true, pasteDraft: "" };
}

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("ko"); });

describe("remaining static display boundaries", () => {
  it("localizes graph selection guidance while preserving the label, column and selection", () => {
    const column: DatasetColumnResponse = {
      column_id: "raw-column", version_id: "version-1", column_index: 0,
      original_name: rawText, display_name: rawText, data_type: "decimal",
      measurement_level: "continuous", role: "feature", unit: rawText,
    };
    const props = { columns: [column], label: rawText, selectedIds: [column.column_id], maximum: 1, onChange: vi.fn() };
    const snapshot = JSON.stringify(props);
    for (const locale of ["en", "ko", "en"] as const) {
      const html = markup(<GraphVariablePicker {...props} />, locale);
      expect(html).toContain(`${translateSystemText("선택", locale)} 1 / 1`);
      expect(html).toContain(translateSystemText("개를 선택했습니다. 다른 변수를 선택하려면 하나를 해제하세요.", locale));
      expect(html).toContain(`<legend>${rawText}</legend>`);
      expect(html).toContain(`<strong>${rawText}</strong>`);
      expect(html).toContain(`<small>${rawText}</small>`);
      expect(html).toContain('checked=""');
      expect(JSON.stringify(props)).toBe(snapshot);
      expect(props.onChange).not.toHaveBeenCalled();
    }
  });

  it("translates only the DOE editor default title, not caller-provided text", () => {
    for (const locale of ["en", "ko", "en"] as const) {
      const defaultHtml = markup(<DoeFactorEditor>body</DoeFactorEditor>, locale);
      expect(defaultHtml).toContain(translateSystemText("요인 범위", locale));
      const title = `${rawText} <img src=x onerror=alert(1)>`;
      const userHtml = markup(<DoeFactorEditor title={title}>body</DoeFactorEditor>, locale);
      expect(userHtml).toContain(`${rawText} &lt;img src=x onerror=alert(1)&gt;`);
      expect(userHtml).not.toContain("<img");
    }
  });

  it("keeps general factorial validation as codes and parameters until display", () => {
    const valid = [factor("A"), factor("B")];
    const cases: Array<[GeneralFactorialDraftIssue, ReturnType<typeof validateGeneralDraft>]> = [
      [{ code: "invalid_design_settings" }, validateGeneralDraft("", valid, "1", "1", false, "2")],
      [{ code: "invalid_interaction_order" }, validateGeneralDraft("design", valid, "1", "1", false, "3")],
      [{ code: "invalid_factor_definitions" }, validateGeneralDraft("design", [factor("A"), factor("A")], "1", "1", false, "2")],
      [{ code: "invalid_level_values" }, validateGeneralDraft("design", [factor("A", ["", "2"]), factor("B")], "1", "1", false, "2")],
      [{ code: "duplicate_levels" }, validateGeneralDraft("design", [factor("A", ["x", "x"]), factor("B")], "1", "1", false, "2")],
      [{ code: "run_limit_exceeded", runCount: 260 }, validateGeneralDraft("design", valid, "65", "1", false, "2")],
    ];
    for (const [issue, validation] of cases) {
      expect(validation.issue).toEqual(issue);
      expect(validation.request).toBeNull();
      const snapshot = JSON.stringify(validation);
      const ko = generalFactorialDraftIssueLabel(issue, "ko");
      const en = generalFactorialDraftIssueLabel(issue, "en");
      expect(ko).toMatch(/[\uAC00-\uD7A3]/u);
      expect(en).not.toMatch(/[\uAC00-\uD7A3]/u);
      expect(generalFactorialDraftIssueLabel(issue, "ko")).toBe(ko);
      expect(JSON.stringify(validation)).toBe(snapshot);
    }
    expect(generalFactorialDraftIssueLabel({ code: "run_limit_exceeded", runCount: 260 }, "en")).toContain("260");
  });

  it("never localizes valid general factorial names, levels or request fields", () => {
    const factors = [factor(rawText, [rawText, "반응"]), factor("B", ["low", "high"])];
    const snapshot = JSON.stringify(factors);
    const expected = {
      name: rawText, factors: [
        { name: rawText, levels: [rawText, "반응"], unit: rawText },
        { name: "B", levels: ["low", "high"], unit: rawText },
      ], replicates: 1, randomize: false, randomization_seed: 1, max_interaction_order: 2,
    };
    for (const locale of ["en", "ko", "en"] as const) {
      setCurrentLocale(locale);
      const validation = validateGeneralDraft(rawText, factors, "1", "1", false, "2");
      expect(validation.issue).toBeNull();
      expect(validation.request).toEqual(expected);
      expect(JSON.stringify(factors)).toBe(snapshot);
    }
  });

  it("keeps export format IDs and unknown kinds raw while translating action text", () => {
    expect(exportKindLabel("analysis_result_json_export")).toBe("JSON");
    expect(exportKindLabel("analysis_result_csv_export")).toBe("CSV");
    expect(exportKindLabel("analysis_result_html_report")).toBe("HTML");
    expect(exportKindLabel(rawText)).toBe(rawText);
    const props = exportProps();
    const snapshot = JSON.stringify(props);
    for (const locale of ["en", "ko", "en"] as const) {
      const html = markup(<AnalysisResultExportPanel {...props} />, locale);
      expect(html).toContain(`JSON ${translateSystemText("생성", locale)}`);
      expect(html).toContain(`CSV ${translateSystemText("생성 중", locale)}`);
      expect(html).toContain(`CSV ${translateSystemText("다운로드", locale)}`);
      expect(html).toContain(rawText);
      expect(JSON.stringify(props)).toBe(snapshot);
      expect(markup(<AnalysisResultExportPanel {...props} isDownloadingExport />, locale))
        .toContain(translateSystemText("다운로드 중", locale));
    }
  });
});

function exportProps(): ComponentProps<typeof AnalysisResultExportPanel> {
  return {
    analysisResult: { analysis_id: "analysis-1", method_id: rawText, status: "succeeded" } as AnalysisResultEnvelope,
    csvExportError: null, csvExportResult: {
      schema_version: 1, export_id: "export-1", analysis_id: "analysis-1",
      format: "analysis_result_csv", artifact_kind: "analysis_result_csv_export",
      media_type: "text/csv", sha256: "export-hash", size_bytes: 100,
      source_result_sha256: "source-hash", stale: false, created_at: "2026-10-18T00:00:00Z",
      columns: [rawText], row_count: 1, preview_rows: [[rawText]],
    }, deletion: null, deletionError: null,
    deletionPreflight: null, downloadError: null, exportError: null, exportList: null,
    exportListError: null, exportResult: null, htmlReportError: null, htmlReportResult: null,
    isExportingCsv: true, isExportingHtml: false, isExportingJson: false,
    isDownloadingExport: false, isDeletingExport: false, isLoadingExportList: false,
    isLoadingDeletionPreflight: false, onCreateCsvExport: vi.fn(), onCreateExport: vi.fn(),
    onCreateHtmlReport: vi.fn(), onDownloadExport: vi.fn(), onLoadDeletionPreflight: vi.fn(),
    onDeleteExport: vi.fn(), onClearDeletion: vi.fn(),
  };
}
