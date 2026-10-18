import { afterEach, describe, expect, it } from "vitest";
import { setCurrentLocale } from "./i18n/store";

import {
  analysisMethodGuidance,
  analysisMethodGuidanceIds,
  getAnalysisMethodGuidance,
  getMethodCardTags,
} from "./analysisMethodGuidance";

describe("analysis method card guidance", () => {
  afterEach(() => setCurrentLocale("ko"));

  it("separates OLS inference from penalty-model guidance in both locales", () => {
    for (const locale of ["en", "ko"] as const) {
      const guidance = getAnalysisMethodGuidance("regression.linear_model", locale);
      const description = guidance.plainLanguage ?? "";
      expect(description).toContain("Ridge");
      expect(description).toContain("Lasso");
      expect(description).toContain("Elastic Net");
      const inference = guidance.resultFocus[1];
      expect(inference).toContain(locale === "en" ? "OLS only" : "OLS 전용");
      const options = guidance.optionChecklist.join(" ");
      expect(options).toContain(locale === "en" ? "nested CV" : "중첩 CV");
    }
  });
  it("keeps concise selection tags for every grouped hypothesis method", () => {
    const hypothesisMethodIds = [
      "hypothesis.one_sample_t",
      "hypothesis.paired_t",
      "hypothesis.two_sample_t",
      "hypothesis.equivalence_tost",
      "hypothesis.paired_equivalence_tost",
      "hypothesis.two_sample_equivalence_tost",
      "hypothesis.one_way_anova",
      "hypothesis.one_sample_wilcoxon",
      "hypothesis.mann_whitney",
      "hypothesis.kruskal_wallis",
    ];

    for (const methodId of hypothesisMethodIds) {
      const tags = getMethodCardTags(methodId, "ko");
      expect(tags.length, methodId).toBeGreaterThanOrEqual(3);
      expect(tags.length, methodId).toBeLessThanOrEqual(4);
      expect(tags.every((tag) => tag.label.trim().length > 0), methodId).toBe(true);
    }
  });

  it("uses study design guidance instead of a sample-size switch", () => {
    const tTest = getAnalysisMethodGuidance("hypothesis.one_sample_t", "ko");
    const wilcoxon = getAnalysisMethodGuidance("hypothesis.one_sample_wilcoxon", "ko");

    expect(getMethodCardTags(tTest.methodId, "ko").map((tag) => tag.label)).toEqual(
      expect.arrayContaining(["연속형 수치", "한 모집단", "평균 비교", "독립 관측"]),
    );
    expect(wilcoxon.plainLanguage).toContain("자동 대체 검정은 아닙니다");
    expect(JSON.stringify([tTest, wilcoxon])).not.toMatch(/N\s*[<>]=?\s*30/);
  });

  it("describes categorical choices without limiting chi-square to three categories", () => {
    expect(
      getMethodCardTags("categorical.one_proportion", "ko").map((tag) => tag.label),
    ).toContain("관심 사건·비사건");
    expect(
      getMethodCardTags("categorical.chi_square_association", "ko").map(
        (tag) => tag.label,
      ),
    ).toContain("2×2 이상 분할표");
  });

  it("provides concise I-MR and run-chart distinctions", () => {
    expect(
      getMethodCardTags("quality.individuals_chart", "ko").map((tag) => tag.label),
    ).toEqual(
      expect.arrayContaining(["개별 관측", "관리한계·특별원인"]),
    );
    expect(
      getMethodCardTags("quality.run_chart", "ko").map((tag) => tag.label),
    ).toContain("관리한계 없음");
  });

  it("localizes every display field without changing static guidance or identity", () => {
    const source = JSON.stringify(analysisMethodGuidance);
    for (const methodId of analysisMethodGuidanceIds) {
      const korean = getAnalysisMethodGuidance(methodId, "ko");
      const english = getAnalysisMethodGuidance(methodId, "en");
      expect(english.methodId).toBe(methodId);
      expect(english.cardTags?.map((tag) => tag.category)).toEqual(
        korean.cardTags?.map((tag) => tag.category),
      );
      expect(english.roleRequirements.map((role) => role.required)).toEqual(
        korean.roleRequirements.map((role) => role.required),
      );
      expect(JSON.stringify(english), methodId).not.toMatch(/[가-힣\uE000\uE001]/u);
    }
    expect(JSON.stringify(analysisMethodGuidance)).toBe(source);
  });

  it("resolves source strings and semantic tokens again after locale switches", () => {
    setCurrentLocale("en");
    expect(getMethodCardTags("eda.descriptive")[0].label).toBe("numeric variable");
    const english = getAnalysisMethodGuidance("quality.two_variances");
    setCurrentLocale("ko");
    expect(getMethodCardTags("eda.descriptive")[0].label).toBe("수치형 변수");
    const korean = getAnalysisMethodGuidance("quality.two_variances");
    expect(english.roleRequirements[0].label).not.toBe(korean.roleRequirements[0].label);
    expect(JSON.stringify([english, korean])).not.toMatch(/[\uE000\uE001]/u);
    expect(getAnalysisMethodGuidance("quality.two_variances", "en")).toEqual(english);
  });

  it("keeps unknown method identity literal while translating fallback guidance", () => {
    const methodId = "수치형 변수\uE000twoVariances.method\uE001";
    const guidance = getAnalysisMethodGuidance(methodId, "en");
    expect(guidance.methodId).toBe(methodId);
    expect(guidance.roleRequirements[0].label).toBe("input role");
    expect(getMethodCardTags(methodId, "en")[0].label).toBe("input role");
    for (const unknownId of ["__proto__", "constructor", "toString"]) {
      expect(getAnalysisMethodGuidance(unknownId, "en").methodId).toBe(unknownId);
      expect(getMethodCardTags(unknownId, "en")[0].label).toBe("input role");
    }
  });
});
