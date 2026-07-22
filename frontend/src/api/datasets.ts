import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  DatasetParsingConfirmationRequest,
  DatasetProfileResponse,
  DatasetRowsPreviewResponse,
  DatasetSchemaResponse,
  DatasetSchemaUpdateRequest,
  DatasetUploadResponse,
  DatasetVersionCatalogResponse,
  DatasetVersionDeleteResponse,
  DatasetVersionDeletionPreflightResponse,
  DatasetVersionMetadataResponse,
  DatasetVersionMetadataUpdateRequest,
  DatasetVersionResponse,
  PastedDatasetRequest,
} from "./types";

export async function uploadDataset(file: File): Promise<DatasetUploadResponse> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetchApi(apiRoutes.datasets(), {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_upload_failed"));
  }

  return (await response.json()) as DatasetUploadResponse;
}

export async function createDatasetFromPastedText(
  request: PastedDatasetRequest,
): Promise<DatasetUploadResponse> {
  const response = await fetchApi(apiRoutes.datasetPaste(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_paste_failed"));
  }

  return (await response.json()) as DatasetUploadResponse;
}

export async function confirmDatasetParsing(
  datasetId: string,
  request: DatasetParsingConfirmationRequest,
): Promise<DatasetVersionResponse> {
  const response = await fetchApi(
    apiRoutes.datasetConfirmParsing(datasetId),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "parsing_confirmation_failed"));
  }

  return (await response.json()) as DatasetVersionResponse;
}

export async function fetchDatasetVersion(
  versionId: string,
): Promise<DatasetVersionResponse> {
  const response = await fetchApi(apiRoutes.datasetVersion(versionId), {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_version_fetch_failed"));
  }

  return (await response.json()) as DatasetVersionResponse;
}

export async function updateDatasetSchema(
  versionId: string,
  request: DatasetSchemaUpdateRequest,
): Promise<DatasetSchemaResponse> {
  const response = await fetchApi(
    apiRoutes.datasetVersionSchema(versionId),
    {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "schema_update_failed"));
  }

  return (await response.json()) as DatasetSchemaResponse;
}

export async function fetchRowsPreview(
  versionId: string,
  offset: number,
  limit: number,
): Promise<DatasetRowsPreviewResponse> {
  const response = await fetchApi(apiRoutes.datasetVersionRows(versionId, offset, limit), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "rows_preview_failed"));
  }

  return (await response.json()) as DatasetRowsPreviewResponse;
}

export async function fetchDatasetProfile(versionId: string): Promise<DatasetProfileResponse> {
  const response = await fetchApi(apiRoutes.datasetVersionProfile(versionId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_profile_failed"));
  }

  return (await response.json()) as DatasetProfileResponse;
}

export async function fetchDatasetVersions(
  limit: number,
  offset: number,
): Promise<DatasetVersionCatalogResponse> {
  const response = await fetchApi(apiRoutes.datasetVersions(limit, offset), {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_versions_fetch_failed"));
  }

  return (await response.json()) as DatasetVersionCatalogResponse;
}

export async function updateDatasetVersionMetadata(
  versionId: string,
  request: DatasetVersionMetadataUpdateRequest,
): Promise<DatasetVersionMetadataResponse> {
  const response = await fetchApi(apiRoutes.datasetVersionMetadata(versionId), {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_version_metadata_update_failed"));
  }
  return (await response.json()) as DatasetVersionMetadataResponse;
}

export async function fetchDatasetVersionDeletionPreflight(
  versionId: string,
): Promise<DatasetVersionDeletionPreflightResponse> {
  const response = await fetchApi(apiRoutes.datasetVersionDeletionPreflight(versionId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_version_deletion_preflight_failed"));
  }
  return (await response.json()) as DatasetVersionDeletionPreflightResponse;
}

export async function deleteDatasetVersion(
  preflight: DatasetVersionDeletionPreflightResponse,
): Promise<DatasetVersionDeleteResponse> {
  const response = await fetchApi(apiRoutes.datasetVersionDeletion(preflight.version_id), {
    method: "DELETE",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({
      confirmation_version_id: preflight.version_id,
      expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
    }),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_version_deletion_failed"));
  }
  return (await response.json()) as DatasetVersionDeleteResponse;
}
