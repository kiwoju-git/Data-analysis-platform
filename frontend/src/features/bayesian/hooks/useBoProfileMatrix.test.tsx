import * as React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { useBoProfileMatrix } from "./useBoProfileMatrix";
import type { ProfileMatrixRow, ProfileMatrixView } from "../boProfileMatrix";
import { BayesianProfileMatrix } from "../BayesianProfileMatrix";
import { InteractiveScatterChart, type InteractiveScatterChartProps } from "../../../charts/InteractiveScatterChart";
import { setCurrentLocale } from "../../../i18n/store";

type Slot = { value?: unknown; deps?: React.DependencyList; cleanup?: () => void };
const dispatcher = (React as unknown as { __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: { ReactCurrentDispatcher: { current: unknown } } }).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentDispatcher;
const runners: Runner<unknown>[] = [];
class Runner<T> {
  private slots: Slot[] = []; private cursor = 0; private pending = true;
  output!: T;
  constructor(private component: () => T) { runners.push(this); this.render(); }
  act(action: () => void) { action(); this.pending = true; this.render(); }
  async flush() { for (let i = 0; i < 20; i++) { await Promise.resolve(); this.render(); } }
  unmount() { this.slots.forEach(slot => slot.cleanup?.()); }
  private slot() { const index = this.cursor++; return this.slots[index] ?? (this.slots[index] = {}); }
  private render() {
    while (this.pending) {
      this.pending = false; this.cursor = 0;
      const effects: (() => void)[] = [], previous = dispatcher.current;
      dispatcher.current = {
        useContext: () => null,
        useRef: (value: unknown) => { const slot = this.slot(); if (!("value" in slot)) slot.value = { current: value }; return slot.value; },
        useState: (initial: unknown) => { const slot = this.slot(); if (!("value" in slot)) slot.value = typeof initial === "function" ? (initial as () => unknown)() : initial;
          return [slot.value, (next: unknown) => { slot.value = typeof next === "function" ? (next as (old: unknown) => unknown)(slot.value) : next; this.pending = true; }]; },
        useEffect: (effect: React.EffectCallback, deps?: React.DependencyList) => { const slot = this.slot(); if (!slot.deps || !deps || deps.some((value, index) => !Object.is(value, slot.deps?.[index]))) effects.push(() => { slot.cleanup?.(); const cleanup = effect(); slot.cleanup = typeof cleanup === "function" ? cleanup : undefined; slot.deps = deps; }); },
      };
      try { this.output = this.component(); } finally { dispatcher.current = previous; }
      effects.forEach(effect => effect());
    }
  }
}
function deferred<T>() { let resolve!: (value: T) => void, reject!: (error: Error) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; }
const view: Omit<ProfileMatrixView, "axes"> = { modelId: "model", modelHash: "hash", historyHash: "history", holds: { x: 1 }, responses: [{ response_id: "desirability", name: "Real response", unit: "mg" }] };
const row: ProfileMatrixRow = { row_id: "row", actual_coordinates: { x: 1 }, constraints_satisfied: true, desirability_moments: { mean: .5 }, response_predictions: [{ response_id: "desirability", mean_raw: 100, latent_standard_deviation_raw: 2, predictive_standard_deviation_raw: 3 }] };
const axes = [{ factor_id: "x", name: "X", unit: "C", category: false, rows: [] }];
const inputs = [{ factorId: "x", points: [{ x: 1 }] }];
afterEach(() => { runners.splice(0).forEach(runner => runner.unmount()); setCurrentLocale("ko"); });

describe("matrix source ownership", () => {
  it("preserves known safe budget errors but redacts arbitrary failures", async () => {
    const runner = new Runner(() => useBoProfileMatrix("source"));
    for (const [message, expected] of [["bayesian_profile_budget", "bayesian_profile_budget"], ["private local path", "bayesian_profile_matrix_failed"]]) {
      runner.act(() => { void runner.output.run(view, axes, inputs, () => Promise.reject(Error(message))); });
      await runner.flush(); expect(runner.output.error).toBe(expected); expect(runner.output.view).toBeNull();
    }
  });
  it("snapshots queued coordinates at click time rather than after the previous request", async () => {
    let source = "A";
    const runner = new Runner(() => useBoProfileMatrix(source)), first = deferred<ProfileMatrixRow[]>();
    runner.act(() => { void runner.output.run(view, axes, inputs, () => first.promise); }); await runner.flush();
    runner.act(() => { source = "B"; });
    const queued = [{ factorId: "x", points: [{ x: 1 }] }]; let evaluated: { x: number }[] = [];
    runner.act(() => { void runner.output.run(view, axes, queued, points => { evaluated = points; return Promise.resolve([row]); }); });
    queued[0].points[0].x = 999;
    first.resolve([row]); await runner.flush();
    expect(evaluated).toEqual([{ x: 1 }]); expect(runner.output.view?.holds.x).toBe(1);
  });
  it.each(["success", "error"] as const)("invalidates delayed %s across holds A-B-A and does not clear newer busy state", async outcome => {
    let source = "A";
    const runner = new Runner(() => useBoProfileMatrix(source)), old = deferred<ProfileMatrixRow[]>(), next = deferred<ProfileMatrixRow[]>();
    runner.act(() => { void runner.output.run(view, axes, inputs, () => old.promise); }); await runner.flush();
    expect(runner.output.busy).toBe(true);
    runner.act(() => { source = "B"; }); expect(runner.output.view).toBeNull(); expect(runner.output.busy).toBe(false);
    runner.act(() => { source = "A"; });
    let calls = 0;
    runner.act(() => { void runner.output.run(view, axes, inputs, () => { calls++; return next.promise; }); });
    await runner.flush(); expect(calls).toBe(0);
    if (outcome === "success") old.resolve([row]); else old.reject(Error("late source mismatch"));
    await runner.flush(); expect(calls).toBe(1); expect(runner.output.busy).toBe(true); expect(runner.output.error).toBeNull(); expect(runner.output.view).toBeNull();
    next.resolve([row]); await runner.flush(); expect(runner.output.busy).toBe(false); expect(runner.output.view?.modelHash).toBe("hash");
  });
  it("does not publish after unmount or mutation of request inputs", async () => {
    const runner = new Runner(() => useBoProfileMatrix("source")), response = deferred<ProfileMatrixRow[]>();
    const hold = { ...view, holds: { x: 1 } };
    runner.act(() => { void runner.output.run(hold, axes, inputs, () => response.promise); });
    hold.holds.x = 999; await runner.flush(); response.resolve([row]); await runner.flush();
    expect(runner.output.view?.holds.x).toBe(1);
    const late = deferred<ProfileMatrixRow[]>(); runner.act(() => { void runner.output.run(view, axes, inputs, () => late.promise); }); await runner.flush(); runner.unmount(); late.resolve([row]); await runner.flush(); expect(runner.output.view).toBeNull();
  });
});

type Element = React.ReactElement<Record<string, unknown>>;
function elements(node: React.ReactNode): Element[] { if (Array.isArray(node)) return node.flatMap(elements); if (!React.isValidElement<Record<string, unknown>>(node)) return []; return [node, ...elements(node.props.children as React.ReactNode)]; }
describe("matrix display-only controls", () => {
  it("shares each response scale over every factor and switches SD/pagination without evaluating", () => {
    setCurrentLocale("en");
    const matrix: ProfileMatrixView = { ...view, axes: Array.from({ length: 3 }, (_, i) => ({ factor_id: `x${i}`, name: `Factor ${i}`, unit: "C", category: false, rows: [{ ...row, actual_coordinates: { [`x${i}`]: 1 }, response_predictions: [{ ...row.response_predictions[0], mean_raw: i * 100, latent_standard_deviation_raw: i + 2, predictive_standard_deviation_raw: i + 3 }] }] })) };
    const runner = new Runner(() => BayesianProfileMatrix({ view: matrix }));
    const charts = () => elements(runner.output).filter(item => item.type === InteractiveScatterChart).map(item => item.props as unknown as InteractiveScatterChartProps);
    expect(charts()).toHaveLength(4); expect(charts()[0].yRange).toEqual(charts()[1].yRange); expect(charts()[0].yRange.max).toBeGreaterThanOrEqual(200);
    for (const metric of ["latent_standard_deviation_raw", "predictive_standard_deviation_raw"]) {
      const select = elements(runner.output).find(item => item.type === "select")!;
      runner.act(() => (select.props.onChange as (event: { currentTarget: { value: string } }) => void)({ currentTarget: { value: metric } }));
      expect(charts()[0].points[0].y).toBe(metric.startsWith("latent") ? 2 : 3); expect(charts()[0].yRange).toEqual(charts()[1].yRange);
    }
    const next = elements(runner.output).find(item => item.props["aria-label"] === "Next page")!;
    runner.act(() => (next.props.onClick as () => void)()); expect(charts()).toHaveLength(2); expect(charts()[0].title).toBe("Factor 2");
    runner.act(() => setCurrentLocale("ko")); expect(charts()[0].points[0].y).toBe(5);
  });
});
