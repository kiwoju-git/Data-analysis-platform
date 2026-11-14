import { describe, expect, it } from "vitest";
import { executeProfileMatrix } from "./boProfileMatrix";

describe("whole-factor profile execution", () => {
  it("snapshots input, chunks sequentially and publishes only complete axes", async () => {
    const points = Array.from({ length: 101 }, (_, x) => ({ x }));
    const calls: number[] = []; let active = 0;
    const result = await executeProfileMatrix([{ factorId: "x", points }], async (chunk, budget) => {
      expect(++active).toBe(1); expect(budget).toBeLessThanOrEqual(60000);
      calls.push(chunk.length); await Promise.resolve(); active--; return chunk.map(p => ({ value: p.x }));
    }, () => true);
    expect(calls).toEqual([100, 1]); expect(result[0].rows).toHaveLength(101);
    expect(points[0]).toEqual({ x: 0 });
  });
  it("rejects later failure and never returns partial axes", async () => {
    let calls = 0;
    await expect(executeProfileMatrix([{ factorId: "a", points: [{ x: 1 }] }, { factorId: "b", points: [{ x: 2 }] }], async () => {
      await Promise.resolve();
      if (++calls === 2) throw Error("invalid_source"); return [1];
    }, () => true)).rejects.toThrow("invalid_source");
  });
  it("rejects stale delayed completion and elapsed total budget", async () => {
    let current = true;
    await expect(executeProfileMatrix([{ factorId: "a", points: [{ x: 1 }] }], () => { current = false; return Promise.resolve([1]); }, () => current)).rejects.toThrow("bayesian_profile_stale");
    let time = 0;
    await expect(executeProfileMatrix([{ factorId: "a", points: [{ x: 1 }] }], () => { time = 120001; return Promise.resolve([1]); }, () => true, () => time)).rejects.toThrow("bayesian_profile_budget");
  });
  it("rejects empty axes, point/axis overflow and response length mismatch", async () => {
    const evaluate = () => Promise.resolve([1]);
    for (const axes of [[], [{ factorId: "a", points: [] }], Array.from({ length: 11 }, (_, i) => ({ factorId: String(i), points: [{ x: 1 }] })), [{ factorId: "a", points: Array.from({ length: 1001 }, () => ({ x: 1 })) }]]) {
      await expect(executeProfileMatrix(axes, evaluate, () => true)).rejects.toThrow("bayesian_profile_budget");
    }
    await expect(executeProfileMatrix([{ factorId: "a", points: [{ x: 1 }, { x: 2 }] }], evaluate, () => true)).rejects.toThrow("bayesian_profile_response_mismatch");
  });
  it("passes only the remaining total budget to each subsequent request", async () => {
    let time = 0;
    const budgets: number[] = [];
    await executeProfileMatrix(["a", "b", "c"].map(factorId => ({ factorId, points: [{ x: 1 }] })), (_points, budget) => {
      budgets.push(budget); time = budgets.length === 1 ? 70000 : 119999; return Promise.resolve([1]);
    }, () => true, () => time);
    expect(budgets).toEqual([60000, 50000, 1]);
  });
});
