import { describe, expect, it } from "vitest";

import {
  isAnalysisDomainAvailableInProfile,
  isAnalysisMethodAvailableInProfile,
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
    expect(resolveStatisticalTwinProfile("presentation-four-domains")).toBe(
      "presentation-four-domains",
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
    expect(presentationScopeText("presentation-regression", "ko")).toContain(
      "상관관계 및 회귀분석",
    );
  });

  it("enables exactly the first four presentation domains", () => {
    const profile = "presentation-four-domains";
    expect(
      [
        "basic-exploration",
        "mean-equivalence",
        "proportions-categorical",
        "correlation-regression-prediction",
      ].every((domainId) => isAnalysisDomainAvailableInProfile(domainId, profile)),
    ).toBe(true);
    expect(
      [
        "doe-optimization",
        "ai-ml-experimental-design",
        "quality-process-monitoring",
        "measurement-variability",
      ].every((domainId) => !isAnalysisDomainAvailableInProfile(domainId, profile)),
    ).toBe(true);
    expect(isAnalysisMethodAvailableInProfile("categorical.two_proportion", profile)).toBe(
      true,
    );
    expect(isAnalysisMethodAvailableInProfile("eda.equal_variances", profile)).toBe(false);
    expect(isAnalysisMethodAvailableInProfile("doe.factorial_design", profile)).toBe(false);
    expect(presentationScopeText(profile, "en")).toContain("Domains 1–4 are available");
  });
});
