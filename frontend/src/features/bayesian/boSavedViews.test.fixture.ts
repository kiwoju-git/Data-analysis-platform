import type { BoViewReceipt } from "../../api/boViews";

export const viewSource = { study_id: "study", study_version_id: "version", definition_sha256: "d".repeat(64), model_id: "model", model_sha256: "a".repeat(64), model_config_sha256: "b".repeat(64), history_revision_id: "history", history_sha256: "c".repeat(64) };
export const viewRequest = { kind: "profiler_matrix" as const, expected_model_sha256: viewSource.model_sha256, expected_history_sha256: viewSource.history_sha256, holds: { x: 1, category: "한글" }, points_per_axis: 2, time_budget_ms: 120000 };
export function receiptFixture(): BoViewReceipt {
  const point = (x: number, category: string) => ({ row_id: `${x}-${category}`, actual_coordinates: { x, category }, constraints_satisfied: x === 1,
    prediction_source: "completed_observations_base_posterior" as const, desirability_moments: { mean: .5 },
    response_predictions: [{ response_id: "desirability", mean_raw: 1e-6, latent_standard_deviation_raw: 1e-8, predictive_standard_deviation_raw: 2e-8 }] });
  return { receipt_id: "receipt", request_sha256: "e".repeat(64), view_sha256: "f".repeat(64), expires_at: "2026-11-14T00:20:00Z", payload: {
    schema_version: 1, kind: "profiler_matrix", source: { ...viewSource }, model_refit: false, policy: "source_locked_conditional_profiler_matrix_v1", holds: { ...viewRequest.holds },
    responses: [{ response_id: "desirability", name: "실제 반응", unit: "mg" }], constraints: [], warnings: [], point_count: 4,
    axes: [{ factor_id: "x", name: "Numeric", unit: "g", kind: "continuous", available_level_count: null, points: [point(0, "한글"), point(1, "한글")] },
      { factor_id: "category", name: "Category", unit: null, kind: "nominal", available_level_count: 2, points: [point(1, "한글"), point(1, "A")] }],
  } };
}
