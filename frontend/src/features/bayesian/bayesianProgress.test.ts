import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import type { BayesianDesirabilityObjective } from "../../api/types/bayesian";
import type { BayesianScalarObjectiveResponse } from "../../api/types/bayesian";
import type { MixedStudyResponse } from "../../api/types/boMixed";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import { buildBayesianProgress, observedDesirability, projectBayesianFactors, factorProgressSourceKey, categoryDisplayTicks } from "./bayesianProgress";

function scalar(goal: "maximize" | "minimize" | "match_target" = "maximize") {
  const { study } = desirabilityFixture();
  study.objective = { name: "Response", unit: "mg", goal_type: goal, direction: goal === "match_target" ? null : goal,
    target_value: goal === "match_target" ? 4 : null, target_tolerance: null, observation_policy: "manual_single_observation" };
  study.trials = [3, 1, 4, 2].map((number, index) => ({ ...study.trials[0], trial_id: `trial-${number}`, trial_number: number,
    objective_value: [6, 2, null, 5][index], state: number === 4 ? "pending" : "completed", response_values: undefined }));
  return study;
}

describe("read-only BO progress", () => {
  it("orders by trial number without changing inputs, excludes unmeasured trials and uses raw units", () => {
    const study = scalar(), before = JSON.stringify(study);
    const result = buildBayesianProgress(study);
    expect(result.rows.map(row => [row.trialNumber, row.value, row.best])).toEqual([[1, 2, 2], [2, 5, 5], [3, 6, 6]]);
    expect(result.unit).toBe("mg"); expect(result.desirability).toBeNull();
    expect(JSON.stringify(study)).toBe(before);
  });
  it("uses cumulative minimum or target distance, not maximum response for every goal", () => {
    expect(buildBayesianProgress(scalar("minimize")).rows.map(row => row.best)).toEqual([2, 2, 2]);
    const target = buildBayesianProgress(scalar("match_target"));
    expect(target.rows.map(row => [row.value, row.distance, row.best])).toEqual([[2, 2, 2], [5, 1, 1], [6, 2, 1]]);
    expect(target.target).toBe(4);
  });
  it("preserves replicates, zero and individual trial identities; does not score abandoned trials", () => {
    const study = scalar();
    study.trials[0] = { ...study.trials[0], origin: "replicate", replicate_of_trial_id: "trial-1", objective_value: 0 };
    study.trials[3].state = "abandoned";
    expect(buildBayesianProgress(study).rows.map(row => row.trialId)).toEqual(["trial-1", "trial-3"]);
    expect(buildBayesianProgress(study).rows[1].value).toBe(0);
  });
  it("reports unavailable values instead of coercing them to zero or silently dropping them", () => {
    const study = scalar(); study.trials[0].objective_value = Number.NaN;
    expect(buildBayesianProgress(study).invalidTrialCount).toBe(1);
    study.trials = []; expect(buildBayesianProgress(study).rows).toEqual([]);
    study.trials = [{ ...scalar().trials[1], objective_value: 1e-10 }];
    expect(buildBayesianProgress(study).rows[0].value).toBe(1e-10);
  });
  it("keeps response IDs and units separate and scores the complete measured vector", () => {
    const { study } = desirabilityFixture();
    const data = buildBayesianProgress(study, "cost");
    expect(data.rows.map(row => row.value)).toEqual([2, 1]); expect(data.unit).toBe("USD");
    expect(data.desirability?.map(row => [row.value, row.best])).toEqual([[0, 0], [1, 1]]);
    expect(buildBayesianProgress(study, "missing").reason).toBe("response_unavailable");
  });
});

describe("observed goal scores (not posterior desirability)", () => {
  it("matches the shared hand-computed backend/display policy fixtures", () => {
    const cases = JSON.parse(readFileSync(new URL("../../../../tests/fixtures/bo_progress_desirability.json", import.meta.url), "utf8")) as Array<{
      name: string; curve_policy: BayesianDesirabilityObjective["curve_policy"]; goals: BayesianDesirabilityObjective["responses"];
      values: Record<string, number>; expected: number;
    }>;
    for (const fixture of cases) {
      const objective = { curve_policy: fixture.curve_policy, responses: fixture.goals } as BayesianDesirabilityObjective;
      const actual = observedDesirability(objective, fixture.values);
      expect(actual, fixture.name).not.toBeNull();
      // Shared 1e-14 absolute tolerance includes subnormal weight rounding.
      expect(Math.abs(actual! - fixture.expected), fixture.name).toBeLessThanOrEqual(1e-14);
    }
  });
  it("matches hand-computed weighted geometric and piecewise DS examples", () => {
    const { study } = desirabilityFixture();
    if (study.objective.goal_type !== "desirability") throw new Error("fixture");
    study.objective.responses[0].importance = 3;
    expect(observedDesirability(study.objective, { yield: .25, cost: 1.5 })).toBeCloseTo(.25 ** .75 * .5 ** .25, 14);
    expect(observedDesirability(study.objective, { yield: -1, cost: 1 })).toBe(0);
    expect(observedDesirability(study.objective, { yield: 2, cost: 0 })).toBe(1);
    expect(observedDesirability(study.objective, { yield: 1 })).toBeNull();
  });
  it("honors asymmetric Gaussian target tails and reports underflow rather than inventing zero", () => {
    const { study } = desirabilityFixture();
    if (study.objective.goal_type !== "desirability") throw new Error("fixture");
    study.objective.curve_policy = "per_response_target_gaussian_or_ds_v1";
    study.objective.responses = [{ response_id: "y", name: "Target", unit: null, goal: "match_target", lower: -2,
      target: 0, upper: 4, importance: 1, curve: { policy: "two_sided_gaussian_target_peak_one_v1", lower_desirability: .2, upper_desirability: .4 } }];
    expect(observedDesirability(study.objective, { y: -2 })).toBeCloseTo(.2, 14);
    expect(observedDesirability(study.objective, { y: 2 })).toBeCloseTo(.4 ** .25, 14);
    expect(observedDesirability(study.objective, { y: 0 })).toBe(1);
    expect(observedDesirability(study.objective, { y: 1e100 })).toBeNull();
    study.objective.responses[0].curve = undefined;
    expect(observedDesirability(study.objective, { y: 2 })).toBe(.5);
  });
});

describe("factor-space projection", () => {
  it("bounds category ticks without changing the underlying level mapping", () => {
    const ticks = Array.from({ length: 32 }, (_, value) => ({ value, label: `긴 이름 ${value}`.repeat(50) }));
    const before = JSON.stringify(ticks), displayed = categoryDisplayTicks(ticks);
    expect(displayed!.length).toBeLessThanOrEqual(8);
    expect(displayed!.every(tick => tick.label.length <= 3)).toBe(true);
    expect(displayed![0]).toEqual({ value: 0, label: "#1" });
    expect(displayed!.at(-1)).toEqual({ value: 31, label: "#32" });
    expect(JSON.stringify(ticks)).toBe(before);
  });
  it("invalidates source identity on pending creation and abandonment even when completed history is unchanged", () => {
    const study = scalar(), key = factorProgressSourceKey(study);
    const same = structuredClone(study);
    expect(factorProgressSourceKey(same)).toBe(key);
    same.trials.find(trial => trial.state === "pending")!.state = "abandoned";
    expect(factorProgressSourceKey(same)).not.toBe(key);
    same.trials = [...study.trials, { ...study.trials[2], trial_id: "new-pending", trial_number: 5 }];
    expect(factorProgressSourceKey(same)).not.toBe(key);
  });
  it("preserves categorical identities and pending/abandoned points without numeric interpolation", () => {
    const { study } = desirabilityFixture();
    const mixed = { ...study, factors: [study.factors[0], { factor_id: "material", name: "Material", unit: null,
      order: 1, domain_kind: "nominal", levels: ["10", "2", "한글"], correlation_policy: "equal_positive_correlation_v1", encoding_rule: "declared_level_index_v1" }],
      trials: study.trials.map((trial, index) => ({ ...trial, actual_coordinates: { x: index, material: index ? "한글" : "10" }, state: index ? "pending" : "abandoned" })) } as unknown as MixedStudyResponse;
    const result = projectBayesianFactors(mixed, "material", "x");
    expect(result.points.map(row => [row.x, row.y, row.state])).toEqual([[0, 0, "abandoned"], [2, 1, "pending"]]);
    expect(result.xTicks?.map(tick => tick.label)).toEqual(["10", "2", "한글"]);
    expect(projectBayesianFactors(mixed, "x", "x").reason).toBe("distinct_factors_required");
    mixed.trials[0].actual_coordinates.material = "unknown";
    expect(projectBayesianFactors(mixed, "material", "x").invalidTrialCount).toBe(1);
  });
  it("does not mutate target definition or infer physical time from trial numbers", () => {
    const study = scalar("match_target");
    const goal = study.objective as BayesianScalarObjectiveResponse;
    expect(goal.target_value).toBe(4); buildBayesianProgress(study); expect(goal.target_value).toBe(4);
  });
});
