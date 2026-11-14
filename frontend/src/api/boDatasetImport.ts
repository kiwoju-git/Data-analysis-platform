import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { AnyBayesianStudyResponse } from "./types/boMixed";
import type { DatasetImportCreateRequest, DatasetImportPreflightResponse, DatasetImportRequest } from "./types/boDatasetImport";
import type { MixtureDatasetCreateRequest, MixtureDatasetImportRequest, MixtureStudy } from "./boMixture";

async function post<T>(path: string, body: DatasetImportRequest | DatasetImportCreateRequest | MixtureDatasetImportRequest | MixtureDatasetCreateRequest, signal?: AbortSignal): Promise<T> {
  const response = await fetchApi(`${getApiBaseUrl()}/api/v1/bayesian-studies/${path}`, {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body), signal,
  });
  if (!response.ok) throw await apiRequestError(response, "bayesian_import_failed");
  return await response.json() as T;
}
export const preflightDatasetImport = (body: DatasetImportRequest, signal?: AbortSignal) => post<DatasetImportPreflightResponse>("import-preflight", body, signal);
export const createDatasetStudy = (body: DatasetImportCreateRequest) => post<AnyBayesianStudyResponse>("from-dataset", body);
export const preflightMixtureDatasetImport = (body: MixtureDatasetImportRequest, signal?: AbortSignal) => post<Omit<DatasetImportPreflightResponse, "schema_version"> & { schema_version: 2 }>("import-preflight", body, signal);
export const createMixtureDatasetStudy = (body: MixtureDatasetCreateRequest) => post<MixtureStudy>("from-dataset", body);
