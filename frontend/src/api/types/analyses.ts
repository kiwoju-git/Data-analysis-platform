import type {
  DescriptiveStatisticsResult,
  EqualVariancesResult,
  GraphicalSummaryResult,
  NormalityResult,
} from "./analysisResultsExploration";
import type {
  ChiSquareAssociationResult,
  OneProportionResult,
  TwoProportionResult,
} from "./analysisResultsCategorical";
import type {
  LinearModelResult,
  PearsonCorrelationResult,
  XyCorrelationResult,
} from "./analysisResultsRegression";
import type {
  AttributeControlChartResult,
  CapabilityResult,
  GageRrResult,
  GageRunChartResult,
  IndividualsChartResult,
  RunChartResult,
  SubgroupChartResult,
} from "./analysisResultsQuality";
import type {
  EquivalenceTostResult,
  KruskalWallisResult,
  MannWhitneyResult,
  OneSampleTResult,
  OneSampleWilcoxonResult,
  OneWayAnovaResult,
  PairedTResult,
  TwoSampleTResult,
} from "./analysisResultsHypothesis";

export type AnalysisModuleId =
  | "exploration"
  | "hypothesis"
  | "categorical"
  | "regression"
  | "quality"
  | "doe";

export type MethodAvailability = "available" | "planned" | "disabled";

export type AnalysisExecutionMode = "inline" | "job";

export interface AnalysisModuleDescriptor {
  module_id: AnalysisModuleId;
  label_ko: string;
  label_en: string;
  order: number;
}

export interface AnalysisMethodDescriptor {
  method_id: string;
  method_version: string;
  module_id: AnalysisModuleId;
  label_ko: string;
  label_en: string;
  availability: MethodAvailability;
  execution_mode: AnalysisExecutionMode;
  requires_dataset: boolean;
  order: number;
  disabled_reason: string | null;
}

export interface AnalysisMethodListResponse {
  modules: AnalysisModuleDescriptor[];
  methods: AnalysisMethodDescriptor[];
}

export type AnalysisFilterOperator =
  | "is_missing"
  | "is_not_missing"
  | "eq"
  | "ne"
  | "gt"
  | "gte"
  | "lt"
  | "lte";

export interface AnalysisFilterCondition {
  column_id: string;
  operator: AnalysisFilterOperator;
  value?: string | number | null;
}

export interface AnalysisFilterSnapshot {
  expression_version: number;
  conditions: AnalysisFilterCondition[];
}

export interface AnalysisRunRequest {
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  filter_snapshot: AnalysisFilterSnapshot;
  roles: Record<string, string>;
  options: Record<string, unknown>;
}

export interface AnalysisWarning {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
}

export interface AnalysisProvenance {
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  source_schema_hash: string | null;
  filter_snapshot_sha256?: string | null;
  row_snapshot_sha256?: string | null;
  row_count_total?: number | null;
  row_count_included?: number | null;
  app_version: string;
  python_version?: string | null;
  platform?: string | null;
  build_commit?: string | null;
  package_versions?: Record<string, string> | null;
}

export interface AnalysisResultEnvelope {
  analysis_id: string;
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  status: "succeeded" | "failed" | "cancelled";
  warnings: AnalysisWarning[];
  provenance: AnalysisProvenance;
  result:
    | DescriptiveStatisticsResult
    | GraphicalSummaryResult
    | NormalityResult
    | EqualVariancesResult
    | OneSampleTResult
    | EquivalenceTostResult
    | PairedTResult
    | OneSampleWilcoxonResult
    | TwoSampleTResult
    | MannWhitneyResult
    | KruskalWallisResult
    | OneWayAnovaResult
    | OneProportionResult
    | TwoProportionResult
    | ChiSquareAssociationResult
    | PearsonCorrelationResult
    | XyCorrelationResult
    | AttributeControlChartResult
    | IndividualsChartResult
    | SubgroupChartResult
    | RunChartResult
    | CapabilityResult
    | GageRrResult
    | GageRunChartResult
    | LinearModelResult
    | Record<string, unknown>
    | null;
}
