import type { AnalysisResultEnvelope, AnalysisRunRequest, AnalysisRunStatusResponse } from "./api";
import { ApiRequestError } from "./api/client";

export interface AnalysisExecutionSource {
  datasetVersionId: string | null;
  schemaHash: string | null;
  methodId: string | null;
  methodVersion: string | null;
  workspace: string;
  sourceChanging?: boolean;
}

export function analysisExecutionSourceKey(source: AnalysisExecutionSource): string {
  return JSON.stringify([source.datasetVersionId, source.schemaHash, source.methodId, source.methodVersion, source.workspace]);
}

export function analysisCompletionMatches(
  result: AnalysisResultEnvelope,
  request: AnalysisRunRequest,
  schemaHash: string,
): boolean {
  const provenance = result.provenance;
  return result.status === "succeeded" && typeof result.analysis_id === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(result.analysis_id) &&
    result.dataset_version_id === request.dataset_version_id && result.method_id === request.method_id &&
    result.method_version === request.method_version && provenance != null &&
    provenance.dataset_version_id === request.dataset_version_id && provenance.method_id === request.method_id &&
    provenance.method_version === request.method_version && provenance.source_schema_hash === schemaHash;
}

export function analysisStatusMatches(status: AnalysisRunStatusResponse, result: AnalysisResultEnvelope): boolean {
  return status.analysis_id === result.analysis_id && status.dataset_version_id === result.dataset_version_id &&
    status.method_id === result.method_id && status.method_version === result.method_version &&
    status.status === "succeeded" && status.result_available;
}

export function analysisExecutionErrorCode(cause: unknown): string {
  if (cause instanceof ApiRequestError) return cause.code;
  return cause instanceof Error && /^[a-z][a-z0-9_]+$/.test(cause.message)
    ? cause.message : "analysis_run_failed";
}
