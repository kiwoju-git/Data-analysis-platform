import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { RsmPlotBundle, RsmVertex } from "../api/types/rsmPlots";
import { setCurrentLocale } from "../i18n/store";
import { t } from "../i18n/translate";
import { ResponseSurfaceContourChart } from "./ResponseSurfaceContourChart";

const outer: RsmVertex[] = [[0, 10], [2, 10], [2, 20], [0, 20]];
const hole: RsmVertex[] = [[.5, 12.5], [1.5, 12.5], [1.5, 17.5], [.5, 17.5]];

function fixture(): RsmPlotBundle {
  return {
    schema_version: 1,
    settings: {
      plot_kind: "contour", x_factor_id: "factor_1", y_factor_id: "factor_2",
      held_actual_values: { factor_3: 1e-6 }, axis_scale: "actual", grid_size: 21,
      contour_levels: { count: 2, thresholds: [2e-6] }, trace_actual_values: null,
      filled: true, lines: true, design_points: true,
    },
    x_axis: { factor_id: "factor_1", name: "Temperature", unit: "K", minimum: 0, maximum: 2 },
    y_axis: { factor_id: "factor_2", name: "Pressure", unit: "bar", minimum: 10, maximum: 20 },
    response_name: "Yield", response_unit: "mg/L", held_actual_values: { Feed: 1e-6 },
    points: [
      { point_id: "node:0", x: 0, y: 10, predicted: 1e-6, outside_design_hull: true },
      { point_id: "node:1", x: 2, y: 10, predicted: 2e-6, outside_design_hull: false },
      { point_id: "node:2", x: 0, y: 20, predicted: -1e-6, outside_design_hull: false },
      { point_id: "node:3", x: 2, y: 20, predicted: 0, outside_design_hull: true },
    ],
    curves: [],
    geometry: {
      algorithm: "contourpy.serial", algorithm_version: "1.3.2",
      grid_orientation: "z[y_index][x_index]", minimum: -1e-6, maximum: 2e-6,
      constant: false, levels: [2e-6],
      lines: [{ level: 2e-6, paths: [[[0, 15], [1, 12.5], [2, 15]]] }],
      bands: [
        { lower: null, upper: 2e-6, polygons: [{ rings: [outer, hole] }] },
        { lower: 2e-6, upper: null, polygons: [{ rings: [hole] }] },
      ],
    },
    design_points: [{ run_order: 1, x: 1, y: 15, on_slice: true },
      { run_order: 2, x: 1.5, y: 17.5, on_slice: false }],
    hull_slice_polygon: [[.25, 11.25], [1.75, 11.25], [1, 18.75]],
    hull_policy: "full_design_coded_convex_hull", final_term_ids: ["Intercept", "A", "B"],
  };
}

function render(bundle: RsmPlotBundle, sourceKey = "analysis:1:view:1") {
  return renderToStaticMarkup(<ResponseSurfaceContourChart bundle={bundle} sourceKey={sourceKey} />);
}

function bands(html: string) {
  return [...html.matchAll(/<path[^>]*data-contour-band="[^"]+"[^>]*>/g)].map((match) => match[0]);
}

afterEach(() => setCurrentLocale("ko"));

describe.each(["ko", "en"] as const)("stored RSM contour presentation in %s", (locale) => {
  it("uses visible actual axes, response units, exact stored table and one keyboard entry", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    const before = JSON.stringify(bundle);
    const html = render(bundle);
    expect(html).toContain("Temperature (K)");
    expect(html).toContain("Pressure (bar)");
    expect(html).toContain("Yield (mg/L)");
    const table = html.match(/<table>[\s\S]*?<\/table>/)?.[0] ?? "";
    expect(table).toContain("<td>0</td><td>10</td><td>0.000001</td>");
    expect(table).toContain("<td>2</td><td>10</td><td>0.000002</td>");
    expect(table).toContain("<td>0</td><td>20</td><td>-0.000001</td>");
    expect(table).toContain("<td>2</td><td>20</td><td>0</td>");
    expect(table).toContain(t("rsm.plot.outsideHull"));
    expect(table).toContain(t("rsm.plot.insideHull"));
    expect(html.match(/tabindex="0"/g)).toHaveLength(1);
    expect(html.match(/data-grid-cell=/g)).toHaveLength(4);
    expect(html).toContain('aria-label="Temperature (K) 0; Pressure (bar) 10; Yield (mg/L) 0.000001"');
    expect(html).toContain("Feed=1e-6");
    expect(JSON.stringify(bundle)).toBe(before);
  });

  it("draws stored polygon holes and stored line coordinates without reconstructing contours", () => {
    setCurrentLocale(locale);
    const html = render(fixture());
    expect(bands(html)).toHaveLength(2);
    expect(bands(html)[0]).toContain('fill-rule="evenodd"');
    expect(bands(html)[0]).toContain(
      'd="M72,256L456,256L456,24L72,24ZM168,198L360,198L360,82L168,82Z"',
    );
    expect(html).toContain('d="M72,140L264,198L456,140"');
    expect(html).toContain('data-contour-level="0.000002"');
    expect(html).toContain('data-on-slice="true"');
    expect(html).toContain('data-on-slice="false"');
    expect(html).toContain(t("rsm.plot.hullNotice"));
    expect(html).toContain(t("rsm.plot.designNotice"));
  });

  it("uses coded coordinates and labels as supplied without applying a second conversion", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    const coded = ([x, y]: RsmVertex): RsmVertex => [x - 1, (y - 15) / 5];
    bundle.settings.axis_scale = "coded";
    bundle.x_axis = { ...bundle.x_axis, unit: null, minimum: -1, maximum: 1 };
    bundle.y_axis = { ...bundle.y_axis!, unit: null, minimum: -1, maximum: 1 };
    bundle.points = bundle.points.map((point) => ({ ...point, x: point.x - 1, y: (point.y - 15) / 5 }));
    bundle.geometry!.bands.forEach((band) => band.polygons.forEach((polygon) => {
      polygon.rings = polygon.rings.map((ring) => ring.map(coded));
    }));
    bundle.geometry!.lines.forEach((line) => { line.paths = line.paths.map((path) => path.map(coded)); });
    bundle.hull_slice_polygon = bundle.hull_slice_polygon.map(coded);
    bundle.design_points = bundle.design_points.map((point) => ({ ...point, x: point.x - 1, y: (point.y - 15) / 5 }));
    const html = render(bundle);
    expect(html).toContain(`Temperature (${t("charts.coded")})`);
    expect(html).toContain(`Pressure (${t("charts.coded")})`);
    expect(html).not.toContain("Temperature (K)");
    expect(html).not.toContain("Pressure (bar)");
    expect(bands(html)[0]).toContain(
      'd="M72,256L456,256L456,24L72,24ZM168,198L360,198L360,82L168,82Z"',
    );
    expect(html).toContain("<td>-1</td><td>-1</td><td>0.000001</td>");
    expect(html).toContain("Feed=1e-6");
  });

  it("keeps constant tiny response values nonzero without inventing contour lines", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    bundle.points = bundle.points.map((point) => ({ ...point, predicted: 1e-12 }));
    bundle.geometry = {
      ...bundle.geometry!, minimum: 1e-12, maximum: 1e-12, constant: true, levels: [],
      lines: [], bands: [{ lower: null, upper: null, polygons: [{ rings: [outer] }] }],
    };
    const html = render(bundle);
    const legend = html.match(/<div class="chart-color-scale rsm-contour-legend">[\s\S]*?<\/div>/)?.[0] ?? "";
    expect(legend).toContain("1e-12");
    expect(legend).not.toContain("inf");
    expect(html).not.toContain("data-contour-level");
    expect(html).not.toMatch(/(?:NaN|Infinity)/);
    expect(bands(html)).toHaveLength(1);
    expect(html.match(/<td>1e-12<\/td>/g)).toHaveLength(4);
  });

  it("distinguishes adjacent large stored thresholds when ordinary significant digits collide", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    bundle.geometry!.levels = [1e12 + 1, 1e12 + 2];
    bundle.geometry!.bands = [
      { lower: null, upper: 1e12 + 1, polygons: [] },
      { lower: 1e12 + 1, upper: 1e12 + 2, polygons: [{ rings: [outer] }] },
      { lower: 1e12 + 2, upper: null, polygons: [] },
    ];
    bundle.geometry!.lines = [1e12 + 1, 1e12 + 2].map((level) => ({
      level, paths: [[[0, 10], [2, 20]]],
    }));
    const html = render(bundle);
    expect(html).toContain("1000000000001 .. 1000000000002");
    expect(html).toContain(">1000000000001</text>");
    expect(html).toContain(">1000000000002</text>");
  });

  it("changes only presentation when fills, lines and design points are disabled", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    bundle.settings = { ...bundle.settings, filled: false, lines: false, design_points: false };
    const before = JSON.stringify(bundle);
    const html = render(bundle);
    expect(html).not.toContain("data-contour-band");
    expect(html).not.toContain("data-contour-level");
    expect(html).not.toContain("data-on-slice");
    expect(html.match(/data-grid-cell=/g)).toHaveLength(4);
    expect(html).toContain('fill-rule="evenodd"');
    expect(html).toContain("<td>0</td><td>10</td><td>0.000001</td>");
    expect(JSON.stringify(bundle)).toBe(before);
  });

  it("keeps main-effect values on the response axis without a fabricated second factor", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    bundle.settings = { ...bundle.settings, plot_kind: "main_effect", y_factor_id: null };
    bundle.y_axis = null;
    bundle.geometry = null;
    bundle.points = [0, 1, 2].map((x) => ({
      point_id: `main:${x}`, x, y: (x + 1) * 1e-6, predicted: (x + 1) * 1e-6,
      outside_design_hull: false,
    }));
    bundle.curves = [{ series_id: "trace:0", trace_actual_value: null, points: bundle.points }];
    const before = JSON.stringify(bundle);
    const html = render(bundle);
    expect(html).toContain('data-chart-id="rsm-conditional"');
    expect(html).toContain("Temperature (K)");
    expect(html).toContain("Yield (mg/L)");
    expect(html).not.toContain("Pressure");
    expect(html).not.toContain("data-grid-cell");
    expect(html).toContain('aria-label="Temperature (K): 0; Yield (mg/L): 1e-6"');
    expect(html.match(/<path class="interactive-data-line /g)).toHaveLength(1);
    expect(html.match(/tabindex="0"/g)).toHaveLength(1);
    expect(JSON.stringify(bundle)).toBe(before);
  });

  it("keeps interaction traces separate and labels their stored actual factor levels", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    bundle.settings = { ...bundle.settings, plot_kind: "interaction", trace_actual_values: [10, 20] };
    bundle.geometry = null;
    bundle.curves = [10, 20].map((trace, index) => ({
      series_id: `trace:${index}`, trace_actual_value: trace,
      points: [0, 2].map((x) => ({
        point_id: `trace:${index}:node:${x}`, x, y: (index + x + 1) * 1e-6,
        predicted: (index + x + 1) * 1e-6, outside_design_hull: false,
      })),
    }));
    bundle.points = bundle.curves.flatMap((curve) => curve.points);
    const html = render(bundle);
    expect(html).toContain("Pressure=10");
    expect(html).toContain("Pressure=20");
    expect(html).toContain("Yield (mg/L)");
    const paths = [...html.matchAll(/<path class="interactive-data-line [^"]+" d="([^"]*)"/g)]
      .map((match) => match[1]);
    expect(paths).toHaveLength(2);
    paths.forEach((path) => {
      expect(path.match(/M/g)).toHaveLength(1);
      expect(path.match(/L/g)).toHaveLength(1);
    });
    expect(html.match(/tabindex="0"/g)).toHaveLength(1);
  });

  it("escapes user names and preserves private-use characters in visible labels", () => {
    setCurrentLocale(locale);
    const bundle = fixture();
    bundle.x_axis.name = 'X <script>"\ue000known.key\ue001';
    bundle.response_name = "Y <img src=x onerror=alert(1)>";
    bundle.held_actual_values = { 'Hold <svg onload="bad">': 1e-6 };
    const html = render(bundle);
    expect(html).toContain("X &lt;script&gt;&quot;\ue000known.key\ue001");
    expect(html).toContain("Y &lt;img src=x onerror=alert(1)&gt;");
    expect(html).toContain("Hold &lt;svg onload=&quot;bad&quot;&gt;=1e-6");
    expect(html).not.toContain("<script");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("<svg onload");
  });
});

it("keeps contour geometry stable across locales and uses instance-unique SVG ids", () => {
  const bundle = fixture();
  setCurrentLocale("ko");
  const ko = render(bundle);
  setCurrentLocale("en");
  expect(bands(render(bundle))).toEqual(bands(ko));
  const html = renderToStaticMarkup(<>
    <ResponseSurfaceContourChart bundle={bundle} sourceKey="analysis:1:view:1" />
    <ResponseSurfaceContourChart bundle={bundle} sourceKey="analysis:2:view:1" />
  </>);
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]);
  expect(ids.length).toBeGreaterThan(4);
  expect(new Set(ids).size).toBe(ids.length);
  expect(html.match(/<pattern /g)).toHaveLength(2);
});
