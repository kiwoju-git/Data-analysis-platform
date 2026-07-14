import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  DoeDesignResponsesResponse,
  DoeDesignResponsesUpsertRequest,
  DoeFactorialAnalysisCreateRequest,
  DoeFactorialAnalysisResponse,
  DoeResponseSurfaceAnalysisCreateRequest,
  DoeResponseSurfaceAnalysisResponse,
  FactorialDesignCreateRequest,
  FactorialDesignResponse,
  ResponseSurfaceDesignCreateRequest,
  ResponseSurfaceDesignResponse,
  ResponseOptimizerCreateRequest,
  ResponseOptimizerResponse,
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

export async function createFactorialAnalysis(
  designId: string,
  request: DoeFactorialAnalysisCreateRequest,
): Promise<DoeFactorialAnalysisResponse> {
  const response = await fetchApi(apiRoutes.doeDesignAnalyses(designId), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_analysis_failed"));
  }

  return (await response.json()) as DoeFactorialAnalysisResponse;
}

export async function fetchFactorialAnalysis(
  designId: string,
  analysisId: string,
): Promise<DoeFactorialAnalysisResponse> {
  const response = await fetchApi(apiRoutes.doeDesignAnalysis(designId, analysisId), {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_factorial_analysis_fetch_failed"));
  }

  return (await response.json()) as DoeFactorialAnalysisResponse;
}

export async function createResponseSurfaceDesign(
  request: ResponseSurfaceDesignCreateRequest,
): Promise<ResponseSurfaceDesignResponse> {
  const response = await fetchApi(apiRoutes.doeResponseSurfaceDesign(), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_rsm_design_failed"));
  }
  return (await response.json()) as ResponseSurfaceDesignResponse;
}

export async function fetchResponseSurfaceDesign(
  designId: string,
): Promise<ResponseSurfaceDesignResponse> {
  const response = await fetchApi(apiRoutes.doeResponseSurfaceDesignById(designId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_rsm_design_fetch_failed"));
  }
  return (await response.json()) as ResponseSurfaceDesignResponse;
}

export async function saveResponseSurfaceResponses(
  designId: string,
  request: DoeDesignResponsesUpsertRequest,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(apiRoutes.doeResponseSurfaceResponses(designId), {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_rsm_responses_failed"));
  }
  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function createResponseSurfaceAnalysis(
  designId: string,
  request: DoeResponseSurfaceAnalysisCreateRequest,
): Promise<DoeResponseSurfaceAnalysisResponse> {
  const response = await fetchApi(apiRoutes.doeResponseSurfaceAnalyses(designId), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_rsm_analysis_failed"));
  }
  return (await response.json()) as DoeResponseSurfaceAnalysisResponse;
}

export async function fetchResponseSurfaceAnalysis(
  designId: string,
  analysisId: string,
): Promise<DoeResponseSurfaceAnalysisResponse> {
  const response = await fetchApi(
    apiRoutes.doeResponseSurfaceAnalysis(designId, analysisId),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_rsm_analysis_fetch_failed"));
  }
  return (await response.json()) as DoeResponseSurfaceAnalysisResponse;
}

export async function createResponseOptimizer(
  designId: string,
  request: ResponseOptimizerCreateRequest,
): Promise<ResponseOptimizerResponse> {
  const response = await fetchApi(apiRoutes.doeResponseSurfaceOptimizations(designId), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "response_optimizer_failed"));
  }
  return (await response.json()) as ResponseOptimizerResponse;
}

export async function fetchResponseOptimizer(
  designId: string,
  optimizationId: string,
): Promise<ResponseOptimizerResponse> {
  const response = await fetchApi(
    apiRoutes.doeResponseSurfaceOptimization(designId, optimizationId),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "response_optimizer_fetch_failed"));
  }
  return (await response.json()) as ResponseOptimizerResponse;
}
