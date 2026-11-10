import { describe, expect, it } from "vitest";
import { desirabilityBatchFixture, desirabilityFixture } from "./bayesianDesirability.fixture";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { validDesirabilityCalculation, validDesirabilitySaved } from "./desirabilityResponseGuard";
import type { DesirabilityCurveBatch, DesirabilityCurveCalculation } from "../../api/types/bayesianDesirability";

describe("versioned desirability response ownership", () => {
  it.each(["controls", "policy", "legacy", "raw_model", "fit"])("validates stored Gaussian controls and rejects %s mismatch", kind => {
    const fixture = desirabilityBatchFixture();
    const {study} = fixture;
    if (study.objective.goal_type !== "desirability") throw new Error("fixture objective");
    study.study_schema_version = 6;
    study.objective.curve_policy = "per_response_target_gaussian_or_ds_v1";
    Object.assign(study.objective.responses[1], {goal: "match_target", lower: 0, target: 1, upper: 6,
      curve: {policy: "two_sided_gaussian_target_peak_one_v1", lower_desirability: .04, upper_desirability: .2}});
    const calculation: DesirabilityCurveCalculation = {...fixture.calculation, schema_version: 7,
      objective: {responses: structuredClone(study.objective.responses)},
      shared_model: {...fixture.calculation.shared_model, schema_version: 7,
        curve_policy: "per_response_target_gaussian_or_ds_v1", moment_policy: "independent_latent_versioned_curve_moments_v1"}};
    const batch: DesirabilityCurveBatch = {...fixture.batch, calculation, method_version: "0.12.0", config_schema_version: 7, result_schema_version: 7, model_schema_version: 7};
    const request = buildDesirabilityRequest(study, {...defaultDesirabilityDraft(study), batchSize: "2"}).request!;
    expect(validDesirabilityCalculation(calculation, study, request)).toBe(true);
    expect(validDesirabilitySaved(batch, study, null)).toBe(true);
    if (kind === "controls") calculation.objective.responses[1].curve!.lower_desirability = .05;
    if (kind === "policy") Object.assign(calculation.shared_model, {curve_policy: "derringer_suich_linear_v1"});
    if (kind === "legacy") Object.assign(calculation, {schema_version: 5});
    if (kind === "raw_model") Object.assign(calculation.shared_model.response_models[0].model, {schema_version: 3});
    if (kind === "fit") Object.assign(request, {fit_policy: {kind: "bounded_multiscale_starts_v1", deterministic_start_count: 1}});
    expect(validDesirabilityCalculation(calculation, study, request)).toBe(false);
  });
  it.each([1, 2, 8])("checks all %s ordered candidates and leaves actual observations as an overlay", size => {
    const { study, calculation, batch } = desirabilityBatchFixture("batch", size);
    expect(validDesirabilityCalculation(calculation, study)).toBe(true);
    expect(validDesirabilitySaved(batch, study, batch.batch_id)).toBe(true);
    batch.items.at(-1)!.current_trial.state = "completed";
    batch.items.at(-1)!.current_trial.response_values = { yield: .9, cost: 1.1 };
    batch.batch_state = size === 1 ? "completed" : "partially_completed";
    expect(validDesirabilitySaved(batch, study, batch.batch_id)).toBe(true);
    expect(batch.items.at(-1)!.trial.state).toBe("pending");
  });
  it("preserves old q1 and requires the exact new request options", () => {
    const old = desirabilityFixture(); expect(validDesirabilitySaved(old.batch, old.study, null)).toBe(true);
    const current = desirabilityBatchFixture();
    const request = buildDesirabilityRequest(current.study, { ...defaultDesirabilityDraft(current.study), batchSize: "2" }).request!;
    expect(validDesirabilityCalculation(current.calculation, current.study, request)).toBe(true);
    current.calculation.batch_options.sample_count = 16;
    expect(validDesirabilityCalculation(current.calculation, current.study, request)).toBe(false);
    expect(validDesirabilityCalculation(old.calculation, current.study, request)).toBe(false);
  });
  it.each(["rank", "duplicate", "missing", "trial_number", "coordinate", "overlay", "response", "prefix", "source", "version"])("rejects %s corruption in the last item", kind => {
    const { study, calculation, batch } = desirabilityBatchFixture(); const last = batch.items[1];
    if (kind === "rank") last.rank = 1;
    if (kind === "duplicate") last.trial.trial_id = batch.items[0].trial.trial_id;
    if (kind === "missing") batch.items.pop();
    if (kind === "trial_number") last.trial.trial_number += 1;
    if (kind === "coordinate") last.trial.actual_coordinates.x = .123;
    if (kind === "overlay") last.current_trial.actual_coordinates.x = .123;
    if (kind === "response") calculation.items[1].response_predictions[0].response_id = "other";
    if (kind === "prefix") calculation.items[1].planning.sampler.conditioned_on_selected_ranks = [];
    if (kind === "source") batch.definition_sha256 = "other";
    if (kind === "version") Object.assign(batch, { item_schema_version: 3 });
    expect(validDesirabilitySaved(batch, study, null)).toBe(false);
  });
});
