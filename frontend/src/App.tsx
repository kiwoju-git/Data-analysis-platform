import { useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import {
  createAnalysisRun,
  createFactorialDesign,
  fetchAnalysisMethods,
  fetchGageRrPreflight,
  fetchHealth,
  fetchRegressionPredictions,
  fetchRegressionPredictionPreflight,
  fetchRegressionPredictionRows,
  saveFactorialDesignResponses,
  type AnalysisResultEnvelope,
  type AnalysisMethodListResponse,
  type AnalysisModuleId,
  type CapabilityResult,
  type ChiSquareAssociationResult,
  type DatasetColumnResponse,
  type DescriptiveStatisticsResult,
  type EqualVariancesResult,
  type EquivalenceTostResult,
  type FactorialDesignCreateRequest,
  type FactorialDesignResponse,
  type DoeDesignResponsesResponse,
  type DoeDesignResponsesUpsertRequest,
  type GageRrPreflightResponse,
  type GageRrResult,
  type GageRunChartResult,
  type GraphicalSummaryResult,
  type HealthResponse,
  type IndividualsChartResult,
  type KruskalWallisResult,
  type LinearModelResult,
  type MannWhitneyResult,
  type NormalityResult,
  type OneProportionResult,
  type OneWayAnovaResult,
  type OneSampleTResult,
  type OneSampleWilcoxonResult,
  type PairedTResult,
  type PearsonCorrelationResult,
  type RegressionPredictionPreflightResponse,
  type RegressionPredictionResponse,
  type RegressionPredictionRowsPageResponse,
  type RunChartResult,
  type SubgroupChartResult,
  type TwoSampleTResult,
  type TwoProportionResult,
  type XyCorrelationResult,
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
import { createLatestRequestGuard } from "./latestRequest";
import { useAnalysisComparisonState } from "./useAnalysisComparisonState";
import { useAnalysisExportState } from "./useAnalysisExportState";
import { useAnalysisHistoryState } from "./useAnalysisHistoryState";
import { useDatasetWorkflow } from "./useDatasetWorkflow";
import { useRestoredAnalysisResultState } from "./useRestoredAnalysisResultState";
import { useRegressionPredictionTargetState } from "./useRegressionPredictionTargetState";
import { useRegressionPredictionExportState } from "./useRegressionPredictionExportState";
import { WorkspaceRouter } from "./WorkspaceRouter";

type HealthState =
  | { kind: "checking" }
  | { kind: "ready"; response: HealthResponse }
  | { kind: "error"; message: string };

type SubgroupChartType = "xbar_r" | "xbar_s";

const numericDataTypes = new Set<DatasetColumnResponse["data_type"]>(["integer", "decimal"]);
const linearModelPredictionPageSize = 25;

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
  const [selectedEqualVariancesResponseColumnId, setSelectedEqualVariancesResponseColumnId] =
    useState<string | null>(null);
  const [selectedEqualVariancesGroupColumnId, setSelectedEqualVariancesGroupColumnId] =
    useState<string | null>(null);
  const [equalVariancesAlpha, setEqualVariancesAlpha] = useState(0.05);
  const [selectedOneSampleTResponseColumnId, setSelectedOneSampleTResponseColumnId] = useState<
    string | null
  >(null);
  const [oneSampleTNullMean, setOneSampleTNullMean] = useState(0);
  const [oneSampleTAlpha, setOneSampleTAlpha] = useState(0.05);
  const [oneSampleTConfidenceLevel, setOneSampleTConfidenceLevel] = useState(0.95);
  const [oneSampleTAlternative, setOneSampleTAlternative] = useState("two_sided");
  const [selectedEquivalenceTostResponseColumnId, setSelectedEquivalenceTostResponseColumnId] =
    useState<string | null>(null);
  const [equivalenceTostReferenceMean, setEquivalenceTostReferenceMean] = useState(0);
  const [equivalenceTostLowerBound, setEquivalenceTostLowerBound] = useState(-1);
  const [equivalenceTostUpperBound, setEquivalenceTostUpperBound] = useState(1);
  const [equivalenceTostAlpha, setEquivalenceTostAlpha] = useState(0.05);
  const [selectedPairedTBeforeColumnId, setSelectedPairedTBeforeColumnId] = useState<
    string | null
  >(null);
  const [selectedPairedTAfterColumnId, setSelectedPairedTAfterColumnId] = useState<string | null>(
    null,
  );
  const [pairedTNullDifference, setPairedTNullDifference] = useState(0);
  const [pairedTAlpha, setPairedTAlpha] = useState(0.05);
  const [pairedTConfidenceLevel, setPairedTConfidenceLevel] = useState(0.95);
  const [pairedTAlternative, setPairedTAlternative] = useState("two_sided");
  const [selectedOneSampleWilcoxonResponseColumnId, setSelectedOneSampleWilcoxonResponseColumnId] =
    useState<string | null>(null);
  const [oneSampleWilcoxonNullLocation, setOneSampleWilcoxonNullLocation] = useState(0);
  const [oneSampleWilcoxonAlpha, setOneSampleWilcoxonAlpha] = useState(0.05);
  const [oneSampleWilcoxonAlternative, setOneSampleWilcoxonAlternative] = useState("two_sided");
  const [oneSampleWilcoxonMethod, setOneSampleWilcoxonMethod] = useState("auto");
  const [oneSampleWilcoxonZeroMethod, setOneSampleWilcoxonZeroMethod] = useState("wilcox");
  const [selectedTwoSampleTResponseColumnId, setSelectedTwoSampleTResponseColumnId] =
    useState<string | null>(null);
  const [selectedTwoSampleTGroupColumnId, setSelectedTwoSampleTGroupColumnId] = useState<
    string | null
  >(null);
  const [twoSampleTAlpha, setTwoSampleTAlpha] = useState(0.05);
  const [twoSampleTConfidenceLevel, setTwoSampleTConfidenceLevel] = useState(0.95);
  const [twoSampleTAlternative, setTwoSampleTAlternative] = useState("two_sided");
  const [twoSampleTVarianceAssumption, setTwoSampleTVarianceAssumption] = useState("welch");
  const [selectedMannWhitneyResponseColumnId, setSelectedMannWhitneyResponseColumnId] =
    useState<string | null>(null);
  const [selectedMannWhitneyGroupColumnId, setSelectedMannWhitneyGroupColumnId] = useState<
    string | null
  >(null);
  const [mannWhitneyAlpha, setMannWhitneyAlpha] = useState(0.05);
  const [mannWhitneyAlternative, setMannWhitneyAlternative] = useState("two_sided");
  const [mannWhitneyMethod, setMannWhitneyMethod] = useState("auto");
  const [selectedKruskalWallisResponseColumnId, setSelectedKruskalWallisResponseColumnId] =
    useState<string | null>(null);
  const [selectedKruskalWallisGroupColumnId, setSelectedKruskalWallisGroupColumnId] = useState<
    string | null
  >(null);
  const [kruskalWallisAlpha, setKruskalWallisAlpha] = useState(0.05);
  const [selectedOneWayAnovaResponseColumnId, setSelectedOneWayAnovaResponseColumnId] =
    useState<string | null>(null);
  const [selectedOneWayAnovaGroupColumnId, setSelectedOneWayAnovaGroupColumnId] = useState<
    string | null
  >(null);
  const [oneWayAnovaAlpha, setOneWayAnovaAlpha] = useState(0.05);
  const [oneWayAnovaConfidenceLevel, setOneWayAnovaConfidenceLevel] = useState(0.95);
  const [selectedOneProportionResponseColumnId, setSelectedOneProportionResponseColumnId] =
    useState<string | null>(null);
  const [oneProportionEventLevel, setOneProportionEventLevel] = useState("");
  const [oneProportionNullProportion, setOneProportionNullProportion] = useState(0.5);
  const [oneProportionAlpha, setOneProportionAlpha] = useState(0.05);
  const [oneProportionConfidenceLevel, setOneProportionConfidenceLevel] = useState(0.95);
  const [oneProportionAlternative, setOneProportionAlternative] = useState("two_sided");
  const [oneProportionCiMethod, setOneProportionCiMethod] = useState("wilson");
  const [selectedTwoProportionResponseColumnId, setSelectedTwoProportionResponseColumnId] =
    useState<string | null>(null);
  const [selectedTwoProportionGroupColumnId, setSelectedTwoProportionGroupColumnId] = useState<
    string | null
  >(null);
  const [twoProportionEventLevel, setTwoProportionEventLevel] = useState("");
  const [twoProportionAlpha, setTwoProportionAlpha] = useState(0.05);
  const [twoProportionConfidenceLevel, setTwoProportionConfidenceLevel] = useState(0.95);
  const [twoProportionAlternative, setTwoProportionAlternative] = useState("two_sided");
  const [selectedChiSquareAssociationRowColumnId, setSelectedChiSquareAssociationRowColumnId] =
    useState<string | null>(null);
  const [
    selectedChiSquareAssociationColumnColumnId,
    setSelectedChiSquareAssociationColumnColumnId,
  ] = useState<string | null>(null);
  const [chiSquareAssociationAlpha, setChiSquareAssociationAlpha] = useState(0.05);
  const [selectedPearsonXColumnId, setSelectedPearsonXColumnId] = useState<string | null>(null);
  const [selectedPearsonYColumnId, setSelectedPearsonYColumnId] = useState<string | null>(null);
  const [pearsonAlpha, setPearsonAlpha] = useState(0.05);
  const [pearsonConfidenceLevel, setPearsonConfidenceLevel] = useState(0.95);
  const [selectedXyCorrelationXColumnIds, setSelectedXyCorrelationXColumnIds] = useState<
    string[]
  >([]);
  const [selectedXyCorrelationYColumnIds, setSelectedXyCorrelationYColumnIds] = useState<
    string[]
  >([]);
  const [xyCorrelationAlpha, setXyCorrelationAlpha] = useState(0.05);
  const [xyCorrelationConfidenceLevel, setXyCorrelationConfidenceLevel] = useState(0.95);
  const [selectedIndividualsChartValueColumnId, setSelectedIndividualsChartValueColumnId] =
    useState<string | null>(null);
  const [selectedIndividualsChartOrderColumnId, setSelectedIndividualsChartOrderColumnId] =
    useState<string | null>(null);
  const [selectedSubgroupChartValueColumnId, setSelectedSubgroupChartValueColumnId] = useState<
    string | null
  >(null);
  const [selectedSubgroupChartSubgroupColumnId, setSelectedSubgroupChartSubgroupColumnId] =
    useState<string | null>(null);
  const [selectedSubgroupChartType, setSelectedSubgroupChartType] =
    useState<SubgroupChartType>("xbar_r");
  const [selectedRunChartValueColumnId, setSelectedRunChartValueColumnId] = useState<
    string | null
  >(null);
  const [selectedRunChartOrderColumnId, setSelectedRunChartOrderColumnId] = useState<
    string | null
  >(null);
  const [selectedCapabilityValueColumnId, setSelectedCapabilityValueColumnId] = useState<
    string | null
  >(null);
  const [capabilityLsl, setCapabilityLsl] = useState("");
  const [capabilityUsl, setCapabilityUsl] = useState("");
  const [capabilityTarget, setCapabilityTarget] = useState("");
  const [selectedGageRrMeasurementColumnId, setSelectedGageRrMeasurementColumnId] = useState<
    string | null
  >(null);
  const [selectedGageRrPartColumnId, setSelectedGageRrPartColumnId] = useState<string | null>(
    null,
  );
  const [selectedGageRrOperatorColumnId, setSelectedGageRrOperatorColumnId] = useState<
    string | null
  >(null);
  const [selectedGageRrReplicateColumnId, setSelectedGageRrReplicateColumnId] = useState<
    string | null
  >(null);
  const [selectedGageRunChartOrderColumnId, setSelectedGageRunChartOrderColumnId] =
    useState<string | null>(null);
  const [gageRrPreflight, setGageRrPreflight] = useState<GageRrPreflightResponse | null>(
    null,
  );
  const [gageRrPreflightError, setGageRrPreflightError] = useState<string | null>(null);
  const [selectedLinearModelResponseColumnId, setSelectedLinearModelResponseColumnId] = useState<
    string | null
  >(null);
  const [selectedLinearModelPredictorColumnIds, setSelectedLinearModelPredictorColumnIds] =
    useState<string[]>([]);
  const [
    selectedLinearModelQuadraticColumnIds,
    setSelectedLinearModelQuadraticColumnIds,
  ] = useState<string[]>([]);
  const [selectedLinearModelInteractionKeys, setSelectedLinearModelInteractionKeys] = useState<
    string[]
  >([]);
  const [linearModelAlpha, setLinearModelAlpha] = useState(0.05);
  const [linearModelConfidenceLevel, setLinearModelConfidenceLevel] = useState(0.95);
  const [
    linearModelPredictionPreflight,
    setLinearModelPredictionPreflight,
  ] = useState<RegressionPredictionPreflightResponse | null>(null);
  const [linearModelPredictionPreflightError, setLinearModelPredictionPreflightError] =
    useState<string | null>(null);
  const [isRunningLinearModelPredictionPreflight, setIsRunningLinearModelPredictionPreflight] =
    useState(false);
  const linearModelPredictionPreflightRequest = useRef(createLatestRequestGuard()).current;
  const [linearModelPrediction, setLinearModelPrediction] =
    useState<RegressionPredictionResponse | null>(null);
  const [linearModelPredictionError, setLinearModelPredictionError] = useState<string | null>(null);
  const [isRunningLinearModelPrediction, setIsRunningLinearModelPrediction] = useState(false);
  const linearModelPredictionRequest = useRef(createLatestRequestGuard()).current;
  const [linearModelPredictionRowsPage, setLinearModelPredictionRowsPage] =
    useState<RegressionPredictionRowsPageResponse | null>(null);
  const [linearModelPredictionRowsError, setLinearModelPredictionRowsError] =
    useState<string | null>(null);
  const [isLoadingLinearModelPredictionRows, setIsLoadingLinearModelPredictionRows] =
    useState(false);
  const linearModelPredictionRowsRequest = useRef(createLatestRequestGuard()).current;
  const linearModelPredictionExportState = useRegressionPredictionExportState(
    linearModelPrediction?.prediction_id ?? null,
  );
  const [analysisFilterDrafts, setAnalysisFilterDrafts] = useState<AnalysisFilterDraft[]>([]);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResultEnvelope | null>(null);
  const [datasetStateRevision, setDatasetStateRevision] = useState(0);
  const [isRunningAnalysis, setIsRunningAnalysis] = useState(false);
  const [factorialDesign, setFactorialDesign] = useState<FactorialDesignResponse | null>(null);
  const [factorialDesignError, setFactorialDesignError] = useState<string | null>(null);
  const [isCreatingFactorialDesign, setIsCreatingFactorialDesign] = useState(false);
  const [factorialDesignResponses, setFactorialDesignResponses] =
    useState<DoeDesignResponsesResponse | null>(null);
  const [factorialDesignResponseError, setFactorialDesignResponseError] = useState<string | null>(
    null,
  );
  const [isSavingFactorialDesignResponses, setIsSavingFactorialDesignResponses] = useState(false);
  const [appRoute, setAppRoute] = useState(currentAppRoute);
  const {
    datasetPageProps,
    flowError,
    profile,
    setFlowError,
    version,
  } = useDatasetWorkflow({
    onDatasetReset: () => {
      setDatasetStateRevision((revision) => revision + 1);
      setSelectedDescriptiveColumnIds([]);
      setSelectedGraphicalSummaryColumnIds([]);
      setSelectedNormalityColumnIds([]);
      setSelectedEqualVariancesResponseColumnId(null);
      setSelectedEqualVariancesGroupColumnId(null);
      setSelectedOneSampleTResponseColumnId(null);
      setSelectedEquivalenceTostResponseColumnId(null);
      setSelectedPairedTBeforeColumnId(null);
      setSelectedPairedTAfterColumnId(null);
      setSelectedOneSampleWilcoxonResponseColumnId(null);
      setSelectedTwoSampleTResponseColumnId(null);
      setSelectedTwoSampleTGroupColumnId(null);
      setSelectedMannWhitneyResponseColumnId(null);
      setSelectedMannWhitneyGroupColumnId(null);
      setSelectedKruskalWallisResponseColumnId(null);
      setSelectedKruskalWallisGroupColumnId(null);
      setSelectedOneWayAnovaResponseColumnId(null);
      setSelectedOneWayAnovaGroupColumnId(null);
      setSelectedOneProportionResponseColumnId(null);
      setOneProportionEventLevel("");
      setSelectedTwoProportionResponseColumnId(null);
      setSelectedTwoProportionGroupColumnId(null);
      setTwoProportionEventLevel("");
      setSelectedChiSquareAssociationRowColumnId(null);
      setSelectedChiSquareAssociationColumnColumnId(null);
      setSelectedPearsonXColumnId(null);
      setSelectedPearsonYColumnId(null);
      setSelectedXyCorrelationXColumnIds([]);
      setSelectedXyCorrelationYColumnIds([]);
      setSelectedLinearModelResponseColumnId(null);
      setSelectedLinearModelPredictorColumnIds([]);
      setSelectedLinearModelQuadraticColumnIds([]);
      setSelectedLinearModelInteractionKeys([]);
      setAnalysisFilterDrafts([]);
      setAnalysisResult(null);
    },
    onDatasetColumnsChanged: (columns) => {
      setSelectedDescriptiveColumnIds(defaultDescriptiveColumnIds(columns));
      setSelectedGraphicalSummaryColumnIds(defaultGraphicalSummaryColumnIds(columns));
      setSelectedNormalityColumnIds(defaultNormalityColumnIds(columns));
      const responseColumnId = defaultEqualVariancesResponseColumnId(columns);
      setSelectedEqualVariancesResponseColumnId(responseColumnId);
      setSelectedEqualVariancesGroupColumnId(
        defaultEqualVariancesGroupColumnId(columns, responseColumnId),
      );
      setSelectedOneSampleTResponseColumnId(defaultOneSampleTResponseColumnId(columns));
      setSelectedEquivalenceTostResponseColumnId(defaultEquivalenceTostResponseColumnId(columns));
      const pairedTBeforeColumnId = defaultPairedTBeforeColumnId(columns);
      setSelectedPairedTBeforeColumnId(pairedTBeforeColumnId);
      setSelectedPairedTAfterColumnId(defaultPairedTAfterColumnId(columns, pairedTBeforeColumnId));
      setSelectedOneSampleWilcoxonResponseColumnId(
        defaultOneSampleWilcoxonResponseColumnId(columns),
      );
      const twoSampleResponseColumnId = defaultTwoSampleTResponseColumnId(columns);
      setSelectedTwoSampleTResponseColumnId(twoSampleResponseColumnId);
      setSelectedTwoSampleTGroupColumnId(
        defaultTwoSampleTGroupColumnId(columns, twoSampleResponseColumnId),
      );
      const mannWhitneyResponseColumnId = defaultMannWhitneyResponseColumnId(columns);
      setSelectedMannWhitneyResponseColumnId(mannWhitneyResponseColumnId);
      setSelectedMannWhitneyGroupColumnId(
        defaultMannWhitneyGroupColumnId(columns, mannWhitneyResponseColumnId),
      );
      const kruskalWallisResponseColumnId = defaultKruskalWallisResponseColumnId(columns);
      setSelectedKruskalWallisResponseColumnId(kruskalWallisResponseColumnId);
      setSelectedKruskalWallisGroupColumnId(
        defaultKruskalWallisGroupColumnId(columns, kruskalWallisResponseColumnId),
      );
      const oneWayAnovaResponseColumnId = defaultOneWayAnovaResponseColumnId(columns);
      setSelectedOneWayAnovaResponseColumnId(oneWayAnovaResponseColumnId);
      setSelectedOneWayAnovaGroupColumnId(
        defaultOneWayAnovaGroupColumnId(columns, oneWayAnovaResponseColumnId),
      );
      setSelectedOneProportionResponseColumnId(defaultOneProportionResponseColumnId(columns));
      setOneProportionEventLevel("");
      const twoProportionResponseColumnId = defaultTwoProportionResponseColumnId(columns);
      setSelectedTwoProportionResponseColumnId(twoProportionResponseColumnId);
      setSelectedTwoProportionGroupColumnId(
        defaultTwoProportionGroupColumnId(columns, twoProportionResponseColumnId),
      );
      setTwoProportionEventLevel("");
      const chiSquareRowColumnId = defaultChiSquareAssociationRowColumnId(columns);
      setSelectedChiSquareAssociationRowColumnId(chiSquareRowColumnId);
      setSelectedChiSquareAssociationColumnColumnId(
        defaultChiSquareAssociationColumnColumnId(columns, chiSquareRowColumnId),
      );
      const pearsonXColumnId = defaultPearsonXColumnId(columns);
      setSelectedPearsonXColumnId(pearsonXColumnId);
      setSelectedPearsonYColumnId(defaultPearsonYColumnId(columns, pearsonXColumnId));
      setSelectedXyCorrelationXColumnIds(defaultXyCorrelationXColumnIds(columns));
      setSelectedXyCorrelationYColumnIds(defaultXyCorrelationYColumnIds(columns));
      setSelectedIndividualsChartValueColumnId(defaultIndividualsChartValueColumnId(columns));
      setSelectedIndividualsChartOrderColumnId(null);
      const subgroupChartValueColumnId = defaultSubgroupChartValueColumnId(columns);
      setSelectedSubgroupChartValueColumnId(subgroupChartValueColumnId);
      setSelectedSubgroupChartSubgroupColumnId(
        defaultSubgroupChartSubgroupColumnId(columns, subgroupChartValueColumnId),
      );
      setSelectedSubgroupChartType("xbar_r");
      setSelectedRunChartValueColumnId(defaultRunChartValueColumnId(columns));
      setSelectedRunChartOrderColumnId(null);
      setSelectedCapabilityValueColumnId(defaultCapabilityValueColumnId(columns));
      setCapabilityLsl("");
      setCapabilityUsl("");
      setCapabilityTarget("");
      resetGageRrSelection(columns);
      const linearModelResponseColumnId = defaultLinearModelResponseColumnId(columns);
      setSelectedLinearModelResponseColumnId(linearModelResponseColumnId);
      setSelectedLinearModelPredictorColumnIds(
        defaultLinearModelPredictorColumnIds(columns, linearModelResponseColumnId),
      );
      setSelectedLinearModelQuadraticColumnIds([]);
      setSelectedLinearModelInteractionKeys([]);
      setAnalysisFilterDrafts([]);
      setAnalysisResult(null);
    },
    onSchemaChanged: (columns) => {
      setDatasetStateRevision((revision) => revision + 1);
      setSelectedDescriptiveColumnIds(defaultDescriptiveColumnIds(columns));
      setSelectedGraphicalSummaryColumnIds(defaultGraphicalSummaryColumnIds(columns));
      setSelectedNormalityColumnIds(defaultNormalityColumnIds(columns));
      const responseColumnId = defaultEqualVariancesResponseColumnId(columns);
      setSelectedEqualVariancesResponseColumnId(responseColumnId);
      setSelectedEqualVariancesGroupColumnId(
        defaultEqualVariancesGroupColumnId(columns, responseColumnId),
      );
      setSelectedOneSampleTResponseColumnId(defaultOneSampleTResponseColumnId(columns));
      setSelectedEquivalenceTostResponseColumnId(defaultEquivalenceTostResponseColumnId(columns));
      const pairedTBeforeColumnId = defaultPairedTBeforeColumnId(columns);
      setSelectedPairedTBeforeColumnId(pairedTBeforeColumnId);
      setSelectedPairedTAfterColumnId(defaultPairedTAfterColumnId(columns, pairedTBeforeColumnId));
      setSelectedOneSampleWilcoxonResponseColumnId(
        defaultOneSampleWilcoxonResponseColumnId(columns),
      );
      const twoSampleResponseColumnId = defaultTwoSampleTResponseColumnId(columns);
      setSelectedTwoSampleTResponseColumnId(twoSampleResponseColumnId);
      setSelectedTwoSampleTGroupColumnId(
        defaultTwoSampleTGroupColumnId(columns, twoSampleResponseColumnId),
      );
      const mannWhitneyResponseColumnId = defaultMannWhitneyResponseColumnId(columns);
      setSelectedMannWhitneyResponseColumnId(mannWhitneyResponseColumnId);
      setSelectedMannWhitneyGroupColumnId(
        defaultMannWhitneyGroupColumnId(columns, mannWhitneyResponseColumnId),
      );
      const kruskalWallisResponseColumnId = defaultKruskalWallisResponseColumnId(columns);
      setSelectedKruskalWallisResponseColumnId(kruskalWallisResponseColumnId);
      setSelectedKruskalWallisGroupColumnId(
        defaultKruskalWallisGroupColumnId(columns, kruskalWallisResponseColumnId),
      );
      const oneWayAnovaResponseColumnId = defaultOneWayAnovaResponseColumnId(columns);
      setSelectedOneWayAnovaResponseColumnId(oneWayAnovaResponseColumnId);
      setSelectedOneWayAnovaGroupColumnId(
        defaultOneWayAnovaGroupColumnId(columns, oneWayAnovaResponseColumnId),
      );
      setSelectedOneProportionResponseColumnId(defaultOneProportionResponseColumnId(columns));
      setOneProportionEventLevel("");
      const twoProportionResponseColumnId = defaultTwoProportionResponseColumnId(columns);
      setSelectedTwoProportionResponseColumnId(twoProportionResponseColumnId);
      setSelectedTwoProportionGroupColumnId(
        defaultTwoProportionGroupColumnId(columns, twoProportionResponseColumnId),
      );
      setTwoProportionEventLevel("");
      const chiSquareRowColumnId = defaultChiSquareAssociationRowColumnId(columns);
      setSelectedChiSquareAssociationRowColumnId(chiSquareRowColumnId);
      setSelectedChiSquareAssociationColumnColumnId(
        defaultChiSquareAssociationColumnColumnId(columns, chiSquareRowColumnId),
      );
      const pearsonXColumnId = defaultPearsonXColumnId(columns);
      setSelectedPearsonXColumnId(pearsonXColumnId);
      setSelectedPearsonYColumnId(defaultPearsonYColumnId(columns, pearsonXColumnId));
      setSelectedXyCorrelationXColumnIds(defaultXyCorrelationXColumnIds(columns));
      setSelectedXyCorrelationYColumnIds(defaultXyCorrelationYColumnIds(columns));
      setSelectedIndividualsChartValueColumnId(defaultIndividualsChartValueColumnId(columns));
      setSelectedIndividualsChartOrderColumnId(null);
      const subgroupChartValueColumnId = defaultSubgroupChartValueColumnId(columns);
      setSelectedSubgroupChartValueColumnId(subgroupChartValueColumnId);
      setSelectedSubgroupChartSubgroupColumnId(
        defaultSubgroupChartSubgroupColumnId(columns, subgroupChartValueColumnId),
      );
      setSelectedSubgroupChartType("xbar_r");
      setSelectedRunChartValueColumnId(defaultRunChartValueColumnId(columns));
      setSelectedRunChartOrderColumnId(null);
      setSelectedCapabilityValueColumnId(defaultCapabilityValueColumnId(columns));
      setCapabilityLsl("");
      setCapabilityUsl("");
      setCapabilityTarget("");
      resetGageRrSelection(columns);
      const linearModelResponseColumnId = defaultLinearModelResponseColumnId(columns);
      setSelectedLinearModelResponseColumnId(linearModelResponseColumnId);
      setSelectedLinearModelPredictorColumnIds(
        defaultLinearModelPredictorColumnIds(columns, linearModelResponseColumnId),
      );
      setSelectedLinearModelQuadraticColumnIds([]);
      setSelectedLinearModelInteractionKeys([]);
      setAnalysisResult(null);
    },
  });
  const currentAnalysisId = analysisResult?.analysis_id ?? null;
  const currentDatasetVersionId = version?.version_id ?? null;
  const analysisExportState = useAnalysisExportState({
    currentAnalysisId,
    currentDatasetVersionId,
    resetKey: datasetStateRevision,
  });
  const analysisHistoryState = useAnalysisHistoryState({
    currentDatasetVersionId,
    refreshKey: currentAnalysisId,
    resetKey: datasetStateRevision,
  });
  const analysisComparisonState = useAnalysisComparisonState({
    resetKey: datasetStateRevision,
  });
  const restoredAnalysisResultState = useRestoredAnalysisResultState({
    analysisCatalog,
    currentAnalysisId,
    currentDatasetVersionId,
    onRefreshAnalysisResultExports: analysisExportState.onRefreshAnalysisResultExports,
    onSelectMethod: handleSelectAnalysisMethod,
    resetKey: datasetStateRevision,
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
  const equalVariancesResponseColumns = useMemo(
    () => (version === null ? [] : selectableEqualVariancesResponseColumns(version.columns)),
    [version],
  );
  const equalVariancesGroupColumns = useMemo(
    () => (version === null ? [] : selectableEqualVariancesGroupColumns(version.columns)),
    [version],
  );
  const oneSampleTResponseColumns = useMemo(
    () => (version === null ? [] : selectableOneSampleTResponseColumns(version.columns)),
    [version],
  );
  const equivalenceTostResponseColumns = useMemo(
    () => (version === null ? [] : selectableEquivalenceTostResponseColumns(version.columns)),
    [version],
  );
  const pairedTBeforeColumns = useMemo(
    () => (version === null ? [] : selectablePairedTColumns(version.columns)),
    [version],
  );
  const pairedTAfterColumns = useMemo(
    () => (version === null ? [] : selectablePairedTColumns(version.columns)),
    [version],
  );
  const oneSampleWilcoxonResponseColumns = useMemo(
    () => (version === null ? [] : selectableOneSampleWilcoxonResponseColumns(version.columns)),
    [version],
  );
  const twoSampleTResponseColumns = useMemo(
    () => (version === null ? [] : selectableTwoSampleTResponseColumns(version.columns)),
    [version],
  );
  const twoSampleTGroupColumns = useMemo(
    () => (version === null ? [] : selectableTwoSampleTGroupColumns(version.columns)),
    [version],
  );
  const mannWhitneyResponseColumns = useMemo(
    () => (version === null ? [] : selectableMannWhitneyResponseColumns(version.columns)),
    [version],
  );
  const mannWhitneyGroupColumns = useMemo(
    () => (version === null ? [] : selectableMannWhitneyGroupColumns(version.columns)),
    [version],
  );
  const kruskalWallisResponseColumns = useMemo(
    () => (version === null ? [] : selectableKruskalWallisResponseColumns(version.columns)),
    [version],
  );
  const kruskalWallisGroupColumns = useMemo(
    () => (version === null ? [] : selectableKruskalWallisGroupColumns(version.columns)),
    [version],
  );
  const oneWayAnovaResponseColumns = useMemo(
    () => (version === null ? [] : selectableOneWayAnovaResponseColumns(version.columns)),
    [version],
  );
  const oneWayAnovaGroupColumns = useMemo(
    () => (version === null ? [] : selectableOneWayAnovaGroupColumns(version.columns)),
    [version],
  );
  const oneProportionResponseColumns = useMemo(
    () => (version === null ? [] : selectableOneProportionResponseColumns(version.columns)),
    [version],
  );
  const twoProportionResponseColumns = useMemo(
    () => (version === null ? [] : selectableTwoProportionResponseColumns(version.columns)),
    [version],
  );
  const twoProportionGroupColumns = useMemo(
    () => (version === null ? [] : selectableTwoProportionGroupColumns(version.columns)),
    [version],
  );
  const chiSquareAssociationRowColumns = useMemo(
    () => (version === null ? [] : selectableChiSquareAssociationColumns(version.columns)),
    [version],
  );
  const chiSquareAssociationColumnColumns = useMemo(
    () => (version === null ? [] : selectableChiSquareAssociationColumns(version.columns)),
    [version],
  );
  const pearsonXColumns = useMemo(
    () => (version === null ? [] : selectablePearsonColumns(version.columns)),
    [version],
  );
  const pearsonYColumns = useMemo(
    () => (version === null ? [] : selectablePearsonColumns(version.columns)),
    [version],
  );
  const xyCorrelationXColumns = useMemo(
    () => (version === null ? [] : selectableXyCorrelationColumns(version.columns)),
    [version],
  );
  const xyCorrelationYColumns = useMemo(
    () => (version === null ? [] : selectableXyCorrelationColumns(version.columns)),
    [version],
  );
  const individualsChartValueColumns = useMemo(
    () => (version === null ? [] : selectableIndividualsChartValueColumns(version.columns)),
    [version],
  );
  const individualsChartOrderColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableIndividualsChartOrderColumns(
            version.columns,
            selectedIndividualsChartValueColumnId,
          ),
    [selectedIndividualsChartValueColumnId, version],
  );
  const subgroupChartValueColumns = useMemo(
    () => (version === null ? [] : selectableSubgroupChartValueColumns(version.columns)),
    [version],
  );
  const subgroupChartSubgroupColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableSubgroupChartSubgroupColumns(
            version.columns,
            selectedSubgroupChartValueColumnId,
          ),
    [selectedSubgroupChartValueColumnId, version],
  );
  const runChartValueColumns = useMemo(
    () => (version === null ? [] : selectableRunChartValueColumns(version.columns)),
    [version],
  );
  const runChartOrderColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableRunChartOrderColumns(version.columns, selectedRunChartValueColumnId),
    [selectedRunChartValueColumnId, version],
  );
  const capabilityValueColumns = useMemo(
    () => (version === null ? [] : selectableCapabilityValueColumns(version.columns)),
    [version],
  );
  const gageRrMeasurementColumns = useMemo(
    () => (version === null ? [] : selectableGageRrMeasurementColumns(version.columns)),
    [version],
  );
  const gageRrPartColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableGageRrIdentifierColumns(version.columns, selectedGageRrMeasurementColumnId),
    [selectedGageRrMeasurementColumnId, version],
  );
  const gageRrOperatorColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableGageRrIdentifierColumns(version.columns, selectedGageRrMeasurementColumnId),
    [selectedGageRrMeasurementColumnId, version],
  );
  const gageRrReplicateColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableGageRrIdentifierColumns(version.columns, selectedGageRrMeasurementColumnId),
    [selectedGageRrMeasurementColumnId, version],
  );
  const gageRunChartOrderColumns = useMemo(
    () =>
      version === null
        ? []
        : selectableGageRunChartOrderColumns(version.columns, {
            measurementColumnId: selectedGageRrMeasurementColumnId,
            partColumnId: selectedGageRrPartColumnId,
            operatorColumnId: selectedGageRrOperatorColumnId,
            replicateColumnId: selectedGageRrReplicateColumnId,
          }),
    [
      selectedGageRrMeasurementColumnId,
      selectedGageRrOperatorColumnId,
      selectedGageRrPartColumnId,
      selectedGageRrReplicateColumnId,
      version,
    ],
  );
  const linearModelResponseColumns = useMemo(
    () => (version === null ? [] : selectableLinearModelResponseColumns(version.columns)),
    [version],
  );
  const linearModelPredictorColumns = useMemo(
    () => (version === null ? [] : selectableLinearModelPredictorColumns(version.columns)),
    [version],
  );

  const descriptiveAnalysisResult =
    analysisResult?.method_id === "eda.descriptive" ? analysisResult : null;
  const graphicalSummaryAnalysisResult =
    analysisResult?.method_id === "eda.graphical_summary" ? analysisResult : null;
  const normalityAnalysisResult =
    analysisResult?.method_id === "eda.normality" ? analysisResult : null;
  const equalVariancesAnalysisResult =
    analysisResult?.method_id === "eda.equal_variances" ? analysisResult : null;
  const oneSampleTAnalysisResult =
    analysisResult?.method_id === "hypothesis.one_sample_t" ? analysisResult : null;
  const equivalenceTostAnalysisResult =
    analysisResult?.method_id === "hypothesis.equivalence_tost" ? analysisResult : null;
  const pairedTAnalysisResult =
    analysisResult?.method_id === "hypothesis.paired_t" ? analysisResult : null;
  const oneSampleWilcoxonAnalysisResult =
    analysisResult?.method_id === "hypothesis.one_sample_wilcoxon" ? analysisResult : null;
  const twoSampleTAnalysisResult =
    analysisResult?.method_id === "hypothesis.two_sample_t" ? analysisResult : null;
  const mannWhitneyAnalysisResult =
    analysisResult?.method_id === "hypothesis.mann_whitney" ? analysisResult : null;
  const kruskalWallisAnalysisResult =
    analysisResult?.method_id === "hypothesis.kruskal_wallis" ? analysisResult : null;
  const oneWayAnovaAnalysisResult =
    analysisResult?.method_id === "hypothesis.one_way_anova" ? analysisResult : null;
  const oneProportionAnalysisResult =
    analysisResult?.method_id === "categorical.one_proportion" ? analysisResult : null;
  const twoProportionAnalysisResult =
    analysisResult?.method_id === "categorical.two_proportion" ? analysisResult : null;
  const chiSquareAssociationAnalysisResult =
    analysisResult?.method_id === "categorical.chi_square_association" ? analysisResult : null;
  const pearsonAnalysisResult =
    analysisResult?.method_id === "regression.pearson" ? analysisResult : null;
  const xyCorrelationAnalysisResult =
    analysisResult?.method_id === "regression.xy_correlation" ? analysisResult : null;
  const linearModelAnalysisResult =
    analysisResult?.method_id === "regression.linear_model" ? analysisResult : null;
  const individualsChartAnalysisResult =
    analysisResult?.method_id === "quality.individuals_chart" ? analysisResult : null;
  const subgroupChartAnalysisResult =
    analysisResult?.method_id === "quality.subgroup_chart" ? analysisResult : null;
  const runChartAnalysisResult =
    analysisResult?.method_id === "quality.run_chart" ? analysisResult : null;
  const capabilityAnalysisResult =
    analysisResult?.method_id === "quality.capability" ? analysisResult : null;
  const gageRrAnalysisResult =
    analysisResult?.method_id === "quality.gage_rr" ? analysisResult : null;
  const gageRunChartAnalysisResult =
    analysisResult?.method_id === "quality.gage_run_chart" ? analysisResult : null;
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
  const equalVariancesResult = isEqualVariancesResult(equalVariancesAnalysisResult?.result)
    ? equalVariancesAnalysisResult.result
    : null;
  const oneSampleTResult = isOneSampleTResult(oneSampleTAnalysisResult?.result)
    ? oneSampleTAnalysisResult.result
    : null;
  const equivalenceTostResult = isEquivalenceTostResult(
    equivalenceTostAnalysisResult?.result,
  )
    ? equivalenceTostAnalysisResult.result
    : null;
  const pairedTResult = isPairedTResult(pairedTAnalysisResult?.result)
    ? pairedTAnalysisResult.result
    : null;
  const oneSampleWilcoxonResult = isOneSampleWilcoxonResult(
    oneSampleWilcoxonAnalysisResult?.result,
  )
    ? oneSampleWilcoxonAnalysisResult.result
    : null;
  const twoSampleTResult = isTwoSampleTResult(twoSampleTAnalysisResult?.result)
    ? twoSampleTAnalysisResult.result
    : null;
  const mannWhitneyResult = isMannWhitneyResult(mannWhitneyAnalysisResult?.result)
    ? mannWhitneyAnalysisResult.result
    : null;
  const kruskalWallisResult = isKruskalWallisResult(kruskalWallisAnalysisResult?.result)
    ? kruskalWallisAnalysisResult.result
    : null;
  const oneWayAnovaResult = isOneWayAnovaResult(oneWayAnovaAnalysisResult?.result)
    ? oneWayAnovaAnalysisResult.result
    : null;
  const oneProportionResult = isOneProportionResult(oneProportionAnalysisResult?.result)
    ? oneProportionAnalysisResult.result
    : null;
  const twoProportionResult = isTwoProportionResult(twoProportionAnalysisResult?.result)
    ? twoProportionAnalysisResult.result
    : null;
  const chiSquareAssociationResult = isChiSquareAssociationResult(
    chiSquareAssociationAnalysisResult?.result,
  )
    ? chiSquareAssociationAnalysisResult.result
    : null;
  const pearsonResult = isPearsonCorrelationResult(pearsonAnalysisResult?.result)
    ? pearsonAnalysisResult.result
    : null;
  const xyCorrelationResult = isXyCorrelationResult(xyCorrelationAnalysisResult?.result)
    ? xyCorrelationAnalysisResult.result
    : null;
  const linearModelResult = isLinearModelResult(linearModelAnalysisResult?.result)
    ? linearModelAnalysisResult.result
    : null;
  const individualsChartResult = isIndividualsChartResult(individualsChartAnalysisResult?.result)
    ? individualsChartAnalysisResult.result
    : null;
  const subgroupChartResult = isSubgroupChartResult(subgroupChartAnalysisResult?.result)
    ? subgroupChartAnalysisResult.result
    : null;
  const runChartResult = isRunChartResult(runChartAnalysisResult?.result)
    ? runChartAnalysisResult.result
    : null;
  const capabilityResult = isCapabilityResult(capabilityAnalysisResult?.result)
    ? capabilityAnalysisResult.result
    : null;
  const gageRrResult = isGageRrResult(gageRrAnalysisResult?.result)
    ? gageRrAnalysisResult.result
    : null;
  const gageRunChartResult = isGageRunChartResult(gageRunChartAnalysisResult?.result)
    ? gageRunChartAnalysisResult.result
    : null;
  const activeLinearModelModelId = linearModelResult?.model_manifest?.model_id ?? null;
  const linearModelPredictionTargetState = useRegressionPredictionTargetState({
    activeModelId: activeLinearModelModelId,
    currentVersionId: version?.version_id ?? null,
  });
  const linearModelPredictionTargetVersionId =
    linearModelPredictionTargetState.selectedTargetVersionId;

  useEffect(() => {
    linearModelPredictionPreflightRequest.cancel();
    linearModelPredictionRequest.cancel();
    linearModelPredictionRowsRequest.cancel();
    setLinearModelPredictionPreflight(null);
    setLinearModelPredictionPreflightError(null);
    setLinearModelPrediction(null);
    setLinearModelPredictionError(null);
    setLinearModelPredictionRowsPage(null);
    setLinearModelPredictionRowsError(null);
    setIsRunningLinearModelPredictionPreflight(false);
    setIsRunningLinearModelPrediction(false);
    setIsLoadingLinearModelPredictionRows(false);
  }, [
    activeLinearModelModelId,
    linearModelPredictionPreflightRequest,
    linearModelPredictionRequest,
    linearModelPredictionRowsRequest,
    linearModelPredictionTargetVersionId,
    version?.version_id,
  ]);

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

  async function handleCreateFactorialDesign(request: FactorialDesignCreateRequest) {
    setIsCreatingFactorialDesign(true);
    setFactorialDesignError(null);
    try {
      const response = await createFactorialDesign(request);
      setFactorialDesign(response);
      setFactorialDesignResponses(null);
      setFactorialDesignResponseError(null);
    } catch (error) {
      setFactorialDesign(null);
      setFactorialDesignResponses(null);
      setFactorialDesignError(error instanceof Error ? error.message : "doe_factorial_failed");
    } finally {
      setIsCreatingFactorialDesign(false);
    }
  }

  async function handleSaveFactorialDesignResponses(
    designId: string,
    request: DoeDesignResponsesUpsertRequest,
  ) {
    setIsSavingFactorialDesignResponses(true);
    setFactorialDesignResponseError(null);
    try {
      const response = await saveFactorialDesignResponses(designId, request);
      setFactorialDesignResponses(response);
      setFactorialDesign((current) =>
        current !== null && current.design_id === response.design_id
          ? { ...current, status: response.status }
          : current,
      );
    } catch (error) {
      setFactorialDesignResponseError(
        error instanceof Error ? error.message : "doe_factorial_responses_failed",
      );
    } finally {
      setIsSavingFactorialDesignResponses(false);
    }
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

  function handleEqualVariancesResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedEqualVariancesResponseColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedEqualVariancesGroupColumnId) {
      setSelectedEqualVariancesGroupColumnId(
        version === null ? null : defaultEqualVariancesGroupColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleEqualVariancesGroupColumnChange(columnId: string) {
    setSelectedEqualVariancesGroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleEqualVariancesAlphaChange(alpha: number) {
    setEqualVariancesAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleOneSampleTResponseColumnChange(columnId: string) {
    setSelectedOneSampleTResponseColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleOneSampleTNullMeanChange(nullMean: number) {
    setOneSampleTNullMean(nullMean);
    setAnalysisResult(null);
  }

  function handleOneSampleTAlphaChange(alpha: number) {
    setOneSampleTAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleOneSampleTConfidenceLevelChange(confidenceLevel: number) {
    setOneSampleTConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleOneSampleTAlternativeChange(alternative: string) {
    setOneSampleTAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleEquivalenceTostResponseColumnChange(columnId: string) {
    setSelectedEquivalenceTostResponseColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleEquivalenceTostReferenceMeanChange(referenceMean: number) {
    setEquivalenceTostReferenceMean(referenceMean);
    setAnalysisResult(null);
  }

  function handleEquivalenceTostLowerBoundChange(lowerBound: number) {
    setEquivalenceTostLowerBound(lowerBound);
    setAnalysisResult(null);
  }

  function handleEquivalenceTostUpperBoundChange(upperBound: number) {
    setEquivalenceTostUpperBound(upperBound);
    setAnalysisResult(null);
  }

  function handleEquivalenceTostAlphaChange(alpha: number) {
    setEquivalenceTostAlpha(alpha);
    setAnalysisResult(null);
  }

  function handlePairedTBeforeColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedPairedTBeforeColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedPairedTAfterColumnId) {
      setSelectedPairedTAfterColumnId(
        version === null ? null : defaultPairedTAfterColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handlePairedTAfterColumnChange(columnId: string) {
    setSelectedPairedTAfterColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handlePairedTNullDifferenceChange(nullDifference: number) {
    setPairedTNullDifference(nullDifference);
    setAnalysisResult(null);
  }

  function handlePairedTAlphaChange(alpha: number) {
    setPairedTAlpha(alpha);
    setAnalysisResult(null);
  }

  function handlePairedTConfidenceLevelChange(confidenceLevel: number) {
    setPairedTConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handlePairedTAlternativeChange(alternative: string) {
    setPairedTAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleOneSampleWilcoxonResponseColumnChange(columnId: string) {
    setSelectedOneSampleWilcoxonResponseColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleOneSampleWilcoxonNullLocationChange(nullLocation: number) {
    setOneSampleWilcoxonNullLocation(nullLocation);
    setAnalysisResult(null);
  }

  function handleOneSampleWilcoxonAlphaChange(alpha: number) {
    setOneSampleWilcoxonAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleOneSampleWilcoxonAlternativeChange(alternative: string) {
    setOneSampleWilcoxonAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleOneSampleWilcoxonMethodChange(method: string) {
    setOneSampleWilcoxonMethod(method);
    setAnalysisResult(null);
  }

  function handleOneSampleWilcoxonZeroMethodChange(zeroMethod: string) {
    setOneSampleWilcoxonZeroMethod(zeroMethod);
    setAnalysisResult(null);
  }

  function handleTwoSampleTResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedTwoSampleTResponseColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedTwoSampleTGroupColumnId) {
      setSelectedTwoSampleTGroupColumnId(
        version === null ? null : defaultTwoSampleTGroupColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleTwoSampleTGroupColumnChange(columnId: string) {
    setSelectedTwoSampleTGroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleTwoSampleTAlphaChange(alpha: number) {
    setTwoSampleTAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleTwoSampleTConfidenceLevelChange(confidenceLevel: number) {
    setTwoSampleTConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleTwoSampleTAlternativeChange(alternative: string) {
    setTwoSampleTAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleTwoSampleTVarianceAssumptionChange(varianceAssumption: string) {
    setTwoSampleTVarianceAssumption(varianceAssumption);
    setAnalysisResult(null);
  }

  function handleMannWhitneyResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedMannWhitneyResponseColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedMannWhitneyGroupColumnId) {
      setSelectedMannWhitneyGroupColumnId(
        version === null ? null : defaultMannWhitneyGroupColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleMannWhitneyGroupColumnChange(columnId: string) {
    setSelectedMannWhitneyGroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleMannWhitneyAlphaChange(alpha: number) {
    setMannWhitneyAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleMannWhitneyAlternativeChange(alternative: string) {
    setMannWhitneyAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleMannWhitneyMethodChange(method: string) {
    setMannWhitneyMethod(method);
    setAnalysisResult(null);
  }

  function handleKruskalWallisResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedKruskalWallisResponseColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedKruskalWallisGroupColumnId) {
      setSelectedKruskalWallisGroupColumnId(
        version === null ? null : defaultKruskalWallisGroupColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleKruskalWallisGroupColumnChange(columnId: string) {
    setSelectedKruskalWallisGroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleKruskalWallisAlphaChange(alpha: number) {
    setKruskalWallisAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleOneWayAnovaResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedOneWayAnovaResponseColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedOneWayAnovaGroupColumnId) {
      setSelectedOneWayAnovaGroupColumnId(
        version === null ? null : defaultOneWayAnovaGroupColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleOneWayAnovaGroupColumnChange(columnId: string) {
    setSelectedOneWayAnovaGroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleOneWayAnovaAlphaChange(alpha: number) {
    setOneWayAnovaAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleOneWayAnovaConfidenceLevelChange(confidenceLevel: number) {
    setOneWayAnovaConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleOneProportionResponseColumnChange(columnId: string) {
    setSelectedOneProportionResponseColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleOneProportionEventLevelChange(eventLevel: string) {
    setOneProportionEventLevel(eventLevel);
    setAnalysisResult(null);
  }

  function handleOneProportionNullProportionChange(nullProportion: number) {
    setOneProportionNullProportion(nullProportion);
    setAnalysisResult(null);
  }

  function handleOneProportionAlphaChange(alpha: number) {
    setOneProportionAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleOneProportionConfidenceLevelChange(confidenceLevel: number) {
    setOneProportionConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleOneProportionAlternativeChange(alternative: string) {
    setOneProportionAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleOneProportionCiMethodChange(ciMethod: string) {
    setOneProportionCiMethod(ciMethod);
    setAnalysisResult(null);
  }

  function handleTwoProportionResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedTwoProportionResponseColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedTwoProportionGroupColumnId) {
      setSelectedTwoProportionGroupColumnId(
        version === null ? null : defaultTwoProportionGroupColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleTwoProportionGroupColumnChange(columnId: string) {
    setSelectedTwoProportionGroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleTwoProportionEventLevelChange(eventLevel: string) {
    setTwoProportionEventLevel(eventLevel);
    setAnalysisResult(null);
  }

  function handleTwoProportionAlphaChange(alpha: number) {
    setTwoProportionAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleTwoProportionConfidenceLevelChange(confidenceLevel: number) {
    setTwoProportionConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleTwoProportionAlternativeChange(alternative: string) {
    setTwoProportionAlternative(alternative);
    setAnalysisResult(null);
  }

  function handleChiSquareAssociationRowColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedChiSquareAssociationRowColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedChiSquareAssociationColumnColumnId) {
      setSelectedChiSquareAssociationColumnColumnId(
        version === null
          ? null
          : defaultChiSquareAssociationColumnColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handleChiSquareAssociationColumnColumnChange(columnId: string) {
    setSelectedChiSquareAssociationColumnColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleChiSquareAssociationAlphaChange(alpha: number) {
    setChiSquareAssociationAlpha(alpha);
    setAnalysisResult(null);
  }

  function handlePearsonXColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedPearsonXColumnId(nextColumnId);
    if (nextColumnId !== null && nextColumnId === selectedPearsonYColumnId) {
      setSelectedPearsonYColumnId(
        version === null ? null : defaultPearsonYColumnId(version.columns, nextColumnId),
      );
    }
    setAnalysisResult(null);
  }

  function handlePearsonYColumnChange(columnId: string) {
    setSelectedPearsonYColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handlePearsonAlphaChange(alpha: number) {
    setPearsonAlpha(alpha);
    setAnalysisResult(null);
  }

  function handlePearsonConfidenceLevelChange(confidenceLevel: number) {
    setPearsonConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleToggleXyCorrelationXColumn(columnId: string, checked: boolean) {
    setSelectedXyCorrelationXColumnIds((current) =>
      checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId),
    );
    setAnalysisResult(null);
  }

  function handleToggleXyCorrelationYColumn(columnId: string, checked: boolean) {
    setSelectedXyCorrelationYColumnIds((current) =>
      checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId),
    );
    setAnalysisResult(null);
  }

  function handleXyCorrelationAlphaChange(alpha: number) {
    setXyCorrelationAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleXyCorrelationConfidenceLevelChange(confidenceLevel: number) {
    setXyCorrelationConfidenceLevel(confidenceLevel);
    setAnalysisResult(null);
  }

  function handleIndividualsChartValueColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedIndividualsChartValueColumnId(nextColumnId);
    setSelectedIndividualsChartOrderColumnId((current) =>
      current === nextColumnId ? null : current,
    );
    setAnalysisResult(null);
  }

  function handleIndividualsChartOrderColumnChange(columnId: string | null) {
    setSelectedIndividualsChartOrderColumnId(columnId);
    setAnalysisResult(null);
  }

  function handleSubgroupChartValueColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedSubgroupChartValueColumnId(nextColumnId);
    setSelectedSubgroupChartSubgroupColumnId((current) =>
      current === nextColumnId ? null : current,
    );
    setAnalysisResult(null);
  }

  function handleSubgroupChartSubgroupColumnChange(columnId: string) {
    setSelectedSubgroupChartSubgroupColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleSubgroupChartTypeChange(chartType: SubgroupChartType) {
    setSelectedSubgroupChartType(chartType);
    setAnalysisResult(null);
  }

  function handleRunChartValueColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedRunChartValueColumnId(nextColumnId);
    setSelectedRunChartOrderColumnId((current) => (current === nextColumnId ? null : current));
    setAnalysisResult(null);
  }

  function handleRunChartOrderColumnChange(columnId: string) {
    setSelectedRunChartOrderColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleCapabilityValueColumnChange(columnId: string) {
    setSelectedCapabilityValueColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleCapabilityLslChange(value: string) {
    setCapabilityLsl(value);
    setAnalysisResult(null);
  }

  function handleCapabilityUslChange(value: string) {
    setCapabilityUsl(value);
    setAnalysisResult(null);
  }

  function handleCapabilityTargetChange(value: string) {
    setCapabilityTarget(value);
    setAnalysisResult(null);
  }

  function resetGageRrSelection(columns: DatasetColumnResponse[]) {
    const measurementColumnId = defaultGageRrMeasurementColumnId(columns);
    setSelectedGageRrMeasurementColumnId(measurementColumnId);
    setSelectedGageRrPartColumnId(defaultGageRrPartColumnId(columns, measurementColumnId));
    setSelectedGageRrOperatorColumnId(
      defaultGageRrOperatorColumnId(columns, measurementColumnId),
    );
    setSelectedGageRrReplicateColumnId(
      defaultGageRrReplicateColumnId(columns, measurementColumnId),
    );
    setSelectedGageRunChartOrderColumnId(null);
    setGageRrPreflight(null);
    setGageRrPreflightError(null);
    setAnalysisResult(null);
  }

  function handleGageRrMeasurementColumnChange(columnId: string) {
    const selectedColumnId = columnId.length > 0 ? columnId : null;
    setSelectedGageRrMeasurementColumnId(selectedColumnId);
    if (version !== null) {
      setSelectedGageRrPartColumnId(defaultGageRrPartColumnId(version.columns, selectedColumnId));
      setSelectedGageRrOperatorColumnId(
        defaultGageRrOperatorColumnId(version.columns, selectedColumnId),
      );
      setSelectedGageRrReplicateColumnId(
        defaultGageRrReplicateColumnId(version.columns, selectedColumnId),
      );
    }
    setSelectedGageRunChartOrderColumnId(null);
    setGageRrPreflight(null);
    setGageRrPreflightError(null);
    setAnalysisResult(null);
  }

  function handleGageRrPartColumnChange(columnId: string) {
    setSelectedGageRrPartColumnId(columnId.length > 0 ? columnId : null);
    setSelectedGageRunChartOrderColumnId((current) =>
      current === columnId ? null : current,
    );
    setGageRrPreflight(null);
    setGageRrPreflightError(null);
    setAnalysisResult(null);
  }

  function handleGageRrOperatorColumnChange(columnId: string) {
    setSelectedGageRrOperatorColumnId(columnId.length > 0 ? columnId : null);
    setSelectedGageRunChartOrderColumnId((current) =>
      current === columnId ? null : current,
    );
    setGageRrPreflight(null);
    setGageRrPreflightError(null);
    setAnalysisResult(null);
  }

  function handleGageRrReplicateColumnChange(columnId: string) {
    setSelectedGageRrReplicateColumnId(columnId.length > 0 ? columnId : null);
    setSelectedGageRunChartOrderColumnId((current) =>
      current === columnId ? null : current,
    );
    setGageRrPreflight(null);
    setGageRrPreflightError(null);
    setAnalysisResult(null);
  }

  function handleGageRunChartOrderColumnChange(columnId: string) {
    setSelectedGageRunChartOrderColumnId(columnId.length > 0 ? columnId : null);
    setAnalysisResult(null);
  }

  function handleLinearModelResponseColumnChange(columnId: string) {
    const nextColumnId = columnId.length > 0 ? columnId : null;
    setSelectedLinearModelResponseColumnId(nextColumnId);
    setSelectedLinearModelPredictorColumnIds((current) => {
      const nextPredictorIds = current.filter((id) => id !== nextColumnId);
      pruneLinearModelExtraTerms(nextPredictorIds);
      return nextPredictorIds;
    });
    setAnalysisResult(null);
  }

  function handleToggleLinearModelPredictorColumn(columnId: string, checked: boolean) {
    if (columnId === selectedLinearModelResponseColumnId) {
      return;
    }
    setSelectedLinearModelPredictorColumnIds((current) => {
      const nextPredictorIds = checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId);
      pruneLinearModelExtraTerms(nextPredictorIds);
      return nextPredictorIds;
    });
    setAnalysisResult(null);
  }

  function pruneLinearModelExtraTerms(nextPredictorIds: string[]) {
    const allowedIds = new Set(nextPredictorIds);
    setSelectedLinearModelQuadraticColumnIds((current) =>
      current.filter((id) => allowedIds.has(id)),
    );
    setSelectedLinearModelInteractionKeys((current) =>
      current.filter((key) => {
        const [leftColumnId, rightColumnId] = splitLinearModelInteractionKey(key);
        return allowedIds.has(leftColumnId) && allowedIds.has(rightColumnId);
      }),
    );
  }

  function handleToggleLinearModelQuadraticColumn(columnId: string, checked: boolean) {
    setSelectedLinearModelQuadraticColumnIds((current) =>
      checked
        ? Array.from(new Set([...current, columnId]))
        : current.filter((id) => id !== columnId),
    );
    setAnalysisResult(null);
  }

  function handleToggleLinearModelInteractionTerm(key: string, checked: boolean) {
    setSelectedLinearModelInteractionKeys((current) =>
      checked ? Array.from(new Set([...current, key])) : current.filter((id) => id !== key),
    );
    setAnalysisResult(null);
  }

  function handleLinearModelAlphaChange(alpha: number) {
    setLinearModelAlpha(alpha);
    setAnalysisResult(null);
  }

  function handleLinearModelConfidenceLevelChange(confidenceLevel: number) {
    setLinearModelConfidenceLevel(confidenceLevel);
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

  async function handleRunEqualVariancesAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "eda.equal_variances" ||
      selectedEqualVariancesResponseColumnId === null ||
      selectedEqualVariancesGroupColumnId === null
    ) {
      setFlowError("equal_variances_columns_required");
      return;
    }
    if (selectedEqualVariancesResponseColumnId === selectedEqualVariancesGroupColumnId) {
      setFlowError("equal_variances_same_response_and_group");
      return;
    }
    if (equalVariancesAlpha <= 0 || equalVariancesAlpha >= 1) {
      setFlowError("invalid_equal_variances_alpha");
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
        roles: {
          response: selectedEqualVariancesResponseColumnId,
          group: selectedEqualVariancesGroupColumnId,
        },
        options: {
          response_column_id: selectedEqualVariancesResponseColumnId,
          group_column_id: selectedEqualVariancesGroupColumnId,
          alpha: equalVariancesAlpha,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunOneSampleTAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.one_sample_t" ||
      selectedOneSampleTResponseColumnId === null
    ) {
      setFlowError("one_sample_t_response_required");
      return;
    }
    if (oneSampleTAlpha <= 0 || oneSampleTAlpha >= 1) {
      setFlowError("invalid_one_sample_t_alpha");
      return;
    }
    if (oneSampleTConfidenceLevel <= 0 || oneSampleTConfidenceLevel >= 1) {
      setFlowError("invalid_one_sample_t_confidence_level");
      return;
    }
    if (!Number.isFinite(oneSampleTNullMean)) {
      setFlowError("invalid_one_sample_t_null_mean");
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
        roles: {
          response: selectedOneSampleTResponseColumnId,
        },
        options: {
          response_column_id: selectedOneSampleTResponseColumnId,
          alpha: oneSampleTAlpha,
          confidence_level: oneSampleTConfidenceLevel,
          alternative: oneSampleTAlternative,
          null_mean: oneSampleTNullMean,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunEquivalenceTostAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.equivalence_tost" ||
      selectedEquivalenceTostResponseColumnId === null
    ) {
      setFlowError("equivalence_tost_response_required");
      return;
    }
    if (!Number.isFinite(equivalenceTostReferenceMean)) {
      setFlowError("invalid_equivalence_tost_reference_mean");
      return;
    }
    if (
      !Number.isFinite(equivalenceTostLowerBound) ||
      !Number.isFinite(equivalenceTostUpperBound)
    ) {
      setFlowError("invalid_equivalence_tost_bounds");
      return;
    }
    if (equivalenceTostLowerBound >= equivalenceTostUpperBound) {
      setFlowError("equivalence_tost_bounds_order_invalid");
      return;
    }
    if (equivalenceTostAlpha <= 0 || equivalenceTostAlpha >= 0.5) {
      setFlowError("invalid_equivalence_tost_alpha");
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
        roles: {
          response: selectedEquivalenceTostResponseColumnId,
        },
        options: {
          design: "one_sample_mean",
          response_column_id: selectedEquivalenceTostResponseColumnId,
          reference_mean: equivalenceTostReferenceMean,
          lower_bound: equivalenceTostLowerBound,
          upper_bound: equivalenceTostUpperBound,
          alpha: equivalenceTostAlpha,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunPairedTAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.paired_t" ||
      selectedPairedTBeforeColumnId === null ||
      selectedPairedTAfterColumnId === null
    ) {
      setFlowError("paired_t_columns_required");
      return;
    }
    if (selectedPairedTBeforeColumnId === selectedPairedTAfterColumnId) {
      setFlowError("paired_t_same_before_and_after_column");
      return;
    }
    if (pairedTAlpha <= 0 || pairedTAlpha >= 1) {
      setFlowError("invalid_paired_t_alpha");
      return;
    }
    if (pairedTConfidenceLevel <= 0 || pairedTConfidenceLevel >= 1) {
      setFlowError("invalid_paired_t_confidence_level");
      return;
    }
    if (!Number.isFinite(pairedTNullDifference)) {
      setFlowError("invalid_paired_t_null_difference");
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
        roles: {
          before: selectedPairedTBeforeColumnId,
          after: selectedPairedTAfterColumnId,
        },
        options: {
          before_column_id: selectedPairedTBeforeColumnId,
          after_column_id: selectedPairedTAfterColumnId,
          alpha: pairedTAlpha,
          confidence_level: pairedTConfidenceLevel,
          alternative: pairedTAlternative,
          null_difference: pairedTNullDifference,
          missing_policy: "complete_pair",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunOneSampleWilcoxonAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.one_sample_wilcoxon" ||
      selectedOneSampleWilcoxonResponseColumnId === null
    ) {
      setFlowError("one_sample_wilcoxon_response_required");
      return;
    }
    if (oneSampleWilcoxonAlpha <= 0 || oneSampleWilcoxonAlpha >= 1) {
      setFlowError("invalid_one_sample_wilcoxon_alpha");
      return;
    }
    if (!Number.isFinite(oneSampleWilcoxonNullLocation)) {
      setFlowError("invalid_one_sample_wilcoxon_null_location");
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
        roles: {
          response: selectedOneSampleWilcoxonResponseColumnId,
        },
        options: {
          response_column_id: selectedOneSampleWilcoxonResponseColumnId,
          alpha: oneSampleWilcoxonAlpha,
          alternative: oneSampleWilcoxonAlternative,
          null_location: oneSampleWilcoxonNullLocation,
          method: oneSampleWilcoxonMethod,
          zero_method: oneSampleWilcoxonZeroMethod,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunTwoSampleTAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.two_sample_t" ||
      selectedTwoSampleTResponseColumnId === null ||
      selectedTwoSampleTGroupColumnId === null
    ) {
      setFlowError("two_sample_t_columns_required");
      return;
    }
    if (selectedTwoSampleTResponseColumnId === selectedTwoSampleTGroupColumnId) {
      setFlowError("two_sample_t_same_response_and_group");
      return;
    }
    if (twoSampleTAlpha <= 0 || twoSampleTAlpha >= 1) {
      setFlowError("invalid_two_sample_t_alpha");
      return;
    }
    if (twoSampleTConfidenceLevel <= 0 || twoSampleTConfidenceLevel >= 1) {
      setFlowError("invalid_two_sample_t_confidence_level");
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
        roles: {
          response: selectedTwoSampleTResponseColumnId,
          group: selectedTwoSampleTGroupColumnId,
        },
        options: {
          response_column_id: selectedTwoSampleTResponseColumnId,
          group_column_id: selectedTwoSampleTGroupColumnId,
          alpha: twoSampleTAlpha,
          confidence_level: twoSampleTConfidenceLevel,
          alternative: twoSampleTAlternative,
          variance_assumption: twoSampleTVarianceAssumption,
          null_difference: 0,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunMannWhitneyAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.mann_whitney" ||
      selectedMannWhitneyResponseColumnId === null ||
      selectedMannWhitneyGroupColumnId === null
    ) {
      setFlowError("mann_whitney_columns_required");
      return;
    }
    if (selectedMannWhitneyResponseColumnId === selectedMannWhitneyGroupColumnId) {
      setFlowError("mann_whitney_same_response_and_group");
      return;
    }
    if (mannWhitneyAlpha <= 0 || mannWhitneyAlpha >= 1) {
      setFlowError("invalid_mann_whitney_alpha");
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
        roles: {
          response: selectedMannWhitneyResponseColumnId,
          group: selectedMannWhitneyGroupColumnId,
        },
        options: {
          response_column_id: selectedMannWhitneyResponseColumnId,
          group_column_id: selectedMannWhitneyGroupColumnId,
          alpha: mannWhitneyAlpha,
          alternative: mannWhitneyAlternative,
          method: mannWhitneyMethod,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunKruskalWallisAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.kruskal_wallis" ||
      selectedKruskalWallisResponseColumnId === null ||
      selectedKruskalWallisGroupColumnId === null
    ) {
      setFlowError("kruskal_wallis_columns_required");
      return;
    }
    if (selectedKruskalWallisResponseColumnId === selectedKruskalWallisGroupColumnId) {
      setFlowError("kruskal_wallis_same_response_and_group");
      return;
    }
    if (kruskalWallisAlpha <= 0 || kruskalWallisAlpha >= 1) {
      setFlowError("invalid_kruskal_wallis_alpha");
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
        roles: {
          response: selectedKruskalWallisResponseColumnId,
          group: selectedKruskalWallisGroupColumnId,
        },
        options: {
          response_column_id: selectedKruskalWallisResponseColumnId,
          group_column_id: selectedKruskalWallisGroupColumnId,
          alpha: kruskalWallisAlpha,
          posthoc_method: "dunn_holm",
          posthoc_policy: "after_significant",
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunOneWayAnovaAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "hypothesis.one_way_anova" ||
      selectedOneWayAnovaResponseColumnId === null ||
      selectedOneWayAnovaGroupColumnId === null
    ) {
      setFlowError("one_way_anova_columns_required");
      return;
    }
    if (selectedOneWayAnovaResponseColumnId === selectedOneWayAnovaGroupColumnId) {
      setFlowError("one_way_anova_same_response_and_group");
      return;
    }
    if (oneWayAnovaAlpha <= 0 || oneWayAnovaAlpha >= 1) {
      setFlowError("invalid_one_way_anova_alpha");
      return;
    }
    if (oneWayAnovaConfidenceLevel <= 0 || oneWayAnovaConfidenceLevel >= 1) {
      setFlowError("invalid_one_way_anova_confidence_level");
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
        roles: {
          response: selectedOneWayAnovaResponseColumnId,
          group: selectedOneWayAnovaGroupColumnId,
        },
        options: {
          response_column_id: selectedOneWayAnovaResponseColumnId,
          group_column_id: selectedOneWayAnovaGroupColumnId,
          alpha: oneWayAnovaAlpha,
          confidence_level: oneWayAnovaConfidenceLevel,
          anova_type: "standard",
          posthoc_method: "tukey_kramer",
          posthoc_policy: "after_significant",
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunOneProportionAnalysis() {
    const eventLevel = oneProportionEventLevel.trim();
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "categorical.one_proportion" ||
      selectedOneProportionResponseColumnId === null ||
      eventLevel.length === 0
    ) {
      setFlowError("one_proportion_response_and_event_required");
      return;
    }
    if (oneProportionNullProportion <= 0 || oneProportionNullProportion >= 1) {
      setFlowError("invalid_one_proportion_null_proportion");
      return;
    }
    if (oneProportionAlpha <= 0 || oneProportionAlpha >= 1) {
      setFlowError("invalid_one_proportion_alpha");
      return;
    }
    if (oneProportionConfidenceLevel <= 0 || oneProportionConfidenceLevel >= 1) {
      setFlowError("invalid_one_proportion_confidence_level");
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
        roles: {
          response: selectedOneProportionResponseColumnId,
        },
        options: {
          response_column_id: selectedOneProportionResponseColumnId,
          event_level: eventLevel,
          null_proportion: oneProportionNullProportion,
          alpha: oneProportionAlpha,
          confidence_level: oneProportionConfidenceLevel,
          alternative: oneProportionAlternative,
          ci_method: oneProportionCiMethod,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunTwoProportionAnalysis() {
    const eventLevel = twoProportionEventLevel.trim();
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "categorical.two_proportion" ||
      selectedTwoProportionResponseColumnId === null ||
      selectedTwoProportionGroupColumnId === null ||
      eventLevel.length === 0
    ) {
      setFlowError("two_proportion_response_group_and_event_required");
      return;
    }
    if (selectedTwoProportionResponseColumnId === selectedTwoProportionGroupColumnId) {
      setFlowError("two_proportion_same_response_and_group");
      return;
    }
    if (twoProportionAlpha <= 0 || twoProportionAlpha >= 1) {
      setFlowError("invalid_two_proportion_alpha");
      return;
    }
    if (twoProportionConfidenceLevel <= 0 || twoProportionConfidenceLevel >= 1) {
      setFlowError("invalid_two_proportion_confidence_level");
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
        roles: {
          response: selectedTwoProportionResponseColumnId,
          group: selectedTwoProportionGroupColumnId,
        },
        options: {
          response_column_id: selectedTwoProportionResponseColumnId,
          group_column_id: selectedTwoProportionGroupColumnId,
          event_level: eventLevel,
          alpha: twoProportionAlpha,
          confidence_level: twoProportionConfidenceLevel,
          alternative: twoProportionAlternative,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunChiSquareAssociationAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "categorical.chi_square_association" ||
      selectedChiSquareAssociationRowColumnId === null ||
      selectedChiSquareAssociationColumnColumnId === null
    ) {
      setFlowError("chi_square_row_and_column_required");
      return;
    }
    if (selectedChiSquareAssociationRowColumnId === selectedChiSquareAssociationColumnColumnId) {
      setFlowError("chi_square_same_row_and_column");
      return;
    }
    if (chiSquareAssociationAlpha <= 0 || chiSquareAssociationAlpha >= 1) {
      setFlowError("invalid_chi_square_alpha");
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
        roles: {
          row: selectedChiSquareAssociationRowColumnId,
          column: selectedChiSquareAssociationColumnColumnId,
        },
        options: {
          row_column_id: selectedChiSquareAssociationRowColumnId,
          column_column_id: selectedChiSquareAssociationColumnColumnId,
          alpha: chiSquareAssociationAlpha,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunPearsonAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "regression.pearson" ||
      selectedPearsonXColumnId === null ||
      selectedPearsonYColumnId === null
    ) {
      setFlowError("pearson_columns_required");
      return;
    }
    if (selectedPearsonXColumnId === selectedPearsonYColumnId) {
      setFlowError("pearson_same_x_and_y_column");
      return;
    }
    if (pearsonAlpha <= 0 || pearsonAlpha >= 1) {
      setFlowError("invalid_pearson_alpha");
      return;
    }
    if (pearsonConfidenceLevel <= 0 || pearsonConfidenceLevel >= 1) {
      setFlowError("invalid_pearson_confidence_level");
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
        roles: {
          x: selectedPearsonXColumnId,
          y: selectedPearsonYColumnId,
        },
        options: {
          x_column_id: selectedPearsonXColumnId,
          y_column_id: selectedPearsonYColumnId,
          alpha: pearsonAlpha,
          confidence_level: pearsonConfidenceLevel,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunXyCorrelationAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "regression.xy_correlation" ||
      selectedXyCorrelationXColumnIds.length === 0 ||
      selectedXyCorrelationYColumnIds.length === 0
    ) {
      setFlowError("xy_correlation_columns_required");
      return;
    }
    if (xyCorrelationAlpha <= 0 || xyCorrelationAlpha >= 1) {
      setFlowError("invalid_xy_correlation_alpha");
      return;
    }
    if (xyCorrelationConfidenceLevel <= 0 || xyCorrelationConfidenceLevel >= 1) {
      setFlowError("invalid_xy_correlation_confidence_level");
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
        roles: {
          x: selectedXyCorrelationXColumnIds.join(","),
          y: selectedXyCorrelationYColumnIds.join(","),
        },
        options: {
          x_column_ids: selectedXyCorrelationXColumnIds,
          y_column_ids: selectedXyCorrelationYColumnIds,
          alpha: xyCorrelationAlpha,
          confidence_level: xyCorrelationConfidenceLevel,
          missing_policy: "pairwise_complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunChartAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "quality.run_chart" ||
      selectedRunChartValueColumnId === null
    ) {
      setFlowError("run_chart_value_column_required");
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
      const roles: Record<string, string> = {
        value: selectedRunChartValueColumnId,
      };
      const options: Record<string, unknown> = {
        value_column_id: selectedRunChartValueColumnId,
        center_method: "median",
        trend_min_length: 6,
        oscillation_min_length: 14,
        runs_test_alpha: 0.05,
        point_limit: 1000,
        missing_policy: "complete_case",
      };
      if (selectedRunChartOrderColumnId !== null) {
        roles.order = selectedRunChartOrderColumnId;
        options.order_column_id = selectedRunChartOrderColumnId;
      }
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles,
        options,
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleCapabilityAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "quality.capability" ||
      selectedCapabilityValueColumnId === null
    ) {
      setFlowError("capability_value_column_required");
      return;
    }
    if (analysisFilterValidationError !== null) {
      setFlowError(analysisFilterValidationError);
      return;
    }

    const lsl = parseCapabilityOptionalNumber(capabilityLsl);
    const usl = parseCapabilityOptionalNumber(capabilityUsl);
    const target = parseCapabilityOptionalNumber(capabilityTarget);
    if (lsl.kind === "error" || usl.kind === "error" || target.kind === "error") {
      setFlowError("capability_spec_limits_invalid");
      return;
    }
    if (lsl.value === null && usl.value === null) {
      setFlowError("capability_spec_limit_required");
      return;
    }
    if (lsl.value !== null && usl.value !== null && lsl.value >= usl.value) {
      setFlowError("capability_spec_limits_invalid");
      return;
    }
    if (
      target.value !== null &&
      ((lsl.value !== null && target.value < lsl.value) ||
        (usl.value !== null && target.value > usl.value))
    ) {
      setFlowError("capability_target_outside_spec");
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
        roles: {
          value: selectedCapabilityValueColumnId,
        },
        options: {
          value_column_id: selectedCapabilityValueColumnId,
          lsl: lsl.value,
          usl: usl.value,
          target: target.value,
          missing_policy: "complete_case",
          histogram_bin_limit: 30,
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleGageRrPreflight() {
    if (
      version === null ||
      selectedGageRrMeasurementColumnId === null ||
      selectedGageRrPartColumnId === null ||
      selectedGageRrOperatorColumnId === null ||
      selectedGageRrReplicateColumnId === null
    ) {
      setGageRrPreflightError("gage_rr_columns_required");
      return;
    }
    const selectedColumns = new Set([
      selectedGageRrMeasurementColumnId,
      selectedGageRrPartColumnId,
      selectedGageRrOperatorColumnId,
      selectedGageRrReplicateColumnId,
    ]);
    if (selectedColumns.size < 4) {
      setGageRrPreflightError("gage_rr_distinct_columns_required");
      return;
    }

    setIsRunningAnalysis(true);
    setFlowError(null);
    setGageRrPreflightError(null);
    try {
      const response = await fetchGageRrPreflight({
        dataset_version_id: version.version_id,
        measurement_column_id: selectedGageRrMeasurementColumnId,
        part_column_id: selectedGageRrPartColumnId,
        operator_column_id: selectedGageRrOperatorColumnId,
        replicate_column_id: selectedGageRrReplicateColumnId,
        missing_policy: "complete_case",
      });
      setGageRrPreflight(response);
    } catch (error) {
      setGageRrPreflight(null);
      setGageRrPreflightError(
        error instanceof Error ? error.message : "gage_rr_preflight_failed",
      );
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleGageRrAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "quality.gage_rr" ||
      selectedGageRrMeasurementColumnId === null ||
      selectedGageRrPartColumnId === null ||
      selectedGageRrOperatorColumnId === null ||
      selectedGageRrReplicateColumnId === null
    ) {
      setFlowError("gage_rr_columns_required");
      return;
    }
    if (analysisFilterValidationError !== null) {
      setFlowError(analysisFilterValidationError);
      return;
    }
    if (
      gageRrPreflight === null ||
      !gageRrPreflight.design.ready_for_anova ||
      gageRrPreflight.dataset_version_id !== version.version_id
    ) {
      setGageRrPreflightError("gage_rr_ready_preflight_required");
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
        roles: {
          measurement: selectedGageRrMeasurementColumnId,
          part: selectedGageRrPartColumnId,
          operator: selectedGageRrOperatorColumnId,
          replicate: selectedGageRrReplicateColumnId,
        },
        options: {
          measurement_column_id: selectedGageRrMeasurementColumnId,
          part_column_id: selectedGageRrPartColumnId,
          operator_column_id: selectedGageRrOperatorColumnId,
          replicate_column_id: selectedGageRrReplicateColumnId,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
      setGageRrPreflightError(null);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleGageRunChartAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "quality.gage_run_chart" ||
      selectedGageRrMeasurementColumnId === null ||
      selectedGageRrPartColumnId === null ||
      selectedGageRrOperatorColumnId === null ||
      selectedGageRrReplicateColumnId === null
    ) {
      setFlowError("gage_run_chart_columns_required");
      return;
    }
    if (analysisFilterValidationError !== null) {
      setFlowError(analysisFilterValidationError);
      return;
    }
    const selectedColumns = new Set([
      selectedGageRrMeasurementColumnId,
      selectedGageRrPartColumnId,
      selectedGageRrOperatorColumnId,
      selectedGageRrReplicateColumnId,
    ]);
    if (selectedColumns.size < 4) {
      setFlowError("gage_run_chart_distinct_columns_required");
      return;
    }

    setIsRunningAnalysis(true);
    setFlowError(null);
    try {
      const filterConditions = serializeAnalysisFilterDrafts(
        analysisFilterDrafts,
        version.columns,
      );
      const roles: Record<string, string> = {
        measurement: selectedGageRrMeasurementColumnId,
        part: selectedGageRrPartColumnId,
        operator: selectedGageRrOperatorColumnId,
        replicate: selectedGageRrReplicateColumnId,
      };
      const options: Record<string, unknown> = {
        measurement_column_id: selectedGageRrMeasurementColumnId,
        part_column_id: selectedGageRrPartColumnId,
        operator_column_id: selectedGageRrOperatorColumnId,
        replicate_column_id: selectedGageRrReplicateColumnId,
        point_limit: 1000,
        missing_policy: "complete_case",
      };
      if (selectedGageRunChartOrderColumnId !== null) {
        roles.order = selectedGageRunChartOrderColumnId;
        options.order_column_id = selectedGageRunChartOrderColumnId;
      }
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles,
        options,
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleIndividualsChartAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "quality.individuals_chart" ||
      selectedIndividualsChartValueColumnId === null
    ) {
      setFlowError("individuals_chart_value_column_required");
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
      const roles: Record<string, string> = {
        value: selectedIndividualsChartValueColumnId,
      };
      const options: Record<string, unknown> = {
        value_column_id: selectedIndividualsChartValueColumnId,
        point_limit: 1000,
        same_side_min_length: 9,
        trend_min_length: 6,
        missing_policy: "complete_case",
      };
      if (selectedIndividualsChartOrderColumnId !== null) {
        roles.order = selectedIndividualsChartOrderColumnId;
        options.order_column_id = selectedIndividualsChartOrderColumnId;
      }
      const response = await createAnalysisRun({
        method_id: selectedMethod.method_id,
        method_version: selectedMethod.method_version,
        dataset_version_id: version.version_id,
        filter_snapshot: {
          expression_version: 1,
          conditions: filterConditions,
        },
        roles,
        options,
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleSubgroupChartAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "quality.subgroup_chart" ||
      selectedSubgroupChartValueColumnId === null ||
      selectedSubgroupChartSubgroupColumnId === null
    ) {
      setFlowError("subgroup_chart_required_columns_missing");
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
        roles: {
          value: selectedSubgroupChartValueColumnId,
          subgroup: selectedSubgroupChartSubgroupColumnId,
        },
        options: {
          value_column_id: selectedSubgroupChartValueColumnId,
          subgroup_column_id: selectedSubgroupChartSubgroupColumnId,
          chart_type: selectedSubgroupChartType,
          point_limit: 1000,
          missing_policy: "complete_case",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunLinearModelAnalysis() {
    if (
      version === null ||
      selectedMethod === null ||
      selectedMethod.method_id !== "regression.linear_model" ||
      selectedLinearModelResponseColumnId === null
    ) {
      setFlowError("linear_model_response_column_required");
      return;
    }
    if (selectedLinearModelPredictorColumnIds.length === 0) {
      setFlowError("linear_model_predictors_required");
      return;
    }
    if (selectedLinearModelPredictorColumnIds.includes(selectedLinearModelResponseColumnId)) {
      setFlowError("linear_model_response_predictor_overlap");
      return;
    }
    if (linearModelAlpha <= 0 || linearModelAlpha >= 1) {
      setFlowError("invalid_linear_model_alpha");
      return;
    }
    if (linearModelConfidenceLevel <= 0 || linearModelConfidenceLevel >= 1) {
      setFlowError("invalid_linear_model_confidence_level");
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
        roles: {
          response: selectedLinearModelResponseColumnId,
          predictors: selectedLinearModelPredictorColumnIds.join(","),
        },
        options: {
          response_column_id: selectedLinearModelResponseColumnId,
          predictor_column_ids: selectedLinearModelPredictorColumnIds,
          quadratic_terms: selectedLinearModelQuadraticColumnIds,
          interaction_terms: selectedLinearModelInteractionKeys.map((key) => {
            const [leftColumnId, rightColumnId] = splitLinearModelInteractionKey(key);
            return {
              left_column_id: leftColumnId,
              right_column_id: rightColumnId,
            };
          }),
          alpha: linearModelAlpha,
          confidence_level: linearModelConfidenceLevel,
          missing_policy: "complete_case",
          include_intercept: true,
          covariance_type: "standard",
        },
      });
      setAnalysisResult(response);
    } catch (error) {
      setFlowError(error instanceof Error ? error.message : "analysis_run_failed");
    } finally {
      setIsRunningAnalysis(false);
    }
  }

  async function handleRunLinearModelPredictionPreflight() {
    if (
      version === null ||
      linearModelResult?.model_manifest === undefined ||
      linearModelPredictionTargetVersionId === null
    ) {
      setLinearModelPredictionPreflightError("regression_model_manifest_required");
      return;
    }

    linearModelPredictionRequest.cancel();
    linearModelPredictionRowsRequest.cancel();
    setIsRunningLinearModelPrediction(false);
    setLinearModelPrediction(null);
    setLinearModelPredictionError(null);
    setLinearModelPredictionRowsPage(null);
    setLinearModelPredictionRowsError(null);
    setIsLoadingLinearModelPredictionRows(false);
    const request = linearModelPredictionPreflightRequest.begin();
    setIsRunningLinearModelPredictionPreflight(true);
    setLinearModelPredictionPreflightError(null);
    try {
      const response = await fetchRegressionPredictionPreflight(
        linearModelResult.model_manifest.model_id,
        {
          dataset_version_id: linearModelPredictionTargetVersionId,
        },
      );
      if (linearModelPredictionPreflightRequest.isCurrent(request)) {
        setLinearModelPredictionPreflight(response);
      }
    } catch (error) {
      if (linearModelPredictionPreflightRequest.isCurrent(request)) {
        setLinearModelPredictionPreflight(null);
        setLinearModelPredictionPreflightError(
          error instanceof Error ? error.message : "regression_prediction_preflight_failed",
        );
      }
    } finally {
      if (linearModelPredictionPreflightRequest.isCurrent(request)) {
        setIsRunningLinearModelPredictionPreflight(false);
      }
    }
  }

  async function handleRunLinearModelPrediction() {
    if (
      version === null ||
      linearModelResult?.model_manifest === undefined ||
      linearModelPredictionTargetVersionId === null
    ) {
      setLinearModelPredictionError("regression_model_manifest_required");
      return;
    }
    if (
      linearModelPredictionPreflight === null ||
      !linearModelPredictionPreflight.prediction_ready ||
      linearModelPredictionPreflight.model_id !== linearModelResult.model_manifest.model_id ||
      linearModelPredictionPreflight.target_dataset_version_id !==
        linearModelPredictionTargetVersionId
    ) {
      setLinearModelPredictionError("regression_prediction_preflight_required");
      return;
    }

    linearModelPredictionRowsRequest.cancel();
    setLinearModelPredictionRowsPage(null);
    setLinearModelPredictionRowsError(null);
    setIsLoadingLinearModelPredictionRows(false);
    const request = linearModelPredictionRequest.begin();
    setIsRunningLinearModelPrediction(true);
    setLinearModelPredictionError(null);
    try {
      const response = await fetchRegressionPredictions(
        linearModelResult.model_manifest.model_id,
        {
          dataset_version_id: linearModelPredictionTargetVersionId,
          confidence_level: linearModelConfidenceLevel,
          missing_policy: "complete_case",
          include_intervals: true,
        },
      );
      if (linearModelPredictionRequest.isCurrent(request)) {
        setLinearModelPrediction(response);
        await loadLinearModelPredictionRows(response.prediction_id, 0);
      }
    } catch (error) {
      if (linearModelPredictionRequest.isCurrent(request)) {
        linearModelPredictionRowsRequest.cancel();
        setLinearModelPrediction(null);
        setLinearModelPredictionError(
          error instanceof Error ? error.message : "regression_prediction_failed",
        );
        setLinearModelPredictionRowsPage(null);
        setLinearModelPredictionRowsError(null);
        setIsLoadingLinearModelPredictionRows(false);
      }
    } finally {
      if (linearModelPredictionRequest.isCurrent(request)) {
        setIsRunningLinearModelPrediction(false);
      }
    }
  }

  async function loadLinearModelPredictionRows(predictionId: string, offset: number) {
    const request = linearModelPredictionRowsRequest.begin();
    setIsLoadingLinearModelPredictionRows(true);
    setLinearModelPredictionRowsError(null);
    try {
      const response = await fetchRegressionPredictionRows(
        predictionId,
        linearModelPredictionPageSize,
        Math.max(0, offset),
      );
      if (linearModelPredictionRowsRequest.isCurrent(request)) {
        setLinearModelPredictionRowsPage(response);
      }
    } catch (error) {
      if (linearModelPredictionRowsRequest.isCurrent(request)) {
        setLinearModelPredictionRowsError(
          error instanceof Error ? error.message : "regression_prediction_rows_failed",
        );
      }
    } finally {
      if (linearModelPredictionRowsRequest.isCurrent(request)) {
        setIsLoadingLinearModelPredictionRows(false);
      }
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
    analysisExportState.clearAnalysisExportErrors();
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
    analysisRunError: flowError,
    analysisResult: descriptiveAnalysisResult,
    workbenchComparisonState: analysisComparisonState,
    workbenchExportState: analysisExportState,
    workbenchHistoryState: analysisHistoryState,
    workbenchRestoredState: restoredAnalysisResultState,
    chiSquareAssociationAlpha,
    chiSquareAssociationAnalysisResult,
    chiSquareAssociationColumnColumnId: selectedChiSquareAssociationColumnColumnId,
    chiSquareAssociationColumnColumns,
    chiSquareAssociationResult,
    chiSquareAssociationRowColumnId: selectedChiSquareAssociationRowColumnId,
    chiSquareAssociationRowColumns,
    descriptiveColumns,
    descriptiveResult,
    equalVariancesAlpha,
    equalVariancesAnalysisResult,
    equalVariancesGroupColumnId: selectedEqualVariancesGroupColumnId,
    equalVariancesGroupColumns,
    equalVariancesResponseColumnId: selectedEqualVariancesResponseColumnId,
    equalVariancesResponseColumns,
    equalVariancesResult,
    equivalenceTostAlpha,
    equivalenceTostAnalysisResult,
    equivalenceTostLowerBound,
    equivalenceTostReferenceMean,
    equivalenceTostResponseColumnId: selectedEquivalenceTostResponseColumnId,
    equivalenceTostResponseColumns,
    equivalenceTostResult,
    equivalenceTostUpperBound,
    graphicalSummaryAnalysisResult,
    graphicalSummaryColumns,
    graphicalSummaryResult,
    factorialDesign,
    factorialDesignError,
    factorialDesignResponseError,
    factorialDesignResponses,
    isRunningAnalysis,
    isCreatingFactorialDesign,
    isSavingFactorialDesignResponses,
    kruskalWallisAlpha,
    kruskalWallisAnalysisResult,
    kruskalWallisGroupColumnId: selectedKruskalWallisGroupColumnId,
    kruskalWallisGroupColumns,
    kruskalWallisResponseColumnId: selectedKruskalWallisResponseColumnId,
    kruskalWallisResponseColumns,
    kruskalWallisResult,
    mannWhitneyAlpha,
    mannWhitneyAlternative,
    mannWhitneyAnalysisResult,
    mannWhitneyGroupColumnId: selectedMannWhitneyGroupColumnId,
    mannWhitneyGroupColumns,
    mannWhitneyMethod,
    mannWhitneyResponseColumnId: selectedMannWhitneyResponseColumnId,
    mannWhitneyResponseColumns,
    mannWhitneyResult,
    normalityAlpha,
    normalityAnalysisResult,
    normalityColumns,
    normalityResult,
    oneProportionAlpha,
    oneProportionAlternative,
    oneProportionAnalysisResult,
    oneProportionCiMethod,
    oneProportionConfidenceLevel,
    oneProportionEventLevel,
    oneProportionNullProportion,
    oneProportionResponseColumnId: selectedOneProportionResponseColumnId,
    oneProportionResponseColumns,
    oneProportionResult,
    oneWayAnovaAlpha,
    oneWayAnovaAnalysisResult,
    oneWayAnovaConfidenceLevel,
    oneWayAnovaGroupColumnId: selectedOneWayAnovaGroupColumnId,
    oneWayAnovaGroupColumns,
    oneWayAnovaResponseColumnId: selectedOneWayAnovaResponseColumnId,
    oneWayAnovaResponseColumns,
    oneWayAnovaResult,
    oneSampleTAlpha,
    oneSampleTAlternative,
    oneSampleTAnalysisResult,
    oneSampleTConfidenceLevel,
    oneSampleTNullMean,
    oneSampleTResponseColumnId: selectedOneSampleTResponseColumnId,
    oneSampleTResponseColumns,
    oneSampleTResult,
    oneSampleWilcoxonAlpha,
    oneSampleWilcoxonAlternative,
    oneSampleWilcoxonAnalysisResult,
    oneSampleWilcoxonMethod,
    oneSampleWilcoxonNullLocation,
    oneSampleWilcoxonResponseColumnId: selectedOneSampleWilcoxonResponseColumnId,
    oneSampleWilcoxonResponseColumns,
    oneSampleWilcoxonResult,
    oneSampleWilcoxonZeroMethod,
    pairedTAfterColumnId: selectedPairedTAfterColumnId,
    pairedTAfterColumns,
    pairedTAlpha,
    pairedTAlternative,
    pairedTAnalysisResult,
    pairedTBeforeColumnId: selectedPairedTBeforeColumnId,
    pairedTBeforeColumns,
    pairedTConfidenceLevel,
    pairedTNullDifference,
    pairedTResult,
    pearsonAlpha,
    pearsonAnalysisResult,
    pearsonConfidenceLevel,
    pearsonResult,
    pearsonXColumnId: selectedPearsonXColumnId,
    pearsonXColumns,
    pearsonYColumnId: selectedPearsonYColumnId,
    pearsonYColumns,
    xyCorrelationAlpha,
    xyCorrelationAnalysisResult,
    xyCorrelationConfidenceLevel,
    xyCorrelationResult,
    xyCorrelationXColumnIds: selectedXyCorrelationXColumnIds,
    xyCorrelationXColumns,
    xyCorrelationYColumnIds: selectedXyCorrelationYColumnIds,
    xyCorrelationYColumns,
    capabilityAnalysisResult,
    capabilityLsl,
    capabilityResult,
    capabilityTarget,
    capabilityUsl,
    capabilityValueColumnId: selectedCapabilityValueColumnId,
    capabilityValueColumns,
    gageRrAnalysisResult,
    gageRrMeasurementColumnId: selectedGageRrMeasurementColumnId,
    gageRrMeasurementColumns,
    gageRrOperatorColumnId: selectedGageRrOperatorColumnId,
    gageRrOperatorColumns,
    gageRrPartColumnId: selectedGageRrPartColumnId,
    gageRrPartColumns,
    gageRrPreflight,
    gageRrPreflightError,
    gageRrReplicateColumnId: selectedGageRrReplicateColumnId,
    gageRrReplicateColumns,
    gageRrResult,
    gageRunChartAnalysisResult,
    gageRunChartOrderColumnId: selectedGageRunChartOrderColumnId,
    gageRunChartOrderColumns,
    gageRunChartResult,
    individualsChartAnalysisResult,
    individualsChartOrderColumnId: selectedIndividualsChartOrderColumnId,
    individualsChartOrderColumns,
    individualsChartResult,
    individualsChartValueColumnId: selectedIndividualsChartValueColumnId,
    individualsChartValueColumns,
    subgroupChartAnalysisResult,
    subgroupChartResult,
    subgroupChartSubgroupColumnId: selectedSubgroupChartSubgroupColumnId,
    subgroupChartSubgroupColumns,
    subgroupChartType: selectedSubgroupChartType,
    subgroupChartValueColumnId: selectedSubgroupChartValueColumnId,
    subgroupChartValueColumns,
    runChartAnalysisResult,
    runChartOrderColumnId: selectedRunChartOrderColumnId,
    runChartOrderColumns,
    runChartResult,
    runChartValueColumnId: selectedRunChartValueColumnId,
    runChartValueColumns,
    linearModelAlpha,
    linearModelAnalysisResult,
    linearModelConfidenceLevel,
    linearModelInteractionKeys: selectedLinearModelInteractionKeys,
    linearModelPredictorColumnIds: selectedLinearModelPredictorColumnIds,
    linearModelPredictorColumns,
    linearModelPrediction,
    linearModelPredictionError,
    linearModelPredictionRowsState: {
      error: linearModelPredictionRowsError,
      isLoading: isLoadingLinearModelPredictionRows,
      page: linearModelPredictionRowsPage,
      onPageChange: (offset: number) => {
        if (linearModelPrediction !== null) {
          void loadLinearModelPredictionRows(linearModelPrediction.prediction_id, offset);
        }
      },
    },
    linearModelPredictionExportState,
    linearModelPredictionTargetState,
    linearModelPredictionPreflight,
    linearModelPredictionPreflightError,
    linearModelQuadraticColumnIds: selectedLinearModelQuadraticColumnIds,
    linearModelResponseColumnId: selectedLinearModelResponseColumnId,
    linearModelResponseColumns,
    linearModelResult,
    isRunningLinearModelPrediction,
    isRunningLinearModelPredictionPreflight,
    profile,
    selectedDescriptiveColumnIds,
    selectedGraphicalSummaryColumnIds,
    selectedNormalityColumnIds,
    selectedMethod,
    selectedMethods,
    selectedModuleId,
    twoSampleTAlpha,
    twoSampleTAlternative,
    twoSampleTAnalysisResult,
    twoSampleTConfidenceLevel,
    twoSampleTGroupColumnId: selectedTwoSampleTGroupColumnId,
    twoSampleTGroupColumns,
    twoSampleTResponseColumnId: selectedTwoSampleTResponseColumnId,
    twoSampleTResponseColumns,
    twoSampleTResult,
    twoSampleTVarianceAssumption,
    twoProportionAlpha,
    twoProportionAlternative,
    twoProportionAnalysisResult,
    twoProportionConfidenceLevel,
    twoProportionEventLevel,
    twoProportionGroupColumnId: selectedTwoProportionGroupColumnId,
    twoProportionGroupColumns,
    twoProportionResponseColumnId: selectedTwoProportionResponseColumnId,
    twoProportionResponseColumns,
    twoProportionResult,
    version,
    onAnalysisFilterDraftsChange: handleAnalysisFilterDraftsChange,
    onCapabilityLslChange: handleCapabilityLslChange,
    onCapabilityTargetChange: handleCapabilityTargetChange,
    onCapabilityUslChange: handleCapabilityUslChange,
    onCapabilityValueColumnChange: handleCapabilityValueColumnChange,
    onGageRrMeasurementColumnChange: handleGageRrMeasurementColumnChange,
    onGageRrOperatorColumnChange: handleGageRrOperatorColumnChange,
    onGageRrPartColumnChange: handleGageRrPartColumnChange,
    onGageRrReplicateColumnChange: handleGageRrReplicateColumnChange,
    onGageRunChartOrderColumnChange: handleGageRunChartOrderColumnChange,
    onCreateFactorialDesign: (request: FactorialDesignCreateRequest) => {
      void handleCreateFactorialDesign(request);
    },
    onSaveFactorialDesignResponses: (
      designId: string,
      request: DoeDesignResponsesUpsertRequest,
    ) => {
      void handleSaveFactorialDesignResponses(designId, request);
    },
    onRunChiSquareAssociationAnalysis: () => {
      void handleRunChiSquareAssociationAnalysis();
    },
    onRunDescriptiveAnalysis: () => {
      void handleRunDescriptiveAnalysis();
    },
    onRunEqualVariancesAnalysis: () => {
      void handleRunEqualVariancesAnalysis();
    },
    onRunEquivalenceTostAnalysis: () => {
      void handleRunEquivalenceTostAnalysis();
    },
    onRunGraphicalSummaryAnalysis: () => {
      void handleRunGraphicalSummaryAnalysis();
    },
    onRunKruskalWallisAnalysis: () => {
      void handleRunKruskalWallisAnalysis();
    },
    onRunMannWhitneyAnalysis: () => {
      void handleRunMannWhitneyAnalysis();
    },
    onRunNormalityAnalysis: () => {
      void handleRunNormalityAnalysis();
    },
    onRunOneProportionAnalysis: () => {
      void handleRunOneProportionAnalysis();
    },
    onRunOneWayAnovaAnalysis: () => {
      void handleRunOneWayAnovaAnalysis();
    },
    onRunOneSampleTAnalysis: () => {
      void handleRunOneSampleTAnalysis();
    },
    onRunOneSampleWilcoxonAnalysis: () => {
      void handleRunOneSampleWilcoxonAnalysis();
    },
    onRunPairedTAnalysis: () => {
      void handleRunPairedTAnalysis();
    },
    onRunPearsonAnalysis: () => {
      void handleRunPearsonAnalysis();
    },
    onRunXyCorrelationAnalysis: () => {
      void handleRunXyCorrelationAnalysis();
    },
    onRunIndividualsChartAnalysis: () => {
      void handleIndividualsChartAnalysis();
    },
    onRunChartAnalysis: () => {
      void handleRunChartAnalysis();
    },
    onRunCapabilityAnalysis: () => {
      void handleCapabilityAnalysis();
    },
    onRunGageRrAnalysis: () => {
      void handleGageRrAnalysis();
    },
    onRunGageRrPreflight: () => {
      void handleGageRrPreflight();
    },
    onRunGageRunChartAnalysis: () => {
      void handleGageRunChartAnalysis();
    },
    onRunLinearModelAnalysis: () => {
      void handleRunLinearModelAnalysis();
    },
    onRunLinearModelPredictionPreflight: () => {
      void handleRunLinearModelPredictionPreflight();
    },
    onRunLinearModelPrediction: () => {
      void handleRunLinearModelPrediction();
    },
    onRunTwoSampleTAnalysis: () => {
      void handleRunTwoSampleTAnalysis();
    },
    onRunTwoProportionAnalysis: () => {
      void handleRunTwoProportionAnalysis();
    },
    onSelectMethod: handleSelectAnalysisMethod,
    onChiSquareAssociationAlphaChange: handleChiSquareAssociationAlphaChange,
    onChiSquareAssociationColumnColumnChange: handleChiSquareAssociationColumnColumnChange,
    onChiSquareAssociationRowColumnChange: handleChiSquareAssociationRowColumnChange,
    onEqualVariancesAlphaChange: handleEqualVariancesAlphaChange,
    onEqualVariancesGroupColumnChange: handleEqualVariancesGroupColumnChange,
    onEqualVariancesResponseColumnChange: handleEqualVariancesResponseColumnChange,
    onEquivalenceTostAlphaChange: handleEquivalenceTostAlphaChange,
    onEquivalenceTostLowerBoundChange: handleEquivalenceTostLowerBoundChange,
    onEquivalenceTostReferenceMeanChange: handleEquivalenceTostReferenceMeanChange,
    onEquivalenceTostResponseColumnChange: handleEquivalenceTostResponseColumnChange,
    onEquivalenceTostUpperBoundChange: handleEquivalenceTostUpperBoundChange,
    onKruskalWallisAlphaChange: handleKruskalWallisAlphaChange,
    onKruskalWallisGroupColumnChange: handleKruskalWallisGroupColumnChange,
    onKruskalWallisResponseColumnChange: handleKruskalWallisResponseColumnChange,
    onMannWhitneyAlphaChange: handleMannWhitneyAlphaChange,
    onMannWhitneyAlternativeChange: handleMannWhitneyAlternativeChange,
    onMannWhitneyGroupColumnChange: handleMannWhitneyGroupColumnChange,
    onMannWhitneyMethodChange: handleMannWhitneyMethodChange,
    onMannWhitneyResponseColumnChange: handleMannWhitneyResponseColumnChange,
    onNormalityAlphaChange: handleNormalityAlphaChange,
    onOneProportionAlphaChange: handleOneProportionAlphaChange,
    onOneProportionAlternativeChange: handleOneProportionAlternativeChange,
    onOneProportionCiMethodChange: handleOneProportionCiMethodChange,
    onOneProportionConfidenceLevelChange: handleOneProportionConfidenceLevelChange,
    onOneProportionEventLevelChange: handleOneProportionEventLevelChange,
    onOneProportionNullProportionChange: handleOneProportionNullProportionChange,
    onOneProportionResponseColumnChange: handleOneProportionResponseColumnChange,
    onOneWayAnovaAlphaChange: handleOneWayAnovaAlphaChange,
    onOneWayAnovaConfidenceLevelChange: handleOneWayAnovaConfidenceLevelChange,
    onOneWayAnovaGroupColumnChange: handleOneWayAnovaGroupColumnChange,
    onOneWayAnovaResponseColumnChange: handleOneWayAnovaResponseColumnChange,
    onOneSampleTAlphaChange: handleOneSampleTAlphaChange,
    onOneSampleTAlternativeChange: handleOneSampleTAlternativeChange,
    onOneSampleTConfidenceLevelChange: handleOneSampleTConfidenceLevelChange,
    onOneSampleTNullMeanChange: handleOneSampleTNullMeanChange,
    onOneSampleTResponseColumnChange: handleOneSampleTResponseColumnChange,
    onOneSampleWilcoxonAlphaChange: handleOneSampleWilcoxonAlphaChange,
    onOneSampleWilcoxonAlternativeChange: handleOneSampleWilcoxonAlternativeChange,
    onOneSampleWilcoxonMethodChange: handleOneSampleWilcoxonMethodChange,
    onOneSampleWilcoxonNullLocationChange: handleOneSampleWilcoxonNullLocationChange,
    onOneSampleWilcoxonResponseColumnChange: handleOneSampleWilcoxonResponseColumnChange,
    onOneSampleWilcoxonZeroMethodChange: handleOneSampleWilcoxonZeroMethodChange,
    onPairedTAfterColumnChange: handlePairedTAfterColumnChange,
    onPairedTAlphaChange: handlePairedTAlphaChange,
    onPairedTAlternativeChange: handlePairedTAlternativeChange,
    onPairedTBeforeColumnChange: handlePairedTBeforeColumnChange,
    onPairedTConfidenceLevelChange: handlePairedTConfidenceLevelChange,
    onPairedTNullDifferenceChange: handlePairedTNullDifferenceChange,
    onPearsonAlphaChange: handlePearsonAlphaChange,
    onPearsonConfidenceLevelChange: handlePearsonConfidenceLevelChange,
    onPearsonXColumnChange: handlePearsonXColumnChange,
    onPearsonYColumnChange: handlePearsonYColumnChange,
    onIndividualsChartOrderColumnChange: handleIndividualsChartOrderColumnChange,
    onIndividualsChartValueColumnChange: handleIndividualsChartValueColumnChange,
    onRunSubgroupChartAnalysis: () => {
      void handleSubgroupChartAnalysis();
    },
    onSubgroupChartSubgroupColumnChange: handleSubgroupChartSubgroupColumnChange,
    onSubgroupChartTypeChange: handleSubgroupChartTypeChange,
    onSubgroupChartValueColumnChange: handleSubgroupChartValueColumnChange,
    onRunChartOrderColumnChange: handleRunChartOrderColumnChange,
    onRunChartValueColumnChange: handleRunChartValueColumnChange,
    onXyCorrelationAlphaChange: handleXyCorrelationAlphaChange,
    onXyCorrelationConfidenceLevelChange: handleXyCorrelationConfidenceLevelChange,
    onLinearModelAlphaChange: handleLinearModelAlphaChange,
    onLinearModelConfidenceLevelChange: handleLinearModelConfidenceLevelChange,
    onLinearModelResponseColumnChange: handleLinearModelResponseColumnChange,
    onToggleLinearModelInteractionTerm: handleToggleLinearModelInteractionTerm,
    onTwoSampleTAlphaChange: handleTwoSampleTAlphaChange,
    onTwoSampleTAlternativeChange: handleTwoSampleTAlternativeChange,
    onTwoSampleTConfidenceLevelChange: handleTwoSampleTConfidenceLevelChange,
    onTwoSampleTGroupColumnChange: handleTwoSampleTGroupColumnChange,
    onTwoSampleTResponseColumnChange: handleTwoSampleTResponseColumnChange,
    onTwoSampleTVarianceAssumptionChange: handleTwoSampleTVarianceAssumptionChange,
    onTwoProportionAlphaChange: handleTwoProportionAlphaChange,
    onTwoProportionAlternativeChange: handleTwoProportionAlternativeChange,
    onTwoProportionConfidenceLevelChange: handleTwoProportionConfidenceLevelChange,
    onTwoProportionEventLevelChange: handleTwoProportionEventLevelChange,
    onTwoProportionGroupColumnChange: handleTwoProportionGroupColumnChange,
    onTwoProportionResponseColumnChange: handleTwoProportionResponseColumnChange,
    onToggleDescriptiveColumn: handleToggleDescriptiveColumn,
    onToggleGraphicalSummaryColumn: handleToggleGraphicalSummaryColumn,
    onToggleNormalityColumn: handleToggleNormalityColumn,
    onToggleLinearModelPredictorColumn: handleToggleLinearModelPredictorColumn,
    onToggleLinearModelQuadraticColumn: handleToggleLinearModelQuadraticColumn,
    onToggleXyCorrelationXColumn: handleToggleXyCorrelationXColumn,
    onToggleXyCorrelationYColumn: handleToggleXyCorrelationYColumn,
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

function selectableEqualVariancesResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableEqualVariancesGroupColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return columns.filter(
    (column) => column.role !== "id" && column.measurement_level !== "id",
  );
}

function defaultEqualVariancesResponseColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  const candidates = selectableEqualVariancesResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultEqualVariancesGroupColumnId(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string | null {
  const candidates = selectableEqualVariancesGroupColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableOneSampleTResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function defaultOneSampleTResponseColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableOneSampleTResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableEquivalenceTostResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableOneSampleTResponseColumns(columns);
}

function defaultEquivalenceTostResponseColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  return defaultOneSampleTResponseColumnId(columns);
}

function selectablePairedTColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function defaultPairedTBeforeColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectablePairedTColumns(columns);
  return candidates[0]?.column_id ?? null;
}

function defaultPairedTAfterColumnId(
  columns: DatasetColumnResponse[],
  beforeColumnId: string | null,
): string | null {
  const candidates = selectablePairedTColumns(columns).filter(
    (column) => column.column_id !== beforeColumnId,
  );
  return candidates[0]?.column_id ?? null;
}

function selectableOneSampleWilcoxonResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function defaultOneSampleWilcoxonResponseColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  const candidates = selectableOneSampleWilcoxonResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableTwoSampleTResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableTwoSampleTGroupColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return selectableEqualVariancesGroupColumns(columns);
}

function defaultTwoSampleTResponseColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableTwoSampleTResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultTwoSampleTGroupColumnId(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string | null {
  const candidates = selectableTwoSampleTGroupColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableMannWhitneyResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableMannWhitneyGroupColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableEqualVariancesGroupColumns(columns);
}

function defaultMannWhitneyResponseColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableMannWhitneyResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultMannWhitneyGroupColumnId(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string | null {
  const candidates = selectableMannWhitneyGroupColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableKruskalWallisResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableKruskalWallisGroupColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableEqualVariancesGroupColumns(columns);
}

function defaultKruskalWallisResponseColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableKruskalWallisResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultKruskalWallisGroupColumnId(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string | null {
  const candidates = selectableKruskalWallisGroupColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableOneWayAnovaResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableOneWayAnovaGroupColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableEqualVariancesGroupColumns(columns);
}

function defaultOneWayAnovaResponseColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableOneWayAnovaResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultOneWayAnovaGroupColumnId(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string | null {
  const candidates = selectableOneWayAnovaGroupColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableOneProportionResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return columns.filter(
    (column) => column.role !== "id" && column.measurement_level !== "id",
  );
}

function defaultOneProportionResponseColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  const candidates = selectableOneProportionResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.measurement_level === "binary")?.column_id ??
    candidates.find((column) => column.measurement_level === "nominal")?.column_id ??
    candidates.find((column) => column.measurement_level === "ordinal")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableTwoProportionResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableOneProportionResponseColumns(columns);
}

function selectableTwoProportionGroupColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableEqualVariancesGroupColumns(columns);
}

function defaultTwoProportionResponseColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  return defaultOneProportionResponseColumnId(columns);
}

function defaultTwoProportionGroupColumnId(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string | null {
  const candidates = selectableTwoProportionGroupColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectableChiSquareAssociationColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return columns.filter(
    (column) => column.role !== "id" && column.measurement_level !== "id",
  );
}

function defaultChiSquareAssociationRowColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  const candidates = selectableChiSquareAssociationColumns(columns);
  return (
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => column.measurement_level === "nominal")?.column_id ??
    candidates.find((column) => column.measurement_level === "binary")?.column_id ??
    candidates.find((column) => column.measurement_level === "ordinal")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultChiSquareAssociationColumnColumnId(
  columns: DatasetColumnResponse[],
  rowColumnId: string | null,
): string | null {
  const candidates = selectableChiSquareAssociationColumns(columns).filter(
    (column) => column.column_id !== rowColumnId,
  );
  return (
    candidates.find((column) => column.measurement_level === "nominal")?.column_id ??
    candidates.find((column) => column.measurement_level === "binary")?.column_id ??
    candidates.find((column) => column.measurement_level === "ordinal")?.column_id ??
    candidates.find((column) => !numericDataTypes.has(column.data_type))?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function selectablePearsonColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableXyCorrelationColumns(columns: DatasetColumnResponse[]): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableIndividualsChartValueColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableIndividualsChartOrderColumns(
  columns: DatasetColumnResponse[],
  valueColumnId: string | null,
): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      column.column_id !== valueColumnId &&
      (numericDataTypes.has(column.data_type) || column.data_type === "datetime"),
  );
}

function selectableSubgroupChartValueColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableSubgroupChartSubgroupColumns(
  columns: DatasetColumnResponse[],
  valueColumnId: string | null,
): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      column.column_id !== valueColumnId &&
      column.data_type !== "datetime" &&
      column.role !== "response" &&
      column.role !== "target",
  );
}

function selectableRunChartValueColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableCapabilityValueColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableGageRrMeasurementColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableGageRrIdentifierColumns(
  columns: DatasetColumnResponse[],
  measurementColumnId: string | null,
): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      column.column_id !== measurementColumnId &&
      column.data_type !== "datetime" &&
      column.role !== "response" &&
      column.role !== "target",
  );
}

function selectableRunChartOrderColumns(
  columns: DatasetColumnResponse[],
  valueColumnId: string | null,
): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      column.column_id !== valueColumnId &&
      (numericDataTypes.has(column.data_type) || column.data_type === "datetime"),
  );
}

function selectableGageRunChartOrderColumns(
  columns: DatasetColumnResponse[],
  roleColumnIds: {
    measurementColumnId: string | null;
    partColumnId: string | null;
    operatorColumnId: string | null;
    replicateColumnId: string | null;
  },
): DatasetColumnResponse[] {
  const excludedIds = new Set(
    [
      roleColumnIds.measurementColumnId,
      roleColumnIds.partColumnId,
      roleColumnIds.operatorColumnId,
      roleColumnIds.replicateColumnId,
    ].filter((columnId): columnId is string => columnId !== null),
  );
  return columns.filter(
    (column) =>
      !excludedIds.has(column.column_id) &&
      (numericDataTypes.has(column.data_type) || column.data_type === "datetime"),
  );
}

function selectableLinearModelResponseColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return selectableDescriptiveColumns(columns);
}

function selectableLinearModelPredictorColumns(
  columns: DatasetColumnResponse[],
): DatasetColumnResponse[] {
  return columns.filter(
    (column) =>
      column.role !== "id" &&
      column.measurement_level !== "id" &&
      (numericDataTypes.has(column.data_type) || isLinearModelCategoricalPredictor(column)),
  );
}

function isLinearModelCategoricalPredictor(column: DatasetColumnResponse): boolean {
  return (
    column.data_type !== "datetime" &&
    (column.data_type === "text" ||
      column.data_type === "boolean" ||
      column.role === "factor" ||
      column.measurement_level === "nominal" ||
      column.measurement_level === "binary" ||
      column.measurement_level === "ordinal")
  );
}

function defaultPearsonXColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectablePearsonColumns(columns);
  return (
    candidates.find((column) => column.role === "feature")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultPearsonYColumnId(
  columns: DatasetColumnResponse[],
  xColumnId: string | null,
): string | null {
  const candidates = selectablePearsonColumns(columns).filter(
    (column) => column.column_id !== xColumnId,
  );
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultXyCorrelationXColumnIds(columns: DatasetColumnResponse[]): string[] {
  const candidates = selectableXyCorrelationColumns(columns);
  return candidates
    .filter((column) => column.role === "feature")
    .concat(candidates.filter((column) => column.role !== "feature"))
    .slice(0, 3)
    .map((column) => column.column_id);
}

function defaultXyCorrelationYColumnIds(columns: DatasetColumnResponse[]): string[] {
  const candidates = selectableXyCorrelationColumns(columns);
  const responseCandidates = candidates.filter(
    (column) => column.role === "response" || column.role === "target",
  );
  return (responseCandidates.length > 0 ? responseCandidates : candidates.slice(1))
    .slice(0, 3)
    .map((column) => column.column_id);
}

function defaultIndividualsChartValueColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  const candidates = selectableIndividualsChartValueColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultSubgroupChartValueColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableSubgroupChartValueColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultSubgroupChartSubgroupColumnId(
  columns: DatasetColumnResponse[],
  valueColumnId: string | null,
): string | null {
  const candidates = selectableSubgroupChartSubgroupColumns(columns, valueColumnId);
  return (
    candidates.find((column) => column.role === "subgroup_id")?.column_id ??
    candidates.find((column) => column.measurement_level === "nominal")?.column_id ??
    candidates.find((column) => column.role === "id")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultRunChartValueColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableRunChartValueColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function parseCapabilityOptionalNumber(
  value: string,
): { kind: "ok"; value: number | null } | { kind: "error" } {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return { kind: "ok", value: null };
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) {
    return { kind: "error" };
  }
  return { kind: "ok", value: parsed };
}

function defaultCapabilityValueColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableCapabilityValueColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultGageRrMeasurementColumnId(columns: DatasetColumnResponse[]): string | null {
  const candidates = selectableGageRrMeasurementColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultGageRrPartColumnId(
  columns: DatasetColumnResponse[],
  measurementColumnId: string | null,
): string | null {
  const candidates = selectableGageRrIdentifierColumns(columns, measurementColumnId);
  return (
    candidates.find((column) => column.role === "part_id")?.column_id ??
    candidates.find((column) => column.measurement_level === "id")?.column_id ??
    candidates.find((column) => column.role === "id")?.column_id ??
    candidates[0]?.column_id ??
    null
  );
}

function defaultGageRrOperatorColumnId(
  columns: DatasetColumnResponse[],
  measurementColumnId: string | null,
): string | null {
  const candidates = selectableGageRrIdentifierColumns(columns, measurementColumnId);
  return (
    candidates.find((column) => column.role === "operator_id")?.column_id ??
    candidates.find((column) => column.measurement_level === "nominal")?.column_id ??
    candidates.find((column) => column.role === "group")?.column_id ??
    candidates.find((column) => column.column_id !== defaultGageRrPartColumnId(
      columns,
      measurementColumnId,
    ))?.column_id ??
    null
  );
}

function defaultGageRrReplicateColumnId(
  columns: DatasetColumnResponse[],
  measurementColumnId: string | null,
): string | null {
  const candidates = selectableGageRrIdentifierColumns(columns, measurementColumnId);
  const usedIds = new Set([
    defaultGageRrPartColumnId(columns, measurementColumnId),
    defaultGageRrOperatorColumnId(columns, measurementColumnId),
  ]);
  return (
    candidates.find((column) => column.role === "replicate_id")?.column_id ??
    candidates.find((column) => column.role === "order")?.column_id ??
    candidates.find((column) => !usedIds.has(column.column_id))?.column_id ??
    null
  );
}

function defaultLinearModelResponseColumnId(
  columns: DatasetColumnResponse[],
): string | null {
  const candidates = selectableLinearModelResponseColumns(columns);
  return (
    candidates.find((column) => column.role === "response")?.column_id ??
    candidates.find((column) => column.role === "target")?.column_id ??
    (candidates.length > 0 ? candidates[candidates.length - 1].column_id : null) ??
    null
  );
}

function defaultLinearModelPredictorColumnIds(
  columns: DatasetColumnResponse[],
  responseColumnId: string | null,
): string[] {
  const candidates = selectableLinearModelPredictorColumns(columns).filter(
    (column) => column.column_id !== responseColumnId,
  );
  return candidates
    .filter((column) => column.role === "feature")
    .concat(candidates.filter((column) => column.role !== "feature"))
    .slice(0, 5)
    .map((column) => column.column_id);
}

function splitLinearModelInteractionKey(key: string): [string, string] {
  const [leftColumnId = "", rightColumnId = ""] = key.split("::");
  return [leftColumnId, rightColumnId];
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

function isEqualVariancesResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is EqualVariancesResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "equal_variances_test" &&
    Array.isArray(candidate.groups) &&
    Array.isArray(candidate.tests)
  );
}

function isOneSampleTResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is OneSampleTResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "one_sample_t_test" &&
    typeof candidate.sample === "object" &&
    candidate.sample !== null &&
    typeof candidate.contrast === "object" &&
    candidate.contrast !== null
  );
}

function isEquivalenceTostResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is EquivalenceTostResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "equivalence_tost" &&
    typeof candidate.sample === "object" &&
    candidate.sample !== null &&
    typeof candidate.estimate === "object" &&
    candidate.estimate !== null &&
    typeof candidate.tests === "object" &&
    candidate.tests !== null &&
    typeof candidate.tost === "object" &&
    candidate.tost !== null
  );
}

function isPairedTResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is PairedTResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "paired_t_test" &&
    typeof candidate.paired_sample === "object" &&
    candidate.paired_sample !== null &&
    typeof candidate.contrast === "object" &&
    candidate.contrast !== null
  );
}

function isOneSampleWilcoxonResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is OneSampleWilcoxonResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "one_sample_wilcoxon_signed_rank_test" &&
    typeof candidate.sample === "object" &&
    candidate.sample !== null &&
    typeof candidate.test === "object" &&
    candidate.test !== null
  );
}

function isTwoSampleTResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is TwoSampleTResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "two_sample_t_test" &&
    Array.isArray(candidate.groups) &&
    typeof candidate.contrast === "object" &&
    candidate.contrast !== null
  );
}

function isMannWhitneyResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is MannWhitneyResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "mann_whitney_u_test" &&
    Array.isArray(candidate.groups) &&
    typeof candidate.test === "object" &&
    candidate.test !== null
  );
}

function isKruskalWallisResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is KruskalWallisResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "kruskal_wallis_test" &&
    Array.isArray(candidate.groups) &&
    typeof candidate.test === "object" &&
    candidate.test !== null &&
    typeof candidate.posthoc === "object" &&
    candidate.posthoc !== null
  );
}

function isOneWayAnovaResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is OneWayAnovaResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "one_way_anova" &&
    Array.isArray(candidate.groups) &&
    typeof candidate.anova_table === "object" &&
    candidate.anova_table !== null &&
    typeof candidate.test === "object" &&
    candidate.test !== null &&
    typeof candidate.posthoc === "object" &&
    candidate.posthoc !== null
  );
}

function isOneProportionResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is OneProportionResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "one_proportion_test" &&
    typeof candidate.sample === "object" &&
    candidate.sample !== null &&
    typeof candidate.test === "object" &&
    candidate.test !== null &&
    typeof candidate.confidence_interval === "object" &&
    candidate.confidence_interval !== null
  );
}

function isTwoProportionResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is TwoProportionResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "two_proportion_test" &&
    Array.isArray(candidate.groups) &&
    typeof candidate.difference === "object" &&
    candidate.difference !== null &&
    typeof candidate.test === "object" &&
    candidate.test !== null
  );
}

function isChiSquareAssociationResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is ChiSquareAssociationResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "chi_square_association" &&
    typeof candidate.contingency_table === "object" &&
    candidate.contingency_table !== null &&
    typeof candidate.test === "object" &&
    candidate.test !== null &&
    typeof candidate.effect_size === "object" &&
    candidate.effect_size !== null
  );
}

function isPearsonCorrelationResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is PearsonCorrelationResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "pearson_correlation" &&
    typeof candidate.association === "object" &&
    candidate.association !== null &&
    typeof candidate.test === "object" &&
    candidate.test !== null &&
    typeof candidate.confidence_interval === "object" &&
    candidate.confidence_interval !== null
  );
}

function isXyCorrelationResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is XyCorrelationResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return candidate.summary_type === "xy_correlation_matrix" && Array.isArray(candidate.pairs);
}

function isIndividualsChartResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is IndividualsChartResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "individuals_chart" &&
    typeof candidate.individuals_chart === "object" &&
    candidate.individuals_chart !== null &&
    typeof candidate.moving_range_chart === "object" &&
    candidate.moving_range_chart !== null &&
    Array.isArray(candidate.signals)
  );
}

function isSubgroupChartResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is SubgroupChartResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "subgroup_chart" &&
    typeof candidate.xbar_chart === "object" &&
    candidate.xbar_chart !== null &&
    (candidate.chart_type === "xbar_s"
      ? typeof candidate.s_chart === "object" && candidate.s_chart !== null
      : typeof candidate.r_chart === "object" && candidate.r_chart !== null) &&
    Array.isArray(candidate.signals)
  );
}

function isRunChartResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is RunChartResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "run_chart" &&
    typeof candidate.runs === "object" &&
    candidate.runs !== null &&
    Array.isArray(candidate.signals) &&
    typeof candidate.chart === "object" &&
    candidate.chart !== null
  );
}

function isCapabilityResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is CapabilityResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "capability_analysis" &&
    typeof candidate.capability === "object" &&
    candidate.capability !== null &&
    typeof candidate.histogram === "object" &&
    candidate.histogram !== null
  );
}

function isGageRrResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is GageRrResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "gage_rr" &&
    Array.isArray(candidate.anova_table) &&
    typeof candidate.variance_components === "object" &&
    candidate.variance_components !== null
  );
}

function isGageRunChartResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is GageRunChartResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "gage_run_chart" &&
    typeof candidate.chart === "object" &&
    candidate.chart !== null &&
    Array.isArray((candidate.chart as Record<string, unknown>).points)
  );
}

function isLinearModelResult(
  value: AnalysisResultEnvelope["result"] | undefined,
): value is LinearModelResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    candidate.summary_type === "linear_model" &&
    typeof candidate.fit === "object" &&
    candidate.fit !== null &&
    Array.isArray(candidate.coefficients) &&
    typeof candidate.diagnostics === "object" &&
    candidate.diagnostics !== null
  );
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
