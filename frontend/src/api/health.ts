import { fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { HealthResponse } from "./types";

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ready" &&
    candidate.service === "datalab-studio-api" &&
    typeof candidate.version === "string"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetchApi(apiRoutes.health(), {
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error("health_check_failed");
  }

  const payload: unknown = await response.json();
  if (!isHealthResponse(payload)) {
    throw new Error("invalid_health_response");
  }

  return payload;
}
