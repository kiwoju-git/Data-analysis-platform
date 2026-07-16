export interface BayesianFactorRequest {
  factor_id: string;
  name: string;
  low: number;
  high: number;
  unit?: string | null;
}

export interface BayesianObjectiveRequest {
  name: string;
  unit?: string | null;
  direction: "minimize" | "maximize";
  observation_policy: "manual_single_observation";
}

export interface BayesianConstraintTermRequest {
  factor_id: string;
  coefficient: number;
}

export interface BayesianLinearConstraintRequest {
  constraint_id: string;
  name: string;
  terms: BayesianConstraintTermRequest[];
  relation: "less_than_or_equal" | "greater_than_or_equal";
  bound: number;
}

export interface BayesianStudyCreateRequest {
  name: string;
  factors: BayesianFactorRequest[];
  objective: BayesianObjectiveRequest;
  constraints: BayesianLinearConstraintRequest[];
  initial_design_seed: number;
  initial_design_size: number;
}

export interface BayesianFactorResponse extends BayesianFactorRequest {
  unit: string | null;
  order: number;
  scaling_rule: "linear_0_1";
}

export interface BayesianObjectiveResponse extends BayesianObjectiveRequest {
  unit: string | null;
}

export type BayesianConstraintTermResponse = BayesianConstraintTermRequest;

export interface BayesianLinearConstraintResponse {
  constraint_id: string;
  name: string;
  terms: BayesianConstraintTermResponse[];
  relation: "less_than_or_equal" | "greater_than_or_equal";
  bound: number;
}

export interface BayesianInitialDesignResponse {
  policy: "sha256_counter_uniform_feasible_v1";
  seed: number;
  requested_size: number;
  generated_size: number;
  attempt_limit: number;
  attempts_consumed: number;
}

export interface BayesianTrialResponse {
  trial_id: string;
  study_version_id: string;
  trial_number: number;
  origin: "initial_design" | "recommendation";
  state: "pending" | "completed" | "abandoned";
  actual_coordinates: Record<string, number>;
  normalized_coordinates: Record<string, number>;
  coordinates_sha256: string;
  objective_value: number | null;
  created_at: string;
  closed_at: string | null;
}

export interface BayesianHistoryRevisionResponse {
  history_revision_id: string;
  study_version_id: string;
  revision_number: number;
  schema_version: 1;
  completed_trial_ids: string[];
  completed_trial_count: number;
  observation_history_sha256: string;
  previous_history_sha256: string | null;
  created_at: string;
}

export interface BayesianStudyResponse {
  study_id: string;
  study_version_id: string;
  version_number: number;
  study_schema_version: 1;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  name: string;
  status: "active" | "completed" | "abandoned";
  created_at: string;
  updated_at: string;
  app_version: string;
  definition_sha256: string;
  factors: BayesianFactorResponse[];
  objective: BayesianObjectiveResponse;
  constraints: BayesianLinearConstraintResponse[];
  initial_design: BayesianInitialDesignResponse;
  trial_count: number;
  pending_trial_count: number;
  completed_trial_count: number;
  abandoned_trial_count: number;
  observation_history: BayesianHistoryRevisionResponse;
  trials: BayesianTrialResponse[];
  surrogate_available: boolean;
  recommendation_available: boolean;
}

export interface BayesianStudySummaryResponse {
  study_id: string;
  study_version_id: string;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  name: string;
  status: "active" | "completed" | "abandoned";
  updated_at: string;
  definition_sha256: string;
  pending_trial_count: number;
  completed_trial_count: number;
  abandoned_trial_count: number;
  observation_history_sha256: string;
}

export interface BayesianStudyListResponse {
  total: number;
  offset: number;
  limit: number;
  items: BayesianStudySummaryResponse[];
}

export interface BayesianTrialListResponse {
  study_id: string;
  study_version_id: string;
  total: number;
  offset: number;
  limit: number;
  items: BayesianTrialResponse[];
}

export interface BayesianObservationCreateRequest {
  objective_value: number;
  expected_history_revision_id: string;
}

export interface BayesianTrialTransitionResponse {
  study_id: string;
  trial: BayesianTrialResponse;
  observation_history: BayesianHistoryRevisionResponse;
}

export interface BayesianHistoryListResponse {
  study_id: string;
  study_version_id: string;
  total: number;
  offset: number;
  limit: number;
  items: BayesianHistoryRevisionResponse[];
}

export interface BayesianRecommendationSearchRequest {
  random_seed: number;
  xi: number;
  candidate_count: number;
  local_start_count: number;
  max_iterations: number;
  max_evaluations: number;
  model_max_iterations: number;
  model_max_evaluations: number;
  hyperparameter_restart_count: number;
  time_budget_ms: number;
  jitter: number;
  duplicate_tolerance: number;
  total_trial_budget: number;
}

export interface BayesianRecommendationCreateRequest {
  expected_history_revision_id: string;
  search: BayesianRecommendationSearchRequest;
}

export interface BayesianConstraintEvaluationResponse {
  constraint_id: string;
  name: string;
  relation: "less_than_or_equal" | "greater_than_or_equal";
  lhs: number;
  bound: number;
  slack: number;
  satisfied: boolean;
}

export interface BayesianSurrogateModelResponse {
  schema_version: 1;
  kernel_policy: "constant_times_matern_5_2_ard_v1";
  fitted_kernel: string;
  constant_value: number;
  length_scales: number[];
  log_marginal_likelihood: number;
  objective_direction_multiplier: number;
  objective_normalization_mean: number;
  objective_normalization_scale: number;
  jitter: number;
  completed_observation_count: number;
  hyperparameter_restart_count: number;
  model_evaluations: number;
  fit_elapsed_ms: number;
  package_versions: Record<string, string>;
}

export interface BayesianRecommendationBudgetResponse {
  candidate_count_requested: number;
  feasible_candidate_count: number;
  local_start_count_requested: number;
  local_starts_attempted: number;
  local_success_count: number;
  local_iterations: number;
  max_evaluations: number;
  evaluations_consumed: number;
  model_max_iterations: number;
  model_max_evaluations: number;
  model_evaluations_consumed: number;
  time_budget_ms: number;
  elapsed_ms: number;
  termination_reason: "search_completed" | "evaluation_budget" | "time_budget";
}

export interface BayesianRecommendationResult {
  schema_version: 1;
  recommended_actual_coordinates: Record<string, number>;
  recommended_normalized_coordinates: Record<string, number>;
  predicted_objective_mean: number;
  posterior_standard_deviation: number;
  expected_improvement: number;
  incumbent_objective: number;
  objective_direction: "minimize" | "maximize";
  constraint_evaluations: BayesianConstraintEvaluationResponse[];
  model: BayesianSurrogateModelResponse;
  budget: BayesianRecommendationBudgetResponse;
  warnings: string[];
  limitations: string[];
}

export interface BayesianRecommendationProvenance {
  study_id: string;
  study_version_id: string;
  recommendation_id: string;
  recommendation_trial_id: string;
  source_history_revision_id: string;
  source_observation_history_sha256: string;
  definition_sha256: string;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  config_schema_version: 1;
  result_schema_version: 1;
  model_schema_version: 1;
  app_version: string;
  python_version: string;
  platform: string;
  build_commit: string | null;
  package_versions: Record<string, string>;
  created_at: string;
}

export interface BayesianRecommendationResponse {
  recommendation_id: string;
  study_id: string;
  study_version_id: string;
  source_history_revision_id: string;
  source_observation_history_sha256: string;
  definition_sha256: string;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  config_schema_version: 1;
  result_schema_version: 1;
  model_schema_version: 1;
  config_sha256: string;
  result_payload_sha256: string;
  created_at: string;
  trial: BayesianTrialResponse;
  result: BayesianRecommendationResult;
  provenance: BayesianRecommendationProvenance;
}

export interface BayesianRecommendationListResponse {
  study_id: string;
  study_version_id: string;
  total: number;
  offset: number;
  limit: number;
  items: BayesianRecommendationResponse[];
}
