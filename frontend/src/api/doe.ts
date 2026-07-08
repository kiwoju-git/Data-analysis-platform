import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  DoeDesignResponsesResponse,
  DoeDesignResponsesUpsertRequest,
  FactorialDesignCreateRequest,
  FactorialDesignResponse,
} from "./types";

export async function createFactorialDesign(
  request: FactorialDesignCreateRequest,
): Promise<FactorialDesignResponse> {
  const response = await fetchApi(apiRoutes.doeFactorialDesign(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_design_failed"));
  }

  return (await response.json()) as FactorialDesignResponse;
}

export async function fetchFactorialDesign(designId: string): Promise<FactorialDesignResponse> {
  const response = await fetchApi(apiRoutes.doeDesign(designId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_design_fetch_failed"));
  }

  return (await response.json()) as FactorialDesignResponse;
}

export async function saveFactorialDesignResponses(
  designId: string,
  request: DoeDesignResponsesUpsertRequest,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(apiRoutes.doeDesignResponses(designId), {
    method: "PUT",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_responses_failed"));
  }

  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function fetchFactorialDesignResponses(
  designId: string,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(apiRoutes.doeDesignResponses(designId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_responses_fetch_failed"));
  }

  return (await response.json()) as DoeDesignResponsesResponse;
}
