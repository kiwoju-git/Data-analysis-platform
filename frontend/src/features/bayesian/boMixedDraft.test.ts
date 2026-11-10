import { describe, expect, it } from "vitest";
import { buildMixedObservations, buildMixedStudyRequest, newMixedFactor, parseMixedCandidatePaste, parseMixedPoint, validMixedStudy, validateMixedCoordinates } from "./boMixedDraft";
import { mixedStudyFixture } from "./boMixed.test.fixture";

function draft() {
  const study = mixedStudyFixture();
  return { name: "Mixed raw", objective: study.objective, seed: "42", size: "8", constraints: [], factors: [newMixedFactor(1), newMixedFactor(2, "nominal")] };
}
describe("mixed factor source identities", () => {
  it("preserves complete category labels, numeric-looking strings and declared order", () => {
    const value = draft(); value.factors[1].levels = ["001", "1", " 한글 ", "A*B", "X".repeat(200)];
    value.factors[1].kind = "ordinal"; value.factors[1].correlation = "ordinal_monotone_latent_rbf_v1";
    const before = JSON.stringify(value), result = buildMixedStudyRequest(value);
    expect(typeof result).not.toBe("string");
    if (typeof result !== "string") expect(result.factors[1]).toMatchObject({ levels: value.factors[1].levels, domain_kind: "ordinal", correlation_policy: "ordinal_monotone_latent_rbf_v1" });
    expect(JSON.stringify(value)).toBe(before);
  });
  it("does not infer ordinal distance or normalize nominal codes as coordinates", () => {
    const study = mixedStudyFixture();
    expect(validMixedStudy(study, study.study_id)).toBe(true);
    expect(validateMixedCoordinates({ x: .5, material: "001" }, { x: .5, material: 0 }, study.factors)).toBe(true);
    expect(validateMixedCoordinates({ x: .5, material: 1 }, { x: .5, material: 0 }, study.factors)).toBe(false);
    expect(validateMixedCoordinates({ x: .5, material: "한글 A" }, { x: .5, material: .5 }, study.factors)).toBe(false);
    expect(parseMixedPoint({ x: "0.25", material: "001" }, study.factors)).toEqual({ x: .25, material: "001" });
    expect(parseMixedPoint({ x: "0.25", material: "1" }, study.factors)).toBeNull();
  });
  it("rejects invalid level policies and parameter budgets, not coercing them", () => {
    for (const levels of [["A", "A"], ["A", ""], ["A", " \t"], ["A"], Array.from({ length: 33 }, (_, i) => String(i))]) {
      const value = draft(); value.factors[1].levels = levels; expect(typeof buildMixedStudyRequest(value)).toBe("string");
    }
    const latent = draft(); latent.factors[1].correlation = "ordinal_monotone_latent_rbf_v1"; expect(buildMixedStudyRequest(latent)).toBe("bayesian_category_correlation_policy_invalid");
    const unequal = draft(); unequal.factors[1].correlation = "unequal_hyperspherical_correlation_v1"; unequal.factors[1].levels = Array.from({ length: 9 }, (_, i) => String(i));
    expect(buildMixedStudyRequest(unequal)).toBe("bayesian_category_correlation_policy_invalid");
    const many = draft(); many.factors = Array.from({ length: 3 }, (_, i) => ({ ...newMixedFactor(i + 1, "nominal"), levels: Array.from({ length: 8 }, (_, j) => String(j)), correlation: "unequal_hyperspherical_correlation_v1" as const }));
    expect(buildMixedStudyRequest(many)).toBe("bayesian_category_parameter_budget_exceeded");
  });
  it("validates numeric lattice bounds and strict design size without silently rounding", () => {
    const value = draft(); value.factors[0] = { ...value.factors[0], kind: "discrete_numeric", low: "1000.1", high: "1000.4", step: "0.1" };
    expect(typeof buildMixedStudyRequest(value)).not.toBe("string");
    for (const size of ["", "2", "5.5", "5abc", "NaN", "65"]) expect(typeof buildMixedStudyRequest({ ...value, size })).toBe("string");
    value.factors[0].high = "1000.45"; expect(buildMixedStudyRequest(value)).toBe("bayesian_factor_domain_invalid");
  });
  it("allows numeric constraints only and never assigns category labels a coefficient", () => {
    const value = draft();
    const constraint = { key: 1, name: "Bound", relation: "less_than_or_equal" as const, bound: "1", coefficients: { factor_1: "1" } };
    expect(typeof buildMixedStudyRequest({ ...value, constraints: [constraint] })).not.toBe("string");
    expect(buildMixedStudyRequest({ ...value, constraints: [{ ...constraint, coefficients: { factor_2: "1" } }] })).toBe("bayesian_constraints_invalid");
    expect(buildMixedStudyRequest({ ...value, constraints: [{ ...constraint, coefficients: { factor_1: "1e" } }] })).toBe("bayesian_constraints_invalid");
  });
  it("imports mixed CSV without numeric conversion of category identity or partial acceptance", () => {
    const study = mixedStudyFixture();
    expect(parseMixedCandidatePaste('x,material\n0.25,"001"\n0.75,"한글 A"', study.factors, true)).toEqual([{ x: .25, material: "001" }, { x: .75, material: "한글 A" }]);
    expect(parseMixedCandidatePaste("0.25,1", study.factors, false)).toBeNull();
    expect(parseMixedCandidatePaste("0.25,001\nNaN,한글 A", study.factors, false)).toBeNull();
    expect(parseMixedCandidatePaste("0.25,001\n0.25,001", study.factors, false)).toBeNull();
  });
  it("rejects mismatched source owner, category code and invented observation vectors", () => {
    const study = mixedStudyFixture(), wrong = structuredClone(study);
    expect(validMixedStudy(study, "00000000-0000-0000-0000-000000000000")).toBe(false);
    wrong.trials[0].encoded_coordinates.material = 1; expect(validMixedStudy(wrong)).toBe(false);
    const pending = mixedStudyFixture(false); pending.trials[0].response_values = { yield: 0, cost: 0 }; expect(validMixedStudy(pending)).toBe(false);
  });
  it("accepts actual zero and requires complete response vectors for each entered trial", () => {
    const study = mixedStudyFixture(false), id = study.trials[0].trial_id;
    const request = buildMixedObservations(study, { [id]: { yield: "0", cost: "1e-8" } }, "same-request");
    expect(typeof request).not.toBe("string");
    if (typeof request !== "string") expect(request.observations).toEqual([{ trial_id: id, response_values: { yield: 0, cost: 1e-8 } }]);
    for (const values of [{ yield: "", cost: "1" }, { yield: "1e", cost: "1" }, { yield: "1", cost: "" }]) expect(typeof buildMixedObservations(study, { [id]: values }, "request")).toBe("string");
  });
});
