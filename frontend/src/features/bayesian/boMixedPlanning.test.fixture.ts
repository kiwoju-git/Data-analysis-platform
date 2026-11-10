import type { MixedBatchResponse, MixedCandidatePage, MixedModelDetail, MixedSelectionItem, MixedSelectionRequest, MixedSelectionResponse } from "../../api/types/boMixed";
import type { ReportSourceDescriptor } from "../../api/types/reports";
import { mixedStudyFixture } from "./boMixed.test.fixture";
import { planningBatchFixture } from "./boPlanning.fixture";
import { initialMixedFit, mixedFitOptions, mixedSource } from "./boMixedPlanningDraft";

// Ownership/presentation fixture only; statistical references belong to the backend tests.
export function mixedPlanningFixture() {
  const study = mixedStudyFixture(), original = planningBatchFixture();
  const modelId = original.batch.source.model_id, revisionId = original.batch.source.candidate_revision_id, selectionId = original.batch.batch_id;
  const items: MixedSelectionItem[] = original.batch.calculation.items.map((row, index) => {
    const actual = { x: .25 + index * .25, material: index % 2 ? "한글 A" : "001" };
    return { schema_version: 2, row_id: row.row_id, source_row_number: index + 1, input_coordinates: actual, actual_coordinates: actual, encoded_coordinates: { x: actual.x, material: index % 2 },
      coordinate_encoding: "numeric_normalized_category_index_v1", distance_policy: "numeric_normalized_category_hamming_v1", ordinal_rank_distance: false,
      canonical_level_indices: { x: null, material: index % 2 }, constraint_evaluations: [], constraints_satisfied: true, nearest_existing_distance: .25, novel: true, eligible: true,
      response_predictions: row.response_predictions, desirability_moments: row.desirability_moments, acquisition: row.acquisition, prediction_source: "completed_observations_base_posterior",
      rank: index + 1, nearest_selected_distance: row.nearest_selected_distance,
      planning: { ...row.planning, sampler: { ...row.planning.sampler, coordinate_encoding: "numeric_normalized_category_index_v1" } } };
  });
  const model: MixedModelDetail = { schema_version: 2, model_id: modelId, study_id: study.study_id, study_version_id: study.study_version_id, source_history_revision_id: study.observation_history.history_revision_id,
    history_sha256: study.observation_history.observation_history_sha256, definition_sha256: study.definition_sha256, snapshot_sha256: "3".repeat(64), config_sha256: "a".repeat(64), created_at: original.batch.created_at, source_is_current: true,
    fit: mixedFitOptions(study, initialMixedFit(study))!, objective: study.objective, response_models: study.objective.responses.map(response => ({ response_id: response.response_id,
      model: { schema_version: 6, policy_version: "bo_mixed_noise_latent_v1", raw_observation_count: 4, effective_training_count: 4, observation_noise_sd_raw: 1e-8, jitter: 1e-8,
        optimizer: { name: "L-BFGS-B", starts: [{ success: true, status: 0, evaluations: 3 }] }, training_level_coverage: [{ factor_id: "material", raw_observation_counts: [2, 2] }],
        parameter_descriptors: [{ index: 0, role: "category_mismatch", factor_id: "material" }], fit_diagnostics: { selected: { log_parameters: [0] } } }, observation_view: {} })),
    incumbent: { policy: "max_posterior_expected_desirability_at_observed_coordinates_v1", best_observed_desirability: .5, best_observed_trial_id: study.trials[0].trial_id, latent_incumbent_value: .4, latent_incumbent_trial_id: study.trials[0].trial_id,
      latent_incumbent_encoded_coordinates: study.trials[0].encoded_coordinates, coordinate_encoding: "numeric_normalized_category_index_v1", observed_trial_desirabilities: [], training_posterior_desirabilities: [] },
    observation_view: {}, warnings: [], model_reusable_without_refit: true };
  const page: MixedCandidatePage = { revision: { schema_version: 3, candidate_set_id: "33333333-3333-4333-8333-333333333333", revision_id: revisionId, revision_number: 1, parent_revision_id: null,
    name: "Synthetic mixed candidates", model_id: null, model_sha256: null, rows_sha256: "4".repeat(64), config_sha256: "5".repeat(64), excluded_coordinates_sha256: "6".repeat(64),
    study_version_id: study.study_version_id, source_history_revision_id: study.observation_history.history_revision_id, definition_sha256: study.definition_sha256, history_sha256: study.observation_history.observation_history_sha256,
    source_trial_count: study.trial_count, row_count: items.length, eligible_count: items.length, created_at: original.batch.created_at, source_is_current: true, duplicate_tolerance: 1e-6, ordinal_rank_distance: false }, offset: 0, limit: 50, items };
  const request: MixedSelectionRequest = { ...mixedSource(study), schema_version: 3, request_id: "44444444-4444-4444-8444-444444444444", kind: "manual_ordered", candidate_revision_id: revisionId,
    expected_rows_sha256: page.revision.rows_sha256, model_id: model.model_id, expected_model_sha256: model.snapshot_sha256, row_ids: items.map(item => item.row_id), policy: null, batch_size: items.length,
    total_trial_budget: 200, duplicate_tolerance: 1e-6, ordinal_rank_distance: false, min_batch_distance: 0, sample_count: 64, max_evaluations: 100000, max_moment_evaluations: 8192, time_budget_ms: 60000 };
  const selection: MixedSelectionResponse = { schema_version: 3, selection_id: selectionId, study_id: study.study_id, study_version_id: study.study_version_id, model_id: modelId, candidate_revision_id: revisionId,
    config_sha256: "7".repeat(64), result_sha256: "8".repeat(64), request,
    calculation: { schema_version: 2, selection_policy: "manual_ordered_mixed_model_v1", model_refit: false, distance_policy: "numeric_normalized_category_hamming_v1", ordinal_rank_distance: false, items, moment_evaluations: 40, max_moment_evaluations: 8192 },
    created_at: original.batch.created_at, source_is_current: true, confirmed_batch_id: null };
  const batch: MixedBatchResponse = { method_id: "doe.bayesian_optimization", method_version: "0.15.0", config_schema_version: 10, result_schema_version: 10, model_schema_version: 10, item_schema_version: 5,
    batch_policy: "source_owned_mixed_planning_v1", batch_size: items.length, batch_id: selectionId, study_id: study.study_id, study_version_id: study.study_version_id, definition_sha256: study.definition_sha256,
    source_history_revision_id: study.observation_history.history_revision_id, source_observation_history_sha256: study.observation_history.observation_history_sha256,
    source: { model_id: modelId, model_sha256: model.snapshot_sha256, candidate_revision_id: revisionId, rows_sha256: page.revision.rows_sha256, selection_id: selectionId, selection_config_sha256: selection.config_sha256, selection_result_sha256: selection.result_sha256 },
    objective: study.objective, response_models: model.response_models, incumbent: model.incumbent, observation_view: {}, warnings: [], selection_request: request, calculation: selection.calculation,
    items: items.map((row, index) => { const trial = { ...study.trials[index], trial_number: index + 5, actual_coordinates: row.actual_coordinates, encoded_coordinates: row.encoded_coordinates, state: "pending" as const, response_values: null, closed_at: null }; return { item_id: original.batch.items[index].item_id, batch_id: selectionId, rank: index + 1, trial, current_trial: { ...trial } }; }),
    config_sha256: "9".repeat(64), result_sha256: "a".repeat(64), created_at: original.batch.created_at, is_latest: true, batch_state: "pending", requested_total_trial_budget: 200, provenance: original.batch.provenance };
  const descriptor: ReportSourceDescriptor = { ...original.descriptor, source: { kind: "bayesian_history_revision", study_id: study.study_id, study_version_id: study.study_version_id, definition_sha256: study.definition_sha256,
    history_revision_id: batch.source_history_revision_id, expected_source_sha256: batch.source_observation_history_sha256, attachment: { kind: "batch", batch_id: batch.batch_id, result_json_sha256: "b".repeat(64), result_payload_sha256: batch.result_sha256 } },
    open_target: `/analysis/doe/doe.bayesian_optimization?study_id=${study.study_id}&mixed_planning_batch_id=${batch.batch_id}` };
  return { study, model, page, selection, batch, descriptor };
}
