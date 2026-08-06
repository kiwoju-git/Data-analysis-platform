import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  DoeDesignResponsesResponse,
  DoeDesignResponsesUpsertRequest,
  DoeDesignDeleteResponse,
  DoeDesignDeletionPreflightResponse,
  DoeFactorialAnalysisCreateRequest,
  DoeFactorialAnalysisResponse,
  DoeResponseSurfaceAnalysisCreateRequest,
  DoeResponseSurfaceAnalysisCatalogResponse,
  DoeResponseSurfaceAnalysisResponse,
  DoeResponseRevisionCreateRequest,
  DoeResponseRevisionHistoryResponse,
  DoeResponseRevisionResponse,
  FactorialDesignCreateRequest,
  FactorialDesignResponse,
  GeneralFactorialAnalysisResponse,
  GeneralFactorialDesignCreateRequest,
  GeneralFactorialDesignResponse,
  LatinHypercubeDesignCreateRequest,
  LatinHypercubeDesignResponse,
  ResponseSurfaceDesignCreateRequest,
  ResponseSurfaceDesignResponse,
  ResponseOptimizerCreateRequest,
  ResponseOptimizerResponse,
} from "./types";

export async function fetchDoeDesignDeletionPreflight(
  designId: string,
): Promise<DoeDesignDeletionPreflightResponse> {
  const response = await fetchApi(apiRoutes.doeDesignDeletionPreflight(designId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_design_deletion_preflight_failed"));
  }
  return (await response.json()) as DoeDesignDeletionPreflightResponse;
}

export async function deleteDoeDesign(
  designId: string,
  deletionManifestSha256: string,
): Promise<DoeDesignDeleteResponse> {
  const response = await fetchApi(apiRoutes.doeDesignDelete(designId), {
    method: "DELETE",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({
      confirmation_design_id: designId,
      expected_deletion_manifest_sha256: deletionManifestSha256,
    }),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_design_delete_failed"));
  }
  return (await response.json()) as DoeDesignDeleteResponse;
}

export async function createGeneralFactorialDesign(
  request: GeneralFactorialDesignCreateRequest,
): Promise<GeneralFactorialDesignResponse> {
  const response = await fetchApi(apiRoutes.doeGeneralFactorialDesign(), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_general_factorial_design_failed"));
  }
  return (await response.json()) as GeneralFactorialDesignResponse;
}

export async function fetchGeneralFactorialDesign(
  designId: string,
): Promise<GeneralFactorialDesignResponse> {
  const response = await fetchApi(apiRoutes.doeGeneralFactorialDesignById(designId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_general_factorial_design_fetch_failed"));
  }
  return (await response.json()) as GeneralFactorialDesignResponse;
}

export async function fetchGeneralFactorialResponses(
  designId: string,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(apiRoutes.doeGeneralFactorialResponses(designId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_general_factorial_responses_fetch_failed"));
  }
  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function saveGeneralFactorialResponses(
  designId: string,
  request: DoeDesignResponsesUpsertRequest,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(apiRoutes.doeGeneralFactorialResponses(designId), {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_general_factorial_responses_failed"));
  }
  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function createGeneralFactorialAnalysis(
  designId: string,
  request: { response_name: string; max_interaction_order: number },
): Promise<GeneralFactorialAnalysisResponse> {
  const response = await fetchApi(apiRoutes.doeGeneralFactorialAnalyses(designId), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_general_factorial_analysis_failed"));
  }
  return (await response.json()) as GeneralFactorialAnalysisResponse;
}

export async function createLatinHypercubeDesign(
  request: LatinHypercubeDesignCreateRequest,
): Promise<LatinHypercubeDesignResponse> {
  const response = await fetchApi(apiRoutes.doeLatinHypercubeDesign(), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "lhs_design_failed"));
  }
  return (await response.json()) as LatinHypercubeDesignResponse;
}

export async function saveLatinHypercubeResponses(
  designId: string,
  request: DoeDesignResponsesUpsertRequest,
): Promise<DoeDesignResponsesResponse> {
  const response = await fetchApi(apiRoutes.doeLatinHypercubeResponses(designId), {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "lhs_responses_failed"));
  }
  return (await response.json()) as DoeDesignResponsesResponse;
}

export async function fetchResponseSurfaceAnalysisCatalog(
  offset = 0,
  limit = 20,
): Promise<DoeResponseSurfaceAnalysisCatalogResponse> {
  const response = await fetchApi(
    apiRoutes.doeResponseSurfaceAnalysisCatalog(offset, limit),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_rsm_analysis_catalog_failed"));
  }
  return (await response.json()) as DoeResponseSurfaceAnalysisCatalogResponse;
}

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

export async function createDoeResponseRevision(
  designId: string,
  request: DoeResponseRevisionCreateRequest,
): Promise<DoeResponseRevisionResponse> {
  const response = await fetchApi(apiRoutes.doeResponseRevisions(designId), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_response_revision_failed"));
  }
  return (await response.json()) as DoeResponseRevisionResponse;
}

export async function fetchDoeResponseRevisions(
  designId: string,
  responseName: string,
  offset = 0,
  limit = 20,
): Promise<DoeResponseRevisionHistoryResponse> {
  const response = await fetchApi(
    apiRoutes.doeResponseRevisions(designId, responseName, offset, limit),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_response_revision_history_failed"));
  }
  return (await response.json()) as DoeResponseRevisionHistoryResponse;
}

export async function fetchDoeResponseRevision(
  designId: string,
  responseRevisionId: string,
): Promise<DoeResponseRevisionResponse> {
  const response = await fetchApi(
    apiRoutes.doeResponseRevision(designId, responseRevisionId),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_response_revision_fetch_failed"));
  }
  return (await response.json()) as DoeResponseRevisionResponse;
}

export async function abandonDoeResponseRevision(
  designId: string,
  responseRevisionId: string,
): Promise<DoeResponseRevisionResponse> {
  const response = await fetchApi(
    apiRoutes.doeResponseRevisionAbandon(designId, responseRevisionId),
    { method: "POST", headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "doe_response_revision_abandon_failed"));
  }
  return (await response.json()) as DoeResponseRevisionResponse;
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
