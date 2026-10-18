import type { ComponentProps, ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  EquivalenceTostResult,
  GraphicalSummaryColumn,
  OlsLinearModelResult,
} from "../api";
import type { EqualVarianceMultipleComparisons } from "../api/types/analysisResultsExploration";
import { GraphicalSummaryColumnVisuals } from "../GraphicalSummaryColumnVisuals";
import { LinearModelFitResults } from "../LinearModelFitResults";
import { setCurrentLocale } from "../i18n/store";
import type { AppLocale } from "../i18n/types";
import type { ChartItemFeedback } from "./ChartItemFeedback";
import { InteractiveDistributionCiChart } from "./InteractiveDistributionCiChart";
import { InteractiveEquivalencePlot } from "./InteractiveEquivalencePlot";
import { InteractiveIndividualValueChart } from "./InteractiveIndividualValueChart";
import { InteractiveQqChart } from "./InteractiveQqChart";
import type { InteractiveScatterChartProps } from "./InteractiveScatterChart";
import { InteractiveVarianceComparisonIntervalsChart } from "./InteractiveVarianceComparisonIntervalsChart";

const captures = vi.hoisted(() => ({
  scatter: new Map<string, InteractiveScatterChartProps>(),
}));

vi.mock("./InteractiveScatterChart", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./InteractiveScatterChart")>();
  return {
    ...actual,
    InteractiveScatterChart: (props: InteractiveScatterChartProps) => {
      captures.scatter.set(props.chartId, props);
      return <actual.InteractiveScatterChart {...props} />;
    },
  };
});

// Expose supplied detail text during SSR without simulating pointer or focus state.
vi.mock("./ChartItemFeedback", () => ({
  ChartItemFeedback: ({ items }: ComponentProps<typeof ChartItemFeedback>) => (
    <dl data-testid="detail-boundary">
      {items.map((item) => <div key={item.id} data-item-id={item.id}>
        <dt>{item.title}</dt>
        {item.details.map((detail, index) => <dd key={index}>{detail.label}: {detail.value}</dd>)}
      </div>)}
    </dl>
  ),
}));

const literalName = "평균 \uE000twoVariances.method\uE001 <column>";

function render(locale: AppLocale, element: ReactElement) {
  setCurrentLocale(locale);
  return renderToStaticMarkup(element);
}

describe("trusted chart display boundaries", () => {
  beforeEach(() => captures.scatter.clear());
  afterEach(() => setCurrentLocale("ko"));

  it("localizes Q-Q details again on locale change without translating the column name", () => {
    const chart = <InteractiveQqChart chartId="qq" columnName={literalName} nBasis={2}
      pointCount={2} points={[{ theoretical: -1, sample: 2 }, { theoretical: 1, sample: 4 }]}
      truncated={false} />;
    const en = render("en", chart);
    const englishPoints = captures.scatter.get("qq")!.points;
    const ko = render("ko", chart);
    const koreanPoints = captures.scatter.get("qq")!.points;
    expect(en).toContain("theoretical quantiles");
    expect(ko).toContain("이론 분위수");
    expect(englishPoints[0].details.find((detail) => detail.value === literalName)).toBeDefined();
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
    expect(englishPoints.map(({ id, x, y }) => ({ id, x, y }))).toEqual(
      koreanPoints.map(({ id, x, y }) => ({ id, x, y })),
    );
    expect(render("en", chart)).toBe(en);
  });

  it("keeps individual series and group text literal while localizing point details", () => {
    const chart = <InteractiveIndividualValueChart chartId="individual" points={[{
      series_id: "s1", series_label: literalName, source_column_label: literalName,
      group: literalName, point_index: 3, canonical_position: 7, value: 2.25,
    }]} />;
    const en = render("en", chart);
    const englishPoint = captures.scatter.get("individual")!.points[0];
    const englishAxis = captures.scatter.get("individual")!.xLabel;
    const ko = render("ko", chart);
    const koreanPoint = captures.scatter.get("individual")!.points[0];
    expect(englishPoint.details[0].value).toBe(literalName);
    expect(englishPoint.details[1].value).toBe(literalName);
    expect(englishPoint.details[3].label).toBe("value");
    expect(koreanPoint.details[3].label).toBe("값");
    expect(englishAxis).not.toMatch(/[가-힣]/u);
    expect(en).toContain(englishAxis);
    expect(captures.scatter.get("individual")!.xLabel).toBe("변수 또는 그룹");
    expect([englishPoint.id, englishPoint.x, englishPoint.y]).toEqual(
      [koreanPoint.id, koreanPoint.x, koreanPoint.y],
    );
    expect(en).toContain("observation 3");
    expect(ko).toContain("관측 3");
  });

  it("localizes distribution interval labels and leaves stored method values untouched", () => {
    const interval = { computed: true, method: literalName, confidence_level: 0.95,
      estimate: 2, lower: 1, upper: 3 };
    const chart = <InteractiveDistributionCiChart chartId="ci" columnName={literalName}
      intervals={{ mean: interval, median: interval, standard_deviation: interval }} />;
    const en = render("en", chart);
    const ko = render("ko", chart);
    expect(en).toContain("confidence interval 1 - 3");
    expect(ko).toContain("신뢰구간 1 - 3");
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
    expect(en).toContain('data-item-id="ci-standard-deviation"');
    expect(ko).toContain('data-item-id="ci-standard-deviation"');
  });

  it("localizes variance detail labels without rewriting group identity or peer names", () => {
    const result: EqualVarianceMultipleComparisons = {
      computed: true, method: "bonett", alpha: 0.05, p_value: 0.01,
      reject_equal_variances: true, warnings: [], pairwise_p_values: [],
      groups: [{ group_label: literalName, group_index: 1, n: 5,
        sample_standard_deviation: 2, comparison_interval: { lower: 1, upper: 3 }, allocation: 1 }],
      non_overlapping_pairs: [{ left_group: literalName, right_group: "평균" }],
    };
    const chart = <InteractiveVarianceComparisonIntervalsChart chartId="variance"
      groupName={literalName} responseName={literalName} result={result} />;
    const en = render("en", chart);
    const ko = render("ko", chart);
    expect(en).not.toContain("표본 표준편차");
    expect(ko).toContain("표본 표준편차");
    expect(en).toContain(": 평균</dd>");
    expect(en).toContain('data-item-id="variance-group-1"');
    expect(result.groups[0].group_label).toBe(literalName);
  });

  it.each([
    "two_sample_independent_mean_difference", "paired_mean_difference", "one_sample_mean_difference",
  ])("localizes equivalence description for %s without changing the plotted estimate", (design) => {
    const result = { design, equivalence_bounds: { lower: -1, upper: 1 },
      confidence_interval: { level: 0.9, lower: -0.5, upper: 0.5 },
      estimate: { value: 0.125 }, tost: { equivalent: true } } as EquivalenceTostResult;
    const chart = <InteractiveEquivalencePlot result={result} />;
    const en = render("en", chart);
    const ko = render("ko", chart);
    expect(en).toContain('aria-label="point estimate 0.125"');
    expect(ko).toContain('aria-label="점 추정치 0.125"');
    expect(en.match(/<desc>(.*?)<\/desc>/u)?.[1]).not.toMatch(/[가-힣]/u);
    expect(en.match(/cx="[^"]+"/u)?.[0]).toBe(ko.match(/cx="[^"]+"/u)?.[0]);
  });

  it("localizes ECDF model labels without translating warnings or source columns", () => {
    const column = graphicalColumn();
    const chart = <GraphicalSummaryColumnVisuals column={column} charts={["ecdf"]} mode="full" />;
    const original = JSON.stringify(column);
    const en = render("en", chart);
    const englishPoint = captures.scatter.get(`graphical-ecdf-${column.column_id}`)!.points[0];
    const ko = render("ko", chart);
    expect(englishPoint.details[2].label).toBe("Cumulative probability");
    expect(ko).toContain("누적확률");
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
    expect(en).toContain(`<li>${"\uE000twoVariances.method\uE001"}</li>`);
    expect(JSON.stringify(column)).toBe(original);
  });

  it("translates only the static label cells of graphical statistics rows", () => {
    const chart = <GraphicalSummaryColumnVisuals column={graphicalColumn()} mode="full" />;
    const en = render("en", chart);
    const ko = render("ko", chart);
    expect(en).not.toContain("<dt>평균</dt>");
    expect(en).not.toContain("<dt>표준편차</dt>");
    expect(ko).toContain("<dt>평균</dt>");
    expect(ko).toContain("<dt>표준편차</dt>");
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
  });

  it("localizes OLS helper labels but preserves unknown reasons and coefficient names", () => {
    const result = linearModelResult();
    const chart = <LinearModelFitResults result={result} />;
    const original = JSON.stringify(result);
    const en = render("en", chart);
    const observed = captures.scatter.get("linear-model-observed-fitted")!;
    const influence = captures.scatter.get("linear-model-leverage-cook")!;
    const ko = render("ko", chart);
    expect(observed.points[0].details.map((detail) => detail.label)).not.toEqual(
      captures.scatter.get("linear-model-observed-fitted")!.points[0].details.map((detail) => detail.label),
    );
    expect(observed.points[0]).toMatchObject({ id: "observed-3", x: 2, y: 2.5 });
    expect(influence.points[0].details[0].label).not.toBe("행 index");
    expect(en).not.toContain("반복된 predictor 조합이 없어");
    expect(ko).toContain("반복된 predictor 조합이 없어");
    expect(en).not.toContain("제거 기준 충족 항 없음");
    expect(ko).toContain("제거 기준 충족 항 없음");
    expect(en).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
    expect(JSON.stringify(result)).toBe(original);
    result.anova!.lack_of_fit.reason = literalName;
    result.model_selection!.stop_reason = literalName;
    expect(render("en", chart)).toContain("평균 \uE000twoVariances.method\uE001 &lt;column&gt;");
  });
});

function graphicalColumn(): GraphicalSummaryColumn {
  return {
    column_id: "source-column", column_index: 0, display_name: literalName, data_type: "decimal",
    measurement_level: "continuous", role: "feature", unit: null,
    n_total: 3, n_used: 2, n_missing: 1, n_non_numeric: 0,
    min: 1, q1: 1, median: 2, q3: 3, max: 3,
    histogram: { binning: "freedman_diaconis", bin_count: 0, bins: [] },
    boxplot: { lower_whisker: 1, q1: 1, median: 2, q3: 3, upper_whisker: 3,
      lower_fence: 1, upper_fence: 3, outlier_count: 0 },
    qq_plot: { point_count: 0, points_truncated: false, points: [] },
    ecdf: { point_count: 2, points_truncated: false,
      points: [{ x: 1, probability: 0.5 }, { x: 3, probability: 1 }] },
    warnings: ["\uE000twoVariances.method\uE001"],
  };
}

function linearModelResult(): OlsLinearModelResult {
  return {
    schema_version: 5, sample: { n_used: 12, df_residual: 10 },
    fit: { residual_standard_error: 1.1, r_squared: 0.91, adjusted_r_squared: 0.9,
      predicted_r_squared: 0.8, press: 14.5 },
    coefficients: [{ term: literalName, term_kind: "numeric", estimate: 2,
      standard_error: 0.2, statistic: 10, p_value: 0.001, vif: 1, reference_level: null,
      confidence_interval: { level: 0.95, lower: 1.8, upper: 2.2 } }],
    anova: { rows: [], lack_of_fit: { available: false, reason: "no_replicated_predictor_settings" } },
    model_selection: { method: "backward_elimination", alpha_to_remove: 0.1,
      initial_terms: [literalName], final_terms: [literalName],
      stop_reason: "all_removal_p_values_at_or_below_alpha", steps: [] },
    diagnostics: { max_vif: 1, condition_number: 2,
      residual_summary: { max_abs_standardized: 1.5, large_standardized_count: 0 },
      leverage: { max: 0.2, high_count: 0, threshold: 0.5 },
      influence: { cooks_distance_max: 0.1, high_cooks_distance_count: 0, cooks_distance_threshold: 0.33 },
      diagnostic_points: { points: [{ row_index: 3, fitted: 2, residual: 0.5,
        standardized_residual: 0.25, leverage: 0.2, cooks_distance: 0.1 }] } },
  } as unknown as OlsLinearModelResult;
}
