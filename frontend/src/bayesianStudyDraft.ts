import type {
  BayesianFactorRequest,
  BayesianLinearConstraintRequest,
  BayesianRecommendationResponse,
  BayesianStudyCreateRequest,
  BayesianStudyResponse,
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

export function minimumBayesianInitialDesignSize(factorCount: number) {
  return Math.max(2, factorCount + 1);
}

export function bayesianRecommendationBudgetBlocker(
  trialCount: number,
  totalTrialBudget: number,
  hardTrialLimit: number,
): "bayesian_optimization_trial_budget_invalid" | "bayesian_optimization_budget_exhausted" | null {
  if (
    !Number.isInteger(totalTrialBudget) ||
    totalTrialBudget < 2 ||
    totalTrialBudget > hardTrialLimit
  ) {
    return "bayesian_optimization_trial_budget_invalid";
  }
  return trialCount >= Math.min(totalTrialBudget, hardTrialLimit)
    ? "bayesian_optimization_budget_exhausted"
    : null;
}

export function bayesianStudyCloseBlocker(
  study: Pick<
    BayesianStudyResponse,
    | "status"
    | "pending_trial_count"
    | "completed_trial_count"
    | "recommendation_minimum_completed_observations"
  >,
  target: "completed" | "abandoned",
  hasRecommendation: boolean,
) {
  if (study.status !== "active") return "bayesian_study_closed";
  if (study.pending_trial_count > 0) return "bayesian_study_close_pending_trials";
  if (
    target === "completed" &&
    (study.completed_trial_count < study.recommendation_minimum_completed_observations ||
      !hasRecommendation)
  ) {
    return "bayesian_study_completion_requirements_not_met";
  }
  return null;
}

export function bayesianRecommendationStatus(
  recommendation: BayesianRecommendationResponse,
): { label: string; description: string; className: string } {
  const currentState = recommendation.current_trial?.state ?? recommendation.trial.state;
  if (recommendation.is_latest === false) {
    return {
      label: "과거 추천",
      description: `과거 recommendation snapshot이며 현재 연결 trial 상태는 ${currentState}입니다.`,
      className: "",
    };
  }
  if (currentState === "completed") {
    return {
      label: "관측 완료",
      description: "추천 당시 예측과 이후 저장된 실제 관측값을 구분해 표시합니다.",
      className: "status-ready",
    };
  }
  if (currentState === "abandoned") {
    return {
      label: "중단됨",
      description: "중단된 추천이며 동일 조건은 향후 추천 후보에서 제외됩니다.",
      className: "status-error",
    };
  }
  return {
    label: "확인 대기",
    description: "관측값이 아닌 다음 확인 실험 후보입니다.",
    className: "status-warning",
  };
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
    Number.isInteger(size) &&
    size >= 1 &&
    size < minimumBayesianInitialDesignSize(parsedFactors.length)
  ) {
    return "bayesian_study_initial_design_too_small";
  }
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
    size < minimumBayesianInitialDesignSize(parsedFactors.length) ||
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
