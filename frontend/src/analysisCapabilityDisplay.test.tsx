import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";

import { AnalysisDomainMethodCard } from "./AnalysisDomainMethodCard";
import { HelpCenterPage } from "./HelpCenterPage";
import { MethodHelpContent } from "./MethodHelpDrawer";
import { mappedAnalysisMethodIds, analysisMethodPlacement } from "./analysisDomainMapping";
import { analysisMethodGuidanceIds, getAnalysisMethodGuidance, getMethodCardTags } from "./analysisMethodGuidance";
import { isContextualAnalysisMethod } from "./analysisMethodPresentation";
import { availabilityLabel } from "./analysisWorkbenchUtils";
import { groupHypothesisMethods } from "./analysisMethodFamilies";
import { ANALYSIS_CAPABILITY_LIMITS } from "./analysisCapabilities";
import capabilities from "./generated/analysisCapabilities.json";
import { DOE_FACTOR_CAPABILITIES, DOE_RUN_CAPABILITIES } from "./doe/factorCapabilities";
import type { AnalysisMethodDescriptor } from "./api";
import { setCurrentLocale } from "./i18n/store";

const prediction: AnalysisMethodDescriptor = {
  method_id: "regression.predict", method_version: "0.1.0", module_id: "regression",
  label_ko: "저장 모델 예측", label_en: "Saved model prediction",
  availability: "available", execution_mode: "dedicated", requires_dataset: false,
  source_prerequisite: "regression_model", order: 1, disabled_reason: null,
  execution_capability: { lifecycle: "synchronous_request", cancellation_support: "none", progress_support: "none" },
};

describe("capability-aligned method help", () => {
  afterEach(() => setCurrentLocale("ko"));

  it("has explicit guidance for every canonical catalog placement", () => {
    expect(mappedAnalysisMethodIds().filter((id) => !analysisMethodGuidanceIds.includes(id))).toEqual([]);
    expect(capabilities.methods.map((method) => method.method_id).sort()).toEqual([...analysisMethodGuidanceIds].sort());
  });

  it("binds displayed factor limits and option claims to generated backend facts", () => {
    expect(ANALYSIS_CAPABILITY_LIMITS.LATIN_HYPERCUBE_FACTOR_LIMIT).toBe(DOE_FACTOR_CAPABILITIES.latinHypercube);
    expect(ANALYSIS_CAPABILITY_LIMITS.BAYESIAN_STUDY_FACTOR_LIMIT).toBe(DOE_FACTOR_CAPABILITIES.bayesianStudy);
    expect(ANALYSIS_CAPABILITY_LIMITS.FACTORIAL_RUN_LIMIT).toBe(DOE_RUN_CAPABILITIES.factorial);
    expect(ANALYSIS_CAPABILITY_LIMITS.GENERAL_FACTORIAL_RUN_LIMIT).toBe(DOE_RUN_CAPABILITIES.generalFactorial);
    expect(capabilities.option_policies.anova_posthoc_default).toBe("when_requested");
    expect(capabilities.option_policies.normality_grouping).toBe("not_supported");
  });

  it("preserves the hypothesis display order while validating canonical family membership", () => {
    const methods = capabilities.methods.filter((method) => method.module_id === "hypothesis")
      .map((method) => ({ ...prediction, method_id: method.method_id }));
    const groups = groupHypothesisMethods(methods, "en");
    expect(groups.map((group) => group.id)).toEqual(["t-tests", "equivalence-tests", "analysis-of-variance", "nonparametric-tests"]);
    for (const group of groups) {
      for (const method of group.methods) expect(analysisMethodPlacement(method.method_id)?.family?.id).toBe(group.id);
    }
  });

  it("uses canonical contextual placement and never promotes a ghost method", () => {
    for (const id of mappedAnalysisMethodIds()) {
      expect(isContextualAnalysisMethod(id), id).toBe(analysisMethodPlacement(id)?.contextual);
    }
    expect(isContextualAnalysisMethod("regression.predict_manual")).toBe(false);
    expect(isContextualAnalysisMethod("regression.predict_pasted")).toBe(true);
  });

  it("describes real normality, graphical-summary, ANOVA and frozen-limit options", () => {
    const normality = getAnalysisMethodGuidance("eda.normality", "en");
    const graphical = getAnalysisMethodGuidance("eda.graphical_summary", "en");
    expect(normality.roleRequirements).toHaveLength(1);
    expect(graphical.roleRequirements).toHaveLength(1);
    expect(graphical.roleRequirements[0].detail).not.toContain("categorical");
    expect(getAnalysisMethodGuidance("hypothesis.one_way_anova", "en").plainLanguage).toContain("when requested");
    expect(getAnalysisMethodGuidance("quality.attribute_control_chart", "en").optionChecklist.join(" ")).toContain("eligible frozen limit set");
  });

  it("describes limits and distinguishes aliased designs from selectable full models", () => {
    expect(getAnalysisMethodGuidance("doe.latin_hypercube", "en").roleRequirements[0].detail).toContain("1-10");
    expect(getAnalysisMethodGuidance("doe.bayesian_optimization", "en").roleRequirements[0].detail).toContain("1-10");
    expect(getAnalysisMethodGuidance("doe.factorial_design", "en").plainLanguage).toContain("fractional");
    expect(getAnalysisMethodGuidance("doe.factorial_design", "en").plainLanguage).toContain("Plackett-Burman");
    expect(getAnalysisMethodGuidance("doe.general_factorial_design", "en").plainLanguage).toContain("multi-level");
    expect(getAnalysisMethodGuidance("eda.principal_components", "en").plainLanguage).toContain("D");
  });

  it.each(["ko", "en"] as const)("requires a saved optimizer model without claiming proven performance (%s)", (locale) => {
    const expected = locale === "en" ? "Saved model" : "저장된 모델";
    expect(getAnalysisMethodGuidance("doe.response_optimizer", locale).roleRequirements[0].label).toBe(expected);
    expect(getMethodCardTags("doe.response_optimizer", locale)[0].label).toBe(expected);
  });

  it.each(["ko", "en"] as const)("keeps source-needed methods navigable and explains prerequisites (%s)", (locale) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<AnalysisDomainMethodCard method={prediction} selected={false} onSelectMethod={() => undefined} />);
    expect(html).not.toContain("disabled=");
    const requiredText = locale === "en" ? "Compatible saved regression model required" : "호환되는 저장 회귀 모델 필요";
    expect(availabilityLabel(prediction, locale)).not.toContain(requiredText);
    expect(html).toContain(`class="analysis-method-prerequisite"`);
    expect(html).toContain(requiredText);
    const badge = html.match(/<small>(.*?)<\/small>/u)?.[1];
    expect(badge).toBe(availabilityLabel(prediction, locale));
    expect(badge).not.toContain(requiredText);
    expect(html).toContain('aria-describedby="analysis-domain-method-regression-predict analysis-domain-method-regression-predict-source"');
    expect(renderToStaticMarkup(<MethodHelpContent method={prediction} />)).toContain(requiredText);
    expect(availabilityLabel({ ...prediction, availability: "disabled" }, locale)).not.toContain(requiredText);
    const rawLabel = "사용자 \uE000capabilityHelp.roadmap\uE001 <source>";
    const literal = renderToStaticMarkup(<AnalysisDomainMethodCard method={{ ...prediction, method_id: "user-method", label_ko: rawLabel, label_en: rawLabel }} selected={false} onSelectMethod={() => undefined} />);
    expect(literal).toContain("사용자 \uE000capabilityHelp.roadmap\uE001 &lt;source&gt;");
  });

  it.each(["ko", "en"] as const)("labels roadmap-only entries separately from executable help (%s)", (locale) => {
    setCurrentLocale(locale);
    const html = renderToStaticMarkup(<HelpCenterPage catalog={{ modules: [], methods: [prediction] }} onOpenAnalysis={() => undefined} />);
    expect(html).toContain('data-help-roadmap="true"');
    expect(html).toContain(locale === "en" ? "Roadmap only" : "로드맵 전용");
    expect(html).toContain("hypothesis.comparability_assessment");
    expect(html).toContain("quality.multivariate_monitoring");
  });
});
