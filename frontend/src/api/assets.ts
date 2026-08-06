import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  WorkspaceAssetCatalogResponse,
  WorkspaceAssetFilters,
} from "./types";

export async function fetchWorkspaceAssets(
  filters: WorkspaceAssetFilters,
  offset = 0,
  limit = 50,
): Promise<WorkspaceAssetCatalogResponse> {
  const response = await fetchApi(apiRoutes.workspaceAssets(filters, offset, limit), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "workspace_asset_catalog_failed"));
  }
  return (await response.json()) as WorkspaceAssetCatalogResponse;
}
