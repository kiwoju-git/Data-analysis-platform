import type { ComponentProps } from "react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { AnalysisPage } from "./AnalysisPage";
import { AnalysisExportDeletionConfirmation } from "./AnalysisResultExportPanel";
import { AnalysisRunDeletionConfirmation } from "./AnalysisHistoryPanel";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import { DatasetPreparationPage } from "./DatasetPreparationPage";
import { PastePreviewGrid } from "./PastePreviewGrid";
import {
  BayesianOptimizationPanel,
  BayesianStudyCloseConfirmation,
  BayesianStudyDeletionConfirmation,
  BayesianSuccessorSeedNotice,
  BayesianTrialTransitionConfirmation,
} from "./BayesianOptimizationPanel";
import { FactorialDesignPreview } from "./FactorialDesignPanel";
import { ResponseOptimizerPanel } from "./ResponseOptimizerPanel";
import { RegressionPredictionWorkspace } from "./RegressionPredictionWorkspace";
import { ResponseOptimizerWorkspace } from "./ResponseOptimizerWorkspace";
import {
  restoredOptimizationMatchesSelection,
  restoredPredictionForSelection,
} from "./dedicatedResultRestore";
import {
  ResponseSurfacePanel,
  ResponseSurfaceResponseEntry,
} from "./ResponseSurfacePanel";
import {
  deleteAnalysisResultExport,
  deleteStoredAnalysisRun,
  fetchAnalysisResultExportDeletionPreflight,
  fetchAnalysisResultExports,
  fetchAnalysisRunComparison,
  fetchAnalysisRunDeletionPreflight,
  fetchAnalysisRunResult,
  fetchAnalysisRuns,
} from "./api";
import { andersonPValueLabel } from "./normalityDisplay";
import type {
  AnalysisMethodListResponse,
  AnalysisRunComparisonResponse,
  AnalysisRunDeletionPreflightResponse,
  AnalysisResultExportListResponse,
  AnalysisResultExportDeletionPreflightResponse,
  AnalysisResultCsvExportResponse,
  AnalysisResultEnvelope,
  AnalysisResultHtmlReportResponse,
  AnalysisResultJsonExportResponse,
  AnalysisRunListResponse,
  BayesianRecommendationResponse,
  BayesianStudyDeletionPreflightResponse,
  BayesianTrialResponse,
  AttributeControlChartResult,
  AttributeControlLimitSetResponse,
  CapabilityResult,
  ChiSquareAssociationResult,
  DatasetColumnResponse,
  DatasetRowsPreviewResponse,
  DatasetUploadResponse,
  DatasetVersionCatalogResponse,
  DatasetVersionResponse,
  DoeDesignResponsesResponse,
  DoeFactorialAnalysisResponse,
  DoeResponseSurfaceAnalysisResponse,
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
  RegressionPredictionCsvExportResponse,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
  ResponseOptimizerResponse,
  ResponseSurfaceDesignResponse,
  RunChartResult,
  SubgroupChartResult,
  XyCorrelationResult,
} from "./api";
import { apiRoutes } from "./api/routes";
import { AppChrome } from "./AppChrome";
import { HelpCenterPage } from "./HelpCenterPage";
import { MethodHelpDrawer } from "./MethodHelpDrawer";
import { ManageAssetsPage } from "./ManageAssetsPage";
import { RoleDictionary } from "./RoleDictionary";
import { ReportCenterPage } from "./ReportCenterPage";
import {
  reportCreationCapabilities,
  reportWorkflowCapabilities,
} from "./reportCenterCapabilities";
import {
  bayesianRecommendationBudgetBlocker,
  bayesianRecommendationStatus,
  bayesianStudyCloseBlocker,
  buildBayesianStudyRequest,
  minimumBayesianInitialDesignSize,
} from "./bayesianStudyDraft";
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
import { parsePastedTablePreview } from "./pastedTablePreview";
import {
  groupPredictionPreflightIssues,
  predictionRangeRows,
} from "./predictionPreflightPresentation";
import { paddedNumericRange, scaleChartValue } from "./charts/chartScale";

vi.mock("./lazyAnalysisPanels", async () => {
  const [regression, quality, doe] = await Promise.all([
    import("./RegressionAnalysisPanels"),
    import("./QualityAnalysisPanels"),
    import("./DoeAnalysisPanels"),
  ]);
  return { ...regression, ...quality, ...doe };
});

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

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
    expect(parseAppRoute("/reports/", "")).toEqual({ page: "reports" });
    expect(parseAppRoute("/help", "")).toEqual({ page: "help" });
    expect(parseAppRoute("/manage", "")).toEqual({ page: "manage" });
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

  it("defines guidance for all 30 documented six-module methods", () => {
    expect(analysisMethodGuidanceIds).toHaveLength(30);
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
    expect(getAnalysisMethodGuidance("doe.response_surface").plainLanguage).toContain(
      "full quadratic OLS",
    );
    expect(getAnalysisMethodGuidance("regression.predict").plainLanguage).toContain(
      "Predict 전용 워크플로",
    );
    expect(getAnalysisMethodGuidance("regression.predict").plainLanguage).toContain(
      "회귀모형 적합 화면에서도 같은 dedicated API",
    );
    expect(getAnalysisMethodGuidance("doe.bayesian_optimization").plainLanguage).toContain(
      "pending/completed/abandoned trial",
    );
    expect(getAnalysisMethodGuidance("doe.bayesian_optimization").plainLanguage).toContain(
      "추천은 관측값이나 전역 최적 보장이 아닙니다",
    );
  });

  it("groups repeated prediction mappings and keeps extrapolation ranges explicit", () => {
    const mappingIssues = Array.from({ length: 6 }, (_, index) => ({
      code: "prediction_column_matched_by_display_name",
      severity: "warning" as const,
      message: `predictor ${index + 1}`,
      source_column_id: `source-${index + 1}`,
      target_column_id: `target-${index + 1}`,
      display_name: `X${index + 1}`,
      count: null,
    }));
    const grouped = groupPredictionPreflightIssues([
      ...mappingIssues,
      {
        code: "prediction_schema_hash_mismatch",
        severity: "warning",
        message: "different target",
        source_column_id: null,
        target_column_id: null,
        display_name: null,
        count: null,
      },
    ]);
    const ranges = predictionRangeRows([
      {
        source_column_id: "source-1",
        target_column_id: "target-1",
        display_name: "temperature_c",
        n_valid: 48,
        n_missing: 0,
        n_non_numeric: 0,
        n_below_training_range: 0,
        n_above_training_range: 1,
        training_min: 60,
        training_max: 90,
      },
    ]);

    expect(grouped.mappingIssues).toHaveLength(6);
    expect(grouped.otherIssues).toHaveLength(0);
    expect(ranges).toHaveLength(1);
    expect(ranges[0]).toMatchObject({ training_min: 60, training_max: 90 });
  });

  it("uses finite padded chart domains and stable scale coordinates", () => {
    const range = paddedNumericRange([10, 10, Number.NaN]);
    expect(range.min).toBeLessThan(10);
    expect(range.max).toBeGreaterThan(10);
    expect(scaleChartValue(10, range, 0, 100)).toBeCloseTo(50);
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
        factorialAnalysis={factorialAnalysisTestResponse()}
        factorialDesign={factorialDesignTestResponse()}
        factorialDesignResponses={factorialDesignResponsesTestResponse()}
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
    expect(html).toContain("효과·OLS/ANOVA 지원");
    expect(html).toContain("Factorial 분석 결과");
    expect(html).toContain("절대 효과 순위");
    expect(html).toContain("ANOVA source");
    expect(html).toContain("factorial-analysis-id");
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
    expect(html).toContain("분석 도움말");
    expect(html).toContain("계산 코드, 기준 데이터, 수치 검증 테스트");
  });

  it("moves global beginner guidance to Help Center and keeps readable preflight copy", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const helpHtml = renderToString(
      <HelpCenterPage catalog={catalog} onOpenAnalysis={() => undefined} />,
    );

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
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

    expect(html).not.toContain("무엇을 알고 싶나요?");
    expect(html).not.toContain("역할 설명");
    expect(html).toContain("분석 선택이 어렵나요? 도움말에서 질문으로 찾기");
    expect(html).toContain("분석 도움말");
    expect(helpHtml).toContain("무엇을 알고 싶나요?");
    expect(helpHtml).toContain("한 컬럼의 분포와 이상치를 보고 싶다");
    expect(helpHtml).toContain("eda.graphical_summary");
    expect(helpHtml).toContain("변수 역할 사전");
    expect(helpHtml).toContain("Response / 반응값 / Y");
    expect(html).not.toContain("사전점검 해설");
    expect(html).not.toContain("독립성은 데이터만으로 자동 검증할 수 없습니다.");
    expect(html).not.toContain("p-value는 차이가 있는지의 근거");
  });

  it("renders accessible selected-method context help without hiding required caveats", () => {
    const method = analysisTestCatalog().methods[0];
    const html = renderToString(
      <MethodHelpDrawer
        method={method}
        open
        profile={null}
        trigger={null}
        version={datasetVersionTestResponse()}
        onClose={() => undefined}
      />,
    );

    expect(html).toContain('role="dialog"');
    expect(html).toContain('id="method-help-drawer"');
    expect(html).toContain("쉽게 말하면");
    expect(html).toContain("필수 역할");
    expect(html).toContain("사용하면 안 되는 경우");
    expect(html).toContain("사전점검과 결과 해석");
    expect(html).toContain("현재 데이터 상태 (구조 수준)");
    expect(html).toContain("실제 usable row와 제외 행");
    expect(html).toContain("결과에서 먼저 볼 값");
    expect(html).toContain("인과관계나 실무적 중요성을 단정하지 마세요");
  });

  it("keeps Report Center capabilities explicit for generic and dedicated workflows", () => {
    expect(reportCreationCapabilities("eda.descriptive")).toEqual({
      json: true,
      csv: true,
      html: true,
    });
    expect(reportCreationCapabilities("regression.predict")).toEqual({
      json: false,
      csv: false,
      html: false,
    });
    expect(reportWorkflowCapabilities.find((item) => item.methodId === "regression.predict"))
      .toMatchObject({ csv: "전용 화면에서 full prediction CSV 지원", html: "현재 지원되지 않음" });
    const html = renderToString(
      <ReportCenterPage catalog={analysisTestCatalog()} currentDatasetVersionId={null} />,
    );
    expect(html).toContain("리포트 센터");
    expect(html).toContain("P0 capability matrix");
    expect(html).toContain("현재 지원되지 않음");
    expect(html).not.toContain("PDF");
  });

  it("highlights role guidance for the selected statistical method", () => {
    const catalog = analysisTestCatalog();

    const renderSelectedMethod = (
      methodId: string,
      moduleId: "hypothesis" | "quality" | "doe",
      labelKo: string,
    ) => {
      const selectedMethod = {
        ...catalog.methods[0],
        availability: "available" as const,
        label_en: labelKo,
        label_ko: labelKo,
        method_id: methodId,
        module_id: moduleId,
      };

      return renderToString(<RoleDictionary selectedMethod={selectedMethod} />);
    };

    const twoSampleHtml = renderSelectedMethod(
      "hypothesis.two_sample_t",
      "hypothesis",
      "2-표본 t-검정",
    );
    expect(twoSampleHtml).toContain("2-표본 t-검정 핵심 역할");
    expect(twoSampleHtml).toContain("독립성은 데이터만으로 검증되지 않으므로");

    const pairedHtml = renderSelectedMethod(
      "hypothesis.paired_t",
      "hypothesis",
      "대응표본 t-검정",
    );
    expect(pairedHtml).toContain("대응표본 t-검정 핵심 역할");
    expect(pairedHtml).toContain("Before/After");
    expect(pairedHtml).toContain("독립 2표본 검정");

    const capabilityHtml = renderSelectedMethod(
      "quality.capability",
      "quality",
      "공정능력",
    );
    expect(capabilityHtml).toContain("Capability 핵심 역할");
    expect(capabilityHtml).toContain("Spec limit은 고객/공정 규격이고 control limit이 아니므로");

    const gageHtml = renderSelectedMethod("quality.gage_rr", "quality", "Gage R&R");
    expect(gageHtml).toContain("Gage R&amp;R 핵심 역할");
    expect(gageHtml).toContain("balanced crossed design");

    const doeHtml = renderSelectedMethod("doe.factorial_design", "doe", "요인배치 설계");
    expect(doeHtml).toContain("DOE 설계 핵심 역할");
    expect(doeHtml).toContain("Factor 이름, low/high level, run order, random seed");

    const rsmHtml = renderSelectedMethod("doe.response_surface", "doe", "반응표면법");
    expect(rsmHtml).toContain("반응표면 설계 핵심 역할");
    expect(rsmHtml).toContain("axial point");

    const bayesianHtml = renderSelectedMethod(
      "doe.bayesian_optimization",
      "doe",
      "베이지안 최적화",
    );
    expect(bayesianHtml).toContain("순차 Bayesian Optimization 핵심 역할");
    expect(bayesianHtml).toContain("Matérn-5/2 GP와 Expected Improvement");
  });

  it("renders available dedicated workflow cards without common dataset preflight", () => {
    const catalog: AnalysisMethodListResponse = {
      modules: [
        {
          module_id: "regression",
          label_ko: "상관관계 및 회귀",
          label_en: "Regression",
          order: 4,
        },
      ],
      methods: [
        {
          method_id: "regression.predict",
          method_version: "0.2.0",
          module_id: "regression",
          label_ko: "예측",
          label_en: "Predict",
          availability: "available",
          execution_mode: "dedicated",
          requires_dataset: false,
          source_prerequisite: "regression_model",
          order: 40,
          disabled_reason: null,
        },
        {
          method_id: "regression.response_optimizer",
          method_version: "0.3.0",
          module_id: "regression",
          label_ko: "반응 최적화",
          label_en: "Response Optimizer",
          availability: "available",
          execution_mode: "dedicated",
          requires_dataset: false,
          source_prerequisite: "response_surface_analysis",
          order: 50,
          disabled_reason: null,
        },
      ],
    };
    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        profile={null}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="regression"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>공통 데이터 필터</div>}
        renderExecutableMethod={() => <div>Predict 전용 패널</div>}
      />,
    );
    expect(html).toContain("사용 가능 · 전용 워크플로");
    expect(html).toContain("저장 회귀모형 선택");
    expect(html).toContain("generic analysis-run으로 실행되지 않습니다");
    expect(html).toContain("Predict 전용 패널");
    expect(html).not.toContain("공통 데이터 필터");
    expect(html).not.toContain("분석 이력");
    expect(html).not.toContain("결과 내보내기");
    expect(html).not.toContain("비활성");
  });

  it("renders source-driven Predict and Response Optimizer workspace entry states", () => {
    const predictionHtml = renderToString(
      <RegressionPredictionWorkspace onNavigateToLinearModel={() => undefined} />,
    );
    const optimizerHtml = renderToString(
      <ResponseOptimizerWorkspace onNavigateToResponseSurface={() => undefined} />,
    );

    expect(predictionHtml).toContain("저장된 회귀모형으로 예측");
    expect(predictionHtml).toContain("Source 회귀모형");
    expect(predictionHtml).toContain("사용 가능 · 전용");
    expect(optimizerHtml).toContain("저장된 RSM 분석으로 반응 최적화");
    expect(optimizerHtml).toContain("Source 반응표면 분석");
    expect(optimizerHtml).toContain("사용 가능 · 전용");
  });

  it("accepts only a stored prediction matching the deep-link source selection", () => {
    const prediction = {
      prediction_id: "11111111-1111-4111-8111-111111111111",
      analysis_id: "66666666-6666-4666-8666-666666666666",
      source_analysis_id: "66666666-6666-4666-8666-666666666666",
      model_id: "22222222-2222-4222-8222-222222222222",
      source_dataset_version_id: "33333333-3333-4333-8333-333333333333",
      target_dataset_version_id: "44444444-4444-4444-8444-444444444444",
      rows: [],
    } as unknown as RegressionPredictionResponse;
    const envelope = {
      analysis_id: prediction.prediction_id,
      method_id: "regression.predict",
      result: prediction,
    } as unknown as AnalysisResultEnvelope;

    expect(
      restoredPredictionForSelection(
        envelope,
        prediction.prediction_id,
        prediction.model_id,
        prediction.target_dataset_version_id,
      ),
    ).toBe(prediction);
    expect(
      restoredPredictionForSelection(
        envelope,
        prediction.prediction_id,
        prediction.model_id,
        "55555555-5555-4555-8555-555555555555",
      ),
    ).toBeNull();
    expect(
      restoredPredictionForSelection(
        { ...envelope, method_id: "regression.linear_model" },
        prediction.prediction_id,
        prediction.model_id,
        prediction.target_dataset_version_id,
      ),
    ).toBeNull();
  });

  it("accepts only a stored optimization matching the selected RSM dependency", () => {
    const design = {
      design_id: "11111111-1111-4111-8111-111111111111",
      design_version_id: "22222222-2222-4222-8222-222222222222",
    } as ResponseSurfaceDesignResponse;
    const analysis = {
      analysis_id: "33333333-3333-4333-8333-333333333333",
    } as DoeResponseSurfaceAnalysisResponse;
    const optimization = {
      optimization_id: "44444444-4444-4444-8444-444444444444",
      design_id: design.design_id,
      design_version_id: design.design_version_id,
      source_analysis_ids: [analysis.analysis_id],
    } as ResponseOptimizerResponse;

    expect(
      restoredOptimizationMatchesSelection(
        optimization,
        optimization.optimization_id,
        design,
        analysis,
      ),
    ).toBe(true);
    expect(
      restoredOptimizationMatchesSelection(
        { ...optimization, source_analysis_ids: ["55555555-5555-4555-8555-555555555555"] },
        optimization.optimization_id,
        design,
        analysis,
      ),
    ).toBe(false);
    expect(restoredOptimizationMatchesSelection(optimization, null, design, analysis)).toBe(
      false,
    );
  });

  it("describes Bayesian recommendations as executable but not observed or globally optimal", () => {
    const catalog = analysisTestCatalog();
    const html = renderToString(
      <HelpCenterPage catalog={catalog} onOpenAnalysis={() => undefined} />,
    );

    expect(html).toContain(
      "관측 이력에 Gaussian Process와 Expected Improvement를 적용해 다음 확인 실험 후보를 추천합니다.",
    );
    expect(html).toContain("추천값은 실제 관측이 아니며 전역 최적을 보장");
    expect(html).not.toContain("현재는 계약 단계로 실행되지 않으며");
  });

  it("renders the dedicated Bayesian study, observation, and recommendation controls", () => {
    const html = renderToString(<BayesianOptimizationPanel />);

    expect(html).toContain("Bayesian 최적화");
    expect(html).toContain("Study 생성");
    expect(html).toContain("앱은 목적함수를 실행하지 않습니다");
    expect(html).toContain("저장된 study");
    expect(html).toContain("초기 trial 수");
    expect(html).toContain("실제 단위 선형 제약");
    expect(html).toContain("제약 추가");
  });

  it("builds actual-unit Bayesian linear constraints and rejects invalid drafts", () => {
    const base = {
      studyName: "Constrained study",
      factors: [
        { key: 1, factorId: "temperature", name: "Temperature", low: "60", high: "80", unit: "C" },
        { key: 2, factorId: "pressure", name: "Pressure", low: "5", high: "15", unit: "bar" },
      ],
      objectiveName: "Yield",
      objectiveUnit: "%",
      direction: "maximize" as const,
      initialDesignSize: "3",
      initialDesignSeed: "20260715",
    };
    const request = buildBayesianStudyRequest({
      ...base,
      constraints: [
        {
          key: 1,
          constraintId: "energy_limit",
          name: "Energy limit",
          coefficients: { 1: "2", 2: "-0.5" },
          relation: "less_than_or_equal" as const,
          bound: "150",
        },
      ],
    });

    expect(request).not.toBe("bayesian_study_input_invalid");
    if (typeof request !== "string") {
      expect(request.constraints).toEqual([
        {
          constraint_id: "energy_limit",
          name: "Energy limit",
          terms: [
            { factor_id: "temperature", coefficient: 2 },
            { factor_id: "pressure", coefficient: -0.5 },
          ],
          relation: "less_than_or_equal",
          bound: 150,
        },
      ]);
    }
    expect(
      buildBayesianStudyRequest({
        ...base,
        constraints: [
          {
            key: 2,
            constraintId: "zero_constraint",
            name: "Invalid zero constraint",
            coefficients: { 1: "", 2: "0" },
            relation: "greater_than_or_equal",
            bound: "0",
          },
        ],
      }),
    ).toBe("bayesian_study_input_invalid");
  });

  it("keeps frontend Bayesian initial-design and trial-budget boundaries aligned", () => {
    expect([1, 2, 6].map(minimumBayesianInitialDesignSize)).toEqual([2, 3, 7]);
    const twoFactorDraft = {
      studyName: "Boundary study",
      factors: [
        { key: 1, factorId: "x1", name: "Input 1", low: "0", high: "1", unit: "" },
        { key: 2, factorId: "x2", name: "Input 2", low: "0", high: "1", unit: "" },
      ],
      constraints: [],
      objectiveName: "Response",
      objectiveUnit: "",
      direction: "maximize" as const,
      initialDesignSeed: "17",
    };

    expect(
      buildBayesianStudyRequest({ ...twoFactorDraft, initialDesignSize: "2" }),
    ).toBe("bayesian_study_initial_design_too_small");
    expect(
      buildBayesianStudyRequest({ ...twoFactorDraft, initialDesignSize: "3" }),
    ).not.toBe("bayesian_study_initial_design_too_small");
    expect(bayesianRecommendationBudgetBlocker(49, 50, 200)).toBeNull();
    expect(bayesianRecommendationBudgetBlocker(50, 50, 200)).toBe(
      "bayesian_optimization_budget_exhausted",
    );
    expect(bayesianRecommendationBudgetBlocker(199, 200, 200)).toBeNull();
    expect(bayesianRecommendationBudgetBlocker(200, 200, 200)).toBe(
      "bayesian_optimization_budget_exhausted",
    );
  });

  it("renders explicit immutable completion and abandon confirmations", () => {
    const trial = {
      trial_id: "00000000-0000-4000-8000-000000000301",
      study_version_id: "00000000-0000-4000-8000-000000000302",
      trial_number: 3,
      origin: "initial_design",
      state: "pending",
      actual_coordinates: { temperature: 72.5 },
      normalized_coordinates: { temperature: 0.625 },
      coordinates_sha256: "a".repeat(64),
      objective_value: null,
      created_at: "2026-07-16T00:00:00Z",
      closed_at: null,
    } satisfies BayesianTrialResponse;
    const completionHtml = renderToString(
      <BayesianTrialTransitionConfirmation
        trial={trial}
        action="complete"
        objectiveValue="91.25"
        isSaving={false}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );
    const abandonHtml = renderToString(
      <BayesianTrialTransitionConfirmation
        trial={trial}
        action="abandon"
        objectiveValue=""
        isSaving={false}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );

    expect(completionHtml).toContain("objective 91.25");
    expect(completionHtml).toContain("이후 수정할 수 없습니다");
    expect(completionHtml).toContain("관측 저장 확인");
    expect(abandonHtml).toContain("향후 추천에서 제외");
    expect(abandonHtml).toContain("최소 완료 관측 수");
    expect(abandonHtml).toContain("Abandon 확인");
  });

  it("renders immutable Bayesian study close confirmation and enforces blockers", () => {
    const closeHtml = renderToString(
      <BayesianStudyCloseConfirmation
        study={{
          study_id: "00000000-0000-4000-8000-000000000501",
          name: "Lifecycle study",
          completed_trial_count: 3,
          abandoned_trial_count: 1,
        }}
        target="completed"
        reason="confirmation_complete"
        note="Confirmation run reviewed"
        isClosing={false}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );

    expect(closeHtml).toContain("종료 후에는 수정하거나 다시 열 수 없습니다");
    expect(closeHtml).toContain("전역 최적해 달성");
    expect(closeHtml).toContain("Confirmation run reviewed");
    expect(
      bayesianStudyCloseBlocker(
        {
          status: "active",
          pending_trial_count: 1,
          completed_trial_count: 2,
          recommendation_minimum_completed_observations: 2,
        },
        "abandoned",
        false,
      ),
    ).toBe("bayesian_study_close_pending_trials");
    expect(
      bayesianStudyCloseBlocker(
        {
          status: "active",
          pending_trial_count: 0,
          completed_trial_count: 2,
          recommendation_minimum_completed_observations: 2,
        },
        "completed",
        false,
      ),
    ).toBe("bayesian_study_completion_requirements_not_met");
    expect(
      bayesianStudyCloseBlocker(
        {
          status: "completed",
          pending_trial_count: 0,
          completed_trial_count: 3,
          recommendation_minimum_completed_observations: 2,
        },
        "completed",
        true,
      ),
    ).toBe("bayesian_study_closed");
  });

  it("warns before reusing a predecessor seed for a successor study", () => {
    const html = renderToString(
      <BayesianSuccessorSeedNotice sameSeed onGenerateSeed={() => undefined} />,
    );

    expect(html).toContain("동일한 seed를 사용하면 동일한 초기 조건이 다시 생성될 수 있습니다");
    expect(html).toContain("기존 관측, history, recommendation은 복사하지 않습니다");
    expect(html).toContain("새 random seed 생성");
  });

  it("shows exact Bayesian deletion impact before enabling irreversible deletion", () => {
    const preflight = {
      preflight_schema_version: 1,
      study_id: "00000000-0000-4000-8000-000000000601",
      study_version_id: "00000000-0000-4000-8000-000000000602",
      status: "abandoned",
      eligible: true,
      blockers: [],
      successor_study_count: 0,
      counts: {
        study_count: 1,
        study_version_count: 1,
        trial_count: 3,
        history_revision_count: 2,
        history_head_count: 1,
        recommendation_count: 1,
        lifecycle_event_count: 1,
        metadata_record_count: 10,
        file_count: 0,
        file_bytes: 0,
      },
      deletion_manifest_sha256: "a".repeat(64),
    } satisfies BayesianStudyDeletionPreflightResponse;
    const html = renderToString(
      <BayesianStudyDeletionConfirmation
        study={{ study_id: preflight.study_id, name: "Closed study" }}
        preflight={preflight}
        isDeleting={false}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );

    expect(html).toContain("metadata 10건");
    expect(html).toContain("파일 0개 · 0 bytes");
    expect(html).toContain("복원할 수 없으며");
    expect(html).toContain("cascade 또는 successor 삭제는 수행하지 않습니다");
    expect(html).toContain("영구 삭제 확인");
  });

  it("labels latest recommendation current trial state separately from its snapshot", () => {
    const recommendation = {
      trial: { state: "pending" },
      current_trial: {
        trial_id: "00000000-0000-4000-8000-000000000401",
        state: "pending",
        objective_value: null,
        closed_at: null,
      },
      is_latest: true,
    } as BayesianRecommendationResponse;

    expect(bayesianRecommendationStatus(recommendation).label).toBe("확인 대기");
    recommendation.current_trial = {
      ...recommendation.current_trial!,
      state: "completed",
      objective_value: 0.95,
      closed_at: "2026-07-16T00:01:00Z",
    };
    expect(bayesianRecommendationStatus(recommendation).label).toBe("관측 완료");
    recommendation.current_trial = {
      ...recommendation.current_trial,
      state: "abandoned",
      objective_value: null,
    };
    expect(bayesianRecommendationStatus(recommendation).label).toBe("중단됨");
    recommendation.is_latest = false;
    expect(bayesianRecommendationStatus(recommendation).label).toBe("과거 추천");
  });

  it("renders the response surface dedicated design and analysis controls", () => {
    const html = renderToString(<ResponseSurfacePanel />);

    expect(html).toContain("반응표면법");
    expect(html).toContain("Rotatable CCI");
    expect(html).toContain("Face-centered CCD");
    expect(html).toContain("CCD 생성");
    expect(html).toContain("Full quadratic, no automatic selection");
  });

  it("renders bounded response optimizer objectives, constraints, and budgets", () => {
    const design = {
      design_id: "00000000-0000-4000-8000-000000000201",
      factors: [
        { name: "Temperature", low: 60, high: 80, unit: "C" },
        { name: "Pressure", low: 5, high: 15, unit: "bar" },
      ],
    } as unknown as ResponseSurfaceDesignResponse;
    const analysis = responseOptimizerAnalysisTestResponse();

    const html = renderToString(
      <ResponseOptimizerPanel design={design} analysis={analysis} />,
    );

    expect(html).toContain("Response Optimizer");
    expect(html).toContain("목표 유형");
    expect(html).toContain("최대화");
    expect(html).toContain("Temperature optimizer lower bound");
    expect(html).toContain("선형 제약 사용");
    expect(html).toContain("최대 평가 수");
    expect(html).toContain("Response Optimizer 실행");
  });

  it("classifies saturated RSM sources as blocking before optimizer execution", () => {
    const analysis = responseOptimizerAnalysisTestResponse();
    analysis.result.sample.df_residual = 0;
    analysis.result.fit.residual_mean_square = null;
    analysis.result.fit.residual_standard_error = null;

    const html = renderToString(
      <ResponseOptimizerPanel
        analysis={analysis}
        design={responseSurfaceDesignTestResponse("analyzed")}
      />,
    );

    expect(html).toContain("차단:");
    expect(html).toContain("response_optimizer_source_model_saturated");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Response Optimizer 실행<\/button>/);
  });

  it("requires an explicit checkbox for advisory RSM source warnings", () => {
    const analysis = responseOptimizerAnalysisTestResponse();
    analysis.result.sample.df_residual = 4;

    const html = renderToString(
      <ResponseOptimizerPanel
        analysis={analysis}
        design={responseSurfaceDesignTestResponse("analyzed")}
      />,
    );

    expect(html).toContain("response_optimizer_source_residual_df_small");
    expect(html).toContain('type="checkbox"');
    expect(html).toContain("source 모형 진단 경고를 검토했습니다");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Response Optimizer 실행<\/button>/);
  });

  it("locks analyzed RSM response controls and warns before a completed analysis", () => {
    const analyzed = responseSurfaceDesignTestResponse("analyzed");
    const completed = responseSurfaceDesignTestResponse("completed");
    const common = {
      responseName: "Yield",
      responseUnit: "%",
      responseValues: { 1: "10" },
      responsesSaved: true,
      responseRevisionNumber: 1,
      responseRevisionSha256: "a".repeat(64),
      revisionHistory: null,
      correctionMode: false,
      isSaving: false,
      isAnalyzing: false,
      onResponseNameChange: () => undefined,
      onResponseUnitChange: () => undefined,
      onResponseValueChange: () => undefined,
      onStartCorrection: () => undefined,
      onSave: () => undefined,
      onAnalyze: () => undefined,
    };

    const analyzedHtml = renderToString(
      <ResponseSurfaceResponseEntry {...common} design={analyzed} />,
    );
    const completedHtml = renderToString(
      <ResponseSurfaceResponseEntry {...common} design={completed} />,
    );
    const correctionHtml = renderToString(
      <ResponseSurfaceResponseEntry
        {...common}
        correctionMode
        design={analyzed}
        revisionHistory={{
          design_id: analyzed.design_id,
          design_version_id: analyzed.design_version_id,
          response_name: "Yield",
          total: 1,
          offset: 0,
          limit: 20,
          items: [
            {
              response_revision_id: "77777777-7777-4777-8777-777777777777",
              design_id: analyzed.design_id,
              design_version_id: analyzed.design_version_id,
              response_revision_schema_version: 1,
              response_revision_sha256: "a".repeat(64),
              response_name: "Yield",
              unit: "%",
              revision_number: 1,
              state: "completed",
              is_current: true,
              response_count: 1,
              supersedes_response_revision_id: null,
              created_at: "2026-07-15T00:00:00.000Z",
              closed_at: "2026-07-15T00:00:00.000Z",
              values: [{ run_order: 1, value: 10 }],
            },
          ],
        }}
      />,
    );

    expect((analyzedHtml.match(/disabled=""/g) ?? []).length).toBeGreaterThanOrEqual(4);
    expect(analyzedHtml).toContain("현재 revision은 읽기 전용입니다");
    expect(analyzedHtml).toContain("새 revision으로 수정");
    expect(completedHtml).toContain("분석을 실행하면 현재 설계의 반응값이 잠깁니다");
    expect(completedHtml).not.toContain('role="status"');
    expect(correctionHtml).toContain("새 revision을 편집 중입니다");
    expect(correctionHtml).toContain("새 revision 저장");
    expect(correctionHtml).toMatch(/<input disabled="" value="Yield"/);
    expect(correctionHtml).toContain("RSM response revision history");
    expect(correctionHtml).not.toContain("새 revision으로 수정");
  });

  it("locks factorial response controls from restored analyzed status", () => {
    const analyzedHtml = renderToString(
      <FactorialDesignPreview
        analysis={factorialAnalysisTestResponse()}
        analysisError={null}
        design={factorialDesignTestResponse()}
        isRunningAnalysis={false}
        isSavingResponses={false}
        onSaveResponses={() => undefined}
        onRunAnalysis={() => undefined}
        responseError={null}
        responses={factorialDesignResponsesTestResponse()}
      />,
    );
    const completedResponses = {
      ...factorialDesignResponsesTestResponse(),
      status: "completed",
    };
    const completedHtml = renderToString(
      <FactorialDesignPreview
        analysis={null}
        analysisError={null}
        design={factorialDesignTestResponse()}
        isRunningAnalysis={false}
        isSavingResponses={false}
        onSaveResponses={() => undefined}
        onRunAnalysis={() => undefined}
        responseError={null}
        responses={completedResponses}
      />,
    );

    expect(analyzedHtml).toContain("읽기 전용입니다");
    expect(analyzedHtml).toContain("새 revision으로 수정");
    expect(analyzedHtml).toContain("Response revision");
    expect((analyzedHtml.match(/disabled=""/g) ?? []).length).toBeGreaterThanOrEqual(7);
    expect(completedHtml).toContain("분석을 실행하면 현재 설계의 반응값이 잠깁니다");
    expect(completedHtml).not.toContain('role="status"');
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

  it("shows a JSON export action for a succeeded analysis result", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const analysisResult = analysisResultEnvelopeTestResponse(selectedMethod.method_id);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        exportState={{ onCreateAnalysisResultJsonExport: () => undefined }}
        profile={null}
        selectedAnalysisResult={analysisResult}
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
    expect(html).toContain("결과 내보내기");
    expect(html).toContain("재현과 기계처리에 적합한 전체 result envelope입니다.");
    expect(html).toContain("표 형태로 검토하기 쉬운 long-form CSV입니다.");
    expect(html).toContain("사람에게 공유하기 좋은 self-contained 정적 보고서입니다.");
    expect(html).toContain("JSON 생성");
    expect(html).toContain("CSV 생성");
    expect(html).toContain("HTML 생성");
    expect(html).toContain(selectedMethod.method_id);
  });

  it("renders saved analysis history with stale badge, restore summary, and export list", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const history = analysisRunListTestResponse(restored);
    const exportList = analysisResultExportListTestResponse(restored);
    const comparison = analysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        exportState={{ analysisResultExportList: exportList }}
        historyState={{
          analysisHistory: history,
          analysisHistoryMethodId: restored.method_id,
          analysisHistoryResultAvailabilityFilter: "available",
          analysisHistoryStaleFilter: "stale",
          analysisHistoryStatus: "succeeded",
          onRefreshAnalysisHistory: () => undefined,
        }}
        profile={null}
        restoredState={{
          restoredAnalysisResult: restored,
          onRestoreAnalysisRun: () => undefined,
        }}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    const text = html.replace(/<!-- -->/g, "");

    expect(text).toContain("현재 데이터셋의 저장된 분석");
    expect(text).toContain("필터 상태");
    expect(text).toContain("method");
    expect(text).toContain("status");
    expect(text).toContain("result");
    expect(html).toContain("이전");
    expect(html).toContain("다음");
    expect(html).toContain("왼쪽");
    expect(html).toContain("오른쪽");
    expect(html).toContain("비교 결과");
    expect(html).toContain("compatible");
    expect(html).toContain("같은 method/version일 때만 자세한 비교가 가능합니다.");
    expect(html).toContain("기술통계 비교");
    expect(html).toContain("delta");
    expect(html).toContain("delta는 right - left입니다.");
    expect(html).toContain("p-value delta");
    expect(html).toContain("mean");
    expect(html).toContain("result_sha256");
    expect(html).toContain("stale · 재검토 필요");
    expect(html).toContain("결과 불러오기");
    expect(html).toContain("불러온 결과");
    expect(html).toContain("ui_export_contract_test");
    expect(text).toContain("1개 표시 · 1-1 · 다음 페이지 없음");
    expect(html).toContain("최근 export");
    expect(html).toContain("JSON");
    expect(html).toContain("CSV");
    expect(html).toContain("다운로드");
  });

  it("renders saved analysis history unavailable-result and pagination states", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const history = analysisRunListTestResponse(restored);
    const unavailableHistory: AnalysisRunListResponse = {
      ...history,
      has_more: true,
      result_available: false,
      runs: history.runs.map((run) => ({
        ...run,
        artifact_count: 0,
        result_available: false,
        stale: false,
      })),
    };

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        historyState={{
          analysisHistory: unavailableHistory,
          analysisHistoryResultAvailabilityFilter: "unavailable",
          onRefreshAnalysisHistory: () => undefined,
        }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        restoredState={{ onRestoreAnalysisRun: () => undefined }}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    const text = html.replace(/<!-- -->/g, "");

    expect(text).toContain("현재 데이터셋의 저장된 분석");
    expect(text).toContain("result unavailable");
    expect(text).toContain("result 없음");
    expect(text).toContain("결과 없음");
    expect(text).toContain("1개 표시 · 1-1 · 다음 페이지 있음");
  });

  it("explains incompatible stored result comparisons", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const baseComparison = analysisRunComparisonTestResponse(restored);
    const comparison: AnalysisRunComparisonResponse = {
      ...baseComparison,
      comparable: false,
      compatibility: {
        ...baseComparison.compatibility,
        same_dataset_version_id: false,
        same_method_version: false,
      },
      right: {
        ...baseComparison.right,
        dataset_version_id: "version-2",
        method_version: "0.2.0",
      },
    };

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{
          analysisHistory: analysisRunListTestResponse(restored),
          onRefreshAnalysisHistory: () => undefined,
        }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        restoredState={{ onRestoreAnalysisRun: () => undefined }}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("incompatible comparison");
    expect(html).toContain("method version mismatch");
    expect(html).toContain("dataset version mismatch");
    expect(html).toContain("different");
  });

  it("renders one-sample t stored result comparison metrics", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod =
      catalog.methods.find((method) => method.method_id === "hypothesis.one_sample_t") ??
      catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse("hypothesis.one_sample_t");
    const history = analysisRunListTestResponse(restored);
    const comparison = oneSampleTAnalysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{ analysisHistory: history }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("1-표본 t-검정 비교");
    expect(html).toContain("response-alpha");
    expect(html).toContain("null_mean");
    expect(html).toContain("contrast.estimate");
    expect(html).toContain("-0.25");
  });

  it("renders two-sample t stored result comparison metrics", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod =
      catalog.methods.find((method) => method.method_id === "hypothesis.two_sample_t") ??
      catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse("hypothesis.two_sample_t");
    const history = analysisRunListTestResponse(restored);
    const comparison = twoSampleTAnalysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{ analysisHistory: history }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("2-표본 t-검정 비교");
    expect(html).toContain("response-alpha");
    expect(html).toContain("group-beta");
    expect(html).toContain("null_difference");
    expect(html).toContain("contrast.estimate");
    expect(html).toContain("group set");
  });

  it("renders paired t stored result comparison metrics", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod =
      catalog.methods.find((method) => method.method_id === "hypothesis.paired_t") ??
      catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse("hypothesis.paired_t");
    const history = analysisRunListTestResponse(restored);
    const comparison = pairedTAnalysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{ analysisHistory: history }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("대응표본 t-검정 비교");
    expect(html).toContain("before-alpha");
    expect(html).toContain("after-beta");
    expect(html).toContain("null_difference");
    expect(html).toContain("paired_sample.mean_difference");
    expect(html).toContain("contrast.estimate");
  });

  it("renders equivalence TOST stored result comparison metrics", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod =
      catalog.methods.find((method) => method.method_id === "hypothesis.equivalence_tost") ??
      catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse("hypothesis.equivalence_tost");
    const history = analysisRunListTestResponse(restored);
    const comparison = equivalenceTostAnalysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{ analysisHistory: history }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("동등성 TOST 비교");
    expect(html).toContain("response-alpha");
    expect(html).toContain("equivalence_bounds.lower");
    expect(html).toContain("tost.equivalent");
    expect(html).toContain("tests.upper.p_value");
    expect(html).toContain("estimate.value");
  });

  it("renders one-way ANOVA stored result comparison metrics", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod =
      catalog.methods.find((method) => method.method_id === "hypothesis.one_way_anova") ??
      catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse("hypothesis.one_way_anova");
    const history = analysisRunListTestResponse(restored);
    const comparison = oneWayAnovaAnalysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{ analysisHistory: history }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("일원분산분석 비교");
    expect(html).toContain("response-alpha");
    expect(html).toContain("group-beta");
    expect(html).toContain("alpha");
    expect(html).toContain("posthoc.performed");
    expect(html).toContain("groups.2.mean");
    expect(html).toContain("test.f_statistic");
    expect(html).toContain("posthoc.comparison_count");
    expect(html).toContain("group set");
  });

  it("renders Kruskal-Wallis stored result comparison metrics", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod =
      catalog.methods.find((method) => method.method_id === "hypothesis.kruskal_wallis") ??
      catalog.methods[0];
    const restored = analysisResultEnvelopeTestResponse("hypothesis.kruskal_wallis");
    const history = analysisRunListTestResponse(restored);
    const comparison = kruskalWallisAnalysisRunComparisonTestResponse(restored);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        comparisonState={{
          analysisComparison: comparison,
          analysisComparisonLeftId: comparison.left.analysis_id,
          analysisComparisonRightId: comparison.right.analysis_id,
        }}
        historyState={{ analysisHistory: history }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="hypothesis"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("Kruskal-Wallis 비교");
    expect(html).toContain("response-alpha");
    expect(html).toContain("group-beta");
    expect(html).toContain("posthoc.performed");
    expect(html).toContain("groups.2.mean_rank");
    expect(html).toContain("test.h_statistic");
    expect(html).toContain("test.effect_size.epsilon_squared");
    expect(html).toContain("posthoc.comparison_count");
    expect(html).toContain("group set");
  });

  it("calls analysis history, result restore, and export list API wrappers", async () => {
    const restored = analysisResultEnvelopeTestResponse();
    const history = analysisRunListTestResponse(restored);
    const exportList = analysisResultExportListTestResponse(restored);
    const comparison = analysisRunComparisonTestResponse(restored);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(history))
      .mockResolvedValueOnce(jsonResponse(restored))
      .mockResolvedValueOnce(jsonResponse(exportList))
      .mockResolvedValueOnce(jsonResponse(comparison));

    const historyResponse = await fetchAnalysisRuns({
      datasetVersionId: "version-1",
      methodId: "eda.descriptive",
      resultAvailable: true,
      limit: 20,
      offset: 0,
      stale: false,
      status: "succeeded",
    });
    const resultResponse = await fetchAnalysisRunResult(restored.analysis_id);
    const exportListResponse = await fetchAnalysisResultExports(restored.analysis_id);
    const comparisonResponse = await fetchAnalysisRunComparison(
      comparison.left.analysis_id,
      comparison.right.analysis_id,
    );

    expect(historyResponse).toEqual(history);
    expect(resultResponse).toEqual(restored);
    expect(exportListResponse).toEqual(exportList);
    expect(comparisonResponse).toEqual(comparison);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8000/api/v1/analysis-runs?limit=20&offset=0&dataset_version_id=version-1&method_id=eda.descriptive&status=succeeded&stale=false&result_available=true",
      expect.objectContaining({
        headers: { Accept: "application/json" },
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `http://127.0.0.1:8000/api/v1/analysis-runs/${restored.analysis_id}/result`,
      expect.objectContaining({
        headers: { Accept: "application/json" },
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      `http://127.0.0.1:8000/api/v1/analysis-runs/${restored.analysis_id}/exports`,
      expect.objectContaining({
        method: "GET",
        headers: { Accept: "application/json" },
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      `http://127.0.0.1:8000/api/v1/analysis-runs/comparison?left_analysis_id=${comparison.left.analysis_id}&right_analysis_id=${comparison.right.analysis_id}`,
      expect.objectContaining({
        headers: { Accept: "application/json" },
      }),
    );
  });

  it("builds API routes from a central route map and encodes path ids", () => {
    expect(apiRoutes.datasetConfirmParsing("dataset/1")).toBe(
      "http://127.0.0.1:8000/api/v1/datasets/dataset%2F1/confirm-parsing",
    );
    expect(apiRoutes.datasetVersion("version/1")).toBe(
      "http://127.0.0.1:8000/api/v1/dataset-versions/version%2F1",
    );
    expect(apiRoutes.datasetVersionRows("version/1", 5, 10)).toBe(
      "http://127.0.0.1:8000/api/v1/dataset-versions/version%2F1/rows?limit=10&offset=5",
    );
    expect(apiRoutes.datasetVersions(20, 40)).toBe(
      "http://127.0.0.1:8000/api/v1/dataset-versions?limit=20&offset=40",
    );
    expect(apiRoutes.regressionPredictionRows("prediction/1", 25, 50)).toBe(
      "http://127.0.0.1:8000/api/v1/regression-models/predictions/prediction%2F1/rows?limit=25&offset=50",
    );
    expect(apiRoutes.regressionPredictionCsvExport("prediction/1")).toBe(
      "http://127.0.0.1:8000/api/v1/regression-models/predictions/prediction%2F1/exports/csv",
    );
    expect(apiRoutes.analysisRunsBase()).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs",
    );
    expect(
      apiRoutes.analysisRuns({
        datasetVersionId: "version-1",
        methodId: "eda.descriptive",
        resultAvailable: true,
        limit: 20,
        offset: 0,
        stale: false,
        status: "succeeded",
      }),
    ).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs?limit=20&offset=0&dataset_version_id=version-1&method_id=eda.descriptive&status=succeeded&stale=false&result_available=true",
    );
    expect(apiRoutes.analysisRunExportDownload("analysis/1", "export/1")).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis%2F1/exports/export%2F1/download",
    );
    expect(
      apiRoutes.analysisRunExportDeletionPreflight("analysis/1", "export/1"),
    ).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis%2F1/exports/export%2F1/deletion-preflight",
    );
    expect(apiRoutes.analysisRunExportDelete("analysis/1", "export/1")).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis%2F1/exports/export%2F1",
    );
    expect(apiRoutes.analysisRunDeletionPreflight("analysis/1")).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis%2F1/deletion-preflight",
    );
    expect(apiRoutes.analysisRunDelete("analysis/1")).toBe(
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis%2F1/deletion",
    );
    expect(apiRoutes.attributeControlLimitSetsBase()).toBe(
      "http://127.0.0.1:8000/api/v1/quality/attribute-control-limit-sets",
    );
    expect(
      apiRoutes.attributeControlLimitSets({
        sourceDatasetVersionId: "version/1",
        chartType: "np",
        limit: 10,
        offset: 20,
      }),
    ).toBe(
      "http://127.0.0.1:8000/api/v1/quality/attribute-control-limit-sets?limit=10&offset=20&source_dataset_version_id=version%2F1&chart_type=np",
    );
    expect(apiRoutes.attributeControlLimitSet("limit/1")).toBe(
      "http://127.0.0.1:8000/api/v1/quality/attribute-control-limit-sets/limit%2F1",
    );
    expect(apiRoutes.attributeControlLimitSetDeletionPreflight("limit/1")).toBe(
      "http://127.0.0.1:8000/api/v1/quality/attribute-control-limit-sets/limit%2F1/deletion-preflight",
    );
    expect(apiRoutes.attributeControlMonitoringPreflight("limit/1")).toBe(
      "http://127.0.0.1:8000/api/v1/quality/attribute-control-limit-sets/limit%2F1/monitoring-preflight",
    );
    expect(apiRoutes.bayesianStudyClose("study/1")).toBe(
      "http://127.0.0.1:8000/api/v1/bayesian-studies/study%2F1/close",
    );
    expect(apiRoutes.bayesianStudyDeletionPreflight("study/1")).toBe(
      "http://127.0.0.1:8000/api/v1/bayesian-studies/study%2F1/deletion-preflight",
    );
    expect(apiRoutes.bayesianStudyDelete("study/1")).toBe(
      "http://127.0.0.1:8000/api/v1/bayesian-studies/study%2F1",
    );
    expect(apiRoutes.regressionModel("model/1")).toBe(
      "http://127.0.0.1:8000/api/v1/regression-models/model%2F1",
    );
    expect(apiRoutes.regressionModelDeletionPreflight("model/1")).toBe(
      "http://127.0.0.1:8000/api/v1/regression-models/model%2F1/deletion-preflight",
    );
  });

  it("calls exact-manifest export deletion API wrappers", async () => {
    const preflight: AnalysisResultExportDeletionPreflightResponse = {
      preflight_schema_version: 1,
      analysis_id: "analysis-1",
      export_id: "export-1",
      artifact_kind: "analysis_result_json_export",
      media_type: "application/json",
      sha256: "a".repeat(64),
      counts: { metadata_record_count: 1, file_count: 1, file_bytes: 2048 },
      deletion_manifest_sha256: "b".repeat(64),
    };
    const deleted = {
      deletion_schema_version: 1 as const,
      analysis_id: preflight.analysis_id,
      export_id: preflight.export_id,
      deletion_manifest_sha256: preflight.deletion_manifest_sha256,
      deleted_at: "2026-07-16T00:00:00Z",
      deleted_counts: preflight.counts,
      cleanup_status: "deleted" as const,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(preflight))
      .mockResolvedValueOnce(jsonResponse(deleted));

    expect(
      await fetchAnalysisResultExportDeletionPreflight(
        preflight.analysis_id,
        preflight.export_id,
      ),
    ).toEqual(preflight);
    expect(
      await deleteAnalysisResultExport(preflight.analysis_id, preflight.export_id, {
        confirmation_analysis_id: preflight.analysis_id,
        confirmation_export_id: preflight.export_id,
        expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
      }),
    ).toEqual(deleted);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis-1/exports/export-1/deletion-preflight",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis-1/exports/export-1",
      expect.objectContaining({
        method: "DELETE",
        body: JSON.stringify({
          confirmation_analysis_id: "analysis-1",
          confirmation_export_id: "export-1",
          expected_deletion_manifest_sha256: "b".repeat(64),
        }),
      }),
    );
  });

  it("shows the exact irreversible export deletion impact", () => {
    const preflight: AnalysisResultExportDeletionPreflightResponse = {
      preflight_schema_version: 1,
      analysis_id: "analysis-1",
      export_id: "export-1",
      artifact_kind: "analysis_result_json_export",
      media_type: "application/json",
      sha256: "a".repeat(64),
      counts: { metadata_record_count: 1, file_count: 1, file_bytes: 2048 },
      deletion_manifest_sha256: "b".repeat(64),
    };

    const html = renderToString(
      <AnalysisExportDeletionConfirmation
        preflight={preflight}
        isDeleting={false}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );

    expect(html).toContain("파일 1개");
    expect(html).toContain("2.0 KB");
    expect(html).toContain("metadata 1건");
    expect(html).toContain("복원할 수 없습니다");
    expect(html).toContain("저장된 분석 결과와 다른 export는 유지됩니다");
    expect(html).toContain("export 영구 삭제");
  });

  it("calls exact-manifest analysis run deletion API wrappers", async () => {
    const preflight = analysisRunDeletionPreflightTestResponse();
    const deleted = {
      deletion_schema_version: 1 as const,
      analysis_id: preflight.analysis_id,
      deletion_manifest_sha256: preflight.deletion_manifest_sha256,
      deleted_at: "2026-07-17T00:00:00Z",
      deleted_counts: preflight.counts,
      cleanup_status: "deleted" as const,
    };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce(jsonResponse(preflight))
      .mockResolvedValueOnce(jsonResponse(deleted));

    expect(await fetchAnalysisRunDeletionPreflight(preflight.analysis_id)).toEqual(preflight);
    expect(
      await deleteStoredAnalysisRun(preflight.analysis_id, {
        confirmation_analysis_id: preflight.analysis_id,
        expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
      }),
    ).toEqual(deleted);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis-1/deletion-preflight",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:8000/api/v1/analysis-runs/analysis-1/deletion",
      expect.objectContaining({
        method: "DELETE",
        body: JSON.stringify({
          confirmation_analysis_id: "analysis-1",
          expected_deletion_manifest_sha256: "d".repeat(64),
        }),
      }),
    );
  });

  it("shows exact irreversible analysis run impact and dependency blockers", () => {
    const preflight = analysisRunDeletionPreflightTestResponse();
    const confirmationHtml = renderToString(
      <AnalysisRunDeletionConfirmation
        isDeleting={false}
        onCancel={() => undefined}
        onConfirm={() => undefined}
        preflight={preflight}
      />,
    );
    const confirmationText = confirmationHtml.replace(/<!-- -->/g, "");
    expect(confirmationText).toContain("파일 5개");
    expect(confirmationText).toContain("2.0 KB");
    expect(confirmationText).toContain("metadata 5건");
    expect(confirmationText).toContain("복원할 수 없습니다");
    expect(confirmationText).toContain("분석 실행 영구 삭제");

    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const result = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const blockedHtml = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        historyState={{
          analysisHistory: analysisRunListTestResponse(result),
          analysisRunDeletionPreflight: {
            ...preflight,
            deletion_ready: false,
            blockers: [
              "analysis_run_deletion_regression_model_dependency",
              "analysis_run_deletion_limit_set_dependency",
            ],
            counts: {
              ...preflight.counts,
              regression_model_count: 1,
              attribute_control_limit_set_count: 1,
            },
          },
        }}
        profile={null}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderExecutableMethod={() => <div />}
      />,
    );
    expect(blockedHtml).toContain("참조 중인 자산이 있어");
    expect(blockedHtml).toContain("저장 회귀모형이 참조 중");
    expect(blockedHtml).toContain("Phase II limit set이 참조 중");
    expect(blockedHtml).not.toContain("분석 실행 영구 삭제");
  });

  it("shows JSON export metadata only for the matching analysis result", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const analysisResult = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const exportResult = analysisResultJsonExportTestResponse(analysisResult);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        exportState={{
          analysisResultJsonExport: exportResult,
          onCreateAnalysisResultJsonExport: () => undefined,
        }}
        profile={null}
        selectedAnalysisResult={analysisResult}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("생성됨");
    expect(html).toContain("2.0 KB");
    expect(html).toContain("sha256");
    expect(html).toContain("sha256:");
    expect(html).toContain("abcdef123456");
    expect(html).toContain("JSON 다운로드");
    expect(html).not.toContain("stale-badge");
  });

  it("warns before exporting stale stored results", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const analysisResult = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const exportResult: AnalysisResultJsonExportResponse = {
      ...analysisResultJsonExportTestResponse(analysisResult),
      stale: true,
    };

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        exportState={{
          analysisResultJsonExport: exportResult,
          onCreateAnalysisResultJsonExport: () => undefined,
        }}
        profile={null}
        selectedAnalysisResult={analysisResult}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("stale result export입니다.");
    expect(html).toContain("공유 전 재실행 여부를 확인하세요.");
    expect(html).toContain("stale · 재검토 필요");
  });

  it("shows export download errors inside the export panel", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const analysisResult = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const exportResult = analysisResultJsonExportTestResponse(analysisResult);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        exportState={{
          analysisResultExportDownloadError: "analysis_export_checksum_mismatch",
          analysisResultJsonExport: exportResult,
          onCreateAnalysisResultJsonExport: () => undefined,
          onDownloadAnalysisResultExport: () => undefined,
        }}
        profile={null}
        selectedAnalysisResult={analysisResult}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("export 다운로드 실패");
    expect(html).toContain("저장된 export 파일 또는 checksum이 맞지 않습니다.");
    expect(html).toContain("export를 다시 생성하세요");
    expect(html).toContain("analysis_export_checksum_mismatch");
  });

  it("shows CSV export metadata only for the matching analysis result", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const analysisResult = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const exportResult = analysisResultCsvExportTestResponse(analysisResult);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        exportState={{
          analysisResultCsvExport: exportResult,
          onCreateAnalysisResultCsvExport: () => undefined,
        }}
        profile={null}
        selectedAnalysisResult={analysisResult}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("생성됨");
    expect(html).toContain("CSV");
    expect(html).toContain("12");
    expect(html).toContain("행");
    expect(html).toContain("4.0 KB");
    expect(html).toContain("sha256");
    expect(html).toContain("123456abcdef");
    expect(html).toContain("CSV 다운로드");
    expect(html).not.toContain("stale-badge");
  });

  it("shows HTML report metadata only for the matching analysis result", () => {
    const catalog = analysisTestCatalog();
    const selectedMethod = catalog.methods[0];
    const analysisResult = analysisResultEnvelopeTestResponse(selectedMethod.method_id);
    const reportResult = analysisResultHtmlReportTestResponse(analysisResult);

    const html = renderToString(
      <AnalysisWorkbench
        analysisRunError={null}
        catalog={catalog}
        exportState={{
          analysisResultHtmlReport: reportResult,
          onCreateAnalysisResultHtmlReport: () => undefined,
        }}
        profile={null}
        selectedAnalysisResult={analysisResult}
        selectedMethod={selectedMethod}
        selectedMethods={[selectedMethod]}
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onSelectMethod={() => undefined}
        renderAnalysisFilters={() => <div>분석 필터</div>}
        renderExecutableMethod={() => <section className="analysis-run-panel">실행 패널</section>}
      />,
    );

    expect(html).toContain("생성됨");
    expect(html).toContain("HTML");
    expect(html).toContain("18");
    expect(html).toContain("개 항목");
    expect(html).toContain("8.0 KB");
    expect(html).toContain("sha256");
    expect(html).toContain("feedfacecafe");
    expect(html).toContain("HTML 다운로드");
    expect(html).not.toContain("stale-badge");
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
    expect(html).toContain("분석 도움말");
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
    expect(html).not.toContain("사전점검 해설");
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
    const targetVersionId = "cccccccc-dddd-eeee-ffff-000000000000";
    const predictionPreflight: RegressionPredictionPreflightResponse = {
      model_id: "12345678-90ab-cdef-1234-567890abcdef",
      analysis_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      source_dataset_version_id: version.version_id,
      target_dataset_version_id: targetVersionId,
      model_manifest_sha256: "a".repeat(64),
      source_schema_hash: "source-schema",
      source_schema_hash_current: "source-schema",
      source_analysis_stale: false,
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
          training_min: 0,
          training_max: 10,
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
      source_analysis_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      source_dataset_version_id: version.version_id,
      target_dataset_version_id: targetVersionId,
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
        method_id: "regression.predict",
        method_version: "0.2.0",
        dataset_version_id: targetVersionId,
        source_schema_hash: "target-schema",
        app_version: "0.1.0",
        source_analysis_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        source_analysis_stale_at_prediction: false,
        source_dataset_version_id: version.version_id,
        source_schema_hash_at_fit: "source-schema",
        source_schema_hash_current: "source-schema",
        target_dataset_version_id: targetVersionId,
        target_schema_hash: "target-schema",
        model_id: "12345678-90ab-cdef-1234-567890abcdef",
        model_manifest_sha256: "a".repeat(64),
        prediction_schema_version: 2,
        model_manifest_schema_version: 2,
        missing_policy: "complete_case",
        confidence_level: 0.95,
        include_intervals: true,
        source_canonical_artifact_sha256: "b".repeat(64),
        target_canonical_artifact_sha256: "c".repeat(64),
        created_at: "2026-07-13T00:00:00Z",
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
    const predictionRowsPage: RegressionPredictionRowsPageResponse = {
      prediction_id: prediction.prediction_id,
      model_id: prediction.model_id,
      offset: 0,
      limit: 25,
      total: 7,
      returned: 1,
      has_previous: false,
      has_next: true,
      rows: prediction.rows,
    };
    const predictionCsvExport: RegressionPredictionCsvExportResponse = {
      schema_version: 1,
      export_id: "eeeeeeee-ffff-0000-1111-222222222222",
      prediction_id: prediction.prediction_id,
      format: "regression_prediction_csv",
      artifact_kind: "regression_prediction_csv_export",
      media_type: "text/csv",
      sha256: "b".repeat(64),
      size_bytes: 2048,
      source_result_sha256: "c".repeat(64),
      stale: false,
      created_at: "2026-07-13T02:00:00Z",
      columns: ["prediction_id", "row_index", "predicted_mean"],
      row_count: 7,
      preview_rows: [],
    };
    const predictionTargetCatalog: DatasetVersionCatalogResponse = {
      offset: 0,
      limit: 20,
      total: 2,
      returned: 2,
      has_previous: false,
      has_next: false,
      versions: [
        {
          version_id: version.version_id,
          dataset_id: version.dataset_id,
          original_filename: "training.csv",
          version_number: 1,
          row_count: version.row_count,
          column_count: version.column_count,
          created_at: version.created_at,
          user_label: null,
          note: null,
          pinned: false,
          metadata_updated_at: null,
        },
        {
          version_id: targetVersionId,
          dataset_id: "dddddddd-eeee-ffff-0000-111111111111",
          original_filename: "prediction-target.csv",
          version_number: 1,
          row_count: 8,
          column_count: 3,
          created_at: "2026-07-13T01:00:00Z",
          user_label: null,
          note: null,
          pinned: false,
          metadata_updated_at: null,
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
        linearModelPredictionExportState={{
          csvExport: predictionCsvExport,
          error: null,
          isCreating: false,
          isDownloading: false,
          onCreate: vi.fn(),
          onDownload: vi.fn(),
        }}
        linearModelPredictionPreflight={predictionPreflight}
        linearModelPredictionRowsState={{
          error: null,
          isLoading: false,
          page: predictionRowsPage,
          onPageChange: vi.fn(),
        }}
        linearModelPredictionTargetState={{
          catalog: predictionTargetCatalog,
          error: null,
          isLoading: false,
          selectedTarget: predictionTargetCatalog.versions[1],
          selectedTargetVersionId: targetVersionId,
          onPageChange: vi.fn(),
          onSelect: vi.fn(),
        }}
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
    expect(html).toContain("Observed vs Fitted");
    expect(html).toContain("linear-model-diagnostic-layout");
    expect(html).toContain("linear-model-diagnostic-primary");
    expect(html).toContain("실제값과 예측값이 같은 y=x 기준선");
    expect(html).toContain("Multiple R");
    expect(html).toContain("Residual SE");
    expect(html).toContain("실제값 10.1");
    expect(html).toContain('tabindex="0"');
    expect(html).toContain("Residuals vs Fitted");
    expect(html).toContain("Leverage vs Cook");
    expect(html).toContain("Model ID");
    expect(html).toContain("저장 모델 관리");
    expect(html).toContain("삭제 영향 확인");
    expect(html).toContain("12345678-90");
    expect(html).toContain("예측 사전점검");
    expect(html).toContain("예측 대상 데이터셋 버전");
    expect(html).toContain("prediction-target.csv");
    expect(html).toContain("사전점검 실행");
    expect(html).toContain("예측 실행");
    expect(html).toContain("예측 준비 가능");
    expect(html).toContain("예측 결과 요약");
    expect(html).toContain("예측 구간 차트");
    expect(html).toContain("Prediction ID");
    expect(html).toContain("예측 평균");
    expect(html).toContain("9.975");
    expect(html).toContain("예측 행 페이지 이동");
    expect(html).toContain("전체 예측 CSV 생성");
    expect(html).toContain("전체 예측 CSV 다운로드");
    expect(html).toContain("1-1 / 7");
    expect(html).toContain("다음");
    expect(html).toContain("Schema hash");
    expect(html).toContain("Source model");
    expect(html).toContain("fresh");
    expect(html).toContain("Source schema");
    expect(html).toContain("적합 시점과 일치");
    expect(html).toContain("컬럼 ID");
    expect(html).toContain("학습범위 위");
  });

  it("renders the P/NP/C/U attribute control chart contract and result", () => {
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
          method_id: "quality.attribute_control_chart",
          method_version: "0.3.0",
          module_id: "quality",
          label_ko: "계수형 관리도",
          label_en: "Control Chart",
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
        attributeControlChartAnalysisResult={{
          ...analysisResultEnvelopeTestResponse("quality.attribute_control_chart"),
          warnings: [
            {
              code: "attribute_control_chart_phase_1_limits_estimated_from_data",
              severity: "info",
              message: "Phase I 중심선과 3-sigma 관리한계는 유효 관측에서 추정했습니다.",
            },
          ],
          result: attributeControlChartTestResult(),
        }}
        attributeControlChartConstantOpportunityConfirmed={false}
        attributeControlChartCountColumnId="column-a"
        attributeControlChartCountColumns={[columns[0]]}
        attributeControlChartDenominatorColumnId="column-b"
        attributeControlChartDenominatorColumns={[columns[1]]}
        attributeControlChartResult={attributeControlChartTestResult()}
        attributeControlChartType="p"
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("계수형 관리도 실행");
    expect(html).toContain("Phase I 기준선 추정");
    expect(html).toContain("Phase II 고정 한계 모니터링");
    expect(html).toContain("Phase I은 현재 데이터에서 기준선을 추정합니다");
    expect(html).toContain('role="radiogroup"');
    expect(html).toContain("P 관리도 실행");
    expect(html).toContain("불량품 수");
    expect(html).toContain("표본 크기");
    expect(html).toContain("가변 표본 크기 불량률");
    expect(html).toContain("Dispersion ratio");
    expect(html).toContain("관측별 한계");
    expect(html).toContain("한계 출처");
    expect(html).toContain("필터 후 유효 관측에서 추정");
    expect(html).toContain("관리한계 밖");
    expect(html).toContain("Phase I 중심선과 3-sigma 관리한계");
    expect(html).toContain("P 관리도. 중심선");
  });

  it("requires visible constant-opportunity confirmation for the C chart", () => {
    const columns = filterTestColumns();
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
          method_id: "quality.attribute_control_chart",
          method_version: "0.3.0",
          module_id: "quality",
          label_ko: "계수형 관리도",
          label_en: "Control Chart",
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
        attributeControlChartConstantOpportunityConfirmed={false}
        attributeControlChartCountColumnId="column-a"
        attributeControlChartCountColumns={[columns[0]]}
        attributeControlChartResult={null}
        attributeControlChartType="c"
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={{ ...datasetVersionTestResponse(), columns, column_count: columns.length }}
      />,
    );

    expect(html).toContain("모든 관측의 검사 기회가 동일함을 확인");
    expect(html).toContain("동일 검사 기회의 결점 수");
    expect(html).toContain("C 관리도 실행");
    expect(html).toContain("disabled");
  });

  it("renders verified Phase II limit-set selection and compatibility state", () => {
    const columns = filterTestColumns();
    const version = {
      ...datasetVersionTestResponse(),
      columns,
      column_count: columns.length,
    };
    const limitSet = attributeControlLimitSetTestResponse();
    const result: AttributeControlChartResult = {
      ...attributeControlChartTestResult(),
      schema_version: 3,
      phase: "phase_2",
      control_limit_method: "phase_2_frozen_three_sigma",
      baseline: "verified_immutable_limit_set",
      center_line: limitSet.frozen_center_line,
      n_total: 1,
      n_used: 1,
      dispersion: {
        available: false,
        method: "pearson_chi_square_over_degrees_of_freedom_against_frozen_center",
        degrees_of_freedom: 0,
        ratio: null,
        reason_code: "attribute_control_chart_dispersion_insufficient_points",
        warning_threshold: 2,
        used_to_adjust_limits: false,
      },
      chart: {
        ...attributeControlChartTestResult().chart,
        point_count: 1,
        points: attributeControlChartTestResult().chart.points.slice(0, 1),
      },
      limit_set_dependency: {
        limit_set_id: limitSet.limit_set_id,
        asset_schema_version: 1,
        asset_sha256: limitSet.asset_sha256,
        source_analysis_id: limitSet.source_analysis_id,
        source_method_version: limitSet.source_method_version,
        source_result_schema_version: limitSet.source_result_schema_version,
        source_dataset_version_id: limitSet.source_dataset_version_id,
        source_schema_hash: limitSet.source_schema_hash,
        source_canonical_sha256: limitSet.source_canonical_sha256,
        source_result_sha256: limitSet.source_result_sha256,
        baseline_closed_at: limitSet.closed_at,
        baseline_point_count: limitSet.baseline_point_count,
        frozen_center_line: limitSet.frozen_center_line,
        fixed_sample_size: null,
        calculation_policy: "phase_2_frozen_three_sigma_v1",
      },
    };
    const catalog = attributeControlCatalogTestResponse();
    const html = renderToString(
      <AnalysisPage
        {...analysisPageTestProps()}
        analysisCatalog={catalog}
        attributeControlChartCountColumnId="column-a"
        attributeControlChartCountColumns={[columns[0]]}
        attributeControlChartDenominatorColumnId="column-b"
        attributeControlChartDenominatorColumns={[columns[1]]}
        attributeControlChartPhase="phase_2"
        attributeControlChartResult={result}
        attributeControlChartType="p"
        attributeControlPhase2State={{
          deletion: null,
          deletionError: null,
          deletionPreflight: {
            preflight_schema_version: 1,
            limit_set_id: limitSet.limit_set_id,
            source_analysis_id: limitSet.source_analysis_id,
            method_id: "quality.attribute_control_chart",
            source_method_version: "0.3.0",
            deletion_ready: false,
            blockers: ["attribute_control_limit_set_deletion_phase_2_dependency"],
            counts: {
              limit_set_count: 1,
              asset_file_count: 1,
              asset_file_bytes: 2048,
              metadata_record_count: 1,
              dependent_phase_2_analysis_count: 1,
            },
            deletion_manifest_sha256: "f".repeat(64),
          },
          error: null,
          isDeleting: false,
          isLoading: false,
          isLoadingDeletionPreflight: false,
          limitSets: [limitSet],
          preflight: {
            schema_version: 2,
            method_id: "quality.attribute_control_chart",
            method_version: "0.3.0",
            phase: "phase_2",
            limit_set_id: limitSet.limit_set_id,
            limit_set_asset_sha256: limitSet.asset_sha256,
            target_dataset_version_id: version.version_id,
            target_schema_hash: version.schema_hash,
            target_canonical_sha256: "b".repeat(64),
            chart_type: "p",
            count_definition: "defectives",
            validation_scope: "schema_and_dependency_only",
            row_data_validated: false,
            ready: true,
            issues: [],
          },
          selectedLimitSet: limitSet,
          selectedLimitSetId: limitSet.limit_set_id,
          onClearDeletion: () => undefined,
          onDeleteLimitSet: () => undefined,
          onLoadDeletionPreflight: () => undefined,
          onSelectLimitSet: () => undefined,
        }}
        selectedMethod={catalog.methods[0]}
        selectedMethods={catalog.methods}
        selectedModuleId="quality"
        version={version}
      />,
    );

    expect(html).toContain("Phase II는 선택한 immutable limit set");
    expect(html).toContain("검증된 limit set");
    expect(html).toContain("기준선 종료");
    expect(html).toContain("검증된 immutable limit set");
    expect(html).toContain(
      "구조 호환성 확인 완료. 실제 행 값과 필터 결과는 실행 시 다시 검증됩니다.",
    );
    expect(html).toContain("사용 불가 · 관측점 부족");
    expect(html).not.toContain("호환성 확인 중");
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
    expect(html).toContain("normal capability");
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
    expect(html).toContain("막대 하나에 Tab으로 진입");
    expect(html).toContain("개별 outlier 값 없이");
    expect(html).toContain("A ECDF 1");
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
          method_version: "0.2.0",
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
    expect(html).toContain("AD p (근사)");
    expect(html).toContain("Stephens 정규성 근사값");
    expect(html).toContain('tabindex="0"');
    expect(html).toContain('tabindex="-1"');
  });

  it("labels an older normality result without the approximate AD p-value", () => {
    const legacyResult = normalityTestResult();
    delete legacyResult.columns[0].anderson_darling.p_value;

    expect(andersonPValueLabel(legacyResult.columns[0].anderson_darling)).toBe(
      "제공되지 않음 (legacy result)",
    );
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
    expect(html).toContain("여기를 클릭하고 Ctrl+V");
    expect(html).toContain("표 보기");
    expect(html).toContain("원문 보기");
    expect(html).toContain("작업 흐름");
  });

  it("renders a safe spreadsheet staging grid with ragged and empty-cell cues", () => {
    const preview = parsePastedTablePreview("이름\t메모\n홍길동\t<img src=x>\n김민수");
    const html = renderToString(
      <PastePreviewGrid
        hasHeaderPreview
        preview={preview}
        selection={{
          address: "B2",
          columnIndex: 1,
          rowIndex: 1,
          value: "<img src=x>",
        }}
        onCellSelect={() => undefined}
      />,
    );

    expect(html).toContain('role="grid"');
    expect(html).toContain(">A<");
    expect(html).toContain(">B<");
    expect(html).toContain("열 수 다름");
    expect(html).toContain("구조상 없음");
    expect(html).toContain("B2");
    expect(html).toContain("&lt;img src=x&gt;");
    expect(html).not.toContain("<img src=x>");
  });

  it("shows paste header-preview disagreement without overriding server parsing", () => {
    const upload = datasetUploadTestResponse();
    const html = renderToString(
      <DatasetPreparationPage
        {...datasetPageTestProps()}
        canConfirm
        parsingOptions={parsingSuggestionToConfirmation(upload)}
        pastedHeaderPreference
        upload={upload}
      />,
    );

    expect(html).toMatch(/붙여넣기 표시는 첫 행을 (?:<!-- -->)?헤더처럼/);
    expect(html).toMatch(/서버 제안은 (?:<!-- -->)?헤더 없음/);
    expect(html).toContain("아래 파싱 옵션이 최종 기준");
  });

  it("renders paged canonical preview controls, missing values, and inspector", () => {
    const version = datasetVersionTestResponse();
    const preview: DatasetRowsPreviewResponse = {
      version_id: version.version_id,
      offset: 0,
      limit: 25,
      total_rows: 3,
      returned_rows: 2,
      columns: version.columns,
      rows: [
        { row_index: 0, values: ["A", "긴 값 전체"] },
        { row_index: 1, values: ["B", null] },
      ],
    };
    const html = renderToString(
      <DatasetPreparationPage
        {...datasetPageTestProps()}
        preview={preview}
        previewLimit={25}
        version={version}
      />,
    );

    expect(html).toContain("Canonical 행 미리보기");
    expect(html).toContain("미리보기 페이지 크기");
    expect(html).toContain("이동할 행 번호");
    expect(html).toContain("전체");
    expect(html).toContain("결측");
    expect(html).toContain("선택 셀");
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
        analysisCatalog={analysisCatalog}
        currentDatasetVersionId={null}
        datasetPageProps={datasetPageTestProps()}
        routePage="dataset"
        onActivateDataset={() => undefined}
        onDatasetMetadataChanged={() => undefined}
        onOpenAnalysisMethod={() => undefined}
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
        analysisCatalog={analysisCatalog}
        currentDatasetVersionId="dataset-version-id"
        routePage="analysis"
        onActivateDataset={() => undefined}
        onDatasetMetadataChanged={() => undefined}
        onOpenAnalysisMethod={() => undefined}
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
    const version = datasetVersionTestResponse();
    const html = renderToString(
      <AppChrome
        activePage="dataset"
        activeDatasetSelectorProps={{
          catalogState: {
            activeItem: {
              version_id: version.version_id,
              dataset_id: version.dataset_id,
              original_filename: "sample.txt",
              version_number: version.version_number,
              row_count: version.row_count,
              column_count: version.column_count,
              created_at: version.created_at,
              user_label: null,
              note: null,
              pinned: false,
              metadata_updated_at: null,
            },
            catalog: {
              offset: 0,
              limit: 20,
              total: 1,
              returned: 1,
              has_previous: false,
              has_next: false,
              versions: [
                {
                  version_id: version.version_id,
                  dataset_id: version.dataset_id,
                  original_filename: "sample.txt",
                  version_number: version.version_number,
                  row_count: version.row_count,
                  column_count: version.column_count,
                  created_at: version.created_at,
                  user_label: null,
                  note: null,
                  pinned: false,
                  metadata_updated_at: null,
                },
              ],
            },
            error: null,
            isLoading: false,
            isResolvingActiveItem: false,
            onPageChange: () => undefined,
            onRefresh: () => undefined,
          },
          isSwitching: false,
          onRetrySwitch: () => undefined,
          onSelect: () => undefined,
          pendingVersionId: null,
          version,
        }}
        canOpenAnalysis={false}
        healthClassName="status-pill status-ready"
        healthLabel="API ok"
        onOpenAnalysisPage={() => undefined}
        onOpenDatasetPage={() => undefined}
        onOpenHelpPage={() => undefined}
        onOpenManagePage={() => undefined}
        onOpenReportsPage={() => undefined}
      >
        <div>Workspace child</div>
      </AppChrome>,
    );

    expect(html).toContain("DataLab Studio");
    expect(html).toContain("로컬 분석 작업대");
    expect(html).toContain("Gate A 기반 구성");
    expect(html).toContain("API ok");
    expect(html).toContain("현재 분석 데이터셋");
    expect(html).toContain("sample.txt");
    expect(html).toMatch(/1<\/span>/);
    expect(html).toMatch(/3(?:<!-- -->)?행/);
    expect(html).toMatch(/2(?:<!-- -->)?컬럼/);
    expect(html).toMatch(/schema (?:<!-- -->)?schema-hash/);
    expect(html).toContain("Workspace child");
    expect(html).toContain("리포트");
    expect(html).toContain("관리");
    expect(html).toContain("도움말");
  });

  it("renders the data and regression model management entry surface", () => {
    const html = renderToString(
      <ManageAssetsPage
        activeDatasetVersionId={null}
        onActivateDataset={() => undefined}
        onDatasetMetadataChanged={() => undefined}
      />,
    );

    expect(html).toContain("데이터·모델 관리");
    expect(html).toContain("데이터셋");
    expect(html).toContain("회귀모델");
    expect(html).toContain("목록 새로고침");
    expect(html).toContain("로컬 저장됨");
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

function analysisResultEnvelopeTestResponse(methodId = "eda.descriptive"): AnalysisResultEnvelope {
  return {
    analysis_id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    method_id: methodId,
    method_version: "0.1.0",
    dataset_version_id: "version-1",
    status: "succeeded",
    warnings: [],
    provenance: {
      method_id: methodId,
      method_version: "0.1.0",
      dataset_version_id: "version-1",
      source_schema_hash: "schema-hash",
      app_version: "0.1.0",
      python_version: "3.10.11",
      platform: "Windows-11",
      build_commit: "test",
      package_versions: {
        numpy: "2.2.6",
        scipy: "1.15.3",
      },
    },
    result: {
      schema_version: 1,
      summary_type: "ui_export_contract_test",
    },
  };
}

function analysisResultJsonExportTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisResultJsonExportResponse {
  return {
    schema_version: 1,
    export_id: "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    analysis_id: result.analysis_id,
    format: "analysis_result_json",
    artifact_kind: "analysis_result_json_export",
    media_type: "application/json",
    sha256: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
    size_bytes: 2048,
    source_result_sha256: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    stale: false,
    created_at: "2026-07-04T00:00:00Z",
    result,
  };
}

function analysisResultCsvExportTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisResultCsvExportResponse {
  return {
    schema_version: 1,
    export_id: "cccccccc-dddd-eeee-ffff-000000000000",
    analysis_id: result.analysis_id,
    format: "analysis_result_csv",
    artifact_kind: "analysis_result_csv_export",
    media_type: "text/csv",
    sha256: "123456abcdef7890123456abcdef7890123456abcdef7890123456abcdef7890",
    size_bytes: 4096,
    source_result_sha256: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    stale: false,
    created_at: "2026-07-04T00:00:00Z",
    columns: ["section", "path", "value"],
    row_count: 12,
    preview_rows: [
      ["analysis_id", "analysis_id", result.analysis_id],
      ["method_id", "method_id", result.method_id],
    ],
  };
}

function analysisResultHtmlReportTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisResultHtmlReportResponse {
  return {
    schema_version: 1,
    export_id: "dddddddd-eeee-ffff-0000-111111111111",
    analysis_id: result.analysis_id,
    format: "analysis_result_html_report",
    artifact_kind: "analysis_result_html_report",
    media_type: "text/html",
    sha256: "feedfacecafe7890feedfacecafe7890feedfacecafe7890feedfacecafe7890",
    size_bytes: 8192,
    source_result_sha256: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    stale: false,
    created_at: "2026-07-04T00:00:00Z",
    title: "DataLab Studio Analysis Report",
    section_count: 18,
  };
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

function analysisRunListTestResponse(result: AnalysisResultEnvelope): AnalysisRunListResponse {
  return {
    dataset_version_id: result.dataset_version_id,
    method_id: result.method_id,
    status: "succeeded",
    stale: true,
    result_available: true,
    limit: 20,
    offset: 0,
    returned_count: 1,
    has_more: false,
    runs: [
      {
        analysis_id: result.analysis_id,
        method_id: result.method_id,
        method_version: result.method_version,
        dataset_version_id: result.dataset_version_id,
        status: "succeeded",
        stale: true,
        result_available: true,
        artifact_count: 3,
        created_at: "2026-07-04T00:00:00Z",
        updated_at: "2026-07-04T00:00:01Z",
        completed_at: "2026-07-04T00:00:01Z",
      },
    ],
  };
}

function analysisRunDeletionPreflightTestResponse(): AnalysisRunDeletionPreflightResponse {
  return {
    preflight_schema_version: 1,
    analysis_id: "analysis-1",
    method_id: "eda.descriptive",
    method_version: "0.1.0",
    status: "succeeded",
    stale: false,
    deletion_ready: true,
    blockers: [],
    counts: {
      analysis_run_count: 1,
      analysis_artifact_count: 4,
      result_file_count: 1,
      artifact_file_count: 4,
      export_file_count: 3,
      total_file_count: 5,
      file_bytes: 2048,
      metadata_record_count: 5,
      regression_model_count: 0,
      regression_prediction_count: 0,
      attribute_control_limit_set_count: 0,
      job_reference_count: 0,
    },
    deletion_manifest_sha256: "d".repeat(64),
  };
}

function analysisResultExportListTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisResultExportListResponse {
  return {
    analysis_id: result.analysis_id,
    exports: [
      {
        export_id: "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
        analysis_id: result.analysis_id,
        artifact_kind: "analysis_result_json_export",
        media_type: "application/json",
        sha256: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        created_at: "2026-07-04T00:00:00Z",
        download_url: `/api/v1/analysis-runs/${result.analysis_id}/exports/bbbbbbbb-cccc-dddd-eeee-ffffffffffff/download`,
      },
      {
        export_id: "cccccccc-dddd-eeee-ffff-000000000000",
        analysis_id: result.analysis_id,
        artifact_kind: "analysis_result_csv_export",
        media_type: "text/csv",
        sha256: "123456abcdef7890123456abcdef7890123456abcdef7890123456abcdef7890",
        created_at: "2026-07-04T00:00:01Z",
        download_url: `/api/v1/analysis-runs/${result.analysis_id}/exports/cccccccc-dddd-eeee-ffff-000000000000/download`,
      },
    ],
  };
}

function analysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: result.method_id,
      method_version: result.method_version,
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: true,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: result.warnings.length,
      summary_type:
        typeof result.result?.summary_type === "string" ? result.result.summary_type : null,
      row_count_total: result.provenance.row_count_total ?? null,
      row_count_included: result.provenance.row_count_included ?? null,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: result.provenance.filter_snapshot_sha256 ?? null,
      row_snapshot_sha256: result.provenance.row_snapshot_sha256 ?? null,
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: result.method_id,
      method_version: result.method_version,
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type:
        typeof result.result?.summary_type === "string" ? result.result.summary_type : null,
      row_count_total: result.provenance.row_count_total ?? null,
      row_count_included: result.provenance.row_count_included ?? null,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: result.provenance.filter_snapshot_sha256 ?? null,
      row_snapshot_sha256: "3333333333333333333333333333333333333333333333333333333333333333",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
      {
        field: "stale",
        left: true,
        right: false,
      },
    ],
    method_specific: {
      descriptive_statistics: {
        summary_type: "descriptive_statistics",
        columns: [
          {
            column_id: "column-alpha",
            display_name: "alpha",
            metrics: [
              { metric: "n_used", left: 2, right: 1, delta: -1 },
              { metric: "mean", left: 1.5, right: 2, delta: 0.5 },
            ],
          },
        ],
        left_only_column_ids: [],
        right_only_column_ids: [],
      },
      one_sample_t_test: null,
      two_sample_t_test: null,
      paired_t_test: null,
      equivalence_tost: null,
      one_way_anova: null,
      kruskal_wallis: null,
    },
  };
}

function oneSampleTAnalysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: "hypothesis.one_sample_t",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: 0,
      summary_type: "one_sample_t_test",
      row_count_total: 4,
      row_count_included: 4,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: "hypothesis.one_sample_t",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type: "one_sample_t_test",
      row_count_total: 4,
      row_count_included: 4,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
    method_specific: {
      descriptive_statistics: null,
      one_sample_t_test: {
        summary_type: "one_sample_t_test",
        left_response_column_id: "column-alpha",
        right_response_column_id: "column-alpha",
        response_display_name: "response-alpha",
        same_response_column: true,
        settings: [
          { setting: "null_mean", left: 10, right: 10.25, same: false },
          { setting: "alpha", left: 0.05, right: 0.05, same: true },
        ],
        metrics: [
          { metric: "sample.mean", left: 10.5, right: 10.5, delta: 0 },
          { metric: "contrast.estimate", left: 0.5, right: 0.25, delta: -0.25 },
        ],
      },
      two_sample_t_test: null,
      paired_t_test: null,
      equivalence_tost: null,
      one_way_anova: null,
      kruskal_wallis: null,
    },
  };
}

function twoSampleTAnalysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: "hypothesis.two_sample_t",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: 0,
      summary_type: "two_sample_t_test",
      row_count_total: 4,
      row_count_included: 4,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: "hypothesis.two_sample_t",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type: "two_sample_t_test",
      row_count_total: 4,
      row_count_included: 4,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
    method_specific: {
      descriptive_statistics: null,
      one_sample_t_test: null,
      two_sample_t_test: {
        summary_type: "two_sample_t_test",
        left_response_column_id: "column-alpha",
        right_response_column_id: "column-alpha",
        response_display_name: "response-alpha",
        same_response_column: true,
        left_group_column_id: "column-beta",
        right_group_column_id: "column-beta",
        group_display_name: "group-beta",
        same_group_column: true,
        same_group_label_set: true,
        same_group_label_order: true,
        settings: [
          { setting: "null_difference", left: 0, right: -1, same: false },
          { setting: "variance_assumption", left: "welch", right: "welch", same: true },
        ],
        metrics: [
          { metric: "groups.0.mean", left: 1.5, right: 1.5, delta: 0 },
          { metric: "groups.1.mean", left: 4.5, right: 4.5, delta: 0 },
          { metric: "contrast.estimate", left: -3, right: -3, delta: 0 },
        ],
      },
      paired_t_test: null,
      equivalence_tost: null,
      one_way_anova: null,
      kruskal_wallis: null,
    },
  };
}

function pairedTAnalysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: "hypothesis.paired_t",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: 0,
      summary_type: "paired_t_test",
      row_count_total: 4,
      row_count_included: 4,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: "hypothesis.paired_t",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type: "paired_t_test",
      row_count_total: 4,
      row_count_included: 4,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
    method_specific: {
      descriptive_statistics: null,
      one_sample_t_test: null,
      two_sample_t_test: null,
      paired_t_test: {
        summary_type: "paired_t_test",
        left_before_column_id: "column-alpha",
        right_before_column_id: "column-alpha",
        before_display_name: "before-alpha",
        same_before_column: true,
        left_after_column_id: "column-beta",
        right_after_column_id: "column-beta",
        after_display_name: "after-beta",
        same_after_column: true,
        settings: [
          { setting: "null_difference", left: 0, right: 0.5, same: false },
          { setting: "difference_definition", left: "after_minus_before", right: "after_minus_before", same: true },
        ],
        metrics: [
          { metric: "paired_sample.mean_difference", left: 2, right: 2, delta: 0 },
          { metric: "contrast.estimate", left: 2, right: 1.5, delta: -0.5 },
        ],
      },
      equivalence_tost: null,
      one_way_anova: null,
      kruskal_wallis: null,
    },
  };
}

function equivalenceTostAnalysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: "hypothesis.equivalence_tost",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: 0,
      summary_type: "equivalence_tost",
      row_count_total: 6,
      row_count_included: 6,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: "hypothesis.equivalence_tost",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type: "equivalence_tost",
      row_count_total: 6,
      row_count_included: 6,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
    method_specific: {
      descriptive_statistics: null,
      one_sample_t_test: null,
      two_sample_t_test: null,
      paired_t_test: null,
      equivalence_tost: {
        summary_type: "equivalence_tost",
        left_response_column_id: "column-alpha",
        right_response_column_id: "column-alpha",
        response_display_name: "response-alpha",
        same_response_column: true,
        settings: [
          { setting: "equivalence_bounds.lower", left: -0.8, right: -0.25, same: false },
          { setting: "equivalence_bounds.upper", left: 0.8, right: 0.25, same: false },
          { setting: "tost.equivalent", left: true, right: false, same: false },
        ],
        metrics: [
          { metric: "estimate.value", left: -0.0833333333333339, right: -0.0833333333333339, delta: 0 },
          { metric: "tests.upper.p_value", left: 0.002505, right: 0.041, delta: 0.038495 },
        ],
      },
      one_way_anova: null,
      kruskal_wallis: null,
    },
  };
}

function oneWayAnovaAnalysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: "hypothesis.one_way_anova",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: 0,
      summary_type: "one_way_anova",
      row_count_total: 12,
      row_count_included: 12,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: "hypothesis.one_way_anova",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type: "one_way_anova",
      row_count_total: 12,
      row_count_included: 12,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
    method_specific: {
      descriptive_statistics: null,
      one_sample_t_test: null,
      two_sample_t_test: null,
      paired_t_test: null,
      equivalence_tost: null,
      one_way_anova: {
        summary_type: "one_way_anova",
        left_response_column_id: "column-alpha",
        right_response_column_id: "column-alpha",
        response_display_name: "response-alpha",
        same_response_column: true,
        left_group_column_id: "column-beta",
        right_group_column_id: "column-beta",
        group_display_name: "group-beta",
        same_group_column: true,
        same_group_label_set: true,
        same_group_label_order: true,
        settings: [
          { setting: "alpha", left: 0.05, right: 0.01, same: false },
          { setting: "posthoc.performed", left: true, right: true, same: true },
        ],
        metrics: [
          { metric: "groups.0.mean", left: 7.5, right: 7.5, delta: 0 },
          { metric: "groups.2.mean", left: 13.5, right: 13.5, delta: 0 },
          { metric: "test.f_statistic", left: 21.6, right: 21.6, delta: 0 },
          { metric: "posthoc.comparison_count", left: 3, right: 3, delta: 0 },
        ],
      },
      kruskal_wallis: null,
    },
  };
}

function kruskalWallisAnalysisRunComparisonTestResponse(
  result: AnalysisResultEnvelope,
): AnalysisRunComparisonResponse {
  return {
    left: {
      analysis_id: result.analysis_id,
      method_id: "hypothesis.kruskal_wallis",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "1111111111111111111111111111111111111111111111111111111111111111",
      warning_count: 0,
      summary_type: "kruskal_wallis_test",
      row_count_total: 9,
      row_count_included: 9,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      created_at: "2026-07-04T00:00:00Z",
      completed_at: "2026-07-04T00:00:01Z",
    },
    right: {
      analysis_id: "ffffffff-eeee-dddd-cccc-bbbbbbbbbbbb",
      method_id: "hypothesis.kruskal_wallis",
      method_version: "0.1.0",
      dataset_version_id: result.dataset_version_id,
      status: "succeeded",
      stale: false,
      result_sha256: "2222222222222222222222222222222222222222222222222222222222222222",
      warning_count: 0,
      summary_type: "kruskal_wallis_test",
      row_count_total: 9,
      row_count_included: 9,
      source_schema_hash: result.provenance.source_schema_hash ?? null,
      filter_snapshot_sha256: null,
      row_snapshot_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      created_at: "2026-07-04T00:02:00Z",
      completed_at: "2026-07-04T00:02:01Z",
    },
    comparable: true,
    compatibility: {
      same_method_id: true,
      same_method_version: true,
      same_dataset_version_id: true,
      same_summary_type: true,
    },
    differences: [
      {
        field: "result_sha256",
        left: "1111111111111111111111111111111111111111111111111111111111111111",
        right: "2222222222222222222222222222222222222222222222222222222222222222",
      },
    ],
    method_specific: {
      descriptive_statistics: null,
      one_sample_t_test: null,
      two_sample_t_test: null,
      paired_t_test: null,
      equivalence_tost: null,
      one_way_anova: null,
      kruskal_wallis: {
        summary_type: "kruskal_wallis_test",
        left_response_column_id: "column-alpha",
        right_response_column_id: "column-alpha",
        response_display_name: "response-alpha",
        same_response_column: true,
        left_group_column_id: "column-beta",
        right_group_column_id: "column-beta",
        group_display_name: "group-beta",
        same_group_column: true,
        same_group_label_set: true,
        same_group_label_order: true,
        settings: [
          { setting: "alpha", left: 0.05, right: 0.01, same: false },
          { setting: "posthoc.performed", left: true, right: false, same: false },
        ],
        metrics: [
          { metric: "groups.0.mean_rank", left: 2, right: 2, delta: 0 },
          { metric: "groups.2.mean_rank", left: 8, right: 8, delta: 0 },
          { metric: "test.h_statistic", left: 7.2, right: 7.2, delta: 0 },
          {
            metric: "test.effect_size.epsilon_squared",
            left: 0.8666666666666667,
            right: 0.8666666666666667,
            delta: 0,
          },
          { metric: "posthoc.comparison_count", left: 3, right: 0, delta: -3 },
        ],
      },
    },
  };
}

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
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

function responseSurfaceDesignTestResponse(status: string): ResponseSurfaceDesignResponse {
  return {
    design_id: "00000000-0000-4000-8000-000000000201",
    design_version_id: "00000000-0000-4000-8000-000000000211",
    version_number: 1,
    method_id: "doe.response_surface",
    method_version: "0.1.0",
    design_schema_version: 2,
    family: "central_composite",
    name: "RSM test design",
    status,
    created_at: "2026-07-15T00:00:00.000Z",
    updated_at: "2026-07-15T00:00:00.000Z",
    app_version: "0.1.0",
    factors: [
      { name: "Temperature", low: 60, high: 80, unit: "C" },
      { name: "Pressure", low: 5, high: 15, unit: "bar" },
    ],
    options: {
      alpha_mode: "face_centered",
      alpha: 1,
      factorial_replicates: 1,
      axial_replicates: 1,
      center_points: 1,
      randomize: false,
      randomization_seed: 1,
    },
    run_count: 1,
    design_sha256: "a".repeat(64),
    runs: [
      {
        standard_order: 1,
        run_order: 1,
        replicate_index: 1,
        point_type: "center",
        center_point: true,
        factor_levels: { Temperature: 70, Pressure: 10 },
        coded_levels: { Temperature: 0, Pressure: 0 },
      },
    ],
  };
}

function responseOptimizerAnalysisTestResponse(): DoeResponseSurfaceAnalysisResponse {
  return {
    analysis_id: "00000000-0000-4000-8000-000000000202",
    response_name: "Yield",
    result: {
      factor_names: ["Temperature", "Pressure"],
      sample: { parameter_count: 6, rank: 6, df_residual: 7 },
      fit: { residual_mean_square: 0.04, residual_standard_error: 0.2 },
      terms: [{ confidence_interval: { level: 0.95 } }],
      anova: {
        lack_of_fit: {
          available: true,
          lack_of_fit: { p_value: 0.4 },
        },
      },
      diagnostics: {
        high_cooks_distance_count: 0,
        high_leverage_count: 0,
        high_standardized_residual_count: 0,
        shapiro_wilk: { p_value: 0.5 },
      },
      contour: {
        points: [{ predicted: 80 }, { predicted: 95 }],
      },
    },
  } as unknown as DoeResponseSurfaceAnalysisResponse;
}

function factorialDesignTestResponse(): FactorialDesignResponse {
  return {
    design_id: "11111111-1111-4111-8111-111111111111",
    design_version_id: "22222222-2222-4222-8222-222222222222",
    version_number: 1,
    method_id: "doe.factorial_design",
    method_version: "0.3.0",
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

function factorialDesignResponsesTestResponse(): DoeDesignResponsesResponse {
  return {
    design_id: "11111111-1111-4111-8111-111111111111",
    design_version_id: "22222222-2222-4222-8222-222222222222",
    version_number: 1,
    status: "analyzed",
    responses: [
      {
        response_name: "Yield",
        unit: "kg",
        response_revision_id: "77777777-7777-4777-8777-777777777777",
        response_revision_number: 1,
        response_revision_schema_version: 1,
        response_revision_sha256: "a".repeat(64),
        created_at: "2026-07-15T00:00:00.000Z",
        closed_at: "2026-07-15T00:00:00.000Z",
        response_count: 5,
        values: [1, 2, 3, 4, 5].map((runOrder) => ({
          run_order: runOrder,
          value: 10 + runOrder,
        })),
      },
    ],
  };
}

function factorialAnalysisTestResponse(): DoeFactorialAnalysisResponse {
  const anovaRow = {
    df: 1,
    sum_squares: 8,
    mean_square: 8,
    f_statistic: 12,
    p_value: 0.04,
  };
  return {
    analysis_id: "factorial-analysis-id",
    design_id: "11111111-1111-4111-8111-111111111111",
    design_version_id: "22222222-2222-4222-8222-222222222222",
    design_version_number: 1,
    method_id: "doe.factorial_design",
    method_version: "0.3.0",
    analysis_schema_version: 2,
    design_sha256: "design-hash-012345678901234567890123456789012345678901234567890",
    response_revision_id: "77777777-7777-4777-8777-777777777777",
    response_revision_number: 1,
    response_revision_sha256:
      "response-hash-012345678901234567890123456789012345678901234567",
    response_sha256: "response-hash-012345678901234567890123456789012345678901234567",
    response_name: "Yield",
    created_at: "2026-07-14T00:00:00.000Z",
    app_version: "0.1.0",
    python_version: "3.10.11",
    platform: "Windows-11",
    build_commit: "test-build",
    package_versions: { numpy: "2.2.6", scipy: "1.15.3" },
    result: {
      schema_version: 1,
      summary_type: "factorial_analysis",
      method: "ordinary_least_squares_factorial_effects",
      response: { name: "Yield", unit: "kg" },
      factor_names: ["Temperature", "Pressure"],
      coding: {
        low: -1,
        high: 1,
        center: 0,
        effect_definition: "effect=2*coefficient",
      },
      model_policy: {
        hierarchy_enforced: true,
        max_interaction_order: 2,
        automatic_term_selection: false,
        center_curvature_included: true,
        block_fixed_effects_included: false,
        sum_of_squares: "partial_drop_one",
      },
      sample: {
        n_observations: 5,
        factorial_point_count: 4,
        center_point_count: 1,
        block_count: 1,
        parameter_count: 5,
        rank: 5,
        df_model: 4,
        df_residual: 0,
      },
      fit: {
        response_mean: 13,
        sse: 0,
        model_ss: 10,
        total_ss: 10,
        residual_mean_square: null,
        residual_standard_error: null,
        r_squared: 1,
        adjusted_r_squared: null,
        f_statistic: null,
        f_p_value: null,
      },
      terms: [
        {
          term_id: "intercept",
          label: "Intercept",
          kind: "intercept",
          factor_names: [],
          coefficient: 13,
          effect: null,
          standard_error: null,
          statistic: null,
          p_value: null,
          confidence_interval: null,
          effect_confidence_interval: null,
          partial_sum_squares: null,
          f_statistic: null,
          f_p_value: null,
        },
        {
          term_id: "factor_1",
          label: "Temperature",
          kind: "factorial",
          factor_names: ["Temperature"],
          coefficient: 2,
          effect: 4,
          standard_error: null,
          statistic: null,
          p_value: null,
          confidence_interval: null,
          effect_confidence_interval: null,
          partial_sum_squares: 8,
          f_statistic: null,
          f_p_value: null,
        },
        {
          term_id: "factor_2",
          label: "Pressure",
          kind: "factorial",
          factor_names: ["Pressure"],
          coefficient: -1,
          effect: -2,
          standard_error: null,
          statistic: null,
          p_value: null,
          confidence_interval: null,
          effect_confidence_interval: null,
          partial_sum_squares: 2,
          f_statistic: null,
          f_p_value: null,
        },
      ],
      ranked_effects: [
        { term_id: "factor_1", label: "Temperature", effect: 4, absolute_effect: 4 },
        { term_id: "factor_2", label: "Pressure", effect: -2, absolute_effect: 2 },
      ],
      anova: {
        sum_of_squares_policy: "partial_drop_one",
        model: { ...anovaRow, df: 4, sum_squares: 10, mean_square: 2.5 },
        residual: {
          df: 0,
          sum_squares: 0,
          mean_square: null,
          f_statistic: null,
          p_value: null,
        },
        total: {
          df: 4,
          sum_squares: 10,
          mean_square: null,
          f_statistic: null,
          p_value: null,
        },
        lack_of_fit: {
          available: false,
          unique_design_point_count: 5,
          pure_error: { ...anovaRow, df: 0, sum_squares: 0, mean_square: null },
          lack_of_fit: { ...anovaRow, df: 0, sum_squares: 0, mean_square: null },
          residual_df: 0,
        },
      },
      diagnostics: {
        residual_mean: 0,
        residual_min: 0,
        residual_max: 0,
        max_abs_standardized_residual: null,
        high_standardized_residual_count: 0,
        max_leverage: 1,
        high_leverage_threshold: 2,
        high_leverage_count: 0,
        max_cooks_distance: null,
        cooks_distance_threshold: 0.8,
        high_cooks_distance_count: 0,
        durbin_watson: null,
        shapiro_wilk: { statistic: null, p_value: null },
        point_limit: 256,
        points_truncated: false,
        points: [],
        qq_points: [],
      },
      plots: {
        main_effects: [
          { factor: "Temperature", low_mean: 11, high_mean: 15 },
          { factor: "Pressure", low_mean: 14, high_mean: 12 },
        ],
        interactions: [],
      },
      warnings: ["doe_factorial_model_saturated_no_inference"],
    },
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
    schema_version: 2,
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
          adjusted_statistic: 0.172314,
          p_value: 0.9342,
          p_value_method: "stephens_normal_unknown_mean_variance",
          p_value_is_approximate: true,
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
    pastedHeaderPreference: null,
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
    onPasteDataset: () => Promise.resolve(true),
    onPreviewLimitChange: () => undefined,
    onSaveSchema: () => undefined,
    onSchemaDraftChange: () => undefined,
    onUpload: () => undefined,
  };
}

function attributeControlCatalogTestResponse(): AnalysisMethodListResponse {
  return {
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
        method_id: "quality.attribute_control_chart",
        method_version: "0.3.0",
        module_id: "quality",
        label_ko: "계수형 관리도",
        label_en: "Control Chart",
        availability: "available",
        execution_mode: "inline",
        requires_dataset: true,
        order: 1,
        disabled_reason: null,
      },
    ],
  };
}

function attributeControlLimitSetTestResponse(): AttributeControlLimitSetResponse {
  return {
    asset_schema_version: 1,
    asset_sha256: "a".repeat(64),
    limit_set_id: "11111111-1111-4111-8111-111111111111",
    status: "closed",
    method_id: "quality.attribute_control_chart",
    source_method_version: "0.3.0",
    phase2_method_version: "0.3.0",
    source_result_schema_version: 3,
    source_analysis_id: "22222222-2222-4222-8222-222222222222",
    source_dataset_version_id: "33333333-3333-4333-8333-333333333333",
    source_schema_hash: "c".repeat(64),
    source_canonical_sha256: "d".repeat(64),
    source_config_sha256: "e".repeat(64),
    source_result_sha256: "f".repeat(64),
    filter_snapshot_sha256: "1".repeat(64),
    row_snapshot_sha256: "2".repeat(64),
    chart_type: "p",
    count_definition: "defectives",
    count: {
      column_id: "44444444-4444-4444-8444-444444444444",
      data_type: "integer",
      measurement_level: "count",
      role: "target",
      unit: null,
    },
    denominator: {
      column_id: "55555555-5555-4555-8555-555555555555",
      data_type: "integer",
      measurement_level: "count",
      role: "unspecified",
      unit: null,
    },
    denominator_role: "sample_size",
    baseline_point_count: 20,
    total_count: 100,
    total_denominator: 1000,
    frozen_center_line: 0.1,
    fixed_sample_size: null,
    constant_opportunity_confirmed: false,
    sigma_multiplier: 3,
    calculation_policy: "phase_2_frozen_three_sigma_v1",
    natural_bound_policy: "binomial_zero_one",
    eligibility: {
      eligible: true,
      policy: "phase_2_baseline_eligibility_v1",
      minimum_point_count: 20,
      checks_passed: [
        "minimum_point_count",
        "no_phase_1_limit_signals",
        "usable_normal_approximation",
        "pearson_dispersion_not_above_two",
        "complete_untruncated_point_payload",
      ],
    },
    creator_provenance: {
      app_version: "0.1.0",
      python_version: "3.10.11",
      platform: "Windows",
      build_commit: null,
      package_versions: {},
    },
    created_at: "2026-07-16T00:00:00Z",
    closed_at: "2026-07-16T00:00:00Z",
  };
}

function attributeControlChartTestResult(): AttributeControlChartResult {
  return {
    schema_version: 3,
    summary_type: "attribute_control_chart",
    method: "p_chart",
    chart_type: "p",
    count_definition: "defectives",
    distribution_assumption: "binomial",
    control_limit_method: "phase_1_estimated_three_sigma",
    baseline: "all_filtered_valid_points",
    order_source: "canonical_row_order",
    missing_policy: "complete_case",
    constant_opportunity_confirmed: false,
    control_rules: [
      {
        code: "attribute_control_chart_point_beyond_control_limits",
        definition: "one_point_strictly_outside_three_sigma_control_limits",
        enabled: true,
      },
    ],
    warnings: ["attribute_control_chart_limit_signal_detected"],
    count: {
      column_id: "column-a",
      column_index: 0,
      display_name: "Defectives",
      data_type: "integer",
      measurement_level: "count",
      role: "target",
      unit: null,
    },
    denominator: {
      column_id: "column-b",
      column_index: 1,
      display_name: "Sample size",
      data_type: "integer",
      measurement_level: "count",
      role: "unspecified",
      unit: null,
    },
    denominator_role: "sample_size",
    n_total: 2,
    n_used: 2,
    n_excluded_missing_count: 0,
    n_excluded_non_numeric_count: 0,
    n_excluded_missing_denominator: 0,
    n_excluded_non_numeric_denominator: 0,
    total_count: 11,
    total_denominator: 100,
    center_line: 0.11,
    limits_vary: false,
    lcl_truncated_count: 2,
    ucl_truncated_count: 0,
    dispersion: {
      available: true,
      method: "pearson_chi_square_over_degrees_of_freedom",
      degrees_of_freedom: 1,
      ratio: 2.3,
      reason_code: null,
      warning_threshold: 2,
      used_to_adjust_limits: false,
    },
    chart: {
      x_axis: "canonical_row_position",
      y_axis: "proportion_defective",
      center_line: 0.11,
      limits_vary: false,
      point_count: 2,
      points_truncated: false,
      point_limit: 1000,
      points: [
        {
          position: 1,
          canonical_position: 1,
          count: 1,
          denominator: 50,
          value: 0.02,
          lcl: 0,
          ucl: 0.2427,
          lcl_truncated: true,
          ucl_truncated: false,
          signal_codes: [],
        },
        {
          position: 2,
          canonical_position: 2,
          count: 10,
          denominator: 50,
          value: 0.2,
          lcl: 0,
          ucl: 0.18,
          lcl_truncated: true,
          ucl_truncated: false,
          signal_codes: ["attribute_control_chart_point_beyond_control_limits"],
        },
      ],
    },
    signals: [
      {
        signal_id: "attribute-p-2-limit",
        code: "attribute_control_chart_point_beyond_control_limits",
        severity: "warning",
        position: 2,
        canonical_position: 2,
        value: 0.2,
        limit: "upper",
        definition: "one_point_strictly_outside_three_sigma_control_limits",
      },
    ],
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
