import type { ComponentProps } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import App from "./App";
import { AnalysisPage } from "./AnalysisPage";
import { AnalysisWorkbench } from "./AnalysisWorkbench";
import { DatasetPreparationPage } from "./DatasetPreparationPage";
import type {
  AnalysisMethodListResponse,
  DatasetColumnResponse,
  DatasetUploadResponse,
  DatasetVersionResponse,
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
  });

  it("keeps planned Workbench methods non-executable", () => {
    const catalog = analysisTestCatalog();
    const selectedMethods = catalog.methods.filter((method) => method.module_id === "hypothesis");

    const html = renderToString(
      <AnalysisWorkbench
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
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
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
        selectedModuleId="exploration"
        version={version}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onNormalityAlphaChange={() => undefined}
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
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
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
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("그래프 요약");
    expect(html).toContain("그래프 요약 실행");
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
        analysisResult={null}
        descriptiveColumns={[columns[0]]}
        descriptiveResult={null}
        graphicalSummaryAnalysisResult={null}
        graphicalSummaryColumns={[columns[0]]}
        graphicalSummaryResult={null}
        isRunningAnalysis={false}
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
        selectedModuleId="exploration"
        version={datasetVersionTestResponse()}
        onAnalysisFilterDraftsChange={() => undefined}
        onRunDescriptiveAnalysis={() => undefined}
        onRunGraphicalSummaryAnalysis={() => undefined}
        onRunNormalityAnalysis={() => undefined}
        onSelectMethod={() => undefined}
        onNormalityAlphaChange={() => undefined}
        onToggleDescriptiveColumn={() => undefined}
        onToggleGraphicalSummaryColumn={() => undefined}
        onToggleNormalityColumn={() => undefined}
      />,
    );

    expect(html).toContain("정규성 검정");
    expect(html).toContain("정규성 검정 실행");
    expect(html).toContain("유의수준 alpha");
    expect(html).toContain("A");
  });

  it("renders the DatasetPreparationPage intake workflow", () => {
    const html = renderToString(<DatasetPreparationPage {...datasetPageTestProps()} />);

    expect(html).toContain("데이터셋 파싱 확정");
    expect(html).toContain("원본 데이터 파일");
    expect(html).toContain("복사한 표 붙여넣기");
    expect(html).toContain("작업 흐름");
  });

  it("routes the workspace between dataset preparation and analysis pages", () => {
    const datasetHtml = renderToString(
      <WorkspaceRouter
        analysisPageProps={analysisPageTestProps()}
        datasetPageProps={datasetPageTestProps()}
        flowError={null}
        isAnalysisPage={false}
      />,
    );
    const analysisHtml = renderToString(
      <WorkspaceRouter
        analysisPageProps={analysisPageTestProps()}
        datasetPageProps={datasetPageTestProps()}
        flowError="analysis_run_failed"
        isAnalysisPage
      />,
    );

    expect(datasetHtml).toContain("데이터셋 파싱 확정");
    expect(datasetHtml).not.toContain("분석 모듈");
    expect(analysisHtml).toContain("분석 모듈");
    expect(analysisHtml).toContain("오류 코드:");
    expect(analysisHtml).toContain("analysis_run_failed");
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

function analysisPageTestProps(): ComponentProps<typeof AnalysisPage> {
  return {
    analysisCatalog: null,
    analysisCatalogError: null,
    analysisFilterDrafts: [],
    analysisFilterValidationError: null,
    analysisFilterValidationMessage: null,
    analysisResult: null,
    descriptiveColumns: [],
    descriptiveResult: null,
    graphicalSummaryAnalysisResult: null,
    graphicalSummaryColumns: [],
    graphicalSummaryResult: null,
    isRunningAnalysis: false,
    normalityAlpha: 0.05,
    normalityAnalysisResult: null,
    normalityColumns: [],
    normalityResult: null,
    profile: null,
    selectedDescriptiveColumnIds: [],
    selectedGraphicalSummaryColumnIds: [],
    selectedNormalityColumnIds: [],
    selectedMethod: null,
    selectedMethods: [],
    selectedModuleId: "exploration",
    version: null,
    onAnalysisFilterDraftsChange: () => undefined,
    onRunDescriptiveAnalysis: () => undefined,
    onRunGraphicalSummaryAnalysis: () => undefined,
    onRunNormalityAnalysis: () => undefined,
    onSelectMethod: () => undefined,
    onNormalityAlphaChange: () => undefined,
    onToggleDescriptiveColumn: () => undefined,
    onToggleGraphicalSummaryColumn: () => undefined,
    onToggleNormalityColumn: () => undefined,
  };
}
