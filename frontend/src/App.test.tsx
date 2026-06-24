import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import type { AnalysisMethodListResponse } from "./api";
import {
  analysisMethodGuidanceIds,
  getAnalysisMethodGuidance,
} from "./analysisMethodGuidance";
import { buildAnalysisHash, parseAnalysisHash } from "./analysisNavigation";
import { applyBayesianOptimizationPreset, type SchemaDraft } from "./schemaPresets";

describe("App", () => {
  it("renders the DataLab Studio shell", () => {
    const html = renderToString(<App />);

    expect(html).toContain("DataLab Studio");
    expect(html).toContain("로컬 분석 작업대");
    expect(html).toContain("업로드");
    expect(html).toContain("분석 모듈");
    expect(html).toContain("데이터셋 파싱 확정");
    expect(html).toContain("원본 데이터 파일");
    expect(html).toContain("스키마 확인");
    expect(html).toContain("미리보기");
  });

  it("assigns the headerless Bayesian sample schema preset", () => {
    const drafts: SchemaDraft[] = Array.from({ length: 34 }, (_, index) => ({
      column_id: `column-${index + 1}`,
      display_name: `column_${index + 1}`,
      measurement_level: "unknown",
      role: "unspecified",
      unit: "",
    }));

    const updated = applyBayesianOptimizationPreset(drafts);

    expect(updated[0]).toMatchObject({ measurement_level: "id", role: "id" });
    expect(updated[1]).toMatchObject({ measurement_level: "continuous", role: "feature" });
    expect(updated[4]).toMatchObject({ measurement_level: "count", role: "feature" });
    expect(updated[5]).toMatchObject({ measurement_level: "count", role: "feature" });
    expect(updated[22]).toMatchObject({ measurement_level: "count", role: "feature" });
    expect(updated[24]).toMatchObject({ measurement_level: "continuous", role: "feature" });
    expect(updated[25]).toMatchObject({ measurement_level: "continuous", role: "response" });
    expect(updated[33]).toMatchObject({ measurement_level: "continuous", role: "response" });
  });

  it("round-trips the six-module analysis hash selection", () => {
    const hash = buildAnalysisHash("hypothesis", "hypothesis.two_sample_t");

    expect(hash).toBe("analysis/hypothesis/hypothesis.two_sample_t");
    expect(parseAnalysisHash(`#${hash}`)).toEqual({
      moduleId: "hypothesis",
      methodId: "hypothesis.two_sample_t",
    });
  });

  it("rejects unknown analysis module hashes", () => {
    expect(parseAnalysisHash("#analysis/unknown/eda.descriptive")).toBeNull();
    expect(parseAnalysisHash("#datasets")).toBeNull();
  });

  it("defines guidance for all 29 documented six-module methods", () => {
    expect(analysisMethodGuidanceIds).toHaveLength(29);
    expect(getAnalysisMethodGuidance("eda.descriptive").roleRequirements[0]).toMatchObject({
      label: "분석 변수",
      required: true,
    });
    expect(
      getAnalysisMethodGuidance("regression.response_optimizer").preflightChecks,
    ).toContain("설계영역");
    expect(getAnalysisMethodGuidance("doe.factorial_design").optionChecklist).toContain(
      "랜덤 seed",
    );
  });

  it("keeps planned Workbench methods non-executable", () => {
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.two_sample_t",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "두 표본 t 검정",
          label_en: "2-Sample t",
          availability: "planned",
          execution_mode: "inline",
          requires_dataset: true,
          order: 1,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisWorkbench
        catalog={catalog}
        profile={null}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={null}
        onSelectMethod={() => undefined}
        renderExecutableMethod={() => {
          throw new Error("planned method should not render an executable panel");
        }}
      />,
    );

    expect(html).toContain("두 표본 t 검정");
    expect(html).toContain("Welch 기본");
    expect(html).toContain("계산 코드, 기준 데이터, 수치 검증 테스트");
  });
});
