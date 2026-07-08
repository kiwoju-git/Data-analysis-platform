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

export interface RegressionPredictionResponse {
  prediction_id: string;
  model_id: string;
  analysis_id: string;
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
  provenance: Record<string, unknown>;
  columns: RegressionPredictionColumnMapping[];
  rows: RegressionPredictionRow[];
}
