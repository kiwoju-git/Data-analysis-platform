import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AnalysisSelectionQuickGuide } from "./AnalysisSelectionQuickGuide";

describe("AnalysisSelectionQuickGuide", () => {
  it("renders study-design choices without executing a method", () => {
    const onSelectMethod = vi.fn();
    const html = renderToString(
      <AnalysisSelectionQuickGuide
        selectedModuleId="hypothesis"
        onSelectMethod={onSelectMethod}
      />,
    );

    expect(html).toContain("1-Sample t");
    expect(html).toContain("Mann-Whitney");
    expect(html).toContain("Paired t");
    expect(html).toContain("One-Way ANOVA");
    expect(html).toContain("Kruskal-Wallis");
    expect(html).toContain("대응표본 비모수 검정은 현재 별도 method로 지원하지 않습니다");
    expect(html).toContain(
      "표본 수 30과 정규성 검정 p-value는 절대적인 자동 선택 기준이 아닙니다",
    );
    expect(onSelectMethod).not.toHaveBeenCalled();
  });

  it("renders the categorical decision choices", () => {
    const html = renderToString(
      <AnalysisSelectionQuickGuide
        selectedModuleId="categorical"
        onSelectMethod={() => undefined}
      />,
    );

    expect(html).toContain("한 모집단 사건 비율");
    expect(html).toContain("독립 2그룹 사건 비율");
    expect(html).toContain("두 범주형 변수의 관련성");
    expect(html).toContain("희소한 2×2 분할표");
  });

  it("does not render a guide outside hypothesis and categorical modules", () => {
    const html = renderToString(
      <AnalysisSelectionQuickGuide
        selectedModuleId="quality"
        onSelectMethod={() => undefined}
      />,
    );

    expect(html).toBe("");
  });
});
