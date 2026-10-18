import type { ManagedReportDescriptor, ReportSourceDescriptor, ReportSourceKind, ReportSourceRef, StoredReportCapability, StoredSourceSnapshot } from "./api/types/reports";

export const REPORT_SOURCE_KINDS: readonly ReportSourceKind[] = ["analysis_run", "regression_prediction", "doe_analysis", "doe_optimizer_result", "lhs_design_revision", "bayesian_history_revision"];
const uuid = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/iu;
export const isReportHash = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/u.test(value);
const id = (value: unknown): value is string => typeof value === "string" && uuid.test(value);
const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const fields = (value: Record<string, unknown>, ids: string[], hashes: string[]) => ids.every((key) => id(value[key])) && hashes.every((key) => isReportHash(value[key]));
const revision = (value: unknown) => object(value) && fields(value, ["response_revision_id"], ["response_revision_sha256"]);

export function isReportSourceRef(value: unknown): value is ReportSourceRef {
  if (!object(value)) return false;
  switch (value.kind) {
    case "analysis_run": return fields(value, ["analysis_id"], ["expected_source_sha256"]);
    case "doe_analysis": return ["factorial", "general_factorial", "response_surface"].includes(String(value.family)) && fields(value, ["design_id", "design_version_id", "analysis_id"], ["design_sha256", "expected_source_sha256"]) && revision(value.response_revision);
    case "lhs_design_revision": return fields(value, ["design_id", "design_version_id"], ["expected_source_sha256"]) && Array.isArray(value.response_revisions) && value.response_revisions.length <= 32 && value.response_revisions.every(revision) && new Set(value.response_revisions.map((item) => (item as Record<string, unknown>).response_revision_id)).size === value.response_revisions.length;
    case "bayesian_history_revision": {
      if (!fields(value, ["study_id", "study_version_id", "history_revision_id"], ["definition_sha256", "expected_source_sha256"]) || !object(value.attachment)) return false;
      const attachment = value.attachment;
      return attachment.kind === "none" || (attachment.kind === "recommendation" && fields(attachment, ["recommendation_id"], ["result_json_sha256", "result_payload_sha256"])) || (attachment.kind === "batch" && fields(attachment, ["batch_id"], ["result_json_sha256", "result_payload_sha256"]));
    }
    case "regression_prediction": {
      const prediction = value.prediction;
      if (!object(prediction)) return false;
      if (prediction.storage === "analysis_run") return fields(prediction, ["analysis_id"], ["expected_source_sha256"]);
      if (prediction.storage === "completed_prediction") return ["pls", "gaussian_process"].includes(String(prediction.family)) && fields(prediction, ["source_analysis_id", "model_id", "prediction_artifact_id"], ["source_result_sha256", "model_manifest_sha256", "expected_source_sha256"]);
      return prediction.storage === "doe_prediction" && fields(prediction, ["prediction_id"], ["expected_source_sha256"]) && object(prediction.source) && prediction.source.kind === "doe_analysis" && isReportSourceRef(prediction.source);
    }
    case "doe_optimizer_result": {
      const optimizer = value.optimizer;
      if (!object(optimizer)) return false;
      if (optimizer.workflow === "regression") return fields(optimizer, ["analysis_id"], ["expected_source_sha256"]);
      return optimizer.workflow === "response_surface" && fields(optimizer, ["design_id", "design_version_id", "optimization_id"], ["design_sha256", "expected_source_sha256", "source_bundle_sha256"]) && Array.isArray(optimizer.source_dependencies) && optimizer.source_dependencies.length > 0 && optimizer.source_dependencies.length <= 32 && optimizer.source_dependencies.every((item: unknown) => object(item) && fields(item, ["analysis_id"], ["analysis_sha256"]) && revision(item.response_revision));
    }
    default: return false;
  }
}

export function reportSourceKey(source: ReportSourceRef): string {
  const stable = (value: unknown): unknown => Array.isArray(value) ? value.map(stable) : object(value) ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])])) : value;
  return JSON.stringify(stable(source));
}

export function isManagedReport(value: unknown): value is ManagedReportDescriptor {
  return object(value) && id(value.export_id) && isReportSourceRef(value.source) && isReportHash(value.source_ref_sha256) && isReportHash(value.sha256) &&
    ["en", "ko"].includes(String(value.locale)) && ["full", "summary"].includes(String(value.report_level)) && value.media_type === "text/html" &&
    typeof value.renderer_version === "string" && typeof value.created_at === "string" && typeof value.stale === "boolean" &&
    typeof value.size_bytes === "number" && Number.isSafeInteger(value.size_bytes) && value.size_bytes >= 0;
}

export function isReportSourceDescriptor(value: unknown): value is ReportSourceDescriptor {
  return object(value) && isReportSourceRef(value.source) && isReportHash(value.source_ref_sha256) && typeof value.title === "string" && typeof value.created_at === "string" && typeof value.stale === "boolean" && typeof value.open_target === "string";
}

export function isStoredReportCapability(value: unknown): value is StoredReportCapability {
  return object(value) && value.capability_schema_version === 1 && isReportSourceRef(value.source) && isReportHash(value.source_ref_sha256) && typeof value.title === "string" &&
    ["en", "ko"].includes(String(value.locale)) && ["full", "summary", "unsupported"].includes(String(value.report_level)) && typeof value.stale === "boolean" && typeof value.html_available === "boolean" &&
    (value.reason === null || typeof value.reason === "string") && (value.renderer_id === null || typeof value.renderer_id === "string") && (value.renderer_version === null || typeof value.renderer_version === "string") &&
    Array.isArray(value.sections) && value.sections.every((section: unknown) => object(section) && typeof section.section_id === "string" && typeof section.title === "string" && ["rendered", "missing", "not_applicable"].includes(String(section.status)) && (section.reason === null || typeof section.reason === "string"));
}

export function isStoredSourceSnapshot(value: unknown): value is StoredSourceSnapshot {
  return object(value) && value.schema_version === 1 && isReportSourceRef(value.source) && isReportHash(value.source_ref_sha256) &&
    ["en", "ko"].includes(String(value.locale)) && typeof value.title === "string" && typeof value.created_at === "string" &&
    typeof value.stale === "boolean" && object(value.payload);
}

export function managedReportQuery(search: string): { kind: ReportSourceKind; reportId: string | null; error: string | null } {
  const params = new URLSearchParams(search);
  const kinds = params.getAll("source_kind"), reports = params.getAll("report_id");
  const kind = kinds[0] ?? "regression_prediction";
  if (kinds.length > 1 || reports.length > 1 || !REPORT_SOURCE_KINDS.includes(kind as ReportSourceKind) || (reports.length > 0 && !id(reports[0]))) {
    return { kind: "regression_prediction", reportId: null, error: "managed_report_query_invalid" };
  }
  return { kind: kind as ReportSourceKind, reportId: reports[0] ?? null, error: null };
}

export function safeReportOpenTarget(value: string): string | null {
  const hasControl = Array.from(value).some((character) => character.charCodeAt(0) < 32 || character.charCodeAt(0) === 127);
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\") || hasControl) return null;
  const parsed = new URL(value, "http://local.invalid");
  return parsed.origin === "http://local.invalid" ? `${parsed.pathname}${parsed.search}${parsed.hash}` : null;
}
