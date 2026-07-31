import type { DatasetColumnResponse } from "./api";

export type DatasetColumnCompositionKind =
  | "numeric"
  | "categorical"
  | "datetime"
  | "other";

export interface DatasetColumnCompositionItem {
  kind: DatasetColumnCompositionKind;
  label: string;
  count: number;
}

const labels: Record<DatasetColumnCompositionKind, string> = {
  numeric: "수치형",
  categorical: "범주·문자형",
  datetime: "날짜시간형",
  other: "ID·기타",
};

export function summarizeDatasetColumnComposition(
  columns: readonly DatasetColumnResponse[],
): DatasetColumnCompositionItem[] {
  const counts: Record<DatasetColumnCompositionKind, number> = {
    numeric: 0,
    categorical: 0,
    datetime: 0,
    other: 0,
  };
  columns.forEach((column) => {
    counts[classifyDatasetColumn(column)] += 1;
  });
  return (Object.keys(counts) as DatasetColumnCompositionKind[]).map((kind) => ({
    kind,
    label: labels[kind],
    count: counts[kind],
  }));
}

function classifyDatasetColumn(
  column: DatasetColumnResponse,
): DatasetColumnCompositionKind {
  if (column.role === "id" || column.measurement_level === "id") {
    return "other";
  }
  if (column.data_type === "integer" || column.data_type === "decimal") {
    return "numeric";
  }
  if (column.data_type === "datetime" || column.measurement_level === "datetime") {
    return "datetime";
  }
  if (column.data_type === "text" || column.data_type === "boolean") {
    return "categorical";
  }
  return "other";
}
