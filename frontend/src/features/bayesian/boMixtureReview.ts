import * as api from "../../api/boMixture";
import { createPlanningRequestFence, planningHash, planningId } from "./boPlanningDraft";
import { mixtureReviewDraftKey, validMixtureModel, validMixturePage, validMixtureSelection } from "./boMixtureDraft";
import { sameDesirabilityJson } from "./desirabilityResponseGuard";

const mismatch = () => Error("bayesian_mixture_source_mismatch");
export function validMixtureSelectionConfig(config: api.MixtureSelectionRequest): boolean {
  return !!config && config.schema_version === 6 && planningId(config.request_id) && planningId(config.candidate_revision_id) && planningHash(config.expected_rows_sha256) &&
    ["manual_mixture_base_posterior_v1", "greedy_mixture_maximin_v1"].includes(config.policy) && Number.isSafeInteger(config.batch_size) && config.batch_size >= 1 && config.batch_size <= 8 &&
    Number.isSafeInteger(config.expected_trial_count) && config.expected_trial_count >= 1 && Number.isSafeInteger(config.total_trial_budget) && config.total_trial_budget >= config.expected_trial_count + config.batch_size && config.total_trial_budget <= 200 &&
    Number.isFinite(config.min_batch_distance) && config.min_batch_distance >= 0 && Number.isSafeInteger(config.time_budget_ms) && config.time_budget_ms >= 1000 && config.time_budget_ms <= 60000 &&
    Number.isSafeInteger(config.max_moment_evaluations) && config.max_moment_evaluations >= 1 && config.max_moment_evaluations <= 65536 && Array.isArray(config.row_ids) &&
    (config.policy === "manual_mixture_base_posterior_v1" ? config.row_ids.length === config.batch_size && new Set(config.row_ids).size === config.row_ids.length && config.row_ids.every(planningHash) : config.row_ids.length === 0);
}
export function mixtureAppliedDraft(selection: api.MixtureSelection, model: api.MixtureModel) {
  const config = selection.config;
  if (!validMixtureSelectionConfig(config)) throw mismatch();
  return { seed: String(model.fit.search.random_seed), budget: String(config.total_trial_budget), distance: String(config.min_batch_distance), batch: String(config.batch_size), manual: config.policy === "manual_mixture_base_posterior_v1", selected: [...config.row_ids] };
}
export async function createMixtureReview(study: api.MixtureStudy, model: api.MixtureModel, request: api.MixtureSelectionRequest, current: () => boolean) {
  const captured = structuredClone(request);
  const selection = await api.createMixtureSelection(study.study_id, captured);
  if (!current()) return null;
  if (!validMixtureSelection(selection, study, model) || !validMixtureSelectionConfig(selection.config) || !sameDesirabilityJson(selection.config, captured) || selection.result.items.length !== captured.batch_size ||
    captured.policy === "manual_mixture_base_posterior_v1" && !sameDesirabilityJson(selection.result.items.map(row => row.row_id), captured.row_ids)) throw mismatch();
  return selection;
}
export async function restoreMixtureReview(study: api.MixtureStudy, selectionId: string, current: () => boolean) {
  const selection = await api.fetchMixtureSelection(study.study_id, selectionId);
  if (!current()) return null;
  if (selection.selection_id !== selectionId || !validMixtureSelectionConfig(selection.config)) throw mismatch();
  const model = await api.fetchMixtureModel(study.study_id, selection.config.model_id);
  if (!current()) return null;
  if (!validMixtureModel(model, study) || !validMixtureSelection(selection, study, model) || selection.result.items.length !== selection.config.batch_size ||
    selection.config.policy === "manual_mixture_base_posterior_v1" && !sameDesirabilityJson(selection.result.items.map(row => row.row_id), selection.config.row_ids)) throw mismatch();
  const draft = mixtureAppliedDraft(selection, model);
  return { selection, model, draft, draftKey: mixtureReviewDraftKey(draft) };
}
export async function fetchMixtureReviewPage(study: api.MixtureStudy, model: api.MixtureModel, revision: api.MixturePage["revision"], offset: number, current: () => boolean) {
  const page = await api.fetchMixtureCandidates(study.study_id, revision.revision_id, offset);
  if (!current()) return null;
  if (!validMixturePage(page, study, model) || page.revision.revision_id !== revision.revision_id || page.revision.rows_sha256 !== revision.rows_sha256 || page.offset !== offset || page.limit !== 50) throw mismatch();
  return page;
}
export async function runMixtureTask(fence: ReturnType<typeof createPlanningRequestFence>, task: (current: () => boolean) => Promise<void>, handlers: { success: () => void; error: (cause: unknown) => void; settled: () => void }) {
  const token = fence.begin(), current = () => fence.current(token);
  try { await task(current); if (current()) handlers.success(); }
  catch (cause) { if (current()) handlers.error(cause); }
  finally { if (current()) handlers.settled(); }
}
