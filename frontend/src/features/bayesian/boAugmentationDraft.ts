import type { BayesianStudyResponse } from "../../api/types/bayesian";
import type { AugmentationBatchResponse, AugmentationCalculation, AugmentationPolicy, AugmentationSelectionRequest, AugmentationSelectionResponse } from "../../api/types/boAugmentation";
import type { CandidatePage, CandidateRow, PlanningModelDetail } from "../../api/types/boPlanning";
import type { MixedAugmentationCalculation, MixedSelectionRequest, MixedStudyResponse } from "../../api/types/boMixed";
import type { ReportSourceDescriptor } from "../../api/types/reports";
import { parseDoeResponseNumber } from "../../doe/doeResponsePaste";
import { isReportSourceDescriptor } from "../../managedReportSource";
import { currentPlanningModel, parsePlanningPoint, planningHash, planningId, planningInteger } from "./boPlanningDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";
import { validAutoStrategy } from "../../api/boAutoStrategy";

export interface AugmentationDraft {
  policy: AugmentationPolicy; batchSize: string; budget: string; distance: string;
  evaluations: string; moments: string; seconds: string;
}
export function augmentationFailureCode(caught: unknown): string {
  const code = caught instanceof Error ? caught.message : "";
  return /^(bayesian_[a-z0-9_]{1,110}|api_unreachable|api_contract_mismatch|validation_error)$/.test(code) ? code : "bayesian_augmentation_request_failed";
}
export function initialAugmentationDraft(study: BayesianStudyResponse): AugmentationDraft {
  return { policy: study.factors.every(factor => factor.domain_kind !== "discrete_numeric") ? "greedy_incremental_maxpro_v1" : "greedy_mixed_maximin_v1",
    batchSize: "2", budget: "200", distance: "0", evaluations: "100000", moments: "65536", seconds: "60" };
}
export function modelFreeAugmentation(policy: AugmentationPolicy): boolean {
  return policy === "greedy_incremental_maxpro_v1" || policy === "greedy_mixed_maximin_v1";
}
export const augmentationSource = (study: BayesianStudyResponse) => ({ expected_study_version_id: study.study_version_id,
  expected_definition_sha256: study.definition_sha256, expected_history_revision_id: study.observation_history.history_revision_id,
  expected_history_sha256: study.observation_history.observation_history_sha256, expected_trial_count: study.trial_count });
export function augmentationRequest(study: BayesianStudyResponse, page: CandidatePage | null, model: PlanningModelDetail | null,
  draft: AugmentationDraft, requestId: string): AugmentationSelectionRequest | null {
  if (!page || page.revision.schema_version !== 2 || !page.revision.source_is_current || page.revision.source_trial_count !== study.trial_count ||
    page.revision.study_version_id !== study.study_version_id || page.revision.definition_sha256 !== study.definition_sha256 ||
    page.revision.source_history_revision_id !== study.observation_history.history_revision_id || page.revision.history_sha256 !== study.observation_history.observation_history_sha256 ||
    study.status !== "active" || study.pending_trial_count !== 0 || study.objective.goal_type !== "desirability" || ![5, 6].includes(study.study_schema_version)) return null;
  const batch = planningInteger(draft.batchSize, 1, 8), budget = planningInteger(draft.budget, 2, 200),
    evaluations = planningInteger(draft.evaluations, 1, 100000), moments = planningInteger(draft.moments, 1, 65536),
    seconds = planningInteger(draft.seconds, 1, 60), distance = parseDoeResponseNumber(draft.distance), tolerance = page.revision.duplicate_tolerance;
  if (batch === null || budget === null || budget < study.trial_count + batch || evaluations === null || moments === null || seconds === null ||
    distance === null || distance < 0 || distance > Math.sqrt(study.factors.length) || !Number.isFinite(tolerance) || tolerance < 1e-12 || tolerance > .1 || page.revision.eligible_count < batch ||
    (draft.policy === "greedy_incremental_maxpro_v1" && study.factors.some(factor => factor.domain_kind === "discrete_numeric")) ||
    (!modelFreeAugmentation(draft.policy) && (!model || !currentPlanningModel(model, study)))) return null;
  return { ...augmentationSource(study), schema_version: 2, request_id: requestId, candidate_revision_id: page.revision.revision_id,
    expected_rows_sha256: page.revision.rows_sha256, model_id: modelFreeAugmentation(draft.policy) ? null : model!.model_id,
    expected_model_sha256: modelFreeAugmentation(draft.policy) ? null : model!.snapshot_sha256, policy: draft.policy,
    batch_size: batch, total_trial_budget: budget, duplicate_tolerance: tolerance, min_batch_distance_normalized: distance,
    max_evaluations: evaluations, max_moment_evaluations: moments, time_budget_ms: seconds * 1000 };
}
function validRow(row: CandidateRow, study: BayesianStudyResponse): boolean {
  if (!row || !planningHash(row.row_id) || !Number.isInteger(row.source_row_number) || row.source_row_number < 1 ||
    row.eligible !== (row.novel && row.constraints_satisfied) || typeof row.novel !== "boolean" || typeof row.constraints_satisfied !== "boolean" ||
    !(row.nearest_existing_distance === null || (Number.isFinite(row.nearest_existing_distance) && row.nearest_existing_distance >= 0)) ||
    !row.actual_coordinates || !row.normalized_coordinates) return false;
  const point = parsePlanningPoint(Object.fromEntries(Object.entries(row.actual_coordinates).map(([key, value]) => [key, String(value)])), study.factors);
  return point !== null && Object.keys(row.normalized_coordinates).length === study.factors.length && study.factors.every(factor => {
    const z = row.normalized_coordinates[factor.factor_id], expected = (point[factor.factor_id] - factor.low) / (factor.high - factor.low);
    return Number.isFinite(z) && z >= 0 && z <= 1 && Math.abs(z - expected) <= 32 * Number.EPSILON * Math.max(1, Math.abs(expected));
  });
}
export function validAugmentationPage(page: CandidatePage, study: BayesianStudyResponse): boolean {
  const r = page?.revision;
  return !!r && r.schema_version === 2 && planningId(r.revision_id) && planningId(r.candidate_set_id) &&
    r.study_version_id === study.study_version_id && r.definition_sha256 === study.definition_sha256 && planningId(r.source_history_revision_id) &&
    [r.rows_sha256, r.config_sha256, r.history_sha256, r.excluded_coordinates_sha256].every(planningHash) &&
    (r.model_id === null ? r.model_sha256 === null : planningId(r.model_id) && planningHash(r.model_sha256)) &&
    Number.isFinite(r.duplicate_tolerance) && r.duplicate_tolerance >= 1e-12 && r.duplicate_tolerance <= .1 &&
    Number.isInteger(r.row_count) && r.row_count >= 1 && r.row_count <= 10000 && Number.isInteger(r.eligible_count) && r.eligible_count >= 0 && r.eligible_count <= r.row_count &&
    Number.isInteger(page.offset) && page.offset >= 0 && page.offset <= r.row_count && Number.isInteger(page.limit) && page.limit >= 1 && page.limit <= 100 &&
    Array.isArray(page.items) && page.items.length === Math.min(page.limit, r.row_count - page.offset) &&
    new Set(page.items.map(row => row.row_id)).size === page.items.length && page.items.every(row => validRow(row, study));
}
export function validAugmentationCalculation(value: AugmentationCalculation, request: AugmentationSelectionRequest, study: BayesianStudyResponse): boolean {
  const trace = value?.augmentation;
  if (!validSavedAutoEvidence(value, request, study) || value.model_refit !== false || !trace || trace.schema_version !== 1 || trace.model_refit !== false || trace.fantasy_observations !== false ||
    trace.policy !== request.policy || !trace.source || trace.source.model_snapshot_id !== request.model_id || trace.source.model_snapshot_sha256 !== request.expected_model_sha256 ||
    trace.source.candidate_revision_id !== request.candidate_revision_id || trace.source.candidate_revision_sha256 !== request.expected_rows_sha256 || trace.source.history_sha256 !== request.expected_history_sha256 ||
    !Array.isArray(trace.steps) || trace.steps.length !== request.batch_size || !Array.isArray(trace.selected_row_ids) || trace.selected_row_ids.length !== request.batch_size ||
    !Array.isArray(value.selected_rows) || value.selected_rows.length !== request.batch_size || new Set(trace.selected_row_ids).size !== request.batch_size ||
    !Number.isInteger(value.prediction_evaluations) || value.prediction_evaluations < 0 || value.prediction_evaluations > value.max_moment_evaluations ||
    !Number.isInteger(trace.evaluations) || trace.evaluations < 1 || trace.evaluations > trace.max_evaluations ||
    trace.max_evaluations !== request.max_evaluations || value.max_moment_evaluations !== request.max_moment_evaluations ||
    !Array.isArray(trace.warnings) || trace.warnings.some(warning => typeof warning !== "string")) return false;
  return trace.steps.every((step, index) => {
    const row = value.selected_rows[index];
    if (step.rank !== index + 1 || step.row_id !== trace.selected_row_ids[index] || row.row_id !== step.row_id || !validRow(row, study) || !row.eligible ||
      !Number.isFinite(step.score) || !Number.isFinite(step.nearest_existing_distance) || step.nearest_existing_distance < 0 ||
      !(step.nearest_selected_distance === null || (Number.isFinite(step.nearest_selected_distance) && step.nearest_selected_distance >= 0)) ||
      !(step.competitive_threshold === null || (Number.isFinite(step.competitive_threshold) && step.competitive_threshold >= 0 && step.competitive_threshold <= 1))) return false;
    if (modelFreeAugmentation(request.policy)) return !("response_predictions" in row) && value.prediction_evaluations === 0;
    if (!("response_predictions" in row) || study.objective.goal_type !== "desirability" || row.prediction_source !== "completed_observations_base_posterior") return false;
    return Number.isFinite(row.desirability_moments.mean) && row.desirability_moments.mean >= 0 && row.desirability_moments.mean <= 1 &&
      Number.isFinite(row.desirability_moments.variance) && row.desirability_moments.variance >= 0 && row.desirability_moments.variance <= .25 &&
      (row.acquisition === null || (Number.isFinite(row.acquisition.value) && row.acquisition.value >= 0 && row.acquisition.value <= 1)) &&
      row.response_predictions.length === study.objective.responses.length && new Set(row.response_predictions.map(prediction => prediction.response_id)).size === row.response_predictions.length &&
      row.response_predictions.every(prediction => study.objective.goal_type === "desirability" && study.objective.responses.some(response => response.response_id === prediction.response_id) &&
        [prediction.mean_raw, prediction.latent_standard_deviation_raw, prediction.predictive_standard_deviation_raw].every(Number.isFinite) &&
        prediction.latent_standard_deviation_raw >= 0 && prediction.predictive_standard_deviation_raw >= prediction.latent_standard_deviation_raw);
  });
}
export function validAugmentationSelection(value: AugmentationSelectionResponse, study: BayesianStudyResponse, expected?: AugmentationSelectionRequest): boolean {
  return !!value && [2, 4].includes(value.schema_version) && value.schema_version === value.request?.schema_version && value.study_id === study.study_id && value.study_version_id === study.study_version_id && planningId(value.selection_id) &&
    planningHash(value.config_sha256) && planningHash(value.result_sha256) && value.model_id === value.request?.model_id &&
    value.candidate_revision_id === value.request?.candidate_revision_id && value.request.expected_study_version_id === study.study_version_id &&
    value.request.expected_definition_sha256 === study.definition_sha256 && (!expected || sameDesirabilityJson(value.request, expected)) &&
    validAugmentationCalculation(value.calculation, value.request, study);
}
export function validAugmentationBatch(value: AugmentationBatchResponse, study: BayesianStudyResponse, id: string): boolean {
  const version = value?.selection_request?.schema_version === 4 ? 11 : 9;
  if (!value || !planningId(id) || value.batch_id !== id || value.source?.selection_id !== id || value.study_id !== study.study_id || value.study_version_id !== study.study_version_id ||
    value.definition_sha256 !== study.definition_sha256 || value.method_version !== (version === 11 ? "0.16.0" : "0.14.0") || value.config_schema_version !== version || value.result_schema_version !== version || value.model_schema_version !== version ||
    value.item_schema_version !== 4 || value.batch_policy !== "source_owned_augmentation_v1" || study.objective.goal_type !== "desirability" ||
    !sameDesirabilityJson(value.objective.responses, study.objective.responses) || !planningId(value.source_history_revision_id) ||
    ![value.result_sha256, value.config_sha256, value.source_observation_history_sha256, value.source.rows_sha256, value.source.selection_config_sha256, value.source.selection_result_sha256].every(planningHash) ||
    value.source.candidate_revision_id !== value.selection_request?.candidate_revision_id || value.source.model_id !== value.selection_request.model_id || value.source.model_sha256 !== value.selection_request.expected_model_sha256 ||
    value.source.rows_sha256 !== value.selection_request.expected_rows_sha256 || value.source_history_revision_id !== value.selection_request.expected_history_revision_id || value.source_observation_history_sha256 !== value.selection_request.expected_history_sha256 ||
    (value.model === null ? value.source.model_id !== null : value.model.model_id !== value.source.model_id || value.model.snapshot_sha256 !== value.source.model_sha256) ||
    !validAugmentationCalculation(value.calculation, value.selection_request, study) || value.batch_size !== value.selection_request.batch_size || !Array.isArray(value.items) || value.items.length !== value.batch_size ||
    new Set(value.items.map(item => item.trial.trial_id)).size !== value.batch_size) return false;
  return value.items.every((item, index) => item.batch_id === id && item.rank === index + 1 && planningId(item.item_id) && planningId(item.trial.trial_id) &&
    item.current_trial.trial_id === item.trial.trial_id && sameDesirabilityJson(item.trial.actual_coordinates, value.calculation.selected_rows[index].actual_coordinates) &&
    sameDesirabilityJson(item.current_trial.actual_coordinates, item.trial.actual_coordinates));
}
export function validSavedAutoEvidence(value: AugmentationCalculation | MixedAugmentationCalculation, request: AugmentationSelectionRequest | MixedSelectionRequest, study: BayesianStudyResponse | MixedStudyResponse): boolean {
  if (!value || !request) return false;
  if (request.schema_version === 2 || request.schema_version === 3) return value.schema_version === (request.schema_version === 2 ? 1 : 3) && !("auto_evidence" in value && value.auto_evidence);
  if (value.schema_version !== (request.schema_version === 4 ? 2 : 4) || !("auto_evidence" in value) || !value.auto_evidence || !request.auto_strategy || study.objective.goal_type !== "desirability") return false;
  const receipt = value.auto_evidence, diagnostic = receipt.diagnostic, reference = request.auto_strategy;
  return receipt.schema_version === 1 && reference.schema_version === 1 && !!diagnostic &&
    !("source_is_current" in diagnostic) && receipt.decision_sha256 === reference.expected_decision_sha256 &&
    diagnostic.model_id === reference.routing_model_id && diagnostic.model_sha256 === reference.expected_model_sha256 &&
    diagnostic.history_sha256 === request.expected_history_sha256 && diagnostic.source_history_revision_id === request.expected_history_revision_id &&
    (request.model_id === null || request.model_id === reference.routing_model_id && request.expected_model_sha256 === reference.expected_model_sha256) && receipt.decision.recommended_policy === request.policy &&
    validAutoStrategy({ ...receipt, decision_only: true, selection_created: false, apply_allowed: false,
      diagnostic: { ...diagnostic, source_is_current: false } }, study.study_id, {
      model_id: reference.routing_model_id, snapshot_sha256: reference.expected_model_sha256,
      config_sha256: diagnostic.config_sha256, history_sha256: request.expected_history_sha256,
      source_history_revision_id: request.expected_history_revision_id, source_is_current: false, objective: study.objective,
    }, study.factors.map(factor => factor.domain_kind ?? "continuous"), reference.r_squared_threshold);
}
export function validAugmentationReportSource(descriptor: ReportSourceDescriptor, batch: AugmentationBatchResponse): boolean {
  if (!isReportSourceDescriptor(descriptor) || descriptor.source.kind !== "bayesian_history_revision") return false;
  const source = descriptor.source;
  return source.study_id === batch.study_id && source.study_version_id === batch.study_version_id && source.definition_sha256 === batch.definition_sha256 &&
    source.history_revision_id === batch.source_history_revision_id && source.expected_source_sha256 === batch.source_observation_history_sha256 &&
    source.attachment.kind === "batch" && source.attachment.batch_id === batch.batch_id && source.attachment.result_payload_sha256 === batch.result_sha256;
}
