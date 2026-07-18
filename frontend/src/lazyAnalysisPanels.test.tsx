import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  AnalysisPanelErrorBoundary,
  AnalysisPanelLoadError,
  AnalysisPanelLoading,
} from "./AnalysisPanelBoundary";
import * as lazyPanels from "./lazyAnalysisPanels";

describe("lazy analysis panels", () => {
  it("exposes accessible loading and sanitized error states", () => {
    const loadingHtml = renderToString(<AnalysisPanelLoading />);
    const errorHtml = renderToString(<AnalysisPanelLoadError />);

    expect(loadingHtml).toContain('role="status"');
    expect(loadingHtml).toContain('aria-label="분석 패널 로딩"');
    expect(errorHtml).toContain('role="alert"');
    expect(errorHtml).toContain("화면 다시 불러오기");
    expect(errorHtml).not.toContain("stack");
  });

  it("replaces panel children with the public error state after a load failure", () => {
    const boundary = new AnalysisPanelErrorBoundary({
      children: createElement("span", null, "private chunk detail"),
      resetKey: "regression.linear_model",
    });
    boundary.state = AnalysisPanelErrorBoundary.getDerivedStateFromError();

    const html = renderToString(boundary.render());
    expect(html).toContain("분석 화면을 불러오지 못했습니다.");
    expect(html).not.toContain("private chunk detail");
  });

  it("keeps regression, quality, and DOE exports behind three module loaders", async () => {
    const [regression, quality, doe] = await Promise.all([
      import("./RegressionAnalysisPanels"),
      import("./QualityAnalysisPanels"),
      import("./DoeAnalysisPanels"),
    ]);

    expect(Object.keys(regression).sort()).toEqual([
      "LinearModelPanel",
      "PearsonCorrelationPanel",
      "RegressionPredictionWorkspace",
      "XyCorrelationPanel",
    ]);
    expect(Object.keys(quality).sort()).toEqual([
      "AttributeControlChartPanel",
      "CapabilityPanel",
      "GageRrPreflightPanel",
      "GageRunChartPanel",
      "IndividualsChartPanel",
      "RunChartPanel",
      "SubgroupChartPanel",
    ]);
    expect(Object.keys(doe).sort()).toEqual([
      "BayesianOptimizationPanel",
      "FactorialDesignPanel",
      "ResponseOptimizerWorkspace",
      "ResponseSurfacePanel",
    ]);
    expect(Object.keys(lazyPanels)).toHaveLength(15);
  });
});
