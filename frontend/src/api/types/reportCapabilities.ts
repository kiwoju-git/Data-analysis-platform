export interface ReportSectionContract {
  section_id: string;
  core: boolean;
}

export interface ReportVariantContract {
  variant_id: string;
  sections: ReportSectionContract[];
}

export interface MethodReportContract {
  method_id: string;
  summary_type: string;
  accepted_schema_versions: number[];
  renderer_id: string;
  renderer_version: string;
  variants: ReportVariantContract[];
}

export interface ReportSectionCapability {
  section_id: string;
  title: string;
  status: "rendered" | "missing" | "not_applicable";
  reason: string | null;
}

export interface AnalysisReportCapability {
  capability_schema_version: 1;
  analysis_id: string;
  method_id: string;
  summary_type: string | null;
  result_schema_version: number | null;
  source_result_sha256: string;
  stale: boolean;
  locale: "en" | "ko";
  renderer_id: string | null;
  renderer_version: string | null;
  variant_id: string | null;
  report_level: "full" | "summary" | "unsupported";
  sections: ReportSectionCapability[];
  reason: string | null;
  html_available: boolean;
  source_validation: "stored_dependencies_only";
}

export interface AnalysisResultHtmlReportRequest {
  locale: "en" | "ko";
  expected_source_result_sha256?: string;
}
