import type { DatasetColumnResponse, DatasetColumnRole, DatasetMeasurementLevel } from "./datasets";

export interface PearsonCorrelationColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface PearsonCorrelationSampleSummary {
  n: number;
  mean: number;
  std: number;
  min: number;
  max: number;
}

export interface PearsonCorrelationAssociation {
  correlation: number;
  r_squared: number;
  covariance: number;
  correlation_definition: string;
}

export interface PearsonCorrelationTestResult {
  statistic: number;
  statistic_name: string;
  p_value: number;
  reject_null: boolean;
  null_hypothesis: string;
  alternative: string;
}

export interface PearsonCorrelationConfidenceInterval {
  method: string;
  level: number;
  lower: number | null;
  upper: number | null;
}

export interface PearsonScatterPoint {
  x: number;
  y: number;
}

export interface PearsonScatterplot {
  x_column_id: string;
  y_column_id: string;
  point_count: number;
  points_truncated: boolean;
  point_limit: number;
  points: PearsonScatterPoint[];
}

export interface PearsonCorrelationResult {
  schema_version: number;
  summary_type: "pearson_correlation";
  method: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  x: PearsonCorrelationColumnRef;
  y: PearsonCorrelationColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_x: number;
  n_excluded_missing_y: number;
  n_excluded_non_numeric_x: number;
  n_excluded_non_numeric_y: number;
  x_summary: PearsonCorrelationSampleSummary;
  y_summary: PearsonCorrelationSampleSummary;
  scatterplot: PearsonScatterplot;
  association: PearsonCorrelationAssociation;
  test: PearsonCorrelationTestResult;
  confidence_interval: PearsonCorrelationConfidenceInterval;
}

export interface XyCorrelationColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface XyCorrelationAssociation {
  correlation: number;
  r_squared: number;
  covariance: number;
  correlation_definition: string;
}

export interface XyCorrelationTestResult {
  statistic: number;
  statistic_name: string;
  p_value: number;
  reject_null: boolean;
  null_hypothesis: string;
  alternative: string;
}

export interface XyCorrelationConfidenceInterval {
  method: string;
  level: number;
  lower: number | null;
  upper: number | null;
}

export interface XyCorrelationPairResult {
  x: XyCorrelationColumnRef;
  y: XyCorrelationColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_x: number;
  n_excluded_missing_y: number;
  n_excluded_non_numeric_x: number;
  n_excluded_non_numeric_y: number;
  status: "ok" | "failed";
  error_code: string | null;
  warnings: string[];
  association: XyCorrelationAssociation | null;
  test: XyCorrelationTestResult | null;
  confidence_interval: XyCorrelationConfidenceInterval | null;
}

export interface XyCorrelationResult {
  schema_version: number;
  summary_type: "xy_correlation_matrix";
  method: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  x_columns: XyCorrelationColumnRef[];
  y_columns: XyCorrelationColumnRef[];
  x_column_count: number;
  y_column_count: number;
  pair_count: number;
  pairs: XyCorrelationPairResult[];
}

export interface LinearModelColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface LinearModelSample {
  n_total: number;
  n_used: number;
  n_excluded_missing: number;
  n_excluded_non_numeric: number;
  df_model: number;
  df_residual: number;
}

export interface LinearModelFit {
  r_squared: number;
  adjusted_r_squared: number;
  residual_standard_error: number;
  sigma_squared: number;
  sse: number;
  ssr: number;
  tss: number;
  f_statistic: number;
  f_p_value: number;
}

export interface LinearModelCoefficient {
  term: string;
  term_kind: string;
  column_id: string | null;
  source_column_ids: string[];
  response_column_id: string;
  level: string | null;
  reference_level: string | null;
  coding: string | null;
  estimate: number;
  standard_error: number;
  statistic: number;
  statistic_name: string;
  p_value: number;
  confidence_interval: {
    method: string;
    level: number;
    lower: number;
    upper: number;
  };
  vif: number | null;
}

export interface LinearModelDiagnostics {
  rank: number;
  parameter_count: number;
  condition_number: number;
  max_vif: number | null;
  residual_summary: {
    mean: number;
    min: number;
    q1: number;
    median: number;
    q3: number;
    max: number;
    max_abs_standardized: number | null;
    large_standardized_threshold: number;
    large_standardized_count: number;
    large_standardized_row_indices: number[];
  };
  leverage: {
    mean: number;
    max: number;
    threshold: number;
    high_count: number;
    high_row_indices: number[];
  };
  influence: {
    cooks_distance_max: number | null;
    cooks_distance_threshold: number;
    high_cooks_distance_count: number;
    high_cooks_distance_row_indices: number[];
  };
  diagnostic_points: {
    point_limit: number;
    points_included: number;
    truncated: boolean;
    points: Array<{
      row_index: number;
      fitted: number;
      residual: number;
      standardized_residual: number | null;
      leverage: number;
      cooks_distance: number | null;
    }>;
  };
}

export interface LinearModelManifestPointer {
  model_id: string;
  manifest_schema_version: number;
  manifest_sha256: string;
}

export interface LinearModelResult {
  schema_version: number;
  summary_type: "linear_model";
  method: string;
  missing_policy: string;
  alpha: number;
  confidence_level: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: LinearModelColumnRef;
  predictors: LinearModelColumnRef[];
  model_specification: {
    intercept: boolean;
    terms: Array<{
      term: string;
      kind: string;
      column_id: string | null;
      source_column_ids?: string[];
      coding?: string;
      reference_level?: string;
      levels?: string[];
    }>;
  };
  sample: LinearModelSample;
  fit: LinearModelFit;
  coefficients: LinearModelCoefficient[];
  diagnostics: LinearModelDiagnostics;
  model_manifest?: LinearModelManifestPointer;
}
