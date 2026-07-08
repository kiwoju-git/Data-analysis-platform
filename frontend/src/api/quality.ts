import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { GageRrPreflightRequest, GageRrPreflightResponse } from "./types";

export async function fetchGageRrPreflight(
  request: GageRrPreflightRequest,
): Promise<GageRrPreflightResponse> {
  const response = await fetchApi(apiRoutes.gageRrPreflight(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "gage_rr_preflight_failed"));
  }

  return (await response.json()) as GageRrPreflightResponse;
}
