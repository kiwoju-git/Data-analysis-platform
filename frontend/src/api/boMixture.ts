import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { BayesianDesirabilityObjective, BayesianHistoryRevisionResponse, BayesianLinearConstraintRequest, BayesianReplicateCreateRequest, BayesianStudyCloseRequest, BayesianTrialAbandonRequest } from "./types/bayesian";
import type { MixedActualPoint, MixedFactorRequest, MixedFactorResponse, MixedFitOptions, MixedSourceRequest, MixedStudyResponse, MixedTrialResponse, MixedEvaluationRequest, MixedObservationBatchRequest } from "./types/boMixed";
import type { DatasetImportRequest } from "./types/boDatasetImport";
import type { ReportSourceDescriptor } from "./types/reports";

export interface MixtureComponent { factor_id: string; name: string; low: number; high: number; unit: string }
export interface MixtureGroup { total: number; coding: "lower" | "upper" | "auto"; components: MixtureComponent[] }
export type MixtureFactor = MixedFactorResponse | (MixtureComponent & { domain_kind: "mixture_component"; order: number; scaling_rule: string });
export interface MixtureStudyRequest {
  schema_version: 8; name: string; mixture: MixtureGroup; process_factors: MixedFactorRequest[];
  objective: BayesianDesirabilityObjective; constraints: BayesianLinearConstraintRequest[]; initial_design_seed: number; initial_design_size: number;
}
export interface MixtureDatasetImportRequest extends Omit<DatasetImportRequest, "schema_version" | "objective" | "factor_mappings"> {
  schema_version: 2; mixture: MixtureGroup; objective: BayesianDesirabilityObjective;
  factor_mappings: { column_id: string; factor: MixedFactorRequest | (MixtureComponent & { domain_kind: "mixture_component" }) }[];
}
export type MixtureDatasetCreateRequest = MixtureDatasetImportRequest & { request_id: string; expected_preflight_sha256: string };
export interface MixtureTrial extends Omit<MixedTrialResponse, "coordinate_encoding"> { coordinate_encoding: "mixture_pseudocomponents_process_v1" }
export interface MixtureStudy extends Omit<MixedStudyResponse, "study_schema_version" | "factors" | "trials" | "initial_design" | "recommendation_workflow"> {
  study_schema_version: 8; mixture: MixtureGroup; process_factors: MixedFactorRequest[]; factors: MixtureFactor[];
  trials: MixtureTrial[]; initial_design: Record<string, unknown>; design_domain: Record<string, unknown>;
  recommendation_workflow: "fixed_candidate_mixture_planning_v1";
}
export interface MixtureModel {
  schema_version: 3; model_id: string; study_id: string; study_version_id: string;
  source_history_revision_id: string; definition_sha256: string; history_sha256: string;
  snapshot_sha256: string; config_sha256: string; created_at: string; source_is_current: boolean;
  fit: MixedFitOptions; objective: BayesianDesirabilityObjective; design_domain: Record<string, unknown>;
  response_models: unknown[]; warnings: string[]; model_reusable_without_refit: true;
}
export interface MixtureRow {
  row_id: string; actual_coordinates: MixedActualPoint; constraints_satisfied: boolean;
  response_predictions: { response_id: string; mean_raw: number; latent_standard_deviation_raw: number; predictive_standard_deviation_raw: number }[];
  desirability_moments: { mean: number; variance: number };
  eligible: boolean; novel: boolean; input_coordinates: MixedActualPoint;
  nearest_existing_distance: number | null;
}
export interface MixturePage {
  revision: { revision_id: string; rows_sha256: string; model_id: string;
    study_version_id: string; definition_sha256: string; history_sha256: string; row_count: number };
  source_is_current: boolean; offset: number; limit: number; items: MixtureRow[]; generation: Record<string, unknown>;
}
export interface MixtureSelection {
  selection_id: string; config_sha256: string; result_sha256: string; created_at: string;
  config: MixtureSelectionRequest;
  result: { schema_version: 13; model_refit: false; joint_improvement_claimed: false; items: MixtureRow[]; warnings?: string[]; [key: string]: unknown };
}
export interface MixtureCandidateRequest extends MixedSourceRequest {
  schema_version: 4; request_id: string; candidate_set_id: string; name: string; model_id: string; expected_model_sha256: string;
  source: { kind: "seeded_uniform"; seed: number; count: number } | { kind: "explicit_rows"; points: MixedActualPoint[] };
  time_budget_ms: number; max_moment_evaluations: number;
}
export interface MixtureSelectionRequest extends MixedSourceRequest {
  schema_version: 6; request_id: string; candidate_revision_id: string; expected_rows_sha256: string; model_id: string; expected_model_sha256: string;
  policy: "manual_mixture_base_posterior_v1" | "greedy_mixture_maximin_v1"; row_ids: string[]; batch_size: number; total_trial_budget: number; min_batch_distance: number;
  time_budget_ms: number; max_moment_evaluations: number;
}
export interface MixtureBatch {
  batch_id: string; schema_version: 13; config_sha256: string; result_sha256: string; created_at: string;
  config: MixtureSelectionRequest; result: MixtureSelection["result"];
  items: { rank: number; result: MixtureRow; trial: MixtureTrial }[];
}
export interface MixtureObservationResult { batch_schema_version: 3; study: MixtureStudy; observation_history: BayesianHistoryRevisionResponse; request_id: string; completed_trial_count: number }
const route = (study: string, path = "") => `${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(study)}${path ? `/${path}` : ""}`;
async function request<T>(url: string, body?: unknown, method: "POST" | "PUT" = "POST"): Promise<T> {
  const response = await fetchApi(url, { headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) }, ...(body === undefined ? {} : { method, body: JSON.stringify(body) }) });
  if (!response.ok) throw await apiRequestError(response, "bayesian_mixture_request_failed");
  return await response.json() as T;
}
export const createMixtureStudy = (body: MixtureStudyRequest) => request<MixtureStudy>(route("mixture"), body);
export const fetchMixtureStudy = (study: string) => request<MixtureStudy>(route(study));
export const createMixtureModel = (study: string, body: MixedSourceRequest & { request_id: string; fit: MixedFitOptions }) => request<MixtureModel>(route(study, "mixture-planning-models"), body);
export const listMixtureModels = (study: string) => request<{ items: MixtureModel[] }>(route(study, "mixture-planning-models"));
export const fetchMixtureModel = (study: string, id: string) => request<MixtureModel>(route(study, `mixture-planning-models/${encodeURIComponent(id)}`));
export const evaluateMixtureModel = (study: string, id: string, body: MixedEvaluationRequest) => request<{ items: MixtureRow[] }>(route(study, `mixture-planning-models/${encodeURIComponent(id)}/evaluate`), body);
export const createMixtureCandidates = (study: string, body: MixtureCandidateRequest) => request<MixturePage>(route(study, "mixture-candidate-revisions"), body);
export const fetchMixtureCandidates = (study: string, id: string, offset = 0) => request<MixturePage>(route(study, `mixture-candidate-revisions/${encodeURIComponent(id)}?offset=${offset}&limit=50`));
export const createMixtureSelection = (study: string, body: MixtureSelectionRequest) => request<MixtureSelection>(route(study, "mixture-selections"), body);
export const fetchMixtureSelection = (study: string, id: string) => request<MixtureSelection>(route(study, `mixture-selections/${encodeURIComponent(id)}`));
export const confirmMixtureSelection = (study: string, id: string, body: { expected_config_sha256: string; expected_result_sha256: string }) => request<Record<string, unknown>>(route(study, `mixture-selections/${encodeURIComponent(id)}/confirm`), body);
export const fetchMixtureBatch = (study: string, id: string) => request<MixtureBatch>(route(study, `mixture-planning-batches/${encodeURIComponent(id)}`));
export const fetchMixtureBatchReportSource = (study: string, id: string) => request<ReportSourceDescriptor>(route(study, `mixture-planning-batches/${encodeURIComponent(id)}/report-source`));
export const recordMixtureObservations = (study: string, body: MixedObservationBatchRequest) => request<MixtureObservationResult>(route(study, "observations/batch"), body, "PUT");
export const replicateMixtureTrial = (study: string, trial: string, body: BayesianReplicateCreateRequest) => request<Record<string, unknown>>(route(study, `trials/${encodeURIComponent(trial)}/replicates`), body);
export const closeMixtureStudy = (study: string, body: BayesianStudyCloseRequest) => request<{ study: MixtureStudy }>(route(study, "close"), body);
export const abandonMixtureTrial = (study: string, trial: string, body: BayesianTrialAbandonRequest) => request<{ study_id: string; trial: MixtureTrial }>(route(study, `trials/${encodeURIComponent(trial)}/abandon`), body);
