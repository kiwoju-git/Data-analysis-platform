import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { BayesianResponseGoals } from "./BayesianResponseGoals";
import { buildVectorObjective, newResponseDraft } from "./bayesianVectorDraft";

const rows = (n: number) => Array.from({ length: n }, (_, i) => ({ ...newResponseDraft(i + 1), lower: "0", target: "10" }));
describe("six-response desirability capacity", () => {
  it.each([1, 4, 5, 6])("preserves all %i response goals and their identities", count => {
    const result = buildVectorObjective("Goals", rows(count));
    expect(result).not.toBeTypeOf("string");
    if (typeof result === "string") throw new Error(result);
    expect(result.responses.map(row => row.response_id)).toEqual(rows(count).map(row => row.responseId));
  });
  it("rejects a seventh response", () => {
    expect(buildVectorObjective("Goals", rows(7))).toBe("bayesian_vector_goals_invalid");
  });
  it.each([4, 5, 6])("enables Add response until the sixth row (%i)", count => {
    const html = renderToStaticMarkup(<BayesianResponseGoals draft={{ responseGoals: rows(count),
      updateResponseGoal: () => undefined, removeResponseGoal: () => undefined, addResponseGoal: () => undefined }} />);
    const add = html.match(/<button[^>]*>[^]*?반응 추가<\/button>/g)?.at(-1) ?? "";
    expect(add).not.toBe("");
    // Inspect the last button opening tag, not earlier disabled remove controls.
    const opening = add.slice(add.lastIndexOf("<button"), add.lastIndexOf("<button") + add.slice(add.lastIndexOf("<button")).indexOf(">"));
    expect(opening.includes("disabled")).toBe(count === 6);
  });
});
