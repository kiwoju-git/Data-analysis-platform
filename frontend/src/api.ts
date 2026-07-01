export interface HealthResponse {
  status: "ready";
  service: "datalab-studio-api";
  version: string;
}

export interface UploadWarning {
  code: string;
  message: string;
}

export interface DelimiterCandidate {
  delimiter: string;
  label: string;
  score: number;
}

export interface ParsingSuggestion {
  kind: "delimited_text" | "xlsx";
  encoding_candidates: string[];
  suggested_encoding: string | null;
  delimiter_candidates: DelimiterCandidate[];
  suggested_delimiter: string | null;
  quote_char: string | null;
  decimal: string;
  thousands: string | null;
  has_header: boolean;
  header_row: number;
  data_start_row: number;
  xlsx_requires_sheet_selection: boolean;
}

export interface DatasetUploadResponse {
  dataset_id: string;
  original_filename: string;
  size_bytes: number;
  sha256: string;
  detected_format: "csv" | "tsv" | "xlsx" | "delimited_text";
  parsing: ParsingSuggestion;
  warnings: UploadWarning[];
  next_step: "confirm_schema";
}

export interface PastedDatasetRequest {
  content: string;
  original_filename?: string | null;
}

export interface ConfirmedParsingOptions {
  kind: "delimited_text" | "xlsx";
  encoding: string | null;
  delimiter: string | null;
  quote_char: string | null;
  decimal: string;
  thousands: string | null;
  has_header: boolean;
  header_row: number;
  data_start_row: number | null;
  missing_tokens: string[];
  xlsx_sheet_name: string | null;
}

export interface DatasetParsingConfirmationRequest {
  parsing: ConfirmedParsingOptions;
  columns: [];
}

export type DatasetMeasurementLevel =
  | "unknown"
  | "continuous"
  | "ordinal"
  | "nominal"
  | "binary"
  | "count"
  | "datetime"
  | "id";

export type DatasetColumnRole =
  | "unspecified"
  | "id"
  | "feature"
  | "target"
  | "group"
  | "time"
  | "order"
  | "subgroup_id"
  | "part_id"
  | "operator_id"
  | "replicate_id"
  | "sample_size"
  | "opportunities"
  | "factor"
  | "response";

export interface DatasetColumnResponse {
  column_id: string;
  version_id: string;
  column_index: number;
  original_name: string;
  display_name: string;
  data_type: "integer" | "decimal" | "boolean" | "datetime" | "text";
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface DatasetArtifactResponse {
  artifact_id: string;
  version_id: string;
  kind: string;
  path: string;
  sha256: string;
  media_type: string;
  size_bytes: number;
  created_at: string;
}

export interface DatasetVersionResponse {
  version_id: string;
  dataset_id: string;
  version_number: number;
  row_count: number;
  column_count: number;
  schema_hash: string;
  created_at: string;
  source_sha256: string;
  parsing: ConfirmedParsingOptions;
  columns: DatasetColumnResponse[];
  canonical_artifact: DatasetArtifactResponse | null;
}

export interface DatasetColumnSchemaUpdate {
  column_id: string;
  display_name: string;
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface DatasetSchemaUpdateRequest {
  columns: DatasetColumnSchemaUpdate[];
}

export interface DatasetSchemaResponse {
  version_id: string;
  dataset_id: string;
  schema_hash: string;
  columns: DatasetColumnResponse[];
}

export interface DatasetPreviewRow {
  row_index: number;
  values: Array<string | null>;
}

export interface DatasetRowsPreviewResponse {
  version_id: string;
  offset: number;
  limit: number;
  total_rows: number;
  returned_rows: number;
  columns: DatasetColumnResponse[];
  rows: DatasetPreviewRow[];
}

export interface DatasetProfileIssue {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
}

export interface DatasetDateTimeFormatCandidate {
  format: string;
  n_matched: number;
}

export interface DatasetDateTimeProfile {
  n_datetime: number;
  n_non_datetime: number;
  datetime_min: string | null;
  datetime_max: string | null;
  timezone_aware_count: number;
  timezone_naive_count: number;
  mixed_timezone_awareness: boolean;
  format_candidates: DatasetDateTimeFormatCandidate[];
}

export interface DatasetColumnProfile {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  n_total: number;
  n_present: number;
  n_missing: number;
  missing_rate: number;
  unique_count: number;
  unique_count_capped: boolean;
  n_numeric: number;
  n_non_numeric: number;
  numeric_min: number | null;
  numeric_max: number | null;
  numeric_mean: number | null;
  datetime_profile: DatasetDateTimeProfile | null;
  constant: boolean;
  warnings: DatasetProfileIssue[];
}

export interface DatasetProfileResponse {
  profile_schema_version: number;
  version_id: string;
  dataset_id: string;
  row_count: number;
  column_count: number;
  schema_hash: string;
  computed_at: string;
  unique_count_limit: number;
  canonical_artifact: DatasetArtifactResponse | null;
  profile_artifact: DatasetArtifactResponse | null;
  preflight: {
    estimated_memory_bytes: number;
    duplicate_row_count: number;
    duplicate_row_count_capped: boolean;
    duplicate_row_check_limit: number;
  };
  columns: DatasetColumnProfile[];
  warnings: DatasetProfileIssue[];
}

export type AnalysisModuleId =
  | "exploration"
  | "hypothesis"
  | "categorical"
  | "regression"
  | "quality"
  | "doe";

export type MethodAvailability = "available" | "planned" | "disabled";

export type AnalysisExecutionMode = "inline" | "job";

export interface AnalysisModuleDescriptor {
  module_id: AnalysisModuleId;
  label_ko: string;
  label_en: string;
  order: number;
}

export interface AnalysisMethodDescriptor {
  method_id: string;
  method_version: string;
  module_id: AnalysisModuleId;
  label_ko: string;
  label_en: string;
  availability: MethodAvailability;
  execution_mode: AnalysisExecutionMode;
  requires_dataset: boolean;
  order: number;
  disabled_reason: string | null;
}

export interface AnalysisMethodListResponse {
  modules: AnalysisModuleDescriptor[];
  methods: AnalysisMethodDescriptor[];
}

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

export type AnalysisFilterOperator =
  | "is_missing"
  | "is_not_missing"
  | "eq"
  | "ne"
  | "gt"
  | "gte"
  | "lt"
  | "lte";

export interface AnalysisFilterCondition {
  column_id: string;
  operator: AnalysisFilterOperator;
  value?: string | number | null;
}

export interface AnalysisFilterSnapshot {
  expression_version: number;
  conditions: AnalysisFilterCondition[];
}

export interface AnalysisRunRequest {
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  filter_snapshot: AnalysisFilterSnapshot;
  roles: Record<string, string>;
  options: Record<string, unknown>;
}

export interface AnalysisWarning {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
}

export interface AnalysisProvenance {
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  source_schema_hash: string | null;
  filter_snapshot_sha256?: string | null;
  row_snapshot_sha256?: string | null;
  row_count_total?: number | null;
  row_count_included?: number | null;
  app_version: string;
}

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
  computed: boolean;
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

export interface OneProportionColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface OneProportionLevelSummary {
  level: string;
  count: number;
  is_event: boolean;
}

export interface OneProportionSampleSummary {
  event_count: number;
  non_event_count: number;
  total: number;
  sample_proportion: number;
  difference_from_null: number;
  odds: number | null;
}

export interface OneProportionTestResult {
  statistic: number;
  statistic_name: string;
  p_value: number;
  reject_null: boolean;
  alternative: string;
  exact: boolean;
}

export interface OneProportionConfidenceInterval {
  method: string;
  level: number;
  lower: number;
  upper: number;
}

export interface OneProportionEffectSize {
  cohen_h: number;
  definition: string;
}

export interface OneProportionResult {
  schema_version: number;
  summary_type: "one_proportion_test";
  method: string;
  input_mode: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  ci_method: string;
  null_proportion: number;
  event_level: string;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: OneProportionColumnRef;
  n_total: number;
  n_used: number;
  n_missing: number;
  levels: OneProportionLevelSummary[];
  sample: OneProportionSampleSummary;
  test: OneProportionTestResult;
  confidence_interval: OneProportionConfidenceInterval;
  effect_size: OneProportionEffectSize;
}

export interface TwoProportionColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface TwoProportionLevelSummary {
  level: string;
  count: number;
}

export interface TwoProportionGroupSummary {
  group_label: string;
  group_index: number;
  event_count: number;
  non_event_count: number;
  total: number;
  sample_proportion: number;
  levels: TwoProportionLevelSummary[];
  warnings: string[];
}

export interface TwoProportionConfidenceInterval {
  method: string;
  level: number;
  lower: number;
  upper: number;
}

export interface TwoProportionDifferenceResult {
  estimate: number;
  definition: string;
  confidence_interval: TwoProportionConfidenceInterval;
}

export interface TwoProportionEffectMeasure {
  estimate: number | null;
  confidence_interval: TwoProportionConfidenceInterval | null;
  definition: string;
}

export interface TwoProportionEffectSizes {
  risk_ratio: TwoProportionEffectMeasure;
  odds_ratio: TwoProportionEffectMeasure;
}

export interface TwoProportionContingencyRow {
  group_label: string;
  event_count: number;
  non_event_count: number;
}

export interface TwoProportionContingencyTable {
  columns: string[];
  rows: TwoProportionContingencyRow[];
  expected_counts: number[][];
  min_expected_count: number;
}

export interface TwoProportionTestResult {
  statistic: number | null;
  statistic_name: string;
  p_value: number;
  reject_null: boolean;
  alternative: string;
  exact: boolean;
}

export interface TwoProportionResult {
  schema_version: number;
  summary_type: "two_proportion_test";
  method: string;
  input_mode: string;
  missing_policy: string;
  alternative: string;
  alpha: number;
  confidence_level: number;
  ci_method: string;
  event_level: string;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  response: TwoProportionColumnRef;
  group: TwoProportionColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_response: number;
  n_excluded_missing_group: number;
  group_count: number;
  groups: TwoProportionGroupSummary[];
  contingency_table: TwoProportionContingencyTable;
  difference: TwoProportionDifferenceResult;
  effect_sizes: TwoProportionEffectSizes;
  test: TwoProportionTestResult;
}

export interface ChiSquareAssociationColumnRef {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface ChiSquareAssociationLevelSummary {
  level: string;
  index: number;
  count: number;
}

export interface ChiSquareAssociationCell {
  column_level: string;
  observed: number;
  expected: number;
  row_percent: number | null;
  column_percent: number | null;
  total_percent: number | null;
  standardized_residual: number | null;
}

export interface ChiSquareAssociationTableRow {
  row_level: string;
  row_total: number;
  cells: ChiSquareAssociationCell[];
}

export interface ChiSquareAssociationContingencyTable {
  row_levels: string[];
  column_levels: string[];
  rows: ChiSquareAssociationTableRow[];
  column_totals: number[];
  grand_total: number;
}

export interface ChiSquareAssociationExpectedCountSummary {
  min_expected: number;
  cells_below_1: number;
  cells_below_5: number;
  cell_count: number;
  share_below_5: number;
  rule_of_thumb_passed: boolean;
}

export interface ChiSquareAssociationTestResult {
  statistic: number;
  statistic_name: string;
  df: number;
  p_value: number;
  reject_null: boolean;
  continuity_correction: boolean;
}

export interface ChiSquareAssociationEffectSize {
  cramers_v: number;
  definition: string;
}

export interface ChiSquareAssociationRecommendedAlternative {
  method: string;
  reason: string;
  implemented: boolean;
}

export interface ChiSquareAssociationResult {
  schema_version: number;
  summary_type: "chi_square_association";
  method: string;
  input_mode: string;
  missing_policy: string;
  alpha: number;
  package_versions: {
    numpy: string;
    scipy: string;
  };
  warnings: string[];
  row_variable: ChiSquareAssociationColumnRef;
  column_variable: ChiSquareAssociationColumnRef;
  n_total: number;
  n_used: number;
  n_excluded_missing_row: number;
  n_excluded_missing_column: number;
  row_levels: ChiSquareAssociationLevelSummary[];
  column_levels: ChiSquareAssociationLevelSummary[];
  contingency_table: ChiSquareAssociationContingencyTable;
  expected_count_summary: ChiSquareAssociationExpectedCountSummary;
  test: ChiSquareAssociationTestResult;
  effect_size: ChiSquareAssociationEffectSize;
  recommended_alternative_tests: ChiSquareAssociationRecommendedAlternative[];
}

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

export interface AnalysisResultEnvelope {
  analysis_id: string;
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  status: "succeeded" | "failed" | "cancelled";
  warnings: AnalysisWarning[];
  provenance: AnalysisProvenance;
  result:
    | DescriptiveStatisticsResult
    | GraphicalSummaryResult
    | NormalityResult
    | EqualVariancesResult
    | OneSampleTResult
    | EquivalenceTostResult
    | PairedTResult
    | OneSampleWilcoxonResult
    | TwoSampleTResult
    | MannWhitneyResult
    | KruskalWallisResult
    | OneWayAnovaResult
    | OneProportionResult
    | TwoProportionResult
    | ChiSquareAssociationResult
    | PearsonCorrelationResult
    | XyCorrelationResult
    | IndividualsChartResult
    | SubgroupChartResult
    | RunChartResult
    | CapabilityResult
    | GageRrResult
    | GageRunChartResult
    | LinearModelResult
    | Record<string, unknown>
    | null;
}

export function getApiBaseUrl(): string {
  const configuredBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl;
  }
  return "http://127.0.0.1:8000";
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ready" &&
    candidate.service === "datalab-studio-api" &&
    typeof candidate.version === "string"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/health`, {
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error("health_check_failed");
  }

  const payload: unknown = await response.json();
  if (!isHealthResponse(payload)) {
    throw new Error("invalid_health_response");
  }

  return payload;
}

export async function uploadDataset(file: File): Promise<DatasetUploadResponse> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/datasets`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_upload_failed"));
  }

  return (await response.json()) as DatasetUploadResponse;
}

export async function createDatasetFromPastedText(
  request: PastedDatasetRequest,
): Promise<DatasetUploadResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/datasets/paste`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_paste_failed"));
  }

  return (await response.json()) as DatasetUploadResponse;
}

export async function confirmDatasetParsing(
  datasetId: string,
  request: DatasetParsingConfirmationRequest,
): Promise<DatasetVersionResponse> {
  const response = await fetchApi(
    `${getApiBaseUrl()}/api/v1/datasets/${datasetId}/confirm-parsing`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "parsing_confirmation_failed"));
  }

  return (await response.json()) as DatasetVersionResponse;
}

export async function updateDatasetSchema(
  versionId: string,
  request: DatasetSchemaUpdateRequest,
): Promise<DatasetSchemaResponse> {
  const response = await fetchApi(
    `${getApiBaseUrl()}/api/v1/dataset-versions/${versionId}/schema`,
    {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "schema_update_failed"));
  }

  return (await response.json()) as DatasetSchemaResponse;
}

export async function fetchRowsPreview(
  versionId: string,
  offset: number,
  limit: number,
): Promise<DatasetRowsPreviewResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetchApi(
    `${getApiBaseUrl()}/api/v1/dataset-versions/${versionId}/rows?${params.toString()}`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "rows_preview_failed"));
  }

  return (await response.json()) as DatasetRowsPreviewResponse;
}

export async function fetchDatasetProfile(versionId: string): Promise<DatasetProfileResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/dataset-versions/${versionId}/profile`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_profile_failed"));
  }

  return (await response.json()) as DatasetProfileResponse;
}

export async function fetchAnalysisMethods(
  signal?: AbortSignal,
): Promise<AnalysisMethodListResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/analysis-methods`, {
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_methods_failed"));
  }

  return (await response.json()) as AnalysisMethodListResponse;
}

export async function createFactorialDesign(
  request: FactorialDesignCreateRequest,
): Promise<FactorialDesignResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/doe-designs/factorial`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_design_failed"));
  }

  return (await response.json()) as FactorialDesignResponse;
}

export async function fetchFactorialDesign(designId: string): Promise<FactorialDesignResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/doe-designs/${designId}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_design_fetch_failed"));
  }

  return (await response.json()) as FactorialDesignResponse;
}

export async function saveFactorialDesignResponses(
  designId: string,
  request: DoeDesignResponsesUpsertRequest,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/doe-designs/${designId}/responses`, {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_responses_failed"));
  }

  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function fetchFactorialDesignResponses(
  designId: string,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/doe-designs/${designId}/responses`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_responses_fetch_failed"));
  }

  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function createAnalysisRun(
  request: AnalysisRunRequest,
): Promise<AnalysisResultEnvelope> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/analysis-runs`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_run_failed"));
  }

  return (await response.json()) as AnalysisResultEnvelope;
}

export async function fetchRegressionPredictionPreflight(
  modelId: string,
  request: RegressionPredictionPreflightRequest,
): Promise<RegressionPredictionPreflightResponse> {
  const response = await fetchApi(
    `${getApiBaseUrl()}/api/v1/regression-models/${modelId}/prediction-preflight`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "regression_prediction_preflight_failed"));
  }

  return (await response.json()) as RegressionPredictionPreflightResponse;
}

export async function fetchGageRrPreflight(
  request: GageRrPreflightRequest,
): Promise<GageRrPreflightResponse> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/quality/gage-rr/preflight`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "gage_rr_preflight_failed"));
  }

  return (await response.json()) as GageRrPreflightResponse;
}

export async function fetchRegressionPredictions(
  modelId: string,
  request: RegressionPredictionRequest,
): Promise<RegressionPredictionResponse> {
  const response = await fetchApi(
    `${getApiBaseUrl()}/api/v1/regression-models/${modelId}/predictions`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "regression_prediction_failed"));
  }

  return (await response.json()) as RegressionPredictionResponse;
}

async function fetchApi(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error("api_unreachable");
    }
    throw error;
  }
}

async function apiErrorCode(response: Response, fallback: string): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (typeof payload === "object" && payload !== null) {
      const error = (payload as Record<string, unknown>).error;
      if (typeof error === "object" && error !== null) {
        const code = (error as Record<string, unknown>).code;
        if (typeof code === "string" && code.length > 0) {
          return code;
        }
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}
