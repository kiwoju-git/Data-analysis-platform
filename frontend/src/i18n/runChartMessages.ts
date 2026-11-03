import type { ApiNoticeMessageKeys } from "./apiNoticePresentation";

// Only Run Chart warning display uses these keys; stored DTOs remain unchanged.
export const runChartNoticeKeys: ApiNoticeMessageKeys = {
  run_chart_not_control_chart: "runChart.notice.notControlChart",
  run_chart_uses_canonical_row_order: "runChart.notice.canonicalOrder",
  run_chart_uses_numeric_order_column: "runChart.notice.numericOrder",
  run_chart_uses_datetime_order_column: "runChart.notice.datetimeOrder",
  run_chart_trend_rule_defined: "runChart.notice.trendRule",
  run_chart_oscillation_rule_defined: "runChart.notice.oscillationRule",
  run_chart_runs_test_defined: "runChart.notice.exactRunsRule",
  run_chart_runs_test_unavailable: "runChart.notice.exactRunsUnavailable",
  missing_values_excluded: "runChart.notice.missingMeasurements",
  non_numeric_values_excluded: "runChart.notice.nonNumericMeasurements",
  run_chart_order_missing_excluded: "runChart.notice.missingOrder",
  run_chart_order_non_numeric_excluded: "runChart.notice.nonNumericOrder",
  run_chart_order_invalid_datetime_excluded: "runChart.notice.invalidDatetimeOrder",
  run_chart_order_ties_stable_sorted: "runChart.notice.orderTies",
  run_chart_ties_excluded_from_runs: "runChart.notice.medianTies",
  run_chart_trend_signal_detected: "runChart.notice.trendDetected",
  run_chart_oscillation_signal_detected: "runChart.notice.oscillationDetected",
  run_chart_clustering_signal_detected: "runChart.notice.clusteringDetected",
  run_chart_mixture_signal_detected: "runChart.notice.mixtureDetected",
  run_chart_points_truncated: "runChart.notice.pointsLimited",
};
