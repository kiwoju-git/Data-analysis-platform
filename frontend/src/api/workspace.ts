import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { WorkspaceSummaryResponse } from "./types";

export async function fetchWorkspaceSummary(): Promise<WorkspaceSummaryResponse> {
  const response = await fetchApi(apiRoutes.workspaceSummary(), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "workspace_summary_fetch_failed"));
  }
  return (await response.json()) as WorkspaceSummaryResponse;
}
