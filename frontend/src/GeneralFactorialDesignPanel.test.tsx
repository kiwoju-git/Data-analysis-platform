import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GeneralFactorialDesignPanel } from "./GeneralFactorialDesignPanel";
import {
  parsePastedLevels,
  threeLevelPresetLevels,
  validateGeneralDraft,
  type GeneralFactorDraft,
} from "./generalFactorialDraft";

function factor(
  id: string,
  levelType: GeneralFactorDraft["levelType"],
  levels: string[],
): GeneralFactorDraft {
  return {
    id,
    name: id,
    levelType,
    levels,
    unit: "",
    expanded: false,
    pasteDraft: "",
  };
}

describe("GeneralFactorialDesignPanel", () => {
  it("renders explicit level types, counts, editors, and the three-level preset", () => {
    const html = renderToString(<GeneralFactorialDesignPanel />);

    expect(html).toContain("수준 유형");
    expect(html).toContain("숫자 수준");
    expect(html).toContain("문자 수준");
    expect(html).toContain("모든 요인을 3수준으로 설정");
    expect(html).toContain("수준 붙여넣기");
    expect(html).toContain("treatment coding");
  });

  it("parses newline or comma pasted levels while preserving order", () => {
    expect(parsePastedLevels("A\nB\nC")).toEqual(["A", "B", "C"]);
    expect(parsePastedLevels("High, Middle, Low")).toEqual(["High", "Middle", "Low"]);
  });

  it("preserves endpoints and existing values in the three-level preset", () => {
    expect(threeLevelPresetLevels(["Low", "High"])).toEqual(["Low", "", "High"]);
    expect(threeLevelPresetLevels(["60", "70", "80"])).toEqual(["60", "70", "80"]);
    expect(threeLevelPresetLevels(["A", "B", "C", "D"])).toEqual(["A", "B", "D"]);
  });

  it("builds mixed 2 by 3 by 5 levels without sorting or coercing text", () => {
    const validation = validateGeneralDraft(
      "mixed levels",
      [
        factor("Temperature", "numeric", ["60", "80"]),
        factor("Material", "categorical", ["C", "A", "B"]),
        factor("Batch", "numeric", ["1", "2", "3", "4", "5"]),
      ],
      "1",
      "17",
      true,
      "3",
    );

    expect(validation.runCount).toBe(30);
    expect(validation.request?.factors[0]?.levels).toEqual([60, 80]);
    expect(validation.request?.factors[1]?.levels).toEqual(["C", "A", "B"]);
  });

  it("accepts ten levels and rejects blank or duplicate levels", () => {
    const tenLevels = Array.from({ length: 10 }, (_, index) => String(index + 1));
    expect(
      validateGeneralDraft(
        "ten levels",
        [factor("A", "numeric", tenLevels), factor("B", "categorical", ["x", "y"])],
        "1",
        "1",
        false,
        "2",
      ).request,
    ).not.toBeNull();
    expect(
      validateGeneralDraft(
        "blank",
        [factor("A", "numeric", ["1", ""]), factor("B", "categorical", ["x", "y"])],
        "1",
        "1",
        false,
        "2",
      ).request,
    ).toBeNull();
    expect(
      validateGeneralDraft(
        "duplicate",
        [factor("A", "numeric", ["1", "1.0"]), factor("B", "categorical", ["x", "y"])],
        "1",
        "1",
        false,
        "2",
      ).request,
    ).toBeNull();
  });
});
