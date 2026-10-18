import type { SavedPredictionDescriptor } from "./api/types/reports";

export function savedPredictionDescriptor(value: unknown, expected: {
  saveResult: boolean; family: "pls" | "gaussian_process"; analysisId: string; modelId: string; manifestSha256: string;
}): SavedPredictionDescriptor | null {
  const fail = (): never => { throw new Error("prediction_saved_result_invalid"); };
  if (value == null) return expected.saveResult ? fail() : null;
  if (!expected.saveResult || !record(value) || !record(value.source) ||
      value.source.kind !== "regression_prediction" || !record(value.source.prediction)) return fail();
  const source = value.source.prediction;
  if (source.storage !== "completed_prediction" || source.family !== expected.family ||
      source.source_analysis_id !== expected.analysisId || source.model_id !== expected.modelId ||
      source.model_manifest_sha256 !== expected.manifestSha256 ||
      !hash(source.source_result_sha256) || !hash(source.expected_source_sha256) ||
      typeof source.prediction_artifact_id !== "string" || !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/iu.test(source.prediction_artifact_id) ||
      typeof value.created_at !== "string" || !Number.isFinite(Date.parse(value.created_at))) return fail();
  return {
    source: { kind: "regression_prediction", prediction: {
      storage: "completed_prediction", family: expected.family, source_analysis_id: expected.analysisId,
      source_result_sha256: source.source_result_sha256, model_id: expected.modelId,
      model_manifest_sha256: expected.manifestSha256, prediction_artifact_id: source.prediction_artifact_id,
      expected_source_sha256: source.expected_source_sha256,
    } },
    created_at: value.created_at,
  };
}

function record(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function hash(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{64}$/u.test(value); }
