import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import cases from "../../../tests/fixtures/numeric_display_cases.json";
import { setCurrentLocale } from "../i18n/store";
import { numericAxisPlan } from "./numericAxisPlan";
import { formattedAxisTicks, numericChartTicks, STANDARD_CHART_LAYOUT } from "./chartLayout";
import { ChartAxes } from "./ChartAxes";
import { paddedNumericRange, scaleChartValue } from "./chartScale";
import { InteractiveScatterChart } from "./InteractiveScatterChart";
import { GpProfileChart, GpScatter } from "./GaussianProcessCharts";
import { gpFixture } from "./resultChartFixtures";

afterEach(() => setCurrentLocale("ko"));
describe("shared bounded numeric axis cases", () => {
  it.each(cases)("$id uses representable positions and distinct locale labels", ({ min, max, offset, expected_values }) => {
    const range = { min, max }; const plan = numericAxisPlan(range);
    expect(plan.values.length).toBeGreaterThanOrEqual(2); expect(plan.values.length).toBeLessThanOrEqual(32);
    expect(plan.values.every((value, index) => Number.isFinite(value) && value >= min && value <= max && (index === 0 || value > plan.values[index - 1]))).toBe(true);
    expect(plan.offset !== 0).toBe(offset);
    if (expected_values) expect(plan.values).toEqual(expected_values);
    for (const locale of ["ko", "en"] as const) {
      setCurrentLocale(locale);
      const ticks = formattedAxisTicks(plan, locale);
      expect(new Set(ticks.map((tick) => tick.label)).size).toBe(ticks.length);
      expect(numericChartTicks(range).every((tick) => tick.label !== "NaN")).toBe(true);
      const html = renderToStaticMarkup(<svg><ChartAxes layout={STANDARD_CHART_LAYOUT} x={{ label: "X", unit: "mg/L", range }} y={{ label: "Y", range }} /></svg>);
      expect(html).not.toMatch(/(?:="(?:NaN|Infinity)|>NaN<)/);
      if (offset) expect(html).toContain("data-axis-offset=");
    }
    expect(range).toEqual({ min, max });
  });
  it("keeps custom labels absolute and passes a backwards-compatible context", () => {
    const formatter = vi.fn((value: number) => `custom:${value}`);
    const range = { min: 1e12, max: 1e12 + 5 };
    const ticks = numericChartTicks(range, 5, formatter);
    expect(ticks[0].label).toBe("custom:1000000000000");
    expect(formatter).toHaveBeenCalledWith(1e12, expect.objectContaining({ range, step: 1, offset: 0 }));
    const html = renderToStaticMarkup(<svg><ChartAxes layout={STANDARD_CHART_LAYOUT} x={{ label: "X", range, formatTick: formatter }} y={{ label: "Y", range: { min: 0, max: 1 } }} /></svg>);
    expect(html).not.toContain("data-axis-offset");
  });
  it("preserves explicit category labels even on offset-sized coordinates", () => {
    const html = renderToStaticMarkup(<svg><ChartAxes layout={STANDARD_CHART_LAYOUT}
      x={{ label: "Category", range: { min: 1e12, max: 1e12 + 5 }, ticks: [{ value: 1e12, label: "User <one>" }, { value: 1e12 + 5, label: "User two" }] }}
      y={{ label: "Y", range: { min: 0, max: 1 } }} /></svg>);
    expect(html).toContain("User &lt;one&gt;"); expect(html).not.toContain("data-axis-offset");
  });
  it("rejects invalid ranges and bounds target-driven work", () => {
    for (const range of [{ min: NaN, max: 1 }, { min: 0, max: Infinity }, { min: 1, max: 1 }, { min: 2, max: 1 }]) expect(numericAxisPlan(range).values).toEqual([]);
    expect(numericAxisPlan({ min: 0, max: 1 }, 1e12).values.length).toBeLessThanOrEqual(32);
  });
  it.each(["ko", "en"] as const)("actual GP numeric callers retain adaptive offsets and exact stored details in %s", (locale) => {
    setCurrentLocale(locale);
    const result = gpFixture();
    const profile = result.conditional_profiles[0];
    profile.points = profile.points.map((point, index) => ({ ...point, value: 1e12 + index * 5,
      predicted_mean: 1000 + index * .01, predictive_interval_95: { lower: 1000 + index * .01 - .001, upper: 1000 + index * .01 + .001 } }));
    const originalPoint = result.diagnostics.points[0];
    result.diagnostics.points = [0, 1].map((index) => ({ ...originalPoint, row_index: index, observed: 1e12 + index * 5, fitted: 1e12 + index * 5 }));
    const before = JSON.stringify(result);
    for (const chart of [<GpProfileChart result={result} profile={profile} scope="stored" />, <GpScatter result={result} mode="fitted" scope="stored" />]) {
      const html = renderToStaticMarkup(chart);
      expect(html).toContain("data-axis-offset=");
      const labels = [...html.matchAll(/<text class="chart-tick-label" text-anchor="middle"[^>]*>([^<]*)<\/text>/g)].map((match) => match[1]);
      expect(labels.length).toBeGreaterThan(1); expect(new Set(labels).size).toBe(labels.length);
      expect(html).toContain("1000000000005");
    }
    expect(JSON.stringify(result)).toBe(before);
  });
  it.each([[-Number.MAX_VALUE, Number.MAX_VALUE], [Number.MAX_VALUE, Number.MAX_VALUE], [1, 1 + Number.EPSILON]])("keeps extreme finite SVG projection finite: %s", (min, max) => {
    const range = paddedNumericRange([min, max]);
    expect(Number.isFinite(range.min) && Number.isFinite(range.max)).toBe(true);
    for (const value of [min, max]) expect(Number.isFinite(scaleChartValue(value, range, 72, 456))).toBe(true);
    const html = renderToStaticMarkup(<InteractiveScatterChart chartId="extreme" title="Stored" description="Stored" annotations={[]} emptyLabel="Empty"
      xLabel="X" yLabel="Y" xRange={range} yRange={range} points={[min, max].map((value, index) => ({ id: `${index}`, title: "Stored", ariaLabel: "Stored", className: "point", details: [], x: value, y: value }))} />);
    expect(html).not.toMatch(/(?:cx|cy|x1|y1|x2|y2)="(?:NaN|Infinity|-Infinity)"/);
  });
});
