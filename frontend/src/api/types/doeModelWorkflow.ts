export interface DoeModelSelectionOptions {
  method: "none" | "backward_elimination";
  alpha_to_remove: number;
  hierarchy_policy: "strong";
  saturated_start_policy: "pool_smallest_adjusted_ss";
  display_step_details: boolean;
}

export interface DoeModelSelectionStep {
  step: number;
  phase: "initial_full_model" | "initial_pooling" | "backward_elimination";
  active_term_ids: string[];
  removed_term_id: string | null;
  removal_df: number | null;
  removal_adjusted_ss: number | null;
  removal_p_value: number | null;
  stop_reason: string | null;
  coefficients: Array<{ column_index: number; coefficient: number }>;
  sse: number;
  residual_df: number;
  residual_standard_error: number | null;
  r_squared: number;
  adjusted_r_squared: number | null;
  press: number | null;
  predicted_r_squared: number | null;
}

export interface DoeModelSelectionResult extends DoeModelSelectionOptions {
  tie_break_policy: string;
  initial_model_saturated: boolean;
  initial_parameter_count: number;
  initial_residual_df: number;
  target_pool_count: number;
  initial_term_ids: string[];
  pooled_term_ids: string[];
  removed_term_ids: string[];
  final_term_ids: string[];
  fixed_term_ids: string[];
  stop_reason: string;
  steps: DoeModelSelectionStep[];
  post_selection_inference: "exploratory" | "not_selected";
}

export interface DoeFinalCoefficient {
  term_id: string;
  label: string;
  kind: string;
  factor_names: string[];
  coefficient: number;
  effect: number | null;
  standard_error: number | null;
  t_statistic: number | null;
  p_value: number | null;
  vif: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  status: "structural" | "retained";
}

export interface DoePredictionFeature {
  term_id: string;
  label: string;
  kind: "intercept" | "main_effect" | "interaction" | "center_curvature" | "block";
  factor_names: string[];
  level_indices: number[];
  block_index: number | null;
}

export interface DoePredictionBasis {
  schema_version: 1;
  coding: "coded" | "treatment";
  features: DoePredictionFeature[];
  coefficients: number[];
  xtx_inverse: number[][];
  residual_mean_square: number | null;
  residual_df: number;
  confidence_level: number;
  block_levels: Array<number | null>;
  center_settings: Array<Record<string, number>>;
}

export interface DoeResidualView {
  n: number;
  histogram: Array<{ lower: number; upper: number; count: number }>;
  qq_points: Array<{ run_order: number; theoretical_quantile: number; residual: number }>;
  reference_line: { slope: number; intercept: number } | null;
  points: Array<{ run_order: number; fitted: number; residual: number }>;
}

export interface DoeFinalModelWorkflow {
  anova_groups?: Array<{ kind: string; label: string; df: number; adjusted_ss: number; mean_square: number | null; f_statistic: number | null; p_value: number | null; terms: Array<{ label: string; df: number; adjusted_ss: number; mean_square: number | null; f_statistic: number | null; p_value: number | null }> }>;
  equation: { scale: "coded" | "treatment"; response_name: string; intercept: number; terms: DoeFinalCoefficient[]; display_equation: string };
  coded_coefficients: DoeFinalCoefficient[];
  prediction_basis: DoePredictionBasis;
  press: number | null;
  predicted_r_squared: number | null;
  residual_plots: {
    raw: DoeResidualView;
    standardized: DoeResidualView;
    points: Array<{ run_order: number; observed: number; fitted: number; residual: number; standardized_residual: number | null; leverage: number; cooks_distance: number | null }>;
    n_total: number; point_limit: number; truncated: boolean;
  };
  factorial_plots: {
    cells: Array<{ settings: Record<string, number>; fitted_mean: number; data_mean: number | null; n: number }>;
    available: boolean; reason: string | null; marginalization: "equal_level_and_block_weights";
  };
  warnings: string[];
}

export interface DoePredictionRowRequest {
  row_id: string;
  factor_settings: Record<string, number | string>;
  block_index?: number | null;
}
export interface DoePredictionPreflightRequest {
  rows: DoePredictionRowRequest[];
  confidence_level: number;
}
export interface DoePredictionPreflightResponse {
  schema_version: 1; design_id: string; analysis_id: string; source_analysis_sha256: string;
  preflight_sha256: string; valid: boolean; row_count: number;
  issues: Array<{ row_id: string; code: string; factor_name: string | null }>;
  warnings: string[];
}
export interface DoePredictionInterval { lower: number; upper: number; level: number }
export interface DoePredictionResponse {
  schema_version: 1; prediction_id: string; design_id: string; analysis_id: string;
  response_revision_id: string; response_revision_sha256: string; source_analysis_sha256: string;
  created_at: string;
  rows: Array<{ row_id: string; factor_settings: Record<string, number | string>; block_index: number | null;
    fitted_mean: number; standard_error_fit: number | null; mean_confidence_interval: DoePredictionInterval | null;
    individual_prediction_interval: DoePredictionInterval | null; interval_unavailability_reason: string | null; domain_status: "in_domain" }>;
  warnings: string[];
}
export interface DoeAnalysisAssetDescriptor {
  asset_id: string; analysis_id: string; kind: "prediction" | "html_report"; schema_version: 1;
  locale: "en" | "ko" | null; source_analysis_sha256: string; sha256: string; media_type: string;
  size_bytes: number; created_at: string;
}
export interface DoeAnalysisAssetList { analysis_id: string; items: DoeAnalysisAssetDescriptor[] }
export interface DoeAnalysisDeletionPreflight {
  analysis_id: string; prediction_count: number; report_count: number; deletion_manifest_sha256: string;
}
