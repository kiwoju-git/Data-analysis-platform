import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { AnalysisDomainMethodCard } from "./AnalysisDomainMethodCard";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import { MethodHelpContent } from "./MethodHelpDrawer";
import type { AnalysisMethodDescriptor } from "./api";
import { setCurrentLocale } from "./i18n/store";

const method: AnalysisMethodDescriptor = {
  method_id: "quality.two_variances",
  method_version: "0.1.0",
  module_id: "quality",
  label_ko: "두 분산 검정",
  label_en: "Two Variances",
  availability: "available",
  execution_mode: "inline",
  execution_capability: {
    lifecycle: "synchronous_request",
    cancellation_support: "none",
    progress_support: "none",
  },
  requires_dataset: true,
  order: 1,
  disabled_reason: null,
};

describe("trusted analysis catalog display boundaries", () => {
  afterEach(() => setCurrentLocale("ko"));

  it("renders semantic guidance tags and help fields in the current locale", () => {
    const renderCard = () => renderToStaticMarkup(
      <AnalysisDomainMethodCard method={method} selected={false} onSelectMethod={() => undefined} />,
    );
    const renderHelp = () => renderToStaticMarkup(<MethodHelpContent method={method} />);
    setCurrentLocale("en");
    const englishCard = renderCard();
    const englishHelp = renderHelp();
    expect(englishCard).toContain("Two independent groups");
    expect(englishHelp).toContain("Numeric response");
    expect(englishCard + englishHelp).not.toMatch(/[\uE000\uE001]/u);
    setCurrentLocale("ko");
    const koreanCard = renderCard();
    const koreanHelp = renderHelp();
    expect(koreanCard).not.toBe(englishCard);
    expect(koreanHelp).toContain("반응");
    expect(koreanCard + koreanHelp).not.toMatch(/[\uE000\uE001]/u);
    expect(koreanHelp).toContain(method.method_id);
    setCurrentLocale("en");
    expect(renderCard()).toBe(englishCard);
  });

  it("renders localized recovery guidance and preserves the literal error code", () => {
    const renderError = (code: string) => renderToStaticMarkup(
      <AnalysisWorkbench catalog={{ modules: [], methods: [method] }}
        selectedModuleId="quality" selectedMethod={method} selectedMethods={[method]}
        analysisRunError={code} version={null} profile={null}
        onSelectMethod={() => undefined} renderExecutableMethod={() => <section />} />,
    );
    setCurrentLocale("en");
    expect(renderError("analysis_run_failed")).toContain("Analysis run failed");
    expect(renderError("analysis_run_failed")).toContain("analysis_run_failed");
    const literalCode = "수치형 변수\uE000twoVariances.method\uE001";
    expect(renderError(literalCode)).toContain(literalCode);
    setCurrentLocale("ko");
    expect(renderError("analysis_run_failed")).toContain("분석 실행 실패");
  });
});
