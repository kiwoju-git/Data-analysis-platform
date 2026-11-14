import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { BoLooView } from "./boLoo";
import type { ReportSourceDescriptor } from "./types/reports";
import type { BayesianLinearConstraintRequest } from "./types/bayesian";

export interface BoViewSource {
  study_id: string; study_version_id: string; definition_sha256: string;
  model_id: string; model_sha256: string; model_config_sha256: string;
  history_revision_id: string; history_sha256: string;
}
export interface BoViewResponse { response_id: string; name: string; unit: string | null }
export interface BoProfilePoint {
  row_id: string; actual_coordinates: Record<string, number | string>; constraints_satisfied: boolean;
  prediction_source: "completed_observations_base_posterior";
  response_predictions: { response_id: string; mean_raw: number; latent_standard_deviation_raw: number; predictive_standard_deviation_raw: number }[];
  desirability_moments: { mean: number };
}
export interface BoProfileAxis {
  factor_id: string; name: string; unit: string | null; kind: "continuous" | "discrete_numeric" | "nominal" | "ordinal" | "mixture_component";
  available_level_count: number | null; points: BoProfilePoint[];
  path?: { policy: "excess_above_lower" | "deficit_below_upper" | "held_mixture_process_axis_v1"; feasible_interval: [number, number] | null; unavailable_reason: string | null } | null;
}
interface ViewPayloadBase { schema_version: 1 | 2; source: BoViewSource; model_refit: false; responses: BoViewResponse[] }
export interface BoMatrixPayload extends ViewPayloadBase {
  kind: "profiler_matrix"; policy: "source_locked_conditional_profiler_matrix_v1" | "source_locked_mixture_profiler_matrix_v1";
  mixture_domain?: Record<string, unknown> | null;
  holds: Record<string, number | string>; constraints: BayesianLinearConstraintRequest[];
  warnings: string[];
  axes: BoProfileAxis[]; point_count: number;
}
export interface BoLooPayload extends ViewPayloadBase {
  schema_version: 1;
  kind: "conditional_loo"; calculation: BoLooView["calculation"]; calculation_sha256: string;
}
export type BoViewPayload = BoMatrixPayload | BoLooPayload;
export type BoViewEvaluationRequest = {
  kind: "profiler_matrix"; expected_model_sha256: string; expected_history_sha256: string;
  holds: Record<string, number | string>; points_per_axis: number; time_budget_ms: number;
} | { kind: "conditional_loo"; expected_model_sha256: string; expected_history_sha256: string };
export interface BoViewReceipt { receipt_id: string; request_sha256: string; view_sha256: string; expires_at: string; payload: BoViewPayload }
export interface BoSaveViewRequest { request_id: string; receipt_id: string; expected_model_sha256: string; expected_request_sha256: string; expected_view_sha256: string }
export interface BoSavedViewSummary { schema_version: 1; view_id: string; source: BoViewSource; kind: BoViewPayload["kind"]; request_sha256: string; view_sha256: string; created_at: string }
export interface BoSavedView extends BoSavedViewSummary { evaluation_request: BoViewEvaluationRequest; payload: BoViewPayload }
const path = (studyId: string) => `${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(studyId)}`;
async function request<T>(url: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetchApi(url, { method: body === undefined ? "GET" : "POST", signal, headers: { Accept: "application/json", "Content-Type": "application/json" }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  if (!response.ok) throw await apiRequestError(response, "bayesian_view_request_failed");
  return await response.json() as T;
}
export const evaluateBoView = (studyId: string, modelId: string, body: BoViewEvaluationRequest, signal?: AbortSignal) => request<BoViewReceipt>(`${path(studyId)}/planning-models/${encodeURIComponent(modelId)}/view-evaluations`, body, signal);
export const saveBoView = (studyId: string, body: BoSaveViewRequest) => request<BoSavedView>(`${path(studyId)}/views`, body);
export const readBoView = (studyId: string, viewId: string) => request<BoSavedView>(`${path(studyId)}/views/${encodeURIComponent(viewId)}`);
export const listBoViews = (studyId: string) => request<{ items: BoSavedViewSummary[] }>(`${path(studyId)}/views`);
export const boViewReportSource = (studyId: string, viewId: string) => request<ReportSourceDescriptor>(`${path(studyId)}/views/${encodeURIComponent(viewId)}/report-source`);
