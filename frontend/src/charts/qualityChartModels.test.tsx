import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { ComponentProps } from "react";
import { setCurrentLocale } from "../i18n/store";
import { AttributeResultChart, IndividualsResultChart, RunResultChart } from "./QualityResultCharts";
import { InteractiveHistogramChart } from "./InteractiveHistogramChart";
import { PredictionIntervalChart } from "./PredictionIntervalChart";

describe("stored quality and prediction charts", () => {
  it("preserves a legacy constant-data count bin without inventing density", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<InteractiveHistogramChart chartId="constant" columnName="Constant" nBasis={8}
      bins={[{ lower: 3, upper: 3, count: 8, include_lower: true, include_upper: true }]} />);
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("Count 8");
    expect(html).not.toContain("empty-state");
  });
  it("preserves I/MR signal shapes and zero control limits", () => {
    setCurrentLocale("en");
    const html = renderToStaticMarkup(<IndividualsResultChart label="Temperature" chartKind="individuals" unit="C"
      series={{ x_axis: "order_rank", center_line: 1, lcl: 0, ucl: 3, point_count: 3, point_limit: 10, points_truncated: false,
        points: [[], ["individuals_chart_i_beyond_3_sigma"], ["individuals_chart_i_trend"]].map((signal_codes, index) => ({ position: index + 1, canonical_position: index + 5, value: index + 1, signal_codes })) }} />);
    expect(html).toContain("LCL: 0");
    expect(html).toContain("Temperature (C)");
    expect(html).toMatch(/<rect[^>]*role="img"/);
    expect(html).toMatch(/<polygon[^>]*role="img"/);
    expect(html.match(/tabindex="0"/g)).toHaveLength(1);
  });
  it("keeps each attribute point's stored limits", () => {
    const result: ComponentProps<typeof AttributeResultChart>["result"] = { chart_type: "p", center_line: 0.2, chart: { y_axis: "proportion_defective", point_count: 2,
      points: [{ position: 1, canonical_position: 1, value: .1, count: 1, denominator: 10, lcl: 0, ucl: .4, lcl_truncated: true, ucl_truncated: false, signal_codes: [] },
        { position: 2, canonical_position: 2, value: .2, count: 4, denominator: 20, lcl: .02, ucl: .3, lcl_truncated: false, ucl_truncated: false, signal_codes: [] }] } };
    const html = renderToStaticMarkup(<AttributeResultChart result={result} />);
    expect(html).toContain("LCL 0, UCL 0.4");
    expect(html).toContain("LCL 0.02, UCL 0.3");
    expect(html).toContain("Proportion defective");
  });
  it("does not invent Run Chart management limits", () => {
    const result: ComponentProps<typeof RunResultChart>["result"] = { value: { display_name: "Value", unit: "m" }, center_line: 0,
      chart: { x_axis: "order_rank", points: [{ position: 1, canonical_position: 4, value: 0, relative_to_center: "tie", signal_codes: [] }] } };
    const html = renderToStaticMarkup(<RunResultChart result={result} />);
    expect(html).toContain("Median: 0");
    expect(html).not.toMatch(/LCL|UCL/);
    expect(html).toContain("run-point-tie");
  });
  it("uses stored histogram density and keeps zero specifications", () => {
    const html = renderToStaticMarkup(<InteractiveHistogramChart chartId="density" columnName="Length" unit="cm" nBasis={10}
      bins={[{ lower: 0, upper: 2, count: 10, density: .5, include_lower: true, include_upper: true }]}
      ordinate="density" referenceValues={[{ label: "LSL", value: 0 }]} densityFitPoints={[{ x: 0, density: .1 }, { x: 2, density: .2 }]} />);
    expect(html).toContain("Density 0.5");
    expect(html).toContain("LSL: 0");
    expect(html).toContain("Length (cm)");
  });
  it("renders point-only predictions and only the intervals actually stored", () => {
    const html = renderToStaticMarkup(<PredictionIntervalChart sourceKey="prediction:1" total={2} rows={[
      { row_index: 0, predicted_mean: 7, warnings: [], mean_confidence_interval: null, prediction_interval: null },
      { row_index: 3, predicted_mean: 9, warnings: [], mean_confidence_interval: { method: "t", level: .95, lower: 8, upper: 10 }, prediction_interval: null },
    ]} />);
    expect(html).toContain('aria-label="1: 7"');
    expect(html).toContain('aria-label="4: 9"');
    expect(html.match(/data-interval-kind="mean_ci"/g)).toHaveLength(1);
    expect(html).not.toContain('data-interval-kind="prediction_interval"');
    expect(html).toContain("95%");
  });
});
