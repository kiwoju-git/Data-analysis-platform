import type { BayesianDesirabilityObjective, BayesianConstraintEvaluationResponse } from "./bayesian";
import type { DesirabilityReviewRequest, DesirabilityQ1Calculation, DesirabilityCurveCalculation, DesirabilityPlanning, DesirabilityOrderedBatch } from "./bayesianDesirability";

export type PlanningFitOptions = Exclude<DesirabilityReviewRequest, { schema_version: 4 }>;
export interface PlanningModelCreateRequest { request_id: string; fit: PlanningFitOptions }
export interface PlanningModelSummary {
  schema_version: 1; model_id: string; study_id: string; study_version_id: string;
  source_history_revision_id: string; history_sha256: string; definition_sha256: string;
  snapshot_sha256: string; config_sha256: string; created_at: string; source_is_current: boolean;
}
export interface PlanningModelDetail extends PlanningModelSummary {
  fit: PlanningFitOptions; objective: Pick<BayesianDesirabilityObjective, "responses">;
  response_models: DesirabilityCurveCalculation["shared_model"]["response_models"];
  incumbent: DesirabilityQ1Calculation["incumbent"];
  observation_view: DesirabilityQ1Calculation["observation_view"];
  warnings: string[]; model_reusable_without_refit: true;
}
export interface PlanningSourceRequest {
  model_id: string; expected_model_sha256: string; expected_history_revision_id: string;
  expected_history_sha256: string; expected_trial_count: number;
}
export type CandidateSource = { kind: "seeded_uniform"; count: number; seed: number }
  | { kind: "explicit_rows"; points: Record<string, number>[] }
  | { kind: "append_rows"; points: Record<string, number>[] }
  | { kind: "remove_rows"; row_ids: string[] };
export interface CandidateRevisionCreateRequest extends PlanningSourceRequest {
  request_id: string; candidate_set_id: string; name: string; expected_head_revision_id: string | null;
  source: CandidateSource; include_constraint_violations: boolean;
}
export interface CandidateRow {
  row_id: string; source_row_number: number; input_coordinates: Record<string, number>;
  canonical_level_indices: Record<string, number | null>; actual_coordinates: Record<string, number>;
  normalized_coordinates: Record<string, number>; constraint_evaluations: BayesianConstraintEvaluationResponse[];
  constraints_satisfied: boolean; nearest_existing_distance: number | null; novel: boolean; eligible: boolean;
}
export interface EvaluatedCandidateRow extends CandidateRow {
  response_predictions: DesirabilityQ1Calculation["items"][number]["response_predictions"];
  desirability_moments: DesirabilityQ1Calculation["items"][number]["desirability_moments"];
  acquisition: DesirabilityQ1Calculation["items"][number]["acquisition"];
  prediction_source: "completed_observations_base_posterior";
}
export interface CandidateRevisionSummaryV1 {
  schema_version: 1; candidate_set_id: string; name: string; revision_id: string; revision_number: number;
  parent_revision_id: string | null; model_id: string; model_sha256: string; rows_sha256: string;
  config_sha256: string; excluded_coordinates_sha256: string; source_trial_count: number;
  row_count: number; eligible_count: number; created_at: string; source_is_current: boolean;
}
export interface CandidateRevisionSummaryV2 extends Omit<CandidateRevisionSummaryV1, "schema_version" | "model_id" | "model_sha256"> {
  schema_version: 2; model_id: string | null; model_sha256: string | null;
  study_version_id: string; source_history_revision_id: string; definition_sha256: string; history_sha256: string;
  duplicate_tolerance: number;
}
export type CandidateRevisionSummary = CandidateRevisionSummaryV1 | CandidateRevisionSummaryV2;
export interface CandidatePage { revision: CandidateRevisionSummary; offset: number; limit: number; items: CandidateRow[] }
export interface PlanningEvaluationRequest { expected_model_sha256: string; points: Record<string, number>[]; time_budget_ms: number }
export interface PlanningEvaluationResponse {
  schema_version: 1; model_id: string; model_sha256: string; request_sha256: string;
  items: EvaluatedCandidateRow[]; source_is_current: boolean; eligibility_source_trial_count: number;
  eligibility_coordinates_sha256: string; eligibility_is_current: boolean; model_refit: false;
}
export interface PlanningSelectionCreateRequest extends PlanningSourceRequest {
  request_id: string; candidate_revision_id: string; expected_rows_sha256: string;
  row_ids: string[]; total_trial_budget: number;
}
export interface PlanningSelectionItem extends Omit<EvaluatedCandidateRow, "prediction_source"> {
  rank: number; nearest_selected_distance: number | null; planning: Omit<DesirabilityPlanning, "search_seed">;
}
export interface PlanningSelectionCalculation {
  schema_version: 1; selection_policy: "manual_ordered_fixed_model_v1"; model_refit: false;
  items: PlanningSelectionItem[]; moment_evaluations: number; max_moment_evaluations: number;
}
export interface PlanningSelectionResponse {
  schema_version: 1; selection_id: string; study_id: string; study_version_id: string;
  model_id: string; model_sha256: string; candidate_revision_id: string; rows_sha256: string;
  config_sha256: string; result_sha256: string; request: PlanningSelectionCreateRequest;
  calculation: PlanningSelectionCalculation; created_at: string; source_is_current: boolean;
  confirmed_batch_id: string | null;
}
export interface PlanningSelectionSummary extends Pick<PlanningSelectionResponse,
  "selection_id" | "study_id" | "study_version_id" | "model_id" | "candidate_revision_id" |
  "config_sha256" | "result_sha256" | "created_at" | "source_is_current" | "confirmed_batch_id"> {
  selected_count: number;
}
export interface PlanningConfirmRequest { expected_config_sha256: string; expected_result_sha256: string }
export interface PlanningBatchResponse extends Omit<DesirabilityOrderedBatch,
  "method_version" | "result_schema_version" | "config_schema_version" | "model_schema_version" | "batch_policy" | "calculation"> {
  method_version: "0.13.0"; result_schema_version: 8; config_schema_version: 8; model_schema_version: 8;
  batch_policy: "manual_ordered_fixed_model_v1"; calculation: PlanningSelectionCalculation;
  source: { model_id: string; model_sha256: string; candidate_revision_id: string; rows_sha256: string;
    selection_id: string; selection_config_sha256: string; selection_result_sha256: string };
  objective: Pick<BayesianDesirabilityObjective, "responses">;
  response_models: PlanningModelDetail["response_models"]; incumbent: PlanningModelDetail["incumbent"];
  observation_view: PlanningModelDetail["observation_view"];
  warnings: string[];
}
