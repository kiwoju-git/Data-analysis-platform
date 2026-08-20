export interface RegressionPredictionPreflightRequest {
  dataset_version_id: string;
}

export interface RegressionPredictionPreflightIssue {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  source_column_id: string | null;
  target_column_id: string | null;
  display_name: string | null;
  count: number | null;
}

export interface RegressionPredictionColumnMapping {
  source_column_id: string;
  display_name: string;
  predictor_kind: "numeric" | "categorical";
  target_column_id: string | null;
  match_type: "column_id" | "display_name" | "missing" | "ambiguous";
  status: "ok" | "warning" | "error";
}

export interface RegressionPredictionNumericCheck {
  source_column_id: string;
  target_column_id: string;
  display_name: string;
  training_min: number | null;
  training_max: number | null;
  n_valid: number;
  n_missing: number;
  n_non_numeric: number;
  n_below_training_range: number;
  n_above_training_range: number;
}

export interface RegressionPredictionCategoricalCheck {
  source_column_id: string;
  target_column_id: string;
  display_name: string;
  training_level_count: number;
  n_valid: number;
  n_missing: number;
  n_unseen_level: number;
}

export interface RegressionPredictionPreflightResponse {
  model_id: string;
  analysis_id: string;
  source_dataset_version_id: string;
  target_dataset_version_id: string;
  model_manifest_sha256: string;
  source_schema_hash: string;
  source_schema_hash_current: string | null;
  source_analysis_stale: boolean | null;
  target_schema_hash: string;
  schema_hash_match: boolean;
  row_count_total: number;
  row_count_usable: number;
  prediction_ready: boolean;
  required_columns: RegressionPredictionColumnMapping[];
  numeric_checks: RegressionPredictionNumericCheck[];
  categorical_checks: RegressionPredictionCategoricalCheck[];
  issues: RegressionPredictionPreflightIssue[];
}

export interface RegressionPredictionRequest {
  dataset_version_id: string;
  confidence_level: number;
  missing_policy: "complete_case";
  include_intervals: boolean;
}

export interface RegressionPredictionWarning {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  count: number | null;
}

export interface RegressionPredictionInterval {
  method: "t";
  level: number;
  lower: number;
  upper: number;
}

export interface RegressionPredictionRow {
  row_index: number;
  predicted_mean: number;
  mean_confidence_interval: RegressionPredictionInterval | null;
  prediction_interval: RegressionPredictionInterval | null;
  warnings: string[];
}

export interface RegressionModelManifestResponse {
  model_id: string;
  analysis_id: string;
  dataset_version_id: string;
  method_id: string;
  method_version: string;
  schema_hash: string;
  manifest_sha256: string;
  created_at: string;
  app_version: string;
  manifest: Record<string, unknown>;
}

export interface RegressionModelCatalogResponseColumn {
  column_id: string;
  display_name: string;
  data_type: string;
  measurement_level: string;
  unit: string | null;
}

export interface RegressionModelCatalogItem {
  model_id: string;
  source_analysis_id: string;
  source_dataset_version_id: string;
  method_id: "regression.linear_model" | "regression.partial_least_squares";
  method_version: string;
  schema_hash: string;
  response: RegressionModelCatalogResponseColumn | null;
  predictor_count: number | null;
  created_at: string;
  availability: "available" | "source_stale" | "integrity_error";
  availability_code: string | null;
  user_label: string | null;
  note: string | null;
  pinned: boolean;
  metadata_updated_at: string | null;
}

export interface RegressionModelMetadataUpdateRequest {
  user_label?: string | null;
  note?: string | null;
  pinned?: boolean | null;
  expected_metadata_updated_at?: string | null;
}

export interface RegressionModelMetadataResponse {
  model_id: string;
  user_label: string | null;
  note: string | null;
  pinned: boolean;
  metadata_updated_at: string;
}

export interface RegressionModelCatalogResponse {
  models: RegressionModelCatalogItem[];
  total: number;
  returned: number;
  limit: number;
  offset: number;
  has_previous: boolean;
  has_next: boolean;
}

export interface PlsPointPredictionRequest {
  expected_model_manifest_sha256: string;
  rows: Array<{
    client_row_id: string;
    values: Record<string, number>;
  }>;
}

export interface PlsPointPredictionResponse {
  model_id: string;
  model_manifest_sha256: string;
  response_column_id: string;
  row_count: number;
  intervals_supported: false;
  rows: Array<{
    client_row_id: string;
    predicted_value: number;
    warnings: string[];
  }>;
}

export interface RegressionModelDeletionCounts {
  regression_model_count: 1;
  manifest_artifact_count: 1;
  manifest_file_count: 1;
  manifest_file_bytes: number;
  metadata_record_count: number;
  dependent_prediction_count: number;
  dependent_prediction_file_count: number;
  dependent_prediction_export_count: number;
  dependent_prediction_file_bytes: number;
  dependent_pasted_prediction_count: number;
  dependent_optimization_count: number;
}

export interface RegressionModelDependentPredictionDescriptor {
  prediction_id: string;
  analysis_id: string;
  target_dataset_version_id: string | null;
  target_dataset_display_name: string;
  created_at: string;
  completed_at: string | null;
  row_count_total: number;
  row_count_predicted: number;
  row_count_excluded: number;
  stale: boolean;
  result_available: boolean;
  deletion_ready: boolean;
  blocker_codes: string[];
}

export interface RegressionModelDependentPredictionPage {
  model_id: string;
  offset: number;
  limit: number;
  total: number;
  returned: number;
  has_previous: boolean;
  has_next: boolean;
  predictions: RegressionModelDependentPredictionDescriptor[];
}

export interface RegressionModelDeletionPreflightResponse {
  preflight_schema_version: 3;
  model_id: string;
  source_analysis_id: string;
  method_id: "regression.linear_model";
  method_version: string;
  deletion_ready: boolean;
  cascade_deletion_ready: boolean;
  blockers: string[];
  cascade_blockers: string[];
  counts: RegressionModelDeletionCounts;
  deletion_manifest_sha256: string;
  cascade_deletion_manifest_sha256: string | null;
  dependent_predictions: RegressionModelDependentPredictionDescriptor[];
  dependent_predictions_truncated: boolean;
}

export interface RegressionModelDeleteRequest {
  confirmation_model_id: string;
  expected_deletion_manifest_sha256: string;
  mode?: "model_only" | "model_and_predictions";
}

export interface RegressionModelDeleteResponse {
  deletion_schema_version: 3;
  model_id: string;
  source_analysis_id: string;
  deletion_manifest_sha256: string;
  deleted_at: string;
  deleted_counts: RegressionModelDeletionCounts;
  deletion_mode: "model_only" | "model_and_predictions";
  cleanup_status: "deleted" | "quarantined_pending_cleanup";
}

export interface RegressionPredictionProvenance extends AnalysisProvenance {
  source_analysis_id: string;
  source_analysis_stale_at_prediction: boolean;
  source_dataset_version_id: string;
  source_schema_hash_at_fit: string;
  source_schema_hash_current: string;
  target_dataset_version_id: string;
  target_schema_hash: string;
  model_id: string;
  model_manifest_sha256: string;
  prediction_schema_version: number;
  model_manifest_schema_version: number;
  missing_policy: "complete_case";
  confidence_level: number;
  include_intervals: boolean;
  source_canonical_artifact_sha256: string;
  target_canonical_artifact_sha256: string;
  created_at: string;
}

export interface RegressionPredictionResponse {
  prediction_id: string;
  model_id: string;
  analysis_id: string;
  source_analysis_id: string;
  source_dataset_version_id: string;
  target_dataset_version_id: string;
  model_manifest_sha256: string;
  target_schema_hash: string;
  row_count_total: number;
  row_count_predicted: number;
  row_count_excluded: number;
  row_count_omitted: number;
  row_limit: number;
  truncated: boolean;
  confidence_level: number;
  warnings: RegressionPredictionWarning[];
  provenance: RegressionPredictionProvenance;
  columns: RegressionPredictionColumnMapping[];
  rows: RegressionPredictionRow[];
}

export interface RegressionPredictionRowsPageResponse {
  prediction_id: string;
  model_id: string;
  offset: number;
  limit: number;
  total: number;
  returned: number;
  has_previous: boolean;
  has_next: boolean;
  rows: RegressionPredictionRow[];
}

export interface RegressionPredictionCsvExportResponse {
  schema_version: number;
  export_id: string;
  prediction_id: string;
  format: "regression_prediction_csv";
  artifact_kind: "regression_prediction_csv_export";
  media_type: "text/csv";
  sha256: string;
  size_bytes: number;
  source_result_sha256: string;
  stale: boolean;
  created_at: string;
  columns: string[];
  row_count: number;
  preview_rows: string[][];
}

export interface RegressionPastedPredictionColumnMappingRequest {
  input_column_index: number;
  source_column_id: string;
}

export interface RegressionPastedPredictionInput {
  content: string;
  has_header: boolean;
  delimiter: "auto" | "tab" | "comma";
  column_mappings: RegressionPastedPredictionColumnMappingRequest[];
}

export interface RegressionPastedPredictionPreflightRequest
  extends RegressionPastedPredictionInput {
  expected_model_manifest_sha256: string;
}

export interface RegressionPastedPredictionExecuteRequest
  extends RegressionPastedPredictionPreflightRequest {
  expected_normalized_input_sha256: string;
  confidence_level: number;
  include_intervals: boolean;
}

export interface RegressionPastedPredictionMapping {
  input_column_index: number;
  input_column_name: string;
  source_column_id: string;
  display_name: string;
  predictor_kind: "numeric" | "categorical";
}

export interface RegressionPastedPredictionPreflightResponse {
  input_schema_version: 1;
  model_id: string;
  model_manifest_sha256: string;
  normalized_input_sha256: string;
  delimiter: "tab" | "comma";
  has_header: boolean;
  row_count_total: number;
  row_count_usable: number;
  row_count_excluded: number;
  prediction_ready: boolean;
  mappings: RegressionPastedPredictionMapping[];
  preview_rows: string[][];
  issues: RegressionPredictionPreflightIssue[];
}

export interface RegressionPastedPredictionRow extends RegressionPredictionRow {
  predictor_values: Record<string, number | string>;
}

export interface RegressionPastedPredictionResponse {
  prediction_id: string;
  input_kind: "pasted_table";
  model_id: string;
  source_analysis_id: string;
  source_dataset_version_id: string;
  model_manifest_sha256: string;
  normalized_input_sha256: string;
  row_count_total: number;
  row_count_predicted: number;
  row_count_excluded: number;
  row_count_omitted: number;
  row_limit: number;
  truncated: boolean;
  confidence_level: number;
  warnings: RegressionPredictionWarning[];
  mappings: RegressionPastedPredictionMapping[];
  rows: RegressionPastedPredictionRow[];
  created_at: string;
}

export interface RegressionPastedPredictionRowsPageResponse {
  prediction_id: string;
  model_id: string;
  offset: number;
  limit: number;
  total: number;
  returned: number;
  has_previous: boolean;
  has_next: boolean;
  rows: RegressionPastedPredictionRow[];
}

export interface RegressionResponseOptimizationRequest {
  expected_model_manifest_sha256: string;
  goal: {
    kind: "maximize" | "minimize" | "target" | "range";
    lower: number | null;
    target: number | null;
    upper: number | null;
  };
  factor_bounds: Array<{ column_id: string; lower: number; upper: number }>;
  fixed_categorical_levels: Array<{ column_id: string; level: string }>;
  linear_constraints: Array<{
    name: string;
    coefficients: Record<string, number>;
    relation: "less_than_or_equal" | "greater_than_or_equal";
    bound: number;
  }>;
  search: {
    random_seed: number;
    random_candidate_count: number;
    multi_start_count: number;
    max_iterations: number;
    max_evaluations: number;
    profile_point_count: number;
  };
}

export interface RegressionResponseOptimizationProfilePoint {
  predictor_value: number | string;
  predicted_response: number;
  desirability: number;
}

export interface RegressionResponseOptimizationProfile {
  column_id: string;
  display_name: string;
  kind: "numeric" | "categorical";
  fixed_at: number | string;
  conditional_on_other_predictors_at_optimum: true;
  points: RegressionResponseOptimizationProfilePoint[];
}

export interface RegressionResponseOptimizationResult {
  schema_version: 1;
  summary_type: "regression_response_optimizer";
  method: string;
  goal: {
    kind: "maximize" | "minimize" | "target" | "range";
    lower: number | null;
    target: number | null;
    upper: number | null;
    scale: "response_units";
  };
  recommendation: {
    predictor_settings: Record<string, number | string>;
    predicted_response: number;
    individual_desirability: number;
    overall_desirability: number;
    within_training_domain: boolean;
    all_constraints_satisfied: boolean;
  };
  factor_region: {
    training_domains: Array<Record<string, unknown>>;
    search_bounds: Array<{ column_id: string; lower: number; upper: number }>;
    fixed_categorical_levels: Record<string, string>;
    categorical_combination_count: number;
    linear_constraints: Array<Record<string, unknown>>;
  };
  profiles: RegressionResponseOptimizationProfile[];
  search: {
    evaluation_count: number;
    termination_reason: string;
    global_optimum_guaranteed: false;
  } & Record<string, unknown>;
  warnings: string[];
  optimization_id: string;
  model_id: string;
  source_analysis_id: string;
  source_dataset_version_id: string;
  model_manifest_sha256: string;
}

export interface RegressionResponseOptimizationResponse {
  optimization_id: string;
  model_id: string;
  source_analysis_id: string;
  source_dataset_version_id: string;
  method_id: "regression.linear_model_optimizer";
  method_version: string;
  model_manifest_sha256: string;
  config_sha256: string;
  result_sha256: string;
  result: RegressionResponseOptimizationResult;
  created_at: string;
}

export interface RegressionResponseOptimizationListResponse {
  model_id: string;
  optimizations: RegressionResponseOptimizationResponse[];
  total: number;
}
import type { AnalysisProvenance } from "./analyses";
