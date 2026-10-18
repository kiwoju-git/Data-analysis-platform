import type { PlsPointPredictionRequest, PlsPointPredictionResponse } from "./api/types/regression";

export function plsPredictionSnapshot(analysisId: string, request: PlsPointPredictionRequest,
  response: PlsPointPredictionResponse, receivedAt: string,
  source: { modelId: string; responseColumnId: string }) {
  const ids = new Set(request.rows.map((row) => row.client_row_id));
  if (response === null || typeof response !== "object" || !Array.isArray(response.rows)
    || response.model_id !== source.modelId || response.response_column_id !== source.responseColumnId
    || request.expected_model_manifest_sha256 !== response.model_manifest_sha256
    || response.intervals_supported !== false || response.row_count !== request.rows.length
    || request.rows.length < 1 || request.rows.length !== response.rows.length
    || ids.size !== request.rows.length
    || new Set(response.rows.map((row) => row?.client_row_id)).size !== response.rows.length
    || response.rows.some((row) => row === null || typeof row !== "object"
      || !ids.has(row.client_row_id) || typeof row.predicted_value !== "number" || !Number.isFinite(row.predicted_value)
      || !Array.isArray(row.warnings) || !row.warnings.every((warning) => typeof warning === "string"))) {
    throw new Error("pls_prediction_snapshot_mismatch");
  }
  return {
    schema_version: 1 as const, artifact_kind: "pls_point_prediction_snapshot" as const,
    source_analysis_id: analysisId, client_received_at: receivedAt,
    prediction_recalculated_on_export: false as const,
    request: { ...request, rows: request.rows.map((row) => ({ ...row, values: { ...row.values } })) },
    response: { ...response, rows: response.rows.map((row) => ({ ...row, warnings: [...row.warnings] })) },
  };
}
