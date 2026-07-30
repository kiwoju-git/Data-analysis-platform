import type {
  BayesianBatchSearchRequest,
  BayesianRecommendationBatchItemResponse,
  BayesianRecommendationCreateRequest,
} from "../../api";

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

export const defaultBayesianBatchSearch: BayesianBatchSearchRequest = {
  random_seed: 20260715,
  candidate_count_per_step: 256,
  local_start_count_per_step: 4,
  max_iterations_per_step: 100,
  max_evaluations_total: 32768,
  model_max_iterations: 50,
  model_max_evaluations: 200,
  hyperparameter_restart_count: 0,
  time_budget_ms: 60000,
  jitter: 1e-8,
  duplicate_tolerance: 1e-6,
  total_trial_budget: 50,
  batch_policy: "greedy_posterior_mean_fantasy_ei_v1",
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

export function batchReasonText(item: BayesianRecommendationBatchItemResponse) {
  const rank = `후보 ${item.rank}`;
  if (item.reason_code === "target_distance_reduction") {
    return `${rank}은 예측 평균이 목표값에 더 가까워질 가능성과 예측 불확실성을 함께 고려해 선택되었습니다.`;
  }
  if (item.reason_code === "uncertainty_driven") {
    return `${rank}은 예측 평균 자체보다 아직 관측이 적은 영역의 불확실성 때문에 탐색 후보로 선택되었습니다.`;
  }
  if (item.reason_code === "batch_diversity_adjusted") {
    return `${rank}은 앞선 batch 후보를 실제 관측이 아닌 posterior-mean fantasy로 조건화한 뒤에도 acquisition 값이 높고, 앞선 조건과의 중복을 피하도록 선택되었습니다.`;
  }
  if (item.reason_code === "predicted_improvement_driven") {
    return `${rank}은 현재 최선값보다 나은 예측 평균을 중심으로 선택되었습니다.`;
  }
  return `${rank}은 예측 평균의 개선 가능성과 posterior 불확실성을 함께 고려해 선택되었습니다.`;
}

export function bayesianErrorCode(caught: unknown) {
  return caught instanceof Error ? caught.message : "bayesian_request_failed";
}

export function validBayesianId(value: string | null): string | null {
  return value !== null && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value) ? value : null;
}
