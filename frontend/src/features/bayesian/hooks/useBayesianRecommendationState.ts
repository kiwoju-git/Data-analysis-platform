import { useCallback, useEffect, useRef, useState } from "react";

import {
  createBayesianRecommendation,
  fetchBayesianRecommendation,
  fetchLatestBayesianRecommendation,
  type BayesianRecommendationResponse,
  type BayesianStudyResponse,
} from "../../../api";
import { bayesianRecommendationBudgetBlocker } from "../../../bayesianStudyDraft";
import { createLatestRequestGuard } from "../../../latestRequest";
import {
  bayesianErrorCode,
  defaultBayesianSearch,
} from "../bayesianDisplay";

export function useBayesianRecommendationState({
  selectedStudyId,
  requestedRecommendationId,
  onRecommendationSelected,
}: {
  selectedStudyId: string | null;
  requestedRecommendationId: string | null;
  onRecommendationSelected: (recommendationId: string | null) => void;
}) {
  const [recommendation, setRecommendation] =
    useState<BayesianRecommendationResponse | null>(null);
  const [totalTrialBudget, setTotalTrialBudget] = useState(
    String(defaultBayesianSearch.total_trial_budget),
  );
  const [isRestoring, setIsRestoring] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const restoreGuard = useRef(createLatestRequestGuard()).current;
  const createGuard = useRef(createLatestRequestGuard()).current;

  const loadRecommendation = useCallback(
    async (
      studyId: string,
      recommendationId: string | null,
    ): Promise<BayesianRecommendationResponse | null> => {
      const request = restoreGuard.begin();
      setIsRestoring(true);
      setError(null);
      try {
        const restored =
          recommendationId === null
            ? (await fetchLatestBayesianRecommendation(studyId)).item
            : await fetchBayesianRecommendation(studyId, recommendationId);
        if (!restoreGuard.isCurrent(request)) return null;
        if (restored !== null && restored.study_id !== studyId) {
          setRecommendation(null);
          setError("bayesian_recommendation_study_mismatch");
          return null;
        }
        setRecommendation(restored);
        if (recommendationId === null && restored !== null) {
          onRecommendationSelected(restored.recommendation_id);
        }
        if (
          restored?.requested_total_trial_budget !== null &&
          restored?.requested_total_trial_budget !== undefined
        ) {
          setTotalTrialBudget(String(restored.requested_total_trial_budget));
        }
        return restored;
      } catch (caught) {
        if (restoreGuard.isCurrent(request)) {
          setRecommendation(null);
          setError(bayesianErrorCode(caught));
        }
        return null;
      } finally {
        if (restoreGuard.isCurrent(request)) setIsRestoring(false);
      }
    },
    [onRecommendationSelected, restoreGuard],
  );

  useEffect(() => {
    restoreGuard.cancel();
    createGuard.cancel();
    setRecommendation(null);
    setError(null);
    setIsRestoring(false);
    setIsRecommending(false);
    setTotalTrialBudget(String(defaultBayesianSearch.total_trial_budget));
    if (selectedStudyId !== null) {
      void loadRecommendation(selectedStudyId, requestedRecommendationId);
    }
    return () => restoreGuard.cancel();
  }, [createGuard, loadRecommendation, requestedRecommendationId, restoreGuard, selectedStudyId]);

  async function onRecommend(study: BayesianStudyResponse): Promise<boolean> {
    const parsedTotalTrialBudget = Number(totalTrialBudget);
    const blocker = bayesianRecommendationBudgetBlocker(
      study.trial_count,
      parsedTotalTrialBudget,
      study.recommendation_hard_trial_limit,
    );
    if (blocker !== null) {
      setError(blocker);
      return false;
    }
    const request = createGuard.begin();
    setIsRecommending(true);
    setError(null);
    try {
      const created = await createBayesianRecommendation(study.study_id, {
        expected_history_revision_id: study.observation_history.history_revision_id,
        search: { ...defaultBayesianSearch, total_trial_budget: parsedTotalTrialBudget },
      });
      if (!createGuard.isCurrent(request)) return false;
      setRecommendation(created);
      onRecommendationSelected(created.recommendation_id);
      return true;
    } catch (caught) {
      if (createGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      return false;
    } finally {
      if (createGuard.isCurrent(request)) setIsRecommending(false);
    }
  }

  const onRefresh = useCallback(async () => {
    if (selectedStudyId === null) return null;
    return loadRecommendation(
      selectedStudyId,
      recommendation?.recommendation_id ?? requestedRecommendationId,
    );
  }, [loadRecommendation, recommendation?.recommendation_id, requestedRecommendationId, selectedStudyId]);

  function clearRecommendation() {
    restoreGuard.cancel();
    createGuard.cancel();
    setRecommendation(null);
    setError(null);
    setIsRestoring(false);
    setIsRecommending(false);
    setTotalTrialBudget(String(defaultBayesianSearch.total_trial_budget));
  }

  return {
    clearRecommendation,
    error,
    isRecommending,
    isRestoring,
    onRecommend,
    onRefresh,
    recommendation,
    setError,
    setTotalTrialBudget,
    totalTrialBudget,
  };
}
