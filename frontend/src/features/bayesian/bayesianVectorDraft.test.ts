import { describe, expect, it } from "vitest";
import { buildVectorObjective, vectorObservationEntries, vectorDraftCell, newResponseDraft } from "./bayesianVectorDraft";

describe("measured vector drafts", () => {
  it("keeps goals separate from measured units and omits unused thresholds", () => {
    const result = buildVectorObjective("Quality", [
      { ...newResponseDraft(1), name: "수율", lower: "-1e-6", target: "0", upper: "unused" },
      { ...newResponseDraft(2), goal: "minimize", lower: "unused", target: "1", upper: "2", importance: "3" },
    ]);
    expect(result).toMatchObject({ goal_type: "desirability", responses: [
      { response_id: "response_1", name: "수율", lower: -1e-6, target: 0, upper: null },
      { response_id: "response_2", lower: null, target: 1, upper: 2, importance: 3 },
    ] });
  });
  it.each(["", " ", "-", "1e", "0x10", "1abc", "NaN", "Infinity"])("rejects invalid goal %j without changing draft", value => {
    const draft = { ...newResponseDraft(1), target: value };
    expect(typeof buildVectorObjective("Q", [draft])).toBe("string");
    expect(draft.target).toBe(value);
  });
  it("rejects order, duplicate IDs, nonpositive importance and response limits", () => {
    const valid = { ...newResponseDraft(1), lower: "0", target: "1" };
    for (const rows of [[{ ...valid, target: "0" }], [valid, valid], [{ ...valid, importance: "0" }], [], Array.from({ length: 5 }, (_, i) => ({ ...valid, responseId: `r${i}` }))]) {
      expect(typeof buildVectorObjective("Q", rows)).toBe("string");
    }
  });
  it("saves only complete touched pending rows; zero is a real measurement", () => {
    expect(vectorObservationEntries(["a", "b"], ["r1", "r2"], { a: { r1: "0", r2: "1e-8" } })).toEqual([
      { trial_id: "a", response_values: { r1: 0, r2: 1e-8 } },
    ]);
    expect(typeof vectorObservationEntries(["a"], ["r1", "r2"], { a: { r1: "0", r2: "" } })).toBe("string");
    expect(typeof vectorObservationEntries(["a"], ["r1"], { b: { r1: "1" } })).toBe("string");
    expect(typeof vectorObservationEntries(["a"], ["r1"], { a: { r1: "1", other: "2" } })).toBe("string");
    expect(typeof vectorObservationEntries(["a"], ["r1"], {})).toBe("string");
  });
  it("does not read Object prototype values for valid API response IDs", () => {
    const draft = { a: { cost: "2" } };
    expect(vectorDraftCell(draft, "a", "constructor")).toBe("");
    expect(typeof vectorObservationEntries(["a"], ["cost", "constructor", "toString"], draft)).toBe("string");
    expect(vectorObservationEntries(["a"], ["constructor", "toString"], { a: { constructor: "0", toString: "1" } })).toEqual([
      { trial_id: "a", response_values: { constructor: 0, toString: 1 } },
    ]);
  });
});
