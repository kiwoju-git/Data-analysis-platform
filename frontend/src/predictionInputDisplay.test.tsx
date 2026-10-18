import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { LinearModelResult } from "./api";
import { ApiRequestError } from "./api/client";
import { PasteDatasetPanel } from "./PasteDatasetPanel";
import { RegressionManualPredictionPanel } from "./RegressionManualPredictionPanel";
import {
  manualPredictionErrorDisplay,
  manualPredictionValidationMessage,
  parseImportedRows,
  serializeRows,
  validateRows,
} from "./regressionManualPredictionInput";
import { setCurrentLocale } from "./i18n/store";
import {
  parsePastedTablePreview,
  pastedDelimiterLabel,
  pastedPreviewWarningMessage,
} from "./pastedTablePreview";
import {
  parseRegressionPastedPredictionPreview,
  regressionPredictionPreviewHeaders,
} from "./regressionPastedPredictionPreview";
import type { PastedDatasetDraft } from "./usePastedDatasetDraft";

const harness = vi.hoisted(() => ({ draft: null as PastedDatasetDraft | null }));
vi.mock("./usePastedDatasetDraft", () => ({ usePastedDatasetDraft: () => harness.draft }));

const literalName = "평균 \uE000twoVariances.method\uE001 <column>";
const literalLevel = "필수 값 \uE000twoVariances.method\uE001";

function model(): LinearModelResult {
  return {
    predictors: [
      { column_id: "numeric-id", display_name: literalName, predictor_kind: "numeric" },
      { column_id: "category-id", display_name: "그룹", predictor_kind: "categorical" },
    ],
    training_domain: { predictors: [
      { column_id: "numeric-id", kind: "numeric", minimum: 0, maximum: 10, integer_only: true },
      { column_id: "category-id", kind: "categorical", levels: [literalLevel] },
    ] },
  } as unknown as LinearModelResult;
}

describe("prediction and paste display boundaries", () => {
  afterEach(() => setCurrentLocale("ko"));

  it("preserves the Korean row-label contract and raw predictor names in both locales", () => {
    setCurrentLocale("ko");
    const korean = renderToStaticMarkup(<RegressionManualPredictionPanel modelResult={model()} />);
    expect(korean).toContain('aria-label="1행 평균 \uE000twoVariances.method\uE001 &lt;column&gt;"');
    setCurrentLocale("en");
    const english = renderToStaticMarkup(<RegressionManualPredictionPanel modelResult={model()} />);
    expect(english).toContain('aria-label="Row 1: 평균 \uE000twoVariances.method\uE001 &lt;column&gt;"');
  });

  it("presents local validation codes after a locale switch without exposing invalid values", () => {
    const result = model();
    const rows = [{ id: "row-1", values: { "numeric-id": literalName, "category-id": "invalid" } }];
    const domains = new Map(result.training_domain!.predictors.map((item) => [item.column_id, item]));
    const original = JSON.stringify(rows);
    const issues = validateRows(rows, result, domains);
    expect([...issues.values()]).toEqual(["numeric", "known_level"]);
    expect(manualPredictionValidationMessage("numeric", "en")).toBe("Please enter a number");
    expect(manualPredictionValidationMessage("numeric", "ko")).toBe("숫자를 입력하세요");
    const english = manualPredictionErrorDisplay({ kind: "validation", code: "missing_predictor_header" }, "en");
    expect(english.message).not.toMatch(/[가-힣\uE000\uE001]/u);
    expect(english.code).toBe("missing_predictor_header");
    expect(JSON.stringify(rows)).toBe(original);
    for (const [value, code] of [["NaN", "numeric"], ["Infinity", "numeric"], ["1.25", "integer"]]) {
      expect(validateRows([{ id: "row-2", values: { "numeric-id": value, "category-id": literalLevel } }], result, domains).get("row-2:numeric-id")).toBe(code);
    }
    expect(parseImportedRows("", false, result).error).toBe("no_values");
    expect(parseImportedRows(literalName, true, result).error).toBe("header_without_data");
  });

  it("retains typed request errors for locale-aware presentation without evaluating server prose", () => {
    const cause = new ApiRequestError({ status: 422, code: "gp_prediction_failed",
      backendMessage: literalName, correlationId: literalLevel, routeNotFound: false });
    const state = { kind: "request" as const, cause };
    const en = manualPredictionErrorDisplay(state, "en");
    const ko = manualPredictionErrorDisplay(state, "ko");
    expect(en.code).toBe("gp_prediction_failed");
    expect(en.correlationId).toBe(literalLevel);
    expect(en.message).not.toContain(literalName);
    expect(en.message).not.toMatch(/[가-힣\uE000\uE001]/u);
    expect(ko.message).not.toBe(en.message);
    expect(cause.backendMessage).toBe(literalName);
    expect(manualPredictionErrorDisplay({ kind: "request", cause: new Error(literalName) }, "en").code).toBe("unknown_error");
  });

  it("keeps successful manual import, header identity and serialized values unchanged", () => {
    const result = model();
    const raw = `${literalName}\t그룹\n3\t${literalLevel}`;
    const imported = parseImportedRows(raw, true, result);
    expect(imported.error).toBeNull();
    expect(imported.rows).toEqual([{ "numeric-id": "3", "category-id": literalLevel }]);
    const rows = imported.rows.map((values) => ({ id: "row-1", values }));
    const domains = new Map(result.training_domain!.predictors.map((item) => [item.column_id, item]));
    expect(validateRows(rows, result, domains).size).toBe(0);
    expect(serializeRows(rows, result)).toBe(`numeric-id\tcategory-id\n3\t${literalLevel}`);
    setCurrentLocale("en");
    const en = renderToStaticMarkup(<RegressionManualPredictionPanel modelResult={result} />);
    setCurrentLocale("ko");
    const ko = renderToStaticMarkup(<RegressionManualPredictionPanel modelResult={result} />);
    expect(en).toContain("Required value");
    expect(ko).toContain("필수 값");
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
    expect(en).toContain(`value="${literalLevel}"`);
    expect(parseImportedRows(raw, true, result)).toEqual(imported);
  });

  it("localizes generated prediction headers only, keeping parser headers and user headers literal", () => {
    const generated = parseRegressionPastedPredictionPreview(`3\t${literalLevel}`, "tab", false);
    const original = JSON.stringify(generated);
    setCurrentLocale("en");
    expect(regressionPredictionPreviewHeaders(generated)).toEqual(["input 1", "input 2"]);
    setCurrentLocale("ko");
    expect(regressionPredictionPreviewHeaders(generated)).toEqual(["입력 1", "입력 2"]);
    expect(JSON.stringify(generated)).toBe(original);
    const named = parseRegressionPastedPredictionPreview(`${literalName}\t입력 2\n3\t${literalLevel}`, "tab", true);
    expect(regressionPredictionPreviewHeaders(named, "en")).toEqual([literalName, "입력 2"]);
    expect(named.rows).toEqual([["3", literalLevel]]);
  });

  it("renders coded paste warnings with numeric parameters without changing the raw cells", () => {
    const raw = `${literalName}\tname\n${literalLevel}\t=1+1\nlast\t`;
    const preview = parsePastedTablePreview(raw, { maxRows: 2, maxColumns: 1, maxCells: 2 });
    const original = JSON.stringify(preview);
    const truncated = preview.warnings.find((warning) => warning.code === "paste_preview_truncated")!;
    expect(pastedPreviewWarningMessage(truncated, "en")).toBe(
      "The preview shows up to 2 rows, 1 columns, and 2 cells. The complete original text is submitted unchanged.",
    );
    expect(pastedPreviewWarningMessage(truncated, "ko")).toContain("첫 2행 1열");
    for (const warning of preview.warnings) {
      expect(pastedPreviewWarningMessage(warning, "en")).not.toMatch(/[가-힣\uE000\uE001]/u);
    }
    expect(JSON.stringify(preview)).toBe(original);
    expect(preview.rows[0][0]).toBe(literalName);
    expect(preview.rows[1][0]).toBe(literalLevel);
    const scanned = parsePastedTablePreview(raw, { maxScanCharacters: 12 });
    const scanWarning = scanned.warnings.find((warning) => warning.code === "paste_preview_scan_truncated")!;
    expect(pastedPreviewWarningMessage(scanWarning, "en")).toContain("first 12 characters");
    expect(pastedDelimiterLabel(null, "en")).toBe("single column");
    expect(pastedDelimiterLabel(null, "ko")).toBe("단일 열");
  });

  it("rerenders a stored paste draft warning in both languages without reparsing or editing cells", () => {
    const raw = `${literalName}\tname\n${literalLevel}`;
    const preview = parsePastedTablePreview(raw);
    harness.draft = {
      byteCount: 100, canSubmit: true, characterCount: raw.length, hasHeaderPreview: true,
      mode: "grid", pasteSurfaceRef: { current: null }, rawTextAreaRef: { current: null },
      preview, selection: null, clear: vi.fn(), getRawText: () => raw, getRevision: () => 0, onCellSelect: vi.fn(),
      onDirectPaste: vi.fn(), onRawTextChange: vi.fn(), replace: vi.fn(),
      setHasHeaderPreview: vi.fn(), setMode: vi.fn(),
    };
    setCurrentLocale("en");
    const en = renderToStaticMarkup(<PasteDatasetPanel isSubmitting={false} onRegister={() => Promise.resolve(true)} />);
    setCurrentLocale("ko");
    const ko = renderToStaticMarkup(<PasteDatasetPanel isSubmitting={false} onRegister={() => Promise.resolve(true)} />);
    expect(en).not.toContain("<li>행마다 열 수가 다릅니다.");
    expect(ko).toContain("<li>행마다 열 수가 다릅니다.");
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
    expect(harness.draft.getRawText()).toBe(raw);
  });
});
