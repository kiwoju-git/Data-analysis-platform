import type { CandidatePage, CandidateRevisionCreateRequest, CandidateRow, EvaluatedCandidateRow, PlanningBatchResponse, PlanningModelDetail } from "./boPlanning";
import type { AutoStrategyView } from "../boAutoStrategy";

export interface AutoEvidenceRequest {
  schema_version: 1; routing_model_id: string; expected_model_sha256: string;
  r_squared_threshold: number; expected_decision_sha256: string;
}
export interface AutoStrategyEvidence {
  schema_version: 1; diagnostic: Omit<AutoStrategyView["diagnostic"], "source_is_current">;
  decision: AutoStrategyView["decision"]; decision_sha256: string;
}

export interface AugmentationSourceRequest {
  expected_study_version_id: string; expected_definition_sha256: string;
  expected_history_revision_id: string; expected_history_sha256: string; expected_trial_count: number;
}
export interface CandidateRevisionCreateRequestV2 extends Omit<CandidateRevisionCreateRequest, "model_id" | "expected_model_sha256">, AugmentationSourceRequest {
  schema_version: 2; model_id: string | null; expected_model_sha256: string | null; duplicate_tolerance: number;
}
export type AugmentationPolicy = "greedy_incremental_maxpro_v1" | "greedy_mixed_maximin_v1" |
  "refine_ei_then_desirability_sd_v1" | "confirm_mean_then_competitive_sd_v1" | "refine_ei_alternating_desirability_response_sd_v2";
interface AugmentationSelectionFields extends AugmentationSourceRequest {
  request_id: string; candidate_revision_id: string; expected_rows_sha256: string;
  model_id: string | null; expected_model_sha256: string | null; policy: AugmentationPolicy;
  batch_size: number; total_trial_budget: number; duplicate_tolerance: number; min_batch_distance_normalized: number;
  max_evaluations: number; max_moment_evaluations: number; time_budget_ms: number;
}
export type AugmentationSelectionRequest = AugmentationSelectionFields & (
  { schema_version: 2; auto_strategy?: never } | { schema_version: 4; auto_strategy: AutoEvidenceRequest }
);
export interface AugmentationStep {
  rank: number; row_id: string; criterion: string; score: number; score_scale: "natural_log" | "original";
  optimization_direction: "minimize" | "maximize"; nearest_existing_distance: number;
  nearest_selected_distance: number | null; compared_candidate_count: number; competitive_threshold: number | null;
}
export interface AugmentationTrace {
  schema_version: 1; policy: AugmentationPolicy;
  source: { model_snapshot_id: string | null; model_snapshot_sha256: string | null; candidate_revision_id: string;
    candidate_revision_sha256: string; history_sha256: string };
  selected_row_ids: string[]; steps: AugmentationStep[];
  distance_policy: "normalized_numeric_hamming_nominal_explicit_ordinal_rank_v1";
  ordinal_rank_distance: boolean; tie_break: "row_id_ascending";
  competitive_set_policy: "mean_at_least_observed_location_latent_incumbent" | null;
  reference_count: number; raw_reference_count: number; eligible_candidate_count: number; projection_collisions: number;
  unscorable_candidates: { row_id: string; first_rank: number; score: null; status: "projection_collision" }[];
  evaluations: number; max_evaluations: number; pair_comparisons: number; time_budget_ms: number;
  model_refit: false; fantasy_observations: false; warnings: string[];
  response_uncertainty: null | { policy: "importance_weighted_rms_normalized_latent_sd_v1"; variance_kind: "latent";
    scale: "dimensionless"; context: { response_id: string; normalization_scale: number; normalized_importance: number }[];
    schedule: "first_ei_then_alternating_desirability_sd_response_sd" };
}
export interface AugmentationPredictedRow extends Omit<EvaluatedCandidateRow, "acquisition"> { acquisition: EvaluatedCandidateRow["acquisition"] | null }
interface AugmentationCalculationFields {
  augmentation: AugmentationTrace; selected_rows: (CandidateRow | AugmentationPredictedRow)[];
  source_row_count: number; prediction_evaluations: number; max_moment_evaluations: number; time_budget_ms: number; model_refit: false;
}
export type AugmentationCalculation = AugmentationCalculationFields & (
  { schema_version: 1; auto_evidence?: never } | { schema_version: 2; auto_evidence: AutoStrategyEvidence }
);
export interface AugmentationSelectionResponse {
  schema_version: 2 | 4; selection_id: string; study_id: string; study_version_id: string;
  model_id: string | null; candidate_revision_id: string; config_sha256: string; result_sha256: string;
  request: AugmentationSelectionRequest; calculation: AugmentationCalculation; created_at: string;
  source_is_current: boolean; confirmed_batch_id: string | null;
}
export interface AugmentationBatchResponse extends Omit<PlanningBatchResponse,
  "method_version" | "config_schema_version" | "result_schema_version" | "model_schema_version" | "batch_policy" |
  "calculation" | "source" | "response_models" | "incumbent" | "observation_view" | "warnings"> {
  method_version: "0.14.0" | "0.16.0"; config_schema_version: 9 | 11; result_schema_version: 9 | 11; model_schema_version: 9 | 11;
  batch_policy: "source_owned_augmentation_v1"; calculation: AugmentationCalculation; selection_request: AugmentationSelectionRequest;
  source: Omit<PlanningBatchResponse["source"], "model_id" | "model_sha256"> & { model_id: string | null; model_sha256: string | null };
  model: PlanningModelDetail | null;
}
export type { CandidatePage };

export interface AugmentationRenewalRequest {
  request_id: string; expected_config_sha256: string; expected_result_sha256: string;
}
export interface AugmentationRenewalLineage {
  schema_version: 1; study_version_id: string; renewed_selection_id: string;
  original_selection_id: string; original_config_sha256: string; original_result_sha256: string;
  numerical_policy: "positive_beta_integral_v2"; created_at: string;
}
export interface AugmentationRenewalResponse {
  selection: AugmentationSelectionResponse; lineage: AugmentationRenewalLineage;
}
