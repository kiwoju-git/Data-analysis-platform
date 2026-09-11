import type { FactorialDesignResponse, GeneralFactorialDesignResponse } from "../api/types/doe";

export type FactorialViewDesign = FactorialDesignResponse | GeneralFactorialDesignResponse;
export function isGeneralFactorial(design: FactorialViewDesign): design is GeneralFactorialDesignResponse {
  return design.method_id === "doe.general_factorial_design";
}
export interface FactorialViewFactor {
  name: string; unit: string | null; numeric: boolean;
  levels: Array<{ code: number; actual: number | string }>;
}

export function factorialViewFactors(design: FactorialViewDesign): FactorialViewFactor[] {
  if (isGeneralFactorial(design)) {
    return design.factors.map((factor) => ({ name: factor.name, unit: factor.unit ?? null, numeric: false,
      levels: factor.levels.map((actual, code) => ({ code, actual })) }));
  }
  return design.factors.map((factor) => ({ name: factor.name, unit: factor.unit ?? null, numeric: factor.factor_kind !== "categorical",
    levels: factor.factor_kind === "categorical" ? [{ code: -1, actual: factor.low_label }, { code: 1, actual: factor.high_label }]
      : [{ code: -1, actual: factor.low }, { code: 1, actual: factor.high }] }));
}
