import type { DatasetColumnResponse, DatasetColumnRole, DatasetMeasurementLevel } from "./datasets";

export interface DescriptiveColumnSummary {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  warnings: string[];
}

export interface DescriptiveStatisticsResult {
  schema_version: number;
  summary_type: "descriptive_statistics";
  missing_policy: string;
  quartile_method: string;
  quantile_position?: string;
  std_definition: string;
  columns: DescriptiveColumnSummary[];
}

export interface GraphicalHistogramBin {
  lower: number;
  upper: number;
  count: number;
  include_lower: boolean;
  include_upper: boolean;
}

export interface GraphicalHistogramSummary {
  binning: string;
  bin_count: number;
  bins: GraphicalHistogramBin[];
}

export interface GraphicalConfidenceInterval {
  computed: boolean;
  method: string;
  confidence_level: number;
  estimate: number | null;
  lower: number | null;
  upper: number | null;
}

export interface GraphicalNormalFitCurve {
  computed: boolean;
  scale: string;
  mean?: number | null;
  standard_deviation?: number | null;
  bin_width?: number | null;
  points: Array<{ x: number; expected_count: number }>;
}

export interface GraphicalBoxplotSummary {
  lower_whisker: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  upper_whisker: number | null;
  lower_fence: number | null;
  upper_fence: number | null;
  outlier_count: number;
}

export interface GraphicalPoint {
  theoretical?: number;
  sample?: number;
  x?: number;
  probability?: number;
}

export interface GraphicalPointSeries {
  point_count: number;
  points_truncated: boolean;
  points: GraphicalPoint[];
}

export interface GraphicalSummaryColumn {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  mean?: number | null;
  standard_deviation?: number | null;
  variance?: number | null;
  skewness?: number | null;
  kurtosis_excess?: number | null;
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  histogram: GraphicalHistogramSummary;
  normal_fit_curve?: GraphicalNormalFitCurve;
  anderson_darling?: NormalityAndersonDarlingResult;
  confidence_intervals?: {
    mean: GraphicalConfidenceInterval;
    median: GraphicalConfidenceInterval;
    standard_deviation: GraphicalConfidenceInterval;
  };
  boxplot: GraphicalBoxplotSummary;
  qq_plot: GraphicalPointSeries;
  ecdf: GraphicalPointSeries;
  warnings: string[];
}

export interface GraphicalSummaryResult {
  schema_version: number;
  summary_type: "graphical_summary";
  histogram_method: string;
  boxplot_method: string;
  quartile_method?: string;
  quantile_position?: string;
  confidence_level?: number;
  qq_plot_distribution: string;
  qq_plotting_position: string;
  ecdf_method: string;
  point_limit: number;
  columns: GraphicalSummaryColumn[];
}

export interface NormalityShapiroWilkResult {
  computed: boolean;
  statistic: number | null;
  p_value: number | null;
  valid_n_min: number;
  p_value_accuracy_n_max: number;
}

export interface NormalityAndersonCriticalValue {
  significance_level: number;
  critical_value: number;
  reject_normality: boolean;
}

export interface NormalityAndersonDecision {
  alpha: number;
  critical_value: number | null;
  reject_normality: boolean | null;
  method: string;
}

export interface NormalityAndersonDarlingResult {
  adjusted_statistic?: number | null;
  computed: boolean;
  p_value?: number | null;
  p_value_is_approximate?: boolean;
  p_value_method?: string;
  statistic: number | null;
  critical_values: NormalityAndersonCriticalValue[];
  decision_at_alpha: NormalityAndersonDecision | null;
}

export interface NormalityColumnSummary {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  mean: number | null;
  std: number | null;
  skewness: number | null;
  kurtosis_excess: number | null;
  shapiro_wilk: NormalityShapiroWilkResult;
  anderson_darling: NormalityAndersonDarlingResult;
  qq_plot: GraphicalPointSeries;
  warnings: string[];
}

export interface NormalityResult {
  schema_version: number;
  summary_type: "normality_test";
  missing_policy: string;
  alpha: number;
  qq_plot_distribution: string;
  qq_plotting_position: string;
  shape_moment_definition: string;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  columns: NormalityColumnSummary[];
}

export interface EqualVarianceColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface EqualVarianceGroupSummary {
  group_label: string;
  group_index: number;
  n: number;
  mean: number | null;
  median: number | null;
  variance: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  warnings: string[];
  comparison_interval?: { lower: number; upper: number } | null;
}

export interface EqualVarianceMultipleComparisonGroup {
  group_label: string;
  group_index: number;
  n: number;
  sample_standard_deviation: number;
  comparison_interval: { lower: number; upper: number };
  allocation: number;
}

export interface EqualVarianceMultipleComparisons {
  computed: boolean;
  method: string;
  alpha: number;
  p_value: number | null;
  reject_equal_variances: boolean | null;
  groups: EqualVarianceMultipleComparisonGroup[];
  non_overlapping_pairs: Array<{ left_group: string; right_group: string }>;
  pairwise_p_values: Array<{ left_group: string; right_group: string; p_value: number }>;
  warnings: string[];
}

export interface EqualVarianceTestResult {
  method: string;
  center: string;
  computed: boolean;
  statistic: number | null;
  p_value: number | null;
  alpha: number;
  reject_equal_variances: boolean | null;
  valid_group_n_min: number;
  warnings: string[];
}

export interface EqualVariancesResult {
  schema_version: number;
  summary_type: "equal_variances_test";
  missing_policy: string;
  alpha: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: EqualVarianceColumnRef;
  group: EqualVarianceColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_response: number;
  n_excluded_missing_group: number;
  n_excluded_non_numeric_response: number;
  group_count: number;
  groups: EqualVarianceGroupSummary[];
  tests: EqualVarianceTestResult[];
  multiple_comparisons?: EqualVarianceMultipleComparisons;
  levene?: EqualVarianceTestResult;
  additional_tests?: EqualVarianceTestResult[];
}

export interface PrincipalComponentsEigenanalysisRow {
  component: number;
  eigenvalue: number;
  proportion: number;
  cumulative_proportion: number;
  selected: boolean;
}

export interface PrincipalComponentsVectorRow {
  column_id: string;
  display_name: string;
  values: number[];
}

export interface PrincipalComponentsScoreRow {
  source_row_number: number;
  scores: number[];
  mahalanobis_distance_squared: number;
  outlier: boolean;
}

export interface PrincipalComponentsResult {
  schema_version: 1;
  summary_type: "principal_components_analysis";
  method: string;
  missing_policy: "complete_case";
  sample: {
    n_total: number;
    n_used: number;
    n_excluded: number;
    n_excluded_missing: number;
    n_excluded_non_numeric: number;
    variable_count: number;
  };
  variables: Array<{
    column_id: string;
    display_name: string;
    unit: string | null;
    mean: number;
    sample_standard_deviation: number;
  }>;
  preprocessing: {
    matrix_type: "correlation" | "covariance";
    centered: true;
    standardized: boolean;
    degrees_of_freedom: 1;
  };
  matrix: number[][];
  component_selection: {
    mode: "all" | "fixed" | "cumulative_threshold";
    requested_component_count: number | null;
    cumulative_threshold: number;
    maximum_components: number;
    selected_components: number;
    selected_cumulative_proportion: number;
  };
  eigenanalysis: PrincipalComponentsEigenanalysisRow[];
  eigenvectors: PrincipalComponentsVectorRow[];
  loadings: PrincipalComponentsVectorRow[];
  scores: PrincipalComponentsScoreRow[];
  plot: {
    point_limit: number;
    point_count: number;
    sampled: boolean;
    sampling_policy: string;
    points: PrincipalComponentsScoreRow[];
  };
  outliers: {
    alpha: number;
    method: string;
    degrees_of_freedom: number;
    reference_value: number;
    count: number;
  };
  warnings: string[];
  provenance: {
    algorithm: string;
    sign_policy: string;
    score_equation: string;
  };
}
