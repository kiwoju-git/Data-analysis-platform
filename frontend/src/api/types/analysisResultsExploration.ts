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
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  histogram: GraphicalHistogramSummary;
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
}
