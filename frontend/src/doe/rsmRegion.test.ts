import { describe, expect, it } from "vitest";
import type { ResponseSurfaceDesignResponse } from "../api";
import { isRsmExecutable, isRsmOnLattice, resolveRsmRegion } from "./rsmRegion";

function design(kind: "ccc" | "cci" | "ccf"): ResponseSurfaceDesignResponse {
  const alpha = kind === "ccf" ? 1 : 2;
  const scale = kind === "cci" ? 2.5 : 5;
  return { factors: [{ name: "X", low: 10, high: 20, domain_kind: "continuous", step: null }],
    options: { alpha }, coding: { X: { center: 15, scale, alpha,
      input_bounds_role: kind === "ccc" ? "factorial" : kind === "cci" ? "axial" : "factorial_and_axial",
      factorial_low: 15 - scale, factorial_high: 15 + scale,
      axial_low: 15 - alpha * scale, axial_high: 15 + alpha * scale } },
    runs: [{ factor_levels: { X: 15 - alpha * scale } }, { factor_levels: { X: 15 + alpha * scale } }],
  } as unknown as ResponseSurfaceDesignResponse;
}

describe("saved RSM region presentation", () => {
  it.each([ ["ccc", 5, 25, 5], ["cci", 10, 20, 2.5], ["ccf", 10, 20, 5] ] as const)(
    "%s preserves input and coding while resolving axial bounds", (kind, low, high, scale) => {
      const saved = design(kind); const before = JSON.stringify(saved);
      const region = resolveRsmRegion(saved)[0];
      expect(region.input).toEqual({ lower: 10, upper: 20 });
      expect(region.effective).toEqual({ lower: low, upper: high });
      expect(region.scale).toBe(scale);
      expect(resolveRsmRegion(saved, "factorial_cube")[0].scale).toBe(scale);
      expect(JSON.stringify(saved)).toBe(before);
    });
  it("keeps legacy omitted bounds and custom bounds distinct", () => {
    const saved = design("ccc");
    expect(resolveRsmRegion(saved, "legacy_input_bounds_v1")[0].effective).toEqual({ lower: 10, upper: 20 });
    expect(resolveRsmRegion(saved, "custom", { X: { lower: 12, upper: 24 } })[0].effective.upper).toBe(24);
    expect(() => resolveRsmRegion(saved, "custom", { X: { lower: 4, upper: 24 } })).toThrow();
    expect(isRsmExecutable(23, resolveRsmRegion(saved)[0])).toBe(true);
    expect(isRsmExecutable(23, resolveRsmRegion(saved, "factorial_cube")[0])).toBe(false);
  });
  it("does not move the discrete lattice origin to a custom lower bound", () => {
    const region = { ...resolveRsmRegion(design("ccc"))[0], step: 5 };
    expect(region.anchor).toBe(10);
    expect(isRsmExecutable(5, region)).toBe(true);
    expect(isRsmExecutable(6, region)).toBe(false);
  });
  it("rejects off-lattice custom bounds before requesting a view", () => {
    const saved = design("ccc");
    saved.factors[0] = { ...saved.factors[0], domain_kind: "discrete_numeric", step: 2.5 };
    expect(resolveRsmRegion(saved)[0].anchor).toBe(10);
    expect(resolveRsmRegion(saved, "custom", { X: { lower: 7.5, upper: 22.5 } })[0].effective)
      .toEqual({ lower: 7.5, upper: 22.5 });
    expect(() => resolveRsmRegion(saved, "custom", { X: { lower: 6, upper: 22.5 } }))
      .toThrow("doe_rsm_region_bounds_not_executable");
  });
  it.each([
    [0.3, 0.1, 0.1, true], [-0.3, 0.1, 0.1, true],
    [10.00000000005, 10, 1, false], [1.000000000001, 0, 1, true],
    [1.000000000002, 0, 1, false], [1e12 + 0.1, 1e12, 0.1, true],
    [3e-300, 1e-300, 1e-300, true], [2.5e-300, 1e-300, 1e-300, false],
    [10, 10, 0, false], [10, 10, -1, false], [Infinity, 10, 1, false],
  ])("checks decimal lattice %s from %s with step %s", (value, anchor, step, expected) => {
    expect(isRsmOnLattice(value, anchor, step)).toBe(expected);
  });
});
