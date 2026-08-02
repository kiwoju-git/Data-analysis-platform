import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { DatasetColumnResponse, DatasetVersionResponse, EquivalenceTostResult } from "./api";
import { EquivalenceResultView } from "./EquivalenceResultView";
import { PairedEquivalencePanel } from "./PairedEquivalencePanel";
import { TwoSampleEquivalencePanel } from "./TwoSampleEquivalencePanel";

describe("equivalence designs", () => {
  it("keeps explicit test/reference groups and Welch as the independent default", () => {
    const numeric = column("response", "yield_pct", "decimal");
    const group = column("group", "production_line", "text");
    const html = renderToStaticMarkup(
      <TwoSampleEquivalencePanel
        alpha={0.05}
        analysisResult={null}
        filterDrafts={[]}
        filterValidationError={null}
        groupColumnId={group.column_id}
        groupColumns={[group]}
        isRunningAnalysis={false}
        lowerBound={-1}
        methodId="hypothesis.two_sample_equivalence_tost"
        responseColumnId={numeric.column_id}
        responseColumns={[numeric]}
        result={null}
        upperBound={1}
        varianceAssumption="welch"
        version={version([numeric, group])}
        onAlphaChange={vi.fn()}
        onGroupColumnChange={vi.fn()}
        onLowerBoundChange={vi.fn()}
        onResponseColumnChange={vi.fn()}
        onRun={vi.fn()}
        onUpperBoundChange={vi.fn()}
        onVarianceAssumptionChange={vi.fn()}
      />,
    );
    expect(html).toContain("시험 그룹");
    expect(html).toContain("기준 그룹");
    expect(html).toContain("등분산 가정 안 함 (Welch)");
    expect(html).toContain("시험 그룹 - 기준 그룹");
  });

  it("uses explicit wide paired columns and complete-pair wording", () => {
    const test = column("test", "after", "decimal");
    const reference = column("reference", "before", "decimal");
    const html = renderToStaticMarkup(
      <PairedEquivalencePanel
        alpha={0.05}
        analysisResult={null}
        filterValidationError={null}
        isRunningAnalysis={false}
        lowerBound={-0.5}
        methodId="hypothesis.paired_equivalence_tost"
        referenceColumnId={reference.column_id}
        responseColumns={[test, reference]}
        result={null}
        testColumnId={test.column_id}
        upperBound={0.5}
        version={version([test, reference])}
        onAlphaChange={vi.fn()}
        onLowerBoundChange={vi.fn()}
        onReferenceColumnChange={vi.fn()}
        onRun={vi.fn()}
        onTestColumnChange={vi.fn()}
        onUpperBoundChange={vi.fn()}
      />,
    );
    expect(html).toContain("시험 측정");
    expect(html).toContain("기준 측정");
    expect(html).toContain("complete pair");
    expect(html).toContain("시험 측정 - 기준 측정");
  });

  it("renders bounds, CI, keyboard-focusable estimate, and qualified decision text", () => {
    const html = renderToStaticMarkup(<EquivalenceResultView analysisResult={null} result={result()} />);
    expect(html).toContain("동등성 신뢰구간");
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("동등성 근거 있음");
    expect(html).toContain("일반 t-검정에서 차이가 유의하지 않았다는 사실만으로 동등하다고 결론낼 수 없습니다");
    expect(html).toContain("완전한 쌍");
  });
});

function column(id: string, name: string, dataType: "decimal" | "text"): DatasetColumnResponse {
  return {
    version_id: "version-1",
    column_id: id,
    column_index: id === "reference" || id === "group" ? 1 : 0,
    original_name: name,
    display_name: name,
    data_type: dataType,
    measurement_level: dataType === "decimal" ? "continuous" : "nominal",
    role: "unspecified",
    unit: null,
  } as DatasetColumnResponse;
}

function version(columns: DatasetColumnResponse[]): DatasetVersionResponse {
  return { version_id: "version-1", columns } as DatasetVersionResponse;
}

function result(): EquivalenceTostResult {
  const testColumn = column("test", "after", "decimal");
  const referenceColumn = column("reference", "before", "decimal");
  return {
    schema_version: 2,
    summary_type: "equivalence_tost",
    method: "paired_mean_difference_tost",
    input_mode: "dataset_wide_paired_columns",
    design: "paired_mean_difference",
    difference_definition: "test_minus_reference",
    missing_policy: "complete_pair",
    alpha: 0.05,
    confidence_level: 0.9,
    reference_mean: null,
    equivalence_bounds: { lower: -0.5, upper: 0.5, scale: "raw_difference_units", estimate_definition: "mean_paired_test_minus_reference" },
    package_versions: { numpy: "2.2.6", scipy: "1.15.3" },
    warnings: [],
    response: testColumn,
    test_column: testColumn,
    reference_column: referenceColumn,
    n_total: 6,
    n_used: 5,
    n_missing: 1,
    n_non_numeric: 0,
    n_complete_pairs: 5,
    n_incomplete_pairs: 1,
    sample: { n: 5, mean: 0.1, median: 0.1, variance: 0.01, std: 0.1, min: -0.05, max: 0.2, warnings: [] },
    estimate: { value: 0.1, definition: "mean_paired_test_minus_reference", standard_error: 0.04, df: 4 },
    tests: {
      lower: { bound: -0.5, null_hypothesis: "difference <= lower", alternative: "difference > lower", statistic: 15, df: 4, p_value: 0.0001, reject_null: true },
      upper: { bound: 0.5, null_hypothesis: "difference >= upper", alternative: "difference < upper", statistic: -10, df: 4, p_value: 0.0003, reject_null: true },
    },
    tost: { p_value: 0.0003, equivalent: true, decision_rule: "both_one_sided_tests_reject_at_alpha", ci_inside_equivalence_bounds: true },
    confidence_interval: { level: 0.9, lower: 0.015, upper: 0.185, inside_equivalence_bounds: true },
    effect_size: null,
  } as EquivalenceTostResult;
}
