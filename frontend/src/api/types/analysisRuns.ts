export type AnalysisRunState =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancel_requested"
  | "cancelled";

export interface AnalysisRunListItem {
  analysis_id: string;
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  status: AnalysisRunState;
  stale: boolean;
  result_available: boolean;
  artifact_count: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface AnalysisRunListResponse {
  dataset_version_id: string | null;
  method_id: string | null;
  status: AnalysisRunState | null;
  stale: boolean | null;
  result_available: boolean | null;
  limit: number;
  offset: number;
  returned_count: number;
  has_more: boolean;
  runs: AnalysisRunListItem[];
}

export interface AnalysisRunDeletionCounts {
  analysis_run_count: 1;
  analysis_artifact_count: number;
  result_file_count: number;
  artifact_file_count: number;
  export_file_count: number;
  total_file_count: number;
  file_bytes: number;
  metadata_record_count: number;
  regression_model_count: number;
  regression_prediction_count: number;
  attribute_control_limit_set_count: number;
  job_reference_count: number;
}

export interface AnalysisRunDeletionPreflightResponse {
  preflight_schema_version: 1;
  analysis_id: string;
  method_id: string;
  method_version: string;
  status: AnalysisRunState;
  stale: boolean;
  deletion_ready: boolean;
  blockers: string[];
  counts: AnalysisRunDeletionCounts;
  deletion_manifest_sha256: string;
}

export interface AnalysisRunDeleteRequest {
  confirmation_analysis_id: string;
  expected_deletion_manifest_sha256: string;
}

export interface AnalysisRunDeleteResponse {
  deletion_schema_version: 1;
  analysis_id: string;
  deletion_manifest_sha256: string;
  deleted_at: string;
  deleted_counts: AnalysisRunDeletionCounts;
  cleanup_status: "deleted" | "quarantined_pending_cleanup";
}

export interface AnalysisRunComparisonSide {
  analysis_id: string;
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  status: "succeeded" | "failed" | "cancelled";
  stale: boolean;
  result_sha256: string;
  warning_count: number;
  summary_type: string | null;
  row_count_total: number | null;
  row_count_included: number | null;
  source_schema_hash: string | null;
  filter_snapshot_sha256: string | null;
  row_snapshot_sha256: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisRunComparisonCompatibility {
  same_method_id: boolean;
  same_method_version: boolean;
  same_dataset_version_id: boolean;
  same_summary_type: boolean;
}

export interface AnalysisRunComparisonDifference {
  field: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
}

export interface DescriptiveMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface DescriptiveColumnComparison {
  column_id: string;
  display_name: string;
  metrics: DescriptiveMetricComparison[];
}

export interface DescriptiveStatisticsComparison {
  summary_type: "descriptive_statistics";
  columns: DescriptiveColumnComparison[];
  left_only_column_ids: string[];
  right_only_column_ids: string[];
}

export interface OneSampleTMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface OneSampleTSettingComparison {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
}

export interface OneSampleTTestComparison {
  summary_type: "one_sample_t_test";
  left_response_column_id: string | null;
  right_response_column_id: string | null;
  response_display_name: string | null;
  same_response_column: boolean;
  settings: OneSampleTSettingComparison[];
  metrics: OneSampleTMetricComparison[];
}

export interface TwoSampleTMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface TwoSampleTSettingComparison {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
}

export interface TwoSampleTTestComparison {
  summary_type: "two_sample_t_test";
  left_response_column_id: string | null;
  right_response_column_id: string | null;
  response_display_name: string | null;
  same_response_column: boolean;
  left_group_column_id: string | null;
  right_group_column_id: string | null;
  group_display_name: string | null;
  same_group_column: boolean;
  same_group_label_set: boolean;
  same_group_label_order: boolean;
  settings: TwoSampleTSettingComparison[];
  metrics: TwoSampleTMetricComparison[];
}

export interface PairedTMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface PairedTSettingComparison {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
}

export interface PairedTTestComparison {
  summary_type: "paired_t_test";
  left_before_column_id: string | null;
  right_before_column_id: string | null;
  before_display_name: string | null;
  same_before_column: boolean;
  left_after_column_id: string | null;
  right_after_column_id: string | null;
  after_display_name: string | null;
  same_after_column: boolean;
  settings: PairedTSettingComparison[];
  metrics: PairedTMetricComparison[];
}

export interface EquivalenceTostMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface EquivalenceTostSettingComparison {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
}

export interface EquivalenceTostComparison {
  summary_type: "equivalence_tost";
  left_response_column_id: string | null;
  right_response_column_id: string | null;
  response_display_name: string | null;
  same_response_column: boolean;
  settings: EquivalenceTostSettingComparison[];
  metrics: EquivalenceTostMetricComparison[];
}

export interface OneWayAnovaMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface OneWayAnovaSettingComparison {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
}

export interface OneWayAnovaComparison {
  summary_type: "one_way_anova";
  left_response_column_id: string | null;
  right_response_column_id: string | null;
  response_display_name: string | null;
  same_response_column: boolean;
  left_group_column_id: string | null;
  right_group_column_id: string | null;
  group_display_name: string | null;
  same_group_column: boolean;
  same_group_label_set: boolean;
  same_group_label_order: boolean;
  settings: OneWayAnovaSettingComparison[];
  metrics: OneWayAnovaMetricComparison[];
}

export interface KruskalWallisMetricComparison {
  metric: string;
  left: number | null;
  right: number | null;
  delta: number | null;
}

export interface KruskalWallisSettingComparison {
  setting: string;
  left: string | number | boolean | null;
  right: string | number | boolean | null;
  same: boolean;
}

export interface KruskalWallisComparison {
  summary_type: "kruskal_wallis_test";
  left_response_column_id: string | null;
  right_response_column_id: string | null;
  response_display_name: string | null;
  same_response_column: boolean;
  left_group_column_id: string | null;
  right_group_column_id: string | null;
  group_display_name: string | null;
  same_group_column: boolean;
  same_group_label_set: boolean;
  same_group_label_order: boolean;
  settings: KruskalWallisSettingComparison[];
  metrics: KruskalWallisMetricComparison[];
}

export interface AnalysisRunMethodSpecificComparison {
  descriptive_statistics: DescriptiveStatisticsComparison | null;
  one_sample_t_test: OneSampleTTestComparison | null;
  two_sample_t_test: TwoSampleTTestComparison | null;
  paired_t_test: PairedTTestComparison | null;
  equivalence_tost: EquivalenceTostComparison | null;
  one_way_anova: OneWayAnovaComparison | null;
  kruskal_wallis: KruskalWallisComparison | null;
}

export interface AnalysisRunComparisonResponse {
  left: AnalysisRunComparisonSide;
  right: AnalysisRunComparisonSide;
  comparable: boolean;
  compatibility: AnalysisRunComparisonCompatibility;
  differences: AnalysisRunComparisonDifference[];
  method_specific: AnalysisRunMethodSpecificComparison | null;
}
