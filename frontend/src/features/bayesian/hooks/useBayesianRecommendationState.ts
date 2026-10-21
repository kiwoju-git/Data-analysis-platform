import { useCallback, useEffect, useRef, useState } from "react";

import {
  createBayesianRecommendationBatch,
  fetchBayesianRecommendation,
  fetchBayesianRecommendationBatch,
  fetchLatestBayesianRecommendation,
  fetchLatestBayesianRecommendationBatch,
  type BayesianExecutionMode,
  type BayesianExplorationProfile,
  type BayesianRecommendationBatchResponse,
  type BayesianRecommendationResponse,
  type BayesianStudyResponse,
} from "../../../api";
import { bayesianRecommendationBudgetBlocker } from "../../../bayesianStudyDraft";
import { createLatestRequestGuard } from "../../../latestRequest";
import {
  bayesianErrorCode,
  defaultBayesianBatchSearch,
} from "../bayesianDisplay";
import { buildNoisePolicy, defaultNoiseDraft, strictBoNumber, type BayesianNoiseDraft } from "../boNoisePolicy";

const ignoreSelection = () => undefined;

export function useBayesianRecommendationState({
  selectedStudyId,
  sourceHistoryKey = null,
  requestedBatchId = null,
  requestedRecommendationId,
  onBatchSelected = ignoreSelection,
  onRecommendationSelected,
}: {
  selectedStudyId: string | null;
  sourceHistoryKey?: string | null;
  requestedBatchId?: string | null;
  requestedRecommendationId: string | null;
  onBatchSelected?: (batchId: string | null) => void;
  onRecommendationSelected: (recommendationId: string | null) => void;
}) {
  const [batch, setBatch] =
    useState<BayesianRecommendationBatchResponse | null>(null);
  const [recommendation, setRecommendation] =
    useState<BayesianRecommendationResponse | null>(null);
  const [executionMode, setExecutionMode] =
    useState<BayesianExecutionMode>("sequential_single");
  const [batchSize, setBatchSize] = useState("1");
  const [explorationProfile, setExplorationProfile] =
    useState<BayesianExplorationProfile>("balanced");
  const [customXi, setCustomXi] = useState("0.01");
  const [totalTrialBudget, setTotalTrialBudget] = useState(
    String(defaultBayesianBatchSearch.total_trial_budget),
  );
  const [isRestoring, setIsRestoring] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noiseDraft, setNoiseDraft] = useState<BayesianNoiseDraft>(defaultNoiseDraft);
  const [draftChanged, setDraftChanged] = useState(false);
  const restoreGuard = useRef(createLatestRequestGuard()).current;
  const createGuard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    createGuard.cancel();
    setIsRecommending(false);
    return () => createGuard.cancel();
  }, [createGuard, sourceHistoryKey]);

  const loadRecommendation = useCallback(
    async (
      studyId: string,
      batchId: string | null,
      recommendationId: string | null,
    ) => {
      const request = restoreGuard.begin();
      setIsRestoring(true);
      setError(null);
      try {
        if (recommendationId !== null) {
          const restored = await fetchBayesianRecommendation(
            studyId,
            recommendationId,
          );
          if (!restoreGuard.isCurrent(request)) return null;
          if (restored.study_id !== studyId) {
            setBatch(null);
            setRecommendation(null);
            setError("bayesian_recommendation_study_mismatch");
            return null;
          }
          setBatch(null);
          setRecommendation(restored);
          if (restored.requested_total_trial_budget !== null) {
            setTotalTrialBudget(
              String(restored.requested_total_trial_budget),
            );
          }
          return restored;
        }

        const restoredBatch =
          batchId === null
            ? (await fetchLatestBayesianRecommendationBatch(studyId)).item
            : await fetchBayesianRecommendationBatch(studyId, batchId);
        if (!restoreGuard.isCurrent(request)) return null;
        if (restoredBatch !== null) {
          if (restoredBatch.study_id !== studyId) {
            setBatch(null);
            setRecommendation(null);
            setError("bayesian_recommendation_study_mismatch");
            return null;
          }
          setBatch(restoredBatch);
          setRecommendation(null);
          setExecutionMode(restoredBatch.execution_mode);
          setBatchSize(String(restoredBatch.batch_size));
          setExplorationProfile(
            restoredBatch.acquisition.exploration_profile,
          );
          setCustomXi(
            String(restoredBatch.acquisition.xi_standardized),
          );
          setTotalTrialBudget(
            String(restoredBatch.requested_total_trial_budget),
          );
          if (batchId === null) onBatchSelected(restoredBatch.batch_id);
          if (restoredBatch.result_schema_version === 2) {
            const noise = restoredBatch.shared_model.noise;
            setNoiseDraft({ ...defaultNoiseDraft, noiseMode: noise.mode,
              noiseInitial: noise.mode === "estimate" ? String(noise.initial_variance_scaled) : defaultNoiseDraft.noiseInitial,
              noiseLower: String(noise.bounds_scaled?.[0] ?? 1e-6), noiseUpper: String(noise.bounds_scaled?.[1] ?? 1),
              fixedNoiseSd: noise.fixed_sd_raw === null ? "" : String(noise.fixed_sd_raw),
              observationMode: restoredBatch.observation_view.mode,
              nearbyUnits: restoredBatch.observation_view.nearby_diagnostics.units,
              nearbyTolerances: Object.fromEntries(Object.entries(restoredBatch.observation_view.nearby_diagnostics.tolerances ?? {}).map(([id, value]) => [id, String(value)])),
              sampleCount: String(restoredBatch.items[0]?.planning.requested_sample_count ?? 64),
              minBatchDistance: String(restoredBatch.search_budget.min_batch_distance_normalized),
            });
          }
          setDraftChanged(false);
          return restoredBatch;
        }

        const restoredLegacy = (
          await fetchLatestBayesianRecommendation(studyId)
        ).item;
        if (!restoreGuard.isCurrent(request)) return null;
        setBatch(null);
        setRecommendation(restoredLegacy);
        if (restoredLegacy !== null) {
          onRecommendationSelected(restoredLegacy.recommendation_id);
        }
        return restoredLegacy;
      } catch (caught) {
        if (restoreGuard.isCurrent(request)) {
          setBatch(null);
          setRecommendation(null);
          setError(bayesianErrorCode(caught));
        }
        return null;
      } finally {
        if (restoreGuard.isCurrent(request)) setIsRestoring(false);
      }
    },
    [
      onBatchSelected,
      onRecommendationSelected,
      restoreGuard,
    ],
  );

  useEffect(() => {
    restoreGuard.cancel();
    createGuard.cancel();
    setBatch(null);
    setRecommendation(null);
    setError(null);
    setIsRestoring(false);
    setIsRecommending(false);
    if (selectedStudyId !== null) {
      void loadRecommendation(
        selectedStudyId,
        requestedBatchId,
        requestedRecommendationId,
      );
    }
    return () => { restoreGuard.cancel(); createGuard.cancel(); };
  }, [
    createGuard,
    loadRecommendation,
    requestedBatchId,
    requestedRecommendationId,
    restoreGuard,
    selectedStudyId,
  ]);

  async function onRecommend(study: BayesianStudyResponse): Promise<boolean> {
    if (study.study_id !== selectedStudyId) return false;
    const policy = buildNoisePolicy(noiseDraft, study.factors);
    if (policy.payload === null) {
      setError("bayesian_surrogate_policy_invalid");
      return false;
    }
    const parsedBatchSize = Number(batchSize);
    const parsedTotalTrialBudget = Number(totalTrialBudget);
    const resolvedBatchSize =
      executionMode === "sequential_single" ? 1 : parsedBatchSize;
    if (
      (executionMode === "parallel_batch" &&
        (!Number.isInteger(parsedBatchSize) ||
          parsedBatchSize < 2 ||
          parsedBatchSize > 8)) ||
      (executionMode === "sequential_single" && parsedBatchSize !== 1)
    ) {
      setError("bayesian_optimization_batch_size_invalid");
      return false;
    }
    const blocker = bayesianRecommendationBudgetBlocker(
      study.trial_count,
      parsedTotalTrialBudget,
      study.recommendation_hard_trial_limit,
      resolvedBatchSize,
    );
    if (blocker !== null) {
      setError(blocker);
      return false;
    }
    const xi = resolveXi(explorationProfile, customXi);
    if (xi === null) {
      setError("bayesian_optimization_xi_invalid");
      return false;
    }
    const request = createGuard.begin();
    setIsRecommending(true);
    setError(null);
    try {
      const created = await createBayesianRecommendationBatch(
        study.study_id,
        {
          schema_version: 2,
          expected_history_revision_id:
            study.observation_history.history_revision_id,
          expected_history_sha256: study.observation_history.observation_history_sha256,
          execution_mode: executionMode,
          batch_size: resolvedBatchSize,
          acquisition: {
            kind:
              study.objective.goal_type === "match_target"
                ? "expected_target_improvement"
                : "expected_improvement",
            exploration_profile: explorationProfile,
            xi_standardized: xi,
          },
          search: {
            ...defaultBayesianBatchSearch,
            batch_policy: "greedy_mc_joint_latent_improvement_v2",
            total_trial_budget: parsedTotalTrialBudget,
          },
          ...policy.payload,
        },
      );
      if (!createGuard.isCurrent(request)) return false;
      if (created.study_id !== study.study_id || created.source_history_revision_id !== study.observation_history.history_revision_id ||
        created.source_observation_history_sha256 !== study.observation_history.observation_history_sha256) {
        setError("bayesian_recommendation_study_mismatch");
        return false;
      }
      setBatch(created);
      setDraftChanged(false);
      setRecommendation(null);
      onBatchSelected(created.batch_id);
      return true;
    } catch (caught) {
      if (createGuard.isCurrent(request)) {
        setError(bayesianErrorCode(caught));
      }
      return false;
    } finally {
      if (createGuard.isCurrent(request)) setIsRecommending(false);
    }
  }

  const onRefresh = useCallback(async () => {
    if (selectedStudyId === null) return null;
    return loadRecommendation(
      selectedStudyId,
      batch?.batch_id ?? requestedBatchId,
      recommendation?.recommendation_id ?? requestedRecommendationId,
    );
  }, [
    batch?.batch_id,
    loadRecommendation,
    recommendation?.recommendation_id,
    requestedBatchId,
    requestedRecommendationId,
    selectedStudyId,
  ]);

  function onExecutionModeChange(value: BayesianExecutionMode) {
    invalidateDraft();
    setExecutionMode(value);
    setBatchSize(value === "sequential_single" ? "1" : "2");
    setError(null);
  }

  function invalidateDraft() {
    createGuard.cancel();
    restoreGuard.cancel();
    setIsRecommending(false);
    setIsRestoring(false);
    setDraftChanged(true);
    setError(null);
  }

  function onNoiseDraftChange(value: BayesianNoiseDraft) {
    invalidateDraft();
    setNoiseDraft(value);
  }

  function clearRecommendation() {
    restoreGuard.cancel();
    createGuard.cancel();
    setBatch(null);
    setRecommendation(null);
    setError(null);
    setIsRestoring(false);
    setIsRecommending(false);
  }

  return {
    batch,
    batchSize,
    noiseDraft,
    draftChanged,
    onNoiseDraftChange,
    clearRecommendation,
    customXi,
    error,
    executionMode,
    explorationProfile,
    isRecommending,
    isRestoring,
    onExecutionModeChange,
    onRecommend,
    onRefresh,
    recommendation,
    setBatchSize: (value: string) => { invalidateDraft(); setBatchSize(value); },
    setCustomXi: (value: string) => { invalidateDraft(); setCustomXi(value); },
    setError,
    setExplorationProfile: (value: BayesianExplorationProfile) => { invalidateDraft(); setExplorationProfile(value); },
    setTotalTrialBudget: (value: string) => { invalidateDraft(); setTotalTrialBudget(value); },
    totalTrialBudget,
  };
}

function resolveXi(
  profile: BayesianExplorationProfile,
  customValue: string,
) {
  if (profile === "exploitation") return 0;
  if (profile === "balanced") return 0.01;
  if (profile === "exploration") return 0.1;
  const parsed = strictBoNumber(customValue);
  return parsed !== null && parsed >= 0 && parsed <= 10
    ? parsed
    : null;
}
