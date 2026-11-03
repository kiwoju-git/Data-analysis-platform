import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GageRrPreflightPanel } from "./GageRrPreflightPanel";
import type { DatasetVersionResponse, GageRrResult } from "./api";
import { setCurrentLocale } from "./i18n/store";
import { t } from "./i18n/translate";

vi.mock("./GageRrResultCharts", () => ({ GageRrResultCharts: () => null }));
afterEach(() => setCurrentLocale("en"));
const fixtures = JSON.parse(readFileSync(new URL("../../tests/fixtures/gage_rr_six_panel.json", import.meta.url), "utf8")) as { retain: GageRrResult };

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
  it.each(["ko", "en"] as const)("localizes stored policy and ANOVA/component labels without rewriting values in %s", (locale) => {
    setCurrentLocale(locale);
    const result = structuredClone(fixtures.retain);
    result.anova_table[0].p_value = 1e-10;
    result.full_anova_table![0].p_value = 1e-10;
    result.variance_components.repeatability.percent_contribution = 1e-10;
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(<GageRrPreflightPanel {...props} result={result} />);
    expect(html).toContain(`aria-label="${t("gage.followup.replicateMode")}"`);
    expect(html).toContain('data-gage-control="interaction-policy"');
    expect(html).toContain(t("gage.charts.repeatability"));
    expect(html).toContain(t("gage.charts.operatorAxis"));
    expect(html).toContain(t("gage.followup.reason.retained_by_request"));
    expect(html.match(/<td>1e-10<\/td>/g)).toHaveLength(2);
    expect(html).toContain("1e-10%");
    expect(JSON.stringify(result)).toBe(before);
  });
  it("shows legacy explicit/retain policy without assigning a new pooling decision", () => {
    setCurrentLocale("en");
    const result = structuredClone(fixtures.retain);
    result.schema_version = 1;
    delete result.interaction_selection;
    delete result.replicate_mode;
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(<GageRrPreflightPanel {...props} result={result} />);
    expect(html).toContain("(explicit_column)");
    expect(html).toContain("(retain)");
    expect(html).not.toContain(t("gage.followup.reason.interaction_not_significant"));
    expect(JSON.stringify(result)).toBe(before);
  });
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
