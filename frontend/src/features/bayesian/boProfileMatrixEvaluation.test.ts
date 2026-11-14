import { afterEach, describe, expect, it, vi } from "vitest";
import { evaluatePlanningModel } from "../../api/boPlanning";
import { evaluateMixedModel } from "../../api/boMixed";
import { numericMatrixChunk, mixedMatrixChunk } from "./boProfileMatrixEvaluation";
import { augmentationFixture } from "./boAugmentation.fixture";
import { mixedPlanningFixture } from "./boMixedPlanning.test.fixture";
import { planningBatchFixture } from "./boPlanning.fixture";
import type { PlanningEvaluationResponse } from "../../api/types/boPlanning";
import type { MixedEvaluationResponse } from "../../api/types/boMixed";
vi.mock("../../api/boPlanning", () => ({ evaluatePlanningModel: vi.fn() }));
vi.mock("../../api/boMixed", () => ({ evaluateMixedModel: vi.fn() }));
afterEach(() => vi.clearAllMocks());
describe("matrix chunk exact response guards", () => {
  it.each([undefined, "different_posterior"])("rejects numeric prediction provenance %s", async predictionSource => {
    const { study, model } = augmentationFixture(true), { batch } = planningBatchFixture();
    const response = { schema_version: 1, model_id: model.model_id, model_sha256: model.snapshot_sha256, request_sha256: "a".repeat(64), source_is_current: true, eligibility_source_trial_count: study.trial_count, eligibility_coordinates_sha256: "b".repeat(64), eligibility_is_current: true, model_refit: false, items: batch.calculation.items.map(row => ({ ...row, prediction_source: predictionSource })) };
    vi.mocked(evaluatePlanningModel).mockResolvedValue(response as unknown as PlanningEvaluationResponse);
    await expect(numericMatrixChunk(study.study_id, model, response.items.map(row => row.actual_coordinates), 1234)).rejects.toThrow("bayesian_profile_response_mismatch");
  });
  it("validates numeric source, finite quantities, response IDs and coordinates without refitting", async () => {
    const { study, model } = augmentationFixture(true), { batch } = planningBatchFixture();
    const response: PlanningEvaluationResponse = { schema_version: 1, model_id: model.model_id, model_sha256: model.snapshot_sha256, request_sha256: "a".repeat(64), source_is_current: true, eligibility_source_trial_count: study.trial_count, eligibility_coordinates_sha256: "b".repeat(64), eligibility_is_current: true, model_refit: false, items: batch.calculation.items.map(row => ({ ...row, prediction_source: "completed_observations_base_posterior" })) };
    const points = response.items.map(row => row.actual_coordinates);
    vi.mocked(evaluatePlanningModel).mockResolvedValue(response);
    expect(await numericMatrixChunk(study.study_id, model, points, 1234)).toEqual(response.items);
    expect(evaluatePlanningModel).toHaveBeenLastCalledWith(study.study_id, model.model_id, { expected_model_sha256: model.snapshot_sha256, points, time_budget_ms: 1234 });
    for (const mutate of [(value: PlanningEvaluationResponse) => { value.model_sha256 = "wrong"; }, (value: PlanningEvaluationResponse) => { value.items[0].response_predictions[0].mean_raw = NaN; }, (value: PlanningEvaluationResponse) => { value.items[0].response_predictions[0].response_id = "unknown"; }, (value: PlanningEvaluationResponse) => { value.items[0].input_coordinates.x = 999; }]) {
      const invalid = structuredClone(response); mutate(invalid); vi.mocked(evaluatePlanningModel).mockResolvedValue(invalid);
      await expect(numericMatrixChunk(study.study_id, model, points, 1234)).rejects.toThrow("bayesian_profile_response_mismatch");
    }
  });
  it("validates mixed model hash and full category/uncertainty payload", async () => {
    const { study, model, selection } = mixedPlanningFixture(); if (selection.calculation.schema_version !== 2) throw Error("fixture");
    const response: MixedEvaluationResponse = { model_id: model.model_id, snapshot_sha256: model.snapshot_sha256, model_refit: false, items: selection.calculation.items, eligibility_history_sha256: model.history_sha256, eligibility_is_current: true };
    const points = response.items.map(row => row.actual_coordinates);
    vi.mocked(evaluateMixedModel).mockResolvedValue(response);
    expect(await mixedMatrixChunk(study, model, points, 456)).toEqual(response.items);
    expect(evaluateMixedModel).toHaveBeenLastCalledWith(study.study_id, model.model_id, { expected_model_sha256: model.snapshot_sha256, points, time_budget_ms: 456, max_moment_evaluations: 65536 });
    for (const mutate of [(value: MixedEvaluationResponse) => { value.snapshot_sha256 = "wrong"; }, (value: MixedEvaluationResponse) => { value.items[0].response_predictions[0].predictive_standard_deviation_raw = -1; }, (value: MixedEvaluationResponse) => { value.items[0].input_coordinates.material = "undeclared"; }]) {
      const invalid = structuredClone(response); mutate(invalid); vi.mocked(evaluateMixedModel).mockResolvedValue(invalid);
      await expect(mixedMatrixChunk(study, model, points, 456)).rejects.toThrow("bayesian_profile_response_mismatch");
    }
  });
});
