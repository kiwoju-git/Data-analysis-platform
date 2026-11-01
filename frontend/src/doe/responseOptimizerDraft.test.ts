import { describe, expect, it } from "vitest";
import { optimizerBoundError, optimizerRequest, restoreOptimizerDraft, type OptimizerDraft } from "./responseOptimizerDraft";
import type { ResponseOptimizerResponse } from "../api";
import { formatExactNumericValue, formatInterval, formatMeasurement } from "../statisticalNumberFormat";

function fixture(): Parameters<typeof optimizerRequest>[0] {
  return {
    analysis: { analysis_id: "analysis" },
    design: { factors: [{ name: "X", low: -10, high: 10, unit: null }] },
    goal: "target", thresholds: { lower: "-2", target: "0", upper: "2" },
    lowerWeight: "1", upperWeight: "1", importance: "1", bounds: { X: { lower: "-10", upper: "10" } },
    linearEnabled: false, linearRelation: "less_than_or_equal", linearBound: "0", linearCoefficients: { X: "1" },
    randomSeed: "0", randomCandidates: "0", multiStarts: "1", maxIterations: "120", maxEvaluations: "5000", timeBudgetMs: "5000",
    acknowledgedSourceWarningCodes: [],
  } satisfies OptimizerDraft & Parameters<typeof optimizerRequest>[0];
}

describe("optimizer numeric draft boundary", () => {
  it("distinguishes field numeric, order and permitted-region errors without changing drafts", () => {
    const bounds = { lower: "", upper: "1" };
    expect(optimizerBoundError(bounds, { lower: -2, upper: 2 })).toBe("number");
    expect(bounds.lower).toBe("");
    expect(optimizerBoundError({ lower: "1", upper: "1" }, { lower: -2, upper: 2 })).toBe("order");
    expect(optimizerBoundError({ lower: "-3", upper: "1" }, { lower: -2, upper: 2 })).toBe("range");
    expect(optimizerBoundError({ lower: "-2e0", upper: "0" }, { lower: -2, upper: 2 })).toBeNull();
    expect(optimizerBoundError({ lower: "-1.5", upper: "0" }, { lower: -2, upper: 2 }, { anchor: -2, step: 1 })).toBe("lattice");
  });
  it.each(["", " ", "-", ".", "1e", "1e-", "10abc", "NaN", "Infinity"])("rejects incomplete target %j without coercion", (raw) => {
    const input = fixture(); input.thresholds.target = raw;
    expect(optimizerRequest(input)).toBe("response_optimizer_objective_invalid");
    expect(input.thresholds.target).toBe(raw);
  });
  it("accepts exact zero, signed decimals and scientific notation", () => {
    const input = fixture(); input.thresholds = { lower: "-1.25e-2", target: "-0", upper: "2E-2" };
    const request = optimizerRequest(input);
    expect(typeof request).toBe("object");
    if (typeof request === "string") throw new Error(request);
    expect(request.objectives[0]).toMatchObject({ lower: -0.0125, target: -0, upper: 0.02 });
  });
  it.each(["1.5", "10abc", "", "1e2", "-1"])("rejects non-integer budget %j", (raw) => {
    const input = fixture(); input.maxIterations = raw;
    expect(optimizerRequest(input)).toBe("response_optimizer_search_budget_invalid");
  });
  it("rejects empty bounds and linear coefficients", () => {
    const input = fixture(); input.bounds.X.lower = "";
    expect(optimizerRequest(input)).toBe("response_optimizer_factor_bound_invalid");
    input.bounds.X.lower = "-10"; input.linearEnabled = true; input.linearCoefficients.X = " ";
    expect(optimizerRequest(input)).toBe("response_optimizer_linear_constraint_invalid");
  });
  it.each(["maximize", "minimize", "target", "range"] as const)("uses only applicable %s thresholds", (goal) => {
    const input = { ...fixture(), goal };
    if (goal === "maximize") input.thresholds.upper = "invalid-unused";
    if (goal === "minimize") input.thresholds.lower = "invalid-unused";
    if (goal === "range") input.thresholds.target = "invalid-unused";
    const result = optimizerRequest(input);
    expect(typeof result).toBe("object");
    if (typeof result === "string") throw new Error(result);
    expect(result.objectives[0].upper).toBe(goal === "maximize" ? null : 2);
    expect(result.objectives[0].lower).toBe(goal === "minimize" ? null : -2);
    expect(result.objectives[0].target).toBe(goal === "range" ? null : 0);
  });
  it("rejects invalid threshold order before any request", () => {
    const input = fixture(); input.thresholds.target = "2";
    expect(optimizerRequest(input)).toBe("response_optimizer_objective_thresholds_invalid");
  });

  it("preserves all saved constraints and their names on restore/rerun", () => {
    const request = optimizerRequest(fixture());
    if (typeof request === "string") throw new Error(request);
    const constraints = [
      { name: "first", coefficients: { X: 1 }, relation: "less_than_or_equal" as const, bound: 8 },
      { name: "second", coefficients: { X: -1 }, relation: "less_than_or_equal" as const, bound: 7 },
    ];
    const saved = { result: { objectives: request.objectives, search: request.search,
      factor_region: { search_bounds: request.factor_bounds, design_bounds: [{ factor_name: "X" }], linear_constraints: constraints },
    } } as unknown as ResponseOptimizerResponse;
    const restored = restoreOptimizerDraft(saved);
    const rerun = optimizerRequest({ ...fixture(), ...restored });
    expect(typeof rerun).toBe("object");
    if (typeof rerun === "string") throw new Error(rerun);
    expect(rerun.linear_constraints).toEqual(constraints);
    expect(rerun.linear_constraints[1].coefficients).not.toBe(constraints[1].coefficients);
    expect(restored.regionMode).toBe("legacy_input_bounds_v1");
  });
});

describe("RSM/optimizer semantic display", () => {
  it.each(["ko", "en"] as const)("retains integer/exponent zeros in %s", (locale) => {
    for (const value of [0, -0, 10, 100000, 1000000, 1e-10, 1e10]) {
      const text = formatMeasurement(value, locale);
      expect(Number(text.replace(/,/g, ""))).toBe(value === 0 ? 0 : value);
    }
    expect(formatInterval({ lower: 1000.000001, upper: 1000.000002 }, locale)).toContain("000001");
    expect(formatExactNumericValue(1e-10)).toBe("1e-10");
  });
});
