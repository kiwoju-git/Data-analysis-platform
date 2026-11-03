import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DatasetVersionResponse, RunChartResult } from "./api";
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
