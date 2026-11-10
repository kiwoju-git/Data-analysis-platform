import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { BayesianReplicateCreateRequest, BayesianStudyCloseRequest, BayesianTrialAbandonRequest } from "./types/bayesian";
import type { MixedBatchResponse, MixedCandidateCreateRequest, MixedCandidatePage, MixedCandidateSummary, MixedEvaluationRequest, MixedEvaluationResponse,
  MixedModelCreateRequest, MixedModelDetail, MixedModelSummary, MixedObservationBatchRequest, MixedObservationBatchResponse,
  MixedReplicateCreateResponse, MixedSelectionRequest, MixedSelectionResponse, MixedSelectionSummary, MixedStudyCloseResponse,
  MixedStudyCreateRequest, MixedStudyResponse, MixedTrialTransitionResponse } from "./types/boMixed";
import type { PlanningConfirmRequest } from "./types/boPlanning";
import type { ReportSourceDescriptor } from "./types/reports";

const route = (study: string, path = "") => `${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(study)}${path ? `/${path}` : ""}`;
async function request<T>(url: string, body?: unknown, method: "POST" | "PUT" = "POST"): Promise<T> {
  const response = await fetchApi(url, { headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    ...(body === undefined ? {} : { method, body: JSON.stringify(body) }) });
  if (!response.ok) throw await apiRequestError(response, "bayesian_mixed_request_failed");
  return await response.json() as T;
}
export const createMixedStudy = (body: MixedStudyCreateRequest) => request<MixedStudyResponse>(`${getApiBaseUrl()}/api/v1/bayesian-studies/mixed`, body);
export const fetchMixedStudy = (study: string) => request<MixedStudyResponse>(route(study));
export const recordMixedObservations = (study: string, body: MixedObservationBatchRequest) => request<MixedObservationBatchResponse>(route(study, "observations/batch"), body, "PUT");
export const createMixedReplicates = (study: string, trial: string, body: BayesianReplicateCreateRequest) => request<MixedReplicateCreateResponse>(route(study, `trials/${encodeURIComponent(trial)}/replicates`), body);
export const abandonMixedTrial = (study: string, trial: string, body: BayesianTrialAbandonRequest) => request<MixedTrialTransitionResponse>(route(study, `trials/${encodeURIComponent(trial)}/abandon`), body);
export const closeMixedStudy = (study: string, body: BayesianStudyCloseRequest) => request<MixedStudyCloseResponse>(route(study, "close"), body);
export const createMixedModel = (study: string, body: MixedModelCreateRequest) => request<MixedModelDetail>(route(study, "mixed-planning-models"), body);
export const listMixedModels = (study: string) => request<{ items: MixedModelSummary[] }>(route(study, "mixed-planning-models"));
export const fetchMixedModel = (study: string, id: string) => request<MixedModelDetail>(route(study, `mixed-planning-models/${encodeURIComponent(id)}`));
export const evaluateMixedModel = (study: string, id: string, body: MixedEvaluationRequest) => request<MixedEvaluationResponse>(route(study, `mixed-planning-models/${encodeURIComponent(id)}/evaluate`), body);
export const createMixedCandidateRevision = (study: string, body: MixedCandidateCreateRequest) => request<MixedCandidatePage>(route(study, "mixed-candidate-revisions"), body);
export const listMixedCandidateSets = (study: string) => request<{ items: MixedCandidateSummary[] }>(route(study, "mixed-candidate-sets"));
export const fetchMixedCandidatePage = (study: string, id: string, offset = 0, limit = 50) => request<MixedCandidatePage>(route(study, `mixed-candidate-revisions/${encodeURIComponent(id)}?offset=${offset}&limit=${limit}`));
export const createMixedSelection = (study: string, body: MixedSelectionRequest) => request<MixedSelectionResponse>(route(study, "mixed-selections"), body);
export const listMixedSelections = (study: string) => request<{ items: MixedSelectionSummary[] }>(route(study, "mixed-selections"));
export const fetchMixedSelection = (study: string, id: string) => request<MixedSelectionResponse>(route(study, `mixed-selections/${encodeURIComponent(id)}`));
export const confirmMixedSelection = (study: string, id: string, body: PlanningConfirmRequest) => request<MixedBatchResponse>(route(study, `mixed-selections/${encodeURIComponent(id)}/confirm`), body);
export const fetchMixedBatch = (study: string, id: string) => request<MixedBatchResponse>(route(study, `mixed-planning-batches/${encodeURIComponent(id)}`));
export const fetchMixedBatchReportSource = (study: string, id: string) => request<ReportSourceDescriptor>(route(study, `mixed-planning-batches/${encodeURIComponent(id)}/report-source`));
