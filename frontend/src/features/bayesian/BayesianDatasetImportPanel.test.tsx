import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { DatasetVersionResponse } from "../../api";
import { setCurrentLocale } from "../../i18n/store";
import { BayesianDatasetImportPanel } from "./BayesianDatasetImportPanel";

const version: DatasetVersionResponse = {
  version_id: "synthetic-version", dataset_id: "synthetic-dataset", version_number: 1,
  row_count: 8, column_count: 0, schema_hash: "a".repeat(64), source_sha256: "b".repeat(64),
  created_at: "2026-11-12T00:00:00Z", columns: [], canonical_artifact: null,
  parsing: { kind: "delimited_text", encoding: "utf-8", delimiter: ",", quote_char: '"', decimal: ".",
    thousands: null, has_header: true, header_row: 1, data_start_row: 2, missing_tokens: [""], xlsx_sheet_name: null },
};

describe("dataset import field labels", () => {
  afterEach(() => setCurrentLocale("ko"));
  it.each([
    { locale: "en" as const, labels: ["Response objective", "Goal", "Missing-data policy"] },
    { locale: "ko" as const, labels: ["반응 목표", "목표", "결측 처리"] },
  ])("gives mode, goal and missing policy exact accessible labels ($locale)", ({ locale, labels }) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<BayesianDatasetImportPanel version={version}
      filterSnapshot={{ expression_version: 1, conditions: [] }} ownerKey="new" disabled={false}
      onBusyChange={() => undefined} onCreated={() => undefined} />);
    for (const label of labels) expect(html).toContain(`<select aria-label="${label}"`);
    expect(html).toContain(locale === "en" ? "Start from existing X/Y" : "기존 X/Y로 시작");
    expect(html).toContain(locale === "en" ? "<details><summary>Advanced options</summary>" : "<details><summary>고급 옵션</summary>");
    expect(html).toContain(locale === "en" ? "Actual-unit numeric constraints" : "실제 단위 숫자 요인 제약");
  });
});
