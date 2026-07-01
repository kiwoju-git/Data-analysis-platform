import type { ComponentProps } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";
import { AnalysisPage } from "./AnalysisPage";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import { DatasetPreparationPage } from "./DatasetPreparationPage";
import type {
  AnalysisMethodListResponse,
  CapabilityResult,
  ChiSquareAssociationResult,
  DatasetColumnResponse,
  DatasetUploadResponse,
  DatasetVersionResponse,
  FactorialDesignResponse,
  GageRrPreflightResponse,
  GageRrResult,
  GageRunChartResult,
  GraphicalSummaryResult,
  IndividualsChartResult,
  LinearModelResult,
  NormalityResult,
  PearsonCorrelationResult,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RunChartResult,
  SubgroupChartResult,
  XyCorrelationResult,
} from "./api";
import { AppChrome } from "./AppChrome";
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
import { resolveAnalysisSelection } from "./analysisSelection";
import { parseAppRoute } from "./appRoute";
import {
  canConfirmParsingOptions,
  parsingSuggestionToConfirmation,
} from "./useDatasetWorkflow";
import { WorkspaceRouter } from "./WorkspaceRouter";
import { applyBayesianOptimizationPreset, type SchemaDraft } from "./schemaPresets";

describe("App", () => {
  it("renders the DataLab Studio shell", () => {
    const html = renderToString(<App />);

    expect(html).toContain("DataLab Studio");
    expect(html).toContain("로컬 분석 작업대");
    expect(html).toContain("업로드");
    expect(html).toContain("데이터셋");
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
    expect(parseAppRoute("/", "")).toEqual({
      page: "dataset",
    });
    expect(parseAppRoute(path, "")).toEqual({
      page: "analysis",
      selection: {
        moduleId: "regression",
        methodId: "regression.fit_model",
      },
    });
  });

  it("rejects unknown analysis module routes", () => {
    expect(parseAnalysisHash("#analysis/unknown/eda.descriptive")).toBeNull();
    expect(parseAnalysisPath("/analysis/unknown/eda.descriptive")).toBeNull();
    expect(parseAnalysisPath("/analysis/exploration/eda.descriptive/extra")).toBeNull();
    expect(parseAnalysisHash("#datasets")).toBeNull();
  });

  it("resolves route analysis selection against the backend catalog", () => {
    const catalog = analysisTestCatalog();

    expect(
      resolveAnalysisSelection(catalog, {
        moduleId: "hypothesis",
        methodId: "hypothesis.two_sample_t",
      }),
    ).toMatchObject({
      moduleId: "hypothesis",
      methodId: "hypothesis.two_sample_t",
    });
    expect(
      resolveAnalysisSelection(catalog, {
        moduleId: "quality",
        methodId: "unknown",
      }),
    ).toMatchObject({
      moduleId: "quality",
      methodId: null,
    });
    expect(
      resolveAnalysisSelection(catalog, {
        moduleId: "doe",
        methodId: "missing",
      }),
    ).toMatchObject({
      moduleId: "exploration",
      methodId: "eda.descriptive",
    });
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
    expect(getAnalysisMethodGuidance("eda.normality").preflightChecks).toContain("표본 수 범위");
    expect(getAnalysisMethodGuidance("doe.factorial_design").optionChecklist).toContain(
      "랜덤 seed",
    );
    expect(getAnalysisMethodGuidance("doe.factorial_design").plainLanguage).toContain(
      "효과 추정",
    );
  });

  it("renders the DOE factorial design creation panel and run order preview", () => {
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "doe",
          label_ko: "실험 계획법",
          label_en: "Design Of Experiments",
          order: 6,
        },
      ],
      methods: [
        {
          method_id: "doe.factorial_design",
          method_version: "0.1.0",
          module_id: "doe",
          label_ko: "실험 계획 생성",
          label_en: "Design of Experiments",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: false,
          order: 1,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        factorialDesign={factorialDesignTestResponse()}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="doe"
      />,
    );

    expect(html).toContain("실험 계획법");
    expect(html).toContain("2-level full factorial 설계 생성");
    expect(html).toContain("DOE 설계 생성");
    expect(html).toContain("screening design");
    expect(html).toContain("two_level_full_factorial");
    expect(html).toContain("효과/ANOVA 미포함");
    expect(html).toContain("Temperature");
    expect(html).toContain("Pressure");
    expect(html).toContain("design-hash-");
  });

  it("keeps planned Workbench methods non-executable", () => {
    const catalog = analysisTestCatalog();
    const selectedMethods = catalog.methods.filter((method) => method.module_id === "hypothesis");

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        profile={null}
        selectedMethod={selectedMethods[0]}
        selectedMethods={selectedMethods}
        selectedModuleId="hypothesis"
        version={null}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>공통 분석 필터</div>}
        renderExecutableMethod={() => {
          throw new Error("planned method should not render an executable panel");
        }}
      />,
    );

    expect(html).toContain("두 표본 t 검정");
    expect(html).toContain("공통 분석 필터");
    expect(html).toContain("Welch 기본");
    expect(html).toContain("계산 코드, 기준 데이터, 수치 검증 테스트");
  });

  it("shows analysis run errors under the selected execution panel with a readable action", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError="filter_value_required"
        catalog={catalog}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("실행 패널");
    expect(html).toContain("필터 값 필요");
    expect(html).toContain("해결 방법:");
    expect(html).toContain("오류 코드:");
    expect(html).toContain("filter_value_required");
  });

  it("renders the Pearson correlation execution panel for the first Gate C1 method", () => {
    const baseColumns = filterTestColumns();
    const yColumn: DatasetColumnResponse = {
      ...baseColumns[0],
      column_id: "column-c",
      column_index: 2,
      original_name: "c",
      display_name: "C",
      role: "response",
    };
    const columns = [...baseColumns, yColumn];
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      column_count: columns.length,
      columns,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "regression",
          label_ko: "상관관계 및 회귀분석",
          label_en: "Correlation And Regression",
          order: 4,
        },
      ],
      methods: [
        {
          method_id: "regression.pearson",
          method_version: "0.1.0",
          module_id: "regression",
          label_ko: "Pearson 상관",
          label_en: "Pearson Correlation",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 1,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        pearsonResult={pearsonCorrelationTestResult()}
        pearsonXColumnId="column-a"
        pearsonXColumns={[baseColumns[0], yColumn]}
        pearsonYColumnId="column-c"
        pearsonYColumns={[baseColumns[0], yColumn]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="regression"
        version={version}
      />,
    );

    expect(html).toContain("상관관계 및 회귀분석");
    expect(html).toContain("Pearson 상관 실행");
    expect(html).toContain("X 변수");
    expect(html).toContain("Y 변수");
    expect(html).toContain("상관을 인과관계로 해석");
    expect(html).toContain("산점도");
    expect(html).toContain("A C scatter plot");
    expect(html).toContain("0.926872");
  });

  it("renders the X-Y correlation execution panel for the second Gate C1 method", () => {
    const baseColumns = filterTestColumns();
    const xColumn: DatasetColumnResponse = {
      ...baseColumns[0],
      column_id: "column-x2",
      column_index: 2,
      original_name: "x2",
      display_name: "X2",
      role: "feature",
    };
    const yColumn: DatasetColumnResponse = {
      ...baseColumns[0],
      column_id: "column-y",
      column_index: 3,
      original_name: "y",
      display_name: "Y",
      role: "response",
    };
    const columns = [baseColumns[0], xColumn, yColumn];
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      column_count: columns.length,
      columns,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "regression",
          label_ko: "상관관계 및 회귀분석",
          label_en: "Correlation And Regression",
          order: 4,
        },
      ],
      methods: [
        {
          method_id: "regression.xy_correlation",
          method_version: "0.1.0",
          module_id: "regression",
          label_ko: "X-Y 상관행렬",
          label_en: "X-Y Correlation",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 2,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="regression"
        version={version}
        xyCorrelationResult={xyCorrelationTestResult()}
        xyCorrelationXColumnIds={["column-a", "column-x2"]}
        xyCorrelationXColumns={[baseColumns[0], xColumn, yColumn]}
        xyCorrelationYColumnIds={["column-y"]}
        xyCorrelationYColumns={[baseColumns[0], xColumn, yColumn]}
      />,
    );

    expect(html).toContain("X-Y 상관행렬 실행");
    expect(html).toContain("X 변수 집합");
    expect(html).toContain("Y 변수 집합");
    expect(html).toContain("교차 상관행렬");
    expect(html).toContain("상관 Heatmap");
    expect(html).toContain("0.8");
  });

  it("renders the linear model execution panel for the third Gate C1 method", () => {
    const baseColumns = filterTestColumns();
    const xColumn: DatasetColumnResponse = {
      ...baseColumns[0],
      column_id: "column-x2",
      column_index: 2,
      original_name: "x2",
      display_name: "X2",
      role: "feature",
    };
    const yColumn: DatasetColumnResponse = {
      ...baseColumns[0],
      column_id: "column-y",
      column_index: 3,
      original_name: "y",
      display_name: "Y",
      role: "response",
    };
    const columns = [baseColumns[0], xColumn, yColumn];
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      column_count: columns.length,
      columns,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "regression",
          label_ko: "상관관계 및 회귀분석",
          label_en: "Correlation And Regression",
          order: 4,
        },
      ],
      methods: [
        {
          method_id: "regression.linear_model",
          method_version: "0.1.0",
          module_id: "regression",
          label_ko: "회귀모형 적합",
          label_en: "Fit Regression Model",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 3,
          disabled_reason: null,
        },
      ],
    };
    const linearModelResult: LinearModelResult = {
      schema_version: 4,
      summary_type: "linear_model",
      method: "ordinary_least_squares_numeric_predictors",
      missing_policy: "complete_case",
      alpha: 0.05,
      confidence_level: 0.95,
      package_versions: {
        numpy: "2.2.6",
        scipy: "1.15.3",
      },
      warnings: [],
      response: {
        column_id: "column-y",
        column_index: 3,
        display_name: "Y",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "response",
        unit: null,
      },
      predictors: [
        {
          column_id: "column-a",
          column_index: 0,
          display_name: "A",
          data_type: "decimal",
          measurement_level: "continuous",
          role: "feature",
          unit: null,
        },
      ],
      model_specification: {
        intercept: true,
        terms: [
          {
            term: "A",
            kind: "numeric_main_effect",
            column_id: "column-a",
            source_column_ids: ["column-a"],
          },
        ],
      },
      sample: {
        n_total: 8,
        n_used: 8,
        n_excluded_missing: 0,
        n_excluded_non_numeric: 0,
        df_model: 1,
        df_residual: 6,
      },
      fit: {
        r_squared: 0.9,
        adjusted_r_squared: 0.88,
        residual_standard_error: 0.4,
        sigma_squared: 0.16,
        sse: 0.96,
        ssr: 8.64,
        tss: 9.6,
        f_statistic: 54,
        f_p_value: 0.001,
      },
      coefficients: [
        {
          term: "Intercept",
          term_kind: "intercept",
          column_id: null,
          source_column_ids: [],
          response_column_id: "column-y",
          level: null,
          reference_level: null,
          coding: null,
          estimate: 1,
          standard_error: 0.2,
          statistic: 5,
          statistic_name: "t",
          p_value: 0.002,
          confidence_interval: {
            method: "t",
            level: 0.95,
            lower: 0.5,
            upper: 1.5,
          },
          vif: null,
        },
      ],
      diagnostics: {
        rank: 2,
        parameter_count: 2,
        condition_number: 12,
        max_vif: 1,
        residual_summary: {
          mean: 0,
          min: -0.3,
          q1: -0.1,
          median: 0,
          q3: 0.1,
          max: 0.3,
          max_abs_standardized: 1.2,
          large_standardized_threshold: 3,
          large_standardized_count: 0,
          large_standardized_row_indices: [],
        },
        leverage: {
          mean: 0.25,
          max: 0.45,
          threshold: 0.5,
          high_count: 0,
          high_row_indices: [],
        },
        influence: {
          cooks_distance_max: 0.2,
          cooks_distance_threshold: 0.5,
          high_cooks_distance_count: 0,
          high_cooks_distance_row_indices: [],
        },
        diagnostic_points: {
          point_limit: 500,
          points_included: 1,
          truncated: false,
          points: [
            {
              row_index: 0,
              fitted: 10,
              residual: 0.1,
              standardized_residual: 0.25,
              leverage: 0.45,
              cooks_distance: 0.2,
            },
          ],
        },
      },
      model_manifest: {
        model_id: "12345678-90ab-cdef-1234-567890abcdef",
        manifest_schema_version: 2,
        manifest_sha256: "a".repeat(64),
      },
    };
    const predictionPreflight: RegressionPredictionPreflightResponse = {
      model_id: "12345678-90ab-cdef-1234-567890abcdef",
      analysis_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      source_dataset_version_id: version.version_id,
      target_dataset_version_id: version.version_id,
      model_manifest_sha256: "a".repeat(64),
      source_schema_hash: "source-schema",
      target_schema_hash: "target-schema",
      schema_hash_match: false,
      row_count_total: 8,
      row_count_usable: 7,
      prediction_ready: true,
      required_columns: [
        {
          source_column_id: "column-a",
          display_name: "A",
          predictor_kind: "numeric",
          target_column_id: "column-a",
          match_type: "column_id",
          status: "ok",
        },
      ],
      numeric_checks: [
        {
          source_column_id: "column-a",
          target_column_id: "column-a",
          display_name: "A",
          n_valid: 7,
          n_missing: 1,
          n_non_numeric: 0,
          n_below_training_range: 0,
          n_above_training_range: 1,
        },
      ],
      categorical_checks: [],
      issues: [
        {
          code: "prediction_schema_hash_mismatch",
          severity: "warning",
          message: "대상 데이터셋 schema hash가 모델 생성 시점과 다릅니다.",
          source_column_id: null,
          target_column_id: null,
          display_name: null,
          count: null,
        },
      ],
    };
    const prediction: RegressionPredictionResponse = {
      prediction_id: "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
      model_id: "12345678-90ab-cdef-1234-567890abcdef",
      analysis_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      source_dataset_version_id: version.version_id,
      target_dataset_version_id: version.version_id,
      model_manifest_sha256: "a".repeat(64),
      target_schema_hash: "target-schema",
      row_count_total: 8,
      row_count_predicted: 7,
      row_count_excluded: 1,
      row_count_omitted: 0,
      row_limit: 1000,
      truncated: false,
      confidence_level: 0.95,
      warnings: [
        {
          code: "regression_prediction_not_causation",
          severity: "info",
          message: "회귀 예측은 관찰 데이터 기반의 수학적 예측이며 인과 효과를 의미하지 않습니다.",
          count: null,
        },
      ],
      provenance: {
        prediction_schema_version: 1,
        method_id: "regression.predict",
      },
      columns: predictionPreflight.required_columns,
      rows: [
        {
          row_index: 0,
          predicted_mean: 9.975,
          mean_confidence_interval: {
            method: "t",
            level: 0.95,
            lower: 9.4,
            upper: 10.55,
          },
          prediction_interval: {
            method: "t",
            level: 0.95,
            lower: 8.9,
            upper: 11.05,
          },
          warnings: [],
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        linearModelInteractionKeys={["column-a::column-x2"]}
        linearModelPredictorColumnIds={["column-a", "column-x2"]}
        linearModelPredictorColumns={[baseColumns[0], xColumn, yColumn]}
        linearModelPrediction={prediction}
        linearModelPredictionPreflight={predictionPreflight}
        linearModelQuadraticColumnIds={["column-a"]}
        linearModelResult={linearModelResult}
        linearModelResponseColumnId="column-y"
        linearModelResponseColumns={[baseColumns[0], xColumn, yColumn]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="regression"
        version={version}
      />,
    );

    expect(html).toContain("회귀모형 적합 실행");
    expect(html).toContain("반응 변수");
    expect(html).toContain("예측변수");
    expect(html).toContain("treatment coding");
    expect(html).toContain("숫자형 2차항");
    expect(html).toContain("숫자형 상호작용");
    expect(html).toContain("최대 Cook");
    expect(html).toContain("Std residual");
    expect(html).toContain("회귀 진단 차트");
    expect(html).toContain("Residuals vs Fitted");
    expect(html).toContain("Leverage vs Cook");
    expect(html).toContain("Model ID");
    expect(html).toContain("12345678-90");
    expect(html).toContain("예측 사전점검");
    expect(html).toContain("사전점검 실행");
    expect(html).toContain("예측 실행");
    expect(html).toContain("예측 준비 가능");
    expect(html).toContain("예측 결과 요약");
    expect(html).toContain("예측 구간 차트");
    expect(html).toContain("Prediction ID");
    expect(html).toContain("예측 평균");
    expect(html).toContain("9.975");
    expect(html).toContain("Schema hash");
    expect(html).toContain("컬럼 ID");
    expect(html).toContain("학습범위 위");
  });

  it("renders the individuals chart execution panel for the first quality method", () => {
    const columns = filterTestColumns();
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "quality",
          label_ko: "품질 관리",
          label_en: "Quality Control",
          order: 5,
        },
      ],
      methods: [
        {
          method_id: "quality.individuals_chart",
          method_version: "0.1.0",
          module_id: "quality",
          label_ko: "개별값 관리도",
          label_en: "Variables Charts for Individuals",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 2,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        individualsChartResult={individualsChartTestResult()}
        individualsChartOrderColumnId={null}
        individualsChartOrderColumns={columns.slice(1, 2)}
        individualsChartValueColumnId="column-a"
        individualsChartValueColumns={[columns[0]]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("품질 관리");
    expect(html).toContain("개별값 관리도 실행");
    expect(html).toContain("순서 컬럼");
    expect(html).toContain("선택 안 함");
    expect(html).toContain("canonical row order");
    expect(html).toContain("MRbar / d2");
    expect(html).toContain("same side");
    expect(html).toContain("I chart");
    expect(html).toContain("MR chart");
    expect(html).toContain("individuals_chart_i_beyond_3_sigma");
  });

  it("renders the run chart execution panel for the first quality method", () => {
    const columns = filterTestColumns();
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "quality",
          label_ko: "품질 관리",
          label_en: "Quality Control",
          order: 5,
        },
      ],
      methods: [
        {
          method_id: "quality.run_chart",
          method_version: "0.1.0",
          module_id: "quality",
          label_ko: "런 차트",
          label_en: "Run Chart",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 4,
          disabled_reason: null,
        },
      ],
    };
    const datetimeOrderColumn: DatasetColumnResponse = {
      ...columns[1],
      column_id: "column-when",
      column_index: 1,
      original_name: "when",
      display_name: "When",
      data_type: "datetime",
      measurement_level: "datetime",
      role: "time",
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        runChartOrderColumnId={null}
        runChartOrderColumns={[datetimeOrderColumn]}
        runChartResult={runChartTestResult()}
        runChartValueColumnId="column-a"
        runChartValueColumns={[columns[0]]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("품질 관리");
    expect(html).toContain("런 차트 실행");
    expect(html).toContain("canonical row order");
    expect(html).toContain("When");
    expect(html).toContain("순서");
    expect(html).toContain("Oscillation");
    expect(html).toContain("관리한계");
    expect(html).toContain("계산 안 함");
    expect(html).toContain("Run count");
    expect(html).toContain("A run chart");
    expect(html).toContain("run_chart_trend");
  });

  it("renders the subgroup chart execution panel for the first quality method", () => {
    const columns = filterTestColumns();
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "quality",
          label_ko: "품질 관리",
          label_en: "Quality Control",
          order: 5,
        },
      ],
      methods: [
        {
          method_id: "quality.subgroup_chart",
          method_version: "0.1.0",
          module_id: "quality",
          label_ko: "부분군 관리도",
          label_en: "Variables Charts for Subgroups",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 3,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        subgroupChartResult={subgroupChartTestResult()}
        subgroupChartSubgroupColumnId="column-b"
        subgroupChartSubgroupColumns={[columns[1]]}
        subgroupChartValueColumnId="column-a"
        subgroupChartValueColumns={[columns[0]]}
        version={version}
      />,
    );

    expect(html).toContain("부분군 관리도 실행");
    expect(html).toContain("Xbar-R");
    expect(html).toContain("Xbar-S");
    expect(html).toContain("fixed subgroup size");
    expect(html).toContain("Xbar chart");
    expect(html).toContain("Rbar");
    expect(html).toContain("subgroup_chart_xbar_beyond_control_limits");
  });

  it("renders the capability execution panel for the first quality method", () => {
    const columns = filterTestColumns();
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "quality",
          label_ko: "품질 관리",
          label_en: "Quality Control",
          order: 5,
        },
      ],
      methods: [
        {
          method_id: "quality.capability",
          method_version: "0.1.0",
          module_id: "quality",
          label_ko: "공정능력 분석",
          label_en: "Capability Analysis",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 5,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        capabilityLsl="8"
        capabilityResult={capabilityTestResult()}
        capabilityTarget="12"
        capabilityUsl="16"
        capabilityValueColumnId="column-a"
        capabilityValueColumns={[columns[0]]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("공정능력 분석 실행");
    expect(html).toContain("Normal capability");
    expect(html).toContain("MRbar/d2 within");
    expect(html).toContain("Cp / Pp");
    expect(html).toContain("Cpk / Ppk");
    expect(html).toContain("capability histogram");
    expect(html).toContain("Total ppm");
  });

  it("renders the Gage R&R execution panel with ANOVA and variance components", () => {
    const columns = gageRrTestColumns();
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "quality",
          label_ko: "품질 관리",
          label_en: "Quality Control",
          order: 5,
        },
      ],
      methods: [
        {
          method_id: "quality.gage_rr",
          method_version: "0.1.0",
          module_id: "quality",
          label_ko: "Gage R&R",
          label_en: "Gage R&R Study",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 6,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        gageRrMeasurementColumnId="measurement"
        gageRrMeasurementColumns={[columns[0]]}
        gageRrOperatorColumnId="operator"
        gageRrOperatorColumns={[columns[2]]}
        gageRrPartColumnId="part"
        gageRrPartColumns={[columns[1]]}
        gageRrPreflight={gageRrPreflightTestResponse()}
        gageRrReplicateColumnId="replicate"
        gageRrReplicateColumns={[columns[3]]}
        gageRrResult={gageRrTestResult()}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("Gage R&amp;R 실행");
    expect(html).toContain("사용 가능");
    expect(html).toContain("balanced crossed ANOVA");
    expect(html).toContain("Gage R&amp;R 계산");
    expect(html).toContain("준비됨");
    expect(html).toContain("Replicates per cell");
    expect(html).toContain("Total Gage R&amp;R");
    expect(html).toContain("Part-to-Part");
    expect(html).toContain("%Contribution");
    expect(html).toContain("NDC");
  });

  it("renders the Gage Run Chart execution panel with redacted indexed points", () => {
    const columns = [
      ...gageRrTestColumns(),
      {
        column_id: "run",
        version_id: "version-1",
        column_index: 4,
        original_name: "run",
        display_name: "Run",
        data_type: "integer",
        measurement_level: "ordinal",
        role: "order",
        unit: null,
      } satisfies DatasetColumnResponse,
    ];
    const version: DatasetVersionResponse = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "quality",
          label_ko: "품질 관리",
          label_en: "Quality Control",
          order: 5,
        },
      ],
      methods: [
        {
          method_id: "quality.gage_run_chart",
          method_version: "0.1.0",
          module_id: "quality",
          label_ko: "Gage Run Chart",
          label_en: "Gage Run Chart",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 7,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        gageRrMeasurementColumnId="measurement"
        gageRrMeasurementColumns={[columns[0]]}
        gageRrOperatorColumnId="operator"
        gageRrOperatorColumns={[columns[2]]}
        gageRrPartColumnId="part"
        gageRrPartColumns={[columns[1]]}
        gageRrReplicateColumnId="replicate"
        gageRrReplicateColumns={[columns[3]]}
        gageRunChartOrderColumnId="run"
        gageRunChartOrderColumns={[columns[4]]}
        gageRunChartResult={gageRunChartTestResult()}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("Gage Run Chart 실행");
    expect(html).toContain("part/operator/replicate index only");
    expect(html).toContain("Part facet");
    expect(html).toContain("Operator color");
    expect(html).toContain("Replicate symbol");
    expect(html).toContain("부품 요약");
    expect(html).toContain("측정자 요약");
    expect(html).toContain("redacted");
    expect(html).not.toContain("Part A");
    expect(html).not.toContain("Operator 1");
  });

  it("renders the split AnalysisShell with filters and descriptive execution panel", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "exploration",
          label_ko: "탐색적 분석",
          label_en: "Exploration",
          order: 1,
        },
      ],
      methods: [
        {
          method_id: "eda.descriptive",
          method_version: "0.1.0",
          module_id: "exploration",
          label_ko: "기술통계",
          label_en: "Descriptive Statistics",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 1,
          disabled_reason: null,
        },
      ],
    };
    const version: DatasetVersionResponse = {
      version_id: "version-1",
      dataset_id: "dataset-1",
      version_number: 1,
      row_count: 3,
      column_count: columns.length,
      schema_hash: "schema-hash",
      created_at: "2026-06-27T00:00:00Z",
      source_sha256: "source-hash",
      canonical_artifact: null,
      parsing: {
        kind: "delimited_text",
        encoding: "utf-8",
        delimiter: ",",
        quote_char: "\"",
        decimal: ".",
        thousands: null,
        has_header: true,
        header_row: 1,
        data_start_row: 2,
        missing_tokens: [""],
        xlsx_sheet_name: null,
      },
      columns,
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="exploration"
        version={version}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("탐색적 분석");
    expect(html).toContain("분석 필터");
    expect(html).toContain("기술통계 실행");
    expect(html).toContain("A");
  });

  it("renders the graphical summary execution panel for the second real exploration method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "exploration",
          label_ko: "탐색적 분석",
          label_en: "Exploration",
          order: 1,
        },
      ],
      methods: [
        {
          method_id: "eda.graphical_summary",
          method_version: "0.1.0",
          module_id: "exploration",
          label_ko: "그래프 요약",
          label_en: "Graphical Summary",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 2,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={graphicalSummaryTestResult()}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("그래프 요약");
    expect(html).toContain("그래프 요약 실행");
    expect(html).toContain("분포 시각화");
    expect(html).toContain("히스토그램");
    expect(html).toContain("박스플롯");
    expect(html).toContain("Q-Q Plot");
    expect(html).toContain("ECDF");
    expect(html).toContain("A");
  });

  it("renders the normality execution panel for the third real exploration method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "exploration",
          label_ko: "탐색적 분석",
          label_en: "Exploration",
          order: 1,
        },
      ],
      methods: [
        {
          method_id: "eda.normality",
          method_version: "0.1.0",
          module_id: "exploration",
          label_ko: "정규성 검정",
          label_en: "Normality Test",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 3,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={normalityTestResult()}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("정규성 검정");
    expect(html).toContain("정규성 검정 실행");
    expect(html).toContain("유의수준 alpha");
    expect(html).toContain("Q-Q Plot");
    expect(html).toContain("standard_normal");
    expect(html).toContain("Shapiro p");
    expect(html).toContain("A");
  });

  it("renders the equal variances execution panel for the fourth real exploration method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "exploration",
          label_ko: "탐색적 분석",
          label_en: "Exploration",
          order: 1,
        },
      ],
      methods: [
        {
          method_id: "eda.equal_variances",
          method_version: "0.1.0",
          module_id: "exploration",
          label_ko: "등분산 검정",
          label_en: "Test for Equal Variances",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 4,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("등분산 검정");
    expect(html).toContain("등분산 검정 실행");
    expect(html).toContain("반응 변수");
    expect(html).toContain("그룹 변수");
    expect(html).toContain("A");
    expect(html).toContain("B");
  });

  it("renders the one-sample t execution panel for the first single-sample hypothesis method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.one_sample_t",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "1-표본 t-검정",
          label_en: "1-Sample t-Test",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 1,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("1-표본 t-검정");
    expect(html).toContain("1-표본 t-검정 실행");
    expect(html).toContain("기준 평균");
    expect(html).toContain("반응 변수");
  });

  it("renders the equivalence TOST execution panel for one-sample mean equivalence", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.equivalence_tost",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "동등성 검정",
          label_en: "Equivalence Test (TOST)",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 5,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("동등성 검정");
    expect(html).toContain("동등성 검정 실행");
    expect(html).toContain("동등성 하한");
    expect(html).toContain("동등성 상한");
    expect(html).toContain("TOST CI 수준");
  });

  it("renders the paired t-test execution panel for paired wide data", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.paired_t",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "대응표본 t-검정",
          label_en: "Paired t-Test",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 2,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...pairedTTestProps(columns)}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("대응표본 t-검정");
    expect(html).toContain("대응표본 t-검정 실행");
    expect(html).toContain("첫 번째 측정");
    expect(html).toContain("두 번째 측정");
    expect(html).toContain("기준 차이");
  });

  it("renders the one-sample Wilcoxon execution panel for the first rank-based single-sample method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.one_sample_wilcoxon",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "1-표본 Wilcoxon",
          label_en: "1-Sample Wilcoxon Signed-Rank",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 6,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("1-표본 Wilcoxon");
    expect(html).toContain("1-표본 Wilcoxon 실행");
    expect(html).toContain("기준 위치");
    expect(html).toContain("zero 처리");
    expect(html).toContain("p-value 방식");
  });

  it("renders the two-sample t execution panel for the first real hypothesis method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.two_sample_t",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "2-표본 t-검정",
          label_en: "2-Sample t-Test",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 3,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("2-표본 t-검정");
    expect(html).toContain("2-표본 t-검정 실행");
    expect(html).toContain("Welch 기본");
    expect(html).toContain("반응 변수");
    expect(html).toContain("그룹 변수");
  });

  it("renders the Mann-Whitney execution panel for the first rank-based hypothesis method", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.mann_whitney",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "Mann-Whitney U",
          label_en: "Mann-Whitney U",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 7,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        analysisCatalog={catalog}
        analysisCatalogError={null}
        analysisFilterDrafts={[]}
        analysisFilterValidationError={null}
        analysisFilterValidationMessage={null}
        analysisRunError={null}
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        equalVariancesAlpha={0.05}
        equalVariancesAnalysisResult={null}
        equalVariancesGroupColumnId="column-b"
        equalVariancesGroupColumns={[columns[1]]}
        equalVariancesResponseColumnId="column-a"
        equalVariancesResponseColumns={[columns[0]]}
        equalVariancesResult={null}
        twoSampleTAlpha={0.05}
        twoSampleTAlternative="two_sided"
        twoSampleTAnalysisResult={null}
        twoSampleTConfidenceLevel={0.95}
        twoSampleTGroupColumnId="column-b"
        twoSampleTGroupColumns={[columns[1]]}
        twoSampleTResponseColumnId="column-a"
        twoSampleTResponseColumns={[columns[0]]}
        twoSampleTResult={null}
        twoSampleTVarianceAssumption="welch"
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
        {...chiSquareAssociationTestProps(columns)}
        {...mannWhitneyTestProps(columns)}
        {...kruskalWallisTestProps(columns)}
        {...oneWayAnovaTestProps(columns)}
        {...oneProportionTestProps(columns)}
        {...twoProportionTestProps(columns)}
        {...pairedTTestProps(columns)}
        {...oneSampleWilcoxonTestProps(columns)}
        {...equivalenceTostTestProps(columns)}
        {...pearsonTestProps(columns)}
        normalityAlpha={0.05}
        normalityAnalysisResult={null}
        normalityColumns={[columns[0]]}
        normalityResult={null}
        oneSampleTAlpha={0.05}
        oneSampleTAlternative="two_sided"
        oneSampleTAnalysisResult={null}
        oneSampleTConfidenceLevel={0.95}
        oneSampleTNullMean={0}
        oneSampleTResponseColumnId="column-a"
        oneSampleTResponseColumns={[columns[0]]}
        oneSampleTResult={null}
        profile={null}
        selectedDescriptiveColumnIds={["column-a"]}
        selectedGraphicalSummaryColumnIds={["column-a"]}
        selectedNormalityColumnIds={["column-a"]}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunEqualVariancesAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onRunOneSampleTAnalysis={() => undefined}
        onRunTwoSampleTAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onEqualVariancesAlphaChange={() => undefined}
        onEqualVariancesGroupColumnChange={() => undefined}
        onEqualVariancesResponseColumnChange={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onOneSampleTAlphaChange={() => undefined}
        onOneSampleTAlternativeChange={() => undefined}
        onOneSampleTConfidenceLevelChange={() => undefined}
        onOneSampleTNullMeanChange={() => undefined}
        onOneSampleTResponseColumnChange={() => undefined}
        onTwoSampleTAlphaChange={() => undefined}
        onTwoSampleTAlternativeChange={() => undefined}
        onTwoSampleTConfidenceLevelChange={() => undefined}
        onTwoSampleTGroupColumnChange={() => undefined}
        onTwoSampleTResponseColumnChange={() => undefined}
        onTwoSampleTVarianceAssumptionChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("Mann-Whitney U");
    expect(html).toContain("Mann-Whitney U 실행");
    expect(html).toContain("p-value 방식");
    expect(html).toContain("반응 변수");
    expect(html).toContain("그룹 변수");
  });

  it("renders the Kruskal-Wallis execution panel for three-or-more independent groups", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.kruskal_wallis",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "Kruskal-Wallis",
          label_en: "Kruskal-Wallis",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 8,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...kruskalWallisTestProps(columns)}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("Kruskal-Wallis");
    expect(html).toContain("Kruskal-Wallis 실행");
    expect(html).toContain("반응 변수");
    expect(html).toContain("그룹 변수");
    expect(html).toContain("Dunn 사후검정");
  });

  it("renders the one-way ANOVA execution panel with Tukey-Kramer policy", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "hypothesis",
          label_ko: "가설 검정",
          label_en: "Hypothesis",
          order: 2,
        },
      ],
      methods: [
        {
          method_id: "hypothesis.one_way_anova",
          method_version: "0.1.0",
          module_id: "hypothesis",
          label_ko: "일원분산분석",
          label_en: "One-Way ANOVA",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 4,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...oneWayAnovaTestProps(columns)}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("일원분산분석");
    expect(html).toContain("일원분산분석 실행");
    expect(html).toContain("반응 변수");
    expect(html).toContain("그룹 변수");
    expect(html).toContain("Tukey-Kramer");
  });

  it("renders the 1-proportion execution panel for a binary categorical response", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "categorical",
          label_ko: "범주형 데이터 분석",
          label_en: "Categorical",
          order: 3,
        },
      ],
      methods: [
        {
          method_id: "categorical.one_proportion",
          method_version: "0.1.0",
          module_id: "categorical",
          label_ko: "1-비율",
          label_en: "1-Proportion",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 1,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...oneProportionTestProps(columns)}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="categorical"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("1-비율");
    expect(html).toContain("1-비율 검정 실행");
    expect(html).toContain("사건 수준");
    expect(html).toContain("기준 비율 p0");
    expect(html).toContain("Wilson score");
  });

  it("renders the 2-proportion execution panel for a binary response by group", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "categorical",
          label_ko: "범주형 데이터 분석",
          label_en: "Categorical",
          order: 3,
        },
      ],
      methods: [
        {
          method_id: "categorical.two_proportion",
          method_version: "0.1.0",
          module_id: "categorical",
          label_ko: "2-비율",
          label_en: "2-Proportion",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 2,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...twoProportionTestProps(columns)}
        analysisCatalog={catalog}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="categorical"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("2-비율");
    expect(html).toContain("2-비율 검정 실행");
    expect(html).toContain("이진 반응 변수");
    expect(html).toContain("그룹 변수");
    expect(html).toContain("사건 수준");
    expect(html).toContain("신뢰수준");
  });

  it("renders the chi-square association execution panel for two categorical columns", () => {
    const columns = filterTestColumns();
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "categorical",
          label_ko: "범주형 데이터 분석",
          label_en: "Categorical",
          order: 3,
        },
      ],
      methods: [
        {
          method_id: "categorical.chi_square_association",
          method_version: "0.1.0",
          module_id: "categorical",
          label_ko: "카이제곱 독립성 검정",
          label_en: "Chi-square Test for Association",
          availability: "available",
          execution_mode: "inline",
          requires_dataset: true,
          order: 3,
          disabled_reason: null,
        },
      ],
    };

    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        {...chiSquareAssociationTestProps(columns)}
        analysisCatalog={catalog}
        chiSquareAssociationResult={chiSquareAssociationTestResult()}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="categorical"
        version={datasetVersionTestResponse()}
      />,
    );

    expect(html).toContain("카이제곱 독립성 검정");
    expect(html).toContain("카이제곱 독립성 검정 실행");
    expect(html).toContain("행 변수");
    expect(html).toContain("열 변수");
    expect(html).toContain("Pearson 카이제곱");
    expect(html).toContain("표준화 잔차 Heatmap");
    expect(html).toContain("residual 1.4");
    expect(html).toContain("-1.4");
  });

  it("renders the DatasetPreparationPage intake workflow", () => {
    const html = renderToString(<DatasetPreparationPage {...datasetPageTestProps()} />);

    expect(html).toContain("데이터셋 파싱 확정");
    expect(html).toContain("원본 데이터 파일");
    expect(html).toContain("복사한 표 붙여넣기");
    expect(html).toContain("작업 흐름");
  });

  it("routes the workspace between dataset preparation and analysis pages", () => {
    const analysisCatalog = analysisTestCatalog();
    const selectedMethod = analysisCatalog.methods[0];
    const analysisPageProps = {
      ...analysisPageTestProps(),
      analysisCatalog,
      selectedMethod,
      selectedMethods: [selectedMethod],
      version: datasetVersionTestResponse(),
    };
    const datasetHtml = renderToString(
      <WorkspaceRouter
        analysisPageProps={analysisPageTestProps()}
        datasetPageProps={datasetPageTestProps()}
        isAnalysisPage={false}
      />,
    );
    const analysisHtml = renderToString(
      <WorkspaceRouter
        analysisPageProps={{
          ...analysisPageProps,
          analysisRunError: "two_sample_t_requires_exactly_two_groups",
        }}
        datasetPageProps={{
          ...datasetPageTestProps(),
          flowError: "two_sample_t_requires_exactly_two_groups",
        }}
        isAnalysisPage
      />,
    );

    expect(datasetHtml).toContain("데이터셋 파싱 확정");
    expect(datasetHtml).not.toContain("분석 모듈");
    expect(analysisHtml).toContain("분석 모듈");
    expect(analysisHtml).toContain("2개 그룹 필요");
    expect(analysisHtml).toContain("해결 방법:");
    expect(analysisHtml).toContain("오류 코드:");
    expect(analysisHtml).toContain("two_sample_t_requires_exactly_two_groups");
    expect(analysisHtml).not.toContain(
      '<div class="error-box" role="alert">오류 코드: two_sample_t_requires_exactly_two_groups</div>',
    );
    expect(analysisHtml).not.toContain("원본 데이터 파일");
  });

  it("renders the AppChrome navigation and dataset context", () => {
    const html = renderToString(
      <AppChrome
        canOpenAnalysis={false}
        healthClassName="status-pill status-ready"
        healthLabel="API ok"
        isAnalysisPage={false}
        version={datasetVersionTestResponse()}
        onOpenAnalysisPage={() => undefined}
        onOpenDatasetPage={() => undefined}
      >
        <div>Workspace child</div>
      </AppChrome>,
    );

    expect(html).toContain("DataLab Studio");
    expect(html).toContain("로컬 분석 작업대");
    expect(html).toContain("Gate A 기반 구성");
    expect(html).toContain("API ok");
    expect(html).toContain("Dataset v");
    expect(html).toMatch(/1<\/span>/);
    expect(html).toMatch(/3(?:<!-- -->)?행/);
    expect(html).toMatch(/2(?:<!-- -->)?컬럼/);
    expect(html).toMatch(/schema (?:<!-- -->)?schema-hash/);
    expect(html).toMatch(/source (?:<!-- -->)?source-hash/);
    expect(html).toContain("Workspace child");
  });

  it("maps parsing suggestions into explicit confirmation options", () => {
    const confirmation = parsingSuggestionToConfirmation(datasetUploadTestResponse());

    expect(confirmation).toMatchObject({
      kind: "delimited_text",
      encoding: "utf-8",
      delimiter: "\t",
      has_header: false,
      header_row: 1,
      data_start_row: 10,
      xlsx_sheet_name: null,
    });
    expect(confirmation.missing_tokens).toEqual(["", "NA", "N/A", "null", "N/T"]);
    expect(canConfirmParsingOptions(confirmation)).toBe(true);
    expect(
      canConfirmParsingOptions({
        ...confirmation,
        data_start_row: null,
      }),
    ).toBe(false);
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

function gageRrTestColumns(): DatasetColumnResponse[] {
  return [
    {
      column_id: "measurement",
      version_id: "version-1",
      column_index: 0,
      original_name: "measurement",
      display_name: "Measurement",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "response",
      unit: null,
    },
    {
      column_id: "part",
      version_id: "version-1",
      column_index: 1,
      original_name: "part",
      display_name: "Part",
      data_type: "text",
      measurement_level: "id",
      role: "part_id",
      unit: null,
    },
    {
      column_id: "operator",
      version_id: "version-1",
      column_index: 2,
      original_name: "operator",
      display_name: "Operator",
      data_type: "text",
      measurement_level: "nominal",
      role: "operator_id",
      unit: null,
    },
    {
      column_id: "replicate",
      version_id: "version-1",
      column_index: 3,
      original_name: "replicate",
      display_name: "Replicate",
      data_type: "integer",
      measurement_level: "ordinal",
      role: "replicate_id",
      unit: null,
    },
  ];
}

function analysisTestCatalog(): AnalysisMethodListResponse {
  return {
    modules: [
      {
        module_id: "exploration",
        label_ko: "탐색적 분석",
        label_en: "Exploration",
        order: 1,
      },
      {
        module_id: "hypothesis",
        label_ko: "가설",
        label_en: "Hypothesis",
        order: 2,
      },
      {
        module_id: "quality",
        label_ko: "품질",
        label_en: "Quality",
        order: 5,
      },
    ],
    methods: [
      {
        method_id: "eda.descriptive",
        method_version: "0.1.0",
        module_id: "exploration",
        label_ko: "기술통계",
        label_en: "Descriptive Statistics",
        availability: "available",
        execution_mode: "inline",
        requires_dataset: true,
        order: 1,
        disabled_reason: null,
      },
      {
        method_id: "eda.graphical_summary",
        method_version: "0.1.0",
        module_id: "exploration",
        label_ko: "그래프 요약",
        label_en: "Graphical Summary",
        availability: "available",
        execution_mode: "inline",
        requires_dataset: true,
        order: 2,
        disabled_reason: null,
      },
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
}

function datasetUploadTestResponse(): DatasetUploadResponse {
  return {
    dataset_id: "dataset-1",
    original_filename: "sample.txt",
    size_bytes: 123,
    sha256: "source-hash",
    detected_format: "delimited_text",
    parsing: {
      kind: "delimited_text",
      encoding_candidates: ["utf-8"],
      suggested_encoding: "utf-8",
      delimiter_candidates: [
        {
          delimiter: "\t",
          label: "tab",
          score: 0.99,
        },
      ],
      suggested_delimiter: "\t",
      quote_char: "\"",
      decimal: ".",
      thousands: null,
      has_header: false,
      header_row: 1,
      data_start_row: 10,
      xlsx_requires_sheet_selection: false,
    },
    warnings: [],
    next_step: "confirm_schema",
  };
}

function datasetVersionTestResponse(): DatasetVersionResponse {
  const columns = filterTestColumns();
  return {
    version_id: "version-1",
    dataset_id: "dataset-1",
    version_number: 1,
    row_count: 3,
    column_count: columns.length,
    schema_hash: "schema-hash",
    created_at: "2026-06-27T00:00:00Z",
    source_sha256: "source-hash",
    canonical_artifact: null,
    parsing: {
      kind: "delimited_text",
      encoding: "utf-8",
      delimiter: ",",
      quote_char: "\"",
      decimal: ".",
      thousands: null,
      has_header: true,
      header_row: 1,
      data_start_row: 2,
      missing_tokens: [""],
      xlsx_sheet_name: null,
    },
    columns,
  };
}

function factorialDesignTestResponse(): FactorialDesignResponse {
  return {
    design_id: "11111111-1111-4111-8111-111111111111",
    design_version_id: "22222222-2222-4222-8222-222222222222",
    version_number: 1,
    method_id: "doe.factorial_design",
    method_version: "0.1.0",
    family: "two_level_full_factorial",
    name: "screening design",
    status: "designed",
    created_at: "2026-07-02T00:00:00.000Z",
    updated_at: "2026-07-02T00:00:00.000Z",
    app_version: "0.1.0",
    factors: [
      { name: "Temperature", low: 60, high: 80, unit: "C" },
      { name: "Pressure", low: 5, high: 15, unit: "bar" },
    ],
    options: {
      replicates: 1,
      center_points: 1,
      randomize: false,
      randomization_seed: 20260702,
      block_count: 1,
    },
    run_count: 5,
    design_sha256: "design-hash-012345678901234567890123456789012345678901234567890",
    runs: [
      {
        standard_order: 1,
        run_order: 1,
        replicate_index: 1,
        center_point: false,
        block_index: null,
        factor_levels: { Temperature: 60, Pressure: 5 },
        coded_levels: { Temperature: -1, Pressure: -1 },
      },
      {
        standard_order: 2,
        run_order: 2,
        replicate_index: 1,
        center_point: false,
        block_index: null,
        factor_levels: { Temperature: 80, Pressure: 5 },
        coded_levels: { Temperature: 1, Pressure: -1 },
      },
      {
        standard_order: 3,
        run_order: 3,
        replicate_index: 1,
        center_point: false,
        block_index: null,
        factor_levels: { Temperature: 60, Pressure: 15 },
        coded_levels: { Temperature: -1, Pressure: 1 },
      },
      {
        standard_order: 4,
        run_order: 4,
        replicate_index: 1,
        center_point: false,
        block_index: null,
        factor_levels: { Temperature: 80, Pressure: 15 },
        coded_levels: { Temperature: 1, Pressure: 1 },
      },
      {
        standard_order: 5,
        run_order: 5,
        replicate_index: 1,
        center_point: true,
        block_index: null,
        factor_levels: { Temperature: 70, Pressure: 10 },
        coded_levels: { Temperature: 0, Pressure: 0 },
      },
    ],
  };
}

function graphicalSummaryTestResult(): GraphicalSummaryResult {
  return {
    schema_version: 1,
    summary_type: "graphical_summary",
    histogram_method: "fixed_count",
    boxplot_method: "tukey_1_5_iqr",
    qq_plot_distribution: "standard_normal",
    qq_plotting_position: "rank_minus_half_over_n",
    ecdf_method: "right_continuous",
    point_limit: 1000,
    columns: [
      {
        column_id: "column-a",
        column_index: 0,
        display_name: "A",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "feature",
        unit: null,
        n_total: 5,
        n_used: 5,
        n_missing: 0,
        n_non_numeric: 0,
        min: 1,
        q1: 2,
        median: 3,
        q3: 4,
        max: 5,
        histogram: {
          binning: "fixed_count",
          bin_count: 2,
          bins: [
            {
              lower: 1,
              upper: 3,
              count: 2,
              include_lower: true,
              include_upper: false,
            },
            {
              lower: 3,
              upper: 5,
              count: 3,
              include_lower: true,
              include_upper: true,
            },
          ],
        },
        boxplot: {
          lower_whisker: 1,
          q1: 2,
          median: 3,
          q3: 4,
          upper_whisker: 5,
          lower_fence: -1,
          upper_fence: 7,
          outlier_count: 0,
        },
        qq_plot: {
          point_count: 5,
          points_truncated: false,
          points: [
            { theoretical: -1.28, sample: 1 },
            { theoretical: -0.52, sample: 2 },
            { theoretical: 0, sample: 3 },
            { theoretical: 0.52, sample: 4 },
            { theoretical: 1.28, sample: 5 },
          ],
        },
        ecdf: {
          point_count: 5,
          points_truncated: false,
          points: [
            { x: 1, probability: 0.2 },
            { x: 2, probability: 0.4 },
            { x: 3, probability: 0.6 },
            { x: 4, probability: 0.8 },
            { x: 5, probability: 1 },
          ],
        },
        warnings: [],
      },
    ],
  };
}

function normalityTestResult(): NormalityResult {
  return {
    schema_version: 1,
    summary_type: "normality_test",
    missing_policy: "complete_case",
    alpha: 0.05,
    qq_plot_distribution: "standard_normal",
    qq_plotting_position: "rank_minus_half_over_n",
    shape_moment_definition: "sample_adjusted",
    package_versions: {
      numpy: "2.2.6",
      scipy: "1.15.3",
    },
    warnings: [],
    columns: [
      {
        column_id: "column-a",
        column_index: 0,
        display_name: "A",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "feature",
        unit: null,
        n_total: 5,
        n_used: 5,
        n_missing: 0,
        n_non_numeric: 0,
        mean: 3,
        std: 1.5811388300841898,
        skewness: 0,
        kurtosis_excess: -1.2,
        shapiro_wilk: {
          computed: true,
          statistic: 0.986762,
          p_value: 0.967174,
          valid_n_min: 3,
          p_value_accuracy_n_max: 5000,
        },
        anderson_darling: {
          computed: true,
          statistic: 0.143595,
          critical_values: [
            {
              significance_level: 5,
              critical_value: 0.984,
              reject_normality: false,
            },
          ],
          decision_at_alpha: {
            alpha: 0.05,
            critical_value: 0.984,
            reject_normality: false,
            method: "nearest_significance_level",
          },
        },
        qq_plot: {
          point_count: 5,
          points_truncated: false,
          points: [
            { theoretical: -1.28, sample: 1 },
            { theoretical: -0.52, sample: 2 },
            { theoretical: 0, sample: 3 },
            { theoretical: 0.52, sample: 4 },
            { theoretical: 1.28, sample: 5 },
          ],
        },
        warnings: [],
      },
    ],
  };
}

function pearsonCorrelationTestResult(): PearsonCorrelationResult {
  return {
    schema_version: 1,
    summary_type: "pearson_correlation",
    method: "pearson_product_moment_correlation",
    missing_policy: "complete_case",
    alternative: "two_sided",
    alpha: 0.05,
    confidence_level: 0.95,
    package_versions: {
      numpy: "2.2.6",
      scipy: "1.15.3",
    },
    warnings: ["pearson_correlation_not_causation"],
    x: {
      column_id: "column-a",
      column_index: 0,
      display_name: "A",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "feature",
      unit: null,
    },
    y: {
      column_id: "column-c",
      column_index: 2,
      display_name: "C",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "response",
      unit: null,
    },
    n_total: 6,
    n_used: 6,
    n_excluded_missing_x: 0,
    n_excluded_missing_y: 0,
    n_excluded_non_numeric_x: 0,
    n_excluded_non_numeric_y: 0,
    x_summary: {
      n: 6,
      mean: 3.5,
      std: 1.8708286933869707,
      min: 1,
      max: 6,
    },
    y_summary: {
      n: 6,
      mean: 3.3333333333333335,
      std: 2.250925735484551,
      min: 1,
      max: 7,
    },
    scatterplot: {
      x_column_id: "column-a",
      y_column_id: "column-c",
      point_count: 6,
      points_truncated: false,
      point_limit: 500,
      points: [
        { x: 1, y: 1 },
        { x: 2, y: 2 },
        { x: 3, y: 1 },
        { x: 4, y: 4 },
        { x: 5, y: 5 },
        { x: 6, y: 7 },
      ],
    },
    association: {
      correlation: 0.9268715709799871,
      r_squared: 0.859090909090909,
      covariance: 4.2,
      correlation_definition: "pearson_product_moment",
    },
    test: {
      statistic: 0.9268715709799871,
      statistic_name: "r",
      p_value: 0.007826113791877531,
      reject_null: true,
      null_hypothesis: "population_correlation_equals_0",
      alternative: "two_sided",
    },
    confidence_interval: {
      method: "fisher_z",
      level: 0.95,
      lower: 0.46536068630404304,
      upper: 0.9921355297202177,
    },
  };
}

function xyCorrelationTestResult(): XyCorrelationResult {
  const xA = {
    column_id: "column-a",
    column_index: 0,
    display_name: "A",
    data_type: "decimal" as const,
    measurement_level: "continuous" as const,
    role: "feature" as const,
    unit: null,
  };
  const x2 = {
    column_id: "column-x2",
    column_index: 2,
    display_name: "X2",
    data_type: "decimal" as const,
    measurement_level: "continuous" as const,
    role: "feature" as const,
    unit: null,
  };
  const y = {
    column_id: "column-y",
    column_index: 3,
    display_name: "Y",
    data_type: "decimal" as const,
    measurement_level: "continuous" as const,
    role: "response" as const,
    unit: null,
  };
  return {
    schema_version: 1,
    summary_type: "xy_correlation_matrix",
    method: "pairwise_pearson_product_moment_correlation",
    missing_policy: "complete_case_by_pair",
    alternative: "two_sided",
    alpha: 0.05,
    confidence_level: 0.95,
    package_versions: {
      numpy: "2.2.6",
      scipy: "1.15.3",
    },
    warnings: ["xy_correlation_not_causation"],
    x_columns: [xA, x2],
    y_columns: [y],
    x_column_count: 2,
    y_column_count: 1,
    pair_count: 2,
    pairs: [
      {
        x: xA,
        y,
        n_total: 6,
        n_used: 6,
        n_excluded_missing_x: 0,
        n_excluded_missing_y: 0,
        n_excluded_non_numeric_x: 0,
        n_excluded_non_numeric_y: 0,
        status: "ok",
        error_code: null,
        warnings: [],
        association: {
          correlation: 0.8,
          r_squared: 0.64,
          covariance: 2.5,
          correlation_definition: "pearson_product_moment",
        },
        test: {
          statistic: 0.8,
          statistic_name: "r",
          p_value: 0.055,
          reject_null: false,
          null_hypothesis: "population_correlation_equals_0",
          alternative: "two_sided",
        },
        confidence_interval: {
          method: "fisher_z",
          level: 0.95,
          lower: -0.1,
          upper: 0.98,
        },
      },
      {
        x: x2,
        y,
        n_total: 6,
        n_used: 6,
        n_excluded_missing_x: 0,
        n_excluded_missing_y: 0,
        n_excluded_non_numeric_x: 0,
        n_excluded_non_numeric_y: 0,
        status: "ok",
        error_code: null,
        warnings: [],
        association: {
          correlation: -0.5,
          r_squared: 0.25,
          covariance: -1.1,
          correlation_definition: "pearson_product_moment",
        },
        test: {
          statistic: -0.5,
          statistic_name: "r",
          p_value: 0.312,
          reject_null: false,
          null_hypothesis: "population_correlation_equals_0",
          alternative: "two_sided",
        },
        confidence_interval: {
          method: "fisher_z",
          level: 0.95,
          lower: -0.93,
          upper: 0.57,
        },
      },
    ],
  };
}

function chiSquareAssociationTestResult(): ChiSquareAssociationResult {
  return {
    schema_version: 1,
    summary_type: "chi_square_association",
    method: "pearson_chi_square_independence",
    input_mode: "columns",
    missing_policy: "complete_case",
    alpha: 0.05,
    package_versions: {
      numpy: "2.2.6",
      scipy: "1.15.3",
    },
    warnings: ["pearson_chi_square_no_continuity_correction"],
    row_variable: {
      column_id: "column-a",
      column_index: 0,
      display_name: "A",
      data_type: "text",
      measurement_level: "nominal",
      role: "group",
      unit: null,
    },
    column_variable: {
      column_id: "column-b",
      column_index: 1,
      display_name: "B",
      data_type: "text",
      measurement_level: "nominal",
      role: "group",
      unit: null,
    },
    n_total: 50,
    n_used: 50,
    n_excluded_missing_row: 0,
    n_excluded_missing_column: 0,
    row_levels: [
      { level: "A1", index: 0, count: 30 },
      { level: "A2", index: 1, count: 20 },
    ],
    column_levels: [
      { level: "B1", index: 0, count: 25 },
      { level: "B2", index: 1, count: 25 },
    ],
    contingency_table: {
      row_levels: ["A1", "A2"],
      column_levels: ["B1", "B2"],
      column_totals: [25, 25],
      grand_total: 50,
      rows: [
        {
          row_level: "A1",
          row_total: 30,
          cells: [
            {
              column_level: "B1",
              observed: 18,
              expected: 15,
              row_percent: 0.6,
              column_percent: 0.72,
              total_percent: 0.36,
              standardized_residual: 1.4,
            },
            {
              column_level: "B2",
              observed: 12,
              expected: 15,
              row_percent: 0.4,
              column_percent: 0.48,
              total_percent: 0.24,
              standardized_residual: -1.4,
            },
          ],
        },
        {
          row_level: "A2",
          row_total: 20,
          cells: [
            {
              column_level: "B1",
              observed: 7,
              expected: 10,
              row_percent: 0.35,
              column_percent: 0.28,
              total_percent: 0.14,
              standardized_residual: -1.1,
            },
            {
              column_level: "B2",
              observed: 13,
              expected: 10,
              row_percent: 0.65,
              column_percent: 0.52,
              total_percent: 0.26,
              standardized_residual: 1.1,
            },
          ],
        },
      ],
    },
    expected_count_summary: {
      min_expected: 10,
      cells_below_1: 0,
      cells_below_5: 0,
      cell_count: 4,
      share_below_5: 0,
      rule_of_thumb_passed: true,
    },
    test: {
      statistic: 3.2,
      statistic_name: "chi_square",
      df: 1,
      p_value: 0.073638,
      reject_null: false,
      continuity_correction: false,
    },
    effect_size: {
      cramers_v: 0.253,
      definition: "cramers_v",
    },
    recommended_alternative_tests: [],
  };
}

function datasetPageTestProps(): ComponentProps<typeof DatasetPreparationPage> {
  return {
    canApplyBayesianPreset: false,
    canConfirm: false,
    delimiterOptions: [",", "\t"],
    flowError: null,
    isConfirming: false,
    isLoadingPreview: false,
    isLoadingProfile: false,
    isPastingDataset: false,
    isSavingSchema: false,
    isUploading: false,
    parsingOptions: null,
    pasteTextAreaRef: null,
    pastedTextLength: 0,
    preview: null,
    previewLimit: 10,
    previewOffset: 0,
    profile: null,
    schemaDrafts: [],
    selectedFile: null,
    upload: null,
    version: null,
    onApplyBayesianPreset: () => undefined,
    onConfirmParsing: () => undefined,
    onFileChange: () => undefined,
    onLoadDatasetProfile: () => undefined,
    onLoadRowsPreview: () => undefined,
    onParsingOptionsChange: () => undefined,
    onPasteDataset: () => undefined,
    onPastedTextLengthChange: () => undefined,
    onSaveSchema: () => undefined,
    onSchemaDraftChange: () => undefined,
    onUpload: () => undefined,
  };
}

function individualsChartTestResult(): IndividualsChartResult {
  return {
    schema_version: 1,
    summary_type: "individuals_chart",
    method: "i_mr_chart",
    order_source: "canonical_row_order",
    order_tie_breaker: null,
    order_timezone: null,
    missing_policy: "complete_case",
    sigma_estimator: {
      method: "average_moving_range_d2",
      moving_range_length: 2,
      d2: 1.128,
      mrbar: 0.88,
      sigma: 0.7801418439716312,
    },
    control_rules: [
      {
        code: "individuals_chart_i_beyond_3_sigma",
        chart: "individuals",
        definition: "one_point_outside_3_sigma_limits",
        enabled: true,
      },
      {
        code: "individuals_chart_mr_beyond_ucl",
        chart: "moving_range",
        definition: "one_moving_range_above_upper_control_limit",
        enabled: true,
      },
      {
        code: "individuals_chart_i_same_side_centerline",
        chart: "individuals",
        definition: "consecutive_points_on_same_side_of_centerline",
        minimum_length: 9,
        enabled: true,
      },
      {
        code: "individuals_chart_i_trend",
        chart: "individuals",
        definition: "strictly_monotonic_consecutive_points",
        minimum_length: 6,
        enabled: true,
      },
      {
        code: "individuals_chart_i_alternating",
        chart: "individuals",
        definition: "strictly_alternating_consecutive_point_directions",
        minimum_length: 14,
        enabled: true,
      },
      {
        code: "individuals_chart_i_two_of_three_beyond_2_sigma",
        chart: "individuals",
        definition: "two_of_three_consecutive_points_beyond_2_sigma_same_side",
        window_size: 3,
        minimum_count: 2,
        sigma_multiple: 2,
        enabled: true,
      },
      {
        code: "individuals_chart_i_four_of_five_beyond_1_sigma",
        chart: "individuals",
        definition: "four_of_five_consecutive_points_beyond_1_sigma_same_side",
        window_size: 5,
        minimum_count: 4,
        sigma_multiple: 1,
        enabled: true,
      },
      {
        code: "individuals_chart_i_fifteen_within_1_sigma",
        chart: "individuals",
        definition: "fifteen_consecutive_points_within_1_sigma_centerline",
        minimum_length: 15,
        sigma_multiple: 1,
        enabled: true,
      },
      {
        code: "individuals_chart_i_eight_outside_1_sigma",
        chart: "individuals",
        definition: "eight_consecutive_points_outside_1_sigma_centerline",
        minimum_length: 8,
        sigma_multiple: 1,
        enabled: true,
      },
    ],
    warnings: [
      "individuals_chart_uses_canonical_row_order",
      "individuals_chart_control_limits_estimated_from_moving_range",
      "individuals_chart_process_stability_not_proven",
      "individuals_chart_i_limit_signal_detected",
      "individuals_chart_mr_limit_signal_detected",
    ],
    value: {
      column_id: "column-a",
      column_index: 0,
      display_name: "A",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "response",
      unit: null,
    },
    order: null,
    n_total: 6,
    n_used: 6,
    n_excluded_missing_value: 0,
    n_excluded_non_numeric_value: 0,
    n_excluded_missing_order: 0,
    n_excluded_non_numeric_order: 0,
    order_duplicate_count: 0,
    individuals_chart: {
      x_axis: "canonical_row_position",
      center_line: 10.733333333333333,
      lcl: 8.39290780141844,
      ucl: 13.07375886524823,
      point_count: 6,
      points_truncated: false,
      point_limit: 1000,
      points: [
        { position: 1, canonical_position: 1, value: 10, signal_codes: [] },
        { position: 2, canonical_position: 2, value: 10.1, signal_codes: [] },
        { position: 3, canonical_position: 3, value: 10.2, signal_codes: [] },
        { position: 4, canonical_position: 4, value: 10.1, signal_codes: [] },
        { position: 5, canonical_position: 5, value: 10, signal_codes: [] },
        {
          position: 6,
          canonical_position: 6,
          value: 14,
          signal_codes: ["individuals_chart_i_beyond_3_sigma"],
        },
      ],
    },
    moving_range_chart: {
      x_axis: "canonical_row_position",
      center_line: 0.88,
      lcl: 0,
      ucl: 2.87496,
      d3: 0,
      d4: 3.267,
      point_count: 5,
      points_truncated: false,
      point_limit: 1000,
      points: [
        {
          position: 2,
          previous_position: 1,
          canonical_position: 2,
          previous_canonical_position: 1,
          value: 0.1,
          signal_codes: [],
        },
        {
          position: 3,
          previous_position: 2,
          canonical_position: 3,
          previous_canonical_position: 2,
          value: 0.1,
          signal_codes: [],
        },
        {
          position: 4,
          previous_position: 3,
          canonical_position: 4,
          previous_canonical_position: 3,
          value: 0.1,
          signal_codes: [],
        },
        {
          position: 5,
          previous_position: 4,
          canonical_position: 5,
          previous_canonical_position: 4,
          value: 0.1,
          signal_codes: [],
        },
        {
          position: 6,
          previous_position: 5,
          canonical_position: 6,
          previous_canonical_position: 5,
          value: 4,
          signal_codes: ["individuals_chart_mr_beyond_ucl"],
        },
      ],
    },
    signals: [
      {
        signal_id: "i-limit-1",
        code: "individuals_chart_i_beyond_3_sigma",
        severity: "warning",
        chart: "individuals",
        position: 6,
        canonical_position: 6,
        value: 14,
        limit: "upper",
        definition: "one_point_outside_3_sigma_limits",
      },
      {
        signal_id: "mr-limit-1",
        code: "individuals_chart_mr_beyond_ucl",
        severity: "warning",
        chart: "moving_range",
        position: 6,
        previous_position: 5,
        canonical_position: 6,
        previous_canonical_position: 5,
        value: 4,
        limit: "upper",
        definition: "one_moving_range_above_upper_control_limit",
      },
    ],
  };
}

function subgroupChartTestResult(): SubgroupChartResult {
  return {
    schema_version: 1,
    summary_type: "subgroup_chart",
    method: "xbar_r_chart",
    chart_type: "xbar_r",
    order_source: "canonical_subgroup_first_seen",
    missing_policy: "complete_case",
    subgroup_size: 2,
    subgroup_count: 3,
    constants: {
      source: "standard_xbar_r_constants",
      subgroup_size: 2,
      a2: 1.88,
      d3: 0,
      d4: 3.267,
    },
    control_rules: [
      {
        code: "subgroup_chart_xbar_beyond_control_limits",
        chart: "xbar",
        definition: "one_subgroup_mean_outside_xbar_control_limits",
        enabled: true,
      },
      {
        code: "subgroup_chart_r_beyond_control_limits",
        chart: "r",
        definition: "one_subgroup_range_outside_r_control_limits",
        enabled: true,
      },
    ],
    warnings: [
      "subgroup_chart_uses_canonical_subgroup_order",
      "subgroup_chart_control_limits_estimated_from_xbar_r_constants",
      "subgroup_chart_rational_subgroups_not_proven",
      "subgroup_chart_xbar_limit_signal_detected",
    ],
    value: {
      column_id: "column-a",
      column_index: 0,
      display_name: "A",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "response",
      unit: null,
    },
    subgroup: {
      column_id: "column-b",
      column_index: 1,
      display_name: "B",
      data_type: "text",
      measurement_level: "nominal",
      role: "subgroup_id",
      unit: null,
    },
    n_total: 6,
    n_used: 6,
    n_excluded_missing_value: 0,
    n_excluded_non_numeric_value: 0,
    n_excluded_missing_subgroup: 0,
    subgroup_size_distribution: [{ size: 2, count: 3 }],
    xbar_chart: {
      x_axis: "subgroup_position",
      center_line: 11,
      lcl: 7.24,
      ucl: 14.76,
      point_count: 3,
      points_truncated: false,
      point_limit: 1000,
      points: [
        {
          position: 1,
          subgroup_label: "A",
          first_canonical_position: 1,
          last_canonical_position: 2,
          n: 2,
          value: 11,
          mean: 11,
          range: 2,
          signal_codes: [],
        },
        {
          position: 2,
          subgroup_label: "B",
          first_canonical_position: 3,
          last_canonical_position: 4,
          n: 2,
          value: 12,
          mean: 12,
          range: 2,
          signal_codes: [],
        },
        {
          position: 3,
          subgroup_label: "C",
          first_canonical_position: 5,
          last_canonical_position: 6,
          n: 2,
          value: 16,
          mean: 16,
          range: 2,
          signal_codes: ["subgroup_chart_xbar_beyond_control_limits"],
        },
      ],
    },
    r_chart: {
      x_axis: "subgroup_position",
      center_line: 2,
      lcl: 0,
      ucl: 6.534,
      point_count: 3,
      points_truncated: false,
      point_limit: 1000,
      points: [
        {
          position: 1,
          subgroup_label: "A",
          first_canonical_position: 1,
          last_canonical_position: 2,
          n: 2,
          value: 2,
          mean: 11,
          range: 2,
          signal_codes: [],
        },
        {
          position: 2,
          subgroup_label: "B",
          first_canonical_position: 3,
          last_canonical_position: 4,
          n: 2,
          value: 2,
          mean: 12,
          range: 2,
          signal_codes: [],
        },
        {
          position: 3,
          subgroup_label: "C",
          first_canonical_position: 5,
          last_canonical_position: 6,
          n: 2,
          value: 2,
          mean: 16,
          range: 2,
          signal_codes: [],
        },
      ],
    },
    signals: [
      {
        signal_id: "xbar-limit-1",
        code: "subgroup_chart_xbar_beyond_control_limits",
        severity: "warning",
        chart: "xbar",
        position: 3,
        subgroup_label: "C",
        first_canonical_position: 5,
        last_canonical_position: 6,
        value: 16,
        limit: "upper",
        definition: "one_subgroup_mean_outside_xbar_control_limits",
      },
    ],
  };
}

function capabilityTestResult(): CapabilityResult {
  return {
    schema_version: 1,
    summary_type: "capability_analysis",
    method: "normal_capability",
    distribution: "normal",
    missing_policy: "complete_case",
    sigma_estimators: {
      overall: "sample_standard_deviation_ddof_1",
      within: "average_moving_range_d2",
      moving_range_length: 2,
      d2: 1.128,
      mrbar: 1,
    },
    warnings: [
      "capability_normal_model_assumed",
      "capability_control_limits_not_spec_limits",
      "capability_process_stability_not_proven",
      "capability_measurement_system_not_verified",
      "capability_within_sigma_uses_canonical_moving_range",
      "capability_point_estimates_without_ci",
    ],
    value: {
      column_id: "column-a",
      column_index: 0,
      display_name: "A",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "response",
      unit: null,
    },
    spec_limits: {
      lsl: 8,
      usl: 16,
      target: 12,
    },
    n_total: 5,
    n_used: 5,
    n_excluded_missing_value: 0,
    n_excluded_non_numeric_value: 0,
    sample: {
      mean: 12,
      std_overall: 1.5811388300841898,
      std_within: 0.8865248226950355,
      min: 10,
      max: 14,
    },
    capability: {
      within: {
        two_sided: 1.504,
        lower: 1.504,
        upper: 1.504,
        min_side: 1.504,
      },
      overall: {
        two_sided: 0.8432740427115678,
        lower: 0.8432740427115678,
        upper: 0.8432740427115678,
        min_side: 0.8432740427115678,
      },
    },
    observed_nonconformance: {
      below_lsl_count: 0,
      above_usl_count: 0,
      total_count: 0,
      below_lsl_proportion: 0,
      above_usl_proportion: 0,
      total_proportion: 0,
      total_ppm: 0,
    },
    expected_nonconformance_normal: {
      below_lsl_probability: 0.005706018193000826,
      above_usl_probability: 0.005706018193000826,
      total_probability: 0.011412036386001651,
      total_ppm: 11412.036386001651,
    },
    histogram: {
      bin_count: 5,
      bins: [
        {
          lower: 10,
          upper: 10.8,
          midpoint: 10.4,
          count: 1,
          proportion: 0.2,
          density: 0.25,
          normal_density: 0.1519,
        },
        {
          lower: 10.8,
          upper: 11.6,
          midpoint: 11.2,
          count: 1,
          proportion: 0.2,
          density: 0.25,
          normal_density: 0.2218,
        },
        {
          lower: 11.6,
          upper: 12.4,
          midpoint: 12,
          count: 1,
          proportion: 0.2,
          density: 0.25,
          normal_density: 0.2523,
        },
        {
          lower: 12.4,
          upper: 13.2,
          midpoint: 12.8,
          count: 1,
          proportion: 0.2,
          density: 0.25,
          normal_density: 0.2218,
        },
        {
          lower: 13.2,
          upper: 14,
          midpoint: 13.6,
          count: 1,
          proportion: 0.2,
          density: 0.25,
          normal_density: 0.1519,
        },
      ],
    },
  };
}

function gageRrPreflightTestResponse(): GageRrPreflightResponse {
  return {
    schema_version: 1,
    method_id: "quality.gage_rr",
    preflight_type: "balanced_crossed_anova",
    dataset_version_id: "version-1",
    schema_hash: "schema-hash",
    row_count_total: 12,
    summary_type: "gage_rr_preflight",
    method: "balanced_crossed_anova_preflight",
    missing_policy: "complete_case",
    columns: {
      measurement: {
        column_id: "measurement",
        column_index: 0,
        display_name: "Measurement",
        data_type: "decimal",
        measurement_level: "continuous",
        role: "response",
        unit: null,
      },
      part: {
        column_id: "part",
        column_index: 1,
        display_name: "Part",
        data_type: "text",
        measurement_level: "id",
        role: "part_id",
        unit: null,
      },
      operator: {
        column_id: "operator",
        column_index: 2,
        display_name: "Operator",
        data_type: "text",
        measurement_level: "nominal",
        role: "operator_id",
        unit: null,
      },
      replicate: {
        column_id: "replicate",
        column_index: 3,
        display_name: "Replicate",
        data_type: "integer",
        measurement_level: "ordinal",
        role: "replicate_id",
        unit: null,
      },
    },
    sample: {
      n_total: 12,
      n_used: 12,
      n_excluded: 0,
      n_excluded_missing_measurement: 0,
      n_excluded_non_numeric_measurement: 0,
      n_excluded_missing_part: 0,
      n_excluded_missing_operator: 0,
      n_excluded_missing_replicate: 0,
      n_excluded_missing_identifier: 0,
    },
    design: {
      design_type: "crossed",
      balanced: true,
      ready_for_anova: true,
      part_count: 3,
      operator_count: 2,
      replicate_level_count: 2,
      expected_cell_count: 6,
      observed_cell_count: 6,
      missing_cell_count: 0,
      min_replicates_per_cell: 2,
      max_replicates_per_cell: 2,
      expected_replicates_per_cell: 2,
      replicate_set_consistent: true,
      duplicate_replicates_per_cell: 0,
      cell_replicate_count_distribution: [{ replicate_count: 2, cell_count: 6 }],
    },
    issues: [
      {
        code: "gage_rr_preflight_only_no_variance_components",
        severity: "info",
        message:
          "이번 단계는 Gage R&R 계산 전 설계 사전점검만 수행하며 ANOVA table, 분산성분, %GRR, ndc를 계산하지 않습니다.",
        count: null,
      },
    ],
    next_step: "ready_for_balanced_crossed_anova",
  };
}

function gageRrTestResult(): GageRrResult {
  return {
    schema_version: 1,
    summary_type: "gage_rr",
    method: "balanced_crossed_anova",
    missing_policy: "complete_case",
    columns: gageRrPreflightTestResponse().columns,
    sample: {
      n_total: 12,
      n_used: 12,
      n_excluded: 0,
      n_excluded_missing_measurement: 0,
      n_excluded_non_numeric_measurement: 0,
      n_excluded_missing_part: 0,
      n_excluded_missing_operator: 0,
      n_excluded_missing_replicate: 0,
      n_excluded_missing_identifier: 0,
    },
    design: {
      design_type: "crossed",
      balanced: true,
      ready_for_anova: true,
      part_count: 3,
      operator_count: 2,
      replicate_count: 2,
      expected_cell_count: 6,
      observed_cell_count: 6,
      missing_cell_count: 0,
      min_replicates_per_cell: 2,
      max_replicates_per_cell: 2,
      replicate_set_consistent: true,
      duplicate_replicates_per_cell: 0,
    },
    anova_table: [
      {
        source: "part",
        degrees_of_freedom: 2,
        sum_of_squares: 800,
        mean_square: 400,
        f_statistic: 100,
        p_value: 0.009900990099009901,
        denominator: "part_operator",
      },
      {
        source: "operator",
        degrees_of_freedom: 1,
        sum_of_squares: 48,
        mean_square: 48,
        f_statistic: 12,
        p_value: 0.07417990022744853,
        denominator: "part_operator",
      },
      {
        source: "part_operator",
        degrees_of_freedom: 2,
        sum_of_squares: 8,
        mean_square: 4,
        f_statistic: 2,
        p_value: 0.216,
        denominator: "repeatability",
      },
      {
        source: "repeatability",
        degrees_of_freedom: 6,
        sum_of_squares: 12,
        mean_square: 2,
        f_statistic: null,
        p_value: null,
        denominator: null,
      },
      {
        source: "total",
        degrees_of_freedom: 11,
        sum_of_squares: 868,
        mean_square: null,
        f_statistic: null,
        p_value: null,
        denominator: null,
      },
    ],
    variance_components: {
      repeatability: gageRrComponent("repeatability", 2),
      operator: gageRrComponent("operator", 44 / 6),
      part_operator: gageRrComponent("part_operator", 1),
      reproducibility: gageRrComponent("reproducibility", 25 / 3),
      total_gage_rr: gageRrComponent("total_gage_rr", 31 / 3),
      part_to_part: gageRrComponent("part_to_part", 99),
      total_variation: gageRrComponent("total_variation", 328 / 3),
      ndc: 4,
      ndc_formula: "floor(1.41 * part_to_part_sd / total_gage_rr_sd)",
      negative_component_policy: "raw_estimate_reported_final_variance_clamped_to_zero",
      interaction_policy: "preserve_part_operator_interaction_no_pooling",
    },
    warnings: [
      "gage_rr_balanced_crossed_anova_assumed",
      "gage_rr_interaction_not_pooled",
      "gage_rr_independence_not_proven",
      "gage_rr_labels_redacted",
    ],
    notes: [
      "interaction_not_pooled",
      "negative_variance_components_clamped_to_zero",
      "part_operator_replicate_labels_redacted",
    ],
  };
}

function gageRrComponent(component: string, variance: number) {
  const standardDeviation = Math.sqrt(variance);
  return {
    component,
    raw_variance: variance,
    final_variance: variance,
    standard_deviation: standardDeviation,
    study_variation: 6 * standardDeviation,
    clamped_to_zero: false,
    percent_contribution: null,
    percent_study_variation: null,
  };
}

function gageRunChartTestResult(): GageRunChartResult {
  return {
    schema_version: 1,
    summary_type: "gage_run_chart",
    method: "measurement_system_run_chart",
    missing_policy: "complete_case",
    order_source: "numeric_order_column_ascending",
    order_tie_breaker: "canonical_row_position",
    columns: {
      measurement: gageRrPreflightTestResponse().columns.measurement,
      part: gageRrPreflightTestResponse().columns.part,
      operator: gageRrPreflightTestResponse().columns.operator,
      replicate: gageRrPreflightTestResponse().columns.replicate,
      order: {
        column_id: "run",
        column_index: 4,
        display_name: "Run",
        data_type: "integer",
        measurement_level: "ordinal",
        role: "order",
        unit: null,
      },
    },
    sample: {
      n_total: 12,
      n_used: 12,
      n_excluded_missing_measurement: 0,
      n_excluded_non_numeric_measurement: 0,
      n_excluded_missing_part: 0,
      n_excluded_missing_operator: 0,
      n_excluded_missing_replicate: 0,
      n_excluded_missing_identifier: 0,
      n_excluded_missing_order: 0,
      n_excluded_invalid_order: 0,
    },
    design: {
      ready_for_chart: true,
      part_count: 3,
      operator_count: 2,
      replicate_count: 2,
      expected_cell_count: 6,
      observed_cell_count: 6,
      missing_cell_count: 0,
      min_replicates_per_cell: 2,
      max_replicates_per_cell: 2,
      replicate_set_consistent: true,
      duplicate_replicates_per_cell: 0,
    },
    summary: {
      mean: 23,
      minimum: 9,
      maximum: 35,
      range: 26,
    },
    part_summaries: [
      { index: 1, n: 4, mean: 13, minimum: 9, maximum: 17, range: 8 },
      { index: 2, n: 4, mean: 23, minimum: 20, maximum: 26, range: 6 },
      { index: 3, n: 4, mean: 33, minimum: 31, maximum: 35, range: 4 },
    ],
    operator_summaries: [
      { index: 1, n: 6, mean: 21, minimum: 9, maximum: 33, range: 24 },
      { index: 2, n: 6, mean: 25, minimum: 15, maximum: 35, range: 20 },
    ],
    chart: {
      point_count: 12,
      points_truncated: false,
      point_limit: 1000,
      x_axis: "run_order",
      color_role: "operator_index",
      facet_role: "part_index",
      symbol_role: "replicate_index",
      label_policy: "part_operator_replicate_labels_redacted",
      points: [
        {
          position: 1,
          canonical_position: 2,
          value: 11,
          part_index: 1,
          operator_index: 1,
          replicate_index: 2,
        },
        {
          position: 2,
          canonical_position: 1,
          value: 9,
          part_index: 1,
          operator_index: 1,
          replicate_index: 1,
        },
        {
          position: 3,
          canonical_position: 4,
          value: 17,
          part_index: 1,
          operator_index: 2,
          replicate_index: 2,
        },
      ],
    },
    warnings: [
      "gage_run_chart_diagnostic_only",
      "gage_run_chart_requires_gage_design",
      "gage_run_chart_labels_redacted",
      "gage_run_chart_uses_order_column",
    ],
    notes: [
      "diagnostic_chart_not_variance_component_analysis",
      "part_operator_replicate_labels_redacted",
    ],
  };
}

function runChartTestResult(): RunChartResult {
  return {
    schema_version: 1,
    summary_type: "run_chart",
    method: "median_run_chart",
    center_method: "median",
    order_source: "canonical_row_order",
    order_tie_breaker: null,
    order_timezone: null,
    missing_policy: "complete_case",
    tie_policy: "exclude_from_runs",
    trend_rule: {
      code: "run_chart_trend",
      definition: "strictly_monotonic_consecutive_points",
      minimum_length: 6,
    },
    oscillation_rule: {
      code: "run_chart_oscillation",
      definition: "strictly_alternating_consecutive_point_directions",
      minimum_length: 14,
    },
    warnings: [
      "run_chart_not_control_chart",
      "run_chart_trend_rule_defined",
      "run_chart_oscillation_rule_defined",
      "run_chart_runs_test_defined",
      "run_chart_trend_signal_detected",
    ],
    order: null,
    value: {
      column_id: "column-a",
      column_index: 0,
      display_name: "A",
      data_type: "decimal",
      measurement_level: "continuous",
      role: "response",
      unit: null,
    },
    n_total: 8,
    n_used: 8,
    n_excluded_missing_value: 0,
    n_excluded_non_numeric_value: 0,
    n_excluded_missing_order: 0,
    n_excluded_non_numeric_order: 0,
    order_duplicate_count: 0,
    center_line: 3.5,
    runs: {
      run_count: 3,
      n_above: 4,
      n_below: 4,
      n_ties: 0,
      longest_run_length: 4,
      run_count_definition: "consecutive above/below median groups excluding ties",
    },
    runs_test: {
      method: "exact_conditional_run_count_distribution",
      alpha: 0.05,
      available: true,
      observed_run_count: 3,
      n_above: 4,
      n_below: 4,
      n_ties: 0,
      n_non_tie: 8,
      expected_run_count: 5,
      variance: 1.7142857142857142,
      p_value_low: 8 / 70,
      p_value_high: 68 / 70,
      interpretation: "not_extreme",
      skipped_reason: null,
      max_exact_n: 5000,
    },
    signals: [
      {
        signal_id: "trend-1",
        code: "run_chart_trend",
        severity: "warning",
        direction: "increasing",
        length: 6,
        start_position: 1,
        end_position: 6,
        definition: "strictly_monotonic_consecutive_points",
      },
    ],
    chart: {
      x_axis: "canonical_row_position",
      point_count: 8,
      points_truncated: false,
      point_limit: 1000,
      points: [
        {
          position: 1,
          value: 1,
          relative_to_center: "below",
          signal_codes: ["run_chart_trend"],
        },
        {
          position: 2,
          value: 2,
          relative_to_center: "below",
          signal_codes: ["run_chart_trend"],
        },
        {
          position: 3,
          value: 3,
          relative_to_center: "below",
          signal_codes: ["run_chart_trend"],
        },
        {
          position: 4,
          value: 4,
          relative_to_center: "above",
          signal_codes: ["run_chart_trend"],
        },
        {
          position: 5,
          value: 5,
          relative_to_center: "above",
          signal_codes: ["run_chart_trend"],
        },
        {
          position: 6,
          value: 6,
          relative_to_center: "above",
          signal_codes: ["run_chart_trend"],
        },
        { position: 7, value: 4, relative_to_center: "above", signal_codes: [] },
        { position: 8, value: 3, relative_to_center: "below", signal_codes: [] },
      ],
    },
  };
}

function analysisPageTestProps(): ComponentProps<typeof AnalysisPage> {
  return {
    analysisCatalog: null,
    analysisCatalogError: null,
    analysisFilterDrafts: [],
    analysisFilterValidationError: null,
    analysisFilterValidationMessage: null,
    analysisRunError: null,
    analysisResult: null,
    descriptiveColumns: [],
    descriptiveResult: null,
    equalVariancesAlpha: 0.05,
    equalVariancesAnalysisResult: null,
    equalVariancesGroupColumnId: null,
    equalVariancesGroupColumns: [],
    equalVariancesResponseColumnId: null,
    equalVariancesResponseColumns: [],
    equalVariancesResult: null,
    equivalenceTostAlpha: 0.05,
    equivalenceTostAnalysisResult: null,
    equivalenceTostLowerBound: -1,
    equivalenceTostReferenceMean: 0,
    equivalenceTostResponseColumnId: null,
    equivalenceTostResponseColumns: [],
    equivalenceTostResult: null,
    equivalenceTostUpperBound: 1,
    mannWhitneyAlpha: 0.05,
    mannWhitneyAlternative: "two_sided",
    mannWhitneyAnalysisResult: null,
    mannWhitneyGroupColumnId: null,
    mannWhitneyGroupColumns: [],
    mannWhitneyMethod: "auto",
    mannWhitneyResponseColumnId: null,
    mannWhitneyResponseColumns: [],
    mannWhitneyResult: null,
    twoSampleTAlpha: 0.05,
    twoSampleTAlternative: "two_sided",
    twoSampleTAnalysisResult: null,
    twoSampleTConfidenceLevel: 0.95,
    twoSampleTGroupColumnId: null,
    twoSampleTGroupColumns: [],
    twoSampleTResponseColumnId: null,
    twoSampleTResponseColumns: [],
    twoSampleTResult: null,
    twoSampleTVarianceAssumption: "welch",
    chiSquareAssociationAlpha: 0.05,
    chiSquareAssociationAnalysisResult: null,
    chiSquareAssociationColumnColumnId: null,
    chiSquareAssociationColumnColumns: [],
    chiSquareAssociationResult: null,
    chiSquareAssociationRowColumnId: null,
    chiSquareAssociationRowColumns: [],
    graphicalSummaryAnalysisResult: null,
    graphicalSummaryColumns: [],
    graphicalSummaryResult: null,
    isRunningAnalysis: false,
    kruskalWallisAlpha: 0.05,
    kruskalWallisAnalysisResult: null,
    kruskalWallisGroupColumnId: null,
    kruskalWallisGroupColumns: [],
    kruskalWallisResponseColumnId: null,
    kruskalWallisResponseColumns: [],
    kruskalWallisResult: null,
    normalityAlpha: 0.05,
    normalityAnalysisResult: null,
    normalityColumns: [],
    normalityResult: null,
    oneProportionAlpha: 0.05,
    oneProportionAlternative: "two_sided",
    oneProportionAnalysisResult: null,
    oneProportionCiMethod: "wilson",
    oneProportionConfidenceLevel: 0.95,
    oneProportionEventLevel: "",
    oneProportionNullProportion: 0.5,
    oneProportionResponseColumnId: null,
    oneProportionResponseColumns: [],
    oneProportionResult: null,
    oneWayAnovaAlpha: 0.05,
    oneWayAnovaAnalysisResult: null,
    oneWayAnovaConfidenceLevel: 0.95,
    oneWayAnovaGroupColumnId: null,
    oneWayAnovaGroupColumns: [],
    oneWayAnovaResponseColumnId: null,
    oneWayAnovaResponseColumns: [],
    oneWayAnovaResult: null,
    twoProportionAlpha: 0.05,
    twoProportionAlternative: "two_sided",
    twoProportionAnalysisResult: null,
    twoProportionConfidenceLevel: 0.95,
    twoProportionEventLevel: "",
    twoProportionGroupColumnId: null,
    twoProportionGroupColumns: [],
    twoProportionResponseColumnId: null,
    twoProportionResponseColumns: [],
    twoProportionResult: null,
    oneSampleTAlpha: 0.05,
    oneSampleTAlternative: "two_sided",
    oneSampleTAnalysisResult: null,
    oneSampleTConfidenceLevel: 0.95,
    oneSampleTNullMean: 0,
    oneSampleTResponseColumnId: null,
    oneSampleTResponseColumns: [],
    oneSampleTResult: null,
    oneSampleWilcoxonAlpha: 0.05,
    oneSampleWilcoxonAlternative: "two_sided",
    oneSampleWilcoxonAnalysisResult: null,
    oneSampleWilcoxonMethod: "auto",
    oneSampleWilcoxonNullLocation: 0,
    oneSampleWilcoxonResponseColumnId: null,
    oneSampleWilcoxonResponseColumns: [],
    oneSampleWilcoxonResult: null,
    oneSampleWilcoxonZeroMethod: "wilcox",
    pairedTAfterColumnId: null,
    pairedTAfterColumns: [],
    pairedTAlpha: 0.05,
    pairedTAlternative: "two_sided",
    pairedTAnalysisResult: null,
    pairedTBeforeColumnId: null,
    pairedTBeforeColumns: [],
    pairedTConfidenceLevel: 0.95,
    pairedTNullDifference: 0,
    pairedTResult: null,
    pearsonAlpha: 0.05,
    pearsonAnalysisResult: null,
    pearsonConfidenceLevel: 0.95,
    pearsonResult: null,
    pearsonXColumnId: null,
    pearsonXColumns: [],
    pearsonYColumnId: null,
    pearsonYColumns: [],
    xyCorrelationAlpha: 0.05,
    xyCorrelationAnalysisResult: null,
    xyCorrelationConfidenceLevel: 0.95,
    xyCorrelationResult: null,
    xyCorrelationXColumnIds: [],
    xyCorrelationXColumns: [],
    xyCorrelationYColumnIds: [],
    xyCorrelationYColumns: [],
    profile: null,
    selectedDescriptiveColumnIds: [],
    selectedGraphicalSummaryColumnIds: [],
    selectedNormalityColumnIds: [],
    selectedMethod: null,
    selectedMethods: [],
    selectedModuleId: "exploration",
    version: null,
    onAnalysisFilterDraftsChange: () => undefined,
    onRunChiSquareAssociationAnalysis: () => undefined,
    onRunDescriptiveAnalysis: () => undefined,
    onRunEqualVariancesAnalysis: () => undefined,
    onRunEquivalenceTostAnalysis: () => undefined,
    onRunGraphicalSummaryAnalysis: () => undefined,
    onRunKruskalWallisAnalysis: () => undefined,
    onRunMannWhitneyAnalysis: () => undefined,
    onRunNormalityAnalysis: () => undefined,
    onRunOneProportionAnalysis: () => undefined,
    onRunOneSampleTAnalysis: () => undefined,
    onRunOneSampleWilcoxonAnalysis: () => undefined,
    onRunPairedTAnalysis: () => undefined,
    onRunTwoSampleTAnalysis: () => undefined,
    onSelectMethod: () => undefined,
    onChiSquareAssociationAlphaChange: () => undefined,
    onChiSquareAssociationColumnColumnChange: () => undefined,
    onChiSquareAssociationRowColumnChange: () => undefined,
    onEqualVariancesAlphaChange: () => undefined,
    onEqualVariancesGroupColumnChange: () => undefined,
    onEqualVariancesResponseColumnChange: () => undefined,
    onEquivalenceTostAlphaChange: () => undefined,
    onEquivalenceTostLowerBoundChange: () => undefined,
    onEquivalenceTostReferenceMeanChange: () => undefined,
    onEquivalenceTostResponseColumnChange: () => undefined,
    onEquivalenceTostUpperBoundChange: () => undefined,
    onKruskalWallisAlphaChange: () => undefined,
    onKruskalWallisGroupColumnChange: () => undefined,
    onKruskalWallisResponseColumnChange: () => undefined,
    onMannWhitneyAlphaChange: () => undefined,
    onMannWhitneyAlternativeChange: () => undefined,
    onMannWhitneyGroupColumnChange: () => undefined,
    onMannWhitneyMethodChange: () => undefined,
    onMannWhitneyResponseColumnChange: () => undefined,
    onNormalityAlphaChange: () => undefined,
    onOneProportionAlphaChange: () => undefined,
    onOneProportionAlternativeChange: () => undefined,
    onOneProportionCiMethodChange: () => undefined,
    onOneProportionConfidenceLevelChange: () => undefined,
    onOneProportionEventLevelChange: () => undefined,
    onOneProportionNullProportionChange: () => undefined,
    onOneProportionResponseColumnChange: () => undefined,
    onOneWayAnovaAlphaChange: () => undefined,
    onOneWayAnovaConfidenceLevelChange: () => undefined,
    onOneWayAnovaGroupColumnChange: () => undefined,
    onOneWayAnovaResponseColumnChange: () => undefined,
    onRunOneWayAnovaAnalysis: () => undefined,
    onTwoProportionAlphaChange: () => undefined,
    onTwoProportionAlternativeChange: () => undefined,
    onTwoProportionConfidenceLevelChange: () => undefined,
    onTwoProportionEventLevelChange: () => undefined,
    onTwoProportionGroupColumnChange: () => undefined,
    onTwoProportionResponseColumnChange: () => undefined,
    onRunTwoProportionAnalysis: () => undefined,
    onOneSampleTAlphaChange: () => undefined,
    onOneSampleTAlternativeChange: () => undefined,
    onOneSampleTConfidenceLevelChange: () => undefined,
    onOneSampleTNullMeanChange: () => undefined,
    onOneSampleTResponseColumnChange: () => undefined,
    onOneSampleWilcoxonAlphaChange: () => undefined,
    onOneSampleWilcoxonAlternativeChange: () => undefined,
    onOneSampleWilcoxonMethodChange: () => undefined,
    onOneSampleWilcoxonNullLocationChange: () => undefined,
    onOneSampleWilcoxonResponseColumnChange: () => undefined,
    onOneSampleWilcoxonZeroMethodChange: () => undefined,
    onPairedTAfterColumnChange: () => undefined,
    onPairedTAlphaChange: () => undefined,
    onPairedTAlternativeChange: () => undefined,
    onPairedTBeforeColumnChange: () => undefined,
    onPairedTConfidenceLevelChange: () => undefined,
    onPairedTNullDifferenceChange: () => undefined,
    onPearsonAlphaChange: () => undefined,
    onPearsonConfidenceLevelChange: () => undefined,
    onPearsonXColumnChange: () => undefined,
    onPearsonYColumnChange: () => undefined,
    onRunPearsonAnalysis: () => undefined,
    onRunXyCorrelationAnalysis: () => undefined,
    onXyCorrelationAlphaChange: () => undefined,
    onXyCorrelationConfidenceLevelChange: () => undefined,
    onTwoSampleTAlphaChange: () => undefined,
    onTwoSampleTAlternativeChange: () => undefined,
    onTwoSampleTConfidenceLevelChange: () => undefined,
    onTwoSampleTGroupColumnChange: () => undefined,
    onTwoSampleTResponseColumnChange: () => undefined,
    onTwoSampleTVarianceAssumptionChange: () => undefined,
    onToggleDescriptiveColumn: () => undefined,
    onToggleGraphicalSummaryColumn: () => undefined,
    onToggleNormalityColumn: () => undefined,
    onToggleXyCorrelationXColumn: () => undefined,
    onToggleXyCorrelationYColumn: () => undefined,
  };
}

function kruskalWallisTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "kruskalWallisAlpha"
  | "kruskalWallisAnalysisResult"
  | "kruskalWallisGroupColumnId"
  | "kruskalWallisGroupColumns"
  | "kruskalWallisResponseColumnId"
  | "kruskalWallisResponseColumns"
  | "kruskalWallisResult"
  | "onKruskalWallisAlphaChange"
  | "onKruskalWallisGroupColumnChange"
  | "onKruskalWallisResponseColumnChange"
  | "onRunKruskalWallisAnalysis"
> {
  return {
    kruskalWallisAlpha: 0.05,
    kruskalWallisAnalysisResult: null,
    kruskalWallisGroupColumnId: "column-b",
    kruskalWallisGroupColumns: [columns[1]],
    kruskalWallisResponseColumnId: "column-a",
    kruskalWallisResponseColumns: [columns[0]],
    kruskalWallisResult: null,
    onKruskalWallisAlphaChange: () => undefined,
    onKruskalWallisGroupColumnChange: () => undefined,
    onKruskalWallisResponseColumnChange: () => undefined,
    onRunKruskalWallisAnalysis: () => undefined,
  };
}

function oneWayAnovaTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "oneWayAnovaAlpha"
  | "oneWayAnovaAnalysisResult"
  | "oneWayAnovaConfidenceLevel"
  | "oneWayAnovaGroupColumnId"
  | "oneWayAnovaGroupColumns"
  | "oneWayAnovaResponseColumnId"
  | "oneWayAnovaResponseColumns"
  | "oneWayAnovaResult"
  | "onOneWayAnovaAlphaChange"
  | "onOneWayAnovaConfidenceLevelChange"
  | "onOneWayAnovaGroupColumnChange"
  | "onOneWayAnovaResponseColumnChange"
  | "onRunOneWayAnovaAnalysis"
> {
  return {
    oneWayAnovaAlpha: 0.05,
    oneWayAnovaAnalysisResult: null,
    oneWayAnovaConfidenceLevel: 0.95,
    oneWayAnovaGroupColumnId: "column-b",
    oneWayAnovaGroupColumns: [columns[1]],
    oneWayAnovaResponseColumnId: "column-a",
    oneWayAnovaResponseColumns: [columns[0]],
    oneWayAnovaResult: null,
    onOneWayAnovaAlphaChange: () => undefined,
    onOneWayAnovaConfidenceLevelChange: () => undefined,
    onOneWayAnovaGroupColumnChange: () => undefined,
    onOneWayAnovaResponseColumnChange: () => undefined,
    onRunOneWayAnovaAnalysis: () => undefined,
  };
}

function oneProportionTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "oneProportionAlpha"
  | "oneProportionAlternative"
  | "oneProportionAnalysisResult"
  | "oneProportionCiMethod"
  | "oneProportionConfidenceLevel"
  | "oneProportionEventLevel"
  | "oneProportionNullProportion"
  | "oneProportionResponseColumnId"
  | "oneProportionResponseColumns"
  | "oneProportionResult"
  | "onOneProportionAlphaChange"
  | "onOneProportionAlternativeChange"
  | "onOneProportionCiMethodChange"
  | "onOneProportionConfidenceLevelChange"
  | "onOneProportionEventLevelChange"
  | "onOneProportionNullProportionChange"
  | "onOneProportionResponseColumnChange"
  | "onRunOneProportionAnalysis"
> {
  return {
    oneProportionAlpha: 0.05,
    oneProportionAlternative: "two_sided",
    oneProportionAnalysisResult: null,
    oneProportionCiMethod: "wilson",
    oneProportionConfidenceLevel: 0.95,
    oneProportionEventLevel: "yes",
    oneProportionNullProportion: 0.5,
    oneProportionResponseColumnId: "column-b",
    oneProportionResponseColumns: [columns[1]],
    oneProportionResult: null,
    onOneProportionAlphaChange: () => undefined,
    onOneProportionAlternativeChange: () => undefined,
    onOneProportionCiMethodChange: () => undefined,
    onOneProportionConfidenceLevelChange: () => undefined,
    onOneProportionEventLevelChange: () => undefined,
    onOneProportionNullProportionChange: () => undefined,
    onOneProportionResponseColumnChange: () => undefined,
    onRunOneProportionAnalysis: () => undefined,
  };
}

function twoProportionTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "twoProportionAlpha"
  | "twoProportionAlternative"
  | "twoProportionAnalysisResult"
  | "twoProportionConfidenceLevel"
  | "twoProportionEventLevel"
  | "twoProportionGroupColumnId"
  | "twoProportionGroupColumns"
  | "twoProportionResponseColumnId"
  | "twoProportionResponseColumns"
  | "twoProportionResult"
  | "onTwoProportionAlphaChange"
  | "onTwoProportionAlternativeChange"
  | "onTwoProportionConfidenceLevelChange"
  | "onTwoProportionEventLevelChange"
  | "onTwoProportionGroupColumnChange"
  | "onTwoProportionResponseColumnChange"
  | "onRunTwoProportionAnalysis"
> {
  return {
    twoProportionAlpha: 0.05,
    twoProportionAlternative: "two_sided",
    twoProportionAnalysisResult: null,
    twoProportionConfidenceLevel: 0.95,
    twoProportionEventLevel: "yes",
    twoProportionGroupColumnId: "column-b",
    twoProportionGroupColumns: [columns[1]],
    twoProportionResponseColumnId: "column-a",
    twoProportionResponseColumns: [columns[0]],
    twoProportionResult: null,
    onTwoProportionAlphaChange: () => undefined,
    onTwoProportionAlternativeChange: () => undefined,
    onTwoProportionConfidenceLevelChange: () => undefined,
    onTwoProportionEventLevelChange: () => undefined,
    onTwoProportionGroupColumnChange: () => undefined,
    onTwoProportionResponseColumnChange: () => undefined,
    onRunTwoProportionAnalysis: () => undefined,
  };
}

function chiSquareAssociationTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "chiSquareAssociationAlpha"
  | "chiSquareAssociationAnalysisResult"
  | "chiSquareAssociationColumnColumnId"
  | "chiSquareAssociationColumnColumns"
  | "chiSquareAssociationResult"
  | "chiSquareAssociationRowColumnId"
  | "chiSquareAssociationRowColumns"
  | "onChiSquareAssociationAlphaChange"
  | "onChiSquareAssociationColumnColumnChange"
  | "onChiSquareAssociationRowColumnChange"
  | "onRunChiSquareAssociationAnalysis"
> {
  return {
    chiSquareAssociationAlpha: 0.05,
    chiSquareAssociationAnalysisResult: null,
    chiSquareAssociationColumnColumnId: "column-b",
    chiSquareAssociationColumnColumns: [columns[1]],
    chiSquareAssociationResult: null,
    chiSquareAssociationRowColumnId: "column-a",
    chiSquareAssociationRowColumns: [columns[0], columns[1]],
    onChiSquareAssociationAlphaChange: () => undefined,
    onChiSquareAssociationColumnColumnChange: () => undefined,
    onChiSquareAssociationRowColumnChange: () => undefined,
    onRunChiSquareAssociationAnalysis: () => undefined,
  };
}

function equivalenceTostTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "equivalenceTostAlpha"
  | "equivalenceTostAnalysisResult"
  | "equivalenceTostLowerBound"
  | "equivalenceTostReferenceMean"
  | "equivalenceTostResponseColumnId"
  | "equivalenceTostResponseColumns"
  | "equivalenceTostResult"
  | "equivalenceTostUpperBound"
  | "onEquivalenceTostAlphaChange"
  | "onEquivalenceTostLowerBoundChange"
  | "onEquivalenceTostReferenceMeanChange"
  | "onEquivalenceTostResponseColumnChange"
  | "onEquivalenceTostUpperBoundChange"
  | "onRunEquivalenceTostAnalysis"
> {
  return {
    equivalenceTostAlpha: 0.05,
    equivalenceTostAnalysisResult: null,
    equivalenceTostLowerBound: -1,
    equivalenceTostReferenceMean: 0,
    equivalenceTostResponseColumnId: "column-a",
    equivalenceTostResponseColumns: [columns[0]],
    equivalenceTostResult: null,
    equivalenceTostUpperBound: 1,
    onEquivalenceTostAlphaChange: () => undefined,
    onEquivalenceTostLowerBoundChange: () => undefined,
    onEquivalenceTostReferenceMeanChange: () => undefined,
    onEquivalenceTostResponseColumnChange: () => undefined,
    onEquivalenceTostUpperBoundChange: () => undefined,
    onRunEquivalenceTostAnalysis: () => undefined,
  };
}

function mannWhitneyTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "mannWhitneyAlpha"
  | "mannWhitneyAlternative"
  | "mannWhitneyAnalysisResult"
  | "mannWhitneyGroupColumnId"
  | "mannWhitneyGroupColumns"
  | "mannWhitneyMethod"
  | "mannWhitneyResponseColumnId"
  | "mannWhitneyResponseColumns"
  | "mannWhitneyResult"
  | "onMannWhitneyAlphaChange"
  | "onMannWhitneyAlternativeChange"
  | "onMannWhitneyGroupColumnChange"
  | "onMannWhitneyMethodChange"
  | "onMannWhitneyResponseColumnChange"
  | "onRunMannWhitneyAnalysis"
> {
  return {
    mannWhitneyAlpha: 0.05,
    mannWhitneyAlternative: "two_sided",
    mannWhitneyAnalysisResult: null,
    mannWhitneyGroupColumnId: "column-b",
    mannWhitneyGroupColumns: [columns[1]],
    mannWhitneyMethod: "auto",
    mannWhitneyResponseColumnId: "column-a",
    mannWhitneyResponseColumns: [columns[0]],
    mannWhitneyResult: null,
    onMannWhitneyAlphaChange: () => undefined,
    onMannWhitneyAlternativeChange: () => undefined,
    onMannWhitneyGroupColumnChange: () => undefined,
    onMannWhitneyMethodChange: () => undefined,
    onMannWhitneyResponseColumnChange: () => undefined,
    onRunMannWhitneyAnalysis: () => undefined,
  };
}

function pairedTTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "pairedTAfterColumnId"
  | "pairedTAfterColumns"
  | "pairedTAlpha"
  | "pairedTAlternative"
  | "pairedTAnalysisResult"
  | "pairedTBeforeColumnId"
  | "pairedTBeforeColumns"
  | "pairedTConfidenceLevel"
  | "pairedTNullDifference"
  | "pairedTResult"
  | "onPairedTAfterColumnChange"
  | "onPairedTAlphaChange"
  | "onPairedTAlternativeChange"
  | "onPairedTBeforeColumnChange"
  | "onPairedTConfidenceLevelChange"
  | "onPairedTNullDifferenceChange"
  | "onRunPairedTAnalysis"
> {
  return {
    pairedTAfterColumnId: "column-b",
    pairedTAfterColumns: [columns[1]],
    pairedTAlpha: 0.05,
    pairedTAlternative: "two_sided",
    pairedTAnalysisResult: null,
    pairedTBeforeColumnId: "column-a",
    pairedTBeforeColumns: [columns[0]],
    pairedTConfidenceLevel: 0.95,
    pairedTNullDifference: 0,
    pairedTResult: null,
    onPairedTAfterColumnChange: () => undefined,
    onPairedTAlphaChange: () => undefined,
    onPairedTAlternativeChange: () => undefined,
    onPairedTBeforeColumnChange: () => undefined,
    onPairedTConfidenceLevelChange: () => undefined,
    onPairedTNullDifferenceChange: () => undefined,
    onRunPairedTAnalysis: () => undefined,
  };
}

function pearsonTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "pearsonAlpha"
  | "pearsonAnalysisResult"
  | "pearsonConfidenceLevel"
  | "pearsonResult"
  | "pearsonXColumnId"
  | "pearsonXColumns"
  | "pearsonYColumnId"
  | "pearsonYColumns"
  | "onPearsonAlphaChange"
  | "onPearsonConfidenceLevelChange"
  | "onPearsonXColumnChange"
  | "onPearsonYColumnChange"
  | "onRunPearsonAnalysis"
> {
  const numericColumns = columns.filter(
    (column) => column.data_type === "decimal" || column.data_type === "integer",
  );
  return {
    pearsonAlpha: 0.05,
    pearsonAnalysisResult: null,
    pearsonConfidenceLevel: 0.95,
    pearsonResult: null,
    pearsonXColumnId: numericColumns[0]?.column_id ?? null,
    pearsonXColumns: numericColumns,
    pearsonYColumnId: numericColumns[1]?.column_id ?? null,
    pearsonYColumns: numericColumns,
    onPearsonAlphaChange: () => undefined,
    onPearsonConfidenceLevelChange: () => undefined,
    onPearsonXColumnChange: () => undefined,
    onPearsonYColumnChange: () => undefined,
    onRunPearsonAnalysis: () => undefined,
  };
}

function oneSampleWilcoxonTestProps(
  columns: DatasetColumnResponse[],
): Pick<
  ComponentProps<typeof AnalysisPage>,
  | "oneSampleWilcoxonAlpha"
  | "oneSampleWilcoxonAlternative"
  | "oneSampleWilcoxonAnalysisResult"
  | "oneSampleWilcoxonMethod"
  | "oneSampleWilcoxonNullLocation"
  | "oneSampleWilcoxonResponseColumnId"
  | "oneSampleWilcoxonResponseColumns"
  | "oneSampleWilcoxonResult"
  | "oneSampleWilcoxonZeroMethod"
  | "onOneSampleWilcoxonAlphaChange"
  | "onOneSampleWilcoxonAlternativeChange"
  | "onOneSampleWilcoxonMethodChange"
  | "onOneSampleWilcoxonNullLocationChange"
  | "onOneSampleWilcoxonResponseColumnChange"
  | "onOneSampleWilcoxonZeroMethodChange"
  | "onRunOneSampleWilcoxonAnalysis"
> {
  return {
    oneSampleWilcoxonAlpha: 0.05,
    oneSampleWilcoxonAlternative: "two_sided",
    oneSampleWilcoxonAnalysisResult: null,
    oneSampleWilcoxonMethod: "auto",
    oneSampleWilcoxonNullLocation: 0,
    oneSampleWilcoxonResponseColumnId: "column-a",
    oneSampleWilcoxonResponseColumns: [columns[0]],
    oneSampleWilcoxonResult: null,
    oneSampleWilcoxonZeroMethod: "wilcox",
    onOneSampleWilcoxonAlphaChange: () => undefined,
    onOneSampleWilcoxonAlternativeChange: () => undefined,
    onOneSampleWilcoxonMethodChange: () => undefined,
    onOneSampleWilcoxonNullLocationChange: () => undefined,
    onOneSampleWilcoxonResponseColumnChange: () => undefined,
    onOneSampleWilcoxonZeroMethodChange: () => undefined,
    onRunOneSampleWilcoxonAnalysis: () => undefined,
  };
}
