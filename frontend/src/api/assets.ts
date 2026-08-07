import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  EditableWorkspaceAssetType,
  WorkspaceAssetCatalogResponse,
  WorkspaceAssetFilters,
  WorkspaceAssetMetadataResponse,
  WorkspaceAssetMetadataUpdateRequest,
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

export async function updateWorkspaceAssetMetadata(
  assetType: EditableWorkspaceAssetType,
  assetId: string,
  body: WorkspaceAssetMetadataUpdateRequest,
): Promise<WorkspaceAssetMetadataResponse> {
  const response = await fetchApi(apiRoutes.workspaceAssetMetadata(assetType, assetId), {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "workspace_asset_metadata_update_failed"));
  }
  return (await response.json()) as WorkspaceAssetMetadataResponse;
}
