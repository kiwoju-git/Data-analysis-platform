import { apiRequestError, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { GraphPreviewRequest, GraphPreviewResponse } from "./types";

export async function createGraphPreview(
  request: GraphPreviewRequest,
): Promise<GraphPreviewResponse> {
  const response = await fetchApi(apiRoutes.visualizationPreview(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw await apiRequestError(response, "graph_preview_failed");
  }
  return (await response.json()) as GraphPreviewResponse;
}
