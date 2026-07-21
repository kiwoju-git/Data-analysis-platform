import type {
  RegressionPredictionNumericCheck,
  RegressionPredictionPreflightIssue,
} from "./api";

export function groupPredictionPreflightIssues(
  issues: RegressionPredictionPreflightIssue[],
) {
  const sourceBlockers = issues.filter(
    (issue) =>
      issue.code.startsWith("regression_prediction_source_") && issue.severity === "error",
  );
  const mappingIssues = issues.filter(
    (issue) => issue.code === "prediction_column_matched_by_display_name",
  );
  const hiddenCodes = new Set([
    "prediction_schema_hash_mismatch",
    "prediction_column_matched_by_display_name",
    "prediction_extrapolation_risk",
  ]);
  return {
    sourceBlockers,
    mappingIssues,
    otherIssues: issues.filter(
      (issue) => !hiddenCodes.has(issue.code) && !sourceBlockers.includes(issue),
    ),
  };
}

export function predictionRangeRows(checks: RegressionPredictionNumericCheck[]) {
  return checks.filter(
    (check) => check.n_below_training_range + check.n_above_training_range > 0,
  );
}
