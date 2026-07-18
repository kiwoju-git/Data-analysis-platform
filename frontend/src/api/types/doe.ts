export interface DoeFactorRequest {
  name: string;
  low: number;
  high: number;
  unit?: string | null;
}

export interface FactorialDesignCreateRequest {
  name: string;
  factors: DoeFactorRequest[];
  replicates: number;
  center_points: number;
  randomize: boolean;
  randomization_seed: number;
  block_count: number;
}

export interface DoeFactorResponse {
  name: string;
  low: number;
  high: number;
  unit: string | null;
}

export interface FactorialDesignOptionsResponse {
  replicates: number;
  center_points: number;
  randomize: boolean;
  randomization_seed: number;
  block_count: number;
}

export interface FactorialDesignRunResponse {
  standard_order: number;
  run_order: number;
  replicate_index: number;
  center_point: boolean;
  block_index: number | null;
  factor_levels: Record<string, number>;
  coded_levels: Record<string, number>;
}

export interface FactorialDesignResponse {
  design_id: string;
  design_version_id: string;
  version_number: number;
  method_id: string;
  method_version: string;
  family: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
  app_version: string;
  factors: DoeFactorResponse[];
  options: FactorialDesignOptionsResponse;
  run_count: number;
  design_sha256: string;
  runs: FactorialDesignRunResponse[];
}

export interface DoeResponseValueRequest {
  run_order: number;
  value: number;
}

export interface DoeDesignResponsesUpsertRequest {
  response_name: string;
  unit?: string | null;
  values: DoeResponseValueRequest[];
}

export interface DoeDesignResponseValue {
  run_order: number;
  value: number;
}

export interface DoeDesignResponseSeries {
  response_name: string;
  unit: string | null;
  response_revision_id: string;
  response_revision_number: number;
  response_revision_schema_version: 1;
  response_revision_sha256: string;
  created_at: string;
  closed_at: string | null;
  response_count: number;
  values: DoeDesignResponseValue[];
}

export interface DoeDesignResponsesResponse {
  design_id: string;
  design_version_id: string;
  version_number: number;
  status: string;
  responses: DoeDesignResponseSeries[];
}

export interface DoeResponseRevisionCreateRequest extends DoeDesignResponsesUpsertRequest {
  supersedes_response_revision_id: string | null;
}

export interface DoeResponseRevisionResponse {
  response_revision_id: string;
  design_id: string;
  design_version_id: string;
  response_revision_schema_version: 1;
  response_revision_sha256: string;
  response_name: string;
  unit: string | null;
  revision_number: number;
  state: "completed" | "abandoned";
  is_current: boolean;
  response_count: number;
  supersedes_response_revision_id: string | null;
  created_at: string;
  closed_at: string | null;
  values: DoeDesignResponseValue[];
}

export interface DoeResponseRevisionHistoryResponse {
  design_id: string;
  design_version_id: string;
  response_name: string;
  total: number;
  offset: number;
  limit: number;
  items: DoeResponseRevisionResponse[];
}

export interface DoeFactorialAnalysisCreateRequest {
  response_name: string;
  response_revision_id?: string | null;
  max_interaction_order: number;
  confidence_level: number;
  point_limit: number;
}

export interface DoeFactorialConfidenceInterval {
  level: number;
  lower: number;
  upper: number;
}

export interface DoeFactorialTerm {
  term_id: string;
  label: string;
  kind: string;
  factor_names: string[];
  coefficient: number;
  effect: number | null;
  standard_error: number | null;
  statistic: number | null;
  p_value: number | null;
  confidence_interval: DoeFactorialConfidenceInterval | null;
  effect_confidence_interval: DoeFactorialConfidenceInterval | null;
  partial_sum_squares: number | null;
  f_statistic: number | null;
  f_p_value: number | null;
}

export interface DoeFactorialAnovaRow {
  df: number;
  sum_squares: number;
  mean_square: number | null;
  f_statistic: number | null;
  p_value: number | null;
}

export interface DoeFactorialDiagnosticPoint {
  run_order: number;
  standard_order: number;
  observed: number;
  fitted: number;
  residual: number;
  standardized_residual: number | null;
  leverage: number;
  cooks_distance: number | null;
}

export interface DoeFactorialAnalysisResult {
  schema_version: 1;
  summary_type: "factorial_analysis";
  method: string;
  response: { name: string; unit: string | null };
  factor_names: string[];
  coding: {
    low: number;
    high: number;
    center: number;
    effect_definition: string;
  };
  model_policy: {
    hierarchy_enforced: boolean;
    max_interaction_order: number;
    automatic_term_selection: boolean;
    center_curvature_included: boolean;
    block_fixed_effects_included: boolean;
    sum_of_squares: string;
  };
  sample: {
    n_observations: number;
    factorial_point_count: number;
    center_point_count: number;
    block_count: number;
    parameter_count: number;
    rank: number;
    df_model: number;
    df_residual: number;
  };
  fit: {
    response_mean: number;
    sse: number;
    model_ss: number;
    total_ss: number;
    residual_mean_square: number | null;
    residual_standard_error: number | null;
    r_squared: number;
    adjusted_r_squared: number | null;
    f_statistic: number | null;
    f_p_value: number | null;
  };
  terms: DoeFactorialTerm[];
  ranked_effects: Array<{
    term_id: string;
    label: string;
    effect: number;
    absolute_effect: number;
  }>;
  anova: {
    sum_of_squares_policy: string;
    model: DoeFactorialAnovaRow;
    residual: DoeFactorialAnovaRow;
    total: DoeFactorialAnovaRow;
    lack_of_fit: {
      available: boolean;
      unique_design_point_count: number;
      pure_error: DoeFactorialAnovaRow;
      lack_of_fit: DoeFactorialAnovaRow;
      residual_df: number;
    };
  };
  diagnostics: {
    residual_mean: number;
    residual_min: number;
    residual_max: number;
    max_abs_standardized_residual: number | null;
    high_standardized_residual_count: number;
    max_leverage: number;
    high_leverage_threshold: number;
    high_leverage_count: number;
    max_cooks_distance: number | null;
    cooks_distance_threshold: number;
    high_cooks_distance_count: number;
    durbin_watson: number | null;
    shapiro_wilk: { statistic: number | null; p_value: number | null };
    point_limit: number;
    points_truncated: boolean;
    points: DoeFactorialDiagnosticPoint[];
    qq_points: Array<{ theoretical: number; ordered_residual: number }>;
  };
  plots: {
    main_effects: Array<{ factor: string; low_mean: number; high_mean: number }>;
    interactions: Array<{
      first_factor: string;
      second_factor: string;
      cells: Array<{ first_level: number; second_level: number; mean: number; n: number }>;
    }>;
  };
  warnings: string[];
}

export interface DoeFactorialAnalysisResponse {
  analysis_id: string;
  design_id: string;
  design_version_id: string;
  design_version_number: number;
  method_id: string;
  method_version: string;
  analysis_schema_version: number;
  design_sha256: string;
  response_revision_id: string;
  response_revision_number: number;
  response_revision_sha256: string;
  response_sha256: string;
  response_name: string;
  created_at: string;
  app_version: string;
  python_version: string;
  platform: string;
  build_commit: string | null;
  package_versions: Record<string, string>;
  result: DoeFactorialAnalysisResult;
}

export interface ResponseSurfaceDesignCreateRequest {
  name: string;
  factors: DoeFactorRequest[];
  alpha_mode: "rotatable" | "face_centered";
  factorial_replicates: number;
  axial_replicates: number;
  center_points: number;
  randomize: boolean;
  randomization_seed: number;
}

export interface ResponseSurfaceDesignOptionsResponse {
  alpha_mode: "rotatable" | "face_centered";
  alpha: number;
  factorial_replicates: number;
  axial_replicates: number;
  center_points: number;
  randomize: boolean;
  randomization_seed: number;
}

export interface ResponseSurfaceDesignRunResponse {
  standard_order: number;
  run_order: number;
  replicate_index: number;
  point_type: "factorial" | "axial" | "center";
  center_point: boolean;
  factor_levels: Record<string, number>;
  coded_levels: Record<string, number>;
}

export interface ResponseSurfaceDesignResponse {
  design_id: string;
  design_version_id: string;
  version_number: number;
  method_id: "doe.response_surface";
  method_version: string;
  design_schema_version: 1 | 2;
  family: "central_composite" | "central_composite_inscribed";
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
  app_version: string;
  factors: DoeFactorResponse[];
  options: ResponseSurfaceDesignOptionsResponse;
  run_count: number;
  design_sha256: string;
  runs: ResponseSurfaceDesignRunResponse[];
}

export interface DoeResponseSurfaceAnalysisCreateRequest {
  response_name: string;
  response_revision_id?: string | null;
  confidence_level: number;
  point_limit: number;
  contour_grid_size: number;
}

export interface DoeResponseSurfaceTerm {
  term_id: string;
  label: string;
  kind: "intercept" | "main_effect" | "interaction" | "quadratic";
  factor_names: string[];
  coefficient: number;
  standard_error: number | null;
  statistic: number | null;
  p_value: number | null;
  confidence_interval: DoeFactorialConfidenceInterval | null;
  partial_sum_squares: number | null;
  f_statistic: number | null;
  f_p_value: number | null;
}

export interface DoeResponseSurfaceDiagnosticPoint extends DoeFactorialDiagnosticPoint {
  point_type: "factorial" | "axial" | "center";
}

export interface DoeResponseSurfaceAnalysisResult {
  schema_version: 1;
  summary_type: "response_surface_analysis";
  method: "full_quadratic_ordinary_least_squares";
  response: { name: string; unit: string | null };
  factor_names: string[];
  coding: {
    center: number;
    factorial_low: number;
    factorial_high: number;
    axial_distance: number;
    actual_bounds_are_axial_bounds: boolean;
  };
  model_policy: {
    full_quadratic: boolean;
    automatic_term_selection: boolean;
    hierarchy_enforced: boolean;
    sum_of_squares: string;
    contour_other_factors_held_at_center: boolean;
  };
  sample: {
    n_observations: number;
    factorial_point_count: number;
    axial_point_count: number;
    center_point_count: number;
    unique_design_point_count: number;
    parameter_count: number;
    rank: number;
    df_model: number;
    df_residual: number;
  };
  fit: DoeFactorialAnalysisResult["fit"];
  terms: DoeResponseSurfaceTerm[];
  anova: DoeFactorialAnalysisResult["anova"];
  stationary_point: {
    available: boolean;
    classification: "minimum" | "maximum" | "saddle" | "indeterminate";
    coded_coordinates: Record<string, number>;
    actual_coordinates: Record<string, number>;
    predicted_response: number | null;
    within_axial_bounds: boolean;
    within_factorial_cube: boolean;
    hessian_eigenvalues: number[];
  };
  contour: {
    x_factor: string;
    y_factor: string;
    held_coded_levels: Record<string, number>;
    grid_size: number;
    coded_range: [number, number];
    points: Array<{
      x_coded: number;
      y_coded: number;
      x_actual: number;
      y_actual: number;
      predicted: number;
    }>;
  };
  diagnostics: Omit<DoeFactorialAnalysisResult["diagnostics"], "points"> & {
    points: DoeResponseSurfaceDiagnosticPoint[];
  };
  warnings: string[];
}

export interface DoeResponseSurfaceAnalysisResponse {
  analysis_id: string;
  design_id: string;
  design_version_id: string;
  design_version_number: number;
  method_id: "doe.response_surface";
  method_version: string;
  analysis_schema_version: number;
  design_sha256: string;
  response_revision_id: string;
  response_revision_number: number;
  response_revision_sha256: string;
  response_sha256: string;
  response_name: string;
  created_at: string;
  app_version: string;
  python_version: string;
  platform: string;
  build_commit: string | null;
  package_versions: Record<string, string>;
  result: DoeResponseSurfaceAnalysisResult;
}

export interface DoeResponseSurfaceAnalysisCatalogItem {
  analysis_id: string;
  design_id: string;
  design_name: string;
  response_name: string;
  response_revision_id: string | null;
  response_revision_number: number | null;
  method_id: "doe.response_surface";
  method_version: string;
  created_at: string;
  eligibility_status:
    | "eligible"
    | "acknowledgment_required"
    | "ineligible"
    | "integrity_error"
    | "incompatible_method_version";
  blocking_issue_count: number;
  advisory_issue_count: number;
  informational_issue_count: number;
  availability_code: string | null;
}

export interface DoeResponseSurfaceAnalysisCatalogResponse {
  analyses: DoeResponseSurfaceAnalysisCatalogItem[];
  total: number;
  returned: number;
  limit: number;
  offset: number;
  has_previous: boolean;
  has_next: boolean;
}

export type ResponseOptimizerGoal = "maximize" | "minimize" | "target" | "range";

export interface ResponseOptimizerObjectiveRequest {
  source_analysis_id: string;
  goal: ResponseOptimizerGoal;
  lower: number | null;
  target: number | null;
  upper: number | null;
  lower_weight: number;
  upper_weight: number;
  importance: number;
}

export interface ResponseOptimizerFactorBoundRequest {
  factor_name: string;
  lower: number;
  upper: number;
}

export interface ResponseOptimizerLinearConstraintRequest {
  name: string;
  coefficients: Record<string, number>;
  relation: "less_than_or_equal" | "greater_than_or_equal";
  bound: number;
}

export interface ResponseOptimizerSearchOptionsRequest {
  random_seed: number;
  random_candidate_count: number;
  multi_start_count: number;
  max_iterations: number;
  max_evaluations: number;
  time_budget_ms: number;
}

export interface ResponseOptimizerCreateRequest {
  objectives: ResponseOptimizerObjectiveRequest[];
  factor_bounds: ResponseOptimizerFactorBoundRequest[];
  linear_constraints: ResponseOptimizerLinearConstraintRequest[];
  search: ResponseOptimizerSearchOptionsRequest;
  acknowledged_source_warning_codes: string[];
}

export type ResponseOptimizerEligibilitySeverity =
  | "blocking"
  | "acknowledgment_required"
  | "informational";

export interface ResponseOptimizerEligibilityIssue {
  source_analysis_id: string | null;
  code: string;
  severity: ResponseOptimizerEligibilitySeverity;
  source_warning_code: string | null;
}

export interface ResponseOptimizerSourceEligibility {
  eligible: boolean;
  acknowledgment_required: boolean;
  issues: ResponseOptimizerEligibilityIssue[];
  acknowledged_source_warning_codes: string[];
}

export interface ResponseOptimizerResult {
  schema_version: 2;
  summary_type: "response_optimizer";
  method: "derringer_suich_bounded_multistart_slsqp";
  model_policy: {
    individual_desirability: "derringer_suich";
    composite_desirability: "importance_weighted_geometric_mean";
    bounded_to_declared_design_region: boolean;
    linear_constraints_supported: boolean;
    global_optimum_guaranteed: boolean;
    point_predictions_only: boolean;
  };
  factor_region: {
    design_bounds: Array<{
      factor_name: string;
      lower: number;
      upper: number;
      unit: string | null;
    }>;
    search_bounds: ResponseOptimizerFactorBoundRequest[];
    linear_constraints: ResponseOptimizerLinearConstraintRequest[];
  };
  objectives: Array<{
    source_analysis_id: string;
    response_name: string;
    response_unit: string | null;
    goal: ResponseOptimizerGoal;
    lower: number | null;
    target: number | null;
    upper: number | null;
    lower_weight: number;
    upper_weight: number;
    importance: number;
  }>;
  recommendation: {
    actual_coordinates: Record<string, number>;
    coded_coordinates: Record<string, number>;
    composite_desirability: number;
    objectives: Array<{
      source_analysis_id: string;
      response_name: string;
      goal: ResponseOptimizerGoal;
      predicted_response: number;
      individual_desirability: number;
      importance: number;
    }>;
    constraints: Array<{
      name: string;
      relation: "less_than_or_equal" | "greater_than_or_equal";
      lhs: number;
      bound: number;
      slack: number;
      satisfied: boolean;
    }>;
    all_constraints_satisfied: boolean;
  };
  search: {
    algorithm: "seeded_candidates_plus_slsqp_multistart";
    random_seed: number;
    random_candidate_count: number;
    multi_start_count: number;
    max_iterations: number;
    max_evaluations: number;
    time_budget_ms: number;
    evaluation_count: number;
    local_starts_attempted: number;
    local_success_count: number;
    local_iterations: number;
    elapsed_ms: number;
    termination_reason: "search_completed" | "evaluation_budget" | "time_budget";
    global_optimum_guaranteed: boolean;
  };
  source_model_eligibility: ResponseOptimizerSourceEligibility;
  acknowledged_source_warning_codes: string[];
  warnings: string[];
}

export interface ResponseOptimizerResponse {
  optimization_id: string;
  design_id: string;
  design_version_id: string;
  design_version_number: number;
  method_id: "regression.response_optimizer";
  method_version: string;
  config_schema_version: 2;
  result_schema_version: 2;
  config_sha256: string;
  design_sha256: string;
  source_analysis_ids: string[];
  source_bundle_sha256: string;
  acknowledged_source_warning_codes: string[];
  created_at: string;
  app_version: string;
  python_version: string;
  platform: string;
  build_commit: string | null;
  package_versions: Record<string, string>;
  result: ResponseOptimizerResult;
}
