import { describe, expect, it } from "vitest";

import {
  analysisModuleIdsForProfile,
  isAnalysisModuleAvailableInProfile,
  presentationScopeText,
  resolveStatisticalTwinProfile,
} from "./productProfile";

describe("presentation product profile", () => {
  it("keeps full as the conservative default", () => {
    expect(resolveStatisticalTwinProfile(undefined)).toBe("full");
    expect(resolveStatisticalTwinProfile("unexpected")).toBe("full");
  });

  it("recognizes only the explicit presentation values", () => {
    expect(resolveStatisticalTwinProfile("presentation")).toBe("presentation");
    expect(resolveStatisticalTwinProfile("presentation-regression")).toBe(
      "presentation-regression",
    );
    expect(resolveStatisticalTwinProfile("full")).toBe("full");
  });

  it("keeps the two public analysis scopes distinct", () => {
    expect(analysisModuleIdsForProfile("presentation")).toEqual([
      "exploration",
      "hypothesis",
    ]);
    expect(analysisModuleIdsForProfile("presentation-regression")).toEqual([
      "exploration",
      "hypothesis",
      "regression",
    ]);
    expect(isAnalysisModuleAvailableInProfile("regression", "presentation")).toBe(false);
    expect(
      isAnalysisModuleAvailableInProfile("regression", "presentation-regression"),
    ).toBe(true);
    expect(presentationScopeText("presentation-regression")).toContain(
      "상관관계 및 회귀분석",
    );
  });
});
