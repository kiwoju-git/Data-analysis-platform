import { describe, expect, it } from "vitest";
import type { RsmPlotSettings, RsmPlotSource, RsmPlotView } from "../api/types/rsmPlots";
import { rsmViewMatchesSnapshot } from "./rsmPlotSnapshot";

function fixture() {
  const source: RsmPlotSource = {
    expected_result_sha256: "a".repeat(64),
    response_revision_id: "revision-1",
    response_revision_sha256: "b".repeat(64),
  };
  const settings: RsmPlotSettings = {
    plot_kind: "contour", x_factor_id: "factor_1", y_factor_id: "factor_2",
    held_actual_values: { factor_3: 1000.000001, factor_4: 1e-6 },
    axis_scale: "actual", grid_size: 21, contour_levels: { count: 3, thresholds: null },
    trace_actual_values: null, filled: true, lines: true, design_points: true,
  };
  const snapshot = { design: "design-1", analysis: "analysis-1", source, settings };
  const view: RsmPlotView = {
    schema_version: 1, design_id: snapshot.design, design_version_id: "version-1",
    design_sha256: "c".repeat(64), analysis_id: snapshot.analysis, ...source,
    view_sha256: "d".repeat(64),
    bundle: {
      schema_version: 1, settings: structuredClone(settings),
      x_axis: { factor_id: "factor_1", name: "Temperature", unit: "K", minimum: 0, maximum: 2 },
      y_axis: { factor_id: "factor_2", name: "Pressure", unit: "bar", minimum: 10, maximum: 20 },
      response_name: "Yield", response_unit: "mg/L",
      held_actual_values: { Feed: 1000.000001, Catalyst: 1e-6 },
      points: [], curves: [], geometry: null, design_points: [], hull_slice_polygon: [],
      hull_policy: "full_design_coded_convex_hull", final_term_ids: ["Intercept", "A"],
    },
  };
  return { snapshot, view };
}

describe("RSM exact request snapshot matching", () => {
  it("accepts the exact immutable source and settings without mutating either", () => {
    const { snapshot, view } = fixture();
    const before = JSON.stringify({ snapshot, view });
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(true);
    expect(JSON.stringify({ snapshot, view })).toBe(before);
  });

  it("does not reject equivalent held settings merely because object insertion order changed", () => {
    const { snapshot, view } = fixture();
    view.bundle.settings.held_actual_values = { factor_4: 1e-6, factor_3: 1000.000001 };
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(true);
  });

  it.each([
    ["design_id", "design-2"],
    ["analysis_id", "analysis-2"],
    ["expected_result_sha256", "e".repeat(64)],
    ["response_revision_id", "revision-2"],
    ["response_revision_sha256", "f".repeat(64)],
  ] as const)("rejects a response from a different %s", (key, value) => {
    const { snapshot, view } = fixture();
    view[key] = value;
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(false);
  });

  it.each(["", "d".repeat(63), "d".repeat(65), "g".repeat(64), "D".repeat(64)])(
    "rejects an invalid view content hash %s",
    (hash) => {
      const { snapshot, view } = fixture();
      view.view_sha256 = hash;
      expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(false);
    },
  );

  const staleSettings: Array<[string, Partial<RsmPlotSettings>]> = [
    ["factor pair", { x_factor_id: "factor_2", y_factor_id: "factor_1" }],
    ["x factor", { x_factor_id: "factor_4" }],
    ["y factor", { y_factor_id: "factor_3" }],
    ["main effect", { plot_kind: "main_effect", y_factor_id: null }],
    ["interaction", { plot_kind: "interaction" }],
    ["held exact value", { held_actual_values: { factor_3: 1000.000002, factor_4: 1e-6 } }],
    ["tiny held exact value", { held_actual_values: { factor_3: 1000.000001, factor_4: 2e-6 } }],
    ["held variable identity", { held_actual_values: { factor_3: 1000.000001, factor_5: 1e-6 } }],
    ["axis scale", { axis_scale: "coded" }],
    ["grid size", { grid_size: 31 }],
    ["level count", { contour_levels: { count: 4, thresholds: null } }],
    ["explicit thresholds", { contour_levels: { count: 3, thresholds: [1e-6, 2e-6] } }],
    ["trace values", { trace_actual_values: [1e-6, 2e-6] }],
    ["filled polygons", { filled: false }],
    ["contour lines", { lines: false }],
    ["design points", { design_points: false }],
  ];

  it.each(staleSettings)("rejects stale %s settings before publishing a view", (_name, patch) => {
    const { snapshot, view } = fixture();
    view.bundle.settings = { ...view.bundle.settings, ...patch };
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(false);
  });

  it("compares ordered trace and threshold arrays without sorting the request", () => {
    const { snapshot, view } = fixture();
    snapshot.settings.trace_actual_values = [10, 20];
    snapshot.settings.contour_levels = { count: 3, thresholds: [1e-6, 2e-6] };
    view.bundle.settings = structuredClone(snapshot.settings);
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(true);
    view.bundle.settings.trace_actual_values = [20, 10];
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(false);
    view.bundle.settings.trace_actual_values = [10, 20];
    view.bundle.settings.contour_levels.thresholds = [2e-6, 1e-6];
    expect(rsmViewMatchesSnapshot(view, snapshot)).toBe(false);
  });
});
