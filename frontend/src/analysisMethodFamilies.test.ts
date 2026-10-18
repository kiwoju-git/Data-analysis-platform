import { describe, expect, it } from "vitest";

import type { AnalysisMethodDescriptor } from "./api";
import { groupHypothesisMethods } from "./analysisMethodFamilies";
import { isContextualAnalysisMethod } from "./analysisMethodPresentation";

const methodIds = [
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

describe("analysis method presentation", () => {
  it("groups all ten hypothesis methods into four visible families", () => {
    const families = groupHypothesisMethods(methodIds.map(descriptor), "ko");

    expect(families.map((family) => family.label)).toEqual([
      "t-검정",
      "동등성 검정",
      "분산분석",
      "비모수 검정",
    ]);
    expect(families.flatMap((family) => family.methods.map((method) => method.method_id))).toEqual(
      methodIds,
    );
  });

  it("keeps unmapped methods visible and hides only contextual regression methods", () => {
    const families = groupHypothesisMethods([
      descriptor("hypothesis.future_reference_test"),
    ], "ko");

    expect(families[0]?.label).toBe("기타 검정");
    expect(isContextualAnalysisMethod("regression.predict")).toBe(true);
    expect(isContextualAnalysisMethod("regression.linear_model")).toBe(false);
  });

  it("localizes family display fields without changing method identities or user text", () => {
    const method = {
      ...descriptor("hypothesis.one_sample_t"),
      label_ko: "사용자 \uE000language.selector\uE001",
      label_en: "User \uE000language.selector\uE001",
    };
    const english = groupHypothesisMethods([method], "en");
    const korean = groupHypothesisMethods([method], "ko");
    expect(english[0].label).toBe("t-test");
    expect(korean[0].label).toBe("t-검정");
    expect(english[0].id).toBe(korean[0].id);
    expect(english[0].methods[0]).toBe(method);
    expect(english[0].methods[0].label_ko).toBe("사용자 \uE000language.selector\uE001");
  });
});

function descriptor(methodId: string): AnalysisMethodDescriptor {
  return {
    availability: "available",
    disabled_reason: null,
    execution_mode: "inline",
    execution_capability: {
      lifecycle: "synchronous_request",
      cancellation_support: "none",
      progress_support: "none",
    },
    label_en: methodId,
    label_ko: methodId,
    method_id: methodId,
    method_version: "0.1.0",
    module_id: "hypothesis",
    order: methodIds.indexOf(methodId) + 1,
    requires_dataset: true,
  };
}
