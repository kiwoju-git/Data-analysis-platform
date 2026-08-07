import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { DatasetVersionResponse, EqualVariancesResult } from "./api";
import { EqualVariancesPanel } from "./EqualVariancesPanel";

describe("EqualVariancesPanel", () => {
  it("separates multiple comparisons from Brown-Forsythe Levene and renders intervals", () => {
    const html = renderToString(
      <EqualVariancesPanel
        alpha={0.05}
        analysisResult={null}
        filterValidationError={null}
        groupColumnId="group"
        groupColumns={[]}
        isRunningAnalysis={false}
        methodId="eda.equal_variances"
        responseColumnId="response"
        responseColumns={[]}
        result={currentResult()}
        version={{} as DatasetVersionResponse}
        onAlphaChange={() => undefined}
        onGroupColumnChange={() => undefined}
        onResponseColumnChange={() => undefined}
        onRun={() => undefined}
      />,
    );

    expect(html).toContain("다중 비교</td><td>-");
    expect(html).toContain("Levene 검정 (Brown-Forsythe)");
    expect(html).toContain("표준편차 다중 비교구간");
    expect(html).toContain('role="img"');
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("고전 Levene 검정 (평균 중심)");
  });
});

function currentResult(): EqualVariancesResult {
  const column = (columnId: string, displayName: string) => ({
    column_id: columnId,
    column_index: columnId === "response" ? 0 : 1,
    display_name: displayName,
    data_type: columnId === "response" ? ("decimal" as const) : ("text" as const),
    measurement_level: columnId === "response" ? ("continuous" as const) : ("nominal" as const),
    role: columnId === "response" ? ("response" as const) : ("group" as const),
    unit: null,
  });
  const test = {
    method: "levene_brown_forsythe",
    center: "median",
    computed: true,
    statistic: 1.78106,
    p_value: 0.170707,
    alpha: 0.05,
    reject_equal_variances: false,
    valid_group_n_min: 10,
    warnings: [],
  };
  return {
    schema_version: 2,
    summary_type: "equal_variances_test",
    missing_policy: "complete_case",
    alpha: 0.05,
    package_versions: { numpy: "2.2.6", scipy: "1.15.3" },
    warnings: [],
    response: column("response", "yield_pct"),
    group: column("group", "production_line"),
    n_total: 30,
    n_used: 30,
    n_excluded_missing_response: 0,
    n_excluded_missing_group: 0,
    n_excluded_non_numeric_response: 0,
    group_count: 3,
    groups: [
      groupSummary("Line-A", 0, 12.1, 10.8, 13.6),
      groupSummary("Line-B", 1, 10.3, 9.1, 11.8),
      groupSummary("Line-C", 2, 6.4, 5.3, 7.6),
    ],
    tests: [test],
    multiple_comparisons: {
      computed: true,
      method: "bonett_nakayama_multiple_comparisons",
      alpha: 0.05,
      p_value: 0.145,
      reject_equal_variances: false,
      groups: [
        comparisonGroup("Line-A", 0, 12.1, 10.8, 13.6),
        comparisonGroup("Line-B", 1, 10.3, 9.1, 11.8),
        comparisonGroup("Line-C", 2, 6.4, 5.3, 7.6),
      ],
      non_overlapping_pairs: [{ left_group: "Line-A", right_group: "Line-C" }],
      pairwise_p_values: [{ left_group: "Line-A", right_group: "Line-C", p_value: 0.02 }],
      warnings: [],
    },
    levene: test,
    additional_tests: [{ ...test, method: "levene_mean", center: "mean" }],
  };
}

function groupSummary(
  groupLabel: string,
  groupIndex: number,
  std: number,
  lower: number,
  upper: number,
) {
  return {
    group_label: groupLabel,
    group_index: groupIndex,
    n: 10,
    mean: 90,
    median: 90,
    variance: std * std,
    std,
    min: 70,
    max: 110,
    warnings: [],
    comparison_interval: { lower, upper },
  };
}

function comparisonGroup(
  groupLabel: string,
  groupIndex: number,
  sampleStandardDeviation: number,
  lower: number,
  upper: number,
) {
  return {
    group_label: groupLabel,
    group_index: groupIndex,
    n: 10,
    sample_standard_deviation: sampleStandardDeviation,
    comparison_interval: { lower, upper },
    allocation: 0.0167,
  };
}
