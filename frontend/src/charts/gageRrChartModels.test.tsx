import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GageRrResult } from "../api/types/analysisResultsQuality";
import { GageRrResultCharts } from "../GageRrResultCharts";
import { LocaleProvider } from "../i18n/LocaleProvider";
import { setCurrentLocale } from "../i18n/store";
import { t } from "../i18n/translate";
import { componentChart, gageChartModels, gagePlotState } from "./gageRrChartModels";

const fixtures = JSON.parse(readFileSync(new URL("../../../tests/fixtures/gage_rr_six_panel.json", import.meta.url), "utf8")) as { retain: GageRrResult; auto_pool: GageRrResult };
afterEach(() => { vi.unstubAllGlobals(); setCurrentLocale("en"); });
const copy = (result: GageRrResult) => structuredClone(result);

describe("Gage six-panel saved-value adapters", () => {
  it("keeps the hand-checkable R/Xbar numbers and never connects operator sections", () => {
    const result = fixtures.retain;
    const before = JSON.stringify(result);
    const model = gageChartModels(result.plot_bundle!, 0, 0, t);
    expect(gagePlotState(result)).toBe("valid");
    expect(model.dispersion.points).toHaveLength(30);
    model.dispersion.points.forEach((point) => expect(point.y).toBeCloseTo(0.2, 12));
    expect(model.dispersion.referenceLines.map((line) => line.y1)).toEqual(expect.arrayContaining([0]));
    expect(model.dispersion.referenceLines[2].y1).toBeCloseTo(0.6534, 12);
    expect(model.xbar.referenceLines[1].y1).toBeCloseTo(59, 12);
    expect(model.xbar.referenceLines[2].y1).toBeCloseTo(59.3, 12);
    for (const series of model.dispersion.series) {
      expect(series.pointIds).toHaveLength(10);
      expect(new Set(model.dispersion.points.filter((point) => series.pointIds.includes(point.id)).map((point) => point.seriesId))).toEqual(new Set([series.id]));
    }
    expect(model.responsePart.points.filter((point) => point.id.startsWith("raw:"))).toHaveLength(60);
    expect(model.boxes).toHaveLength(3);
    // Type 7 at (20 - 1) * .25 = 4.75, between 53.7 and 53.9.
    expect(model.boxes[0].q1).toBeCloseTo(53.85, 12);
    expect(model.boxes[0].mean).toBeCloseTo(58.8, 12);
    expect(model.dots).toHaveLength(60);
    expect(JSON.stringify(result)).toBe(before);
  });

  it("uses selected repeatability but leaves observed interaction means unchanged", () => {
    const retained = gageChartModels(fixtures.retain.plot_bundle!, 0, 0, t);
    const pooled = gageChartModels(fixtures.auto_pool.plot_bundle!, 0, 0, t);
    expect(pooled.xbar.referenceLines[2].y1).toBeCloseTo(59 + 3 * Math.sqrt(0.0125 / 2), 12);
    expect(pooled.interaction.points.map((point) => point.y)).toEqual(retained.interaction.points.map((point) => point.y));
    const chart = componentChart(fixtures.auto_pool, t);
    expect(chart.bars).toHaveLength(8);
    expect(chart.bars.find((bar) => bar.id === "total_gage_rr:1")?.value).toBe(fixtures.auto_pool.variance_components.total_gage_rr.percent_study_variation);
  });

  it("paints individual measurements above means without changing saved values or display coordinates", () => {
    const bundle = fixtures.retain.plot_bundle!;
    const before = JSON.stringify(bundle);
    const model = gageChartModels(bundle, 0, 0, t);
    const points = model.responsePart.points;
    const means = points.filter((point) => point.id.startsWith("part-mean:"));
    const raw = points.filter((point) => point.id.startsWith("raw:"));
    expect(points.slice(0, means.length)).toEqual(means);
    expect(points.slice(means.length)).toEqual(raw);
    expect(raw.map((point) => point.id)).toEqual([...bundle.response_by_part.points].reverse().map((point) => `raw:${point.source_row_number}`));
    expect(points.at(-1)?.id).toBe("raw:1");
    for (const saved of bundle.response_by_part.points) {
      const plotted = raw.find((point) => point.id === `raw:${saved.source_row_number}`)!;
      expect(plotted.y).toBe(saved.value);
      expect(plotted.x).toBe(saved.part_index + ((saved.source_row_number * 17 % 31) / 30 - 0.5) * 0.44);
    }
    for (const saved of bundle.parts) {
      const plotted = means.find((point) => point.id === `part-mean:${saved.part_index}`)!;
      expect(plotted.y).toBe(saved.mean);
      expect(plotted.x).toBe(saved.part_index);
      expect(plotted.marker).toBe("diamond");
      expect(plotted.ariaLabel).toBeTruthy();
      expect(plotted.details).not.toHaveLength(0);
    }
    expect(model.responsePart.series.at(-1)?.pointIds).toEqual(means.map((point) => point.id));
    expect(JSON.stringify(bundle)).toBe(before);
  });

  it("preserves global scales and full-part summaries on a later display page", () => {
    const bundle = fixtures.retain.plot_bundle!;
    const first = gageChartModels(bundle, 0, 0, t);
    const next = gageChartModels(bundle, 1, 0, t);
    expect(next.dispersion.yRange).toEqual(first.dispersion.yRange);
    expect(next.xbar.yRange).toEqual(first.xbar.yRange);
    expect(next.yRange).toEqual(first.yRange);
    expect(next.boxes).toEqual(first.boxes);
  });

  it("reduces global limit extrema without spreading a large stored cell array", () => {
    const bundle = structuredClone(fixtures.retain.plot_bundle!);
    bundle.xbar.points = Array.from({ length: 200_000 }, (_, index) => ({ part_index: index, operator_index: 0,
      n: 2, value: 50 + index / 10_000, outside_repeatability_limits: false }));
    const model = gageChartModels(bundle, 0, 0, t);
    expect(model.xbar.points).toHaveLength(10);
    expect(model.xbar.yRange.max).toBeGreaterThan(69.9999);
    expect(Number.isFinite(model.xbar.yRange.max)).toBe(true);
  });

  it("distinguishes legacy missing data from corrupt current data", () => {
    const legacy = copy(fixtures.retain); legacy.schema_version = 2; delete legacy.plot_bundle;
    expect(gagePlotState(legacy)).toBe("legacy");
    expect(componentChart(legacy, t).bars).toHaveLength(8);
    const current = copy(fixtures.retain); delete current.plot_bundle;
    expect(gagePlotState(current)).toBe("invalid");
    const invalid = copy(fixtures.retain); invalid.plot_bundle!.components.items[0].percent_contribution = -1;
    expect(gagePlotState(invalid)).toBe("invalid");
  });

  it.each(["null-part", "null-point", "empty-points", "missing-constants"])("rejects malformed %s without throwing or hiding the tables", (kind) => {
    const result = copy(fixtures.retain);
    const bundle = result.plot_bundle!;
    if (kind === "null-part") (bundle.parts as unknown[])[0] = null;
    if (kind === "null-point") (bundle.xbar.points as unknown[])[0] = null;
    if (kind === "empty-points") bundle.xbar.points = [];
    if (kind === "missing-constants") delete (bundle.dispersion as Partial<typeof bundle.dispersion>).constants;
    expect(gagePlotState(result)).toBe("invalid");
  });

  it("uses the stored bundle for current components and honors unavailable status", () => {
    const result = copy(fixtures.retain);
    result.variance_components.total_gage_rr.percent_contribution = 77;
    expect(componentChart(result, t).bars[0].value).toBe(result.plot_bundle!.components.items[0].percent_contribution);
    result.plot_bundle!.components.status = "unavailable";
    expect(componentChart(result, t).bars).toHaveLength(0);
  });

  it.each(["en", "ko"] as const)("renders six accessible stored-data charts without changing Korean user names in %s", (locale) => {
    vi.stubGlobal("window", { localStorage: { getItem: () => locale } });
    const result = copy(fixtures.auto_pool);
    result.plot_bundle!.measurement.display_name = "사용자 측정값 <script>";
    const before = JSON.stringify(result);
    const html = renderToStaticMarkup(<LocaleProvider><GageRrResultCharts result={result} sourceKey="synthetic:hash:3" /></LocaleProvider>);
    expect(html.match(/data-gage-chart-kind=/g)).toHaveLength(6);
    expect(html.match(/class="chart-frame-svg"/g)).toHaveLength(6);
    expect(html).toContain("사용자 측정값 &lt;script&gt;");
    expect(html).not.toContain("<script>");
    expect(html).toContain('data-series-id="operator:0"');
    expect(html).toContain('data-box-id="box:0"');
    expect(html.indexOf('data-point-id="part-mean:0"')).toBeLessThan(html.indexOf('data-point-id="raw:60"'));
    expect(html.indexOf('data-point-id="raw:3"')).toBeLessThan(html.indexOf('data-point-id="raw:1"'));
    expect(html).toContain(locale === "en" ? "Interaction is pooled" : "교호작용이 풀링");
    expect(JSON.stringify(result)).toBe(before);
  });
});
