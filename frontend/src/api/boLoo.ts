import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";

export interface BoLooPoint {
  trial_id: string; observation_index: number; observed: number; predicted: number; residual: number;
}
export interface BoLooResponse {
  response_id: string; raw_observation_count: number; effective_training_count: number; n_scored: number;
  rmse: number; r_squared: number | null; r_squared_reason: "constant_observations" | null; points: BoLooPoint[];
}
export interface BoLooView {
  schema_version: 1; study_id: string; model_id: string; model_sha256: string; config_sha256: string;
  source_history_revision_id: string; history_sha256: string; source_is_current: boolean; calculation_sha256: string;
  calculation: {
    schema_version: 1; policy: "fixed_full_fit_parameters_row_loo_v1";
    evaluation_unit: "individual_observed_trial"; normalization_policy: "frozen_full_fit_mean_scale";
    r_squared_policy: "one_minus_press_over_raw_centered_tss"; model_refit: false; auto_routing_applied: false;
    warnings: string[]; responses: BoLooResponse[];
  };
}
export async function requestBoLoo(studyId: string, modelId: string, modelHash: string, historyHash: string, mixed: boolean, signal: AbortSignal): Promise<BoLooView> {
  const family = mixed ? "mixed-planning-models" : "planning-models";
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(studyId)}/${family}/${encodeURIComponent(modelId)}/loo`, {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, signal,
    body: JSON.stringify({ expected_model_sha256: modelHash, expected_history_sha256: historyHash }),
  });
  if (!response.ok) throw await apiRequestError(response, "bayesian_loo_diagnostic_invalid");
  return await response.json() as BoLooView;
}
