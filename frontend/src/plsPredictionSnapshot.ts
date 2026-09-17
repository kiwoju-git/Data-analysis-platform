import type { PlsPointPredictionRequest, PlsPointPredictionResponse } from "./api/types/regression";

export function plsPredictionSnapshot(analysisId: string, request: PlsPointPredictionRequest,
  response: PlsPointPredictionResponse, receivedAt: string) {
  if (request.expected_model_manifest_sha256 !== response.model_manifest_sha256 ||
    request.rows.length !== response.rows.length ||
    request.rows.some((row, index) => row.client_row_id !== response.rows[index].client_row_id)) {
    throw new Error("pls_prediction_snapshot_mismatch");
  }
  return {
    schema_version: 1, artifact_kind: "pls_point_prediction_snapshot",
    source_analysis_id: analysisId, client_received_at: receivedAt,
    prediction_recalculated_on_export: false,
    request, response,
  };
}
