import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import type { AnalysisMethodListResponse, DatasetColumnResponse } from "./api";
import {
  analysisMethodGuidanceIds,
  getAnalysisMethodGuidance,
} from "./analysisMethodGuidance";
import {
  filterOperatorOptions,
  serializeAnalysisFilterDrafts,
  validateAnalysisFilterDrafts,
  type AnalysisFilterDraft,
} from "./analysisFilters";
import {
  buildAnalysisHash,
  buildAnalysisPath,
  parseAnalysisHash,
  parseAnalysisLocation,
  parseAnalysisPath,
} from "./analysisNavigation";
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
    expect(html).toContain("복사한 표 붙여넣기");
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

  it("round-trips route-level analysis paths and keeps legacy hash fallback", () => {
    const path = buildAnalysisPath("regression", "regression.fit_model");

    expect(path).toBe("/analysis/regression/regression.fit_model");
    expect(parseAnalysisPath(path)).toEqual({
      moduleId: "regression",
      methodId: "regression.fit_model",
    });
    expect(parseAnalysisLocation(path, "")).toEqual({
      moduleId: "regression",
      methodId: "regression.fit_model",
    });
    expect(parseAnalysisLocation("/", "#analysis/hypothesis/hypothesis.two_sample_t")).toEqual({
      moduleId: "hypothesis",
      methodId: "hypothesis.two_sample_t",
    });
  });

  it("rejects unknown analysis module routes", () => {
    expect(parseAnalysisHash("#analysis/unknown/eda.descriptive")).toBeNull();
    expect(parseAnalysisPath("/analysis/unknown/eda.descriptive")).toBeNull();
    expect(parseAnalysisPath("/analysis/exploration/eda.descriptive/extra")).toBeNull();
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

  it("builds supported descriptive filter payloads without unsupported operators", () => {
    const columns = filterTestColumns();

    expect(filterOperatorOptions(columns[0]).map((operator) => operator.value)).toEqual([
      "is_not_missing",
      "is_missing",
      "eq",
      "ne",
      "gt",
      "gte",
      "lt",
      "lte",
    ]);
    expect(filterOperatorOptions(columns[1]).map((operator) => operator.value)).toEqual([
      "is_not_missing",
      "is_missing",
      "eq",
      "ne",
    ]);

    const drafts: AnalysisFilterDraft[] = [
      {
        id: "filter-1",
        column_id: "column-a",
        operator: "gt",
        value: "1.5",
      },
      {
        id: "filter-2",
        column_id: "column-b",
        operator: "is_not_missing",
        value: "",
      },
    ];

    expect(validateAnalysisFilterDrafts(drafts, columns)).toBeNull();
    expect(serializeAnalysisFilterDrafts(drafts, columns)).toEqual([
      {
        column_id: "column-a",
        operator: "gt",
        value: "1.5",
      },
      {
        column_id: "column-b",
        operator: "is_not_missing",
      },
    ]);
  });

  it("rejects incomplete descriptive filter drafts before API submission", () => {
    const columns = filterTestColumns();
    const drafts: AnalysisFilterDraft[] = [
      {
        id: "filter-1",
        column_id: "column-a",
        operator: "lte",
        value: "",
      },
    ];

    expect(validateAnalysisFilterDrafts(drafts, columns)).toBe("filter_value_required");
    expect(() => serializeAnalysisFilterDrafts(drafts, columns)).toThrow("filter_value_required");
  });
});

function filterTestColumns(): DatasetColumnResponse[] {
  return [
    {
      column_id: "column-a",
      version_id: "version-1",
      column_index: 0,
      original_name: "a",
      display_name: "A",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "feature",
      unit: null,
    },
    {
      column_id: "column-b",
      version_id: "version-1",
      column_index: 1,
      original_name: "b",
      display_name: "B",
      data_type: "text",
      measurement_level: "nominal",
      role: "group",
      unit: null,
    },
  ];
}
