export interface CurvePreviewRequest {
  schema_version: 1;
  controls: { lower: number; target: number; upper: number; lower_desirability: number; upper_desirability: number; peak: 1 };
  plot_lower: number;
  plot_upper: number;
  assumed_distribution: { mean: number; standard_deviation: number; incumbent: number; xi: number } | null;
}
export interface CurvePreviewResponse {
  schema_version: 1; preview_only: true; persisted: false; applied_to_recommendations: false;
  request_snapshot: CurvePreviewRequest;
  curve_policy: "two_sided_gaussian_target_peak_one_v1";
  comparison_policy: "derringer_suich_linear_v1";
  moment_policy: "gaussian_target_closed_form_centered_variance_v1";
  points: { response_value: number; gaussian: number; linear: number }[];
  gaussian_underflow_count: number;
  metrics: { policy: string; mean: number | null; variance: number | null; second_moment: number | null;
    beta_ei: number | null; ei_distribution: string | null; unavailable_code: string | null; ei_unavailable_code: string | null;
    normal_tail_bound: number | null; integration_error: number | null }[];
}
