import { apiRequestError, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type { HealthResponse, RuntimeInfoResponse } from "./types";

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

function isRuntimeInfoResponse(value: unknown): value is RuntimeInfoResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  if (
    candidate.service !== "datalab-studio-api" ||
    typeof candidate.app_version !== "string" ||
    typeof candidate.api_contract_version !== "number" ||
    typeof candidate.metadata_schema_version !== "number" ||
    typeof candidate.build_commit !== "string" ||
    typeof candidate.capabilities !== "object" ||
    candidate.capabilities === null
  ) {
    return false;
  }
  return Object.values(candidate.capabilities as Record<string, unknown>).every(
    (capability) => typeof capability === "boolean",
  );
}

export async function fetchRuntimeInfo(signal?: AbortSignal): Promise<RuntimeInfoResponse> {
  const response = await fetchApi(apiRoutes.runtimeInfo(), {
    // The response is already marked no-store by the backend. A Cache-Control
    // request header would turn this cross-origin GET into a CORS preflight.
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw await apiRequestError(response, "runtime_info_failed");
  }
  const payload: unknown = await response.json();
  if (!isRuntimeInfoResponse(payload)) {
    throw new Error("runtime_info_invalid");
  }
  return payload;
}
