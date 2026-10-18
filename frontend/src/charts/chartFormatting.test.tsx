import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCurrentLocale } from "../i18n/store";
import { formatLocaleNumber } from "../i18n/formatters";
import { ChartAxes } from "./ChartAxes";
import { InteractiveScatterChart, type InteractiveScatterChartProps } from "./InteractiveScatterChart";
import { formatChartTick, integerChartTicks, numericChartTicks, STANDARD_CHART_LAYOUT } from "./chartLayout";
import { LineMetricChart } from "./PlsResultCharts";
import { ScreePlot } from "./PrincipalComponentCharts";
import { GpUncertaintyChart } from "./GaussianProcessCharts";
import { gpFixture, pcaFixture, plsFixture } from "./resultChartFixtures";

const props: InteractiveScatterChartProps = {
  chartId: "format-contract", sourceKey: "analysis:unchanged", title: "Stored result", description: "Stored coordinates",
  annotations: [], emptyLabel: "Empty", xLabel: "Count", yLabel: "Response", xUnit: "s", yUnit: "mg/L",
  xRange: { min: 0, max: 2 }, yRange: { min: -0.5, max: 1 },
  points: [{ id: "row:7", title: "User \ue000name & <x>", ariaLabel: "Row 7", className: "scatter-point",
    details: [{ label: "Saved", value: "0.25" }], x: 1, y: 0.25 }],
  referenceLines: [{ label: "Zero", x1: 0, x2: 2, y1: 0, y2: 0 }],
};
const renderChart = (overrides: Partial<InteractiveScatterChartProps> = {}) =>
  renderToStaticMarkup(<InteractiveScatterChart {...props} {...overrides} />);
const ticks = (html: string) => [...html.matchAll(/<text class="chart-tick-label"[^>]*>([^<]*)<\/text>/g)].map((match) => match[1]);
const xTicks = (html: string) => [...html.matchAll(/<text class="chart-tick-label" text-anchor="middle"[^>]*>([^<]*)<\/text>/g)].map((match) => match[1]);
const geometry = (html: string) => [...html.matchAll(/<(?:circle|line|path)\b[^>]*>/g)].map((match) => match[0]);

afterEach(() => setCurrentLocale("ko"));

describe("display-only chart tick formatting", () => {
  it("wires the legacy formatter into both numeric axes", () => {
    const html = renderChart({ formatValue: (value) => `legacy:${value}` });
    expect(ticks(html).length).toBeGreaterThan(0);
    expect(ticks(html).every((label) => label.startsWith("legacy:"))).toBe(true);
    expect(html).toContain("Count (s)");
    expect(html).toContain("Response (mg/L)");
  });

  it("lets each axis override the legacy formatter without changing data geometry", () => {
    const html = renderChart({ formatValue: (value) => `legacy:${value}`,
      xFormatValue: (value) => `count:${value}`, yFormatValue: (value) => `${value * 100}%` });
    expect(ticks(html)).toContain("count:1");
    expect(ticks(html)).toContain("-50%");
    expect(ticks(html)).not.toContain("legacy:1");
    expect(geometry(html)).toEqual(geometry(renderChart()));
    expect(props.points[0].y).toBe(0.25);
  });

  it("keeps an unspecified axis on its legacy formatter", () => {
    const html = renderChart({ formatValue: (value) => `legacy:${value}`, yFormatValue: (value) => `Y:${value}` });
    expect(ticks(html)).toContain("legacy:1");
    expect(ticks(html)).toContain("Y:-0.5");
  });

  it("gives explicit labels priority and never invents fractional components", () => {
    const unused = vi.fn(() => "incorrect");
    const html = renderChart({ xRange: { min: 1, max: 3 }, xFormatValue: unused,
      xTicks: [1, 2, 3].map((value) => ({ value, label: `PC${value} \ue000 & <stored>` })) });
    expect(unused).not.toHaveBeenCalled();
    expect(ticks(html)).toContain("PC1 \ue000 &amp; &lt;stored&gt;");
    expect(html).not.toContain("PC1.5");
    expect(html).not.toContain("PC2.5");
  });

  it("uses AxisSpec.formatTick only for finite generated positions", () => {
    const xFormat = vi.fn((value: number) => `X:${value.toFixed(2)}`);
    const yFormat = vi.fn((value: number) => `Y:${value}`);
    const html = renderToStaticMarkup(<svg><ChartAxes layout={STANDARD_CHART_LAYOUT}
      x={{ label: "X", range: { min: -1, max: 1 }, formatTick: xFormat }}
      y={{ label: "Y", range: { min: 0, max: 1 }, formatTick: yFormat,
        ticks: [{ value: NaN, label: "Invalid" }, { value: 0, label: "User zero" }] }} /></svg>);
    expect(ticks(html)).toContain("X:0.00");
    expect(ticks(html)).toContain("User zero");
    expect(ticks(html)).not.toContain("Invalid");
    expect(xFormat.mock.calls.every(([value]) => Number.isFinite(value))).toBe(true);
    expect(yFormat).not.toHaveBeenCalled();
  });

  it.each(["ko", "en"] as const)("uses current %s number policy when no formatter is supplied", (locale) => {
    setCurrentLocale(locale);
    expect(formatChartTick(12345)).toBe(formatLocaleNumber(12345, locale, { maximumSignificantDigits: 5 }));
    expect(ticks(renderChart({ xRange: { min: 1000, max: 5000 }, points: [{ ...props.points[0], x: 2000 }] }))).toContain("2,000");
    expect(formatChartTick(-0)).toBe("0");
    expect(formatChartTick(NaN)).toBe("-");
    expect(formatChartTick(Infinity)).toBe("-");
    expect(formatChartTick(-Infinity)).toBe("-");
    expect(formatChartTick(1e-8)).toMatch(/^1(?:\.0+)?e-8$/i);
    expect(formatChartTick(2e9)).toMatch(/^2(?:\.0+)?e\+?9$/i);
    expect(numericChartTicks({ min: 0, max: 8e-8 }).filter((tick) => tick.value > 0).every((tick) => /e-/.test(tick.label))).toBe(true);
  });

  it("keeps numeric tick values independent from labels and rejects invalid ranges", () => {
    const range = { min: -0.5, max: 1 };
    const original = numericChartTicks(range);
    const formatted = numericChartTicks(range, 5, (value) => `${value * 100}%`);
    expect(formatted.map((tick) => tick.value)).toEqual(original.map((tick) => tick.value));
    expect(formatted[0]).toEqual({ value: -0.5, label: "-50%" });
    expect(range).toEqual({ min: -0.5, max: 1 });
    expect(numericChartTicks({ min: NaN, max: 1 })).toEqual([]);
    expect(numericChartTicks({ min: 0, max: Infinity })).toEqual([]);
  });

  it("preserves actual PCA/PLS component labels and stored negative R-squared", () => {
    const pca = pcaFixture();
    const pls = plsFixture();
    pls.component_selection.rows[0].predicted_r_squared = -0.4;
    const before = JSON.stringify({ pca, pls });
    const pcaHtml = renderToStaticMarkup(<ScreePlot result={pca} analysisId="pca:1" />);
    const plsHtml = renderToStaticMarkup(<LineMetricChart result={pls} analysisId="pls:1" />);
    for (const html of [pcaHtml, plsHtml]) {
      expect(xTicks(html)).toEqual(["1", "2"]);
    }
    expect(plsHtml).toContain("-0.4");
    expect(JSON.stringify({ pca, pls })).toBe(before);
  });

  it("shows only integer rows for a two-observation uncertainty chart", () => {
    const result = gpFixture();
    result.diagnostics.points = [result.diagnostics.points[0], { ...result.diagnostics.points[0], row_index: 1 }];
    const html = renderToStaticMarkup(<GpUncertaintyChart result={result} scope="selected" />);
    expect(xTicks(html)).toEqual(["1", "2"]);
  });

  it("bounds integer-axis work for short, negative and billion-row ranges", () => {
    expect(integerChartTicks({ min: 0.96, max: 2.04 }).map((tick) => tick.value)).toEqual([1, 2]);
    expect(integerChartTicks({ min: -2.04, max: -0.96 }).map((tick) => tick.value)).toEqual([-2, -1]);
    const large = integerChartTicks({ min: 0, max: 1e9 });
    expect(large.length).toBeLessThanOrEqual(6);
    expect(large.every((tick) => Number.isInteger(tick.value))).toBe(true);
    expect(integerChartTicks({ min: 1e9 + 0.96, max: 1e9 + 2.04 }).map((tick) => tick.label)).toEqual(["1,000,000,001", "1,000,000,002"]);
    expect(numericChartTicks({ min: 0.96, max: 2.04 }).some((tick) => !Number.isInteger(tick.value))).toBe(true);
  });
});
