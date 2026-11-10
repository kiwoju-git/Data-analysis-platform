import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { BoLooView } from "./boLoo";
import type { AugmentationPolicy } from "./types/boAugmentation";

export interface AutoStrategyView {
  schema_version: 1; decision_only: true; selection_created: false; apply_allowed: boolean;
  diagnostic: BoLooView; decision_sha256: string;
  decision: {
    schema_version: 1; policy: "conditional_loo_any_low_explore_else_refine_v1";
    threshold: number; comparison: "strictly_less_than"; recommended_policy: AugmentationPolicy | null;
    reason: "r_squared_unavailable" | "any_response_below_threshold" | "all_responses_meet_threshold";
    response_ids: string[]; below_threshold_response_ids: string[]; unavailable_response_ids: string[];
    ordinal_rank_distance_requires_consent: boolean; warnings: string[];
  };
}
export interface AutoStrategySource {
  model_id: string; snapshot_sha256: string; config_sha256: string; history_sha256: string;
  source_history_revision_id: string; source_is_current: boolean;
  objective: { responses: { response_id: string; name: string; unit: string | null }[] };
}
const modelPath = (studyId: string, modelId: string, mixed: boolean) => `${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(studyId)}/${mixed ? "mixed-planning-models" : "planning-models"}/${encodeURIComponent(modelId)}`;

export async function requestAutoStrategy(studyId: string, model: AutoStrategySource, mixed: boolean, threshold: number, signal: AbortSignal): Promise<AutoStrategyView> {
  const response = await fetchApi(`${modelPath(studyId, model.model_id, mixed)}/auto-strategy`, {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, signal,
    body: JSON.stringify({ expected_model_sha256: model.snapshot_sha256, expected_history_sha256: model.history_sha256, r_squared_threshold: threshold }),
  });
  if (!response.ok) throw await apiRequestError(response, "bayesian_auto_strategy_invalid");
  return await response.json() as AutoStrategyView;
}

export async function verifyAutoStrategySource(studyId: string, model: AutoStrategySource, mixed: boolean, signal: AbortSignal): Promise<boolean> {
  const response = await fetchApi(modelPath(studyId, model.model_id, mixed), { signal });
  if (!response.ok) throw await apiRequestError(response, "bayesian_auto_strategy_invalid");
  const current = await response.json() as AutoStrategySource;
  const matches = current.source_is_current === true && current.model_id === model.model_id && current.snapshot_sha256 === model.snapshot_sha256
    && current.history_sha256 === model.history_sha256 && current.config_sha256 === model.config_sha256
    && current.source_history_revision_id === model.source_history_revision_id;
  if (!matches) return false;
  const studyResponse = await fetchApi(`${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(studyId)}`, { signal });
  if (!studyResponse.ok) throw await apiRequestError(studyResponse, "bayesian_auto_strategy_invalid");
  const study = await studyResponse.json() as { status: string; pending_trial_count: number; observation_history: { history_revision_id: string; observation_history_sha256: string } };
  return study.status === "active" && study.pending_trial_count === 0
    && study.observation_history.history_revision_id === model.source_history_revision_id
    && study.observation_history.observation_history_sha256 === model.history_sha256;
}

export function validAutoStrategy(view: AutoStrategyView, studyId: string, model: AutoStrategySource, kinds: readonly string[], threshold: number): boolean {
  const diagnostic = view?.diagnostic, decision = view?.decision, calculation = diagnostic?.calculation;
  if (view?.schema_version !== 1 || view.decision_only !== true || view.selection_created !== false || typeof view.apply_allowed !== "boolean"
    || !/^[a-f0-9]{64}$/.test(view.decision_sha256) || !decision || decision.schema_version !== 1
    || decision.policy !== "conditional_loo_any_low_explore_else_refine_v1" || decision.comparison !== "strictly_less_than" || decision.threshold !== threshold
    || diagnostic?.study_id !== studyId || diagnostic.model_id !== model.model_id || diagnostic.model_sha256 !== model.snapshot_sha256
    || diagnostic.history_sha256 !== model.history_sha256 || diagnostic.config_sha256 !== model.config_sha256
    || diagnostic.source_history_revision_id !== model.source_history_revision_id || typeof diagnostic.source_is_current !== "boolean"
    || calculation?.policy !== "fixed_full_fit_parameters_row_loo_v1" || calculation.model_refit !== false || calculation.auto_routing_applied !== false
    || !Array.isArray(calculation.responses)) return false;
  const rows = calculation.responses, ids = rows.map(row => row.response_id);
  const same = (left: unknown, right: unknown) => JSON.stringify(left) === JSON.stringify(right);
  if (!same(ids, model.objective.responses.map(row => row.response_id)) || !same(decision.response_ids, ids)
    || rows.some(row => row.r_squared !== null && (!Number.isFinite(row.r_squared) || row.r_squared > 1))) return false;
  const unavailable = rows.filter(row => row.r_squared === null).map(row => row.response_id);
  const below = rows.filter(row => row.r_squared !== null && row.r_squared < threshold).map(row => row.response_id);
  const expected = unavailable.length ? null : below.length ? kinds.every(kind => kind === "continuous")
    ? "greedy_incremental_maxpro_v1" : "greedy_mixed_maximin_v1" : "refine_ei_alternating_desirability_response_sd_v2";
  return decision.recommended_policy === expected && same(decision.below_threshold_response_ids, below) && same(decision.unavailable_response_ids, unavailable)
    && decision.reason === (unavailable.length ? "r_squared_unavailable" : below.length ? "any_response_below_threshold" : "all_responses_meet_threshold")
    && decision.ordinal_rank_distance_requires_consent === kinds.includes("ordinal") && (!view.apply_allowed || (diagnostic.source_is_current && expected !== null));
}
