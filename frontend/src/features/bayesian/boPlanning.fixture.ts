import type { PlanningBatchResponse, PlanningSelectionItem } from "../../api/types/boPlanning";
import type { ReportSourceDescriptor } from "../../api/types/reports";
import { desirabilityBatchFixture } from "./bayesianDesirability.fixture";

// Synthetic ownership/presentation data, not a GP or acquisition numerical reference.
export function planningBatchFixture() {
  const original = desirabilityBatchFixture(), study = original.study;
  const id = (index: number) => `11111111-1111-4111-8111-${String(index).padStart(12, "0")}`;
  study.study_id = id(1); study.study_version_id = id(2); study.observation_history.history_revision_id = id(3);
  const items: PlanningSelectionItem[] = original.calculation.items.map((row, index) => ({
    row_id: String(index + 1).repeat(64), source_row_number: index + 1, input_coordinates: { ...row.actual_coordinates },
    actual_coordinates: { ...row.actual_coordinates }, normalized_coordinates: { ...row.normalized_coordinates }, canonical_level_indices: { x: null },
    constraint_evaluations: row.constraint_evaluations, constraints_satisfied: true, nearest_existing_distance: row.nearest_existing_distance,
    novel: true, eligible: true, response_predictions: row.response_predictions, desirability_moments: row.desirability_moments,
    acquisition: row.acquisition, rank: index + 1, nearest_selected_distance: row.nearest_selected_distance,
    planning: { score: row.planning.score, mc_standard_error: row.planning.mc_standard_error, conditional_variance_raw: row.planning.conditional_variance_raw,
      sampler: row.planning.sampler, proof: row.planning.proof },
  }));
  const batch: PlanningBatchResponse = { ...original.batch, study_id: study.study_id, study_version_id: study.study_version_id,
    source_history_revision_id: study.observation_history.history_revision_id, method_version: "0.13.0", result_schema_version: 8,
    config_schema_version: 8, model_schema_version: 8, batch_policy: "manual_ordered_fixed_model_v1", batch_id: id(4),
    calculation: { schema_version: 1, selection_policy: "manual_ordered_fixed_model_v1", model_refit: false, items, moment_evaluations: 40, max_moment_evaluations: 8192 },
    source: { model_id: id(5), model_sha256: "3".repeat(64), candidate_revision_id: id(6), rows_sha256: "4".repeat(64), selection_id: id(4), selection_config_sha256: "5".repeat(64), selection_result_sha256: "6".repeat(64) },
    objective: original.calculation.objective, response_models: original.calculation.shared_model.response_models, incumbent: original.calculation.incumbent,
    observation_view: original.calculation.observation_view, warnings: [],
    items: original.batch.items.map((item, index) => {
      const trial = { ...item.trial, trial_id: id(10 + index), study_version_id: study.study_version_id };
      return { ...item, batch_id: id(4), item_id: id(20 + index), trial, current_trial: { ...trial } };
    }),
  };
  const descriptor: ReportSourceDescriptor = { source: { kind: "bayesian_history_revision", study_id: batch.study_id, study_version_id: batch.study_version_id,
    definition_sha256: batch.definition_sha256, history_revision_id: batch.source_history_revision_id, expected_source_sha256: batch.source_observation_history_sha256,
    attachment: { kind: "batch", batch_id: batch.batch_id, result_json_sha256: "7".repeat(64), result_payload_sha256: batch.result_sha256 } },
    source_ref_sha256: "8".repeat(64), title: "Synthetic saved batch", created_at: batch.created_at, stale: false,
    open_target: `/analysis/doe/doe.bayesian_optimization?study_id=${batch.study_id}&planning_batch_id=${batch.batch_id}` };
  return { study, batch, descriptor };
}
