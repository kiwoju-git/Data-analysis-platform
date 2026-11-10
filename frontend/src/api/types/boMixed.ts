import type { BayesianDesirabilityObjective, BayesianFactorRequest, BayesianFactorResponse, BayesianHistoryRevisionResponse,
  BayesianLinearConstraintRequest, BayesianStudyLifecycleEventResponse, BayesianStudyResponse, BayesianTrialResponse } from "./bayesian";
import type { PlanningFitOptions } from "./boPlanning";
import type { DesirabilityPlanning, DesirabilityQ1Calculation } from "./bayesianDesirability";
import type { CandidateRevisionSummaryV2, CandidateRow } from "./boPlanning";
import type { AugmentationPolicy, AugmentationTrace } from "./boAugmentation";

export type MixedCorrelationPolicy = "equal_positive_correlation_v1" | "unequal_hyperspherical_correlation_v1" | "ordinal_monotone_latent_rbf_v1";
export interface MixedCategoricalFactorRequest {
  factor_id: string; name: string; unit: string | null; domain_kind: "nominal" | "ordinal"; levels: string[]; correlation_policy: MixedCorrelationPolicy;
}
export interface MixedNumericFactorRequest extends BayesianFactorRequest { domain_kind: "continuous" | "discrete_numeric" }
export type MixedFactorRequest = MixedNumericFactorRequest | MixedCategoricalFactorRequest;
export interface MixedCategoricalFactorResponse extends MixedCategoricalFactorRequest { order: number; encoding_rule: "declared_level_index_v1" }
export type MixedFactorResponse = (BayesianFactorResponse & { domain_kind: "continuous" | "discrete_numeric" }) | MixedCategoricalFactorResponse;
export type MixedActualPoint = Record<string, number | string>;
export type MixedEncodedPoint = Record<string, number>;
export interface MixedStudyCreateRequest {
  schema_version: 7; name: string; factors: MixedFactorRequest[]; objective: BayesianDesirabilityObjective; constraints: BayesianLinearConstraintRequest[];
  initial_design_seed: number; initial_design_size: number; initial_design_policy: "sha256_counter_mixed_uniform_feasible_v1"; predecessor_study_id: string | null;
}
export interface MixedInitialDesign {
  policy: "sha256_counter_mixed_uniform_feasible_v1"; seed: number; requested_size: number; generated_size: number;
  attempt_limit: number; attempts_consumed: number; rejected_duplicate_count: number; rejected_infeasible_count: number;
  coordinate_encoding: "numeric_normalized_category_index_v1"; category_level_counts: Record<string, number[]>; unobserved_level_indices: Record<string, number[]>;
  warnings: string[];
}
export interface MixedTrialResponse extends Omit<BayesianTrialResponse, "actual_coordinates" | "normalized_coordinates" | "response_values" | "objective_value"> {
  actual_coordinates: MixedActualPoint; encoded_coordinates: MixedEncodedPoint; coordinate_encoding: "numeric_normalized_category_index_v1";
  objective_value: null; response_values: Record<string, number> | null; replicate_of_trial_id: string | null;
}
export interface MixedStudyResponse extends Omit<BayesianStudyResponse, "study_schema_version" | "factors" | "objective" | "initial_design" | "trials" | "recommendation_blockers"> {
  study_schema_version: 7; factors: MixedFactorResponse[]; objective: BayesianDesirabilityObjective; initial_design: MixedInitialDesign;
  trials: MixedTrialResponse[]; recommendation_blockers: string[];
  recommendation_workflow: "fixed_candidate_mixed_planning_v1";
}
export type AnyBayesianStudyResponse = BayesianStudyResponse | MixedStudyResponse;
export interface MixedObservationBatchRequest {
  request_id: string; expected_study_version_id: string; expected_history_revision_id: string; expected_observation_history_sha256: string;
  observations: { trial_id: string; response_values: Record<string, number> }[];
}
export interface MixedObservationBatchResponse {
  batch_schema_version: 2; study: MixedStudyResponse; completed_trial_ids: string[]; completed_trial_count: number;
  observation_history: BayesianHistoryRevisionResponse; request_id: string; created_at: string;
}
export interface MixedTrialTransitionResponse { study_id: string; trial: MixedTrialResponse; observation_history: BayesianHistoryRevisionResponse }
export interface MixedStudyCloseResponse { study: MixedStudyResponse; lifecycle_event: BayesianStudyLifecycleEventResponse }
export interface MixedReplicateCreateResponse {
  schema_version: 2; study_id: string; study_version_id: string; request_id: string; parent_trial_id: string; source_history_revision_id: string;
  source_history_sha256: string; request_sha256: string; trials: MixedTrialResponse[]; replayed: boolean;
}

export interface MixedSourceRequest { expected_study_version_id: string; expected_definition_sha256: string; expected_history_revision_id: string; expected_history_sha256: string; expected_trial_count: number }
export interface MixedFitOptions {
  response_models: PlanningFitOptions["response_models"];
  observation_policy: { mode: "retain_raw" | "exact_replicates"; nearby_tolerances: null; nearby_units: "actual" | "normalized" };
  xi_desirability: number; search: PlanningFitOptions["search"];
  fit_policy: { policy: "bounded_typed_factor_starts_v1"; deterministic_start_count: number }; max_moment_evaluations: number;
}
export interface MixedModelCreateRequest extends MixedSourceRequest { request_id: string; fit: MixedFitOptions }
export interface MixedModelSummary {
  schema_version: 2; model_id: string; study_id: string; study_version_id: string; source_history_revision_id: string;
  history_sha256: string; definition_sha256: string; snapshot_sha256: string; config_sha256: string; created_at: string; source_is_current: boolean;
}
export interface MixedModelDetail extends MixedModelSummary {
  fit: MixedFitOptions; objective: BayesianDesirabilityObjective;
  response_models: { response_id: string; model: Record<string, unknown>; observation_view: Record<string, unknown> }[];
  incumbent: { policy: "max_posterior_expected_desirability_at_observed_coordinates_v1"; best_observed_desirability: number;
    best_observed_trial_id: string; latent_incumbent_value: number; latent_incumbent_trial_id: string; latent_incumbent_encoded_coordinates: MixedEncodedPoint;
    coordinate_encoding: "numeric_normalized_category_index_v1"; observed_trial_desirabilities: { trial_id: string; value: number }[];
    training_posterior_desirabilities: { trial_id: string; moments: DesirabilityQ1Calculation["items"][number]["desirability_moments"] }[] };
  observation_view: Record<string, unknown>; warnings: string[]; model_reusable_without_refit: true;
}
export interface MixedCandidateRow extends Omit<CandidateRow, "input_coordinates" | "actual_coordinates" | "normalized_coordinates"> {
  schema_version: 2; input_coordinates: MixedActualPoint; actual_coordinates: MixedActualPoint; encoded_coordinates: MixedEncodedPoint;
  coordinate_encoding: "numeric_normalized_category_index_v1";
  distance_policy: "numeric_normalized_category_hamming_v1" | "numeric_normalized_nominal_hamming_ordinal_rank_v1"; ordinal_rank_distance: boolean;
}
export interface EvaluatedMixedCandidateRow extends MixedCandidateRow {
  response_predictions: DesirabilityQ1Calculation["items"][number]["response_predictions"];
  desirability_moments: DesirabilityQ1Calculation["items"][number]["desirability_moments"];
  acquisition: DesirabilityQ1Calculation["items"][number]["acquisition"] | null;
  prediction_source: "completed_observations_base_posterior";
}
export interface MixedEvaluationRequest { expected_model_sha256: string; points: MixedActualPoint[]; time_budget_ms: number; max_moment_evaluations: number }
export interface MixedEvaluationResponse {
  model_id: string; snapshot_sha256: string; items: EvaluatedMixedCandidateRow[]; model_refit: false;
  eligibility_history_sha256: string; eligibility_is_current: boolean;
}
export type MixedCandidateSource = { kind: "seeded_uniform"; count: number; seed: number } | { kind: "explicit_rows" | "append_rows"; points: MixedActualPoint[] } | { kind: "remove_rows"; row_ids: string[] };
export interface MixedCandidateCreateRequest extends MixedSourceRequest {
  schema_version: 3; request_id: string; candidate_set_id: string; name: string; expected_head_revision_id: string | null;
  model_id: string | null; expected_model_sha256: string | null; duplicate_tolerance: number; ordinal_rank_distance: boolean;
  include_constraint_violations: boolean; source: MixedCandidateSource;
}
export interface MixedCandidateSummary extends Omit<CandidateRevisionSummaryV2, "schema_version"> { schema_version: 3; ordinal_rank_distance: boolean }
export interface MixedCandidatePage { revision: MixedCandidateSummary; offset: number; limit: number; items: MixedCandidateRow[] }
export interface MixedSelectionRequest extends MixedSourceRequest {
  schema_version: 3; request_id: string; kind: "manual_ordered" | "augmentation"; candidate_revision_id: string; expected_rows_sha256: string;
  model_id: string | null; expected_model_sha256: string | null; row_ids: string[]; policy: AugmentationPolicy | null;
  batch_size: number; total_trial_budget: number; duplicate_tolerance: number; ordinal_rank_distance: boolean; min_batch_distance: number;
  sample_count: number; max_evaluations: number; max_moment_evaluations: number; time_budget_ms: number;
}
export interface MixedSelectionItem extends EvaluatedMixedCandidateRow {
  acquisition: NonNullable<EvaluatedMixedCandidateRow["acquisition"]>; rank: number; nearest_selected_distance: number | null;
  planning: Omit<DesirabilityPlanning, "search_seed" | "sampler"> & { sampler: DesirabilityPlanning["sampler"] & { coordinate_encoding: "numeric_normalized_category_index_v1" } };
}
export interface MixedManualCalculation {
  schema_version: 2; selection_policy: "manual_ordered_mixed_model_v1"; model_refit: false;
  distance_policy: MixedCandidateRow["distance_policy"]; ordinal_rank_distance: boolean; items: MixedSelectionItem[];
  moment_evaluations: number; max_moment_evaluations: number;
}
export interface MixedAugmentationCalculation {
  schema_version: 3; augmentation: AugmentationTrace; selected_rows: (MixedCandidateRow | EvaluatedMixedCandidateRow)[];
  source_row_count: number; prediction_evaluations: number; max_moment_evaluations: number; time_budget_ms: number; model_refit: false;
}
export type MixedSelectionCalculation = MixedManualCalculation | MixedAugmentationCalculation;
export interface MixedSelectionResponse {
  schema_version: 3; selection_id: string; study_id: string; study_version_id: string; model_id: string | null;
  candidate_revision_id: string; config_sha256: string; result_sha256: string; request: MixedSelectionRequest;
  calculation: MixedSelectionCalculation; created_at: string; source_is_current: boolean; confirmed_batch_id: string | null;
}
export interface MixedSelectionSummary extends Pick<MixedSelectionResponse, "schema_version" | "selection_id" | "study_id" | "study_version_id" | "model_id" | "candidate_revision_id" | "config_sha256" | "result_sha256" | "created_at" | "source_is_current" | "confirmed_batch_id"> {
  kind: MixedSelectionRequest["kind"]; policy: AugmentationPolicy | null; selected_count: number;
}
export interface MixedBatchResponse {
  method_id: "doe.bayesian_optimization"; method_version: "0.15.0";
  config_schema_version: 10; result_schema_version: 10; model_schema_version: 10; item_schema_version: 5;
  batch_policy: "source_owned_mixed_planning_v1"; batch_size: number;
  batch_id: string; study_id: string; study_version_id: string; source_history_revision_id: string;
  source_observation_history_sha256: string; definition_sha256: string;
  source: { model_id: string | null; model_sha256: string | null; candidate_revision_id: string; rows_sha256: string;
    selection_id: string; selection_config_sha256: string; selection_result_sha256: string };
  objective: BayesianDesirabilityObjective; response_models: MixedModelDetail["response_models"] | null;
  incumbent: MixedModelDetail["incumbent"] | null; observation_view: Record<string, unknown> | null; warnings: string[];
  selection_request: MixedSelectionRequest; calculation: MixedSelectionCalculation;
  items: { item_id: string; batch_id: string; rank: number; trial: MixedTrialResponse; current_trial: MixedTrialResponse }[];
  config_sha256: string; result_sha256: string; created_at: string; is_latest: boolean;
  batch_state: "pending" | "partially_completed" | "completed" | "abandoned" | "closed_mixed";
  requested_total_trial_budget: number; provenance: import("./boPlanning").PlanningBatchResponse["provenance"];
}
