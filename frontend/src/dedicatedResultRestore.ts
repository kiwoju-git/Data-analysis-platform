import type {
  AnalysisResultEnvelope,
  DoeResponseSurfaceAnalysisResponse,
  RegressionPredictionResponse,
  ResponseOptimizerResponse,
  ResponseSurfaceDesignResponse,
} from "./api";

export function restoredPredictionForSelection(
  envelope: AnalysisResultEnvelope,
  predictionId: string,
  modelId: string | null,
  targetDatasetVersionId: string | null,
): RegressionPredictionResponse | null {
  const prediction = predictionResult(envelope.result);
  if (
    modelId === null ||
    targetDatasetVersionId === null ||
    envelope.method_id !== "regression.predict" ||
    envelope.analysis_id !== predictionId ||
    prediction === null ||
    prediction.prediction_id !== predictionId ||
    prediction.model_id !== modelId ||
    prediction.target_dataset_version_id !== targetDatasetVersionId
  ) {
    return null;
  }
  return prediction;
}

export function restoredOptimizationMatchesSelection(
  optimization: ResponseOptimizerResponse,
  optimizationId: string | null,
  design: ResponseSurfaceDesignResponse,
  analysis: DoeResponseSurfaceAnalysisResponse,
): boolean {
  return optimizationId !== null &&
    optimization.optimization_id === optimizationId &&
    optimization.design_id === design.design_id &&
    optimization.design_version_id === design.design_version_id &&
    optimization.source_analysis_ids.length === 1 &&
    optimization.source_analysis_ids[0] === analysis.analysis_id;
}

function predictionResult(value: unknown): RegressionPredictionResponse | null {
  if (value === null || typeof value !== "object") return null;
  const candidate = value as Partial<RegressionPredictionResponse>;
  return typeof candidate.prediction_id === "string" &&
    typeof candidate.model_id === "string" &&
    typeof candidate.analysis_id === "string" &&
    typeof candidate.source_dataset_version_id === "string" &&
    typeof candidate.target_dataset_version_id === "string" &&
    Array.isArray(candidate.rows)
    ? (candidate as RegressionPredictionResponse)
    : null;
}
