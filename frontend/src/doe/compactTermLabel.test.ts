import { expect, it } from "vitest";
import type { DoeAnalysisTerm } from "../api/types/doeModelWorkflow";
import { compactTermLabel } from "./compactTermLabel";

const term: DoeAnalysisTerm = {
  term_id: "factor_1:factor_2", kind: "interaction", label: "factor_2 * A × B = C",
  factor_ids: ["factor_2", "A × B = C"], order: 2, hierarchy_dependencies: [],
  hierarchy_role: "factorial_term", default_disposition: "candidate", df: 1, estimable: true,
};
it("uses canonical term IDs, never interpreting a user factor name as an ID", () => {
  expect(compactTermLabel(term, "coded", term.factor_ids)).toBe("AB");
  expect(compactTermLabel({ ...term, term_id: "factor_1", kind: "main_effect", factor_ids: ["factor_2"] }, "coded", term.factor_ids)).toBe("A");
});
it("maps treatment factor names without splitting user labels or term IDs", () => {
  expect(compactTermLabel({ ...term, term_id: "factor_2:A × B = C" }, "treatment", term.factor_ids)).toBe("AB");
  expect(compactTermLabel(term, "treatment", [])).toBeNull();
});
