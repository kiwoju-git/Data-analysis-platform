import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { AugmentationBatchResponse, AugmentationSelectionRequest, AugmentationSelectionResponse, CandidatePage, CandidateRevisionCreateRequestV2 } from "./types/boAugmentation";
import type { PlanningConfirmRequest } from "./types/boPlanning";
import type { ReportSourceDescriptor } from "./types/reports";

const route = (study: string, path: string) => `${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(study)}/${path}`;
async function request<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetchApi(url, { headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    ...(body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }) });
  if (!response.ok) throw await apiRequestError(response, "bayesian_augmentation_request_failed");
  return await response.json() as T;
}
export const createAugmentationCandidates = (study: string, body: CandidateRevisionCreateRequestV2) => request<CandidatePage>(route(study, "candidate-revisions"), body);
export const createAugmentation = (study: string, body: AugmentationSelectionRequest) => request<AugmentationSelectionResponse>(route(study, "augmentations"), body);
export const fetchAugmentation = (study: string, id: string) => request<AugmentationSelectionResponse>(route(study, `augmentations/${encodeURIComponent(id)}`));
export const confirmAugmentation = (study: string, id: string, body: PlanningConfirmRequest) => request<AugmentationBatchResponse>(route(study, `augmentations/${encodeURIComponent(id)}/confirm`), body);
export const fetchAugmentationBatch = (study: string, id: string) => request<AugmentationBatchResponse>(route(study, `augmentation-batches/${encodeURIComponent(id)}`));
export const fetchAugmentationReportSource = (study: string, id: string) => request<ReportSourceDescriptor>(route(study, `augmentation-batches/${encodeURIComponent(id)}/report-source`));
