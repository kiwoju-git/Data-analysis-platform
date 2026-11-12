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
});
