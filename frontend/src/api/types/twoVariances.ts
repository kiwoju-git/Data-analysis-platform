export interface TwoVariancesOptions {
  response_column_id: string;
  group_column_id: string;
  numerator_group_key: string;
  denominator_group_key: string;
  method: "brown_forsythe" | "normal_f";
  ratio_scale: "variance" | "standard_deviation";
  hypothesized_ratio: number;
  alternative: "two_sided" | "less" | "greater";
  confidence_level: number;
  preflight_fingerprint?: string | null;
}
export interface TwoVariancesPreflightResponse {
  preflight_schema_version: 1;
  fingerprint: string;
  groups: Array<{ key: string; display_label: string; n_used: number }>;
  n_total: number; n_used: number; n_excluded: number;
  eligible: boolean;
  reason_codes: string[];
}
export type RatioBound = { kind: "finite"; value: number } | { kind: "unbounded"; value: null };
export interface TwoVariancesResult {
  schema_version: 1;
  summary_type: "two_variances_test";
  method: TwoVariancesOptions["method"];
  response: { column_id: string; display_name: string; unit: string | null };
  group_column: { column_id: string; display_name: string; unit: string | null };
  sample: { n_total: number; n_used: number; n_excluded: number; missing_policy: "complete_case" };
  groups: Array<{ key: string; label: string; role: "numerator" | "denominator"; n: number; mean: number; variance: number; standard_deviation: number }>;
  ratio_estimate: { scale: TwoVariancesOptions["ratio_scale"]; value: number; variance: number; standard_deviation: number };
  hypothesis: { ratio: number; alternative: TwoVariancesOptions["alternative"]; confidence_level: number };
  test: { statistic: number; df1: number; df2: number; p_value: number; alpha: number; reject: boolean };
  ratio_interval: { available: false; reason: string } | { available: true; reason: null; confidence_level: number; lower: RatioBound; upper: RatioBound };
  plot: { row_identity: "filtered_analysis_row"; point_limit_per_group: number; groups: Array<{ key: string; n_total: number; n_displayed: number; points: Array<{ row_number: number; value: number }> }> };
  warnings: string[];
  package_versions: Record<string, string>;
}
export function isTwoVariancesResult(value: unknown): value is TwoVariancesResult {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<TwoVariancesResult>;
  return item.schema_version === 1 && item.summary_type === "two_variances_test"
    && Array.isArray(item.groups) && item.groups.length === 2 && !!item.test && !!item.ratio_interval && !!item.plot;
}
