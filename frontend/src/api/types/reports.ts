import type { ReportSectionCapability } from "./reportCapabilities";

export type ReportSourceKind = "analysis_run" | "regression_prediction" | "doe_analysis" | "doe_optimizer_result" | "lhs_design_revision" | "bayesian_history_revision";
export interface ResponseRevisionRef { response_revision_id: string; response_revision_sha256: string }
export interface AnalysisRunReportSource { kind: "analysis_run"; analysis_id: string; expected_source_sha256: string }
export interface DoeAnalysisReportSource {
  kind: "doe_analysis";
  family: "factorial" | "general_factorial" | "response_surface";
  design_id: string; design_version_id: string; design_sha256: string;
  analysis_id: string; expected_source_sha256: string; response_revision: ResponseRevisionRef;
}
export interface CompletedPredictionRef {
  storage: "completed_prediction"; family: "pls" | "gaussian_process";
  source_analysis_id: string; source_result_sha256: string; model_id: string;
  model_manifest_sha256: string; prediction_artifact_id: string; expected_source_sha256: string;
}
export interface RegressionPredictionReportSource {
  kind: "regression_prediction";
  prediction: CompletedPredictionRef
    | { storage: "analysis_run"; analysis_id: string; expected_source_sha256: string }
    | { storage: "doe_prediction"; source: DoeAnalysisReportSource; prediction_id: string; expected_source_sha256: string };
}
export interface DoeOptimizerReportSource {
  kind: "doe_optimizer_result";
  optimizer: { workflow: "regression"; analysis_id: string; expected_source_sha256: string }
    | { workflow: "response_surface"; design_id: string; design_version_id: string; design_sha256: string;
      optimization_id: string; expected_source_sha256: string; source_bundle_sha256: string;
      source_dependencies: Array<{ analysis_id: string; analysis_sha256: string; response_revision: ResponseRevisionRef }> };
}
export interface LhsDesignReportSource {
  kind: "lhs_design_revision"; design_id: string; design_version_id: string;
  expected_source_sha256: string; response_revisions: ResponseRevisionRef[];
}
export interface BayesianHistoryReportSource {
  kind: "bayesian_history_revision"; study_id: string; study_version_id: string;
  definition_sha256: string; history_revision_id: string; expected_source_sha256: string;
  attachment: { kind: "none" }
    | { kind: "recommendation"; recommendation_id: string; result_json_sha256: string; result_payload_sha256: string }
    | { kind: "batch"; batch_id: string; result_json_sha256: string; result_payload_sha256: string };
}
export type ReportSourceRef = AnalysisRunReportSource | RegressionPredictionReportSource | DoeAnalysisReportSource | DoeOptimizerReportSource | LhsDesignReportSource | BayesianHistoryReportSource;
export interface ReportSourceDescriptor {
  source: ReportSourceRef; source_ref_sha256: string; title: string; created_at: string; stale: boolean; open_target: string;
}
export interface ReportSourceList { items: ReportSourceDescriptor[]; limit: number; offset: number; has_more: boolean }
export interface StoredReportCapability {
  capability_schema_version: 1; source: ReportSourceRef; source_ref_sha256: string; title: string;
  locale: "en" | "ko"; stale: boolean; report_level: "full" | "summary" | "unsupported";
  renderer_id: string | null; renderer_version: string | null;
  sections: ReportSectionCapability[]; reason: string | null; html_available: boolean;
}
export interface ManagedReportDescriptor {
  export_id: string; source: ReportSourceRef; source_ref_sha256: string; locale: "en" | "ko";
  report_level: "full" | "summary"; renderer_version: string; sha256: string; size_bytes: number;
  created_at: string; stale: boolean; media_type: "text/html";
}
export interface ManagedReportList { items: ManagedReportDescriptor[] }
export interface SavedPredictionDescriptor { source: RegressionPredictionReportSource; created_at: string }
export interface StoredSourceSnapshot {
  schema_version: 1; source: ReportSourceRef; source_ref_sha256: string; locale: "en" | "ko";
  title: string; created_at: string; stale: boolean; payload: Record<string, unknown>;
}
