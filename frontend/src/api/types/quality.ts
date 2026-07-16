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
  source_method_version: "0.1.0";
  phase2_method_version: "0.2.0";
  source_result_schema_version: 1;
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
