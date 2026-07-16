import type {
  BayesianFactorRequest,
  BayesianLinearConstraintRequest,
  BayesianStudyCreateRequest,
} from "./api";

export interface FactorDraft {
  key: number;
  factorId: string;
  name: string;
  low: string;
  high: string;
  unit: string;
}

export interface ConstraintDraft {
  key: number;
  constraintId: string;
  name: string;
  coefficients: Record<number, string>;
  relation: "less_than_or_equal" | "greater_than_or_equal";
  bound: string;
}

export function buildBayesianStudyRequest(input: {
  studyName: string;
  factors: FactorDraft[];
  constraints: ConstraintDraft[];
  objectiveName: string;
  objectiveUnit: string;
  direction: "minimize" | "maximize";
  initialDesignSize: string;
  initialDesignSeed: string;
}): BayesianStudyCreateRequest | string {
  const factorIds = input.factors.map((factor) => factor.factorId.trim());
  const parsedFactors: BayesianFactorRequest[] = input.factors.map((factor) => ({
    factor_id: factor.factorId.trim(),
    name: factor.name.trim(),
    low: Number(factor.low),
    high: Number(factor.high),
    unit: factor.unit.trim() || null,
  }));
  const size = Number(input.initialDesignSize);
  const seed = Number(input.initialDesignSeed);
  const constraintIds = input.constraints.map((constraint) => constraint.constraintId.trim());
  const parsedConstraints: BayesianLinearConstraintRequest[] = input.constraints.map(
    (constraint) => ({
      constraint_id: constraint.constraintId.trim(),
      name: constraint.name.trim(),
      terms: input.factors
        .map((factor, index) => ({
          factor_id: parsedFactors[index].factor_id,
          coefficient: Number(constraint.coefficients[factor.key] || "0"),
        }))
        .filter((term) => term.coefficient !== 0),
      relation: constraint.relation,
      bound: Number(constraint.bound),
    }),
  );
  const invalidConstraintCoefficient = input.constraints.some((constraint) =>
    input.factors.some((factor) => {
      const value = constraint.coefficients[factor.key]?.trim() ?? "";
      return value.length > 0 && !Number.isFinite(Number(value));
    }),
  );
  if (
    input.studyName.trim().length === 0 ||
    input.objectiveName.trim().length === 0 ||
    new Set(factorIds).size !== factorIds.length ||
    parsedFactors.some(
      (factor) =>
        !/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(factor.factor_id) ||
        factor.name.length === 0 ||
        !Number.isFinite(factor.low) ||
        !Number.isFinite(factor.high) ||
        factor.low >= factor.high,
    ) ||
    !Number.isInteger(size) ||
    size < Math.max(2, parsedFactors.length + 1) ||
    size > 64 ||
    !Number.isInteger(seed) ||
    seed < 0 ||
    input.constraints.length > 16 ||
    new Set(constraintIds).size !== constraintIds.length ||
    invalidConstraintCoefficient ||
    parsedConstraints.some(
      (constraint) =>
        !/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(constraint.constraint_id) ||
        constraint.name.length === 0 ||
        constraint.terms.length === 0 ||
        constraint.terms.some((term) => !Number.isFinite(term.coefficient)) ||
        !Number.isFinite(constraint.bound),
    )
  ) {
    return "bayesian_study_input_invalid";
  }
  return {
    name: input.studyName.trim(),
    factors: parsedFactors,
    objective: {
      name: input.objectiveName.trim(),
      unit: input.objectiveUnit.trim() || null,
      direction: input.direction,
      observation_policy: "manual_single_observation",
    },
    constraints: parsedConstraints,
    initial_design_seed: seed,
    initial_design_size: size,
  };
}
