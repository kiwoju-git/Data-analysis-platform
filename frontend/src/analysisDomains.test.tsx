import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AnalysisDomainLanding } from "./AnalysisDomainLanding";
import { ANALYSIS_DOMAINS } from "./analysisDomains";
import {
  analysisDomainForMethod,
  analysisFamilyForMethod,
  mappedAnalysisMethodIds,
  validateAnalysisDomainCatalog,
} from "./analysisDomainMapping";
import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
} from "./api";

const expectedRegistryMethodIds = [
  "eda.descriptive",
  "eda.graphical_summary",
  "eda.normality",
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
    label_ko: methodId === "eda.equal_variances" ? "등분산 검정" : methodId,
    method_id: methodId,
    method_version: "0.1.0",
    module_id: moduleId,
    order,
    requires_dataset: !methodId.startsWith("doe."),
  };
}
