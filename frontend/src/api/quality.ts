import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes, type AttributeControlLimitSetsRouteParams } from "./routes";
import type { GageRrPreflightRequest, GageRrPreflightResponse } from "./types";
import type {
  AttributeControlLimitSetDeleteRequest,
  AttributeControlLimitSetDeleteResponse,
  AttributeControlLimitSetDeletionPreflightResponse,
  AttributeControlLimitSetCreateRequest,
  AttributeControlLimitSetListResponse,
  AttributeControlLimitSetResponse,
  AttributeControlMonitoringPreflightRequest,
  AttributeControlMonitoringPreflightResponse,
} from "./types";

export async function fetchAttributeControlLimitSetDeletionPreflight(
  limitSetId: string,
): Promise<AttributeControlLimitSetDeletionPreflightResponse> {
  const response = await fetchApi(
    apiRoutes.attributeControlLimitSetDeletionPreflight(limitSetId),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(
      await apiErrorCode(response, "attribute_control_limit_set_deletion_preflight_failed"),
    );
  }
  return (await response.json()) as AttributeControlLimitSetDeletionPreflightResponse;
}

export async function deleteAttributeControlLimitSet(
  limitSetId: string,
  request: AttributeControlLimitSetDeleteRequest,
): Promise<AttributeControlLimitSetDeleteResponse> {
  const response = await fetchApi(apiRoutes.attributeControlLimitSet(limitSetId), {
    method: "DELETE",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "attribute_control_limit_set_deletion_failed"));
  }
  return (await response.json()) as AttributeControlLimitSetDeleteResponse;
}

export async function createAttributeControlLimitSet(
  request: AttributeControlLimitSetCreateRequest,
): Promise<AttributeControlLimitSetResponse> {
  const response = await fetchApi(apiRoutes.attributeControlLimitSetsBase(), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "attribute_control_limit_set_create_failed"));
  }
  return (await response.json()) as AttributeControlLimitSetResponse;
}

export async function fetchAttributeControlLimitSet(
  limitSetId: string,
): Promise<AttributeControlLimitSetResponse> {
  const response = await fetchApi(apiRoutes.attributeControlLimitSet(limitSetId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "attribute_control_limit_set_fetch_failed"));
  }
  return (await response.json()) as AttributeControlLimitSetResponse;
}

export async function fetchAttributeControlLimitSets(
  params: AttributeControlLimitSetsRouteParams = {},
): Promise<AttributeControlLimitSetListResponse> {
  const response = await fetchApi(apiRoutes.attributeControlLimitSets(params), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "attribute_control_limit_set_list_failed"));
  }
  return (await response.json()) as AttributeControlLimitSetListResponse;
}

export async function fetchAttributeControlMonitoringPreflight(
  limitSetId: string,
  request: AttributeControlMonitoringPreflightRequest,
): Promise<AttributeControlMonitoringPreflightResponse> {
  const response = await fetchApi(apiRoutes.attributeControlMonitoringPreflight(limitSetId), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "attribute_control_monitoring_preflight_failed"));
  }
  return (await response.json()) as AttributeControlMonitoringPreflightResponse;
}

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
