import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  RegressionPredictionPreflightRequest,
  RegressionPredictionPreflightResponse,
  RegressionPredictionRequest,
  RegressionPredictionResponse,
} from "./types";

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
