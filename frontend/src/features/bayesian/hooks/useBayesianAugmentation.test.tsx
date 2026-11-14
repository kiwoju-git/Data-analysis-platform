import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../../../api/boAugmentation";
import * as planning from "../../../api/boPlanning";
import type { AugmentationRenewalRequest, AugmentationRenewalResponse } from "../../../api/types/boAugmentation";
import { augmentationFixture } from "../boAugmentation.fixture";
import { useBayesianAugmentation } from "./useBayesianAugmentation";

type Slot = { value?: unknown; deps?: React.DependencyList; cleanup?: () => void };
const dispatcher = (React as unknown as { __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED: { ReactCurrentDispatcher: { current: unknown } } }).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentDispatcher;
const runners: Runner<unknown>[] = [];
class Runner<T> {
  private slots: Slot[] = []; private cursor = 0; private pending = true;
  output!: T;
  constructor(private component: () => T) { runners.push(this); this.render(); }
  act(action: () => void) { action(); this.pending = true; this.render(); }
  async flush() { for (let i = 0; i < 30; i++) { await Promise.resolve(); this.render(); } }
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
function legacy() {
  const fixture = augmentationFixture(true);
  for (const row of fixture.selection.calculation.selected_rows) if ("acquisition" in row && row.acquisition) delete row.acquisition.numerical_policy;
  return fixture;
}
function renewed(fixture: ReturnType<typeof legacy>, request: AugmentationRenewalRequest): AugmentationRenewalResponse {
  const selection = structuredClone(fixture.selection);
  selection.selection_id = "a1111111-1111-4111-8111-111111111111";
  selection.request.request_id = request.request_id;
  selection.calculation.augmentation.steps[0].score = .123;
  for (const row of selection.calculation.selected_rows) if ("acquisition" in row && row.acquisition) row.acquisition.numerical_policy = "positive_beta_integral_v2";
  return { selection, lineage: { schema_version: 1, study_version_id: selection.study_version_id,
    renewed_selection_id: selection.selection_id, original_selection_id: fixture.selection.selection_id,
    original_config_sha256: fixture.selection.config_sha256, original_result_sha256: fixture.selection.result_sha256,
    numerical_policy: "positive_beta_integral_v2", created_at: selection.created_at } };
}
function mockSource(fixture: ReturnType<typeof legacy>) {
  vi.spyOn(planning, "listCandidateSets").mockResolvedValue({ items: [fixture.page.revision] });
  vi.spyOn(planning, "listPlanningModels").mockResolvedValue({ items: [fixture.model] });
  vi.spyOn(planning, "fetchCandidatePage").mockResolvedValue(fixture.page);
  vi.spyOn(planning, "fetchPlanningModel").mockResolvedValue(fixture.model);
  vi.spyOn(api, "fetchAugmentation").mockResolvedValue(fixture.selection);
  vi.spyOn(api, "fetchAugmentationRenewal").mockResolvedValue(null);
  vi.spyOn(api, "confirmAugmentation");
}
async function open(runner: Runner<ReturnType<typeof useBayesianAugmentation>>, id: string) {
  await runner.flush(); runner.act(() => runner.output.openSelection(id)); await runner.flush();
  expect(runner.output.selection?.selection_id).toBe(id);
}
beforeEach(() => vi.spyOn(globalThis.crypto, "randomUUID").mockReturnValue("b1111111-1111-4111-8111-111111111111"));
afterEach(() => { runners.splice(0).forEach(runner => runner.unmount()); vi.restoreAllMocks(); });

describe("saved augmentation renewal hook", () => {
  it("renews only the stored receipt and publishes exact new scores without auto-confirm", async () => {
    const fixture = legacy(); mockSource(fixture);
    const callback = vi.fn(), runner = new Runner(() => useBayesianAugmentation({ study: fixture.study, disabled: false, onConfirmed: callback }));
    const renew = vi.spyOn(api, "renewAugmentation").mockImplementation((_study, _id, request) => Promise.resolve(renewed(fixture, request)));
    await open(runner, fixture.selection.selection_id);
    expect(runner.output.canConfirm).toBe(false); expect(runner.output.canRenew).toBe(true);
    runner.act(() => runner.output.renew()); await runner.flush();
    expect(renew).toHaveBeenCalledWith(fixture.study.study_id, fixture.selection.selection_id, {
      request_id: "b1111111-1111-4111-8111-111111111111", expected_config_sha256: fixture.selection.config_sha256, expected_result_sha256: fixture.selection.result_sha256,
    });
    expect(runner.output.selection?.request).toEqual({ ...fixture.selection.request, request_id: "b1111111-1111-4111-8111-111111111111" });
    expect(runner.output.selection?.calculation.augmentation.steps[0].score).toBe(.123);
    expect(runner.output.renewal?.original_selection_id).toBe(fixture.selection.selection_id);
    expect(runner.output.canConfirm).toBe(true); expect(runner.output.busy).toBeNull();
    expect(api.confirmAugmentation).not.toHaveBeenCalled(); expect(callback).not.toHaveBeenCalled();
  });
  it("keeps the same request ID after a lost response and clears busy/error on manual replay", async () => {
    const fixture = legacy(); mockSource(fixture);
    const renew = vi.spyOn(api, "renewAugmentation").mockRejectedValueOnce(Error("api_unreachable"))
      .mockImplementationOnce((_study, _id, request) => Promise.resolve(renewed(fixture, request)));
    const runner = new Runner(() => useBayesianAugmentation({ study: fixture.study, disabled: false, onConfirmed: vi.fn() }));
    await open(runner, fixture.selection.selection_id);
    runner.act(() => runner.output.renew()); await runner.flush();
    expect(runner.output.canRetry).toBe(true); expect(runner.output.error).not.toBeNull(); expect(runner.output.busy).toBeNull();
    runner.act(() => runner.output.retry()); await runner.flush();
    expect(renew.mock.calls[1]).toEqual(renew.mock.calls[0]);
    expect(runner.output.canRetry).toBe(false); expect(runner.output.error).toBeNull(); expect(runner.output.busy).toBeNull();
    expect(runner.output.selection?.confirmed_batch_id).toBeNull(); expect(api.confirmAugmentation).not.toHaveBeenCalled();
  });
  it.each(["success", "error"] as const)("ignores old renewal %s and finally across source A-B-A", async outcome => {
    const fixture = legacy(); mockSource(fixture); let study = fixture.study;
    const first = deferred<AugmentationRenewalResponse>(), next = deferred<AugmentationRenewalResponse>();
    const renew = vi.spyOn(api, "renewAugmentation").mockReturnValueOnce(first.promise).mockReturnValueOnce(next.promise);
    const runner = new Runner(() => useBayesianAugmentation({ study, disabled: false, onConfirmed: vi.fn() }));
    await open(runner, fixture.selection.selection_id); runner.act(() => runner.output.renew()); await runner.flush();
    runner.act(() => { study = { ...fixture.study, observation_history: { ...fixture.study.observation_history, observation_history_sha256: "f".repeat(64) } }; }); await runner.flush();
    expect(runner.output.selection).toBeNull();
    runner.act(() => { study = fixture.study; }); await open(runner, fixture.selection.selection_id);
    runner.act(() => runner.output.renew()); await runner.flush(); expect(runner.output.busy).toBe("renew");
    if (outcome === "success") first.resolve(renewed(fixture, renew.mock.calls[0][2])); else first.reject(Error("api_unreachable"));
    await runner.flush(); expect(runner.output.busy).toBe("renew"); expect(runner.output.error).toBeNull(); expect(runner.output.renewal).toBeNull();
    next.resolve(renewed(fixture, renew.mock.calls[1][2])); await runner.flush();
    expect(runner.output.busy).toBeNull(); expect(runner.output.renewal).not.toBeNull();
  });
  it.each(["success", "error"] as const)("invalidates old renewal %s after options change without clearing a newer read", async outcome => {
    const fixture = legacy(); mockSource(fixture); const response = deferred<AugmentationRenewalResponse>();
    const renew = vi.spyOn(api, "renewAugmentation").mockReturnValue(response.promise);
    const runner = new Runner(() => useBayesianAugmentation({ study: fixture.study, disabled: false, onConfirmed: vi.fn() }));
    await open(runner, fixture.selection.selection_id); runner.act(() => runner.output.renew()); await runner.flush();
    runner.act(() => runner.output.updateDraft("batchSize", "1")); expect(runner.output.selection).toBeNull();
    const read = deferred<typeof fixture.selection>(); vi.mocked(api.fetchAugmentation).mockReturnValueOnce(read.promise);
    runner.act(() => runner.output.openSelection(fixture.selection.selection_id)); expect(runner.output.busy).toBe("read");
    if (outcome === "success") response.resolve(renewed(fixture, renew.mock.calls[0][2])); else response.reject(Error("api_unreachable"));
    await runner.flush(); expect(runner.output.busy).toBe("read"); expect(runner.output.error).toBeNull(); expect(runner.output.canRetry).toBe(false);
    read.resolve(fixture.selection); await runner.flush(); expect(runner.output.busy).toBeNull(); expect(runner.output.needsRenewal).toBe(true);
  });
  it("restores persisted lineage only for the active read/source", async () => {
    const fixture = legacy(); mockSource(fixture);
    const value = renewed(fixture, { request_id: "b1111111-1111-4111-8111-111111111111", expected_config_sha256: fixture.selection.config_sha256, expected_result_sha256: fixture.selection.result_sha256 });
    vi.mocked(api.fetchAugmentation).mockResolvedValue(value.selection);
    vi.mocked(api.fetchAugmentationRenewal).mockResolvedValue(value.lineage);
    let study = fixture.study;
    const runner = new Runner(() => useBayesianAugmentation({ study, disabled: false, onConfirmed: vi.fn() }));
    await open(runner, value.selection.selection_id); expect(runner.output.renewal).toEqual(value.lineage);
    const delayed = deferred<typeof value.lineage | null>(); vi.mocked(api.fetchAugmentationRenewal).mockReturnValueOnce(delayed.promise);
    runner.act(() => runner.output.openSelection(value.selection.selection_id)); await runner.flush(); expect(runner.output.busy).toBe("read");
    runner.act(() => { study = { ...fixture.study, observation_history: { ...fixture.study.observation_history, observation_history_sha256: "f".repeat(64) } }; }); await runner.flush();
    delayed.resolve(value.lineage); await runner.flush(); expect(runner.output.selection).toBeNull(); expect(runner.output.renewal).toBeNull(); expect(runner.output.busy).toBeNull();
  });
});
