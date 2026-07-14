import type { DatasetColumnResponse, DatasetColumnRole, DatasetMeasurementLevel } from "./datasets";

export type AttributeControlChartType = "p" | "np" | "c" | "u";

export interface AttributeControlChartColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface AttributeControlChartPoint {
  position: number;
  canonical_position: number;
  count: number;
  denominator: number | null;
  value: number;
  lcl: number;
  ucl: number;
  lcl_truncated: boolean;
  ucl_truncated: boolean;
  signal_codes: string[];
}

export interface AttributeControlChartSignal {
  signal_id: string;
  code: "attribute_control_chart_point_beyond_control_limits";
  severity: "warning";
  position: number;
  canonical_position: number;
  value: number;
  limit: "lower" | "upper";
  definition: string;
}

export interface AttributeControlChartResult {
  schema_version: number;
  summary_type: "attribute_control_chart";
  method: "p_chart" | "np_chart" | "c_chart" | "u_chart";
  chart_type: AttributeControlChartType;
  count_definition: "defectives" | "defects";
  distribution_assumption: "binomial" | "poisson";
  control_limit_method: "phase_1_estimated_three_sigma";
  baseline: "all_filtered_valid_points";
  order_source: "canonical_row_order";
  missing_policy: "complete_case";
  constant_opportunity_confirmed: boolean;
  control_rules: Array<{
    code: string;
    definition: string;
    enabled: boolean;
  }>;
  warnings: string[];
  count: AttributeControlChartColumnRef;
  denominator: AttributeControlChartColumnRef | null;
  denominator_role: "sample_size" | "inspection_opportunity" | null;
  n_total: number;
  n_used: number;
  n_excluded_missing_count: number;
  n_excluded_non_numeric_count: number;
  n_excluded_missing_denominator: number;
  n_excluded_non_numeric_denominator: number;
  total_count: number;
  total_denominator: number | null;
  center_line: number;
  limits_vary: boolean;
  lcl_truncated_count: number;
  ucl_truncated_count: number;
  dispersion: {
    method: string;
    degrees_of_freedom: number;
    ratio: number;
    warning_threshold: number;
    used_to_adjust_limits: false;
  };
  chart: {
    x_axis: "canonical_row_position";
    y_axis:
      | "proportion_defective"
      | "defective_count"
      | "defect_count"
      | "defects_per_opportunity";
    center_line: number;
    limits_vary: boolean;
    point_count: number;
    points_truncated: boolean;
    point_limit: number;
    points: AttributeControlChartPoint[];
  };
  signals: AttributeControlChartSignal[];
}

export interface IndividualsChartColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface IndividualsChartSigmaEstimator {
  method: string;
  moving_range_length: number;
  d2: number;
  mrbar: number;
  sigma: number;
}

export interface IndividualsChartSignal {
  signal_id: string;
  code: string;
  severity: "info" | "warning" | "error";
  chart: "individuals" | "moving_range";
  position: number;
  start_position?: number;
  end_position?: number;
  positions?: number[];
  previous_position?: number;
  canonical_position: number;
  start_canonical_position?: number;
  canonical_positions?: number[];
  previous_canonical_position?: number;
  value: number;
  limit?: "lower" | "upper";
  direction?:
    | "above"
    | "below"
    | "increasing"
    | "decreasing"
    | "alternating"
    | "within"
    | "outside";
  length?: number;
  count?: number;
  sigma_multiple?: number;
  definition: string;
}

export interface IndividualsChartPoint {
  position: number;
  canonical_position: number;
  value: number;
  signal_codes: string[];
}

export interface MovingRangeChartPoint extends IndividualsChartPoint {
  previous_position: number;
  previous_canonical_position: number;
}

export interface IndividualsChartSeries {
  x_axis: "canonical_row_position" | "order_rank";
  center_line: number;
  lcl: number;
  ucl: number;
  point_count: number;
  points_truncated: boolean;
  point_limit: number;
  points: IndividualsChartPoint[];
}

export interface MovingRangeChartSeries {
  x_axis: "canonical_row_position" | "order_rank";
  center_line: number;
  lcl: number;
  ucl: number;
  d3: number;
  d4: number;
  point_count: number;
  points_truncated: boolean;
  point_limit: number;
  points: MovingRangeChartPoint[];
}

export interface IndividualsChartResult {
  schema_version: number;
  summary_type: "individuals_chart";
  method: string;
  order_source: string;
  order_tie_breaker: string | null;
  order_timezone: string | null;
  missing_policy: string;
  sigma_estimator: IndividualsChartSigmaEstimator;
  control_rules: Array<{
    code: string;
    chart: "individuals" | "moving_range";
    definition: string;
    minimum_length?: number;
    window_size?: number;
    minimum_count?: number;
    sigma_multiple?: number;
    enabled: boolean;
  }>;
  warnings: string[];
  value: IndividualsChartColumnRef;
  order: IndividualsChartColumnRef | null;
  n_total: number;
  n_used: number;
  n_excluded_missing_value: number;
  n_excluded_non_numeric_value: number;
  n_excluded_missing_order: number;
  n_excluded_non_numeric_order: number;
  order_duplicate_count: number;
  individuals_chart: IndividualsChartSeries;
  moving_range_chart: MovingRangeChartSeries;
  signals: IndividualsChartSignal[];
}

export interface SubgroupChartColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface SubgroupChartConstants {
  source: string;
  subgroup_size: number;
  a2?: number;
  d3?: number;
  d4?: number;
  a3?: number;
  b3?: number;
  b4?: number;
  stddev_definition?: string;
}

export interface SubgroupChartSignal {
  signal_id: string;
  code: string;
  severity: "info" | "warning" | "error";
  chart: "xbar" | "r" | "s";
  position: number;
  subgroup_label: string;
  first_canonical_position: number;
  last_canonical_position: number;
  value: number;
  limit: "lower" | "upper";
  definition: string;
}

export interface SubgroupChartPoint {
  position: number;
  subgroup_label: string;
  first_canonical_position: number;
  last_canonical_position: number;
  n: number;
  value: number;
  mean: number;
  range: number;
  stddev?: number;
  signal_codes: string[];
}

export interface SubgroupChartSeries {
  x_axis: "subgroup_position";
  center_line: number;
  lcl: number;
  ucl: number;
  point_count: number;
  points_truncated: boolean;
  point_limit: number;
  points: SubgroupChartPoint[];
}

export interface SubgroupChartResult {
  schema_version: number;
  summary_type: "subgroup_chart";
  method: string;
  chart_type: "xbar_r" | "xbar_s";
  order_source: string;
  missing_policy: string;
  subgroup_size: number;
  subgroup_count: number;
  constants: SubgroupChartConstants;
  control_rules: Array<{
    code: string;
    chart: "xbar" | "r" | "s";
    definition: string;
    enabled: boolean;
  }>;
  warnings: string[];
  value: SubgroupChartColumnRef;
  subgroup: SubgroupChartColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_value: number;
  n_excluded_non_numeric_value: number;
  n_excluded_missing_subgroup: number;
  subgroup_size_distribution: Array<{ size: number; count: number }>;
  xbar_chart: SubgroupChartSeries;
  r_chart?: SubgroupChartSeries;
  s_chart?: SubgroupChartSeries;
  signals: SubgroupChartSignal[];
}

export interface RunChartColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface RunChartRuns {
  run_count: number;
  n_above: number;
  n_below: number;
  n_ties: number;
  longest_run_length: number;
  run_count_definition: string;
}

export interface RunChartRunsTest {
  method: string;
  alpha: number;
  available: boolean;
  observed_run_count: number;
  n_above: number;
  n_below: number;
  n_ties: number;
  n_non_tie: number;
  expected_run_count: number | null;
  variance: number | null;
  p_value_low: number | null;
  p_value_high: number | null;
  interpretation: "not_extreme" | "clustering" | "mixture" | "not_available";
  skipped_reason: string | null;
  max_exact_n: number;
}

export interface RunChartSignal {
  signal_id: string;
  code: string;
  severity: "info" | "warning" | "error";
  direction: "increasing" | "decreasing" | "alternating" | "low_runs" | "high_runs";
  length: number;
  start_position: number;
  end_position: number;
  definition: string;
}

export interface RunChartPoint {
  position: number;
  canonical_position?: number;
  value: number;
  relative_to_center: "above" | "below" | "tie";
  signal_codes: string[];
}

export interface RunChartChartPayload {
  x_axis: "canonical_row_position" | "order_rank";
  point_count: number;
  points_truncated: boolean;
  point_limit: number;
  points: RunChartPoint[];
}

export interface RunChartResult {
  schema_version: number;
  summary_type: "run_chart";
  method: string;
  center_method: string;
  order_source: string;
  order_tie_breaker: string | null;
  order_timezone: string | null;
  missing_policy: string;
  tie_policy: string;
  trend_rule: {
    code: string;
    definition: string;
    minimum_length: number;
  };
  oscillation_rule: {
    code: string;
    definition: string;
    minimum_length: number;
  };
  runs_test: RunChartRunsTest;
  warnings: string[];
  value: RunChartColumnRef;
  order: RunChartColumnRef | null;
  n_total: number;
  n_used: number;
  n_excluded_missing_value: number;
  n_excluded_non_numeric_value: number;
  n_excluded_missing_order: number;
  n_excluded_non_numeric_order: number;
  order_duplicate_count: number;
  center_line: number;
  runs: RunChartRuns;
  signals: RunChartSignal[];
  chart: RunChartChartPayload;
}

export interface CapabilityColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface CapabilityIndexSet {
  two_sided: number | null;
  lower: number | null;
  upper: number | null;
  min_side: number | null;
}

export interface CapabilityHistogramBin {
  lower: number;
  upper: number;
  midpoint: number;
  count: number;
  proportion: number;
  density: number;
  normal_density: number;
}

export interface CapabilityResult {
  schema_version: number;
  summary_type: "capability_analysis";
  method: string;
  distribution: "normal";
  missing_policy: string;
  sigma_estimators: {
    overall: string;
    within: string;
    moving_range_length: number;
    d2: number;
    mrbar: number;
  };
  warnings: string[];
  value: CapabilityColumnRef;
  spec_limits: {
    lsl: number | null;
    usl: number | null;
    target: number | null;
  };
  n_total: number;
  n_used: number;
  n_excluded_missing_value: number;
  n_excluded_non_numeric_value: number;
  sample: {
    mean: number;
    std_overall: number;
    std_within: number;
    min: number;
    max: number;
  };
  capability: {
    within: CapabilityIndexSet;
    overall: CapabilityIndexSet;
  };
  observed_nonconformance: {
    below_lsl_count: number;
    above_usl_count: number;
    total_count: number;
    below_lsl_proportion: number;
    above_usl_proportion: number;
    total_proportion: number;
    total_ppm: number;
  };
  expected_nonconformance_normal: {
    below_lsl_probability: number;
    above_usl_probability: number;
    total_probability: number;
    total_ppm: number;
  };
  histogram: {
    bin_count: number;
    bins: CapabilityHistogramBin[];
  };
}

export interface GageRrPreflightRequest {
  dataset_version_id: string;
  measurement_column_id: string;
  part_column_id: string;
  operator_column_id: string;
  replicate_column_id: string;
  missing_policy: "complete_case";
}

export interface GageRrPreflightColumn {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: string;
  measurement_level: string;
  role: string;
  unit: string | null;
}

export interface GageRrPreflightSample {
  n_total: number;
  n_used: number;
  n_excluded: number;
  n_excluded_missing_measurement: number;
  n_excluded_non_numeric_measurement: number;
  n_excluded_missing_part: number;
  n_excluded_missing_operator: number;
  n_excluded_missing_replicate: number;
  n_excluded_missing_identifier: number;
}

export interface GageRrCellReplicateCount {
  replicate_count: number;
  cell_count: number;
}

export interface GageRrPreflightDesign {
  design_type: "crossed";
  balanced: boolean;
  ready_for_anova: boolean;
  part_count: number;
  operator_count: number;
  replicate_level_count: number;
  expected_cell_count: number;
  observed_cell_count: number;
  missing_cell_count: number;
  min_replicates_per_cell: number;
  max_replicates_per_cell: number;
  expected_replicates_per_cell: number | null;
  replicate_set_consistent: boolean;
  duplicate_replicates_per_cell: number;
  cell_replicate_count_distribution: GageRrCellReplicateCount[];
}

export interface GageRrPreflightIssue {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  count: number | null;
}

export interface GageRrPreflightResponse {
  schema_version: number;
  method_id: "quality.gage_rr";
  preflight_type: "balanced_crossed_anova";
  dataset_version_id: string;
  schema_hash: string;
  row_count_total: number;
  summary_type: "gage_rr_preflight";
  method: "balanced_crossed_anova_preflight";
  missing_policy: "complete_case";
  columns: {
    measurement: GageRrPreflightColumn;
    part: GageRrPreflightColumn;
    operator: GageRrPreflightColumn;
    replicate: GageRrPreflightColumn;
  };
  sample: GageRrPreflightSample;
  design: GageRrPreflightDesign;
  issues: GageRrPreflightIssue[];
  next_step: "ready_for_balanced_crossed_anova" | "fix_design_before_gage_rr";
}

export interface GageRrSample {
  n_total: number;
  n_used: number;
  n_excluded: number;
  n_excluded_missing_measurement: number;
  n_excluded_non_numeric_measurement: number;
  n_excluded_missing_part: number;
  n_excluded_missing_operator: number;
  n_excluded_missing_replicate: number;
  n_excluded_missing_identifier: number;
}

export interface GageRrDesign {
  design_type: "crossed";
  balanced: boolean;
  ready_for_anova: boolean;
  part_count: number;
  operator_count: number;
  replicate_count: number;
  expected_cell_count: number;
  observed_cell_count: number;
  missing_cell_count: number;
  min_replicates_per_cell: number;
  max_replicates_per_cell: number;
  replicate_set_consistent: boolean;
  duplicate_replicates_per_cell: number;
}

export interface GageRrAnovaRow {
  source: string;
  degrees_of_freedom: number;
  sum_of_squares: number;
  mean_square: number | null;
  f_statistic: number | null;
  p_value: number | null;
  denominator: string | null;
}

export interface GageRrVarianceComponent {
  component: string;
  raw_variance: number;
  final_variance: number;
  standard_deviation: number;
  study_variation: number;
  clamped_to_zero: boolean;
  percent_contribution: number | null;
  percent_study_variation: number | null;
}

export interface GageRrResult {
  schema_version: number;
  summary_type: "gage_rr";
  method: "balanced_crossed_anova";
  missing_policy: "complete_case";
  columns: GageRrPreflightResponse["columns"];
  sample: GageRrSample;
  design: GageRrDesign;
  anova_table: GageRrAnovaRow[];
  variance_components: {
    repeatability: GageRrVarianceComponent;
    operator: GageRrVarianceComponent;
    part_operator: GageRrVarianceComponent;
    reproducibility: GageRrVarianceComponent;
    total_gage_rr: GageRrVarianceComponent;
    part_to_part: GageRrVarianceComponent;
    total_variation: GageRrVarianceComponent;
    ndc: number | null;
    ndc_formula: string;
    negative_component_policy: string;
    interaction_policy: string;
  };
  warnings: string[];
  notes: string[];
}

export interface GageRunChartSample {
  n_total: number;
  n_used: number;
  n_excluded_missing_measurement: number;
  n_excluded_non_numeric_measurement: number;
  n_excluded_missing_part: number;
  n_excluded_missing_operator: number;
  n_excluded_missing_replicate: number;
  n_excluded_missing_identifier: number;
  n_excluded_missing_order: number;
  n_excluded_invalid_order: number;
}

export interface GageRunChartDesign {
  ready_for_chart: boolean;
  part_count: number;
  operator_count: number;
  replicate_count: number | null;
  expected_cell_count: number;
  observed_cell_count: number;
  missing_cell_count: number;
  min_replicates_per_cell: number;
  max_replicates_per_cell: number;
  replicate_set_consistent: boolean;
  duplicate_replicates_per_cell: number;
}

export interface GageRunChartSummary {
  mean: number;
  minimum: number;
  maximum: number;
  range: number;
}

export interface GageRunChartGroupSummary {
  index: number;
  n: number;
  mean: number;
  minimum: number;
  maximum: number;
  range: number;
}

export interface GageRunChartPoint {
  position: number;
  canonical_position: number;
  value: number;
  part_index: number;
  operator_index: number;
  replicate_index: number;
}

export interface GageRunChartPayload {
  point_count: number;
  points_truncated: boolean;
  point_limit: number;
  x_axis: "run_order";
  color_role: "operator_index";
  facet_role: "part_index";
  symbol_role: "replicate_index";
  label_policy: "part_operator_replicate_labels_redacted";
  points: GageRunChartPoint[];
}

export interface GageRunChartResult {
  schema_version: number;
  summary_type: "gage_run_chart";
  method: "measurement_system_run_chart";
  missing_policy: "complete_case";
  order_source: string;
  order_tie_breaker: string;
  columns: {
    measurement: GageRrPreflightResponse["columns"]["measurement"];
    part: GageRrPreflightResponse["columns"]["part"];
    operator: GageRrPreflightResponse["columns"]["operator"];
    replicate: GageRrPreflightResponse["columns"]["replicate"];
    order: GageRrPreflightResponse["columns"]["measurement"] | null;
  };
  sample: GageRunChartSample;
  design: GageRunChartDesign;
  summary: GageRunChartSummary;
  part_summaries: GageRunChartGroupSummary[];
  operator_summaries: GageRunChartGroupSummary[];
  chart: GageRunChartPayload;
  warnings: string[];
  notes: string[];
}
