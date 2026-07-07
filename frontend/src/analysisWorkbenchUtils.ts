import type { AnalysisMethodDescriptor } from "./api";

export function availabilityLabel(method: AnalysisMethodDescriptor): string {
  if (method.availability === "available") {
    return "사용 가능";
  }
  if (method.availability === "disabled") {
    return "비활성";
  }
  return "계획됨";
}

export function shortHash(value: string): string {
  return value.length <= 12 ? value : value.slice(0, 12);
}

export function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value.toLocaleString()} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("ko-KR");
}

export function comparisonCellValue(value: string | number | boolean | null): string {
  if (value === null) {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return value.length > 24 ? shortHash(value) : value;
}

export function comparisonNumberCell(value: number | null): string {
  if (value === null) {
    return "-";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toPrecision(6);
}

export function exportKindLabel(kind: string): string {
  if (kind === "analysis_result_json_export") {
    return "JSON";
  }
  if (kind === "analysis_result_csv_export") {
    return "CSV";
  }
  if (kind === "analysis_result_html_report") {
    return "HTML";
  }
  return kind;
}
