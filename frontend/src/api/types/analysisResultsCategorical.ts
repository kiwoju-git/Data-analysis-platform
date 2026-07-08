import type { DatasetColumnResponse, DatasetColumnRole, DatasetMeasurementLevel } from "./datasets";

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
