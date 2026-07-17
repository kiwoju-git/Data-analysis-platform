import { AnalysisFilterControls } from "./AnalysisFilterControls";
import {
  AnalysisWorkbench,
  type AnalysisWorkbenchComparisonState,
  type AnalysisWorkbenchExportState,
  type AnalysisWorkbenchHistoryState,
  type AnalysisWorkbenchRestoredState,
} from "./AnalysisWorkbench";
import { ChiSquareAssociationPanel } from "./ChiSquareAssociationPanel";
import { DescriptiveAnalysisPanel } from "./DescriptiveAnalysisPanel";
import { EqualVariancesPanel } from "./EqualVariancesPanel";
import { EquivalenceTostPanel } from "./EquivalenceTostPanel";
import { GraphicalSummaryPanel } from "./GraphicalSummaryPanel";
import { KruskalWallisPanel } from "./KruskalWallisPanel";
import type { LinearModelPredictionRowsState } from "./LinearModelPanel";
import { MannWhitneyPanel } from "./MannWhitneyPanel";
import { NormalityAnalysisPanel } from "./NormalityAnalysisPanel";
import { OneProportionPanel } from "./OneProportionPanel";
import { OneWayAnovaPanel } from "./OneWayAnovaPanel";
import { OneSampleTPanel } from "./OneSampleTPanel";
import { OneSampleWilcoxonPanel } from "./OneSampleWilcoxonPanel";
import { PairedTPanel } from "./PairedTPanel";
import { TwoSampleTPanel } from "./TwoSampleTPanel";
import { TwoProportionPanel } from "./TwoProportionPanel";
import {
  AttributeControlChartPanel,
  BayesianOptimizationPanel,
  CapabilityPanel,
  FactorialDesignPanel,
  GageRrPreflightPanel,
  GageRunChartPanel,
  IndividualsChartPanel,
  LinearModelPanel,
  PearsonCorrelationPanel,
  ResponseSurfacePanel,
  RunChartPanel,
  SubgroupChartPanel,
  XyCorrelationPanel,
} from "./lazyAnalysisPanels";
import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
  AnalysisResultEnvelope,
  AttributeControlChartResult,
  AttributeControlChartType,
  CapabilityResult,
  ChiSquareAssociationResult,
  DatasetColumnResponse,
  DatasetProfileResponse,
  DatasetVersionResponse,
  DescriptiveStatisticsResult,
  EqualVariancesResult,
  EquivalenceTostResult,
  FactorialDesignCreateRequest,
  FactorialDesignResponse,
  DoeDesignResponsesResponse,
  DoeDesignResponsesUpsertRequest,
  DoeFactorialAnalysisCreateRequest,
  DoeFactorialAnalysisResponse,
  GageRrPreflightResponse,
  GageRrResult,
  GageRunChartResult,
  GraphicalSummaryResult,
  IndividualsChartResult,
  KruskalWallisResult,
  LinearModelResult,
  MannWhitneyResult,
  NormalityResult,
  OneProportionResult,
  OneWayAnovaResult,
  OneSampleTResult,
  OneSampleWilcoxonResult,
  PairedTResult,
  PearsonCorrelationResult,
  RegressionPredictionPreflightResponse,
  RegressionPredictionResponse,
  RunChartResult,
  SubgroupChartResult,
  TwoSampleTResult,
  TwoProportionResult,
  XyCorrelationResult,
} from "./api";
import type { AnalysisFilterDraft } from "./analysisFilters";
import type {
  AttributeControlPhase,
  AttributeControlPhase2State,
} from "./useAttributeControlPhase2State";
import type { RegressionPredictionTargetState } from "./useRegressionPredictionTargetState";
import type { RegressionPredictionExportState } from "./useRegressionPredictionExportState";

type SubgroupChartType = "xbar_r" | "xbar_s";

interface AnalysisResultByMethod {
  analysisResult: AnalysisResultEnvelope | null;
  graphicalSummaryAnalysisResult: AnalysisResultEnvelope | null;
  normalityAnalysisResult: AnalysisResultEnvelope | null;
  equalVariancesAnalysisResult: AnalysisResultEnvelope | null;
  oneSampleTAnalysisResult: AnalysisResultEnvelope | null;
  equivalenceTostAnalysisResult: AnalysisResultEnvelope | null;
  pairedTAnalysisResult: AnalysisResultEnvelope | null;
  oneSampleWilcoxonAnalysisResult: AnalysisResultEnvelope | null;
  twoSampleTAnalysisResult: AnalysisResultEnvelope | null;
  mannWhitneyAnalysisResult: AnalysisResultEnvelope | null;
  kruskalWallisAnalysisResult: AnalysisResultEnvelope | null;
  oneWayAnovaAnalysisResult: AnalysisResultEnvelope | null;
  oneProportionAnalysisResult: AnalysisResultEnvelope | null;
  twoProportionAnalysisResult: AnalysisResultEnvelope | null;
  chiSquareAssociationAnalysisResult: AnalysisResultEnvelope | null;
  pearsonAnalysisResult: AnalysisResultEnvelope | null;
  xyCorrelationAnalysisResult: AnalysisResultEnvelope | null;
  linearModelAnalysisResult: AnalysisResultEnvelope | null;
  attributeControlChartAnalysisResult: AnalysisResultEnvelope | null;
  individualsChartAnalysisResult: AnalysisResultEnvelope | null;
  subgroupChartAnalysisResult: AnalysisResultEnvelope | null;
  runChartAnalysisResult: AnalysisResultEnvelope | null;
  capabilityAnalysisResult: AnalysisResultEnvelope | null;
  gageRrAnalysisResult: AnalysisResultEnvelope | null;
  gageRunChartAnalysisResult: AnalysisResultEnvelope | null;
}

export interface AnalysisShellProps {
  analysisCatalog: AnalysisMethodListResponse | null;
  analysisCatalogError: string | null;
  analysisFilterDrafts: AnalysisFilterDraft[];
  analysisFilterValidationError: string | null;
  analysisFilterValidationMessage: string | null;
  analysisRunError: string | null;
  analysisResult: AnalysisResultEnvelope | null;
  workbenchComparisonState?: AnalysisWorkbenchComparisonState;
  workbenchExportState?: AnalysisWorkbenchExportState;
  workbenchHistoryState?: AnalysisWorkbenchHistoryState;
  workbenchRestoredState?: AnalysisWorkbenchRestoredState;
  attributeControlChartAnalysisResult?: AnalysisResultEnvelope | null;
  attributeControlChartConstantOpportunityConfirmed?: boolean;
  attributeControlChartCountColumnId?: string | null;
  attributeControlChartCountColumns?: DatasetColumnResponse[];
  attributeControlChartDenominatorColumnId?: string | null;
  attributeControlChartDenominatorColumns?: DatasetColumnResponse[];
  attributeControlChartPhase?: AttributeControlPhase;
  attributeControlPhase2State?: AttributeControlPhase2State;
  attributeControlChartResult?: AttributeControlChartResult | null;
  attributeControlChartType?: AttributeControlChartType;
  capabilityAnalysisResult?: AnalysisResultEnvelope | null;
  capabilityLsl?: string;
  capabilityResult?: CapabilityResult | null;
  capabilityTarget?: string;
  capabilityUsl?: string;
  capabilityValueColumnId?: string | null;
  capabilityValueColumns?: DatasetColumnResponse[];
  chiSquareAssociationAlpha: number;
  chiSquareAssociationAnalysisResult: AnalysisResultEnvelope | null;
  chiSquareAssociationColumnColumnId: string | null;
  chiSquareAssociationColumnColumns: DatasetColumnResponse[];
  chiSquareAssociationResult: ChiSquareAssociationResult | null;
  chiSquareAssociationRowColumnId: string | null;
  chiSquareAssociationRowColumns: DatasetColumnResponse[];
  descriptiveColumns: DatasetColumnResponse[];
  descriptiveResult: DescriptiveStatisticsResult | null;
  equalVariancesAlpha: number;
  equalVariancesAnalysisResult: AnalysisResultEnvelope | null;
  equalVariancesGroupColumnId: string | null;
  equalVariancesGroupColumns: DatasetColumnResponse[];
  equalVariancesResponseColumnId: string | null;
  equalVariancesResponseColumns: DatasetColumnResponse[];
  equalVariancesResult: EqualVariancesResult | null;
  equivalenceTostAlpha: number;
  equivalenceTostAnalysisResult: AnalysisResultEnvelope | null;
  equivalenceTostLowerBound: number;
  equivalenceTostReferenceMean: number;
  equivalenceTostResponseColumnId: string | null;
  equivalenceTostResponseColumns: DatasetColumnResponse[];
  equivalenceTostResult: EquivalenceTostResult | null;
  equivalenceTostUpperBound: number;
  graphicalSummaryAnalysisResult: AnalysisResultEnvelope | null;
  graphicalSummaryColumns: DatasetColumnResponse[];
  graphicalSummaryResult: GraphicalSummaryResult | null;
  factorialDesign?: FactorialDesignResponse | null;
  factorialAnalysis?: DoeFactorialAnalysisResponse | null;
  factorialAnalysisError?: string | null;
  factorialDesignError?: string | null;
  factorialDesignResponseError?: string | null;
  factorialDesignResponses?: DoeDesignResponsesResponse | null;
  gageRrMeasurementColumnId?: string | null;
  gageRrMeasurementColumns?: DatasetColumnResponse[];
  gageRrOperatorColumnId?: string | null;
  gageRrOperatorColumns?: DatasetColumnResponse[];
  gageRrPartColumnId?: string | null;
  gageRrPartColumns?: DatasetColumnResponse[];
  gageRrAnalysisResult?: AnalysisResultEnvelope | null;
  gageRrPreflight?: GageRrPreflightResponse | null;
  gageRrPreflightError?: string | null;
  gageRrReplicateColumnId?: string | null;
  gageRrReplicateColumns?: DatasetColumnResponse[];
  gageRrResult?: GageRrResult | null;
  gageRunChartAnalysisResult?: AnalysisResultEnvelope | null;
  gageRunChartOrderColumnId?: string | null;
  gageRunChartOrderColumns?: DatasetColumnResponse[];
  gageRunChartResult?: GageRunChartResult | null;
  individualsChartAnalysisResult?: AnalysisResultEnvelope | null;
  individualsChartOrderColumnId?: string | null;
  individualsChartOrderColumns?: DatasetColumnResponse[];
  individualsChartResult?: IndividualsChartResult | null;
  individualsChartValueColumnId?: string | null;
  individualsChartValueColumns?: DatasetColumnResponse[];
  isCreatingFactorialDesign?: boolean;
  isRunningFactorialAnalysis?: boolean;
  isSavingFactorialDesignResponses?: boolean;
  isRunningAnalysis: boolean;
  kruskalWallisAlpha: number;
  kruskalWallisAnalysisResult: AnalysisResultEnvelope | null;
  kruskalWallisGroupColumnId: string | null;
  kruskalWallisGroupColumns: DatasetColumnResponse[];
  kruskalWallisResponseColumnId: string | null;
  kruskalWallisResponseColumns: DatasetColumnResponse[];
  kruskalWallisResult: KruskalWallisResult | null;
  linearModelAlpha?: number;
  linearModelAnalysisResult?: AnalysisResultEnvelope | null;
  linearModelConfidenceLevel?: number;
  linearModelInteractionKeys?: string[];
  linearModelPredictorColumnIds?: string[];
  linearModelPredictorColumns?: DatasetColumnResponse[];
  linearModelPrediction?: RegressionPredictionResponse | null;
  linearModelPredictionError?: string | null;
  linearModelPredictionExportState?: RegressionPredictionExportState;
  linearModelPredictionRowsState?: LinearModelPredictionRowsState;
  linearModelPredictionTargetState?: RegressionPredictionTargetState;
  linearModelPredictionPreflight?: RegressionPredictionPreflightResponse | null;
  linearModelPredictionPreflightError?: string | null;
  linearModelQuadraticColumnIds?: string[];
  linearModelResponseColumnId?: string | null;
  linearModelResponseColumns?: DatasetColumnResponse[];
  linearModelResult?: LinearModelResult | null;
  isRunningLinearModelPrediction?: boolean;
  isRunningLinearModelPredictionPreflight?: boolean;
  mannWhitneyAlpha: number;
  mannWhitneyAlternative: string;
  mannWhitneyAnalysisResult: AnalysisResultEnvelope | null;
  mannWhitneyGroupColumnId: string | null;
  mannWhitneyGroupColumns: DatasetColumnResponse[];
  mannWhitneyMethod: string;
  mannWhitneyResponseColumnId: string | null;
  mannWhitneyResponseColumns: DatasetColumnResponse[];
  mannWhitneyResult: MannWhitneyResult | null;
  normalityAlpha: number;
  normalityAnalysisResult: AnalysisResultEnvelope | null;
  normalityColumns: DatasetColumnResponse[];
  normalityResult: NormalityResult | null;
  oneProportionAlpha: number;
  oneProportionAlternative: string;
  oneProportionAnalysisResult: AnalysisResultEnvelope | null;
  oneProportionCiMethod: string;
  oneProportionConfidenceLevel: number;
  oneProportionEventLevel: string;
  oneProportionNullProportion: number;
  oneProportionResponseColumnId: string | null;
  oneProportionResponseColumns: DatasetColumnResponse[];
  oneProportionResult: OneProportionResult | null;
  oneWayAnovaAlpha: number;
  oneWayAnovaAnalysisResult: AnalysisResultEnvelope | null;
  oneWayAnovaConfidenceLevel: number;
  oneWayAnovaGroupColumnId: string | null;
  oneWayAnovaGroupColumns: DatasetColumnResponse[];
  oneWayAnovaResponseColumnId: string | null;
  oneWayAnovaResponseColumns: DatasetColumnResponse[];
  oneWayAnovaResult: OneWayAnovaResult | null;
  oneSampleTAlpha: number;
  oneSampleTAlternative: string;
  oneSampleTAnalysisResult: AnalysisResultEnvelope | null;
  oneSampleTConfidenceLevel: number;
  oneSampleTNullMean: number;
  oneSampleTResponseColumnId: string | null;
  oneSampleTResponseColumns: DatasetColumnResponse[];
  oneSampleTResult: OneSampleTResult | null;
  oneSampleWilcoxonAlpha: number;
  oneSampleWilcoxonAlternative: string;
  oneSampleWilcoxonAnalysisResult: AnalysisResultEnvelope | null;
  oneSampleWilcoxonMethod: string;
  oneSampleWilcoxonNullLocation: number;
  oneSampleWilcoxonResponseColumnId: string | null;
  oneSampleWilcoxonResponseColumns: DatasetColumnResponse[];
  oneSampleWilcoxonResult: OneSampleWilcoxonResult | null;
  oneSampleWilcoxonZeroMethod: string;
  pairedTAfterColumnId: string | null;
  pairedTAfterColumns: DatasetColumnResponse[];
  pairedTAlpha: number;
  pairedTAlternative: string;
  pairedTAnalysisResult: AnalysisResultEnvelope | null;
  pairedTBeforeColumnId: string | null;
  pairedTBeforeColumns: DatasetColumnResponse[];
  pairedTConfidenceLevel: number;
  pairedTNullDifference: number;
  pairedTResult: PairedTResult | null;
  pearsonAlpha: number;
  pearsonAnalysisResult: AnalysisResultEnvelope | null;
  pearsonConfidenceLevel: number;
  pearsonResult: PearsonCorrelationResult | null;
  pearsonXColumnId: string | null;
  pearsonXColumns: DatasetColumnResponse[];
  pearsonYColumnId: string | null;
  pearsonYColumns: DatasetColumnResponse[];
  runChartAnalysisResult?: AnalysisResultEnvelope | null;
  runChartOrderColumnId?: string | null;
  runChartOrderColumns?: DatasetColumnResponse[];
  runChartResult?: RunChartResult | null;
  runChartValueColumnId?: string | null;
  runChartValueColumns?: DatasetColumnResponse[];
  subgroupChartAnalysisResult?: AnalysisResultEnvelope | null;
  subgroupChartResult?: SubgroupChartResult | null;
  subgroupChartSubgroupColumnId?: string | null;
  subgroupChartSubgroupColumns?: DatasetColumnResponse[];
  subgroupChartType?: SubgroupChartType;
  subgroupChartValueColumnId?: string | null;
  subgroupChartValueColumns?: DatasetColumnResponse[];
  xyCorrelationAlpha?: number;
  xyCorrelationAnalysisResult?: AnalysisResultEnvelope | null;
  xyCorrelationConfidenceLevel?: number;
  xyCorrelationResult?: XyCorrelationResult | null;
  xyCorrelationXColumnIds?: string[];
  xyCorrelationXColumns?: DatasetColumnResponse[];
  xyCorrelationYColumnIds?: string[];
  xyCorrelationYColumns?: DatasetColumnResponse[];
  profile: DatasetProfileResponse | null;
  selectedDescriptiveColumnIds: string[];
  selectedGraphicalSummaryColumnIds: string[];
  selectedNormalityColumnIds: string[];
  selectedMethod: AnalysisMethodDescriptor | null;
  selectedMethods: AnalysisMethodDescriptor[];
  selectedModuleId: AnalysisModuleId;
  twoSampleTAlpha: number;
  twoSampleTAlternative: string;
  twoSampleTAnalysisResult: AnalysisResultEnvelope | null;
  twoSampleTConfidenceLevel: number;
  twoSampleTGroupColumnId: string | null;
  twoSampleTGroupColumns: DatasetColumnResponse[];
  twoSampleTResponseColumnId: string | null;
  twoSampleTResponseColumns: DatasetColumnResponse[];
  twoSampleTResult: TwoSampleTResult | null;
  twoSampleTVarianceAssumption: string;
  twoProportionAlpha: number;
  twoProportionAlternative: string;
  twoProportionAnalysisResult: AnalysisResultEnvelope | null;
  twoProportionConfidenceLevel: number;
  twoProportionEventLevel: string;
  twoProportionGroupColumnId: string | null;
  twoProportionGroupColumns: DatasetColumnResponse[];
  twoProportionResponseColumnId: string | null;
  twoProportionResponseColumns: DatasetColumnResponse[];
  twoProportionResult: TwoProportionResult | null;
  version: DatasetVersionResponse | null;
  onAnalysisFilterDraftsChange: (drafts: AnalysisFilterDraft[]) => void;
  onAttributeControlChartConstantOpportunityConfirmedChange?: (confirmed: boolean) => void;
  onAttributeControlChartCountColumnChange?: (columnId: string) => void;
  onAttributeControlChartDenominatorColumnChange?: (columnId: string) => void;
  onAttributeControlChartLimitSetChange?: (limitSetId: string) => void;
  onAttributeControlChartPhaseChange?: (phase: AttributeControlPhase) => void;
  onAttributeControlChartTypeChange?: (chartType: AttributeControlChartType) => void;
  onCapabilityLslChange?: (value: string) => void;
  onCapabilityTargetChange?: (value: string) => void;
  onCapabilityUslChange?: (value: string) => void;
  onCapabilityValueColumnChange?: (columnId: string) => void;
  onGageRrMeasurementColumnChange?: (columnId: string) => void;
  onGageRrOperatorColumnChange?: (columnId: string) => void;
  onGageRrPartColumnChange?: (columnId: string) => void;
  onGageRrReplicateColumnChange?: (columnId: string) => void;
  onGageRunChartOrderColumnChange?: (columnId: string) => void;
  onCreateFactorialDesign?: (request: FactorialDesignCreateRequest) => void;
  onRunFactorialAnalysis?: (
    designId: string,
    request: DoeFactorialAnalysisCreateRequest,
  ) => void;
  onSaveFactorialDesignResponses?: (
    designId: string,
    request: DoeDesignResponsesUpsertRequest,
  ) => void;
  onRunChiSquareAssociationAnalysis: () => void;
  onRunAttributeControlChartAnalysis?: () => void;
  onRunDescriptiveAnalysis: () => void;
  onRunEqualVariancesAnalysis: () => void;
  onRunEquivalenceTostAnalysis: () => void;
  onRunGraphicalSummaryAnalysis: () => void;
  onRunGageRrAnalysis?: () => void;
  onRunGageRrPreflight?: () => void;
  onRunGageRunChartAnalysis?: () => void;
  onRunIndividualsChartAnalysis?: () => void;
  onRunKruskalWallisAnalysis: () => void;
  onRunLinearModelAnalysis?: () => void;
  onRunLinearModelPrediction?: () => void;
  onRunLinearModelPredictionPreflight?: () => void;
  onRunMannWhitneyAnalysis: () => void;
  onRunNormalityAnalysis: () => void;
  onRunOneProportionAnalysis: () => void;
  onRunOneWayAnovaAnalysis: () => void;
  onRunOneSampleTAnalysis: () => void;
  onRunOneSampleWilcoxonAnalysis: () => void;
  onRunPairedTAnalysis: () => void;
  onRunPearsonAnalysis: () => void;
  onRunChartAnalysis?: () => void;
  onRunCapabilityAnalysis?: () => void;
  onRunSubgroupChartAnalysis?: () => void;
  onRunTwoSampleTAnalysis: () => void;
  onRunTwoProportionAnalysis: () => void;
  onRunXyCorrelationAnalysis?: () => void;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  onChiSquareAssociationAlphaChange: (alpha: number) => void;
  onChiSquareAssociationColumnColumnChange: (columnId: string) => void;
  onChiSquareAssociationRowColumnChange: (columnId: string) => void;
  onEqualVariancesAlphaChange: (alpha: number) => void;
  onEqualVariancesGroupColumnChange: (columnId: string) => void;
  onEqualVariancesResponseColumnChange: (columnId: string) => void;
  onEquivalenceTostAlphaChange: (alpha: number) => void;
  onEquivalenceTostLowerBoundChange: (lowerBound: number) => void;
  onEquivalenceTostReferenceMeanChange: (referenceMean: number) => void;
  onEquivalenceTostResponseColumnChange: (columnId: string) => void;
  onEquivalenceTostUpperBoundChange: (upperBound: number) => void;
  onKruskalWallisAlphaChange: (alpha: number) => void;
  onKruskalWallisGroupColumnChange: (columnId: string) => void;
  onKruskalWallisResponseColumnChange: (columnId: string) => void;
  onLinearModelAlphaChange?: (alpha: number) => void;
  onLinearModelConfidenceLevelChange?: (confidenceLevel: number) => void;
  onLinearModelResponseColumnChange?: (columnId: string) => void;
  onToggleLinearModelInteractionTerm?: (key: string, checked: boolean) => void;
  onMannWhitneyAlphaChange: (alpha: number) => void;
  onMannWhitneyAlternativeChange: (alternative: string) => void;
  onMannWhitneyGroupColumnChange: (columnId: string) => void;
  onMannWhitneyMethodChange: (method: string) => void;
  onMannWhitneyResponseColumnChange: (columnId: string) => void;
  onNormalityAlphaChange: (alpha: number) => void;
  onOneProportionAlphaChange: (alpha: number) => void;
  onOneProportionAlternativeChange: (alternative: string) => void;
  onOneProportionCiMethodChange: (ciMethod: string) => void;
  onOneProportionConfidenceLevelChange: (confidenceLevel: number) => void;
  onOneProportionEventLevelChange: (eventLevel: string) => void;
  onOneProportionNullProportionChange: (nullProportion: number) => void;
  onOneProportionResponseColumnChange: (columnId: string) => void;
  onOneWayAnovaAlphaChange: (alpha: number) => void;
  onOneWayAnovaConfidenceLevelChange: (confidenceLevel: number) => void;
  onOneWayAnovaGroupColumnChange: (columnId: string) => void;
  onOneWayAnovaResponseColumnChange: (columnId: string) => void;
  onOneSampleTAlphaChange: (alpha: number) => void;
  onOneSampleTAlternativeChange: (alternative: string) => void;
  onOneSampleTConfidenceLevelChange: (confidenceLevel: number) => void;
  onOneSampleTNullMeanChange: (nullMean: number) => void;
  onOneSampleTResponseColumnChange: (columnId: string) => void;
  onOneSampleWilcoxonAlphaChange: (alpha: number) => void;
  onOneSampleWilcoxonAlternativeChange: (alternative: string) => void;
  onOneSampleWilcoxonMethodChange: (method: string) => void;
  onOneSampleWilcoxonNullLocationChange: (nullLocation: number) => void;
  onOneSampleWilcoxonResponseColumnChange: (columnId: string) => void;
  onOneSampleWilcoxonZeroMethodChange: (zeroMethod: string) => void;
  onPairedTAfterColumnChange: (columnId: string) => void;
  onPairedTAlphaChange: (alpha: number) => void;
  onPairedTAlternativeChange: (alternative: string) => void;
  onPairedTBeforeColumnChange: (columnId: string) => void;
  onPairedTConfidenceLevelChange: (confidenceLevel: number) => void;
  onPairedTNullDifferenceChange: (nullDifference: number) => void;
  onPearsonAlphaChange: (alpha: number) => void;
  onPearsonConfidenceLevelChange: (confidenceLevel: number) => void;
  onPearsonXColumnChange: (columnId: string) => void;
  onPearsonYColumnChange: (columnId: string) => void;
  onRunChartOrderColumnChange?: (columnId: string) => void;
  onRunChartValueColumnChange?: (columnId: string) => void;
  onSubgroupChartSubgroupColumnChange?: (columnId: string) => void;
  onSubgroupChartTypeChange?: (chartType: SubgroupChartType) => void;
  onSubgroupChartValueColumnChange?: (columnId: string) => void;
  onIndividualsChartOrderColumnChange?: (columnId: string | null) => void;
  onIndividualsChartValueColumnChange?: (columnId: string) => void;
  onXyCorrelationAlphaChange?: (alpha: number) => void;
  onXyCorrelationConfidenceLevelChange?: (confidenceLevel: number) => void;
  onTwoSampleTAlphaChange: (alpha: number) => void;
  onTwoSampleTAlternativeChange: (alternative: string) => void;
  onTwoSampleTConfidenceLevelChange: (confidenceLevel: number) => void;
  onTwoSampleTGroupColumnChange: (columnId: string) => void;
  onTwoSampleTResponseColumnChange: (columnId: string) => void;
  onTwoSampleTVarianceAssumptionChange: (varianceAssumption: string) => void;
  onTwoProportionAlphaChange: (alpha: number) => void;
  onTwoProportionAlternativeChange: (alternative: string) => void;
  onTwoProportionConfidenceLevelChange: (confidenceLevel: number) => void;
  onTwoProportionEventLevelChange: (eventLevel: string) => void;
  onTwoProportionGroupColumnChange: (columnId: string) => void;
  onTwoProportionResponseColumnChange: (columnId: string) => void;
  onToggleDescriptiveColumn: (columnId: string, checked: boolean) => void;
  onToggleGraphicalSummaryColumn: (columnId: string, checked: boolean) => void;
  onToggleNormalityColumn: (columnId: string, checked: boolean) => void;
  onToggleLinearModelPredictorColumn?: (columnId: string, checked: boolean) => void;
  onToggleLinearModelQuadraticColumn?: (columnId: string, checked: boolean) => void;
  onToggleXyCorrelationXColumn?: (columnId: string, checked: boolean) => void;
  onToggleXyCorrelationYColumn?: (columnId: string, checked: boolean) => void;
}

export function AnalysisShell({
  analysisCatalog,
  analysisCatalogError,
  analysisFilterDrafts,
  analysisFilterValidationError,
  analysisFilterValidationMessage,
  analysisRunError,
  analysisResult,
  workbenchComparisonState,
  workbenchExportState,
  workbenchHistoryState,
  workbenchRestoredState,
  attributeControlChartAnalysisResult = null,
  attributeControlChartConstantOpportunityConfirmed = false,
  attributeControlChartCountColumnId = null,
  attributeControlChartCountColumns = [],
  attributeControlChartDenominatorColumnId = null,
  attributeControlChartDenominatorColumns = [],
  attributeControlChartPhase = "phase_1",
  attributeControlPhase2State,
  attributeControlChartResult = null,
  attributeControlChartType = "p",
  capabilityAnalysisResult = null,
  capabilityLsl = "",
  capabilityResult = null,
  capabilityTarget = "",
  capabilityUsl = "",
  capabilityValueColumnId = null,
  capabilityValueColumns = [],
  chiSquareAssociationAlpha,
  chiSquareAssociationAnalysisResult,
  chiSquareAssociationColumnColumnId,
  chiSquareAssociationColumnColumns,
  chiSquareAssociationResult,
  chiSquareAssociationRowColumnId,
  chiSquareAssociationRowColumns,
  descriptiveColumns,
  descriptiveResult,
  equalVariancesAlpha,
  equalVariancesAnalysisResult,
  equalVariancesGroupColumnId,
  equalVariancesGroupColumns,
  equalVariancesResponseColumnId,
  equalVariancesResponseColumns,
  equalVariancesResult,
  equivalenceTostAlpha,
  equivalenceTostAnalysisResult,
  equivalenceTostLowerBound,
  equivalenceTostReferenceMean,
  equivalenceTostResponseColumnId,
  equivalenceTostResponseColumns,
  equivalenceTostResult,
  equivalenceTostUpperBound,
  graphicalSummaryAnalysisResult,
  graphicalSummaryColumns,
  graphicalSummaryResult,
  factorialDesign = null,
  factorialAnalysis = null,
  factorialAnalysisError = null,
  factorialDesignError = null,
  factorialDesignResponseError = null,
  factorialDesignResponses = null,
  gageRrMeasurementColumnId = null,
  gageRrMeasurementColumns = [],
  gageRrOperatorColumnId = null,
  gageRrOperatorColumns = [],
  gageRrPartColumnId = null,
  gageRrPartColumns = [],
  gageRrAnalysisResult = null,
  gageRrPreflight = null,
  gageRrPreflightError = null,
  gageRrReplicateColumnId = null,
  gageRrReplicateColumns = [],
  gageRrResult = null,
  gageRunChartAnalysisResult = null,
  gageRunChartOrderColumnId = null,
  gageRunChartOrderColumns = [],
  gageRunChartResult = null,
  isCreatingFactorialDesign = false,
  isRunningFactorialAnalysis = false,
  isSavingFactorialDesignResponses = false,
  isRunningAnalysis,
  kruskalWallisAlpha,
  kruskalWallisAnalysisResult,
  kruskalWallisGroupColumnId,
  kruskalWallisGroupColumns,
  kruskalWallisResponseColumnId,
  kruskalWallisResponseColumns,
  kruskalWallisResult,
  linearModelAlpha = 0.05,
  linearModelAnalysisResult = null,
  linearModelConfidenceLevel = 0.95,
  linearModelInteractionKeys = [],
  linearModelPredictorColumnIds = [],
  linearModelPredictorColumns = [],
  linearModelPrediction = null,
  linearModelPredictionError = null,
  linearModelPredictionExportState = {
    csvExport: null,
    error: null,
    isCreating: false,
    isDownloading: false,
    onCreate: () => undefined,
    onDownload: () => undefined,
  },
  linearModelPredictionRowsState = {
    error: null,
    isLoading: false,
    page: null,
    onPageChange: () => undefined,
  },
  linearModelPredictionTargetState = {
    catalog: null,
    error: null,
    isLoading: false,
    selectedTarget: null,
    selectedTargetVersionId: null,
    onPageChange: () => undefined,
    onSelect: () => undefined,
  },
  linearModelPredictionPreflight = null,
  linearModelPredictionPreflightError = null,
  linearModelQuadraticColumnIds = [],
  linearModelResponseColumnId = null,
  linearModelResponseColumns = [],
  linearModelResult = null,
  isRunningLinearModelPrediction = false,
  isRunningLinearModelPredictionPreflight = false,
  mannWhitneyAlpha,
  mannWhitneyAlternative,
  mannWhitneyAnalysisResult,
  mannWhitneyGroupColumnId,
  mannWhitneyGroupColumns,
  mannWhitneyMethod,
  mannWhitneyResponseColumnId,
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
  oneProportionResponseColumnId,
  oneProportionResponseColumns,
  oneProportionResult,
  oneWayAnovaAlpha,
  oneWayAnovaAnalysisResult,
  oneWayAnovaConfidenceLevel,
  oneWayAnovaGroupColumnId,
  oneWayAnovaGroupColumns,
  oneWayAnovaResponseColumnId,
  oneWayAnovaResponseColumns,
  oneWayAnovaResult,
  oneSampleTAlpha,
  oneSampleTAlternative,
  oneSampleTAnalysisResult,
  oneSampleTConfidenceLevel,
  oneSampleTNullMean,
  oneSampleTResponseColumnId,
  oneSampleTResponseColumns,
  oneSampleTResult,
  oneSampleWilcoxonAlpha,
  oneSampleWilcoxonAlternative,
  oneSampleWilcoxonAnalysisResult,
  oneSampleWilcoxonMethod,
  oneSampleWilcoxonNullLocation,
  oneSampleWilcoxonResponseColumnId,
  oneSampleWilcoxonResponseColumns,
  oneSampleWilcoxonResult,
  oneSampleWilcoxonZeroMethod,
  pairedTAfterColumnId,
  pairedTAfterColumns,
  pairedTAlpha,
  pairedTAlternative,
  pairedTAnalysisResult,
  pairedTBeforeColumnId,
  pairedTBeforeColumns,
  pairedTConfidenceLevel,
  pairedTNullDifference,
  pairedTResult,
  pearsonAlpha,
  pearsonAnalysisResult,
  pearsonConfidenceLevel,
  pearsonResult,
  pearsonXColumnId,
  pearsonXColumns,
  pearsonYColumnId,
  pearsonYColumns,
  individualsChartAnalysisResult = null,
  individualsChartOrderColumnId = null,
  individualsChartOrderColumns = [],
  individualsChartResult = null,
  individualsChartValueColumnId = null,
  individualsChartValueColumns = [],
  runChartAnalysisResult = null,
  runChartOrderColumnId = null,
  runChartOrderColumns = [],
  runChartResult = null,
  runChartValueColumnId = null,
  runChartValueColumns = [],
  subgroupChartAnalysisResult = null,
  subgroupChartResult = null,
  subgroupChartSubgroupColumnId = null,
  subgroupChartSubgroupColumns = [],
  subgroupChartType = "xbar_r",
  subgroupChartValueColumnId = null,
  subgroupChartValueColumns = [],
  xyCorrelationAlpha = 0.05,
  xyCorrelationAnalysisResult = null,
  xyCorrelationConfidenceLevel = 0.95,
  xyCorrelationResult = null,
  xyCorrelationXColumnIds = [],
  xyCorrelationXColumns = [],
  xyCorrelationYColumnIds = [],
  xyCorrelationYColumns = [],
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
  twoSampleTGroupColumnId,
  twoSampleTGroupColumns,
  twoSampleTResponseColumnId,
  twoSampleTResponseColumns,
  twoSampleTResult,
  twoSampleTVarianceAssumption,
  twoProportionAlpha,
  twoProportionAlternative,
  twoProportionAnalysisResult,
  twoProportionConfidenceLevel,
  twoProportionEventLevel,
  twoProportionGroupColumnId,
  twoProportionGroupColumns,
  twoProportionResponseColumnId,
  twoProportionResponseColumns,
  twoProportionResult,
  version,
  onAnalysisFilterDraftsChange,
  onAttributeControlChartConstantOpportunityConfirmedChange = () => undefined,
  onAttributeControlChartCountColumnChange = () => undefined,
  onAttributeControlChartDenominatorColumnChange = () => undefined,
  onAttributeControlChartLimitSetChange = () => undefined,
  onAttributeControlChartPhaseChange = () => undefined,
  onAttributeControlChartTypeChange = () => undefined,
  onCapabilityLslChange = () => undefined,
  onCapabilityTargetChange = () => undefined,
  onCapabilityUslChange = () => undefined,
  onCapabilityValueColumnChange = () => undefined,
  onGageRrMeasurementColumnChange = () => undefined,
  onGageRrOperatorColumnChange = () => undefined,
  onGageRrPartColumnChange = () => undefined,
  onGageRrReplicateColumnChange = () => undefined,
  onGageRunChartOrderColumnChange = () => undefined,
  onCreateFactorialDesign = () => undefined,
  onRunFactorialAnalysis = () => undefined,
  onSaveFactorialDesignResponses = () => undefined,
  onRunAttributeControlChartAnalysis = () => undefined,
  onRunChiSquareAssociationAnalysis,
  onRunDescriptiveAnalysis,
  onRunEqualVariancesAnalysis,
  onRunEquivalenceTostAnalysis,
  onRunGraphicalSummaryAnalysis,
  onRunGageRrAnalysis = () => undefined,
  onRunGageRrPreflight = () => undefined,
  onRunGageRunChartAnalysis = () => undefined,
  onRunIndividualsChartAnalysis = () => undefined,
  onRunKruskalWallisAnalysis,
  onRunLinearModelAnalysis = () => undefined,
  onRunLinearModelPrediction = () => undefined,
  onRunLinearModelPredictionPreflight = () => undefined,
  onRunMannWhitneyAnalysis,
  onRunNormalityAnalysis,
  onRunOneProportionAnalysis,
  onRunOneWayAnovaAnalysis,
  onRunOneSampleTAnalysis,
  onRunOneSampleWilcoxonAnalysis,
  onRunPairedTAnalysis,
  onRunPearsonAnalysis,
  onRunChartAnalysis = () => undefined,
  onRunCapabilityAnalysis = () => undefined,
  onRunSubgroupChartAnalysis = () => undefined,
  onRunTwoSampleTAnalysis,
  onRunTwoProportionAnalysis,
  onRunXyCorrelationAnalysis = () => undefined,
  onSelectMethod,
  onChiSquareAssociationAlphaChange,
  onChiSquareAssociationColumnColumnChange,
  onChiSquareAssociationRowColumnChange,
  onEqualVariancesAlphaChange,
  onEqualVariancesGroupColumnChange,
  onEqualVariancesResponseColumnChange,
  onEquivalenceTostAlphaChange,
  onEquivalenceTostLowerBoundChange,
  onEquivalenceTostReferenceMeanChange,
  onEquivalenceTostResponseColumnChange,
  onEquivalenceTostUpperBoundChange,
  onKruskalWallisAlphaChange,
  onKruskalWallisGroupColumnChange,
  onKruskalWallisResponseColumnChange,
  onLinearModelAlphaChange = () => undefined,
  onLinearModelConfidenceLevelChange = () => undefined,
  onLinearModelResponseColumnChange = () => undefined,
  onToggleLinearModelInteractionTerm = () => undefined,
  onMannWhitneyAlphaChange,
  onMannWhitneyAlternativeChange,
  onMannWhitneyGroupColumnChange,
  onMannWhitneyMethodChange,
  onMannWhitneyResponseColumnChange,
  onNormalityAlphaChange,
  onOneProportionAlphaChange,
  onOneProportionAlternativeChange,
  onOneProportionCiMethodChange,
  onOneProportionConfidenceLevelChange,
  onOneProportionEventLevelChange,
  onOneProportionNullProportionChange,
  onOneProportionResponseColumnChange,
  onOneWayAnovaAlphaChange,
  onOneWayAnovaConfidenceLevelChange,
  onOneWayAnovaGroupColumnChange,
  onOneWayAnovaResponseColumnChange,
  onOneSampleTAlphaChange,
  onOneSampleTAlternativeChange,
  onOneSampleTConfidenceLevelChange,
  onOneSampleTNullMeanChange,
  onOneSampleTResponseColumnChange,
  onOneSampleWilcoxonAlphaChange,
  onOneSampleWilcoxonAlternativeChange,
  onOneSampleWilcoxonMethodChange,
  onOneSampleWilcoxonNullLocationChange,
  onOneSampleWilcoxonResponseColumnChange,
  onOneSampleWilcoxonZeroMethodChange,
  onPairedTAfterColumnChange,
  onPairedTAlphaChange,
  onPairedTAlternativeChange,
  onPairedTBeforeColumnChange,
  onPairedTConfidenceLevelChange,
  onPairedTNullDifferenceChange,
  onPearsonAlphaChange,
  onPearsonConfidenceLevelChange,
  onPearsonXColumnChange,
  onPearsonYColumnChange,
  onIndividualsChartOrderColumnChange = () => undefined,
  onIndividualsChartValueColumnChange = () => undefined,
  onRunChartOrderColumnChange = () => undefined,
  onRunChartValueColumnChange = () => undefined,
  onSubgroupChartSubgroupColumnChange = () => undefined,
  onSubgroupChartTypeChange = () => undefined,
  onSubgroupChartValueColumnChange = () => undefined,
  onXyCorrelationAlphaChange = () => undefined,
  onXyCorrelationConfidenceLevelChange = () => undefined,
  onTwoSampleTAlphaChange,
  onTwoSampleTAlternativeChange,
  onTwoSampleTConfidenceLevelChange,
  onTwoSampleTGroupColumnChange,
  onTwoSampleTResponseColumnChange,
  onTwoSampleTVarianceAssumptionChange,
  onTwoProportionAlphaChange,
  onTwoProportionAlternativeChange,
  onTwoProportionConfidenceLevelChange,
  onTwoProportionEventLevelChange,
  onTwoProportionGroupColumnChange,
  onTwoProportionResponseColumnChange,
  onToggleDescriptiveColumn,
  onToggleGraphicalSummaryColumn,
  onToggleNormalityColumn,
  onToggleLinearModelPredictorColumn = () => undefined,
  onToggleLinearModelQuadraticColumn = () => undefined,
  onToggleXyCorrelationXColumn = () => undefined,
  onToggleXyCorrelationYColumn = () => undefined,
}: AnalysisShellProps) {
  const selectedModule =
    analysisCatalog?.modules.find((module) => module.module_id === selectedModuleId) ?? null;
  const selectedAnalysisResult =
    selectedMethod === null
      ? null
      : selectedAnalysisResultForMethod(selectedMethod.method_id, {
          analysisResult,
          graphicalSummaryAnalysisResult,
          normalityAnalysisResult,
          equalVariancesAnalysisResult,
          oneSampleTAnalysisResult,
          equivalenceTostAnalysisResult,
          pairedTAnalysisResult,
          oneSampleWilcoxonAnalysisResult,
          twoSampleTAnalysisResult,
          mannWhitneyAnalysisResult,
          kruskalWallisAnalysisResult,
          oneWayAnovaAnalysisResult,
          oneProportionAnalysisResult,
          twoProportionAnalysisResult,
          chiSquareAssociationAnalysisResult,
          pearsonAnalysisResult,
          xyCorrelationAnalysisResult,
          linearModelAnalysisResult,
          attributeControlChartAnalysisResult,
          individualsChartAnalysisResult,
          subgroupChartAnalysisResult,
          runChartAnalysisResult,
          capabilityAnalysisResult,
          gageRrAnalysisResult,
          gageRunChartAnalysisResult,
        });
  return (
    <section className="analysis-shell" aria-labelledby="analysis-modules-title">
      <div className="analysis-heading">
        <div>
          <h2 id="analysis-modules-title">분석 모듈</h2>
          {selectedModule !== null ? (
            <p>
              {selectedModule.label_ko} · {selectedModule.label_en}
            </p>
          ) : null}
        </div>
        <span className="status-pill">Gate B0</span>
      </div>
      {analysisCatalogError !== null ? (
        <div className="notice-box">분석 메서드 registry를 불러오지 못했습니다.</div>
      ) : null}
      {analysisCatalog === null && analysisCatalogError === null ? (
        <div className="notice-box">분석 메서드 조회 중</div>
      ) : null}
      {analysisCatalog !== null ? (
        <AnalysisWorkbench
          analysisRunError={analysisRunError}
          catalog={analysisCatalog}
          comparisonState={workbenchComparisonState}
          exportState={workbenchExportState}
          historyState={workbenchHistoryState}
          profile={profile}
          restoredState={workbenchRestoredState}
          selectedAnalysisResult={selectedAnalysisResult}
          selectedMethod={selectedMethod}
          selectedMethods={selectedMethods}
          selectedModuleId={selectedModuleId}
          version={version}
          onSelectMethod={onSelectMethod}
          renderAnalysisFilters={(method) =>
            method.requires_dataset && version !== null ? (
              <>
                <AnalysisFilterControls
                  columns={version.columns}
                  drafts={analysisFilterDrafts}
                  onChange={onAnalysisFilterDraftsChange}
                />
                {analysisFilterValidationMessage !== null ? (
                  <div className="error-box">{analysisFilterValidationMessage}</div>
                ) : null}
              </>
            ) : null
          }
          renderExecutableMethod={(method) => {
            if (method.method_id === "eda.descriptive" && method.availability === "available") {
              return (
                <DescriptiveAnalysisPanel
                  analysisResult={analysisResult}
                  descriptiveColumns={descriptiveColumns}
                  descriptiveResult={descriptiveResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  selectedColumnIds={selectedDescriptiveColumnIds}
                  version={version}
                  onRun={onRunDescriptiveAnalysis}
                  onToggleColumn={onToggleDescriptiveColumn}
                />
              );
            }
            if (
              method.method_id === "eda.graphical_summary" &&
              method.availability === "available"
            ) {
              return (
                <GraphicalSummaryPanel
                  analysisResult={graphicalSummaryAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  graphicalColumns={graphicalSummaryColumns}
                  graphicalResult={graphicalSummaryResult}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  selectedColumnIds={selectedGraphicalSummaryColumnIds}
                  version={version}
                  onRun={onRunGraphicalSummaryAnalysis}
                  onToggleColumn={onToggleGraphicalSummaryColumn}
                />
              );
            }
            if (method.method_id === "eda.normality" && method.availability === "available") {
              return (
                <NormalityAnalysisPanel
                  alpha={normalityAlpha}
                  analysisResult={normalityAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  normalityColumns={normalityColumns}
                  normalityResult={normalityResult}
                  selectedColumnIds={selectedNormalityColumnIds}
                  version={version}
                  onAlphaChange={onNormalityAlphaChange}
                  onRun={onRunNormalityAnalysis}
                  onToggleColumn={onToggleNormalityColumn}
                />
              );
            }
            if (
              method.method_id === "eda.equal_variances" &&
              method.availability === "available"
            ) {
              return (
                <EqualVariancesPanel
                  alpha={equalVariancesAlpha}
                  analysisResult={equalVariancesAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  groupColumnId={equalVariancesGroupColumnId}
                  groupColumns={equalVariancesGroupColumns}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  responseColumnId={equalVariancesResponseColumnId}
                  responseColumns={equalVariancesResponseColumns}
                  result={equalVariancesResult}
                  version={version}
                  onAlphaChange={onEqualVariancesAlphaChange}
                  onGroupColumnChange={onEqualVariancesGroupColumnChange}
                  onResponseColumnChange={onEqualVariancesResponseColumnChange}
                  onRun={onRunEqualVariancesAnalysis}
                />
              );
            }
            if (
              method.method_id === "hypothesis.one_sample_t" &&
              method.availability === "available"
            ) {
              return (
                <OneSampleTPanel
                  alpha={oneSampleTAlpha}
                  alternative={oneSampleTAlternative}
                  analysisResult={oneSampleTAnalysisResult}
                  confidenceLevel={oneSampleTConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  nullMean={oneSampleTNullMean}
                  responseColumnId={oneSampleTResponseColumnId}
                  responseColumns={oneSampleTResponseColumns}
                  result={oneSampleTResult}
                  version={version}
                  onAlphaChange={onOneSampleTAlphaChange}
                  onAlternativeChange={onOneSampleTAlternativeChange}
                  onConfidenceLevelChange={onOneSampleTConfidenceLevelChange}
                  onNullMeanChange={onOneSampleTNullMeanChange}
                  onResponseColumnChange={onOneSampleTResponseColumnChange}
                  onRun={onRunOneSampleTAnalysis}
                />
              );
            }
            if (
              method.method_id === "hypothesis.equivalence_tost" &&
              method.availability === "available"
            ) {
              return (
                <EquivalenceTostPanel
                  alpha={equivalenceTostAlpha}
                  analysisResult={equivalenceTostAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  lowerBound={equivalenceTostLowerBound}
                  methodId={method.method_id}
                  referenceMean={equivalenceTostReferenceMean}
                  responseColumnId={equivalenceTostResponseColumnId}
                  responseColumns={equivalenceTostResponseColumns}
                  result={equivalenceTostResult}
                  upperBound={equivalenceTostUpperBound}
                  version={version}
                  onAlphaChange={onEquivalenceTostAlphaChange}
                  onLowerBoundChange={onEquivalenceTostLowerBoundChange}
                  onReferenceMeanChange={onEquivalenceTostReferenceMeanChange}
                  onResponseColumnChange={onEquivalenceTostResponseColumnChange}
                  onRun={onRunEquivalenceTostAnalysis}
                  onUpperBoundChange={onEquivalenceTostUpperBoundChange}
                />
              );
            }
            if (
              method.method_id === "hypothesis.one_sample_wilcoxon" &&
              method.availability === "available"
            ) {
              return (
                <OneSampleWilcoxonPanel
                  alpha={oneSampleWilcoxonAlpha}
                  alternative={oneSampleWilcoxonAlternative}
                  analysisResult={oneSampleWilcoxonAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  method={oneSampleWilcoxonMethod}
                  methodId={method.method_id}
                  nullLocation={oneSampleWilcoxonNullLocation}
                  responseColumnId={oneSampleWilcoxonResponseColumnId}
                  responseColumns={oneSampleWilcoxonResponseColumns}
                  result={oneSampleWilcoxonResult}
                  version={version}
                  zeroMethod={oneSampleWilcoxonZeroMethod}
                  onAlphaChange={onOneSampleWilcoxonAlphaChange}
                  onAlternativeChange={onOneSampleWilcoxonAlternativeChange}
                  onMethodChange={onOneSampleWilcoxonMethodChange}
                  onNullLocationChange={onOneSampleWilcoxonNullLocationChange}
                  onResponseColumnChange={onOneSampleWilcoxonResponseColumnChange}
                  onRun={onRunOneSampleWilcoxonAnalysis}
                  onZeroMethodChange={onOneSampleWilcoxonZeroMethodChange}
                />
              );
            }
            if (method.method_id === "hypothesis.paired_t" && method.availability === "available") {
              return (
                <PairedTPanel
                  afterColumnId={pairedTAfterColumnId}
                  afterColumns={pairedTAfterColumns}
                  alpha={pairedTAlpha}
                  alternative={pairedTAlternative}
                  analysisResult={pairedTAnalysisResult}
                  beforeColumnId={pairedTBeforeColumnId}
                  beforeColumns={pairedTBeforeColumns}
                  confidenceLevel={pairedTConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  nullDifference={pairedTNullDifference}
                  result={pairedTResult}
                  version={version}
                  onAfterColumnChange={onPairedTAfterColumnChange}
                  onAlphaChange={onPairedTAlphaChange}
                  onAlternativeChange={onPairedTAlternativeChange}
                  onBeforeColumnChange={onPairedTBeforeColumnChange}
                  onConfidenceLevelChange={onPairedTConfidenceLevelChange}
                  onNullDifferenceChange={onPairedTNullDifferenceChange}
                  onRun={onRunPairedTAnalysis}
                />
              );
            }
            if (
              method.method_id === "hypothesis.two_sample_t" &&
              method.availability === "available"
            ) {
              return (
                <TwoSampleTPanel
                  alpha={twoSampleTAlpha}
                  alternative={twoSampleTAlternative}
                  analysisResult={twoSampleTAnalysisResult}
                  confidenceLevel={twoSampleTConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  groupColumnId={twoSampleTGroupColumnId}
                  groupColumns={twoSampleTGroupColumns}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  responseColumnId={twoSampleTResponseColumnId}
                  responseColumns={twoSampleTResponseColumns}
                  result={twoSampleTResult}
                  varianceAssumption={twoSampleTVarianceAssumption}
                  version={version}
                  onAlphaChange={onTwoSampleTAlphaChange}
                  onAlternativeChange={onTwoSampleTAlternativeChange}
                  onConfidenceLevelChange={onTwoSampleTConfidenceLevelChange}
                  onGroupColumnChange={onTwoSampleTGroupColumnChange}
                  onResponseColumnChange={onTwoSampleTResponseColumnChange}
                  onRun={onRunTwoSampleTAnalysis}
                  onVarianceAssumptionChange={onTwoSampleTVarianceAssumptionChange}
                />
              );
            }
            if (
              method.method_id === "hypothesis.mann_whitney" &&
              method.availability === "available"
            ) {
              return (
                <MannWhitneyPanel
                  alpha={mannWhitneyAlpha}
                  alternative={mannWhitneyAlternative}
                  analysisResult={mannWhitneyAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  groupColumnId={mannWhitneyGroupColumnId}
                  groupColumns={mannWhitneyGroupColumns}
                  isRunningAnalysis={isRunningAnalysis}
                  method={mannWhitneyMethod}
                  methodId={method.method_id}
                  responseColumnId={mannWhitneyResponseColumnId}
                  responseColumns={mannWhitneyResponseColumns}
                  result={mannWhitneyResult}
                  version={version}
                  onAlphaChange={onMannWhitneyAlphaChange}
                  onAlternativeChange={onMannWhitneyAlternativeChange}
                  onGroupColumnChange={onMannWhitneyGroupColumnChange}
                  onMethodChange={onMannWhitneyMethodChange}
                  onResponseColumnChange={onMannWhitneyResponseColumnChange}
                  onRun={onRunMannWhitneyAnalysis}
                />
              );
            }
            if (
              method.method_id === "hypothesis.one_way_anova" &&
              method.availability === "available"
            ) {
              return (
                <OneWayAnovaPanel
                  alpha={oneWayAnovaAlpha}
                  analysisResult={oneWayAnovaAnalysisResult}
                  confidenceLevel={oneWayAnovaConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  groupColumnId={oneWayAnovaGroupColumnId}
                  groupColumns={oneWayAnovaGroupColumns}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  responseColumnId={oneWayAnovaResponseColumnId}
                  responseColumns={oneWayAnovaResponseColumns}
                  result={oneWayAnovaResult}
                  version={version}
                  onAlphaChange={onOneWayAnovaAlphaChange}
                  onConfidenceLevelChange={onOneWayAnovaConfidenceLevelChange}
                  onGroupColumnChange={onOneWayAnovaGroupColumnChange}
                  onResponseColumnChange={onOneWayAnovaResponseColumnChange}
                  onRun={onRunOneWayAnovaAnalysis}
                />
              );
            }
            if (
              method.method_id === "hypothesis.kruskal_wallis" &&
              method.availability === "available"
            ) {
              return (
                <KruskalWallisPanel
                  alpha={kruskalWallisAlpha}
                  analysisResult={kruskalWallisAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  groupColumnId={kruskalWallisGroupColumnId}
                  groupColumns={kruskalWallisGroupColumns}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  responseColumnId={kruskalWallisResponseColumnId}
                  responseColumns={kruskalWallisResponseColumns}
                  result={kruskalWallisResult}
                  version={version}
                  onAlphaChange={onKruskalWallisAlphaChange}
                  onGroupColumnChange={onKruskalWallisGroupColumnChange}
                  onResponseColumnChange={onKruskalWallisResponseColumnChange}
                  onRun={onRunKruskalWallisAnalysis}
                />
              );
            }
            if (
              method.method_id === "categorical.one_proportion" &&
              method.availability === "available"
            ) {
              return (
                <OneProportionPanel
                  alpha={oneProportionAlpha}
                  alternative={oneProportionAlternative}
                  analysisResult={oneProportionAnalysisResult}
                  ciMethod={oneProportionCiMethod}
                  confidenceLevel={oneProportionConfidenceLevel}
                  eventLevel={oneProportionEventLevel}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  nullProportion={oneProportionNullProportion}
                  responseColumnId={oneProportionResponseColumnId}
                  responseColumns={oneProportionResponseColumns}
                  result={oneProportionResult}
                  version={version}
                  onAlphaChange={onOneProportionAlphaChange}
                  onAlternativeChange={onOneProportionAlternativeChange}
                  onCiMethodChange={onOneProportionCiMethodChange}
                  onConfidenceLevelChange={onOneProportionConfidenceLevelChange}
                  onEventLevelChange={onOneProportionEventLevelChange}
                  onNullProportionChange={onOneProportionNullProportionChange}
                  onResponseColumnChange={onOneProportionResponseColumnChange}
                  onRun={onRunOneProportionAnalysis}
                />
              );
            }
            if (
              method.method_id === "categorical.two_proportion" &&
              method.availability === "available"
            ) {
              return (
                <TwoProportionPanel
                  alpha={twoProportionAlpha}
                  alternative={twoProportionAlternative}
                  analysisResult={twoProportionAnalysisResult}
                  confidenceLevel={twoProportionConfidenceLevel}
                  eventLevel={twoProportionEventLevel}
                  filterValidationError={analysisFilterValidationError}
                  groupColumnId={twoProportionGroupColumnId}
                  groupColumns={twoProportionGroupColumns}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  responseColumnId={twoProportionResponseColumnId}
                  responseColumns={twoProportionResponseColumns}
                  result={twoProportionResult}
                  version={version}
                  onAlphaChange={onTwoProportionAlphaChange}
                  onAlternativeChange={onTwoProportionAlternativeChange}
                  onConfidenceLevelChange={onTwoProportionConfidenceLevelChange}
                  onEventLevelChange={onTwoProportionEventLevelChange}
                  onGroupColumnChange={onTwoProportionGroupColumnChange}
                  onResponseColumnChange={onTwoProportionResponseColumnChange}
                  onRun={onRunTwoProportionAnalysis}
                />
              );
            }
            if (
              method.method_id === "categorical.chi_square_association" &&
              method.availability === "available"
            ) {
              return (
                <ChiSquareAssociationPanel
                  alpha={chiSquareAssociationAlpha}
                  analysisResult={chiSquareAssociationAnalysisResult}
                  columnColumnId={chiSquareAssociationColumnColumnId}
                  columnColumns={chiSquareAssociationColumnColumns}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  result={chiSquareAssociationResult}
                  rowColumnId={chiSquareAssociationRowColumnId}
                  rowColumns={chiSquareAssociationRowColumns}
                  version={version}
                  onAlphaChange={onChiSquareAssociationAlphaChange}
                  onColumnColumnChange={onChiSquareAssociationColumnColumnChange}
                  onRowColumnChange={onChiSquareAssociationRowColumnChange}
                  onRun={onRunChiSquareAssociationAnalysis}
                />
              );
            }
            if (method.method_id === "regression.pearson" && method.availability === "available") {
              return (
                <PearsonCorrelationPanel
                  alpha={pearsonAlpha}
                  analysisResult={pearsonAnalysisResult}
                  confidenceLevel={pearsonConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  result={pearsonResult}
                  version={version}
                  xColumnId={pearsonXColumnId}
                  xColumns={pearsonXColumns}
                  yColumnId={pearsonYColumnId}
                  yColumns={pearsonYColumns}
                  onAlphaChange={onPearsonAlphaChange}
                  onConfidenceLevelChange={onPearsonConfidenceLevelChange}
                  onRun={onRunPearsonAnalysis}
                  onXColumnChange={onPearsonXColumnChange}
                  onYColumnChange={onPearsonYColumnChange}
                />
              );
            }
            if (
              method.method_id === "regression.xy_correlation" &&
              method.availability === "available"
            ) {
              return (
                <XyCorrelationPanel
                  alpha={xyCorrelationAlpha}
                  analysisResult={xyCorrelationAnalysisResult}
                  confidenceLevel={xyCorrelationConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  result={xyCorrelationResult}
                  version={version}
                  xColumnIds={xyCorrelationXColumnIds}
                  xColumns={xyCorrelationXColumns}
                  yColumnIds={xyCorrelationYColumnIds}
                  yColumns={xyCorrelationYColumns}
                  onAlphaChange={onXyCorrelationAlphaChange}
                  onConfidenceLevelChange={onXyCorrelationConfidenceLevelChange}
                  onRun={onRunXyCorrelationAnalysis}
                  onToggleXColumn={onToggleXyCorrelationXColumn}
                  onToggleYColumn={onToggleXyCorrelationYColumn}
                />
              );
            }
            if (
              method.method_id === "regression.linear_model" &&
              method.availability === "available"
            ) {
              return (
                <LinearModelPanel
                  alpha={linearModelAlpha}
                  analysisResult={linearModelAnalysisResult}
                  confidenceLevel={linearModelConfidenceLevel}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  interactionKeys={linearModelInteractionKeys}
                  predictorColumnIds={linearModelPredictorColumnIds}
                  predictorColumns={linearModelPredictorColumns}
                  prediction={linearModelPrediction}
                  predictionError={linearModelPredictionError}
                  predictionExportState={linearModelPredictionExportState}
                  predictionRowsState={linearModelPredictionRowsState}
                  predictionTargetState={linearModelPredictionTargetState}
                  predictionPreflight={linearModelPredictionPreflight}
                  predictionPreflightError={linearModelPredictionPreflightError}
                  quadraticColumnIds={linearModelQuadraticColumnIds}
                  responseColumnId={linearModelResponseColumnId}
                  responseColumns={linearModelResponseColumns}
                  result={linearModelResult}
                  isRunningPrediction={isRunningLinearModelPrediction}
                  isRunningPredictionPreflight={isRunningLinearModelPredictionPreflight}
                  version={version}
                  onAlphaChange={onLinearModelAlphaChange}
                  onConfidenceLevelChange={onLinearModelConfidenceLevelChange}
                  onResponseColumnChange={onLinearModelResponseColumnChange}
                  onRun={onRunLinearModelAnalysis}
                  onRunPrediction={onRunLinearModelPrediction}
                  onRunPredictionPreflight={onRunLinearModelPredictionPreflight}
                  onToggleInteractionTerm={onToggleLinearModelInteractionTerm}
                  onTogglePredictorColumn={onToggleLinearModelPredictorColumn}
                  onToggleQuadraticColumn={onToggleLinearModelQuadraticColumn}
                />
              );
            }
            if (
              method.method_id === "quality.attribute_control_chart" &&
              method.availability === "available"
            ) {
              return (
                <AttributeControlChartPanel
                  analysisResult={attributeControlChartAnalysisResult}
                  chartType={attributeControlChartType}
                  constantOpportunityConfirmed={
                    attributeControlChartConstantOpportunityConfirmed
                  }
                  countColumnId={attributeControlChartCountColumnId}
                  countColumns={attributeControlChartCountColumns}
                  denominatorColumnId={attributeControlChartDenominatorColumnId}
                  denominatorColumns={attributeControlChartDenominatorColumns}
                  phase={attributeControlChartPhase}
                  phase2State={attributeControlPhase2State}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  result={attributeControlChartResult}
                  version={version}
                  onChartTypeChange={onAttributeControlChartTypeChange}
                  onConstantOpportunityConfirmedChange={
                    onAttributeControlChartConstantOpportunityConfirmedChange
                  }
                  onCountColumnChange={onAttributeControlChartCountColumnChange}
                  onDenominatorColumnChange={onAttributeControlChartDenominatorColumnChange}
                  onLimitSetChange={onAttributeControlChartLimitSetChange}
                  onPhaseChange={onAttributeControlChartPhaseChange}
                  onRun={onRunAttributeControlChartAnalysis}
                />
              );
            }
            if (method.method_id === "quality.run_chart" && method.availability === "available") {
              return (
                <RunChartPanel
                  analysisResult={runChartAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  orderColumnId={runChartOrderColumnId}
                  orderColumns={runChartOrderColumns}
                  result={runChartResult}
                  valueColumnId={runChartValueColumnId}
                  valueColumns={runChartValueColumns}
                  version={version}
                  onOrderColumnChange={onRunChartOrderColumnChange}
                  onRun={onRunChartAnalysis}
                  onValueColumnChange={onRunChartValueColumnChange}
                />
              );
            }
            if (
              method.method_id === "quality.capability" &&
              method.availability === "available"
            ) {
              return (
                <CapabilityPanel
                  analysisResult={capabilityAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  lsl={capabilityLsl}
                  methodId={method.method_id}
                  result={capabilityResult}
                  target={capabilityTarget}
                  usl={capabilityUsl}
                  valueColumnId={capabilityValueColumnId}
                  valueColumns={capabilityValueColumns}
                  version={version}
                  onLslChange={onCapabilityLslChange}
                  onRun={onRunCapabilityAnalysis}
                  onTargetChange={onCapabilityTargetChange}
                  onUslChange={onCapabilityUslChange}
                  onValueColumnChange={onCapabilityValueColumnChange}
                />
              );
            }
            if (method.method_id === "quality.gage_rr") {
              return (
                <GageRrPreflightPanel
                  analysisResult={gageRrAnalysisResult}
                  error={gageRrPreflightError}
                  filterValidationError={analysisFilterValidationError}
                  isRunning={isRunningAnalysis}
                  measurementColumnId={gageRrMeasurementColumnId}
                  measurementColumns={gageRrMeasurementColumns}
                  methodId={method.method_id}
                  operatorColumnId={gageRrOperatorColumnId}
                  operatorColumns={gageRrOperatorColumns}
                  partColumnId={gageRrPartColumnId}
                  partColumns={gageRrPartColumns}
                  preflight={gageRrPreflight}
                  replicateColumnId={gageRrReplicateColumnId}
                  replicateColumns={gageRrReplicateColumns}
                  result={gageRrResult}
                  version={version}
                  onMeasurementColumnChange={onGageRrMeasurementColumnChange}
                  onOperatorColumnChange={onGageRrOperatorColumnChange}
                  onPartColumnChange={onGageRrPartColumnChange}
                  onReplicateColumnChange={onGageRrReplicateColumnChange}
                  onRunAnalysis={onRunGageRrAnalysis}
                  onRunPreflight={onRunGageRrPreflight}
                />
              );
            }
            if (
              method.method_id === "quality.gage_run_chart" &&
              method.availability === "available"
            ) {
              return (
                <GageRunChartPanel
                  analysisResult={gageRunChartAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  measurementColumnId={gageRrMeasurementColumnId}
                  measurementColumns={gageRrMeasurementColumns}
                  methodId={method.method_id}
                  operatorColumnId={gageRrOperatorColumnId}
                  operatorColumns={gageRrOperatorColumns}
                  orderColumnId={gageRunChartOrderColumnId}
                  orderColumns={gageRunChartOrderColumns}
                  partColumnId={gageRrPartColumnId}
                  partColumns={gageRrPartColumns}
                  replicateColumnId={gageRrReplicateColumnId}
                  replicateColumns={gageRrReplicateColumns}
                  result={gageRunChartResult}
                  version={version}
                  onMeasurementColumnChange={onGageRrMeasurementColumnChange}
                  onOperatorColumnChange={onGageRrOperatorColumnChange}
                  onOrderColumnChange={onGageRunChartOrderColumnChange}
                  onPartColumnChange={onGageRrPartColumnChange}
                  onReplicateColumnChange={onGageRrReplicateColumnChange}
                  onRun={onRunGageRunChartAnalysis}
                />
              );
            }
            if (
              method.method_id === "quality.subgroup_chart" &&
              method.availability === "available"
            ) {
              return (
                <SubgroupChartPanel
                  analysisResult={subgroupChartAnalysisResult}
                  chartType={subgroupChartType}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  result={subgroupChartResult}
                  subgroupColumnId={subgroupChartSubgroupColumnId}
                  subgroupColumns={subgroupChartSubgroupColumns}
                  valueColumnId={subgroupChartValueColumnId}
                  valueColumns={subgroupChartValueColumns}
                  version={version}
                  onChartTypeChange={onSubgroupChartTypeChange}
                  onRun={onRunSubgroupChartAnalysis}
                  onSubgroupColumnChange={onSubgroupChartSubgroupColumnChange}
                  onValueColumnChange={onSubgroupChartValueColumnChange}
                />
              );
            }
            if (
              method.method_id === "quality.individuals_chart" &&
              method.availability === "available"
            ) {
              return (
                <IndividualsChartPanel
                  analysisResult={individualsChartAnalysisResult}
                  filterValidationError={analysisFilterValidationError}
                  isRunningAnalysis={isRunningAnalysis}
                  methodId={method.method_id}
                  orderColumnId={individualsChartOrderColumnId}
                  orderColumns={individualsChartOrderColumns}
                  result={individualsChartResult}
                  valueColumnId={individualsChartValueColumnId}
                  valueColumns={individualsChartValueColumns}
                  version={version}
                  onOrderColumnChange={onIndividualsChartOrderColumnChange}
                  onRun={onRunIndividualsChartAnalysis}
                  onValueColumnChange={onIndividualsChartValueColumnChange}
                />
              );
            }
            if (
              method.method_id === "doe.factorial_design" &&
              method.availability === "available"
            ) {
              return (
                <FactorialDesignPanel
                  analysis={factorialAnalysis}
                  analysisError={factorialAnalysisError}
                  design={factorialDesign}
                  error={factorialDesignError}
                  isCreating={isCreatingFactorialDesign}
                  isRunningAnalysis={isRunningFactorialAnalysis}
                  isSavingResponses={isSavingFactorialDesignResponses}
                  methodId={method.method_id}
                  onCreateDesign={onCreateFactorialDesign}
                  onRunAnalysis={onRunFactorialAnalysis}
                  onSaveResponses={onSaveFactorialDesignResponses}
                  responseError={factorialDesignResponseError}
                  responses={factorialDesignResponses}
                />
              );
            }
            if (
              method.method_id === "doe.response_surface" &&
              method.availability === "available"
            ) {
              return <ResponseSurfacePanel />;
            }
            if (
              method.method_id === "doe.bayesian_optimization" &&
              method.availability === "available"
            ) {
              return <BayesianOptimizationPanel />;
            }
            return null;
          }}
        />
      ) : null}
    </section>
  );
}

function selectedAnalysisResultForMethod(
  methodId: string,
  results: AnalysisResultByMethod,
): AnalysisResultEnvelope | null {
  switch (methodId) {
    case "eda.descriptive":
      return results.analysisResult;
    case "eda.graphical_summary":
      return results.graphicalSummaryAnalysisResult;
    case "eda.normality":
      return results.normalityAnalysisResult;
    case "eda.equal_variances":
      return results.equalVariancesAnalysisResult;
    case "hypothesis.one_sample_t":
      return results.oneSampleTAnalysisResult;
    case "hypothesis.equivalence_tost":
      return results.equivalenceTostAnalysisResult;
    case "hypothesis.paired_t":
      return results.pairedTAnalysisResult;
    case "hypothesis.one_sample_wilcoxon":
      return results.oneSampleWilcoxonAnalysisResult;
    case "hypothesis.two_sample_t":
      return results.twoSampleTAnalysisResult;
    case "hypothesis.mann_whitney":
      return results.mannWhitneyAnalysisResult;
    case "hypothesis.kruskal_wallis":
      return results.kruskalWallisAnalysisResult;
    case "hypothesis.one_way_anova":
      return results.oneWayAnovaAnalysisResult;
    case "categorical.one_proportion":
      return results.oneProportionAnalysisResult;
    case "categorical.two_proportion":
      return results.twoProportionAnalysisResult;
    case "categorical.chi_square_association":
      return results.chiSquareAssociationAnalysisResult;
    case "regression.pearson":
      return results.pearsonAnalysisResult;
    case "regression.xy_correlation":
      return results.xyCorrelationAnalysisResult;
    case "regression.linear_model":
      return results.linearModelAnalysisResult;
    case "quality.attribute_control_chart":
      return results.attributeControlChartAnalysisResult;
    case "quality.individuals_chart":
      return results.individualsChartAnalysisResult;
    case "quality.subgroup_chart":
      return results.subgroupChartAnalysisResult;
    case "quality.run_chart":
      return results.runChartAnalysisResult;
    case "quality.capability":
      return results.capabilityAnalysisResult;
    case "quality.gage_rr":
      return results.gageRrAnalysisResult;
    case "quality.gage_run_chart":
      return results.gageRunChartAnalysisResult;
    default:
      return null;
  }
}
