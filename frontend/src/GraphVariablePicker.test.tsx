import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { DatasetColumnResponse, DatasetVersionResponse } from "./api";
import { GraphBuilderPage } from "./GraphBuilderPage";
import { GraphVariablePicker } from "./GraphVariablePicker";
import { toggleGraphVariableSelection } from "./graphVariableSelection";

describe("GraphVariablePicker", () => {
  it("shows selection count, units, long labels, and the clear action", () => {
    const html = renderToString(
      <GraphVariablePicker
        columns={[
          column("temperature", "temperature_c_with_a_long_process_suffix", "C"),
          column("pressure", "pressure_bar", null),
        ]}
        label="표시할 수치 변수"
        maximum={12}
        onChange={vi.fn()}
        selectedIds={["temperature"]}
      />,
    );

    expect(html).toContain("선택 1 / 12");
    expect(html).toContain("temperature_c_with_a_long_process_suffix");
    expect(html).toContain("<small>C</small>");
    expect(html).toContain("모두 지우기");
    expect(html).toContain("graph-variable-option is-selected");
    expect((html.match(/<small>/g) ?? [])).toHaveLength(1);
  });

  it("disables only unchecked options after the maximum is reached", () => {
    const html = renderToString(
      <GraphVariablePicker
        columns={[
          column("a", "a", null),
          column("b", "b", null),
          column("c", "c", null),
        ]}
        label="Y 변수"
        maximum={2}
        onChange={vi.fn()}
        selectedIds={["a", "b"]}
      />,
    );

    expect(html).toContain("선택 2 / 2");
    expect(html).toContain("최대 2개를 선택했습니다");
    expect((html.match(/disabled=""/g) ?? [])).toHaveLength(1);
    expect((html.match(/checked=""/g) ?? [])).toHaveLength(2);
  });

  it("disables an axis already used by the fixed scatter role", () => {
    const html = renderToString(
      <GraphVariablePicker
        columns={[column("x", "fixed_x", null), column("y", "candidate_y", null)]}
        disabledIds={["x"]}
        label="Y variables"
        maximum={6}
        onChange={vi.fn()}
        selectedIds={["y"]}
      />,
    );

    expect((html.match(/disabled=""/g) ?? [])).toHaveLength(1);
    expect((html.match(/checked=""/g) ?? [])).toHaveLength(1);
  });

  it("keeps selected options removable and never silently exceeds the maximum", () => {
    expect(toggleGraphVariableSelection(["a", "b"], "a", 2)).toEqual(["b"]);
    expect(toggleGraphVariableSelection(["a", "b"], "c", 2)).toEqual(["a", "b"]);
    expect(toggleGraphVariableSelection(["a"], "b", 2)).toEqual(["a", "b"]);
  });

  it("retains native checkbox and radio semantics in the Graph Builder", () => {
    const html = renderToString(
      <GraphBuilderPage
        catalog={null}
        version={version()}
        onOpenAnalysis={vi.fn()}
      />,
    );

    expect(html).toContain('class="graph-variable-picker"');
    expect(html).toContain('type="checkbox"');
    expect(html).toContain('class="graph-layout-control"');
    expect((html.match(/type="radio"/g) ?? [])).toHaveLength(4);
    expect(html).toContain("비교 방식");
    expect(html).toContain("수치 변수 1개를 그룹별 비교");
    expect(html).toContain("공통 축");
    expect(html).toContain("개별 패널");
  });
});

function column(
  columnId: string,
  displayName: string,
  unit: string | null,
): DatasetColumnResponse {
  return {
    column_id: columnId,
    version_id: "version-1",
    column_index: 0,
    original_name: displayName,
    display_name: displayName,
    data_type: "decimal",
    measurement_level: "continuous",
    role: "feature",
    unit,
  };
}

function version(): DatasetVersionResponse {
  return {
    version_id: "version-1",
    dataset_id: "dataset-1",
    version_number: 1,
    row_count: 20,
    column_count: 2,
    schema_hash: "schema-hash",
    created_at: "2026-07-25T00:00:00Z",
    source_sha256: "source-sha",
    columns: [
      column("temperature", "temperature_c", "C"),
      column("pressure", "pressure_bar", "bar"),
    ],
    parsing: {
      kind: "delimited_text",
      encoding: "utf-8",
      delimiter: ",",
      quote_char: '"',
      decimal: ".",
      thousands: null,
      has_header: true,
      header_row: 0,
      data_start_row: 1,
      missing_tokens: [],
      xlsx_sheet_name: null,
    },
    canonical_artifact: null,
  };
}
