import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GraphicalSummaryColumnVisuals } from "./GraphicalSummaryColumnVisuals";
import {
  graphPreviewGridClassName,
  graphPreviewPanelClassName,
} from "./graphBuilderLayout";
import type { GraphicalSummaryColumn, GraphPreviewType } from "./api";

describe("Graph Builder layout", () => {
  it.each(["boxplot", "histogram", "qq", "ecdf"] as const)(
    "uses a single-column inner grid for one %s chart",
    (chart) => {
      const html = renderToString(
        <GraphicalSummaryColumnVisuals
          charts={[chart]}
          column={graphicalColumn()}
          mode="full"
        />,
      );

      expect(html).toContain('class="chart-grid chart-grid-single"');
    },
  );

  it("keeps quick and full graphical summaries on their multi-chart grids", () => {
    const quick = renderToString(
      <GraphicalSummaryColumnVisuals column={graphicalColumn()} mode="quick" />,
    );
    const full = renderToString(
      <GraphicalSummaryColumnVisuals column={graphicalColumn()} mode="full" />,
    );

    expect(quick).toContain('class="chart-grid"');
    expect(quick).not.toContain("chart-grid-single");
    expect(full).toContain('class="chart-grid"');
    expect(full).not.toContain("chart-grid-single");
    expect(full).toContain("히스토그램 + 적합 정규곡선");
    expect(full).toContain("Anderson-Darling 정규성 검정");
    expect(full).toContain("5수치 요약");
    expect(full).toContain("추가 그래프: ECDF");
  });

  it.each([
    ["box_plot", "graph-preview-grid-box-plot"],
    ["individual_value_plot", "graph-preview-grid-individual-value-plot"],
    ["histogram", "graph-preview-grid-histogram"],
    ["qq_plot", "graph-preview-grid-qq-plot"],
    ["ecdf", "graph-preview-grid-ecdf"],
    ["scatter_plot", "graph-preview-grid-scatter-plot"],
    ["run_chart", "graph-preview-grid-run-chart"],
    ["imr_chart", "graph-preview-grid-imr-chart"],
  ] as Array<[GraphPreviewType, string]>)(
    "adds a stable result-grid class for %s",
    (graphType, expectedClass) => {
      expect(graphPreviewGridClassName(graphType)).toContain(expectedClass);
    },
  );

  it("reserves full rows for individual-value and I-MR variable cards", () => {
    expect(graphPreviewPanelClassName("individual_values")).toContain(
      "graph-preview-card-full-row",
    );
    expect(graphPreviewPanelClassName("imr_chart")).toContain(
      "graph-preview-card-full-row",
    );
    expect(graphPreviewPanelClassName("run_chart")).not.toContain(
      "graph-preview-card-full-row",
    );
  });
});

function graphicalColumn(): GraphicalSummaryColumn {
  return {
    column_id: "column-1",
    column_index: 0,
    display_name: "temperature_c",
    data_type: "decimal",
    measurement_level: "continuous",
    role: "feature",
    unit: "C",
    n_total: 10,
    n_used: 9,
    n_missing: 1,
    n_non_numeric: 0,
    min: 1,
    q1: 2,
    median: 2.5,
    q3: 3,
    max: 4,
    histogram: {
      binning: "freedman_diaconis",
      bin_count: 1,
      bins: [
        {
          lower: 1,
          upper: 4,
          count: 9,
          include_lower: true,
          include_upper: true,
        },
      ],
    },
    boxplot: {
      lower_whisker: 1,
      q1: 2,
      median: 2.5,
      q3: 3,
      upper_whisker: 4,
      lower_fence: 0.5,
      upper_fence: 4.5,
      outlier_count: 0,
    },
    qq_plot: {
      point_count: 2,
      points_truncated: false,
      points: [
        { theoretical: -0.5, sample: 1 },
        { theoretical: 0.5, sample: 4 },
      ],
    },
    ecdf: {
      point_count: 2,
      points_truncated: false,
      points: [
        { x: 1, probability: 0.5 },
        { x: 4, probability: 1 },
      ],
    },
    warnings: [],
  };
}
