import { createElement, type ComponentType, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  DatasetColumnResponse, DatasetVersionResponse, EquivalenceTostResult,
  EqualVariancesResult, IndividualsChartResult, KruskalWallisResult,
  PearsonCorrelationResult, RunChartResult, XyCorrelationResult,
} from "./api";
import { AttributeControlChartPanel } from "./AttributeControlChartPanel";
import { EqualVariancesPanel } from "./EqualVariancesPanel";
import { EquivalenceResultView } from "./EquivalenceResultView";
import { GageRunChartPanel } from "./GageRunChartPanel";
import { IndividualsChartPanel } from "./IndividualsChartPanel";
import { KruskalWallisPanel } from "./KruskalWallisPanel";
import { LinearModelPanel } from "./LinearModelPanel";
import { OneWayAnovaPanel } from "./OneWayAnovaPanel";
import { PearsonCorrelationPanel } from "./PearsonCorrelationPanel";
import { RunChartPanel } from "./RunChartPanel";
import { XyCorrelationPanel } from "./XyCorrelationPanel";
import { LocaleProvider } from "./i18n/LocaleProvider";
import { setCurrentLocale } from "./i18n/store";
import { translateSystemText } from "./i18n/translate";
import type { AppLocale } from "./i18n/types";

// Chart rendering is covered separately; these fixtures exercise display boundaries.
vi.mock("./charts/InteractiveEquivalencePlot", () => ({ InteractiveEquivalencePlot: () => null }));
vi.mock("./charts/QualityResultCharts", () => ({
  RunResultChart: () => null, IndividualsResultChart: () => null, AttributeResultChart: () => null,
}));
vi.mock("./charts/PearsonResultChart", () => ({ PearsonResultChart: () => null }));

const rawName = "\uBC94\uC8FC\uD615 \uE000startup.failed\uE001";
const column: DatasetColumnResponse = {
  column_id: "column-raw", version_id: "version-1", column_index: 0,
  original_name: rawName, display_name: rawName, data_type: "decimal",
  measurement_level: "continuous", role: "feature", unit: null,
};
const common = {
  alpha: .05, confidenceLevel: .95, analysisResult: null, filterDrafts: [],
  filterValidationError: null, isRunningAnalysis: false, methodId: "synthetic.method",
  responseColumnId: "response", responseColumns: [], groupColumnId: "group", groupColumns: [],
  valueColumnId: "value", valueColumns: [], orderColumnId: null, orderColumns: [],
  result: null, version: { version_id: "version-1", columns: [] } as unknown as DatasetVersionResponse,
};

function markup(node: ReactNode, locale: AppLocale) {
  vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
  return renderToStaticMarkup(<LocaleProvider>{node}</LocaleProvider>);
}

function panel<P extends object>(Component: ComponentType<P>, props: Partial<P>, locale: AppLocale) {
  return markup(createElement(Component, { ...common, ...props } as P), locale);
}

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("ko"); });

describe("analysis panel static display boundaries", () => {
  it("has English translations for the migrated static helper phrases", () => {
    for (const source of [
      "독립 2-표본 평균 차이", "대응표본 평균 차이", "1-표본 평균", "시험군", "기준군",
      "시험 측정", "기준 측정", " 평균 - 기준 평균", "쌍 / ", "행",
      "군집", "혼합", "추세", "진동", "중앙값과 같은 값은 아래쪽에 포함", "같은 값은 하강 방향에 포함", "계산 안 함",
      "가변 표본 크기 불량률", "고정 표본 크기 불량품 수", "동일 검사 기회의 결점 수", "가변 검사 기회의 단위당 결점",
      "불량품 수", "결점 수", "검사 기회", "표본 크기", "Levene (평균 중심, legacy)", "계산 불가", "등분산 기각", "기각하지 않음",
      "실행됨", "overall 비유의로 생략", "요청 안 함", "생략", "없음", "선택", "범주형", "숫자형", "역할",
      "특별원인 신호 있음", "현재 활성화된 관리도 규칙에서 신호 없음",
      "모든 그룹 쌍의 평균을 비교하고 family-wise error를 제어합니다.",
      "선택한 기준 그룹과 나머지 그룹의 평균을 비교합니다.",
      "등분산을 가정하지 않고 모든 그룹 쌍을 비교합니다.", "그룹별 요약과 전체 검정만 계산합니다.",
      "그룹 수준이 20개를 초과하여 Dunnett 비교를 실행할 수 없습니다.",
    ]) {
      expect(translateSystemText(source, "en"), source).not.toMatch(/[\uAC00-\uD7A3]/u);
    }
  });

  it("localizes equivalence design and fallback fragments without translating group names", () => {
    const result = equivalenceResult();
    const snapshot = JSON.stringify(result);
    for (const locale of ["en", "ko", "en"] as const) {
      const html = markup(<EquivalenceResultView analysisResult={null} result={result} />, locale);
      expect(html).toContain(translateSystemText("독립 2-표본 평균 차이", locale));
      expect(html).toContain(`${rawName} - ${translateSystemText("기준군", locale)}`);
      expect(JSON.stringify(result)).toBe(snapshot);
    }
  });

  it("localizes paired sample units and one-sample suffixes while preserving the response", () => {
    const result = { ...equivalenceResult(), design: "paired_mean_difference", n_complete_pairs: 5,
      test_column: column, reference_column: null } as unknown as EquivalenceTostResult;
    const en = markup(<EquivalenceResultView analysisResult={null} result={result} />, "en");
    expect(en).toContain("5 pair / 6 row");
    expect(en).toContain(`${rawName} - ${translateSystemText("기준 측정", "en")}`);
    const ko = markup(<EquivalenceResultView analysisResult={null} result={result} />, "ko");
    expect(ko).toContain("5쌍 / 6행");
    const single = { ...result, design: "one_sample_mean" } as EquivalenceTostResult;
    expect(markup(<EquivalenceResultView analysisResult={null} result={single} />, "en"))
      .toContain(`${rawName}${translateSystemText(" 평균 - 기준 평균", "en")}`);
  });

  it("localizes attribute measurement labels and purposes without changing chart codes", () => {
    for (const locale of ["en", "ko"] as const) {
      const html = panel(AttributeControlChartPanel, { chartType: "u", phase: "phase_1",
        countColumnId: "count", countColumns: [column], denominatorColumnId: "size", denominatorColumns: [],
        constantOpportunityConfirmed: false }, locale);
      expect(html).toContain(translateSystemText("결점 수", locale));
      expect(html).toContain(translateSystemText("검사 기회", locale));
      expect(html).toContain(translateSystemText("가변 검사 기회의 단위당 결점", locale));
      expect(html).toContain('aria-checked="true"');
      expect(html).toContain('value="column-raw"');
      expect(html).toContain(rawName);
      expect(html).toContain(">U</button>");
    }
  });

  it("renders legacy variance labels and decisions while leaving unknown method text literal", () => {
    const result = { schema_version: 1, response: column, group: column, n_used: 8, n_total: 8,
      group_count: 2, groups: [], tests: [
        { method: "levene_mean", statistic: 1.2, p_value: .2, alpha: .05, reject_equal_variances: false },
        { method: rawName, statistic: null, p_value: null, alpha: .05, reject_equal_variances: null },
      ] } as unknown as EqualVariancesResult;
    for (const locale of ["en", "ko"] as const) {
      const html = panel(EqualVariancesPanel, { result }, locale);
      expect(html).toContain(translateSystemText("Levene (평균 중심, legacy)", locale));
      expect(html).toContain(translateSystemText("기각하지 않음", locale));
      expect(html).toContain(translateSystemText("계산 불가", locale));
      expect(html).toContain(rawName);
    }
  });

  it("resolves ANOVA posthoc descriptions and Gage placeholders at render time", () => {
    for (const locale of ["en", "ko"] as const) {
      expect(panel(OneWayAnovaPanel, {}, locale)).toContain(translateSystemText(
        "모든 그룹 쌍의 평균을 비교하고 family-wise error를 제어합니다.", locale));
      const html = panel(GageRunChartPanel, { measurementColumnId: null, measurementColumns: [column],
        partColumnId: null, partColumns: [], operatorColumnId: null, operatorColumns: [],
        replicateColumnId: null, replicateColumns: [] }, locale);
      expect(html).toContain(`<option value="" selected="">${translateSystemText("선택", locale)}</option>`);
      expect(html).toContain(rawName);
    }
  });

  it("localizes Kruskal-Wallis posthoc status from stable reasons", () => {
    const result = { n_used: 8, n_total: 8, group_count: 2, has_ties: false, groups: [],
      test: { h_statistic: 1, df: 1, p_value: .3, effect_size: { epsilon_squared: .1 }, reject_null: false },
      posthoc: { performed: false, reason: "overall_not_significant", comparisons: [] },
    } as unknown as KruskalWallisResult;
    for (const locale of ["en", "ko"] as const) {
      expect(panel(KruskalWallisPanel, { result }, locale))
        .toContain(translateSystemText("overall 비유의로 생략", locale));
    }
    expect(result.posthoc.reason).toBe("overall_not_significant");
  });

  it("localizes Run Chart display labels while preserving raw skipped reasons", () => {
    const about = { available: false, skipped_reason: rawName, observed_runs: 1, expected_runs: null,
      p_value_clustering: null, p_value_mixture: null };
    const result = { value: column, order: null, n_used: 3, n_total: 3, center_line: 1,
      n_excluded_missing_value: 0, n_excluded_non_numeric_value: 0,
      runs: { run_count: 1, n_above: 0, n_below: 0, n_ties: 3, longest_run_length: 0 },
      runs_test: { available: false, skipped_reason: rawName }, signals: [], chart: { points: [], point_count: 3 },
      approximate_randomness_tests: { alpha: .05, about_median: about,
        up_down: { ...about, p_value_trend: null, p_value_oscillation: null } },
    } as unknown as RunChartResult;
    const snapshot = JSON.stringify(result);
    for (const locale of ["en", "ko"] as const) {
      const html = panel(RunChartPanel, { result }, locale);
      for (const text of ["군집", "혼합", "추세", "진동", "중앙값과 같은 값은 아래쪽에 포함", "같은 값은 하강 방향에 포함"]) {
        expect(html).toContain(translateSystemText(text, locale));
      }
      expect(html).toContain(`${translateSystemText("계산 안 함", locale)} · ${rawName}`);
    }
    expect(JSON.stringify(result)).toBe(snapshot);
  });

  it("localizes I-MR status without changing its stored signals", () => {
    const series = { point_count: 3, points: [], lcl: 0, center_line: 1, ucl: 2 };
    const result = { value: column, order: null, n_used: 3, n_total: 3, order_duplicate_count: 0,
      sigma_estimator: { mrbar: 1, sigma: 1 }, individuals_chart: series, moving_range_chart: series,
      signals: [] } as unknown as IndividualsChartResult;
    for (const locale of ["en", "ko"] as const) {
      const html = panel(IndividualsChartPanel, { result }, locale);
      expect(html).toContain(translateSystemText("현재 활성화된 관리도 규칙에서 신호 없음", locale));
      expect(html).toContain(rawName);
    }
    expect(result.signals).toEqual([]);
  });

  it("localizes missing correlation intervals but leaves numeric results intact", () => {
    const pair = { x: column, y: { ...column, column_id: "y" }, n_used: 3, n_total: 3,
      n_excluded_missing_x: 0, n_excluded_missing_y: 0, n_excluded_non_numeric_x: 0, n_excluded_non_numeric_y: 0,
      association: { correlation: .5, r_squared: .25, covariance: .1 }, test: { p_value: .6, reject_null: false },
      confidence_interval: { level: .95, lower: null, upper: null }, status: "ok", error_code: null };
    const summary = { n: 3, mean: 1, std: 1, min: 0, max: 2 };
    const pearson = { ...pair, x_summary: summary, y_summary: summary, scatterplot: { points: [], point_count: 3 } } as unknown as PearsonCorrelationResult;
    const xy = { x_columns: [pair.x], y_columns: [pair.y], x_column_count: 1, y_column_count: 1,
      pair_count: 1, missing_policy: "pairwise_complete_case", pairs: [pair] } as unknown as XyCorrelationResult;
    for (const locale of ["en", "ko"] as const) {
      const expected = `<td>${translateSystemText("계산 불가", locale)}</td>`;
      expect(panel(PearsonCorrelationPanel, { xColumnId: "x", yColumnId: "y", xColumns: [], yColumns: [], result: pearson }, locale)).toContain(expected);
      expect(panel(XyCorrelationPanel, { xColumnIds: ["x"], yColumnIds: ["y"], xColumns: [], yColumns: [], result: xy }, locale)).toContain(expected);
    }
    expect(pair.confidence_interval).toEqual({ level: .95, lower: null, upper: null });
  });

  it("localizes predictor-kind metadata without translating the predictor display name", () => {
    for (const locale of ["en", "ko"] as const) {
      const html = panel(LinearModelPanel, { predictorColumns: [column], predictorColumnIds: [column.column_id],
        modelSelectionMethod: "none", alphaToRemove: .05, interactionKeys: [], quadraticColumnIds: [] }, locale);
      expect(html).toContain(rawName);
      expect(html).toContain(translateSystemText("숫자형", locale));
      expect(html).toContain(translateSystemText("역할", locale));
    }
  });
});

function equivalenceResult(): EquivalenceTostResult {
  const test = { bound: -.5, statistic: 1, df: 4, p_value: .01, reject_null: true };
  return { design: "two_sample_independent_mean_difference", test_group_label: rawName, reference_group_label: null,
    response: column, n_used: 5, n_total: 6, estimate: { value: .1 }, tost: { equivalent: true, p_value: .01 },
    tests: { lower: test, upper: { ...test, bound: .5 } }, equivalence_bounds: { lower: -.5, upper: .5 },
    confidence_interval: { level: .9, lower: -.2, upper: .3 },
  } as unknown as EquivalenceTostResult;
}
