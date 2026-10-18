import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { numericChartTicks, numericChartTickValues, STANDARD_CHART_LAYOUT } from "./chartLayout";
import { ChartAxes } from "./ChartAxes";

describe("pilot numeric axis regressions", () => {
  it("distinguishes narrow-range labels", () => {
    const ticks = numericChartTicks({ min: 1000, max: 1000.01 });
    expect(ticks.length).toBeGreaterThan(1);
    expect(new Set(ticks.map((tick) => tick.label)).size).toBe(ticks.length);
  });
  it("never rounds large-origin coordinates outside their range", () => {
    const values = numericChartTickValues({ min: 1e12, max: 1e12 + 5 });
    expect(values.every((value) => value >= 1e12 && value <= 1e12 + 5)).toBe(true);
    expect(new Set(values).size).toBe(values.length);
    expect(values.length).toBeGreaterThan(1);
  });
  it("renders an explicit large-origin offset", () => {
    const html = renderToStaticMarkup(<svg><ChartAxes layout={STANDARD_CHART_LAYOUT}
      x={{ label: "Stored response", unit: "mg/L", range: { min: 1e12, max: 1e12 + 5 } }}
      y={{ label: "Count", range: { min: 0, max: 1 } }} /></svg>);
    expect(html).toContain("data-axis-offset=\"1000000000000\"");
  });
});
