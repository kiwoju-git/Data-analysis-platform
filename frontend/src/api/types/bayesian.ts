export interface BayesianFactorRequest {
  factor_id: string;
  name: string;
  low: number;
  high: number;
  unit?: string | null;
  domain_kind?: "continuous" | "discrete_numeric";
  step?: number | null;
  display_decimals?: number | null;
}

export interface BayesianObjectiveRequest {
  name: string;
  unit?: string | null;
  goal_type: "minimize" | "maximize" | "match_target";
  target_value?: number | null;
  target_tolerance?: number | null;
  direction?: "minimize" | "maximize" | null;
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
  initial_design_policy:
    | "latin_hypercube_random_cd_v1"
    | "sha256_counter_uniform_feasible_v1";
  predecessor_study_id?: string | null;
}

export interface BayesianFactorResponse extends BayesianFactorRequest {
  unit: string | null;
  domain_kind?: "continuous" | "discrete_numeric";
  step?: number | null;
  display_decimals?: number | null;
  level_count?: number | null;
  order: number;
  scaling_rule: "linear_0_1";
}

export interface BayesianObjectiveResponse extends BayesianObjectiveRequest {
  unit: string | null;
  target_value: number | null;
  target_tolerance: number | null;
  direction: "minimize" | "maximize" | null;
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
  policy:
    | "latin_hypercube_random_cd_v1"
    | "sha256_counter_uniform_feasible_v1";
  seed: number;
  requested_size: number;
  generated_size: number;
  attempt_limit?: number | null;
  attempts_consumed?: number | null;
  scramble?: boolean | null;
  strength?: number | null;
  optimization?: "random_cd" | null;
  centered_discrepancy?: number | null;
  minimum_pairwise_distance?: number | null;
  strata_valid?: boolean | null;
  continuous_strata_valid?: boolean | null;
  discrete_level_balance?: Record<string, number[]>;
  duplicate_count?: number;
  executable_point_count?: number | null;
  numpy_version?: string | null;
  scipy_version?: string | null;
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
  schema_version: 1 | 2;
  completed_trial_ids: string[];
  completed_trial_count: number;
  observation_history_sha256: string;
  previous_history_sha256: string | null;
  created_at: string;
}

export type BayesianStudyStatus = "active" | "completed" | "abandoned";

export type BayesianStudyCloseReason =
  | "objective_satisfied"
  | "budget_reached"
  | "confirmation_complete"
  | "unsafe_or_infeasible"
  | "resources_unavailable"
  | "study_cancelled";

export interface BayesianStudyLifecycleEventResponse {
  schema_version: 1;
  lifecycle_event_id: string;
  study_id: string;
  study_version_id: string;
  lifecycle_revision: 1;
  previous_status: "active";
  resulting_status: "completed" | "abandoned";
  reason_code: BayesianStudyCloseReason;
  note: string | null;
  request_id: string;
  final_history_revision_id: string;
  final_observation_history_sha256: string;
  final_trial_count: number;
  final_completed_trial_count: number;
  final_abandoned_trial_count: number;
  latest_recommendation_id: string | null;
  latest_recommendation_batch_id: string | null;
  definition_sha256: string;
  event_sha256: string;
  closed_at: string;
  created_at: string;
  app_version: string;
  build_commit: string | null;
}

export interface BayesianStudyCloseRequest {
  target_status: "completed" | "abandoned";
  reason_code: BayesianStudyCloseReason;
  note?: string | null;
  request_id: string;
  expected_study_version_id: string;
  expected_history_revision_id: string;
  expected_observation_history_sha256: string;
}

export interface BayesianTrialAbandonRequest {
  expected_history_revision_id?: string | null;
  intent?: "continue_study" | "close_study";
}

export interface BayesianStudyResponse {
  study_id: string;
  study_version_id: string;
  version_number: number;
  study_schema_version: 1 | 2 | 3;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  name: string;
  status: BayesianStudyStatus;
  predecessor_study_id: string | null;
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
  recommendation_minimum_completed_observations: number;
  recommendation_hard_trial_limit: number;
  recommendation_blockers: Array<
    | "bayesian_optimization_history_incomplete"
    | "bayesian_optimization_pending_recommendation_exists"
    | "bayesian_optimization_budget_exhausted"
    | "bayesian_study_not_active"
  >;
  lifecycle_event: BayesianStudyLifecycleEventResponse | null;
}

export interface BayesianStudyCloseResponse {
  study: BayesianStudyResponse;
  lifecycle_event: BayesianStudyLifecycleEventResponse;
}

export interface BayesianStudyDeletionCounts {
  study_count: 1;
  study_version_count: number;
  trial_count: number;
  history_revision_count: number;
  history_head_count: number;
  recommendation_count: number;
  recommendation_batch_count: number;
  recommendation_batch_item_count: number;
  lifecycle_event_count: number;
  metadata_record_count: number;
  file_count: 0;
  file_bytes: 0;
}

export interface BayesianStudyDeletionPreflightResponse {
  preflight_schema_version: 1;
  study_id: string;
  study_version_id: string;
  status: BayesianStudyStatus;
  eligible: boolean;
  blockers: Array<
    "bayesian_study_deletion_active" | "bayesian_study_deletion_referenced"
  >;
  successor_study_count: number;
  counts: BayesianStudyDeletionCounts;
  deletion_manifest_sha256: string;
}

export interface BayesianStudyDeleteRequest {
  confirmation_study_id: string;
  expected_deletion_manifest_sha256: string;
}

export interface BayesianStudyDeleteResponse {
  deletion_schema_version: 1;
  study_id: string;
  deletion_manifest_sha256: string;
  deleted_at: string;
  deleted_counts: BayesianStudyDeletionCounts;
}

export interface BayesianStudySummaryResponse {
  study_id: string;
  study_version_id: string;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  name: string;
  status: BayesianStudyStatus;
  predecessor_study_id: string | null;
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

export interface BayesianObservationBatchCreateRequest {
  request_id: string;
  expected_study_version_id: string;
  expected_history_revision_id: string;
  expected_observation_history_sha256: string;
  observations: Array<{ trial_id: string; objective_value: number }>;
}

export interface BayesianObservationBatchCreateResponse {
  batch_schema_version: 1;
  study: BayesianStudyResponse;
  completed_trial_ids: string[];
  completed_trial_count: number;
  observation_history: BayesianHistoryRevisionResponse;
  request_id: string;
  created_at: string;
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

export interface BayesianRecommendationCurrentTrialResponse {
  trial_id: string;
  state: "pending" | "completed" | "abandoned";
  objective_value: number | null;
  closed_at: string | null;
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
  current_trial?: BayesianRecommendationCurrentTrialResponse | null;
  is_latest?: boolean;
  requested_total_trial_budget?: number | null;
}

export interface BayesianRecommendationListResponse {
  study_id: string;
  study_version_id: string;
  total: number;
  offset: number;
  limit: number;
  items: BayesianRecommendationResponse[];
}

export interface BayesianLatestRecommendationResponse {
  study_id: string;
  study_version_id: string;
  item: BayesianRecommendationResponse | null;
}

export type BayesianExecutionMode = "sequential_single" | "parallel_batch";
export type BayesianExplorationProfile =
  | "exploitation"
  | "balanced"
  | "exploration"
  | "custom";
export type BayesianAcquisitionKind =
  | "expected_improvement"
  | "expected_target_improvement";

export interface BayesianBatchAcquisitionRequest {
  kind: BayesianAcquisitionKind;
  exploration_profile: BayesianExplorationProfile;
  xi_standardized: number;
}

export interface BayesianBatchSearchRequest {
  random_seed: number;
  candidate_count_per_step: number;
  local_start_count_per_step: number;
  max_iterations_per_step: number;
  max_evaluations_total: number;
  model_max_iterations: number;
  model_max_evaluations: number;
  hyperparameter_restart_count: number;
  time_budget_ms: number;
  jitter: number;
  duplicate_tolerance: number;
  total_trial_budget: number;
  batch_policy: "greedy_posterior_mean_fantasy_ei_v1";
}

export interface BayesianRecommendationBatchCreateRequest {
  expected_history_revision_id: string;
  execution_mode: BayesianExecutionMode;
  batch_size: number;
  acquisition: BayesianBatchAcquisitionRequest;
  search: BayesianBatchSearchRequest;
}

export interface BayesianAcquisitionBreakdownResponse {
  xi_standardized: number;
  standardized_margin: number;
  z_value: number | null;
  normal_cdf: number | null;
  normal_density: number | null;
  mean_improvement_term: number;
  uncertainty_term: number;
}

export interface BayesianRecommendationBatchItemResponse {
  item_id: string;
  batch_id: string;
  rank: number;
  trial: BayesianTrialResponse;
  current_trial: BayesianRecommendationCurrentTrialResponse;
  actual_coordinates: Record<string, number>;
  normalized_coordinates: Record<string, number>;
  predicted_objective_mean: number;
  posterior_standard_deviation: number;
  incumbent_objective: number;
  acquisition_kind: BayesianAcquisitionKind;
  acquisition_value: number;
  predicted_improvement_margin: number;
  probability_of_improvement: number | null;
  target_value: number | null;
  predicted_target_distance: number | null;
  incumbent_target_distance: number | null;
  nearest_completed_distance: number | null;
  nearest_existing_trial_distance: number | null;
  nearest_earlier_batch_item_distance: number | null;
  constraint_evaluations: BayesianConstraintEvaluationResponse[];
  fantasy_step: number;
  conditioned_on_item_ids: string[];
  reason_code:
    | "predicted_improvement_driven"
    | "uncertainty_driven"
    | "balanced_improvement_uncertainty"
    | "target_distance_reduction"
    | "batch_diversity_adjusted";
  acquisition_breakdown: BayesianAcquisitionBreakdownResponse;
}

export interface BayesianBatchSharedModelResponse {
  schema_version: 2;
  kernel_policy: "constant_times_matern_5_2_ard_v1";
  fitted_kernel: string;
  constant_value: number;
  length_scales: number[];
  log_marginal_likelihood: number;
  objective_goal_type: "minimize" | "maximize" | "match_target";
  objective_normalization_mean: number;
  objective_normalization_scale: number;
  target_value_standardized: number | null;
  jitter: number;
  completed_observation_count: number;
  hyperparameter_restart_count: number;
  model_evaluations: number;
  fit_elapsed_ms: number;
  package_versions: Record<string, string>;
}

export interface BayesianRecommendationBatchResponse {
  batch_id: string;
  study_id: string;
  study_version_id: string;
  source_history_revision_id: string;
  source_observation_history_sha256: string;
  definition_sha256: string;
  method_id: "doe.bayesian_optimization";
  method_version: string;
  config_schema_version: 1;
  result_schema_version: 1;
  model_schema_version: 2;
  item_schema_version: 1;
  batch_policy: "greedy_posterior_mean_fantasy_ei_v1";
  execution_mode: BayesianExecutionMode;
  batch_size: number;
  acquisition: BayesianBatchAcquisitionRequest;
  shared_model: BayesianBatchSharedModelResponse;
  search_budget: {
    candidate_count_per_step: number;
    local_start_count_per_step: number;
    max_evaluations_total: number;
    evaluations_consumed: number;
    model_max_iterations: number;
    model_max_evaluations: number;
    model_evaluations_consumed: number;
    time_budget_ms: number;
    elapsed_ms: number;
    termination_reason: "search_completed";
  };
  items: BayesianRecommendationBatchItemResponse[];
  warnings: string[];
  limitations: string[];
  config_sha256: string;
  result_sha256: string;
  provenance: {
    study_id: string;
    study_version_id: string;
    batch_id: string;
    source_history_revision_id: string;
    source_observation_history_sha256: string;
    definition_sha256: string;
    method_id: "doe.bayesian_optimization";
    method_version: string;
    config_schema_version: 1;
    result_schema_version: 1;
    model_schema_version: 2;
    item_schema_version: 1;
    app_version: string;
    python_version: string;
    platform: string;
    build_commit: string | null;
    package_versions: Record<string, string>;
    created_at: string;
  };
  created_at: string;
  is_latest: boolean;
  batch_state:
    | "pending"
    | "partially_completed"
    | "completed"
    | "abandoned"
    | "closed_mixed";
  requested_total_trial_budget: number;
}

export interface BayesianLatestRecommendationBatchResponse {
  study_id: string;
  study_version_id: string;
  item: BayesianRecommendationBatchResponse | null;
}
