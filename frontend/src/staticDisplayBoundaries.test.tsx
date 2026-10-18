import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { MethodPurposeHelper } from "./MethodPurposeHelper";
import { StatisticalRoleGuide } from "./StatisticalRoleGuide";
import type { AnalysisMethodDescriptor, AnalysisMethodListResponse } from "./api";
import { availabilityLabel } from "./analysisWorkbenchUtils";
import { graphBuilderDefinition, graphBuilderDefinitions, localizedGraphBuilderDefinitions } from "./graphBuilderRegistry";
import { getCurrentLocale, setCurrentLocale } from "./i18n/store";
import { localizedReportWorkflowCapabilities, reportWorkflowCapabilities } from "./reportCenterCapabilities";

describe("trusted static display boundaries", () => {
  const originalLocale = getCurrentLocale();
  afterEach(() => setCurrentLocale(originalLocale));

  it("localizes report descriptions without mutating stored IDs, paths, or catalog text", () => {
    const before = JSON.stringify(reportWorkflowCapabilities);
    const english = localizedReportWorkflowCapabilities("en");
    const korean = localizedReportWorkflowCapabilities("ko");
    expect(english[0].label).toBe("Run general analysis");
    expect(korean[0].label).toBe("일반 분석 실행");
    expect(english[0].html).toBe("support");
    expect(english.map(({ methodId, workflowPath }) => ({ methodId, workflowPath })))
      .toEqual(korean.map(({ methodId, workflowPath }) => ({ methodId, workflowPath })));
    expect(JSON.stringify(reportWorkflowCapabilities)).toBe(before);
  });

  it("localizes graph display fields without changing execution configuration", () => {
    const before = JSON.stringify(graphBuilderDefinitions);
    const english = localizedGraphBuilderDefinitions("en");
    expect(english[0].description).toBe("Compare the distributions of multiple numeric variables or groups of one numeric variable.");
    expect(graphBuilderDefinition("box_plot", "ko").description).toBe("여러 수치 변수 또는 한 수치 변수의 그룹별 분포를 비교합니다.");
    const execution = ({ graphType, maximumValues, supportsGroup, supportsOrder }: typeof english[number]) => ({ graphType, maximumValues, supportsGroup, supportsOrder });
    expect(english.map(execution)).toEqual(graphBuilderDefinitions.map(execution));
    expect(JSON.stringify(graphBuilderDefinitions)).toBe(before);
  });

  it("localizes availability independently from the method descriptor", () => {
    const method = { availability: "available", execution_mode: "inline" } as AnalysisMethodDescriptor;
    expect(availabilityLabel(method, "en")).toBe("available");
    expect(availabilityLabel(method, "ko")).toBe("사용 가능");
    expect(method).toEqual({ availability: "available", execution_mode: "inline" });
  });

  it("renders purpose and role catalogs in the current locale on every render", () => {
    const catalog = { methods: [] } as unknown as AnalysisMethodListResponse;
    const render = () => renderToStaticMarkup(<><MethodPurposeHelper catalog={catalog} onSelectMethod={() => undefined} /><StatisticalRoleGuide selectedMethod={null} /></>);
    setCurrentLocale("en");
    const english = render();
    expect(english).toContain("I want to see the distribution and outliers of one column.");
    expect(english).toContain("Response / response value / Y");
    expect(english).toContain("eda.graphical_summary");
    expect(english).not.toContain("\uE000");
    setCurrentLocale("ko");
    const korean = render();
    expect(korean).toContain("한 컬럼의 분포와 이상치를 보고 싶다");
    expect(korean).toContain("Response / 반응값 / Y");
    setCurrentLocale("en");
    expect(render()).toBe(english);
  });
});
