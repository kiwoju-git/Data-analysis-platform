import { describe, expect, it } from "vitest";

import type { BayesianStudyResponse } from "../../api";
import { observationPasteErrorMessage, parseObservationPaste } from "./bayesianObservationPaste";

const trials = [
  { trial_id: "trial-a", trial_number: 3 },
  { trial_id: "trial-b", trial_number: 8 },
] as BayesianStudyResponse["trials"];

describe("Bayesian observation paste data boundary", () => {
  it("preserves values and pending order for one-column input", () => {
    expect(parseObservationPaste("response\r\n01.20\r\n\r\n3e2", trials)).toEqual({
      values: { "trial-a": "01.20", "trial-b": "3e2" }, error: null,
    });
    expect(parseObservationPaste("관측\n2.50", trials)).toEqual({
      values: { "trial-a": "2.50" }, error: null,
    });
  });

  it("maps explicit trial numbers without changing IDs or numeric source text", () => {
    expect(parseObservationPaste("trial,response\n8,4.00\n3,-2.5", trials)).toEqual({
      values: { "trial-b": "4.00", "trial-a": "-2.5" }, error: null,
    });
    expect(parseObservationPaste("8\t4.00\n3\t-2.5", trials).values).toEqual({
      "trial-b": "4.00", "trial-a": "-2.5",
    });
  });

  it.each([
    ["", "empty"],
    ["response", "header_without_data"],
    ["1\n2\n3", "too_many_values"],
    ["3,1\n2", "column_count"],
    ["NaN", "non_finite_value"],
    ["Infinity", "non_finite_value"],
  ])("returns stable validation code for %j", (content, code) => {
    expect(parseObservationPaste(content, trials)).toEqual({ values: {}, error: { code } });
  });

  it("keeps unknown and duplicate trial identity in error parameters", () => {
    expect(parseObservationPaste("9,1", trials).error).toEqual({
      code: "trial_not_found", params: { trialNumber: "9" },
    });
    expect(parseObservationPaste("3,1\n3,2", trials).error).toEqual({
      code: "duplicate_trial", params: { trialNumber: "3" },
    });
  });

  it("localizes stored errors at display time without decoding user PUA text", () => {
    const raw = "\uE000doe.interactionOrder.mainEffectsOnly\uE001";
    const error = parseObservationPaste(`${raw},1`, trials).error;
    expect(error).toEqual({ code: "trial_not_found", params: { trialNumber: raw } });
    if (error === null) throw new Error("expected validation error");
    expect(observationPasteErrorMessage(error, "ko")).toBe(`pending Trial ${raw}을 찾을 수 없습니다.`);
    expect(observationPasteErrorMessage(error, "en")).toBe(`Pending Trial ${raw} cannot be found.`);
    expect(error).toEqual({ code: "trial_not_found", params: { trialNumber: raw } });
    expect(observationPasteErrorMessage({ code: "empty" }, "ko")).toBe("붙여넣은 관측값이 없습니다.");
    expect(observationPasteErrorMessage({ code: "empty" }, "en")).toBe("There are no observations pasted.");
  });
});
