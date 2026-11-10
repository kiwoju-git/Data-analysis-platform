import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { buildVectorObjective, newResponseDraft } from "./bayesianVectorDraft";
import { buildDesirabilityRequest, defaultDesirabilityDraft } from "./bayesianDesirabilityDraft";
import { desirabilityFixture } from "./bayesianDesirability.fixture";
import { BayesianCurveSummary } from "./BayesianCurvePolicy";

const draft = () => ({...newResponseDraft(1), name: "측정 <raw>", goal: "match_target" as const, lower: "36", target: "38", upper: "40", curve: "gaussian_target" as const});
describe("versioned target policy", () => {
  it("requires explicit curve opt-in and never adds curve defaults to legacy JSON", () => {
    const gaussian = buildVectorObjective("Q", [draft()]);
    expect(gaussian).toMatchObject({curve_policy: "per_response_target_gaussian_or_ds_v1", responses: [{curve: {lower_desirability: .0183, upper_desirability: .0183}}]});
    const old = buildVectorObjective("Q", [{...draft(), curve: "linear"}]);
    expect(old).toMatchObject({curve_policy: "derringer_suich_linear_v1"});
    expect(JSON.stringify(old)).not.toContain("lower_desirability");
  });
  it.each(["", "0", "1", "NaN", "-0.1", "1abc"])("rejects side ordinate %s", value => {
    expect(typeof buildVectorObjective("Q", [{...draft(), lowerDesirability: value}])).toBe("string");
  });
  it.each(["1", "2", "8"])("routes q%s through schema7 without changing user or preview data", batchSize => {
    const {study} = desirabilityFixture();
    const objective = buildVectorObjective("Q", [draft()]);
    if (typeof objective === "string") throw new Error(objective);
    study.objective = objective; study.study_schema_version = 6;
    const before = JSON.stringify(study);
    const request = buildDesirabilityRequest(study, {...defaultDesirabilityDraft(study), batchSize}).request;
    expect(request).toMatchObject({schema_version: 7, batch_size: Number(batchSize), fit_policy: null});
    expect(request).not.toHaveProperty("objective");
    expect(JSON.stringify(study)).toBe(before);
    expect(renderToStaticMarkup(<BayesianCurveSummary responses={objective.responses} />)).toContain("측정 &lt;raw&gt;");
  });
});
