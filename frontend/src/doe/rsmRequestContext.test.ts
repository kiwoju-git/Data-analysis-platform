import { describe, expect, it } from "vitest";
import { createRsmRequestContext } from "./rsmRequestContext";

describe("RSM source and request lanes", () => {
  it("rejects all old success/error/finally callbacks after edits, including A-B-A", () => {
    const guard = createRsmRequestContext();
    const request = guard.begin("save", { design_id: "A", response: [0, 2] });
    guard.invalidate();
    guard.invalidate();
    expect(guard.isCurrent(request)).toBe(false);
    expect(request.snapshot.response).toEqual([0, 2]);
  });

  it("separates history refresh from an analysis and plot changes from model ownership", () => {
    const guard = createRsmRequestContext();
    const analysis = guard.begin("analyze", { hash: "model" });
    const first = guard.begin("history", {});
    const second = guard.begin("history", {});
    const plot = guard.begin("plot", { x: "A", y: "B" });
    guard.invalidateLane("plot");
    expect(guard.isCurrent(analysis)).toBe(true);
    expect(guard.isCurrent(first)).toBe(false);
    expect(guard.isCurrent(second)).toBe(true);
    expect(guard.isCurrent(plot)).toBe(false);
  });

  it("does not let a previous request clear the latest loading state", async () => {
    const guard = createRsmRequestContext();
    const old = guard.begin("analyze", { options: 1 });
    let finish!: () => void;
    const deferred = new Promise<void>((resolve) => { finish = resolve; });
    let running = true;
    const pending = deferred.finally(() => { if (guard.isCurrent(old)) running = false; });
    const latest = guard.begin("analyze", { options: 2 });
    finish();
    await pending;
    expect(running).toBe(true);
    expect(guard.isCurrent(latest)).toBe(true);
  });
});
