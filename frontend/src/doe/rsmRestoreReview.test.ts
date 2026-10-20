import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ResponseSurfacePanel, ResponseSurfaceResponseEntry } from "../ResponseSurfacePanel";
import type { DoeResponseSurfaceAnalysisResponse, ResponseSurfaceDesignResponse } from "../api";
import type { RsmPlotBundle, RsmPlotSource, RsmPlotView } from "../api/types/rsmPlots";
import { RsmPlotOptions } from "./RsmPlotOptions";
import { DoeModelSelectionSettings } from "./DoeModelSelectionSettings";

const reads = vi.hoisted(() => ({
  design: vi.fn(), analysis: vi.fn(), revision: vi.fn(), history: vi.fn(),
}));
const plots = vi.hoisted(() => ({ source: vi.fn(), list: vi.fn(), restore: vi.fn() }));
vi.mock("../api", async (original) => ({
  ...await original<typeof import("../api")>(),
  fetchResponseSurfaceDesign: reads.design,
  fetchResponseSurfaceAnalysis: reads.analysis,
  fetchDoeResponseRevision: reads.revision,
  fetchDoeResponseRevisions: reads.history,
}));
vi.mock("./RsmModelTerms", async (original) => ({
  ...await original<typeof import("./RsmModelTerms")>(),
  useRsmTermCatalog: () => ({ ready: true, terms: [], options: {}, error: false }),
}));
vi.mock("../api/rsmPlots", async (original) => ({
  ...await original<typeof import("../api/rsmPlots")>(),
  fetchRsmPlotSource: plots.source,
  fetchRsmPlotViews: plots.list,
  fetchRsmPlotView: plots.restore,
}));

type Element = React.ReactElement<Record<string, unknown>>;
type Slot = {
  value?: unknown; deps?: React.DependencyList; cleanup?: () => void; effect?: boolean;
};
const internals = (React as unknown as {
  __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: {
    ReactCurrentDispatcher: { current: unknown };
  };
}).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
const runners: RestoreRunner[] = [];

// The existing node hook-runner pattern, without a new DOM/test-renderer dependency.
class RestoreRunner {
  private slots: Slot[] = [];
  private cursor = 0;
  private pending = true;
  private effects: Array<() => void> = [];
  output: React.ReactNode;

  constructor(private component: () => React.ReactNode = ResponseSurfacePanel) {
    runners.push(this); this.render();
  }
  act(action: () => void) { action(); this.render(); }
  async flush() {
    for (let index = 0; index < 12; index += 1) { await Promise.resolve(); this.render(); }
  }
  unmount() { for (const slot of this.slots) if (slot.effect) slot.cleanup?.(); }
  private slot() {
    const index = this.cursor++;
    return this.slots[index] ?? (this.slots[index] = {});
  }
  private changed(slot: Slot, deps?: React.DependencyList) {
    return !slot.deps || !deps || slot.deps.length !== deps.length
      || deps.some((value, index) => !Object.is(value, slot.deps?.[index]));
  }
  private memo(factory: () => unknown, deps?: React.DependencyList) {
    const slot = this.slot();
    if (this.changed(slot, deps)) { slot.value = factory(); slot.deps = deps; }
    return slot.value;
  }
  private effect(create: React.EffectCallback, deps?: React.DependencyList) {
    const slot = this.slot(); slot.effect = true;
    if (this.changed(slot, deps)) this.effects.push(() => {
      slot.cleanup?.();
      const cleanup = create();
      slot.cleanup = typeof cleanup === "function" ? cleanup : undefined;
      slot.deps = deps;
    });
  }
  private render() {
    while (this.pending) {
      this.pending = false; this.cursor = 0; this.effects = [];
      const previous = internals.ReactCurrentDispatcher.current;
      internals.ReactCurrentDispatcher.current = {
        useContext: () => null,
        useRef: (initial: unknown) => {
          const slot = this.slot();
          if (!("value" in slot)) slot.value = { current: initial };
          return slot.value;
        },
        useState: (initial: unknown) => {
          const slot = this.slot();
          if (!("value" in slot)) slot.value = typeof initial === "function"
            ? (initial as () => unknown)() : initial;
          return [slot.value, (next: unknown) => {
            const value = typeof next === "function"
              ? (next as (previous: unknown) => unknown)(slot.value) : next;
            if (!Object.is(slot.value, value)) { slot.value = value; this.pending = true; }
          }];
        },
        useMemo: (factory: () => unknown, deps?: React.DependencyList) => this.memo(factory, deps),
        useCallback: (callback: unknown, deps?: React.DependencyList) => this.memo(() => callback, deps),
        useEffect: (create: React.EffectCallback, deps?: React.DependencyList) => this.effect(create, deps),
        useLayoutEffect: (create: React.EffectCallback, deps?: React.DependencyList) => this.effect(create, deps),
      };
      try { this.output = this.component(); }
      finally { internals.ReactCurrentDispatcher.current = previous; }
      for (const effect of this.effects) effect();
    }
  }
}

function elements(node: React.ReactNode): Element[] {
  if (Array.isArray(node)) return node.flatMap(elements);
  if (!React.isValidElement<Record<string, unknown>>(node)) return [];
  return [node, ...elements(node.props.children as React.ReactNode)];
}
function responseEntry(runner: RestoreRunner) {
  const entry = elements(runner.output).find((element) => element.type === ResponseSurfaceResponseEntry);
  if (!entry) throw new Error("restored_response_entry_missing");
  return entry.props;
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((accept, fail) => { resolve = accept; reject = fail; });
  return { promise, resolve, reject };
}

const DESIGN_A = "11111111-1111-4111-8111-111111111111";
const DESIGN_B = "22222222-2222-4222-8222-222222222222";
const ANALYSIS_A = "33333333-3333-4333-8333-333333333333";
const ANALYSIS_B = "44444444-4444-4444-8444-444444444444";
const VERSION_A = "55555555-5555-4555-8555-555555555555";
const REVISION_A = "66666666-6666-4666-8666-666666666666";
const sourceA = {
  design_id: DESIGN_A, design_version_id: VERSION_A, design_sha256: "a".repeat(64),
  name: "Completed synthetic A", factors: [
    { name: "A", low: -1, high: 1, unit: null },
    { name: "B", low: -1, high: 1, unit: null },
  ],
  options: { ccd_type: "inscribed", center_points: 5, randomize: false, randomization_seed: 7 },
  runs: [],
};
const analysisA = {
  design_id: DESIGN_A, analysis_id: ANALYSIS_A, design_version_id: VERSION_A,
  design_sha256: sourceA.design_sha256, response_revision_id: REVISION_A,
  response_revision_sha256: "b".repeat(64),
  result: { terms: [], term_preset: "full_quadratic", model_selection: null },
};
const revisionA = {
  response_revision_id: REVISION_A, design_version_id: VERSION_A, state: "completed",
  response_revision_sha256: analysisA.response_revision_sha256,
  response_name: "Response", unit: "mm", values: [], revision_number: 1,
};
let events: EventTarget & { location: { search: string } };
function navigate(runner: RestoreRunner, search: string) {
  runner.act(() => {
    events.location.search = search;
    events.dispatchEvent(new Event("popstate"));
  });
}

beforeEach(() => {
  vi.resetAllMocks();
  events = Object.assign(new EventTarget(), {
    location: { search: `?design_id=${DESIGN_A}&analysis_id=${ANALYSIS_A}` },
  });
  vi.stubGlobal("window", events);
  reads.analysis.mockResolvedValue(analysisA);
  reads.revision.mockResolvedValue(revisionA);
  reads.history.mockResolvedValue({ items: [] });
});
afterEach(() => {
  for (const runner of runners.splice(0)) runner.unmount();
  vi.unstubAllGlobals();
});

describe("saved RSM route restore ownership", () => {
  it.each([
    ["route without saved identifiers", ""],
    ["invalid saved UUID", "?design_id=invalid&analysis_id=invalid"],
  ])("releases pending restore busy state after navigating to %s", async (_label, route) => {
    const pending = deferred<typeof sourceA>();
    reads.design.mockImplementation((id: string) => id === DESIGN_A
      ? Promise.resolve(sourceA) : pending.promise);
    const runner = new RestoreRunner();
    await runner.flush();
    expect(responseEntry(runner).isRestoring).toBe(false);
    expect(responseEntry(runner).canAnalyze).toBe(true);
    navigate(runner, `?design_id=${DESIGN_B}&analysis_id=${ANALYSIS_B}`);
    await runner.flush();
    expect(responseEntry(runner).isRestoring).toBe(true);
    expect(responseEntry(runner).canAnalyze).toBe(false);
    navigate(runner, route);
    await runner.flush();
    expect(responseEntry(runner).isRestoring).toBe(false);
    expect(responseEntry(runner).canAnalyze).toBe(true);
    expect(responseEntry(runner).design).toEqual(sourceA);
    pending.reject(new Error("late_previous_restore_failure"));
    await runner.flush();
    expect(responseEntry(runner).isRestoring).toBe(false);
    expect(responseEntry(runner).design).toEqual(sourceA);
    expect(reads.analysis).toHaveBeenCalledTimes(1);
  });

  it("restores legacy selection defaults instead of carrying the previous backward draft", async () => {
    const sourceB = {
      ...sourceA, design_id: DESIGN_B,
      design_version_id: "88888888-8888-4888-8888-888888888888",
      design_sha256: "f".repeat(64), name: "Legacy synthetic B",
    };
    const legacy = {
      ...analysisA, design_id: DESIGN_B, analysis_id: ANALYSIS_B,
      design_version_id: sourceB.design_version_id, design_sha256: sourceB.design_sha256,
      response_revision_id: "99999999-9999-4999-8999-999999999999",
      response_revision_sha256: "d".repeat(64),
      result: { terms: [], term_preset: "full_quadratic" },
    };
    const previous = {
      ...analysisA, result: {
        ...analysisA.result, model_selection: {
          method: "backward_elimination", alpha_to_remove: .1, hierarchy_policy: "strong",
          display_step_details: false,
          term_policies: [{ term_id: "factor_1", disposition: "forced" }],
        },
      },
    };
    reads.design.mockImplementation((id: string) => Promise.resolve(
      id === DESIGN_A ? sourceA : sourceB,
    ));
    reads.analysis.mockImplementation((_design: string, id: string) => Promise.resolve(
      id === ANALYSIS_A ? previous : legacy,
    ));
    reads.revision.mockImplementation((design: string) => Promise.resolve(
      design === DESIGN_A ? revisionA : {
        ...revisionA, response_revision_id: legacy.response_revision_id,
        response_revision_sha256: legacy.response_revision_sha256,
        design_version_id: sourceB.design_version_id,
      },
    ));
    const runner = new RestoreRunner();
    const selection = () => {
      const settings = elements(responseEntry(runner).modelSettings as React.ReactNode)
        .find((element) => element.type === DoeModelSelectionSettings);
      if (!settings) throw new Error("restored_model_settings_missing");
      return settings.props.value;
    };
    await runner.flush();
    expect(selection()).toMatchObject(previous.result.model_selection);
    navigate(runner, `?design_id=${DESIGN_B}&analysis_id=${ANALYSIS_B}`);
    await runner.flush();
    expect(responseEntry(runner).isRestoring).toBe(false);
    expect(responseEntry(runner).design).toEqual(sourceB);
    expect(selection()).toEqual({
      method: "none", alpha_to_remove: .05, hierarchy_policy: "strong",
      saturated_start_policy: "pool_smallest_adjusted_ss",
      display_step_details: true, term_policies: [],
    });
  });

  it("keeps saved-view selection disabled when the list arrives before the verified source", async () => {
    const source: RsmPlotSource = {
      expected_result_sha256: "c".repeat(64), response_revision_id: REVISION_A,
      response_revision_sha256: analysisA.response_revision_sha256,
    };
    const pendingSource = deferred<RsmPlotSource>();
    const bundle: RsmPlotBundle = {
      schema_version: 1,
      settings: {
        plot_kind: "contour", x_factor_id: "factor_1", y_factor_id: "factor_2",
        held_actual_values: {}, axis_scale: "coded", grid_size: 21,
        contour_levels: { count: 6, thresholds: null }, trace_actual_values: null,
        filled: true, lines: true, design_points: true,
      },
      x_axis: { factor_id: "factor_1", name: "A", unit: null, minimum: -1, maximum: 1 },
      y_axis: { factor_id: "factor_2", name: "B", unit: null, minimum: -1, maximum: 1 },
      response_name: "Response", response_unit: "mm", held_actual_values: {},
      points: [], curves: [], geometry: null, design_points: [], hull_slice_polygon: [],
      hull_policy: "full_design_coded_convex_hull", final_term_ids: ["Intercept", "factor_1"],
    };
    const view: RsmPlotView = {
      schema_version: 1, design_id: DESIGN_A, design_version_id: VERSION_A,
      design_sha256: sourceA.design_sha256, analysis_id: ANALYSIS_A,
      ...source, view_sha256: "d".repeat(64), bundle,
    };
    const saved = {
      asset_id: "77777777-7777-4777-8777-777777777777",
      sha256: "e".repeat(64), created_at: "2026-10-21T00:00:00Z",
    };
    plots.source.mockReturnValue(pendingSource.promise);
    plots.list.mockResolvedValue([saved]);
    plots.restore.mockResolvedValue({ ...saved, view });
    const runner = new RestoreRunner(() => RsmPlotOptions({
      design: sourceA as unknown as ResponseSurfaceDesignResponse,
      analysis: {
        ...analysisA, result: { ...analysisA.result, plot_bundle: bundle, plot_overview: [] },
      } as unknown as DoeResponseSurfaceAnalysisResponse,
    }));
    const select = () => {
      const element = elements(runner.output).find((candidate) =>
        candidate.type === "select" && elements(candidate.props.children as React.ReactNode)
          .some((child) => child.type === "option" && child.props.value === saved.asset_id));
      if (!element) throw new Error("saved_view_select_missing");
      return element;
    };
    await runner.flush();
    expect(Boolean(select().props.disabled)).toBe(true);
    expect(plots.restore).not.toHaveBeenCalled();
    pendingSource.resolve(source);
    await runner.flush();
    expect(Boolean(select().props.disabled)).toBe(false);
    runner.act(() => (select().props.onChange as
      (event: { target: { value: string } }) => void)({ target: { value: saved.asset_id } }));
    expect(Boolean(select().props.disabled)).toBe(true);
    await runner.flush();
    expect(select().props.value).toBe(saved.asset_id);
    expect(Boolean(select().props.disabled)).toBe(false);
    expect(plots.restore).toHaveBeenCalledWith(DESIGN_A, ANALYSIS_A, saved.asset_id);
    expect(elements(runner.output).filter((element) => element.props.role === "alert")).toHaveLength(0);
  });
});
