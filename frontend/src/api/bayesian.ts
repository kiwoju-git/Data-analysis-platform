import { apiErrorCode, fetchApi } from "./client";
import { apiRoutes } from "./routes";
import type {
  BayesianHistoryListResponse,
  BayesianHistoryRevisionResponse,
  BayesianObservationCreateRequest,
  BayesianRecommendationCreateRequest,
  BayesianRecommendationListResponse,
  BayesianRecommendationResponse,
  BayesianStudyCreateRequest,
  BayesianStudyListResponse,
  BayesianStudyResponse,
  BayesianTrialListResponse,
  BayesianTrialTransitionResponse,
} from "./types";

export async function createBayesianStudy(
  request: BayesianStudyCreateRequest,
): Promise<BayesianStudyResponse> {
  const response = await fetchApi(apiRoutes.bayesianStudies(), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_study_create_failed"));
  }
  return (await response.json()) as BayesianStudyResponse;
}

export async function createBayesianRecommendation(
  studyId: string,
  request: BayesianRecommendationCreateRequest,
): Promise<BayesianRecommendationResponse> {
  const response = await fetchApi(apiRoutes.bayesianRecommendations(studyId), {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_recommendation_failed"));
  }
  return (await response.json()) as BayesianRecommendationResponse;
}

export async function fetchBayesianRecommendations(
  studyId: string,
  offset = 0,
  limit = 20,
): Promise<BayesianRecommendationListResponse> {
  const response = await fetchApi(
    apiRoutes.bayesianRecommendations(studyId, offset, limit),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_recommendation_list_failed"));
  }
  return (await response.json()) as BayesianRecommendationListResponse;
}

export async function fetchBayesianRecommendation(
  studyId: string,
  recommendationId: string,
): Promise<BayesianRecommendationResponse> {
  const response = await fetchApi(apiRoutes.bayesianRecommendation(studyId, recommendationId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_recommendation_fetch_failed"));
  }
  return (await response.json()) as BayesianRecommendationResponse;
}

export async function fetchBayesianStudies(
  offset = 0,
  limit = 20,
): Promise<BayesianStudyListResponse> {
  const response = await fetchApi(apiRoutes.bayesianStudies(offset, limit), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_study_list_failed"));
  }
  return (await response.json()) as BayesianStudyListResponse;
}

export async function fetchBayesianStudy(studyId: string): Promise<BayesianStudyResponse> {
  const response = await fetchApi(apiRoutes.bayesianStudy(studyId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_study_fetch_failed"));
  }
  return (await response.json()) as BayesianStudyResponse;
}

export async function fetchBayesianTrials(
  studyId: string,
  offset = 0,
  limit = 50,
): Promise<BayesianTrialListResponse> {
  const response = await fetchApi(apiRoutes.bayesianTrials(studyId, offset, limit), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_trial_list_failed"));
  }
  return (await response.json()) as BayesianTrialListResponse;
}

export async function recordBayesianObservation(
  studyId: string,
  trialId: string,
  request: BayesianObservationCreateRequest,
): Promise<BayesianTrialTransitionResponse> {
  const response = await fetchApi(apiRoutes.bayesianTrialObservation(studyId, trialId), {
    method: "PUT",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_observation_failed"));
  }
  return (await response.json()) as BayesianTrialTransitionResponse;
}

export async function abandonBayesianTrial(
  studyId: string,
  trialId: string,
): Promise<BayesianTrialTransitionResponse> {
  const response = await fetchApi(apiRoutes.bayesianTrialAbandon(studyId, trialId), {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_trial_abandon_failed"));
  }
  return (await response.json()) as BayesianTrialTransitionResponse;
}

export async function fetchBayesianHistory(
  studyId: string,
  offset = 0,
  limit = 50,
): Promise<BayesianHistoryListResponse> {
  const response = await fetchApi(apiRoutes.bayesianHistory(studyId, offset, limit), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_history_list_failed"));
  }
  return (await response.json()) as BayesianHistoryListResponse;
}

export async function fetchBayesianHistoryRevision(
  studyId: string,
  historyRevisionId: string,
): Promise<BayesianHistoryRevisionResponse> {
  const response = await fetchApi(
    apiRoutes.bayesianHistoryRevision(studyId, historyRevisionId),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "bayesian_history_fetch_failed"));
  }
  return (await response.json()) as BayesianHistoryRevisionResponse;
}
