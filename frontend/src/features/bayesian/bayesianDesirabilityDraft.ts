import type { BayesianKernelKind, BayesianStudyResponse, BayesianSurrogatePolicyRequest } from "../../api/types/bayesian";
import type { DesirabilityReviewRequest, DesirabilitySearch } from "../../api/types/bayesianDesirability";
import { parseBoKernelKind } from "./boKernelPolicy";
import { strictBoNumber } from "./boNoisePolicy";

export interface DesirabilityModelDraft {
  responseId: string;
  kernel: BayesianKernelKind;
  noise: BayesianSurrogatePolicyRequest["noise_mode"];
  fixedSd: string;
  initial: string;
  lower: string;
  upper: string;
}
export interface DesirabilityDraft {
  models: DesirabilityModelDraft[];
  aggregation: "retain_raw" | "exact_replicates";
  xi: string;
  totalBudget: string;
  seed: string;
  timeMs: string;
  modelEvaluations: string;
  batchSize: string;
  sampleCount: string;
  momentBudget: string;
  candidateBudget: string;
  q1CandidateBudget: string;
  candidateCount: string;
  localStarts: string;
  localIterations: string;
  modelIterations: string;
  minDistance: string;
  fitPolicy: "legacy" | "bounded_multiscale_starts_v1";
  deterministicStarts: string;
  randomRestarts: string;
}
export const defaultDesirabilitySearch: DesirabilitySearch = {
  random_seed: 42, candidate_count_per_step: 32, local_start_count_per_step: 0,
  max_iterations_per_step: 50, max_evaluations_total: 256, model_max_iterations: 60,
  model_max_evaluations: 1000, hyperparameter_restart_count: 0,
  time_budget_ms: 60000, jitter: 1e-8, duplicate_tolerance: 1e-6,
};
export function defaultDesirabilityDraft(study: BayesianStudyResponse | null): DesirabilityDraft {
  return {
    models: study?.objective.goal_type === "desirability" ? study.objective.responses.map(response => ({
      responseId: response.response_id, kernel: "matern_5_2", noise: "estimate", fixedSd: "",
      initial: "0.01", lower: "0.000001", upper: "1",
    })) : [],
    aggregation: "retain_raw", xi: "0.01", totalBudget: "40", seed: "42", timeMs: "60000", modelEvaluations: "1000",
    batchSize: "1", sampleCount: "64", momentBudget: "8192", candidateBudget: "1024", minDistance: "0",
    q1CandidateBudget: "256", candidateCount: "32", localStarts: "0", localIterations: "50", modelIterations: "60",
    fitPolicy: "legacy", deterministicStarts: "1", randomRestarts: "0",
  };
}
export type DesirabilityDraftErrors = Record<string, "integer" | "nonnegative" | "positive" | "bounds" | "budget" | "searchBudget" | "mapping">;
export function usesBatchDesirabilitySearch(study: BayesianStudyResponse, draft: DesirabilityDraft, purpose: "recommendation" | "planning" = "recommendation"): boolean {
  return purpose === "planning" || draft.batchSize !== "1" || draft.fitPolicy !== "legacy" ||
    (study.objective.goal_type === "desirability" && study.objective.curve_policy === "per_response_target_gaussian_or_ds_v1");
}
export function withDesirabilitySearchBudget(draft: DesirabilityDraft, value: string): DesirabilityDraft {
  // Preserve historical defaults until edited, then share the explicit budget
  // with the planning-model request that uses these same settings.
  return { ...draft, candidateBudget: value, q1CandidateBudget: value };
}
function integer(value: string, low: number, high: number): number | null {
  if (!/^\d+$/.test(value.trim())) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= low && parsed <= high ? parsed : null;
}
export function buildDesirabilityRequest(study: BayesianStudyResponse, draft: DesirabilityDraft, purpose: "recommendation" | "planning" = "recommendation"):
  { request: DesirabilityReviewRequest | null; errors: DesirabilityDraftErrors } {
  const errors: DesirabilityDraftErrors = {};
  if (study.objective.goal_type !== "desirability") return { request: null, errors: { models: "mapping" } };
  const versionedCurve = study.objective.curve_policy === "per_response_target_gaussian_or_ds_v1";
  const ids = study.objective.responses.map(response => response.response_id);
  if (ids.length !== draft.models.length || new Set(draft.models.map(model => model.responseId)).size !== ids.length ||
    draft.models.some(model => !ids.includes(model.responseId))) errors.models = "mapping";
  const models = draft.models.map(model => {
    const initial = strictBoNumber(model.initial), lower = strictBoNumber(model.lower), upper = strictBoNumber(model.upper);
    const fixed = model.noise === "fixed" ? strictBoNumber(model.fixedSd) : null;
    if (parseBoKernelKind(model.kernel) === null || !["estimate", "fixed", "near_noiseless"].includes(model.noise)) errors[`${model.responseId}:kernel`] = "mapping";
    if (initial === null || initial <= 0) errors[`${model.responseId}:initial`] = "positive";
    if (lower === null || lower <= 0) errors[`${model.responseId}:lower`] = "positive";
    if (upper === null || upper <= 0) errors[`${model.responseId}:upper`] = "positive";
    if (lower !== null && upper !== null && lower >= upper) errors[`${model.responseId}:lower`] = "bounds";
    if (initial !== null && lower !== null && upper !== null && (initial < lower || initial > upper)) errors[`${model.responseId}:initial`] = "bounds";
    if (model.noise === "fixed" && (fixed === null || fixed <= 0)) errors[`${model.responseId}:fixedSd`] = "positive";
    return { response_id: model.responseId, kernel: { kind: model.kernel }, surrogate: {
      noise_mode: model.noise, initial_noise_variance_scaled: initial!, lower_noise_variance_scaled: lower!, upper_noise_variance_scaled: upper!, fixed_noise_sd: fixed,
    } };
  });
  const xi = strictBoNumber(draft.xi);
  if (xi === null || xi < 0) errors.xi = "nonnegative";
  const total = integer(draft.totalBudget, 2, Math.min(200, study.recommendation_hard_trial_limit));
  const batchSize = integer(draft.batchSize, 1, 8);
  if (batchSize === null) errors.batchSize = "integer";
  if (total === null || total < study.trial_count + (purpose === "planning" ? 0 : (batchSize ?? 1))) errors.totalBudget = "budget";
  const samples = integer(draft.sampleCount, 16, 256), moments = integer(draft.momentBudget, 1, 65536);
  const batchSearch = usesBatchDesirabilitySearch(study, draft, purpose);
  const budgetKey = batchSearch ? "candidateBudget" : "q1CandidateBudget";
  const candidates = integer(draft[budgetKey], 32, 160000), distance = strictBoNumber(draft.minDistance);
  const pool = integer(draft.candidateCount, 32, 4096), localStarts = integer(draft.localStarts, 0, 16);
  const localIterations = integer(draft.localIterations, 1, 500), modelIterations = integer(draft.modelIterations, 1, 200);
  if (pool === null) errors.candidateCount = "integer";
  if (localStarts === null) errors.localStarts = "integer";
  if (localIterations === null) errors.localIterations = "integer";
  if (modelIterations === null) errors.modelIterations = "integer";
  if (candidates === null) errors[budgetKey] = "integer";
  else if (pool !== null && candidates < pool) errors[budgetKey] = "searchBudget";
  if (batchSize !== null && (purpose === "planning" || batchSize > 1 || draft.fitPolicy !== "legacy" || versionedCurve)) {
    if (samples === null) errors.sampleCount = "integer";
    if (moments === null) errors.momentBudget = "integer";
    if (distance === null || distance < 0) errors.minDistance = "nonnegative";
  }
  const seed = integer(draft.seed, 0, 2147483647), time = integer(draft.timeMs, 1000, 60000);
  const evaluations = integer(draft.modelEvaluations, 2, 2000);
  if (seed === null) errors.seed = "integer";
  if (time === null) errors.timeMs = "integer";
  if (evaluations === null) errors.modelEvaluations = "integer";
  const restarts = integer(draft.randomRestarts, 0, 3), starts = integer(draft.deterministicStarts, 1, 3);
  if (restarts === null) errors.randomRestarts = "integer";
  if (!["legacy", "bounded_multiscale_starts_v1"].includes(draft.fitPolicy)) errors.fitPolicy = "mapping";
  if (draft.fitPolicy !== "legacy" && starts === null) errors.deterministicStarts = "integer";
  if (!["retain_raw", "exact_replicates"].includes(draft.aggregation)) errors.aggregation = "mapping";
  if (Object.keys(errors).length) return { request: null, errors };
  const common = {
    expected_history_revision_id: study.observation_history.history_revision_id,
    expected_history_sha256: study.observation_history.observation_history_sha256,
    response_models: models, observation_policy: { mode: draft.aggregation, nearby_tolerances: null, nearby_units: "normalized" as const },
    xi_desirability: xi!, total_trial_budget: total!,
    search: { ...defaultDesirabilitySearch, random_seed: seed!, time_budget_ms: time!, model_max_evaluations: evaluations!, hyperparameter_restart_count: restarts!,
      candidate_count_per_step: pool!, local_start_count_per_step: localStarts!, max_iterations_per_step: localIterations!,
      model_max_iterations: modelIterations!, max_evaluations_total: candidates! },
  };
  if (versionedCurve) return { errors, request: {
    ...common, schema_version: 7, batch_size: batchSize!,
    fit_policy: draft.fitPolicy === "legacy" ? null : { kind: draft.fitPolicy, deterministic_start_count: starts! },
    batch_options: { sample_count: samples!, max_moment_evaluations: moments!, min_batch_distance_normalized: distance! },
    search: { ...common.search, max_evaluations_total: candidates! },
  } };
  if (draft.fitPolicy !== "legacy") return { errors, request: {
    ...common, schema_version: 6, batch_size: batchSize!,
    fit_policy: { kind: draft.fitPolicy, deterministic_start_count: starts! },
    batch_options: { sample_count: samples!, max_moment_evaluations: moments!, min_batch_distance_normalized: distance! },
    search: { ...common.search, max_evaluations_total: candidates! },
  } };
  return { errors, request: batchSize === 1 && purpose === "recommendation" ? { ...common, schema_version: 4, batch_size: 1 } : {
    ...common, schema_version: 5, batch_size: batchSize!,
    batch_options: { sample_count: samples!, max_moment_evaluations: moments!, min_batch_distance_normalized: distance! },
    search: { ...common.search, max_evaluations_total: candidates! },
  } };
}
