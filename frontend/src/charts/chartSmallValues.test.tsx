import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { GageRunChartResult, PearsonCorrelationResult, RegressionPredictionResponse } from "../api";
import { factorialNumber } from "../doe/factorialWorkflowPresentation";
import { setCurrentLocale } from "../i18n/store";
import { PearsonResultChart } from "./PearsonResultChart";
import { PredictionIntervalChart } from "./PredictionIntervalChart";
import { GageResultChart } from "./GageResultChart";
import { formatChartDetailValue, formatSmallChartValue } from "./chartNumberFormatting";

const ticks = (html: string, anchor: "middle" | "end") => [...html.matchAll(
  new RegExp(`<text class="chart-tick-label" text-anchor="${anchor}"[^>]*>([^<]*)<\\/text>`, "g"),
)].map((match) => match[1]);

function pearsonFixture(): PearsonCorrelationResult {
  const column = { column_index: 0, data_type: "decimal" as const,
    measurement_level: "continuous" as const, role: "feature" as const, unit: "mg/L" };
  const summary = { n: 3, mean: 2e-6, std: 1e-6, min: 1e-6, max: 3e-6 };
  return {
    schema_version: 1, summary_type: "pearson_correlation", method: "pearson",
    missing_policy: "complete_case", alternative: "two-sided", alpha: .05,
    confidence_level: .95, package_versions: { numpy: "fixture", scipy: "fixture" }, warnings: [],
    x: { ...column, column_id: "x", display_name: "User \ue000 <x>" },
    y: { ...column, column_index: 1, column_id: "y", display_name: "Y" },
    n_total: 3, n_used: 3, n_excluded_missing_x: 0, n_excluded_missing_y: 0,
    n_excluded_non_numeric_x: 0, n_excluded_non_numeric_y: 0,
    x_summary: summary, y_summary: summary,
    scatterplot: { x_column_id: "x", y_column_id: "y", point_count: 3,
      points_truncated: false, point_limit: 3,
      points: [1, 2, 3].map((value) => ({ x: value * 1e-6, y: value * 1e-6 })) },
    association: { correlation: 1, r_squared: 1, covariance: 1e-12, correlation_definition: "Pearson r" },
    test: { statistic: 1, statistic_name: "r", p_value: 0, reject_null: true,
      null_hypothesis: "rho=0", alternative: "two-sided" },
    confidence_interval: { method: "fisher", level: .95, lower: null, upper: null },
  };
}

function gageFixture(): GageRunChartResult {
  const measurement = pearsonFixture().x;
  return {
    schema_version: 1, summary_type: "gage_run_chart", method: "measurement_system_run_chart",
    missing_policy: "complete_case", order_source: "canonical", order_tie_breaker: "canonical",
    columns: { measurement, part: measurement, operator: measurement, replicate: measurement, order: null },
    sample: { n_total: 3, n_used: 3, n_excluded_missing_measurement: 0, n_excluded_non_numeric_measurement: 0,
      n_excluded_missing_part: 0, n_excluded_missing_operator: 0, n_excluded_missing_replicate: 0,
      n_excluded_missing_identifier: 0, n_excluded_missing_order: 0, n_excluded_invalid_order: 0 },
    design: { ready_for_chart: true, part_count: 1, operator_count: 1, replicate_count: 3,
      expected_cell_count: 1, observed_cell_count: 1, missing_cell_count: 0,
      min_replicates_per_cell: 3, max_replicates_per_cell: 3, replicate_set_consistent: true,
      duplicate_replicates_per_cell: 0 },
    summary: { mean: 2e-6, minimum: 1e-6, maximum: 3e-6, range: 2e-6 },
    part_summaries: [], operator_summaries: [], warnings: [], notes: [],
    chart: { point_count: 3, point_limit: 3, points_truncated: false, x_axis: "run_order",
      color_role: "operator_index", facet_role: "part_index", symbol_role: "replicate_index",
      label_policy: "part_operator_replicate_labels_redacted",
      points: [1, 2, 3].map((value) => ({ position: value, canonical_position: value,
        value: value * 1e-6, part_index: 1, operator_index: 1, replicate_index: value })) },
  };
}

afterEach(() => setCurrentLocale("ko"));

describe.each(["ko", "en"] as const)("small stored chart values in %s", (locale) => {
  it("keeps Pearson axis ticks and accessible point values distinguishable", () => {
    setCurrentLocale(locale);
    const result = pearsonFixture();
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(<PearsonResultChart result={result} />);
    for (const anchor of ["middle", "end"] as const) {
      expect(new Set(ticks(html, anchor)).size).toBeGreaterThan(1);
      expect(ticks(html, anchor).some((label) => /e-6/i.test(label))).toBe(true);
    }
    expect(html).toContain("User \ue000 &lt;x&gt;: 1e-6");
    expect(html).toContain("Y (mg/L)");
    expect(JSON.stringify(result)).toBe(before);
  });

  it("keeps prediction means and interval endpoints nonzero without changing row ticks", () => {
    setCurrentLocale(locale);
    const rows: RegressionPredictionResponse["rows"] = [1, 2, 3].map((value, row_index) => ({
      row_index, predicted_mean: value * 1e-6, warnings: [], prediction_interval: null,
      mean_confidence_interval: { method: "t", level: .95, lower: (value - .1) * 1e-6, upper: (value + .1) * 1e-6 },
    }));
    const before = JSON.stringify(rows);
    const html = renderToStaticMarkup(<PredictionIntervalChart rows={rows} total={3} sourceKey="tiny:prediction" />);
    expect(new Set(ticks(html, "end")).size).toBeGreaterThan(1);
    expect(ticks(html, "end").some((label) => /e-6/i.test(label))).toBe(true);
    expect(ticks(html, "middle")).toEqual(["1", "2", "3"]);
    expect(html).toContain('aria-label="1: 1e-6"');
    expect(html).toContain("95%");
    expect(html).not.toContain('data-interval-kind="prediction_interval"');
    expect(JSON.stringify(rows)).toBe(before);
  });

  it("preserves tiny Factorial values while retaining ordinary display rounding", () => {
    setCurrentLocale(locale);
    expect(factorialNumber(1e-6)).toBe("1e-6");
    expect(factorialNumber(-2e-8)).toBe("-2e-8");
    expect(factorialNumber(1234.56789)).toBe(Number((1234.56789).toPrecision(6)).toLocaleString());
    expect(factorialNumber(0)).toBe("0");
    expect(factorialNumber(null)).toBe("-");
  });

  it("retains Gage measurement units and nonzero detail values", () => {
    setCurrentLocale(locale);
    const result = gageFixture();
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(<GageResultChart result={result} />);
    expect(new Set(ticks(html, "end")).size).toBeGreaterThan(1);
    expect(html).toContain('aria-label="Run 1: 1e-6"');
    expect(html).toContain("mg/L");
    expect(html).toContain("2e-6");
    expect(JSON.stringify(result)).toBe(before);
  });

  it("limits scientific fallback to tiny fixed-decimal values", () => {
    setCurrentLocale(locale);
    expect(formatSmallChartValue(1e-8, 6)).toBe("1e-8");
    expect(formatSmallChartValue(-2e-8, 6)).toBe("-2e-8");
    expect(formatSmallChartValue(1e-6, 6)).toBeNull();
    expect(formatSmallChartValue(12.3456789, 6)).toBeNull();
    expect(formatSmallChartValue(0, 6)).toBeNull();
    expect(formatSmallChartValue(NaN, 6)).toBeNull();
    expect(formatChartDetailValue(9e-7)).toBe("9e-7");
    expect(formatChartDetailValue(1.1e-6)).toBe("1.1e-6");
    expect(formatChartDetailValue(1.23456789)).toBe("1.234568");
    expect(formatChartDetailValue(1e100)).toBe("1e100");
    expect(formatChartDetailValue(-0)).toBe("0");
    expect(formatChartDetailValue(Infinity)).toBe("-");
  });
});
