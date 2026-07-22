import { apiErrorCode, apiRequestError, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  RegressionModelDeleteRequest,
  RegressionModelDeleteResponse,
  RegressionModelDeletionPreflightResponse,
  RegressionModelManifestResponse,
  RegressionModelCatalogResponse,
  RegressionModelMetadataResponse,
  RegressionModelMetadataUpdateRequest,
  RegressionPredictionPreflightRequest,
  RegressionPredictionPreflightResponse,
  RegressionPredictionRequest,
  RegressionPredictionResponse,
  RegressionPredictionRowsPageResponse,
  RegressionPredictionCsvExportResponse,
} from "./types";

export async function fetchRegressionModels(
  offset = 0,
  limit = 20,
): Promise<RegressionModelCatalogResponse> {
  const response = await fetchApi(apiRoutes.regressionModels(offset, limit), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "regression_model_catalog_failed"));
  }
  return (await response.json()) as RegressionModelCatalogResponse;
}

export async function fetchRegressionModelManifest(
  modelId: string,
): Promise<RegressionModelManifestResponse> {
  const response = await fetchApi(apiRoutes.regressionModel(modelId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "regression_model_availability_failed"));
  }
  return (await response.json()) as RegressionModelManifestResponse;
}

export async function updateRegressionModelMetadata(
  modelId: string,
  request: RegressionModelMetadataUpdateRequest,
): Promise<RegressionModelMetadataResponse> {
  const response = await fetchApi(apiRoutes.regressionModelMetadata(modelId), {
    method: "PATCH",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw await apiRequestError(response, "regression_model_metadata_update_failed");
  }
  return (await response.json()) as RegressionModelMetadataResponse;
}

export async function fetchRegressionModelDeletionPreflight(
  modelId: string,
): Promise<RegressionModelDeletionPreflightResponse> {
  const response = await fetchApi(apiRoutes.regressionModelDeletionPreflight(modelId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw await apiRequestError(response, "regression_model_deletion_preflight_failed");
  }
  return (await response.json()) as RegressionModelDeletionPreflightResponse;
}

export async function deleteRegressionModel(
  modelId: string,
  request: RegressionModelDeleteRequest,
): Promise<RegressionModelDeleteResponse> {
  const response = await fetchApi(apiRoutes.regressionModel(modelId), {
    method: "DELETE",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw await apiRequestError(response, "regression_model_deletion_failed");
  }
  return (await response.json()) as RegressionModelDeleteResponse;
}

export async function fetchRegressionPredictionPreflight(
  modelId: string,
  request: RegressionPredictionPreflightRequest,
): Promise<RegressionPredictionPreflightResponse> {
  const response = await fetchApi(
    apiRoutes.regressionPredictionPreflight(modelId),
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
    throw new Error(await apiErrorCode(response, "regression_prediction_preflight_failed"));
  }

  return (await response.json()) as RegressionPredictionPreflightResponse;
}

export async function fetchRegressionPredictions(
  modelId: string,
  request: RegressionPredictionRequest,
): Promise<RegressionPredictionResponse> {
  const response = await fetchApi(
    apiRoutes.regressionPredictions(modelId),
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
    throw new Error(await apiErrorCode(response, "regression_prediction_failed"));
  }

  return (await response.json()) as RegressionPredictionResponse;
}

export async function fetchRegressionPredictionRows(
  predictionId: string,
  limit: number,
  offset: number,
): Promise<RegressionPredictionRowsPageResponse> {
  const response = await fetchApi(
    apiRoutes.regressionPredictionRows(predictionId, limit, offset),
    {
      headers: { Accept: "application/json" },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "regression_prediction_rows_failed"));
  }

  return (await response.json()) as RegressionPredictionRowsPageResponse;
}

export async function createRegressionPredictionCsvExport(
  predictionId: string,
): Promise<RegressionPredictionCsvExportResponse> {
  const response = await fetchApi(apiRoutes.regressionPredictionCsvExport(predictionId), {
    method: "POST",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "regression_prediction_csv_export_failed"));
  }

  return (await response.json()) as RegressionPredictionCsvExportResponse;
}
