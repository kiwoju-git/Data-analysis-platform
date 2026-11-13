import { describe, expect, it } from "vitest";
import { buildDatasetImportRequest, type DatasetImportDraft } from "./boDatasetImportDraft";
import { newMixedFactor } from "./boMixedDraft";
import { newResponseDraft } from "./bayesianVectorDraft";

const version = { version_id: "version", schema_hash: "a".repeat(64), columns: [
  { column_id: "x", display_name: "실험 X", unit: "C" },
  { column_id: "y", display_name: "측정 Y", unit: "g" },
] };
function draft(): DatasetImportDraft {
  return { name: "Study", factors: [{ ...newMixedFactor(1), columnId: "x", low: "-1", high: "1" }],
    responseMode: "scalar", scalarColumnId: "y", goal: "maximize", target: "", tolerance: "",
    responses: [newResponseDraft(1)], responseColumns: {}, constraints: [], missingPolicy: "reject" };
}
describe("measured X/Y import request", () => {
  it("permits an explicit short display alias without truncating or renaming the original column", () => {
    const longVersion = { ...version, columns: version.columns.map(column => ({ ...column, display_name: column.display_name.repeat(30) })) };
    const input = draft();
    expect(typeof buildDatasetImportRequest(longVersion, { expression_version: 1, conditions: [] }, input)).toBe("string");
    input.displayNames = { x: "X alias", y: "Y alias" };
    const result = buildDatasetImportRequest(longVersion, { expression_version: 1, conditions: [] }, input);
    expect(result).toMatchObject({ factor_mappings: [{ column_id: "x", factor: { name: "X alias" } }], objective: { name: "Y alias" } });
    expect(longVersion.columns[0].display_name).toBe(version.columns[0].display_name.repeat(30));
  });
  it("uses column identities and original names without generated X/seed metadata", () => {
    const input = draft(), before = JSON.stringify(input);
    const result = buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input);
    expect(typeof result).not.toBe("string");
    if (typeof result === "string") return;
    expect(result.factor_mappings[0]).toMatchObject({ column_id: "x", factor: { name: "실험 X", unit: "C", low: -1, high: 1 } });
    expect(result.response_mappings).toEqual([{ column_id: "y", response_id: null }]);
    expect(result.objective.name).toBe("측정 Y");
    expect(result).not.toHaveProperty("initial_design_seed");
    expect(JSON.stringify(input)).toBe(before);
  });
  it.each(["", " ", "1abc", "Infinity"])("rejects invalid bounds %s without coercing to zero", value => {
    const input = draft(); input.factors[0].low = value;
    expect(typeof buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("string");
  });
  it("rejects duplicate X/Y mapping and missing target", () => {
    const input = draft(); input.scalarColumnId = "x";
    expect(typeof buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("string");
    input.scalarColumnId = "y"; input.goal = "match_target";
    expect(typeof buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("string");
  });
  it("keeps explicit filters and complete case policy", () => {
    const input = draft(); input.missingPolicy = "complete_case";
    const filter = { expression_version: 1, conditions: [{ column_id: "x", operator: "gt" as const, value: 0 }] };
    expect(buildDatasetImportRequest(version, filter, input)).toMatchObject({ filter_snapshot: filter, missing_policy: "complete_case" });
  });
  it("preserves category identities and uses explicit desirability response mapping", () => {
    const input = draft(); input.responseMode = "vector"; input.responseColumns = { response_1: "y" };
    input.responses[0] = { ...input.responses[0], lower: "0", target: "100" };
    input.factors[0] = { ...input.factors[0], kind: "nominal", levels: ["한글 ×", "1"] };
    const result = buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input);
    expect(result).toMatchObject({ factor_mappings: [{ factor: { domain_kind: "nominal", levels: ["한글 ×", "1"] } }], response_mappings: [{ column_id: "y", response_id: "response_1" }] });
  });
  it("serializes actual-unit constraints without adding blank coefficient terms", () => {
    const input = draft();
    input.factors.push({ ...newMixedFactor(2), columnId: "z" });
    input.constraints = [{ key: 3, name: "온도 제한", relation: "greater_than_or_equal", bound: "-0.25", coefficients: { factor_1: "1.5", factor_2: "" } }];
    const source = { ...version, columns: [...version.columns, { column_id: "z", display_name: "보조 X", unit: null }] };
    expect(buildDatasetImportRequest(source, { expression_version: 1, conditions: [] }, input)).toMatchObject({
      constraints: [{ constraint_id: "constraint_3", name: "온도 제한", relation: "greater_than_or_equal", bound: -0.25, terms: [{ factor_id: "factor_1", coefficient: 1.5 }] }],
    });
  });
  it.each(["", "1abc", "Infinity", "1e999"])("blocks invalid constraint bound %s without changing the string draft", value => {
    const input = draft(); input.constraints = [{ key: 1, name: "제약", relation: "less_than_or_equal", bound: value, coefficients: { factor_1: "1" } }];
    expect(buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("bayesian_constraints_invalid");
    expect(input.constraints[0].bound).toBe(value);
  });
  it.each(["1abc", "Infinity", "1e999"])("blocks invalid constraint coefficient %s", value => {
    const input = draft(); input.constraints = [{ key: 1, name: "제약", relation: "less_than_or_equal", bound: "1", coefficients: { factor_1: value } }];
    expect(buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("bayesian_constraints_invalid");
  });
  it.each(["equal_positive_correlation_v1", "unequal_hyperspherical_correlation_v1", "ordinal_monotone_latent_rbf_v1"] as const)("preserves explicit category policy %s and Korean levels", correlation => {
    const input = draft(); input.responseMode = "vector"; input.responseColumns = { response_1: "y" };
    input.responses[0] = { ...input.responses[0], lower: "0", target: "100" };
    input.factors[0] = { ...input.factors[0], kind: "ordinal", levels: ["낮음", "높음"], correlation };
    expect(buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toMatchObject({ factor_mappings: [{ factor: { name: "실험 X", levels: ["낮음", "높음"], correlation_policy: correlation } }] });
    input.constraints = [{ key: 1, name: "잘못된 제약", relation: "less_than_or_equal", bound: "1", coefficients: { factor_1: "1" } }];
    expect(buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("bayesian_constraints_invalid");
  });
  it("blocks nominal use of ordinal-only policy and preserves existing category budgets", () => {
    const input = draft(); input.factors[0] = { ...input.factors[0], kind: "nominal", levels: ["낮음", "높음"], correlation: "ordinal_monotone_latent_rbf_v1" };
    expect(buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("bayesian_category_correlation_policy_invalid");
    input.factors[0].correlation = "unequal_hyperspherical_correlation_v1"; input.factors[0].levels = Array.from({ length: 9 }, (_, index) => String(index));
    expect(buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toBe("bayesian_category_correlation_policy_invalid");
  });
});
