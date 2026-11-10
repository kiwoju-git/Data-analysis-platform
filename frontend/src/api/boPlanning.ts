import { apiRequestError, fetchApi, getApiBaseUrl } from "./client";
import type { CandidatePage, CandidateRevisionCreateRequest, CandidateRevisionSummary, PlanningBatchResponse,
  PlanningConfirmRequest, PlanningEvaluationRequest, PlanningEvaluationResponse, PlanningModelCreateRequest,
  PlanningModelDetail, PlanningModelSummary, PlanningSelectionCreateRequest, PlanningSelectionResponse, PlanningSelectionSummary } from "./types/boPlanning";
import type { ReportSourceDescriptor } from "./types/reports";

const route = (studyId: string, path: string) => `${getApiBaseUrl()}/api/v1/bayesian-studies/${encodeURIComponent(studyId)}/${path}`;
async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetchApi(path, { headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
    ...(body === undefined ? {} : { method: "POST", body: JSON.stringify(body) }) });
  if (!response.ok) throw await apiRequestError(response, "bayesian_planning_request_failed");
  return await response.json() as T;
}
export const createPlanningModel = (studyId: string, body: PlanningModelCreateRequest) => request<PlanningModelDetail>(route(studyId, "planning-models"), body);
export const listPlanningModels = (studyId: string) => request<{ items: PlanningModelSummary[] }>(route(studyId, "planning-models"));
export const fetchPlanningModel = (studyId: string, id: string) => request<PlanningModelDetail>(route(studyId, `planning-models/${encodeURIComponent(id)}`));
export const evaluatePlanningModel = (studyId: string, id: string, body: PlanningEvaluationRequest) => request<PlanningEvaluationResponse>(route(studyId, `planning-models/${encodeURIComponent(id)}/evaluate`), body);
export const listCandidateSets = (studyId: string) => request<{ items: CandidateRevisionSummary[] }>(route(studyId, "candidate-sets"));
export const createCandidateRevision = (studyId: string, body: CandidateRevisionCreateRequest) => request<CandidatePage>(route(studyId, "candidate-revisions"), body);
export const fetchCandidatePage = (studyId: string, id: string, offset = 0, limit = 50) => request<CandidatePage>(route(studyId, `candidate-revisions/${encodeURIComponent(id)}?offset=${offset}&limit=${limit}`));
export const createPlanningSelection = (studyId: string, body: PlanningSelectionCreateRequest) => request<PlanningSelectionResponse>(route(studyId, "planning-selections"), body);
export const listPlanningSelections = (studyId: string) => request<{ items: PlanningSelectionSummary[] }>(route(studyId, "planning-selections"));
export const fetchPlanningSelection = (studyId: string, id: string) => request<PlanningSelectionResponse>(route(studyId, `planning-selections/${encodeURIComponent(id)}`));
export const confirmPlanningSelection = (studyId: string, id: string, body: PlanningConfirmRequest) => request<PlanningBatchResponse>(route(studyId, `planning-selections/${encodeURIComponent(id)}/confirm`), body);
export const fetchPlanningBatch = (studyId: string, id: string) => request<PlanningBatchResponse>(route(studyId, `planning-batches/${encodeURIComponent(id)}`));
export const fetchPlanningBatchReportSource = (studyId: string, id: string) => request<ReportSourceDescriptor>(route(studyId, `planning-batches/${encodeURIComponent(id)}/report-source`));
