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
  method_id: "regression.linear_model";
  method_version: string;
  schema_hash: string;
  response: RegressionModelCatalogResponseColumn | null;
  predictor_count: number | null;
  created_at: string;
  availability: "available" | "source_stale" | "integrity_error";
  availability_code: string | null;
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

export interface RegressionModelDeletionCounts {
  regression_model_count: 1;
  manifest_artifact_count: 1;
  manifest_file_count: 1;
  manifest_file_bytes: number;
  metadata_record_count: 2;
  dependent_prediction_count: number;
}

export interface RegressionModelDeletionPreflightResponse {
  preflight_schema_version: 1;
  model_id: string;
  source_analysis_id: string;
  method_id: "regression.linear_model";
  method_version: string;
  deletion_ready: boolean;
  blockers: string[];
  counts: RegressionModelDeletionCounts;
  deletion_manifest_sha256: string;
}

export interface RegressionModelDeleteRequest {
  confirmation_model_id: string;
  expected_deletion_manifest_sha256: string;
}

export interface RegressionModelDeleteResponse {
  deletion_schema_version: 1;
  model_id: string;
  source_analysis_id: string;
  deletion_manifest_sha256: string;
  deleted_at: string;
  deleted_counts: RegressionModelDeletionCounts;
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
import type { AnalysisProvenance } from "./analyses";
