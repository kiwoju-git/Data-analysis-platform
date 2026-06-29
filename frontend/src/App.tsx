import { useEffect, useMemo, useState } from "react";

import "./App.css";
import {
  createAnalysisRun,
  fetchAnalysisMethods,
  fetchHealth,
  type AnalysisResultEnvelope,
  type AnalysisMethodListResponse,
  type AnalysisModuleId,
  type DatasetColumnResponse,
  type DescriptiveStatisticsResult,
  type GraphicalSummaryResult,
  type HealthResponse,
  type NormalityResult,
} from "./api";
import { AppChrome } from "./AppChrome";
import type { AnalysisShellProps } from "./AnalysisShell";
import {
  serializeAnalysisFilterDrafts,
  validateAnalysisFilterDrafts,
  type AnalysisFilterDraft,
} from "./analysisFilters";
import { useAnalysisSelection } from "./analysisSelection";
import { currentAppRoute } from "./appRoute";
import { useDatasetWorkflow } from "./useDatasetWorkflow";
import { WorkspaceRouter } from "./WorkspaceRouter";

type HealthState =
  | { kind: "checking" }
  | { kind: "ready"; response: HealthResponse }
  | { kind: "error"; message: string };

const numericDataTypes = new Set<DatasetColumnResponse["data_type"]>(["integer", "decimal"]);

function statusLabel(health: HealthState): string {
  if (health.kind === "ready") {
    return `API ${health.response.status}`;
  }
  if (health.kind === "error") {
    return health.message;
  }
  return "API 확인 중";
}

function statusClassName(health: HealthState): string {
  if (health.kind === "ready") {
    return "status-pill status-ready";
  }
  if (health.kind === "error") {
    return "status-pill status-error";
  }
  return "status-pill";
}

export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "checking" });
  const [analysisCatalog, setAnalysisCatalog] = useState<AnalysisMethodListResponse | null>(null);
  const [analysisCatalogError, setAnalysisCatalogError] = useState<string | null>(null);
  const {
    selectedMethod,
    selectedMethods,
    selectedModuleId,
    selectAnalysisMethod,
  } = useAnalysisSelection(analysisCatalog);
  const [selectedDescriptiveColumnIds, setSelectedDescriptiveColumnIds] = useState<string[]>([]);
  const [selectedGraphicalSummaryColumnIds, setSelectedGraphicalSummaryColumnIds] = useState<
    string[]
  >([]);
  const [selectedNormalityColumnIds, setSelectedNormalityColumnIds] = useState<string[]>([]);
  const [normalityAlpha, setNormalityAlpha] = useState(0.05);
  const [analysisFilterDrafts, setAnalysisFilterDrafts] = useState<AnalysisFilterDraft[]>([]);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResultEnvelope | null>(null);
  const [isRunningAnalysis, setIsRunningAnalysis] = useState(false);
  const [appRoute, setAppRoute] = useState(currentAppRoute);
  const {
    datasetPageProps,
    flowError,
    profile,
    setFlowError,
    version,
  } = useDatasetWorkflow({
    onDatasetReset: () => {
      setSelectedDescriptiveColumnIds([]);
      setSelectedGraphicalSummaryColumnIds([]);
      setSelectedNormalityColumnIds([]);
      setAnalysisFilterDrafts([]);
      setAnalysisResult(null);
    },
    onDatasetColumnsChanged: (columns) => {
      setSelectedDescriptiveColumnIds(defaultDescriptiveColumnIds(columns));
      setSelectedGraphicalSummaryColumnIds(defaultGraphicalSummaryColumnIds(columns));
      setSelectedNormalityColumnIds(defaultNormalityColumnIds(columns));
      setAnalysisFilterDrafts([]);
      setAnalysisResult(null);
    },
    onSchemaChanged: (columns) => {
      setSelectedDescriptiveColumnIds(defaultDescriptiveColumnIds(columns));
      setSelectedGraphicalSummaryColumnIds(defaultGraphicalSummaryColumnIds(columns));
      setSelectedNormalityColumnIds(defaultNormalityColumnIds(columns));
      setAnalysisResult(null);
    },
  });

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((response) => {
        setHealth({ kind: "ready", response });
      })
      .catch(() => {
        setHealth({
          kind: "error",
          message: "API 연결 필요",
        });
      });

    fetchAnalysisMethods(controller.signal)
      .then((response) => {
        setAnalysisCatalog(response);
        setAnalysisCatalogError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setAnalysisCatalogError("analysis_methods_failed");
        }
      });

    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    function handleRouteChange() {
      setAppRoute(currentAppRoute());
    }

    window.addEventListener("popstate", handleRouteChange);
    window.addEventListener("hashchange", handleRouteChange);
    return () => {
      window.removeEventListener("popstate", handleRouteChange);
      window.removeEventListener("hashchange", handleRouteChange);
    };
  }, []);

  const descriptiveColumns = useMemo(
    () => (version === null ? [] : selectableDescriptiveColumns(version.columns)),
    [version],
  );
  const graphicalSummaryColumns = useMemo(
    () => (version === null ? [] : selectableGraphicalSummaryColumns(version.columns)),
    [version],
  );
  const normalityColumns = useMemo(
    () => (version === null ? [] : selectableNormalityColumns(version.columns)),
    [version],
  );

  const descriptiveAnalysisResult =
    analysisResult?.method_id === "eda.descriptive" ? analysisResult : null;
  const graphicalSummaryAnalysisResult =
    analysisResult?.method_id === "eda.graphical_summary" ? analysisResult : null;
  const normalityAnalysisResult =
    analysisResult?.method_id === "eda.normality" ? analysisResult : null;
  const descriptiveResult = isDescriptiveStatisticsResult(descriptiveAnalysisResult?.result)
    ? descriptiveAnalysisResult.result
    : null;
  const graphicalSummaryResult = isGraphicalSummaryResult(
    graphicalSummaryAnalysisResult?.result,
  )
    ? graphicalSummaryAnalysisResult.result
    : null;
  const normalityResult = isNormalityResult(normalityAnalysisResult?.result)
    ? normalityAnalysisResult.result
    : null;

  const analysisFilterValidationError = useMemo(
    () =>
      version === null
        ? null
        : validateAnalysisFilterDrafts(analysisFilterDrafts, version.columns),
    [analysisFilterDrafts, version],
  );
  const analysisFilterValidationMessage =
    analysisFilterValidationError === null
      ? null
      : filterValidationMessage(analysisFilterValidationError);

  function handleAnalysisFilterDraftsChange(drafts: AnalysisFilterDraft[]) {
    setAnalysisFilterDrafts(drafts);
    setAnalysisResult(null);
  }

  function handleToggleDescriptiveColumn(columnId: string, checked: boolean) {
    setSelectedDescriptiveColumnIds((current) =>
      checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId),
    );
    setAnalysisResult(null);
  }

  function handleToggleGraphicalSummaryColumn(columnId: string, checked: boolean) {
    setSelectedGraphicalSummaryColumnIds((current) =>
      checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId),
    );
    setAnalysisResult(null);
  }

  function handleToggleNormalityColumn(columnId: string, checked: boolean) {
    setSelectedNormalityColumnIds((current) =>
      checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId),
    );
    setAnalysisResult(null);
  }

  function handleNormalityAlphaChange(alpha: number) {
    setNormalityAlpha(alpha);
    setAnalysisResult(null);
  }

  async function handleRunDescriptiveAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "eda.descriptive" ||
      selectedDescriptiveColumnIds.length === 0
    ) {
      setFlowError("descriptive_columns_required");
      return;
    }
    if (analysisFilterValidationError !== null) {
      setFlowError(analysisFilterValidationError);
      return;
    }

    setIsRunningAnalysis(true);
    setFlowError(null);
    try {
      const filterConditions = serializeAnalysisFilterDrafts(
        analysisFilterDrafts,
        version.columns,
      );
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles: {},
        options: {
          column_ids: selectedDescriptiveColumnIds,
          missing_policy: "available_case_by_column",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunGraphicalSummaryAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "eda.graphical_summary" ||
      selectedGraphicalSummaryColumnIds.length === 0
    ) {
      setFlowError("graphical_summary_columns_required");
      return;
    }
    if (analysisFilterValidationError !== null) {
      setFlowError(analysisFilterValidationError);
      return;
    }

    setIsRunningAnalysis(true);
    setFlowError(null);
    try {
      const filterConditions = serializeAnalysisFilterDrafts(
        analysisFilterDrafts,
        version.columns,
      );
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles: {},
        options: {
          column_ids: selectedGraphicalSummaryColumnIds,
          point_limit: 1000,
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunNormalityAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "eda.normality" ||
      selectedNormalityColumnIds.length === 0
    ) {
      setFlowError("normality_columns_required");
      return;
    }
    if (normalityAlpha <= 0 || normalityAlpha >= 1) {
      setFlowError("invalid_normality_alpha");
      return;
    }
    if (analysisFilterValidationError !== null) {
      setFlowError(analysisFilterValidationError);
      return;
    }

    setIsRunningAnalysis(true);
    setFlowError(null);
    try {
      const filterConditions = serializeAnalysisFilterDrafts(
        analysisFilterDrafts,
        version.columns,
      );
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles: {},
        options: {
          column_ids: selectedNormalityColumnIds,
          alpha: normalityAlpha,
          missing_policy: "available_case_by_column",
          include_qq_points: true,
          qq_point_limit: 1000,
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  function handleOpenDatasetPage() {
    if (typeof window !== "undefined") {
      window.history.pushState(null, "", "/");
    }
    setAppRoute({
      page: "dataset",
    });
  }

  function handleSelectAnalysisMethod(moduleId: AnalysisModuleId, methodId: string | null) {
    selectAnalysisMethod(moduleId, methodId);
    if (methodId !== null) {
      setAppRoute({
        page: "analysis",
        selection: {
          moduleId,
          methodId,
        },
      });
    }
  }

  function handleOpenAnalysisPage() {
    const method = selectedMethod ?? selectedMethods[0] ?? analysisCatalog?.methods[0] ?? null;
    if (method === null) {
      return;
    }
    handleSelectAnalysisMethod(method.module_id, method.method_id);
  }

  const isAnalysisPage = appRoute.page === "analysis";
  const analysisPageProps = {
    analysisCatalog,
    analysisCatalogError,
    analysisFilterDrafts,
    analysisFilterValidationError,
    analysisFilterValidationMessage,
    analysisResult: descriptiveAnalysisResult,
    descriptiveColumns,
    descriptiveResult,
    graphicalSummaryAnalysisResult,
    graphicalSummaryColumns,
    graphicalSummaryResult,
    isRunningAnalysis,
    normalityAlpha,
    normalityAnalysisResult,
    normalityColumns,
    normalityResult,
    profile,
    selectedDescriptiveColumnIds,
    selectedGraphicalSummaryColumnIds,
    selectedNormalityColumnIds,
    selectedMethod,
    selectedMethods,
    selectedModuleId,
    version,
    onAnalysisFilterDraftsChange: handleAnalysisFilterDraftsChange,
    onRunDescriptiveAnalysis: () => {
      void handleRunDescriptiveAnalysis();
    },
    onRunGraphicalSummaryAnalysis: () => {
      void handleRunGraphicalSummaryAnalysis();
    },
    onRunNormalityAnalysis: () => {
      void handleRunNormalityAnalysis();
    },
    onSelectMethod: handleSelectAnalysisMethod,
    onNormalityAlphaChange: handleNormalityAlphaChange,
    onToggleDescriptiveColumn: handleToggleDescriptiveColumn,
    onToggleGraphicalSummaryColumn: handleToggleGraphicalSummaryColumn,
    onToggleNormalityColumn: handleToggleNormalityColumn,
  } satisfies AnalysisShellProps;
  return (
    <AppChrome
      canOpenAnalysis={selectedMethod !== null || analysisCatalog !== null}
      healthClassName={statusClassName(health)}
      healthLabel={statusLabel(health)}
      isAnalysisPage={isAnalysisPage}
      version={version}
      onOpenAnalysisPage={handleOpenAnalysisPage}
      onOpenDatasetPage={handleOpenDatasetPage}
    >
      <WorkspaceRouter
        analysisPageProps={analysisPageProps}
        datasetPageProps={datasetPageProps}
        flowError={flowError}
        isAnalysisPage={isAnalysisPage}
      />
    </AppChrome>
  );
}

function selectableDescriptiveColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      numericDataTypes.has(column.data_type) &&
      column.role !== "id" &&
      column.measurement_level !== "id",
  );
}

function defaultDescriptiveColumnIds(columns: DatasetColumnResponse[]): string[] {
  return selectableDescriptiveColumns(columns).map((column) => column.column_id);
}

function selectableGraphicalSummaryColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function defaultGraphicalSummaryColumnIds(columns: DatasetColumnResponse[]): string[] {
  return selectableGraphicalSummaryColumns(columns)
    .slice(0, 20)
    .map((column) => column.column_id);
}

function selectableNormalityColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function defaultNormalityColumnIds(columns: DatasetColumnResponse[]): string[] {
  return selectableNormalityColumns(columns)
    .slice(0, 20)
    .map((column) => column.column_id);
}

function isDescriptiveStatisticsResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is DescriptiveStatisticsResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "descriptive_statistics" &&
    Array.isArray(candidate.columns)
  );
}

function isGraphicalSummaryResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is GraphicalSummaryResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return candidate.summary_type === "graphical_summary" && Array.isArray(candidate.columns);
}

function isNormalityResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is NormalityResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return candidate.summary_type === "normality_test" && Array.isArray(candidate.columns);
}

function filterValidationMessage(code: string): string {
  if (code === "filter_column_not_found") {
    return "필터 컬럼을 찾을 수 없습니다.";
  }
  if (code === "filter_operator_not_supported_for_column") {
    return "선택한 컬럼에는 해당 필터 조건을 사용할 수 없습니다.";
  }
  if (code === "filter_value_required") {
    return "필터 조건 값을 입력하세요.";
  }
  return code;
}
