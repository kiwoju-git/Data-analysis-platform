import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { DesirabilityBatch, DesirabilityReview, DesirabilityReviewRequest } from "./types/bayesianDesirability";
import type { CurvePreviewRequest, CurvePreviewResponse } from "./types/boCurvePreview";

async function jsonResponse<T>(path: string, fallback: string, body?: unknown): Promise<T> {
  const response = await fetchApi(path, {
    headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    ...(body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }),
  });
  if (!response.ok) throw new Error(await apiErrorCode(response, fallback));
  return await response.json() as T;
}
export const createDesirabilityReview = (studyId: string, request: DesirabilityReviewRequest) =>
  jsonResponse<DesirabilityReview>(apiRoutes.bayesianDesirabilityReviews(studyId), "bayesian_recommendation_review_failed", request);
export const confirmDesirabilityReview = (studyId: string, reviewId: string, configHash: string) =>
  jsonResponse<DesirabilityBatch>(apiRoutes.bayesianDesirabilityReviewConfirm(studyId, reviewId), "bayesian_recommendation_confirm_failed", { expected_config_sha256: configHash });
export const fetchDesirabilityBatch = (studyId: string, batchId: string) =>
  jsonResponse<DesirabilityBatch>(apiRoutes.bayesianDesirabilityRecommendation(studyId, batchId), "bayesian_recommendation_batch_fetch_failed");
export const fetchLatestDesirabilityBatch = (studyId: string) =>
  jsonResponse<{ item: DesirabilityBatch | null }>(apiRoutes.bayesianLatestDesirabilityRecommendation(studyId), "bayesian_recommendation_batch_latest_failed");
export const previewBayesianTargetCurve = (request: CurvePreviewRequest) =>
  jsonResponse<CurvePreviewResponse>(apiRoutes.bayesianTargetCurvePreview(), "bayesian_curve_preview_failed", request);
