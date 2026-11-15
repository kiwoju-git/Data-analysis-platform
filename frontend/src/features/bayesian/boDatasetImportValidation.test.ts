import { describe, expect, it } from "vitest";
import * as validation from "./boDatasetImportDraft";
import { newMixedFactor } from "./boMixedDraft";
import { newResponseDraft } from "./bayesianVectorDraft";

const version = { version_id: "version", schema_hash: "a".repeat(64), columns: [
  { column_id: "x", display_name: "Original X", unit: "C" },
  { column_id: "y", display_name: "Original Y", unit: null },
  { column_id: "z", display_name: "Original Z", unit: null },
] };
function draft(): validation.DatasetImportDraft {
  return { name: "Study", factors: [{ ...newMixedFactor(3), columnId: "x", low: "0", high: "10" }],
    responseMode: "vector", scalarColumnId: "y", goal: "maximize", target: "", tolerance: "",
    responses: [{ ...newResponseDraft(7), lower: "0", target: "100" }],
    responseColumns: { response_7: "y" }, constraints: [], missingPolicy: "reject" };
}
// Keeping the existing module import allows the initial red run to assert the
// missing behavior rather than fail during module resolution.
const issues = (input: validation.DatasetImportDraft, source: validation.ImportVersion = version) => {
  expect(validation).toHaveProperty("datasetImportFieldIssues");
  return validation.datasetImportFieldIssues(source, input);
};
describe("BO import field feedback", () => {
  it("identifies missing name and all missing response targets together", () => {
    const input = draft(); input.name = " "; input.responses[0].target = "";
    input.responses.push({ ...newResponseDraft(9), lower: "10", target: "" });
    input.responseColumns.response_9 = "z";
    expect(issues(input)).toEqual([
      { field: "name", code: "required" },
      { field: "response.7.target", code: "required" },
      { field: "response.9.target", code: "required" },
    ]);
  });
  it.each(["", " ", "1abc", "Infinity", "1e", "1e999"])("identifies bad bound %j without coercion", value => {
    const input = draft(); input.factors[0].low = value;
    const before = JSON.stringify(input);
    expect(issues(input)).toContainEqual({ field: "factor.3.low", code: value.trim() ? "finiteNumber" : "required" });
    expect(JSON.stringify(input)).toBe(before);
  });
  it("marks both bounds of a reversed or overflowing interval", () => {
    for (const [low, high, code] of [["10", "0", "boundOrder"], ["-1e308", "1e308", "finiteSpan"]]) {
      const input = draft(); Object.assign(input.factors[0], { low, high });
      expect(issues(input)).toEqual([{ field: "factor.3.low", code }, { field: "factor.3.high", code }]);
    }
  });
  it("checks all shared column identities, not display names", () => {
    const input = draft(); input.responseColumns.response_7 = "x";
    expect(issues(input)).toEqual([{ field: "factor.3.column", code: "duplicateColumn" }, { field: "response.7.column", code: "duplicateColumn" }]);
    input.responseColumns.response_7 = "gone";
    expect(issues(input)).toContainEqual({ field: "response.7.column", code: "selectColumn" });
  });
  it("checks only active thresholds and preserves valid zero/scientific notation", () => {
    const input = draft(); input.factors[0].low = "-0"; input.factors[0].high = "1e1";
    input.responses[0] = { ...input.responses[0], lower: "0", target: "1e-6", upper: "invalid but unused" };
    const before = validation.buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input);
    expect(issues(input)).toEqual([]);
    expect(validation.buildDatasetImportRequest(version, { expression_version: 1, conditions: [] }, input)).toEqual(before);
    input.responses[0].goal = "minimize"; input.responses[0].lower = ""; input.responses[0].upper = "2e-6";
    expect(issues(input)).toEqual([]);
  });
  it("identifies goal order and nonpositive importance without editing the draft", () => {
    const input = draft(); Object.assign(input.responses[0], { goal: "match_target", lower: "10", target: "5", upper: "3", importance: "0" });
    expect(issues(input)).toEqual([
      { field: "response.7.lower", code: "lowerTargetOrder" },
      { field: "response.7.target", code: "lowerTargetOrder" },
      { field: "response.7.upper", code: "targetUpperOrder" },
      { field: "response.7.importance", code: "positiveNumber" },
    ]);
  });
  it("does not require a scalar target until match-target is selected", () => {
    const input = draft(); input.responseMode = "scalar";
    expect(issues(input)).toEqual([]);
    input.goal = "match_target"; input.tolerance = "0";
    expect(issues(input)).toEqual([{ field: "target", code: "required" }, { field: "tolerance", code: "positiveNumber" }]);
  });
  it("identifies discrete step mismatch and invalid category levels", () => {
    const input = draft(); Object.assign(input.factors[0], { kind: "discrete_numeric", step: "3" });
    expect(issues(input)).toContainEqual({ field: "factor.3.step", code: "stepLattice" });
    Object.assign(input.factors[0], { kind: "nominal", levels: ["Long identity", "Long identity"] });
    expect(issues(input)).toContainEqual({ field: "factor.3.levels", code: "categoryLevels" });
    input.factors[0].levels = ["A", "B"]; input.responseMode = "scalar";
    expect(issues(input)).toContainEqual({ field: "responseMode", code: "vectorRequired" });
  });
  it("keeps field ownership stable after row removal and exposes display aliases", () => {
    const input = draft(); input.factors.push({ ...newMixedFactor(5), columnId: "z", low: "" });
    input.factors.shift(); input.displayNames = { z: " " };
    expect(issues(input)).toContainEqual({ field: "factor.5.low", code: "required" });
    expect(issues(input)).toContainEqual({ field: "display.z", code: "displayName" });
  });
  it("preserves a valid fixed mixture component while two other components vary", () => {
    const source = { ...version, columns: [...version.columns, { column_id: "w", display_name: "Component C", unit: null }] };
    const input = draft(); input.mixture = { total: "1", unit: "g", coding: "auto", componentKeys: [3, 4, 5] };
    Object.assign(input.factors[0], { low: "0.2", high: "0.2" });
    input.factors.push({ ...newMixedFactor(4), columnId: "z" }, { ...newMixedFactor(5), columnId: "w" });
    const request = validation.buildDatasetImportRequest(source, { expression_version: 1, conditions: [] }, input);
    expect(typeof request).not.toBe("string");
    expect(issues(input, source)).toEqual([]);
    input.factors[0].low = "0.3";
    expect(issues(input, source)).toContainEqual({ field: "factor.3.low", code: "mixtureBoundOrder" });
  });
});
