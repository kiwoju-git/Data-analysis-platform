import type { AnalysisResultEnvelope } from "./analyses";

export interface AnalysisResultJsonExportResponse {
  schema_version: number;
  export_id: string;
  analysis_id: string;
  format: "analysis_result_json";
  artifact_kind: "analysis_result_json_export";
  media_type: "application/json";
  sha256: string;
  size_bytes: number;
  source_result_sha256: string;
  stale: boolean;
  created_at: string;
  result: AnalysisResultEnvelope;
}

export interface AnalysisResultCsvExportResponse {
  schema_version: number;
  export_id: string;
  analysis_id: string;
  format: "analysis_result_csv";
  artifact_kind: "analysis_result_csv_export";
  media_type: "text/csv";
  sha256: string;
  size_bytes: number;
  source_result_sha256: string;
  stale: boolean;
  created_at: string;
  columns: string[];
  row_count: number;
  preview_rows: string[][];
}

export interface AnalysisResultHtmlReportResponse {
  schema_version: number;
  export_id: string;
  analysis_id: string;
  format: "analysis_result_html_report";
  artifact_kind: "analysis_result_html_report";
  media_type: "text/html";
  sha256: string;
  size_bytes: number;
  source_result_sha256: string;
  stale: boolean;
  created_at: string;
  title: string;
  section_count: number;
}

export interface AnalysisResultExportListItem {
  export_id: string;
  analysis_id: string;
  artifact_kind: string;
  media_type: string;
  sha256: string;
  created_at: string;
  download_url: string;
}

export interface AnalysisResultExportListResponse {
  analysis_id: string;
  exports: AnalysisResultExportListItem[];
}
