export type AttributeControlLimitSetChartType = "p" | "np" | "c" | "u";

export interface AttributeControlLimitSetCreateRequest {
  source_analysis_id: string;
}

export interface AttributeControlLimitSetColumnDependency {
  column_id: string;
  data_type: string;
  measurement_level: string;
  role: string;
  unit: string | null;
}

export interface AttributeControlLimitSetResponse {
  asset_schema_version: 1;
  asset_sha256: string;
  limit_set_id: string;
  status: "closed";
  method_id: "quality.attribute_control_chart";
  source_method_version: "0.1.0" | "0.2.0" | "0.3.0";
  phase2_method_version: "0.2.0" | "0.3.0";
  source_result_schema_version: 1 | 2 | 3;
  source_analysis_id: string;
  source_dataset_version_id: string;
  source_schema_hash: string;
  source_canonical_sha256: string;
  source_config_sha256: string;
  source_result_sha256: string;
  filter_snapshot_sha256: string;
  row_snapshot_sha256: string;
  chart_type: AttributeControlLimitSetChartType;
  count_definition: "defectives" | "defects";
  count: AttributeControlLimitSetColumnDependency;
  denominator: AttributeControlLimitSetColumnDependency | null;
  denominator_role: "sample_size" | "inspection_opportunity" | null;
  baseline_point_count: number;
  total_count: number;
  total_denominator: number | null;
  frozen_center_line: number;
  fixed_sample_size: number | null;
  constant_opportunity_confirmed: boolean;
  sigma_multiplier: number;
  calculation_policy: "phase_2_frozen_three_sigma_v1";
  natural_bound_policy:
    | "binomial_zero_one"
    | "binomial_zero_fixed_sample_size"
    | "poisson_zero";
  eligibility: {
    eligible: true;
    policy: "phase_2_baseline_eligibility_v1";
    minimum_point_count: 20;
    checks_passed: Array<
      | "minimum_point_count"
      | "no_phase_1_limit_signals"
      | "usable_normal_approximation"
      | "pearson_dispersion_not_above_two"
      | "complete_untruncated_point_payload"
    >;
  };
  creator_provenance: {
    app_version: string;
    python_version: string;
    platform: string;
    build_commit: string | null;
    package_versions: Record<string, string>;
  };
  created_at: string;
  closed_at: string;
}

export interface AttributeControlLimitSetListResponse {
  total: number;
  offset: number;
  limit: number;
  items: AttributeControlLimitSetResponse[];
}

export interface AttributeControlLimitSetDeletionCounts {
  limit_set_count: 1;
  asset_file_count: 1;
  asset_file_bytes: number;
  metadata_record_count: 1;
  dependent_phase_2_analysis_count: number;
}

export interface AttributeControlLimitSetDeletionPreflightResponse {
  preflight_schema_version: 1;
  limit_set_id: string;
  source_analysis_id: string;
  method_id: "quality.attribute_control_chart";
  source_method_version: "0.1.0" | "0.2.0" | "0.3.0";
  deletion_ready: boolean;
  blockers: string[];
  counts: AttributeControlLimitSetDeletionCounts;
  deletion_manifest_sha256: string;
}

export interface AttributeControlLimitSetDeleteRequest {
  confirmation_limit_set_id: string;
  expected_deletion_manifest_sha256: string;
}

export interface AttributeControlLimitSetDeleteResponse {
  deletion_schema_version: 1;
  limit_set_id: string;
  source_analysis_id: string;
  deletion_manifest_sha256: string;
  deleted_at: string;
  deleted_counts: AttributeControlLimitSetDeletionCounts;
  cleanup_status: "deleted" | "quarantined_pending_cleanup";
}

export interface AttributeControlMonitoringPreflightRequest {
  target_dataset_version_id: string;
  chart_type: AttributeControlLimitSetChartType;
  count_definition: "defectives" | "defects";
  count_column_id: string;
  denominator_column_id: string | null;
  constant_opportunity_confirmed: boolean;
}

export interface AttributeControlMonitoringPreflightIssue {
  code: string;
  severity: "error";
  message: string;
}

export interface AttributeControlMonitoringPreflightResponse {
  schema_version: 2;
  method_id: "quality.attribute_control_chart";
  method_version: "0.3.0";
  phase: "phase_2";
  limit_set_id: string;
  limit_set_asset_sha256: string;
  target_dataset_version_id: string;
  target_schema_hash: string;
  target_canonical_sha256: string;
  chart_type: AttributeControlLimitSetChartType;
  count_definition: "defectives" | "defects";
  validation_scope: "schema_and_dependency_only";
  row_data_validated: false;
  ready: boolean;
  issues: AttributeControlMonitoringPreflightIssue[];
}
