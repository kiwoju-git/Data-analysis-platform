import type { DatasetColumnResponse } from "./api";

export type LinearModelPredictorKind = "numeric" | "categorical" | "unsupported";

export function linearModelPredictorKind(
  column: DatasetColumnResponse,
): LinearModelPredictorKind {
  if (
    column.role === "id" ||
    column.measurement_level === "id" ||
    column.data_type === "datetime" ||
    column.measurement_level === "datetime"
  ) {
    return "unsupported";
  }
  if (
    column.measurement_level === "nominal" ||
    column.measurement_level === "ordinal" ||
    column.measurement_level === "binary"
  ) {
    return "categorical";
  }
  if (column.data_type === "integer" || column.data_type === "decimal") {
    return "numeric";
  }
  if (column.data_type === "text" || column.data_type === "boolean") {
    return "categorical";
  }
  return "unsupported";
}

export function isNumericLinearModelPredictor(column: DatasetColumnResponse): boolean {
  return linearModelPredictorKind(column) === "numeric";
}

export function isSupportedLinearModelPredictor(column: DatasetColumnResponse): boolean {
  return linearModelPredictorKind(column) !== "unsupported";
}

export function isSupportedLinearModelResponse(column: DatasetColumnResponse): boolean {
  return (
    column.role !== "id" &&
    column.measurement_level !== "id" &&
    (column.data_type === "integer" || column.data_type === "decimal") &&
    (column.measurement_level === "continuous" ||
      column.measurement_level === "count" ||
      column.measurement_level === "unknown")
  );
}
