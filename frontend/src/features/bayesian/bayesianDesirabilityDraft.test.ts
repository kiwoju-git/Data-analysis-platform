import { describe, expect, it } from "vitest";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { desirabilityFixture } from "./bayesianDesirability.fixture";

describe("desirability q1 request snapshots", () => {
  it("uses explicit planning options without consuming a trial or changing recommendation q1", () => {
    const { study } = desirabilityFixture();
    const draft = defaultDesirabilityDraft(study);
    expect(buildDesirabilityRequest(study, draft).request?.schema_version).toBe(4);
    expect(buildDesirabilityRequest(study, draft, "planning").request).toMatchObject({
      schema_version: 5, batch_size: 1, batch_options: { sample_count: 64 },
    });
    draft.totalBudget = String(study.trial_count);
    expect(buildDesirabilityRequest(study, draft).errors.totalBudget).toBe("budget");
    expect(buildDesirabilityRequest(study, draft, "planning").errors).toEqual({});
    draft.sampleCount = "15";
    expect(buildDesirabilityRequest(study, draft, "planning").errors.sampleCount).toBe("integer");
  });
  it("snapshots an entire ordered batch without modifying the q1 contract", () => {
    const { study } = desirabilityFixture(); const draft = defaultDesirabilityDraft(study);
    Object.assign(draft, { batchSize: "8", sampleCount: "16", momentBudget: "16000", candidateBudget: "1024", minDistance: "0.02" });
    const { request, errors } = buildDesirabilityRequest(study, draft);
    expect(errors).toEqual({});
    expect(request).toMatchObject({ schema_version: 5, batch_size: 8, batch_options: {
      sample_count: 16, max_moment_evaluations: 16000, min_batch_distance_normalized: .02,
    }, search: { max_evaluations_total: 1024 } });
    draft.sampleCount = "256"; expect(request).toHaveProperty("batch_options.sample_count", 16);
    draft.totalBudget = "9";
    expect(buildDesirabilityRequest(study, draft).errors.totalBudget).toBe("budget");
  });
  it.each([["batchSize", "2.1"], ["batchSize", "9"], ["sampleCount", "15"], ["sampleCount", "257"],
    ["momentBudget", "65537"], ["momentBudget", ""], ["candidateBudget", "31"], ["minDistance", "-1"], ["minDistance", "1e"]])(
    "rejects invalid batch %s=%s", (key, value) => {
      const { study } = desirabilityFixture(); const draft = { ...defaultDesirabilityDraft(study), batchSize: "2", [key]: value };
      expect(buildDesirabilityRequest(study, draft).errors).toHaveProperty(key);
    });
  it("keeps every response ID, raw measurement SD and original source separate", () => {
    const { study } = desirabilityFixture(); const draft = defaultDesirabilityDraft(study);
    draft.models[1] = { ...draft.models[1], noise: "fixed", fixedSd: "1e-6", kernel: "gaussian" };
    draft.aggregation = "exact_replicates";
    const { request, errors } = buildDesirabilityRequest(study, draft);
    expect(errors).toEqual({}); expect(request).toMatchObject({ schema_version: 4, batch_size: 1, expected_history_revision_id: study.observation_history.history_revision_id,
      expected_history_sha256: study.observation_history.observation_history_sha256, observation_policy: { mode: "exact_replicates", nearby_tolerances: null, nearby_units: "normalized" },
      response_models: [{ response_id: "yield", kernel: { kind: "matern_5_2" } }, { response_id: "cost", kernel: { kind: "gaussian" }, surrogate: { fixed_noise_sd: 1e-6 } }] });
    expect(request).not.toHaveProperty("objective_value"); expect(request?.search).not.toHaveProperty("batch_policy");
    expect(request?.search).not.toHaveProperty("total_trial_budget");
    draft.models[0].initial = ".5"; expect(request?.response_models[0].surrogate.initial_noise_variance_scaled).toBe(.01);
  });
  it.each(["", " ", "5abc", "5.5", "Infinity", "NaN", "0x20", "1e2"])("rejects strict integer draft %j without coercion", value => {
    const { study } = desirabilityFixture(); const draft = defaultDesirabilityDraft(study);
    draft.totalBudget = value; expect(buildDesirabilityRequest(study, draft).request).toBeNull();
    expect(buildDesirabilityRequest(study, draft).errors.totalBudget).toBe("budget");
  });
  it.each([["seed", "2147483648"], ["seed", "-1"], ["timeMs", "999"], ["timeMs", "60001"], ["modelEvaluations", "2001"], ["modelEvaluations", "1"], ["xi", "-1"], ["xi", "NaN"]] as const)("rejects out-of-bound %s=%s", (key, value) => {
    const { study } = desirabilityFixture(); const draft = { ...defaultDesirabilityDraft(study), [key]: value };
    expect(buildDesirabilityRequest(study, draft).errors).toHaveProperty(key);
  });
  it("does not reorder noise bounds or treat missing fixed SD as zero", () => {
    const { study } = desirabilityFixture(); const draft = defaultDesirabilityDraft(study);
    draft.models[0] = { ...draft.models[0], lower: "1", upper: "1e-6" };
    draft.models[1] = { ...draft.models[1], noise: "fixed", fixedSd: "" };
    expect(buildDesirabilityRequest(study, draft).errors).toMatchObject({ "yield:lower": "bounds", "cost:fixedSd": "positive" });
  });
  it("rejects missing/duplicate response models and leaves scalar policy unavailable", () => {
    const { study } = desirabilityFixture(); const draft = defaultDesirabilityDraft(study);
    draft.models[1] = draft.models[0]; expect(buildDesirabilityRequest(study, draft).errors.models).toBe("mapping");
    study.objective = { name: "scalar", goal_type: "maximize", observation_policy: "manual_single_observation", unit: null, target_value: null, target_tolerance: null, direction: "maximize" };
    expect(buildDesirabilityRequest(study, draft).request).toBeNull();
  });
});
