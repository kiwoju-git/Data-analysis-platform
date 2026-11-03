import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AnalysisResultEnvelope, DatasetVersionResponse, RunChartResult } from "./api";
import { RunChartPanel } from "./RunChartPanel";
import { LocaleProvider } from "./i18n/LocaleProvider";
import { setCurrentLocale } from "./i18n/store";

vi.mock("./charts/QualityResultCharts", () => ({ RunResultChart: () => null }));

afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });

function resultFixture(): RunChartResult {
  const about = { available: true, skipped_reason: null, observed_runs: 5, expected_runs: 5.5,
    p_value_clustering: 1e-10, p_value_mixture: 1 - 1e-10 };
  return {
    value: { display_name: "측정값 사용자 이름", unit: "mm" }, order: null,
    n_used: 10, n_total: 10, center_line: 1, n_excluded_missing_value: 0,
    n_excluded_non_numeric_value: 0, runs: { run_count: 5, n_above: 5, n_below: 5,
      n_ties: 0, longest_run_length: 2 },
    runs_test: { available: true, skipped_reason: null, p_value_low: 1e-10, p_value_high: 1 },
    signals: [], chart: { points: [], point_count: 10 },
    approximate_randomness_tests: { alpha: .05, about_median: about,
      up_down: { ...about, p_value_trend: 0, p_value_oscillation: 1 } },
  } as unknown as RunChartResult;
}

describe("Run Chart stored metric display", () => {
  it("localizes the actual Linux warning DTOs only at the Run Chart display boundary", () => {
    vi.stubGlobal("window", { localStorage: { getItem: () => "en" } });
    const warnings = [
      { code: "run_chart_not_control_chart", message: "런 차트는 관리한계를 계산하지 않으며, 신호를 관리도 out-of-control로 해석하지 않습니다." },
      { code: "run_chart_uses_canonical_row_order", message: "이번 slice의 런 차트는 canonical row 순서를 실행 순서로 사용합니다." },
      { code: "run_chart_trend_rule_defined", message: "trend 신호는 연속 6개 이상 값이 엄격히 증가하거나 감소할 때만 표시합니다." },
      { code: "run_chart_oscillation_rule_defined", message: "oscillation 신호는 연속 값의 증가/감소 방향이 엄격히 교대할 때만 표시합니다." },
      { code: "run_chart_runs_test_defined", message: "clustering/mixture 신호는 median 위/아래 run 개수의 exact 조건부 분포로만 평가합니다." },
      { code: "run_chart_trend_signal_detected", message: "명시 정의된 trend 신호가 감지되었습니다." },
      { code: "run_chart_clustering_signal_detected", message: "median 위/아래 run 개수가 exact 분포의 낮은 꼬리에 있어 clustering 신호로 표시했습니다." },
    ];
    const before = JSON.stringify(warnings);
    const html = renderToStaticMarkup(<LocaleProvider><RunChartPanel
      analysisResult={{ warnings } as AnalysisResultEnvelope} filterValidationError={null} isRunningAnalysis={false}
      methodId="quality.run_chart" orderColumnId={null} orderColumns={[]} result={null}
      valueColumnId="measurement" valueColumns={[]}
      version={{ version_id: "synthetic-version" } as DatasetVersionResponse}
      onOrderColumnChange={() => {}} onRun={() => {}} onValueColumnChange={() => {}}
    /></LocaleProvider>);
    const notices = /<ul class="warning-list"[^>]*>(.*?)<\/ul>/su.exec(html)?.[1];
    expect(notices).toBeDefined();
    expect(notices).not.toMatch(/[\uAC00-\uD7A3]/u);
    expect(notices).toContain("does not calculate control limits");
    expect(notices).toContain("exact conditional distribution");
    warnings.forEach((warning) => expect(notices).toContain(warning.code));
    expect(JSON.stringify(warnings)).toBe(before);
  });
  it.each(["en", "ko"] as const)("preserves nonzero probabilities and stored values in %s", (locale) => {
    vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
    const result = resultFixture();
    const source = JSON.stringify(result);
    const html = renderToStaticMarkup(<LocaleProvider><RunChartPanel
      analysisResult={null} filterValidationError={null} isRunningAnalysis={false}
      methodId="quality.run_chart" orderColumnId={null} orderColumns={[]}
      result={result} valueColumnId="measurement" valueColumns={[]}
      version={{ version_id: "synthetic-version" } as DatasetVersionResponse}
      onOrderColumnChange={() => {}} onRun={() => {}} onValueColumnChange={() => {}}
    /></LocaleProvider>);
    const clustering = /data-result-metric="clustering"[^>]*>(.*?)<\/article>/su.exec(html)?.[1];
    const trend = /data-result-metric="trend"[^>]*>(.*?)<\/article>/su.exec(html)?.[1];
    expect(clustering).toContain('class="result-metric-card-value">p=1e-10</strong>');
    expect(trend).toContain('class="result-metric-card-value">p=0</strong>');
    expect(html).toContain("low p=1e-10");
    expect(html.match(/data-result-metric=/g)).toHaveLength(4);
    expect(html).toContain("5.5");
    expect(html).toContain("측정값 사용자 이름");
    expect(JSON.stringify(result)).toBe(source);
  });
});
