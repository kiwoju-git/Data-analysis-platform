import * as React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { evaluateBoView, type BoViewReceipt } from "../../../api/boViews";
import { useBoDiagnosticView } from "./useBoDiagnosticView";
import { receiptFixture, viewRequest, viewSource } from "../boSavedViews.test.fixture";

vi.mock("../../../api/boViews", () => ({ evaluateBoView: vi.fn() }));
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
const expected = { studyId: "study", modelId: "model", modelHash: viewSource.model_sha256, historyHash: viewSource.history_sha256, responseIds: ["desirability"], factorIds: ["x", "category"] };
afterEach(() => { runners.splice(0).forEach(runner => runner.unmount()); vi.resetAllMocks(); });

describe("server receipt UI ownership", () => {
  it.each(["success", "error"] as const)("rejects late %s after holds A-B-A and preserves newer loading", async outcome => {
    let source = "A";
    const first = deferred<BoViewReceipt>(), second = deferred<BoViewReceipt>();
    vi.mocked(evaluateBoView).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const runner = new Runner(() => useBoDiagnosticView(source));
    runner.act(() => { void runner.output.run(expected, viewRequest); }); await runner.flush();
    runner.act(() => { source = "B"; }); expect(runner.output.busy).toBe(false);
    runner.act(() => { source = "A"; });
    runner.act(() => { void runner.output.run(expected, viewRequest); }); await runner.flush();
    expect(evaluateBoView).toHaveBeenCalledTimes(1);
    if (outcome === "success") first.resolve(receiptFixture()); else first.reject(Error("private raw exception"));
    await runner.flush(); expect(evaluateBoView).toHaveBeenCalledTimes(2);
    expect(runner.output.busy).toBe(true); expect(runner.output.error).toBe(false); expect(runner.output.receipt).toBeNull();
    second.resolve(receiptFixture()); await runner.flush();
    expect(runner.output.receipt?.view_sha256).toBe("f".repeat(64)); expect(runner.output.busy).toBe(false);
  });
  it("snapshots request before the serialized queue and never auto-retries a failed POST", async () => {
    const first = deferred<BoViewReceipt>();
    vi.mocked(evaluateBoView).mockReturnValueOnce(first.promise).mockRejectedValueOnce(Error("offline"));
    const runner = new Runner(() => useBoDiagnosticView("source"));
    runner.act(() => { void runner.output.run(expected, viewRequest); }); await runner.flush();
    const request = structuredClone(viewRequest);
    runner.act(() => { void runner.output.run(expected, request); }); request.holds.x = 999;
    first.resolve(receiptFixture()); await runner.flush();
    expect(vi.mocked(evaluateBoView).mock.calls[1][2]).toEqual(viewRequest);
    expect(runner.output.error).toBe(true); expect(runner.output.receipt).toBeNull(); expect(runner.output.pending).toBe(false);
    await runner.flush(); expect(evaluateBoView).toHaveBeenCalledTimes(2);
  });
  it("rejects invalid response source and does not publish after unmount", async () => {
    const invalid = receiptFixture(); invalid.payload.source.model_sha256 = "0".repeat(64);
    vi.mocked(evaluateBoView).mockResolvedValueOnce(invalid);
    const runner = new Runner(() => useBoDiagnosticView("source"));
    runner.act(() => { void runner.output.run(expected, viewRequest); }); await runner.flush();
    expect(runner.output.error).toBe(true); expect(runner.output.receipt).toBeNull();
    const last = deferred<BoViewReceipt>(); vi.mocked(evaluateBoView).mockReturnValueOnce(last.promise);
    runner.act(() => { void runner.output.run(expected, viewRequest); }); await runner.flush(); runner.unmount();
    last.resolve(receiptFixture()); await runner.flush(); expect(runner.output.receipt).toBeNull();
  });
});
