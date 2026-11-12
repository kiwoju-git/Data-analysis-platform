import type {
  BayesianBatchSearchRequest, BayesianConstraintEvaluationResponse,
  BayesianDesirabilityObjective, BayesianKernelBatchResponse, BayesianKernelKind,
  BayesianNoiseBatchResponse, BayesianObservationPolicyRequest,
  BayesianSurrogatePolicyRequest, BayesianTrialResponse,
} from "./bayesian";

export type DesirabilitySearch = Omit<BayesianBatchSearchRequest, "total_trial_budget" | "batch_policy">;
export interface DesirabilityResponseModelRequest {
  response_id: string;
  kernel: { kind: BayesianKernelKind };
  surrogate: BayesianSurrogatePolicyRequest;
}
export interface DesirabilityQ1ReviewRequest {
  schema_version: 4;
  batch_size: 1;
  expected_history_revision_id: string;
  expected_history_sha256: string;
  response_models: DesirabilityResponseModelRequest[];
  observation_policy: BayesianObservationPolicyRequest;
  xi_desirability: number;
  total_trial_budget: number;
  search: DesirabilitySearch;
}
export interface DesirabilityMoments {
  mean: number;
  second_moment: number;
  variance: number;
  estimated_absolute_error: number;
  normal_tail_bound: number;
  integration_evaluations: number;
}
type RawResponseModel = Omit<BayesianKernelBatchResponse["shared_model"], "objective_goal_type"> & {
  log_marginal_likelihood: number;
  training_group_counts: number[];
  fit_elapsed_ms: number;
  package_versions: Record<string, string>;
};
export interface DesirabilityQ1Calculation {
  schema_version: 4;
  batch_size: 1;
  policy: "independent_latent_desirability_beta_ei_v1";
  objective: Pick<BayesianDesirabilityObjective, "responses">;
  shared_model: {
    schema_version: 5;
    policy_version: 1;
    factor_ids: string[];
    response_ids: string[];
    response_models: Array<{ response_id: string; model: RawResponseModel; observation_view: BayesianNoiseBatchResponse["observation_view"] }>;
    normalized_importance: Array<{ response_id: string; weight: number }>;
    curve_policy: "derringer_suich_linear_v1";
    moment_policy: "independent_latent_gaussian_split_quadrature_v1";
    independence_assumption: true;
  };
  incumbent: {
    policy: "max_posterior_expected_desirability_at_observed_coordinates_v1";
    best_observed_desirability: number;
    best_observed_trial_id: string;
    latent_incumbent_value: number;
    latent_incumbent_trial_id: string;
    latent_incumbent_normalized_coordinates: Record<string, number>;
    observed_trial_desirabilities: Array<{ trial_id: string; value: number }>;
    training_posterior_desirabilities: Array<{ trial_id: string; moments: DesirabilityMoments }>;
  };
  observation_view: {
    mode: BayesianObservationPolicyRequest["mode"];
    raw_observation_count: number;
    unique_condition_count: number;
    unique_coordinate_count: number;
    effective_training_count: number;
    groups: Array<{ member_trial_ids: string[]; member_indices: number[]; canonical_actual_coordinates: Record<string, number>;
      canonical_level_indices: Record<string, number | null>; condition_key: string | null; n: number }>;
  };
  items: Array<{
    rank: 1;
    actual_coordinates: Record<string, number>;
    normalized_coordinates: Record<string, number>;
    response_predictions: Array<{ response_id: string; mean_raw: number; latent_standard_deviation_raw: number; predictive_standard_deviation_raw: number }>;
    desirability_moments: DesirabilityMoments;
    acquisition: { kind: "desirability_beta_expected_improvement"; value: number; threshold: number;
      distribution: "point_mass" | "bernoulli_limit" | "beta_moment_match"; alpha: number | null; beta: number | null; xi_desirability: number;
      numerical_policy?: "positive_beta_integral_v2" };
    nearest_existing_distance: number;
    constraint_evaluations: BayesianConstraintEvaluationResponse[];
  }>;
  search_budget: {
    max_evaluations_total: number; evaluations_consumed: number;
    evaluation_unit: "candidate_with_all_response_desirability_moments";
    posterior_evaluations: number; integrand_evaluations: number; response_fit_count: number;
    model_max_evaluations_total: number; model_evaluations_consumed: number; final_factorizations: number;
    time_budget_ms: number; elapsed_ms: number; searches: BayesianNoiseBatchResponse["search_budget"]["searches"];
    termination_reason: string;
  };
  warnings: string[];
  limitations: string[];
}
export interface DesirabilityQ1Review {
  schema_version: 2;
  review_id: string;
  study_id: string;
  study_version_id: string;
  source_history_revision_id: string;
  source_observation_history_sha256: string;
  config_sha256: string;
  expires_at: string;
  calculation: DesirabilityQ1Calculation;
}
export interface DesirabilityQ1Batch extends Omit<DesirabilityQ1Review, "schema_version" | "review_id" | "expires_at"> {
  method_id: "doe.bayesian_optimization";
  method_version: "0.9.0";
  result_schema_version: 4;
  config_schema_version: 4;
  model_schema_version: 5;
  item_schema_version: 3;
  batch_id: string;
  definition_sha256: string;
  batch_size: 1;
  batch_policy: "independent_latent_desirability_beta_ei_v1";
  items: Array<{ item_id: string; batch_id: string; rank: 1; trial: BayesianTrialResponse; current_trial: BayesianTrialResponse }>;
  result_sha256: string;
  created_at: string;
  is_latest: boolean;
  batch_state: "pending" | "completed" | "abandoned";
  requested_total_trial_budget: number;
  provenance: { app_version: string; python_version: string; platform: string; build_commit: string | null; package_versions: Record<string, string> };
}

export interface DesirabilityBatchOptions {
  sample_count: number;
  max_moment_evaluations: number;
  min_batch_distance_normalized: number;
}
export interface DesirabilityBatchReviewRequest extends Omit<DesirabilityQ1ReviewRequest, "schema_version" | "batch_size"> {
  schema_version: 5;
  batch_size: number;
  batch_options: DesirabilityBatchOptions;
}
export interface DesirabilityPlanning {
  score: number;
  mc_standard_error: number;
  conditional_variance_raw: Record<string, number>;
  search_seed: number;
  sampler: {
    numerical_policy?: "positive_beta_integral_v2";
    policy_version: "conditional_mc_desirability_beta_marginal_v1";
    root_seed: number;
    response_sample_seeds: Record<string, string>;
    batch_step: number;
    requested_sample_count: number;
    effective_sample_count: number;
    conditioned_on_selected_ranks: number[];
    baseline_threshold: number;
    representative_prediction_source: "completed_observations_base_posterior";
    common_random_numbers: true;
    response_independence_assumption: true;
    score_is_exact_joint_ei: false;
    mc_standard_error_excludes_beta_approximation_error: true;
    covariance_adjustment_is_measurement_noise: false;
    selected_covariance: Record<string, { rank: number; negative_eigenvalue_adjustment_scaled: number;
      negative_eigenvalue_adjustment_raw: number; roundoff_scale: number; conditional_variance_adjustment_max_scaled: number }>;
    moment_evaluation_unit: "joint_response_desirability_moments";
    max_moment_evaluations: number; moment_evaluations: number; response_moment_evaluations: number;
    integration_evaluations: number; candidate_evaluations: number; exact_selected_evaluations: number;
  };
  proof: {
    response_proofs: Record<string, { selected_mean_scaled: number[]; selected_covariance_scaled: number[][];
      candidate_mean_scaled: number; candidate_variance_scaled: number; cross_covariance_scaled: number[] }>;
    thresholds: number[];
    sample_moments: DesirabilityMoments[];
  };
}
export interface DesirabilityBatchCalculation extends Omit<DesirabilityQ1Calculation, "schema_version" | "batch_size" | "policy" | "items" | "search_budget"> {
  schema_version: 5;
  batch_size: number;
  policy: "conditional_mc_desirability_beta_marginal_v1";
  batch_options: DesirabilityBatchOptions;
  items: Array<Omit<DesirabilityQ1Calculation["items"][number], "rank"> & {
    rank: number; nearest_selected_distance: number | null; planning: DesirabilityPlanning;
  }>;
  search_budget: DesirabilityQ1Calculation["search_budget"] & {
    max_moment_evaluations: number; moment_evaluations: number; incumbent_moment_evaluations: number;
    response_moment_evaluations: number; initial_pool_upper_bound_per_step: number; preflight_moment_allowance: number;
  };
}
export interface DesirabilityBatchReview extends Omit<DesirabilityQ1Review, "schema_version" | "calculation"> {
  schema_version: 3;
  calculation: DesirabilityBatchCalculation;
}
export interface DesirabilityOrderedBatch extends Omit<DesirabilityQ1Batch,
  "method_version" | "result_schema_version" | "config_schema_version" | "item_schema_version" | "batch_size" | "batch_policy" | "items" | "batch_state" | "calculation"> {
  method_version: "0.10.0";
  result_schema_version: 5;
  config_schema_version: 5;
  item_schema_version: 4;
  batch_size: number;
  batch_policy: "conditional_mc_desirability_beta_marginal_v1";
  calculation: DesirabilityBatchCalculation;
  items: Array<Omit<DesirabilityQ1Batch["items"][number], "rank"> & { rank: number }>;
  batch_state: "pending" | "partially_completed" | "completed" | "abandoned" | "closed_mixed";
}
export interface BoFitPolicy {
  kind: "bounded_multiscale_starts_v1";
  deterministic_start_count: number;
}
export interface BoFitDiagnostics {
  schema_version: 1;
  policy: BoFitPolicy["kind"];
  deterministic_start_count: number;
  screening: Array<{ log_parameters: number[]; negative_log_likelihood: number }>;
  refined_screen_indices: number[];
  start_initial_negative_log_likelihoods: number[];
  start_best_evaluations: Array<{ log_parameters: number[]; negative_log_likelihood: number; evaluation_index: number }>;
  selected: { stage: "screen" | "local_evaluation"; screen_index: number | null; start_index: number | null; log_parameters: number[]; negative_log_likelihood: number };
  bound_hits: Array<{ parameter: "signal_amplitude" | "length_scale" | "measurement_variance"; factor_index: number | null; side: "lower" | "upper"; value: number; bound: number }>;
  global_optimum_guaranteed: false;
}
export type DesirabilityFittedRawModel = Omit<RawResponseModel, "schema_version" | "policy_version" | "optimizer"> & {
  schema_version: 5; policy_version: "bo_noise_latent_fit_v4"; fit_diagnostics: BoFitDiagnostics;
  optimizer: Omit<RawResponseModel["optimizer"], "starts"> & {
    max_evaluations: number; max_iterations: number;
    starts: Array<{ success: boolean; status: number; termination_reason: string; iterations: number; evaluations: number;
      initial_log_parameters: number[]; final_log_parameters: number[]; negative_log_likelihood: number }>;
  };
};
export interface DesirabilityFitReviewRequest extends Omit<DesirabilityBatchReviewRequest, "schema_version"> {
  schema_version: 6;
  fit_policy: BoFitPolicy;
}
export interface DesirabilityFitCalculation extends Omit<DesirabilityBatchCalculation, "schema_version" | "shared_model"> {
  schema_version: 6;
  shared_model: Omit<DesirabilityBatchCalculation["shared_model"], "schema_version" | "response_models"> & {
    schema_version: 6;
    response_models: Array<{ response_id: string; model: DesirabilityFittedRawModel; observation_view: BayesianNoiseBatchResponse["observation_view"] }>;
  };
}
export interface DesirabilityFitReview extends Omit<DesirabilityBatchReview, "schema_version" | "calculation"> {
  schema_version: 4; calculation: DesirabilityFitCalculation;
}
export interface DesirabilityFitBatch extends Omit<DesirabilityOrderedBatch, "method_version" | "result_schema_version" | "config_schema_version" | "model_schema_version" | "calculation"> {
  method_version: "0.11.0"; result_schema_version: 6; config_schema_version: 6; model_schema_version: 6;
  calculation: DesirabilityFitCalculation;
}
export interface DesirabilityCurveReviewRequest extends Omit<DesirabilityBatchReviewRequest, "schema_version"> {
  schema_version: 7; fit_policy: BoFitPolicy | null;
}
export interface DesirabilityCurveCalculation extends Omit<DesirabilityBatchCalculation, "schema_version" | "shared_model"> {
  schema_version: 7;
  shared_model: Omit<DesirabilityBatchCalculation["shared_model"], "schema_version" | "response_models" | "curve_policy" | "moment_policy"> & {
    schema_version: 7;
    curve_policy: "per_response_target_gaussian_or_ds_v1";
    moment_policy: "independent_latent_versioned_curve_moments_v1";
    response_models: Array<{ response_id: string; model: RawResponseModel | DesirabilityFittedRawModel; observation_view: BayesianNoiseBatchResponse["observation_view"] }>;
  };
}
export interface DesirabilityCurveReview extends Omit<DesirabilityBatchReview, "schema_version" | "calculation"> {
  schema_version: 5; calculation: DesirabilityCurveCalculation;
}
export interface DesirabilityCurveBatch extends Omit<DesirabilityOrderedBatch, "method_version" | "result_schema_version" | "config_schema_version" | "model_schema_version" | "calculation"> {
  method_version: "0.12.0"; result_schema_version: 7; config_schema_version: 7; model_schema_version: 7;
  calculation: DesirabilityCurveCalculation;
}
export type DesirabilityReviewRequest = DesirabilityQ1ReviewRequest | DesirabilityBatchReviewRequest | DesirabilityFitReviewRequest | DesirabilityCurveReviewRequest;
export type DesirabilityCalculation = DesirabilityQ1Calculation | DesirabilityBatchCalculation | DesirabilityFitCalculation | DesirabilityCurveCalculation;
export type DesirabilityReview = DesirabilityQ1Review | DesirabilityBatchReview | DesirabilityFitReview | DesirabilityCurveReview;
export type DesirabilityBatch = DesirabilityQ1Batch | DesirabilityOrderedBatch | DesirabilityFitBatch | DesirabilityCurveBatch;
