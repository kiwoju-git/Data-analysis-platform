import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ActiveDatasetVersionSelector } from "./ActiveDatasetVersionSelector";
import { DescriptiveAnalysisPanel } from "./DescriptiveAnalysisPanel";
import type {
  DatasetVersionResponse,
  DescriptiveStatisticsResult,
  GraphicalSummaryResult,
} from "./api";
import { InteractiveBoxplotChart } from "./charts/InteractiveBoxplotChart";
import { layoutBoxplotMarkers } from "./charts/boxplotMarkerLayout";
import { formatLocalDateTime } from "./dateFormat";
import type { DatasetVersionCatalogState } from "./useDatasetVersionCatalogState";

describe("EDA usability foundations", () => {
  it("groups coincident boxplot markers and keeps labels inside the plot", () => {
    const labels = layoutBoxplotMarkers(
      [
        { key: "lower", label: "Lower whisker", value: -10, x: 20 },
        { key: "q1", label: "Q1", value: 5, x: 150 },
        { key: "median", label: "Median", value: 5, x: 150 },
        { key: "q3", label: "Q3", value: 5, x: 150 },
        { key: "upper", label: "Upper whisker", value: 1_000_000, x: 380 },
      ],
      80,
      20,
      380,
    );

    expect(labels).toHaveLength(3);
    expect(labels[1].label).toBe("Q1 · Median · Q3");
    expect(labels[0].anchor).toBe("start");
    expect(labels[2].anchor).toBe("end");
    expect(labels.every((label) => label.row === 0)).toBe(true);
    expect(labels.every((label, index) => index === 0 || label.x > labels[index - 1].x)).toBe(
      true,
    );
  });

  it("always renders the five primary boxplot values without fabricating outlier points", () => {
    const html = renderToString(
      <InteractiveBoxplotChart
        boxplot={{
          lower_fence: -3,
          lower_whisker: -2,
          q1: 1,
          median: 1,
          q3: 4,
          upper_whisker: 10,
          upper_fence: 13,
          outlier_count: 2,
        }}
        chartId="box"
        columnName="온도"
      />,
    );

    expect(html).toContain('data-marker="lower-whisker"');
    expect(html).toContain('data-marker="q1"');
    expect(html).toContain('data-marker="median"');
    expect(html).toContain('data-marker="q3"');
    expect(html).toContain('data-marker="upper-whisker"');
    expect(html).toContain('aria-label="Q1 · Median: 1"');
    expect(html).not.toContain("<tspan>Lower whisker</tspan>");
    expect(html).toContain("outliers");
    expect(html).toContain(">2</text>");
  });

  it("renders the selected descriptive quick graph directly below its table row", () => {
    const graphical = graphicalResult();
    const descriptive: DescriptiveStatisticsResult = {
      schema_version: 1,
      summary_type: "descriptive_statistics",
      missing_policy: "available_case_by_column",
      quartile_method: "linear",
      std_definition: "sample",
      columns: [
        {
          column_id: "column-1",
          column_index: 0,
          display_name: "온도",
          data_type: "decimal",
          measurement_level: "continuous",
          role: "feature",
          unit: null,
          n_total: 10,
          n_used: 9,
          n_missing: 1,
          n_non_numeric: 0,
          mean: 2.5,
          std: 1,
          min: 1,
          q1: 2,
          median: 2.5,
          q3: 3,
          max: 4,
          warnings: [],
        },
      ],
    };
    const html = renderToString(
      <DescriptiveAnalysisPanel
        analysisResult={null}
        descriptiveColumns={[]}
        descriptiveResult={descriptive}
        filterValidationError={null}
        isRunningAnalysis={false}
        methodId="eda.descriptive"
        quickGraphState={{
          columnId: "column-1",
          error: null,
          result: graphical,
          status: "ready",
        }}
        selectedColumnIds={["column-1"]}
        version={{ version_id: "version-1" } as DatasetVersionResponse}
        onRun={vi.fn()}
        onToggleColumn={vi.fn()}
      />,
    );

    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain('<span class="descriptive-column-name">온도</span>');
    expect(html).toContain('class="descriptive-graph-button"');
    expect(html).toContain(">그래프</button>");
    expect(html).toContain("그래프 요약에서 전체 보기");
    expect(html).toContain("히스토그램");
    expect(html).toContain("박스플롯");
    expect(html).not.toContain("Q-Q Plot");
  });

  it("formats created_at and safely falls back for invalid timestamps", () => {
    expect(formatLocalDateTime("2026-07-23T05:32:00+00:00")).toMatch(
      /2026.*07.*23.*\d{2}.*\d{2}/,
    );
    expect(formatLocalDateTime("not-a-date")).toBe("날짜 확인 불가");
  });

  it("includes created_at in current and off-page dataset labels", () => {
    const version = {
      version_id: "1234567890abcdef",
      created_at: "2026-07-23T05:32:00+00:00",
      row_count: 240,
      column_count: 15,
      version_number: 1,
      schema_hash: "abcdef0123456789",
    } as DatasetVersionResponse;
    const item = {
      version_id: version.version_id,
      dataset_id: "dataset-1",
      original_filename: "pasted-data.txt",
      version_number: 1,
      row_count: 240,
      column_count: 15,
      created_at: version.created_at,
      user_label: "공정 데이터",
      note: null,
      pinned: false,
      metadata_updated_at: null,
    };
    const catalogState = {
      activeItem: item,
      catalog: null,
      error: null,
      isLoading: false,
      isResolvingActiveItem: false,
      onPageChange: vi.fn(),
      onRefresh: vi.fn(),
    } as unknown as DatasetVersionCatalogState;
    const html = renderToString(
      <ActiveDatasetVersionSelector
        catalogState={catalogState}
        isSwitching={false}
        pendingVersionId={null}
        version={version}
        onRetrySwitch={vi.fn()}
        onSelect={vi.fn()}
      />,
    );

    expect(html).toContain("공정 데이터");
    expect(html).toContain("pasted-data.txt");
    expect(html).toContain("240행");
    expect(html).toContain("15열");
    expect(html).toContain("생성");
    expect(html).toContain("v1");
    expect(html).toContain("12345678");
  });
});

function graphicalResult(): GraphicalSummaryResult {
  return {
    schema_version: 1,
    summary_type: "graphical_summary",
    histogram_method: "freedman_diaconis",
    boxplot_method: "tukey",
    qq_plot_distribution: "normal",
    qq_plotting_position: "filliben",
    ecdf_method: "empirical",
    point_limit: 1000,
    columns: [
      {
        column_id: "column-1",
        column_index: 0,
        display_name: "온도",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "feature",
        unit: null,
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
        qq_plot: { point_count: 0, points_truncated: false, points: [] },
        ecdf: { point_count: 0, points_truncated: false, points: [] },
        warnings: [],
      },
    ],
  };
}
