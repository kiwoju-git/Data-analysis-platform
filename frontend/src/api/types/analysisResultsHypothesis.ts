import type { DatasetColumnResponse, DatasetColumnRole, DatasetMeasurementLevel } from "./datasets";

export interface TwoSampleTColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface TwoSampleTGroupSummary {
  group_label: string;
  group_index: number;
  n: number;
  mean: number;
  median: number;
  variance: number;
  std: number;
  min: number;
  max: number;
  warnings: string[];
}

export interface TwoSampleTConfidenceInterval {
  level: number;
  alternative: string;
  lower: number | null;
  upper: number | null;
}

export interface TwoSampleTEffectSize {
  standardizer: string;
  cohen_d: number | null;
  hedges_g: number | null;
  hedges_correction: number | null;
}

export interface TwoSampleTContrast {
  group_1_label: string;
  group_2_label: string;
  estimate: number;
  estimate_definition: string;
  null_difference: number;
  standard_error: number;
  statistic: number;
  df: number;
  p_value: number;
  reject_null: boolean;
  confidence_interval: TwoSampleTConfidenceInterval;
  effect_size: TwoSampleTEffectSize;
}

export interface TwoSampleTResult {
  schema_version: number;
  summary_type: "two_sample_t_test";
  method: string;
  variance_assumption: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  null_difference: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: TwoSampleTColumnRef;
  group: TwoSampleTColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_response: number;
  n_excluded_missing_group: number;
  n_excluded_non_numeric_response: number;
  group_count: number;
  groups: TwoSampleTGroupSummary[];
  contrast: TwoSampleTContrast;
}

export interface MannWhitneyColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface MannWhitneyGroupSummary {
  group_label: string;
  group_index: number;
  n: number;
  mean: number;
  median: number;
  min: number;
  max: number;
  rank_sum: number;
  mean_rank: number;
  warnings: string[];
}

export interface MannWhitneyEffectSize {
  rank_biserial: number;
  common_language_probability: number;
  definition: string;
}

export interface MannWhitneyTestResult {
  group_1_label: string;
  group_2_label: string;
  u_statistic: number;
  u_statistic_group: string;
  p_value: number;
  reject_null: boolean;
  alternative: string;
  requested_method: string;
  resolved_method: string;
  has_ties: boolean;
  effect_size: MannWhitneyEffectSize;
}

export interface MannWhitneyResult {
  schema_version: number;
  summary_type: "mann_whitney_u_test";
  method: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  requested_method: string;
  resolved_method: string;
  use_continuity: boolean;
  has_ties: boolean;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: MannWhitneyColumnRef;
  group: MannWhitneyColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_response: number;
  n_excluded_missing_group: number;
  n_excluded_non_numeric_response: number;
  group_count: number;
  groups: MannWhitneyGroupSummary[];
  test: MannWhitneyTestResult;
}

export interface KruskalWallisColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface KruskalWallisGroupSummary {
  group_label: string;
  group_index: number;
  n: number;
  mean: number;
  median: number;
  q1: number | null;
  q3: number | null;
  iqr: number | null;
  min: number;
  max: number;
  rank_sum: number;
  mean_rank: number;
  warnings: string[];
}

export interface KruskalWallisEffectSize {
  epsilon_squared: number | null;
  definition: string;
  tie_correction: number;
}

export interface KruskalWallisTestResult {
  h_statistic: number;
  df: number;
  p_value: number;
  reject_null: boolean;
  effect_size: KruskalWallisEffectSize;
}

export interface KruskalWallisPosthocComparison {
  group_1_label: string;
  group_2_label: string;
  mean_rank_difference: number;
  standard_error: number;
  z_statistic: number;
  raw_p_value: number;
  adjusted_p_value: number;
  reject_holm: boolean;
}

export interface KruskalWallisPosthocResult {
  method: string;
  multiplicity_method: string | null;
  policy: string;
  performed: boolean;
  reason: string | null;
  comparisons: KruskalWallisPosthocComparison[];
}

export interface KruskalWallisResult {
  schema_version: number;
  summary_type: "kruskal_wallis_test";
  method: string;
  missing_policy: string;
  alpha: number;
  posthoc_method: string;
  posthoc_policy: string;
  tie_correction: number;
  has_ties: boolean;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: KruskalWallisColumnRef;
  group: KruskalWallisColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_response: number;
  n_excluded_missing_group: number;
  n_excluded_non_numeric_response: number;
  group_count: number;
  groups: KruskalWallisGroupSummary[];
  test: KruskalWallisTestResult;
  posthoc: KruskalWallisPosthocResult;
}

export interface OneWayAnovaColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface OneWayAnovaConfidenceInterval {
  method: string;
  level: number;
  lower: number;
  upper: number;
}

export interface OneWayAnovaGroupSummary {
  group_label: string;
  group_index: number;
  n: number;
  mean: number;
  median: number;
  variance: number;
  std: number;
  sem: number;
  min: number;
  max: number;
  mean_confidence_interval: OneWayAnovaConfidenceInterval;
  warnings: string[];
}

export interface OneWayAnovaTableRow {
  source: string;
  sum_squares: number;
  df: number;
  mean_square: number | null;
}

export interface OneWayAnovaEffectSize {
  eta_squared: number;
  omega_squared: number;
  definition: string;
}

export interface OneWayAnovaTable {
  grand_mean: number;
  rows: OneWayAnovaTableRow[];
  ss_between: number;
  ss_within: number;
  ss_total: number;
  df_between: number;
  df_within: number;
  df_total: number;
  ms_between: number;
  ms_within: number;
  f_statistic: number;
  p_value: number;
  effect_size: OneWayAnovaEffectSize;
}

export interface OneWayAnovaTestResult {
  f_statistic: number;
  df_between: number;
  df_within: number;
  p_value: number;
  reject_null: boolean;
  effect_size: OneWayAnovaEffectSize;
}

export interface OneWayAnovaPosthocComparison {
  group_1_label: string;
  group_2_label: string;
  mean_1: number;
  mean_2: number;
  mean_difference: number;
  standard_error: number;
  q_statistic: number;
  raw_p_value: number;
  adjusted_p_value: number;
  reject_adjusted: boolean;
  confidence_interval: OneWayAnovaConfidenceInterval;
}

export interface OneWayAnovaPosthocResult {
  method: string;
  multiplicity_method: string | null;
  policy: string;
  performed: boolean;
  reason: string | null;
  confidence_level?: number;
  q_critical?: number;
  comparisons: OneWayAnovaPosthocComparison[];
}

export interface OneWayAnovaResult {
  schema_version: number;
  summary_type: "one_way_anova";
  method: string;
  anova_type: string;
  missing_policy: string;
  alpha: number;
  confidence_level: number;
  posthoc_method: string;
  posthoc_policy: string;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: OneWayAnovaColumnRef;
  group: OneWayAnovaColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_response: number;
  n_excluded_missing_group: number;
  n_excluded_non_numeric_response: number;
  group_count: number;
  groups: OneWayAnovaGroupSummary[];
  anova_table: OneWayAnovaTable;
  test: OneWayAnovaTestResult;
  posthoc: OneWayAnovaPosthocResult;
}

export interface OneSampleTColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface OneSampleTSampleSummary {
  n: number;
  mean: number;
  median: number;
  variance: number;
  std: number;
  min: number;
  max: number;
  warnings: string[];
}

export interface OneSampleTConfidenceInterval {
  level: number;
  alternative: string;
  lower: number | null;
  upper: number | null;
}

export interface OneSampleTEffectSize {
  standardizer: string;
  cohen_dz: number | null;
  hedges_g: number | null;
  hedges_correction: number | null;
}

export interface OneSampleTContrast {
  estimate: number;
  estimate_definition: string;
  null_mean: number;
  standard_error: number;
  statistic: number;
  df: number;
  p_value: number;
  reject_null: boolean;
  confidence_interval: OneSampleTConfidenceInterval;
  effect_size: OneSampleTEffectSize;
}

export interface OneSampleTResult {
  schema_version: number;
  summary_type: "one_sample_t_test";
  method: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  null_mean: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: OneSampleTColumnRef;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  sample: OneSampleTSampleSummary;
  contrast: OneSampleTContrast;
}

export interface EquivalenceTostBounds {
  lower: number;
  upper: number;
  scale: string;
  estimate_definition: string;
}

export interface EquivalenceTostEstimate {
  value: number;
  definition: string;
  standard_error: number;
  df: number;
}

export interface EquivalenceTostOneSidedTest {
  bound: number;
  null_hypothesis: string;
  alternative: string;
  statistic: number;
  df: number;
  p_value: number;
  reject_null: boolean;
}

export interface EquivalenceTostDecision {
  p_value: number;
  equivalent: boolean;
  decision_rule: string;
  ci_inside_equivalence_bounds: boolean;
}

export interface EquivalenceTostConfidenceInterval {
  level: number;
  lower: number;
  upper: number;
  inside_equivalence_bounds: boolean;
}

export interface EquivalenceTostEffectSize {
  standardizer: string;
  cohen_dz: number | null;
  hedges_g: number | null;
  hedges_correction: number | null;
}

export interface EquivalenceTostResult {
  schema_version: number;
  summary_type: "equivalence_tost";
  method: string;
  input_mode: string;
  design: "one_sample_mean";
  missing_policy: string;
  alpha: number;
  confidence_level: number;
  reference_mean: number;
  equivalence_bounds: EquivalenceTostBounds;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: OneSampleTColumnRef;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  sample: OneSampleTSampleSummary;
  estimate: EquivalenceTostEstimate;
  tests: {
    lower: EquivalenceTostOneSidedTest;
    upper: EquivalenceTostOneSidedTest;
  };
  tost: EquivalenceTostDecision;
  confidence_interval: EquivalenceTostConfidenceInterval;
  effect_size: EquivalenceTostEffectSize;
}

export interface PairedTColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface PairedTSampleSummary {
  n: number;
  before_mean: number;
  after_mean: number;
  mean_difference: number;
  median_difference: number;
  difference_variance: number;
  difference_std: number;
  min_difference: number;
  max_difference: number;
  positive_difference_count: number;
  negative_difference_count: number;
  zero_difference_count: number;
  warnings: string[];
}

export interface PairedTEffectSize {
  standardizer: string;
  cohen_dz: number | null;
  hedges_g: number | null;
  hedges_correction: number | null;
}

export interface PairedTContrast {
  estimate: number;
  estimate_definition: string;
  null_difference: number;
  standard_error: number;
  statistic: number;
  df: number;
  p_value: number;
  reject_null: boolean;
  confidence_interval: {
    level: number;
    alternative: string;
    lower: number | null;
    upper: number | null;
  };
  effect_size: PairedTEffectSize;
}

export interface PairedTResult {
  schema_version: number;
  summary_type: "paired_t_test";
  method: string;
  design: string;
  difference_definition: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  null_difference: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  before: PairedTColumnRef;
  after: PairedTColumnRef;
  n_total: number;
  n_used: number;
  n_incomplete_pairs: number;
  n_missing_before: number;
  n_missing_after: number;
  n_non_numeric_pairs: number;
  n_non_numeric_before: number;
  n_non_numeric_after: number;
  paired_sample: PairedTSampleSummary;
  contrast: PairedTContrast;
}

export interface OneSampleWilcoxonColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface OneSampleWilcoxonSampleSummary {
  n: number;
  mean: number;
  median: number;
  min: number;
  max: number;
  median_difference: number;
  positive_difference_count: number;
  negative_difference_count: number;
  zero_difference_count: number;
  warnings: string[];
}

export interface OneSampleWilcoxonEffectSize {
  rank_biserial: number | null;
  definition: string;
}

export interface OneSampleWilcoxonTestResult {
  w_statistic: number;
  p_value: number;
  reject_null: boolean;
  alternative: string;
  requested_method: string;
  resolved_method: string;
  zero_method: string;
  zero_difference_count: number;
  tie_count: number;
  positive_rank_sum: number;
  negative_rank_sum: number;
  zero_rank_sum: number;
  rank_sum_total: number;
  effect_size: OneSampleWilcoxonEffectSize;
}

export interface OneSampleWilcoxonResult {
  schema_version: number;
  summary_type: "one_sample_wilcoxon_signed_rank_test";
  method: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  null_location: number;
  requested_method: string;
  resolved_method: string;
  zero_method: string;
  correction: boolean;
  has_ties: boolean;
  tie_count: number;
  zero_difference_count: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: OneSampleWilcoxonColumnRef;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  n_nonzero: number;
  sample: OneSampleWilcoxonSampleSummary;
  test: OneSampleWilcoxonTestResult;
}
