import type { MixedStudyResponse } from "../../api/types/boMixed";
import { planningBatchFixture } from "./boPlanning.fixture";

// Test-only synthetic source/identity data; no fitted model or numeric reference.
export function mixedStudyFixture(completed = true): MixedStudyResponse {
  const base = planningBatchFixture().study;
  const id = (index: number) => `22222222-2222-4222-8222-${String(index).padStart(12, "0")}`;
  if (base.objective.goal_type !== "desirability") throw new Error("synthetic_vector_objective");
  const trials: MixedStudyResponse["trials"] = Array.from({ length: 4 }, (_, index) => ({ trial_id: id(index + 10), study_version_id: base.study_version_id,
    trial_number: index + 1, origin: "initial_design", state: completed ? "completed" : "pending", actual_coordinates: { x: index % 2, material: index < 2 ? "001" : "한글 A" },
    encoded_coordinates: { x: index % 2, material: index < 2 ? 0 : 1 }, coordinate_encoding: "numeric_normalized_category_index_v1",
    coordinates_sha256: String(index + 1).repeat(64), objective_value: null, response_values: completed ? { yield: 1 + index, cost: 4 - index } : null,
    created_at: "2026-11-10T00:00:00Z", closed_at: completed ? "2026-11-10T00:01:00Z" : null, replicate_of_trial_id: null }));
  return { ...base, study_schema_version: 7, method_version: "0.15.0", name: "Synthetic mixed source", objective: base.objective,
    factors: [{ factor_id: "x", name: "Temperature", unit: "C", low: 0, high: 1, domain_kind: "continuous", step: null, display_decimals: null, order: 1, scaling_rule: "linear_0_1" },
      { factor_id: "material", name: "Catalyst <raw>", unit: null, domain_kind: "nominal", levels: ["001", "한글 A"], correlation_policy: "equal_positive_correlation_v1", order: 2, encoding_rule: "declared_level_index_v1" }],
    trials, trial_count: 4, pending_trial_count: completed ? 0 : 4, completed_trial_count: completed ? 4 : 0, abandoned_trial_count: 0,
    observation_history: { ...base.observation_history, schema_version: 2, study_version_id: base.study_version_id,
      completed_trial_ids: completed ? trials.map(row => row.trial_id) : [], completed_trial_count: completed ? 4 : 0 },
    initial_design: { policy: "sha256_counter_mixed_uniform_feasible_v1", seed: 42, requested_size: 4, generated_size: 4, attempt_limit: 4000, attempts_consumed: 4,
      rejected_duplicate_count: 0, rejected_infeasible_count: 0, coordinate_encoding: "numeric_normalized_category_index_v1", category_level_counts: { material: [2, 2] }, unobserved_level_indices: { material: [] }, warnings: [] },
    recommendation_available: completed, recommendation_blockers: completed ? [] : ["bayesian_pending_trials_exist"], recommendation_workflow: "fixed_candidate_mixed_planning_v1", recommendation_minimum_completed_observations: 3,
  };
}
