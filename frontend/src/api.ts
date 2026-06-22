export interface HealthResponse {
  status: "ready";
  service: "datalab-studio-api";
  version: string;
}

export function getApiBaseUrl(): string {
  const configuredBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl;
  }
  return "http://127.0.0.1:8000";
}

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
  const response = await fetch(`${getApiBaseUrl()}/api/v1/health`, {
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
