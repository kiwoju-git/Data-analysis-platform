import { describe, expect, it } from "vitest";

import {
  getAnalysisMethodGuidance,
  getMethodCardTags,
} from "./analysisMethodGuidance";

describe("analysis method card guidance", () => {
  it("uses study design guidance instead of a sample-size switch", () => {
    const tTest = getAnalysisMethodGuidance("hypothesis.one_sample_t");
    const wilcoxon = getAnalysisMethodGuidance("hypothesis.one_sample_wilcoxon");

    expect(getMethodCardTags(tTest.methodId).map((tag) => tag.label)).toEqual(
      expect.arrayContaining(["연속형 수치", "한 모집단", "평균 비교", "독립 관측"]),
    );
    expect(wilcoxon.plainLanguage).toContain("자동 대체 검정은 아닙니다");
    expect(JSON.stringify([tTest, wilcoxon])).not.toMatch(/N\s*[<>]=?\s*30/);
  });

  it("describes categorical choices without limiting chi-square to three categories", () => {
    expect(
      getMethodCardTags("categorical.one_proportion").map((tag) => tag.label),
    ).toContain("관심 사건·비사건");
    expect(
      getMethodCardTags("categorical.chi_square_association").map(
        (tag) => tag.label,
      ),
    ).toContain("2×2 이상 분할표");
  });

  it("provides concise I-MR and run-chart distinctions", () => {
    expect(
      getMethodCardTags("quality.individuals_chart").map((tag) => tag.label),
    ).toEqual(
      expect.arrayContaining(["개별 관측", "관리한계·특별원인"]),
    );
    expect(
      getMethodCardTags("quality.run_chart").map((tag) => tag.label),
    ).toContain("관리한계 없음");
  });
});
