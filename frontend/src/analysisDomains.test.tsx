import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AnalysisDomainLanding } from "./AnalysisDomainLanding";
import { ANALYSIS_DOMAINS } from "./analysisDomains";
import {
  analysisDomainForMethod,
  analysisFamilyForMethod,
  analysisMethodPlacement,
  mappedAnalysisMethodIds,
  landingCatalogMethods,
  validateAnalysisDomainCatalog,
} from "./analysisDomainMapping";
import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
} from "./api";
import { setCurrentLocale } from "./i18n/store";

const expectedRegistryMethodIds = [
  "eda.descriptive",
  "eda.graphical_summary",
  "eda.normality",
  "eda.principal_components",
  "eda.equal_variances",
  "hypothesis.one_sample_t",
  "hypothesis.paired_t",
  "hypothesis.two_sample_t",
  "hypothesis.one_way_anova",
  "hypothesis.equivalence_tost",
  "hypothesis.two_sample_equivalence_tost",
  "hypothesis.paired_equivalence_tost",
  "hypothesis.one_sample_wilcoxon",
  "hypothesis.mann_whitney",
  "hypothesis.kruskal_wallis",
  "categorical.one_proportion",
  "categorical.two_proportion",
  "categorical.chi_square_association",
  "regression.pearson",
  "regression.xy_correlation",
  "regression.linear_model",
  "regression.partial_least_squares",
  "regression.gaussian_process",
  "regression.predict",
  "quality.attribute_control_chart",
  "quality.subgroup_chart",
  "quality.individuals_chart",
  "quality.run_chart",
  "quality.capability",
  "quality.gage_rr",
  "quality.gage_run_chart",
  "doe.factorial_design",
  "doe.general_factorial_design",
  "doe.latin_hypercube",
  "doe.response_surface",
  "doe.response_optimizer",
  "doe.bayesian_optimization",
] as const;

describe("analysis domain navigation", () => {
  it.each(["ko", "en"] as const)("groups the ten mean methods without duplicate family captions (%s)", (locale) => {
    setCurrentLocale(locale);
    try {
      const html = renderToString(<AnalysisDomainLanding catalog={testCatalog()} domain={ANALYSIS_DOMAINS[1]}
        selectedMethodId="hypothesis.one_sample_t" onOpenDomain={() => undefined} onSelectMethod={() => undefined} />);
      const groups = [...html.matchAll(/<section class="analysis-method-group"[^>]*data-family-id="([^"]+)"[\s\S]*?<\/section>/g)];
      expect(groups.map((group) => group[1])).toEqual(["t-tests", "analysis-of-variance", "equivalence-tests", "nonparametric-tests"]);
      expect(groups.map((group) => (group[0].match(/<button/g) ?? []).length)).toEqual([3, 1, 3, 3]);
      for (const group of groups) {
        expect(group[0]).toContain(`aria-labelledby="analysis-method-group-${group[1]}"`);
        expect(group[0]).toContain(`<h3 id="analysis-method-group-${group[1]}">`);
      }
      expect(html).not.toContain('class="analysis-method-family-label"');
      expect(html).toContain('aria-pressed="true"');
      expect(html).toContain('is-planned');
      expect(html).toContain(locale === "ko" ? "비모수 비교" : "Nonparametric Tests");
    } finally { setCurrentLocale("ko"); }
  });
  it("defines the eight presentation domains in the required order", () => {
    expect(ANALYSIS_DOMAINS.map((domain) => domain.id)).toEqual([
      "basic-exploration",
      "mean-equivalence",
      "proportions-categorical",
      "correlation-regression-prediction",
      "doe-optimization",
      "ai-ml-experimental-design",
      "quality-process-monitoring",
      "measurement-variability",
    ]);
  });

  it("maps every current registry method exactly once", () => {
    expect(mappedAnalysisMethodIds().slice().sort()).toEqual(
      expectedRegistryMethodIds.slice().sort(),
    );
    expect(validateAnalysisDomainCatalog(testCatalog())).toEqual([]);
  });

  it("keeps contextual and planned workflows out of executable method lists", () => {
    const regression = analysisDomainForMethod("regression.predict");
    expect(regression?.id).toBe("correlation-regression-prediction");
    expect(
      regression?.families.flatMap((family) => family.methodIds),
    ).not.toContain("regression.predict");
    expect(mappedAnalysisMethodIds()).not.toContain("quality.two_variances");
    expect(analysisFamilyForMethod("eda.equal_variances")?.id).toBe(
      "variance-comparison",
    );
    expect(analysisFamilyForMethod("eda.descriptive")).toBeNull();
    expect(analysisMethodPlacement("doe.general_factorial_design")?.contextual).toBe(true);
    const regressionMethods = ANALYSIS_DOMAINS.find(
      (domain) => domain.id === "correlation-regression-prediction",
    )?.directMethodIds;
    expect(regressionMethods).toContain("regression.partial_least_squares");
    expect(regressionMethods).toContain("regression.gaussian_process");
    expect(ANALYSIS_DOMAINS.flatMap((domain) => domain.directPlannedWorkflows ?? [])).not.toContainEqual(
      expect.objectContaining({ id: "regression.partial_least_squares" }),
    );
  });

  it("uses metadata-driven flat and grouped presentation modes", () => {
    expect(ANALYSIS_DOMAINS.filter((domain) => domain.landingMode === "flat_methods").map((domain) => domain.id)).toEqual([
      "basic-exploration",
      "correlation-regression-prediction",
      "doe-optimization",
      "ai-ml-experimental-design",
    ]);
    const mean = ANALYSIS_DOMAINS[1];
    expect(mean.landingMode).toBe("family_cards");
    expect(mean.families.find((family) => family.id === "analysis-of-variance")?.layout).toBe("direct_single");
    expect(mean.families.find((family) => family.id === "equivalence-tests")?.methodIds).toEqual([
      "hypothesis.equivalence_tost",
      "hypothesis.two_sample_equivalence_tost",
      "hypothesis.paired_equivalence_tost",
    ]);
  });

  it("reports a new unmapped registry method and a stale mapping", () => {
    const catalog = testCatalog();
    const extra = descriptor("future.visible_method", catalog.methods.length + 1);
    expect(
      validateAnalysisDomainCatalog({ ...catalog, methods: [...catalog.methods, extra] }),
    ).toContain("unmapped:future.visible_method");
    expect(
      validateAnalysisDomainCatalog({ ...catalog, methods: catalog.methods.slice(1) }),
    ).toContain(`unknown:${catalog.methods[0].method_id}`);
  });

  it("normalizes every landing without changing placement, count or canonical order", () => {
    const catalog = testCatalog();
    for (const domain of ANALYSIS_DOMAINS) {
      const expected = [...(domain.directMethodIds ?? []), ...domain.families.flatMap((family) => family.methodIds)];
      const entries = landingCatalogMethods({ ...catalog, methods: [...catalog.methods].reverse() }, domain);
      expect(entries.map(({ method }) => method.method_id)).toEqual(expected);
      expect(new Set(expected).size).toBe(expected.length);
      const html = renderToString(<AnalysisDomainLanding catalog={catalog} domain={domain}
        selectedMethodId={null} onOpenDomain={() => undefined} onSelectMethod={() => undefined} />);
      expect(html.match(/<button[^>]*class="analysis-domain-method-card/g) ?? []).toHaveLength(expected.length);
      expect(html).not.toContain('class="analysis-domain-family-card');
      expect(html).not.toContain('<details class="analysis-domain-guide" open');
    }
  });

  it("renders domain and family landings without turning planned work into a button", () => {
    const catalog = testCatalog();
    const rootHtml = renderToString(
      <AnalysisDomainLanding
        catalog={catalog}
        domain={null}
        selectedMethodId={null}
        onOpenDomain={() => undefined}
        onSelectMethod={() => undefined}
      />,
    );
    const measurement = ANALYSIS_DOMAINS[7];
    const basic = ANALYSIS_DOMAINS[0];
    const basicHtml = renderToString(
      <AnalysisDomainLanding
        catalog={catalog}
        domain={basic}
        selectedMethodId={null}
        onOpenDomain={() => undefined}
        onSelectMethod={() => undefined}
      />,
    );
    const familyHtml = renderToString(
      <AnalysisDomainLanding
        catalog={catalog}
        domain={measurement}
        selectedMethodId={null}
        onOpenDomain={() => undefined}
        onSelectMethod={() => undefined}
      />,
    );

    expect(rootHtml.match(/class="analysis-domain-card"/gu)).toHaveLength(8);
    expect(basicHtml.match(/analysis-domain-method-card/gu)).toHaveLength(4);
    expect(basicHtml).toContain("PCA 기반 다변량 검토");
    expect(basicHtml).not.toContain("analysis-domain-family-card");
    expect(rootHtml).not.toContain("analysis-domain-order");
    expect(rootHtml).not.toContain("analysis-domain-counts");
    expect(basicHtml).not.toContain("analysis-domain-guidance");
    expect(basicHtml).toContain('<details class="analysis-domain-guide">');
    expect(basicHtml.indexOf("analysis-domain-method-grid")).toBeLessThan(basicHtml.indexOf("analysis-domain-guide\""));
    expect(familyHtml).toContain('<details class="analysis-domain-guide">');
    expect(familyHtml).toContain("Two Variances");
    expect(familyHtml).not.toContain(">Two Variances</button>");
    expect(familyHtml).toContain("등분산 검정");
  });
});

function testCatalog(): AnalysisMethodListResponse {
  return {
    modules: [],
    methods: expectedRegistryMethodIds.map((methodId, index) => descriptor(methodId, index)),
  };
}

function descriptor(methodId: string, order: number): AnalysisMethodDescriptor {
  const prefix = methodId.split(".")[0];
  const moduleId = (
    prefix === "eda"
      ? "exploration"
      : prefix === "hypothesis"
        ? "hypothesis"
        : prefix
  ) as AnalysisModuleId;
  return {
    availability: "available",
    disabled_reason: null,
    execution_mode: methodId.startsWith("doe.") ? "dedicated" : "inline",
    label_en: methodId,
    label_ko:
      methodId === "eda.equal_variances"
        ? "등분산 검정"
        : methodId === "eda.principal_components"
          ? "PCA 기반 다변량 검토"
          : methodId,
    method_id: methodId,
    method_version: "0.1.0",
    module_id: moduleId,
    order,
    requires_dataset: !methodId.startsWith("doe."),
  };
}
