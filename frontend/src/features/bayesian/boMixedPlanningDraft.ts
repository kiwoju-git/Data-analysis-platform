import type { BayesianKernelKind, BayesianSurrogatePolicyRequest } from "../../api/types/bayesian";
import type { AugmentationPolicy } from "../../api/types/boAugmentation";
import type { EvaluatedMixedCandidateRow, MixedActualPoint, MixedBatchResponse, MixedCandidatePage, MixedCandidateRow, MixedFitOptions, MixedModelDetail, MixedSelectionRequest, MixedSelectionResponse, MixedSourceRequest, MixedStudyResponse } from "../../api/types/boMixed";
import type { ReportSourceDescriptor } from "../../api/types/reports";
import { isReportSourceDescriptor } from "../../managedReportSource";
import { strictBoNumber } from "./boNoisePolicy";
import { defaultDesirabilitySearch, type DesirabilityModelDraft } from "./bayesianDesirabilityDraft";
import { isMixedCategory, validateMixedCoordinates } from "./boMixedDraft";
import { planningHash, planningId, planningInteger } from "./boPlanningDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";
import { modelFreeAugmentation } from "./boAugmentationDraft";
import { decimalLatticeValue, isRsmOnLattice } from "../../doe/rsmRegion";

export interface MixedFitDraft {
  models: DesirabilityModelDraft[]; aggregation: "retain_raw" | "exact_replicates";
  xi: string; seed: string; seconds: string; evaluations: string; starts: string; restarts: string; moments: string;
}
export interface MixedSelectionDraft {
  kind: "manual_ordered" | "augmentation"; policy: AugmentationPolicy; batchSize: string; budget: string;
  distance: string; samples: string; evaluations: string; moments: string; seconds: string;
}
export const mixedSource = (study: MixedStudyResponse): MixedSourceRequest => ({ expected_study_version_id: study.study_version_id,
  expected_definition_sha256: study.definition_sha256, expected_history_revision_id: study.observation_history.history_revision_id,
  expected_history_sha256: study.observation_history.observation_history_sha256, expected_trial_count: study.trial_count });
export const initialMixedFit = (study: MixedStudyResponse): MixedFitDraft => ({ models: study.objective.responses.map(response => ({
  responseId: response.response_id, kernel: "matern_5_2", noise: "estimate", fixedSd: "", initial: ".01", lower: ".000001", upper: "1",
})), aggregation: "retain_raw", xi: ".01", seed: "42", seconds: "60", evaluations: "1000", starts: "3", restarts: "0", moments: "8192" });
export const initialMixedSelection = (): MixedSelectionDraft => ({ kind: "manual_ordered", policy: "greedy_mixed_maximin_v1", batchSize: "2", budget: "200", distance: "0", samples: "64", evaluations: "100000", moments: "65536", seconds: "60" });

export function mixedFitOptions(study: MixedStudyResponse, draft: MixedFitDraft): MixedFitOptions | null {
  if (draft.models.length !== study.objective.responses.length || new Set(draft.models.map(model => model.responseId)).size !== draft.models.length) return null;
  const responseModels: MixedFitOptions["response_models"] = [];
  for (const model of draft.models) {
    const initial = strictBoNumber(model.initial), lower = strictBoNumber(model.lower), upper = strictBoNumber(model.upper), fixed = model.noise === "fixed" ? strictBoNumber(model.fixedSd) : null;
    if (!study.objective.responses.some(response => response.response_id === model.responseId) || !(["matern_5_2", "matern_3_2", "gaussian", "exponential"] as BayesianKernelKind[]).includes(model.kernel) ||
      !(["estimate", "fixed", "near_noiseless"] as BayesianSurrogatePolicyRequest["noise_mode"][]).includes(model.noise) ||
      initial === null || lower === null || upper === null || lower <= 0 || lower >= upper || initial < lower || initial > upper || (model.noise === "fixed" && (fixed === null || fixed <= 0))) return null;
    responseModels.push({ response_id: model.responseId, kernel: { kind: model.kernel }, surrogate: { noise_mode: model.noise,
      initial_noise_variance_scaled: initial, lower_noise_variance_scaled: lower, upper_noise_variance_scaled: upper, fixed_noise_sd: fixed } });
  }
  const xi = strictBoNumber(draft.xi), seed = planningInteger(draft.seed, 0, 2147483647), seconds = planningInteger(draft.seconds, 1, 60), evaluations = planningInteger(draft.evaluations, 2, 2000),
    starts = planningInteger(draft.starts, 1, 3), restarts = planningInteger(draft.restarts, 0, 3), moments = planningInteger(draft.moments, 1, 65536);
  if (xi === null || xi < 0 || seed === null || seconds === null || evaluations === null || starts === null || restarts === null || moments === null || !["retain_raw", "exact_replicates"].includes(draft.aggregation)) return null;
  return { response_models: responseModels, observation_policy: { mode: draft.aggregation, nearby_tolerances: null, nearby_units: "normalized" }, xi_desirability: xi,
    search: { ...defaultDesirabilitySearch, random_seed: seed, time_budget_ms: seconds * 1000, model_max_evaluations: evaluations, hyperparameter_restart_count: restarts },
    fit_policy: { policy: "bounded_typed_factor_starts_v1", deterministic_start_count: starts }, max_moment_evaluations: moments };
}
export function mixedFitDraftFromModel(model: MixedModelDetail): MixedFitDraft {
  return { models: model.fit.response_models.map(response => ({ responseId: response.response_id, kernel: response.kernel.kind, noise: response.surrogate.noise_mode,
    fixedSd: response.surrogate.fixed_noise_sd === null ? "" : String(response.surrogate.fixed_noise_sd), initial: String(response.surrogate.initial_noise_variance_scaled), lower: String(response.surrogate.lower_noise_variance_scaled), upper: String(response.surrogate.upper_noise_variance_scaled) })),
    aggregation: model.fit.observation_policy.mode, xi: String(model.fit.xi_desirability), seed: String(model.fit.search.random_seed), seconds: String(model.fit.search.time_budget_ms / 1000), evaluations: String(model.fit.search.model_max_evaluations),
    starts: String(model.fit.fit_policy.deterministic_start_count), restarts: String(model.fit.search.hyperparameter_restart_count), moments: String(model.fit.max_moment_evaluations) };
}
export function validMixedModel(value: MixedModelDetail, study: MixedStudyResponse): boolean {
  return !!value && value.schema_version === 2 && value.study_id === study.study_id && value.study_version_id === study.study_version_id && value.definition_sha256 === study.definition_sha256 &&
    planningId(value.model_id) && planningId(value.source_history_revision_id) && [value.snapshot_sha256, value.config_sha256, value.history_sha256].every(planningHash) && value.model_reusable_without_refit === true &&
    sameDesirabilityJson(value.objective, study.objective) && Array.isArray(value.response_models) && value.response_models.length === study.objective.responses.length &&
    new Set(value.response_models.map(response => response.response_id)).size === value.response_models.length && value.response_models.every(response => study.objective.responses.some(item => item.response_id === response.response_id) &&
      response.model?.schema_version === 6 && response.model.policy_version === "bo_mixed_noise_latent_v1") && Array.isArray(value.warnings) && value.warnings.every(warning => typeof warning === "string");
}
export const currentMixedModel = (model: MixedModelDetail, study: MixedStudyResponse) => validMixedModel(model, study) && model.source_is_current && model.source_history_revision_id === study.observation_history.history_revision_id && model.history_sha256 === study.observation_history.observation_history_sha256;
export function sameMixedExecutableInput(input: MixedActualPoint, actual: MixedActualPoint, factors: MixedStudyResponse["factors"]): boolean {
  if (!input || !actual || Object.keys(input).length !== factors.length || Object.keys(actual).length !== factors.length) return false;
  return factors.every(factor => {
    const supplied = input[factor.factor_id], executed = actual[factor.factor_id];
    if (isMixedCategory(factor)) return typeof supplied === "string" && supplied === executed && factor.levels.includes(supplied);
    if (typeof supplied !== "number" || typeof executed !== "number" || !Number.isFinite(supplied) || supplied < factor.low || supplied > factor.high) return false;
    if (factor.domain_kind !== "discrete_numeric") return supplied === executed;
    if (!factor.step || !isRsmOnLattice(supplied, factor.low, factor.step)) return false;
    // The server validates the same decimal lattice before recording its exact
    // executable level. Input residue is preserved, not treated as a new level.
    const index = Math.round((supplied - factor.low) / factor.step);
    return decimalLatticeValue(factor.low, factor.step, index) === executed;
  });
}
export function validMixedRow(row: MixedCandidateRow, study: MixedStudyResponse): boolean {
  return !!row && row.schema_version === 2 && planningHash(row.row_id) && Number.isSafeInteger(row.source_row_number) && row.source_row_number > 0 &&
    row.coordinate_encoding === "numeric_normalized_category_index_v1" && typeof row.ordinal_rank_distance === "boolean" &&
    row.distance_policy === (row.ordinal_rank_distance ? "numeric_normalized_nominal_hamming_ordinal_rank_v1" : "numeric_normalized_category_hamming_v1") &&
    validateMixedCoordinates(row.actual_coordinates, row.encoded_coordinates, study.factors) && sameMixedExecutableInput(row.input_coordinates, row.actual_coordinates, study.factors) &&
    typeof row.novel === "boolean" && typeof row.constraints_satisfied === "boolean" && row.eligible === (row.novel && row.constraints_satisfied) &&
    (row.nearest_existing_distance === null || Number.isFinite(row.nearest_existing_distance) && row.nearest_existing_distance >= 0);
}
export function validMixedPage(page: MixedCandidatePage, study: MixedStudyResponse): boolean {
  const revision = page?.revision;
  return !!revision && revision.schema_version === 3 && planningId(revision.revision_id) && planningId(revision.candidate_set_id) && revision.study_version_id === study.study_version_id && revision.definition_sha256 === study.definition_sha256 &&
    [revision.rows_sha256, revision.config_sha256, revision.history_sha256, revision.excluded_coordinates_sha256].every(planningHash) &&
    (revision.model_id === null ? revision.model_sha256 === null : planningId(revision.model_id) && planningHash(revision.model_sha256)) &&
    Number.isFinite(revision.duplicate_tolerance) && revision.duplicate_tolerance >= 1e-12 && revision.duplicate_tolerance <= .1 && typeof revision.ordinal_rank_distance === "boolean" &&
    Number.isInteger(revision.row_count) && revision.row_count >= 1 && revision.row_count <= 10000 && Number.isInteger(revision.eligible_count) && revision.eligible_count >= 0 && revision.eligible_count <= revision.row_count &&
    Number.isInteger(page.offset) && page.offset >= 0 && page.offset <= revision.row_count && Number.isInteger(page.limit) && page.limit >= 1 && page.limit <= 100 && Array.isArray(page.items) &&
    page.items.length === Math.min(page.limit, revision.row_count - page.offset) && new Set(page.items.map(row => row.row_id)).size === page.items.length && page.items.every(row => validMixedRow(row, study) && row.ordinal_rank_distance === revision.ordinal_rank_distance);
}
export function validMixedPrediction(row: EvaluatedMixedCandidateRow, study: MixedStudyResponse): boolean {
  return validMixedRow(row, study) && row.prediction_source === "completed_observations_base_posterior" &&
    Number.isFinite(row.desirability_moments?.mean) && row.desirability_moments.mean >= 0 && row.desirability_moments.mean <= 1 && Number.isFinite(row.desirability_moments.variance) && row.desirability_moments.variance >= 0 && row.desirability_moments.variance <= .25 &&
    (row.acquisition === null || Number.isFinite(row.acquisition?.value) && row.acquisition.value >= 0 && row.acquisition.value <= 1) && Array.isArray(row.response_predictions) && row.response_predictions.length === study.objective.responses.length &&
    new Set(row.response_predictions.map(response => response.response_id)).size === row.response_predictions.length && row.response_predictions.every(response => study.objective.responses.some(item => item.response_id === response.response_id) &&
      [response.mean_raw, response.latent_standard_deviation_raw, response.predictive_standard_deviation_raw].every(Number.isFinite) && response.latent_standard_deviation_raw >= 0 && response.predictive_standard_deviation_raw >= response.latent_standard_deviation_raw);
}
export function mixedSelectionRequest(study: MixedStudyResponse, page: MixedCandidatePage | null, model: MixedModelDetail | null, ids: string[], draft: MixedSelectionDraft, requestId: string): MixedSelectionRequest | null {
  if (!page || !validMixedPage(page, study) || !page.revision.source_is_current || page.revision.source_trial_count !== study.trial_count || page.revision.history_sha256 !== study.observation_history.observation_history_sha256 ||
    page.revision.source_history_revision_id !== study.observation_history.history_revision_id || study.status !== "active" || study.pending_trial_count !== 0) return null;
  const manual = draft.kind === "manual_ordered", free = !manual && modelFreeAugmentation(draft.policy), count = manual ? ids.length : planningInteger(draft.batchSize, 1, 8),
    budget = planningInteger(draft.budget, 2, 200), samples = planningInteger(draft.samples, 16, 256), evaluations = planningInteger(draft.evaluations, 1, 100000), moments = planningInteger(draft.moments, 1, 65536), seconds = planningInteger(draft.seconds, 1, 60), distance = strictBoNumber(draft.distance);
  if (count === null || count < 1 || count > 8 || count > page.revision.eligible_count || budget === null || budget < study.trial_count + count || samples === null || evaluations === null || moments === null || seconds === null || distance === null || distance < 0 || distance > Math.sqrt(study.factors.length) ||
    (!free && (!model || !currentMixedModel(model, study))) || (!manual && draft.policy === "greedy_incremental_maxpro_v1") || (manual && (new Set(ids).size !== count || !ids.every(planningHash)))) return null;
  return { ...mixedSource(study), schema_version: 3, request_id: requestId, kind: draft.kind, candidate_revision_id: page.revision.revision_id, expected_rows_sha256: page.revision.rows_sha256,
    model_id: free ? null : model!.model_id, expected_model_sha256: free ? null : model!.snapshot_sha256, row_ids: manual ? [...ids] : [], policy: manual ? null : draft.policy,
    batch_size: count, total_trial_budget: budget, duplicate_tolerance: page.revision.duplicate_tolerance, ordinal_rank_distance: page.revision.ordinal_rank_distance,
    min_batch_distance: distance, sample_count: samples, max_evaluations: evaluations, max_moment_evaluations: moments, time_budget_ms: seconds * 1000 };
}
export const mixedSelectedRows = (selection: Pick<MixedSelectionResponse, "calculation">) => selection.calculation.schema_version === 2 ? selection.calculation.items : selection.calculation.selected_rows;
export function validMixedSelection(value: MixedSelectionResponse, study: MixedStudyResponse, request?: MixedSelectionRequest): boolean {
  if (!value || value.schema_version !== 3 || value.study_id !== study.study_id || value.study_version_id !== study.study_version_id || !planningId(value.selection_id) || ![value.config_sha256, value.result_sha256].every(planningHash) ||
    value.request?.expected_definition_sha256 !== study.definition_sha256 || value.request.expected_study_version_id !== study.study_version_id || value.model_id !== value.request.model_id || value.candidate_revision_id !== value.request.candidate_revision_id ||
    (request && !sameDesirabilityJson(value.request, request)) || value.calculation?.model_refit !== false) return false;
  const rows = mixedSelectedRows(value);
  if (!Array.isArray(rows) || rows.length !== value.request.batch_size || rows.length < 1 || rows.length > 8 || new Set(rows.map(row => row.row_id)).size !== rows.length || rows.some(row => !validMixedRow(row, study) || !row.eligible || row.ordinal_rank_distance !== value.request.ordinal_rank_distance)) return false;
  if (value.request.kind === "manual_ordered") return value.calculation.schema_version === 2 && value.calculation.selection_policy === "manual_ordered_mixed_model_v1" && value.calculation.items.every((row, index) =>
    validMixedPrediction(row, study) && row.row_id === value.request.row_ids[index] && row.rank === index + 1 && Number.isFinite(row.planning.score) && row.planning.score >= 0 && row.planning.sampler.coordinate_encoding === "numeric_normalized_category_index_v1");
  if (value.calculation.schema_version !== 3) return false;
  const trace = value.calculation.augmentation;
  return trace?.policy === value.request.policy && trace.model_refit === false && trace.fantasy_observations === false && trace.source.model_snapshot_id === value.model_id && trace.source.model_snapshot_sha256 === value.request.expected_model_sha256 &&
    trace.source.candidate_revision_id === value.candidate_revision_id && trace.source.candidate_revision_sha256 === value.request.expected_rows_sha256 && trace.source.history_sha256 === value.request.expected_history_sha256 &&
    trace.selected_row_ids.length === rows.length && trace.steps.length === rows.length && trace.steps.every((step, index) => step.rank === index + 1 && step.row_id === rows[index].row_id && trace.selected_row_ids[index] === step.row_id && Number.isFinite(step.score)) &&
    rows.every(row => value.model_id === null ? !("response_predictions" in row) : "response_predictions" in row && validMixedPrediction(row, study));
}
export function validMixedBatch(batch: MixedBatchResponse, study: MixedStudyResponse, id: string): boolean {
  if (!batch || batch.result_schema_version !== 10 || batch.config_schema_version !== 10 || batch.model_schema_version !== 10 || batch.item_schema_version !== 5 || batch.method_version !== "0.15.0" || batch.batch_policy !== "source_owned_mixed_planning_v1" ||
    batch.batch_id !== id || batch.source?.selection_id !== id || batch.study_id !== study.study_id || batch.study_version_id !== study.study_version_id || batch.definition_sha256 !== study.definition_sha256 || !sameDesirabilityJson(batch.objective, study.objective) ||
    ![batch.config_sha256, batch.result_sha256, batch.source.rows_sha256, batch.source.selection_config_sha256, batch.source.selection_result_sha256].every(planningHash) || batch.source.model_id !== batch.selection_request?.model_id || batch.source.model_sha256 !== batch.selection_request.expected_model_sha256 ||
    batch.source.candidate_revision_id !== batch.selection_request.candidate_revision_id || batch.source.rows_sha256 !== batch.selection_request.expected_rows_sha256 || batch.source_history_revision_id !== batch.selection_request.expected_history_revision_id || batch.source_observation_history_sha256 !== batch.selection_request.expected_history_sha256 ||
    !validMixedSelection({ schema_version: 3, selection_id: id, study_id: batch.study_id, study_version_id: batch.study_version_id, model_id: batch.source.model_id, candidate_revision_id: batch.source.candidate_revision_id,
      config_sha256: batch.source.selection_config_sha256, result_sha256: batch.source.selection_result_sha256, request: batch.selection_request, calculation: batch.calculation, created_at: batch.created_at, source_is_current: false, confirmed_batch_id: id }, study) ||
    !Array.isArray(batch.items) || batch.items.length !== batch.batch_size || batch.batch_size !== batch.selection_request.batch_size || new Set(batch.items.map(item => item.trial.trial_id)).size !== batch.batch_size) return false;
  const rows = mixedSelectedRows(batch);
  return batch.items.every((item, index) => item.batch_id === id && item.rank === index + 1 && planningId(item.item_id) && item.trial.trial_id === item.current_trial.trial_id && item.trial.coordinates_sha256 === item.current_trial.coordinates_sha256 &&
    sameDesirabilityJson(item.trial.actual_coordinates, rows[index].actual_coordinates) && sameDesirabilityJson(item.trial.encoded_coordinates, rows[index].encoded_coordinates) && sameDesirabilityJson(item.current_trial.actual_coordinates, item.trial.actual_coordinates) &&
    validateMixedCoordinates(item.current_trial.actual_coordinates, item.current_trial.encoded_coordinates, study.factors));
}
export function validMixedReportSource(descriptor: ReportSourceDescriptor, batch: MixedBatchResponse): boolean {
  if (!isReportSourceDescriptor(descriptor) || descriptor.source.kind !== "bayesian_history_revision") return false;
  const source = descriptor.source;
  return source.study_id === batch.study_id && source.study_version_id === batch.study_version_id && source.definition_sha256 === batch.definition_sha256 && source.history_revision_id === batch.source_history_revision_id && source.expected_source_sha256 === batch.source_observation_history_sha256 &&
    source.attachment.kind === "batch" && source.attachment.batch_id === batch.batch_id && source.attachment.result_payload_sha256 === batch.result_sha256;
}
export function mixedDefaultPoint(study: MixedStudyResponse): Record<string, string> {
  return Object.fromEntries(study.factors.map(factor => [factor.factor_id, isMixedCategory(factor) ? factor.levels[0] : String(factor.low)]));
}
export function mixedProfilePoints(study: MixedStudyResponse, hold: MixedActualPoint, factorId: string): MixedActualPoint[] | null {
  const factor = study.factors.find(item => item.factor_id === factorId);
  if (!factor) return null;
  let values: (string | number)[];
  if (isMixedCategory(factor)) values = factor.levels;
  else if (factor.domain_kind === "discrete_numeric") {
    const last = Math.round((factor.high - factor.low) / factor.step!), count = last + 1;
    if (count > 100) return null;
    const grid = Array.from({ length: count }, (_, index) => decimalLatticeValue(factor.low, factor.step!, index));
    if (grid.some(value => value === null)) return null;
    values = grid as number[];
  } else values = Array.from({ length: 21 }, (_, index) => index === 20 ? factor.high : factor.low + (factor.high - factor.low) * index / 20);
  return values.map(value => ({ ...hold, [factorId]: value }));
}
