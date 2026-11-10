import type { AugmentationBatchResponse, AugmentationCalculation, AugmentationSelectionResponse } from "../../api/types/boAugmentation";
import type { CandidatePage, CandidateRow, PlanningModelDetail } from "../../api/types/boPlanning";
import type { ReportSourceDescriptor } from "../../api/types/reports";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { augmentationRequest, initialAugmentationDraft } from "./boAugmentationDraft";
import { planningBatchFixture } from "./boPlanning.fixture";

// Ownership and presentation fixture only, not a numerical acquisition reference.
export function augmentationFixture(modelBased = false) {
  const original = planningBatchFixture(), study = original.study, old = original.batch;
  const fit = buildDesirabilityRequest(study, { ...defaultDesirabilityDraft(study), batchSize: "2" }).request;
  if (!fit || fit.schema_version === 4) throw new Error("synthetic_fit_request");
  const model: PlanningModelDetail = { schema_version: 1, model_id: old.source.model_id, study_id: study.study_id, study_version_id: study.study_version_id,
    source_history_revision_id: old.source_history_revision_id, history_sha256: old.source_observation_history_sha256, definition_sha256: old.definition_sha256,
    snapshot_sha256: old.source.model_sha256, config_sha256: "b".repeat(64), created_at: old.created_at, source_is_current: true,
    fit, objective: old.objective, response_models: old.response_models, incumbent: old.incumbent, observation_view: old.observation_view, warnings: [], model_reusable_without_refit: true };
  const rows: CandidateRow[] = old.calculation.items.map(row => ({ row_id: row.row_id, source_row_number: row.source_row_number,
    input_coordinates: row.input_coordinates, actual_coordinates: row.actual_coordinates, normalized_coordinates: row.normalized_coordinates,
    canonical_level_indices: row.canonical_level_indices, constraint_evaluations: row.constraint_evaluations, constraints_satisfied: true,
    nearest_existing_distance: row.nearest_existing_distance, novel: true, eligible: true }));
  const page: CandidatePage = { offset: 0, limit: 50, items: rows, revision: { schema_version: 2, candidate_set_id: "11111111-1111-4111-8111-000000000030",
    name: "Synthetic <candidate>", revision_id: old.source.candidate_revision_id, revision_number: 1, parent_revision_id: null, model_id: null, model_sha256: null,
    rows_sha256: old.source.rows_sha256, config_sha256: "b".repeat(64), excluded_coordinates_sha256: "e".repeat(64), source_trial_count: study.trial_count,
    row_count: rows.length, eligible_count: rows.length, created_at: old.created_at, source_is_current: true, duplicate_tolerance: 1e-6,
    study_version_id: study.study_version_id, source_history_revision_id: study.observation_history.history_revision_id,
    definition_sha256: study.definition_sha256, history_sha256: study.observation_history.observation_history_sha256 } };
  const draft = initialAugmentationDraft(study);
  if (modelBased) draft.policy = "refine_ei_alternating_desirability_response_sd_v2";
  const request = augmentationRequest(study, page, model, draft, "11111111-1111-4111-8111-000000000031");
  if (!request) throw new Error("synthetic_augmentation_request");
  const calculation: AugmentationCalculation = { schema_version: 1, model_refit: false, source_row_count: rows.length,
    prediction_evaluations: modelBased ? 10 : 0, max_moment_evaluations: request.max_moment_evaluations, time_budget_ms: request.time_budget_ms,
    selected_rows: rows.map((row, index) => modelBased ? { ...row, prediction_source: "completed_observations_base_posterior" as const,
      response_predictions: old.calculation.items[index].response_predictions, desirability_moments: old.calculation.items[index].desirability_moments,
      acquisition: old.calculation.items[index].acquisition } : row),
    augmentation: { schema_version: 1, policy: request.policy, source: { model_snapshot_id: request.model_id, model_snapshot_sha256: request.expected_model_sha256,
      candidate_revision_id: request.candidate_revision_id, candidate_revision_sha256: request.expected_rows_sha256, history_sha256: request.expected_history_sha256 },
      selected_row_ids: rows.map(row => row.row_id), steps: rows.map((row, index) => ({ rank: index + 1, row_id: row.row_id,
        criterion: modelBased ? (index ? "base_desirability_standard_deviation" : "base_desirability_beta_ei") : "log_incremental_inverse_projection_distance",
        score: modelBased ? .01 : 1.1, score_scale: modelBased ? "original" : "natural_log", optimization_direction: modelBased ? "maximize" : "minimize",
        nearest_existing_distance: row.nearest_existing_distance!, nearest_selected_distance: index ? 1 / 3 : null,
        compared_candidate_count: rows.length - index, competitive_threshold: null })),
      distance_policy: "normalized_numeric_hamming_nominal_explicit_ordinal_rank_v1", ordinal_rank_distance: false, tie_break: "row_id_ascending", competitive_set_policy: null,
      reference_count: 2, raw_reference_count: 2, eligible_candidate_count: rows.length, projection_collisions: 0, unscorable_candidates: [],
      evaluations: 3, max_evaluations: request.max_evaluations, pair_comparisons: 6, time_budget_ms: request.time_budget_ms, model_refit: false, fantasy_observations: false,
      warnings: ["bayesian_augmentation_not_verified_jmp_parity"], response_uncertainty: modelBased ? { policy: "importance_weighted_rms_normalized_latent_sd_v1", variance_kind: "latent", scale: "dimensionless", context: [], schedule: "first_ei_then_alternating_desirability_sd_response_sd" } : null },
  };
  const selection: AugmentationSelectionResponse = { schema_version: 2, selection_id: old.batch_id, study_id: study.study_id, study_version_id: study.study_version_id,
    model_id: request.model_id, candidate_revision_id: request.candidate_revision_id, config_sha256: old.source.selection_config_sha256,
    result_sha256: old.source.selection_result_sha256, request, calculation, created_at: old.created_at, source_is_current: true, confirmed_batch_id: null };
  const batch: AugmentationBatchResponse = { method_id: "doe.bayesian_optimization", method_version: "0.14.0", config_schema_version: 9, result_schema_version: 9,
    model_schema_version: 9, item_schema_version: 4, batch_id: old.batch_id, study_id: old.study_id, study_version_id: old.study_version_id,
    source_history_revision_id: old.source_history_revision_id, source_observation_history_sha256: old.source_observation_history_sha256, definition_sha256: old.definition_sha256,
    source: { ...old.source, model_id: request.model_id, model_sha256: request.expected_model_sha256 }, objective: old.objective, model: modelBased ? model : null,
    calculation, selection_request: request, batch_policy: "source_owned_augmentation_v1", batch_size: old.batch_size, items: old.items,
    config_sha256: old.config_sha256, result_sha256: old.result_sha256, created_at: old.created_at, is_latest: true, batch_state: "pending",
    requested_total_trial_budget: request.total_trial_budget, provenance: old.provenance };
  const descriptor: ReportSourceDescriptor = { ...original.descriptor,
    open_target: `/analysis/doe/doe.bayesian_optimization?study_id=${study.study_id}&augmentation_batch_id=${batch.batch_id}` };
  return { study, model, page, request, draft, selection, batch, descriptor };
}
