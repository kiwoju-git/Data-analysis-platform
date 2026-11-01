import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { GageRrPreflightPanel } from "./GageRrPreflightPanel";
import type { DatasetVersionResponse } from "./api";
import { setCurrentLocale } from "./i18n/store";

const version: DatasetVersionResponse = {
  version_id: "synthetic-version", dataset_id: "synthetic-dataset", version_number: 1,
  row_count: 60, column_count: 3, schema_hash: "synthetic-hash", created_at: "2026-11-01T00:00:00Z", source_sha256: "synthetic-source",
  parsing: { kind: "delimited_text", encoding: "utf-8", delimiter: ",", quote_char: '"', decimal: ".", thousands: null, has_header: true, header_row: 1, data_start_row: 2, missing_tokens: [], xlsx_sheet_name: null }, columns: [], canonical_artifact: null,
};
const props = {
  version, analysisResult: null, error: null, filterValidationError: null,
  isRunning: false, measurementColumnId: "y", partColumnId: "p", operatorColumnId: "o", replicateColumnId: null,
  measurementColumns: [], partColumns: [], operatorColumns: [], replicateColumns: [],
  methodId: "quality.gage_rr", preflight: null, result: null,
  onMeasurementColumnChange() {}, onPartColumnChange() {}, onOperatorColumnChange() {}, onReplicateColumnChange() {}, onRunAnalysis() {}, onRunPreflight() {},
};

describe("Gage R&R three-column form", () => {
  it("can execute with three roles before any explicit preflight", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<GageRrPreflightPanel {...props} />);
    expect(html).toContain('value="infer_from_rows" selected');
    expect(html).toContain('value="auto_pool" selected');
    expect(html).not.toMatch(/class="primary-button" disabled/);
    expect(html).toContain("separate replicate-ID column is optional");
  });
  it("requires a fourth distinct role only in explicit mode", () => {
    setCurrentLocale("ko");
    const html = renderToStaticMarkup(<GageRrPreflightPanel {...props} replicateMode="explicit_column" />);
    expect(html).toMatch(/class="primary-button" disabled/);
    expect(html).toContain("반복번호");
    const duplicate = renderToStaticMarkup(<GageRrPreflightPanel {...props} replicateMode="explicit_column" replicateColumnId="p" />);
    expect(duplicate).toMatch(/class="primary-button" disabled/);
  });
  it("does not allow a bad filter to reuse prior ready status", () => {
    const html = renderToStaticMarkup(<GageRrPreflightPanel {...props} filterValidationError="invalid_filter" />);
    expect(html).toMatch(/class="primary-button" disabled/);
  });
});
