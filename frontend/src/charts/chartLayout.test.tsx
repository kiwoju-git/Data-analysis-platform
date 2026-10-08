import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ChartAxes } from "./ChartAxes";
import { ChartFrame } from "./ChartFrame";
import { InteractiveScatterChart, type InteractiveScatterPoint } from "./InteractiveScatterChart";
import { InteractiveGridChart } from "./InteractiveGridChart";
import { InteractiveHorizontalBarChart } from "./InteractiveHorizontalBarChart";
import { SQUARE_CHART_LAYOUT, STANDARD_CHART_LAYOUT, numericChartTicks, wrapAxisTitle } from "./chartLayout";

const point = (id: string, x: number, y: number): InteractiveScatterPoint => ({ id, x, y, title: id, ariaLabel: id, className: "chart-point", details: [] });
describe("fixed chart frames and axes", () => {
  it("gives repeated chart IDs unique instance titles and clip paths", () => {
    const frame = <ChartFrame chartId="same" title="T" description="D" layout={STANDARD_CHART_LAYOUT}><circle cx={100} cy={100} r={3.5} /></ChartFrame>;
    const html = renderToStaticMarkup(<>{frame}{frame}</>);
    const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]);
    expect(new Set(ids).size).toBe(ids.length);
    expect(html).toContain('viewBox="0 0 480 320"');
    expect(html).toContain('preserveAspectRatio="xMidYMid meet"');
  });
  it("uses equal pixel lengths for equal square numeric ranges", () => {
    expect(SQUARE_CHART_LAYOUT.plot.width).toBe(384);
    expect(SQUARE_CHART_LAYOUT.plot.height).toBe(384);
    expect(SQUARE_CHART_LAYOUT.maxWidth).toBe(520);
  });
  it("renders visible labels, units and explicit component ticks", () => {
    const html = renderToStaticMarkup(<svg><ChartAxes layout={STANDARD_CHART_LAYOUT}
      x={{ label: "Component", range: { min: 1, max: 3 }, ticks: [1, 2, 3].map((value) => ({ value, label: String(value) })) }}
      y={{ label: "Response", unit: "mg/L", range: { min: -0.5, max: 1 } }} /></svg>);
    expect(html).toContain('class="chart-visible-axis-title"');
    expect(html).toContain("Response (mg/L)");
    expect(html).not.toMatch(/>1\.5<|>2\.5</);
    expect(numericChartTicks({ min: -0.5, max: 1 }).some((tick) => tick.value < 0)).toBe(true);
    expect(wrapAxisTitle("A very long response variable name with a unit", 20)).toHaveLength(2);
  });
  it("keeps separate series, negative predictions, reference zero and interval kinds", () => {
    const points = [point("train:1", 1, 0.8), point("train:2", 2, 0.9), point("cv:1", 1, -0.4), point("cv:2", 2, -0.1)];
    const html = renderToStaticMarkup(<InteractiveScatterChart annotations={[]} chartId="series" title="Selection"
      description="Stored values" emptyLabel="Empty" formatValue={String} points={points}
      xLabel="Components" yLabel="R2" xRange={{ min: 1, max: 2 }} yRange={{ min: -0.4, max: 1 }}
      series={[{ id: "train", label: "Training", className: "train", pointIds: ["train:1", "train:2"], connect: "line" },
        { id: "cv", label: "Cross-validation", className: "cv", pointIds: ["cv:1", "cv:2"], connect: "line" }]}
      referenceLines={[{ label: "Zero", x1: 1, x2: 2, y1: 0, y2: 0 }]}
      intervals={[{ id: "ci", pointId: "train:1", lower: 0.5, upper: 1, kind: "mean_ci" }, { id: "pi", pointId: "train:1", lower: -1, upper: 2, kind: "prediction_interval" }]} />);
    expect(html.match(/<path class="interactive-data-line/g)).toHaveLength(2);
    expect(html).toContain("Cross-validation");
    expect(html).toContain("<title>Zero</title>");
    expect(html).toContain('data-interval-kind="mean_ci"');
    expect(html).toContain('data-interval-kind="prediction_interval"');
    expect(html.match(/tabindex="0"/g)).toHaveLength(1);
  });
  it("does not replace invalid grid values with zero", () => {
    const html = renderToStaticMarkup(<InteractiveGridChart chartId="invalid" title="Grid" description="Grid" xLabel="X" yLabel="Y" valueLabel="Mean"
      cells={[{ id: "bad", x: 1, y: 2, value: NaN, title: "Bad", details: [] }]} />);
    expect(html).not.toContain("data-grid-cell");
    expect(html).not.toContain("chart-color-scale");
  });
  it("paginates bars without losing stable duplicate-name column identities", () => {
    const items = Array.from({ length: 25 }, (_, index) => ({ id: `column:${index}`, label: "Same name", title: `column:${index}`, value: index - 12, details: [] }));
    const html = renderToStaticMarkup(<InteractiveHorizontalBarChart chartId="loading" title="Loading" description="All columns saved" items={items} xLabel="Component 1 loading" yLabel="Predictor" />);
    expect(html.match(/tabindex=/g)).toHaveLength(12);
    expect(html).toContain("1-12");
    expect(html).toContain("25");
  });
});
