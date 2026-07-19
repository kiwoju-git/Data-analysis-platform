import type { BayesianRecommendationCreateRequest } from "../../api";

export const BAYESIAN_CATALOG_PAGE_SIZE = 20;

export const defaultBayesianSearch: BayesianRecommendationCreateRequest["search"] = {
  random_seed: 20260715,
  xi: 0.01,
  candidate_count: 256,
  local_start_count: 4,
  max_iterations: 100,
  max_evaluations: 4096,
  model_max_iterations: 50,
  model_max_evaluations: 200,
  hyperparameter_restart_count: 0,
  time_budget_ms: 15_000,
  jitter: 1e-8,
  duplicate_tolerance: 1e-6,
  total_trial_budget: 50,
};

export type PendingTrialTransition = {
  trialId: string;
  action: "complete" | "abandon";
};

export type StudyCloseTarget = "completed" | "abandoned";

export function constraintText(constraint: {
  terms: Array<{ factor_id: string; coefficient: number }>;
  relation: "less_than_or_equal" | "greater_than_or_equal";
  bound: number;
}) {
  const lhs = constraint.terms
    .map((term) => `${formatNumber(term.coefficient)}×${term.factor_id}`)
    .join(" + ");
  return `${lhs} ${constraint.relation === "less_than_or_equal" ? "≤" : "≥"} ${formatNumber(constraint.bound)}`;
}

export function coordinateText(coordinates: Record<string, number>) {
  return Object.entries(coordinates)
    .map(([factorId, value]) => `${factorId}=${formatNumber(value)}`)
    .join(", ");
}

export function formatNumber(value: number) {
  return Number.isFinite(value) ? value.toPrecision(6) : "-";
}

export function bayesianErrorCode(caught: unknown) {
  return caught instanceof Error ? caught.message : "bayesian_request_failed";
}

export function validBayesianId(value: string | null): string | null {
  return value !== null && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value) ? value : null;
}
