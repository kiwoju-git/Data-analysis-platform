import { useCallback, useEffect, useRef, useState } from "react";

import {
  abandonBayesianTrial,
  closeBayesianStudy,
  createBayesianStudy,
  fetchBayesianStudy,
  recordBayesianObservation,
  type BayesianStudyCloseReason,
  type BayesianStudyCreateRequest,
  type BayesianStudyResponse,
} from "../../../api";
import { createLatestRequestGuard } from "../../../latestRequest";
import {
  bayesianErrorCode,
  type PendingTrialTransition,
  type StudyCloseTarget,
} from "../bayesianDisplay";

export function useBayesianStudyLifecycleState(selectedStudyId: string | null) {
  const [study, setStudy] = useState<BayesianStudyResponse | null>(null);
  const [observations, setObservations] = useState<Record<string, string>>({});
  const [pendingTransition, setPendingTransition] =
    useState<PendingTrialTransition | null>(null);
  const [closeTarget, setCloseTargetState] = useState<StudyCloseTarget>("completed");
  const [closeReason, setCloseReason] =
    useState<BayesianStudyCloseReason>("confirmation_complete");
  const [closeNote, setCloseNote] = useState("");
  const [pendingStudyClose, setPendingStudyClose] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingTrial, setIsSavingTrial] = useState(false);
  const [isClosing, setIsClosing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const restoreGuard = useRef(createLatestRequestGuard()).current;
  const createGuard = useRef(createLatestRequestGuard()).current;
  const transitionGuard = useRef(createLatestRequestGuard()).current;
  const closeGuard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    restoreGuard.cancel();
    createGuard.cancel();
    transitionGuard.cancel();
    closeGuard.cancel();
    setObservations({});
    setPendingTransition(null);
    setPendingStudyClose(false);
    setIsCreating(false);
    setIsSavingTrial(false);
    setIsClosing(false);
    setError(null);
    setStudy(null);
    if (selectedStudyId === null) {
      setIsRestoring(false);
      return;
    }
    const request = restoreGuard.begin();
    setIsRestoring(true);
    void fetchBayesianStudy(selectedStudyId)
      .then((restored) => {
        if (restoreGuard.isCurrent(request)) setStudy(restored);
      })
      .catch((caught: unknown) => {
        if (restoreGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      })
      .finally(() => {
        if (restoreGuard.isCurrent(request)) setIsRestoring(false);
      });
    return () => restoreGuard.cancel();
  }, [closeGuard, createGuard, restoreGuard, selectedStudyId, transitionGuard]);

  const refreshStudy = useCallback(async (): Promise<BayesianStudyResponse | null> => {
    const studyId = study?.study_id ?? selectedStudyId;
    if (studyId === null) return null;
    const request = restoreGuard.begin();
    setIsRestoring(true);
    setError(null);
    try {
      const restored = await fetchBayesianStudy(studyId);
      if (!restoreGuard.isCurrent(request)) return null;
      setStudy(restored);
      return restored;
    } catch (caught) {
      if (restoreGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      return null;
    } finally {
      if (restoreGuard.isCurrent(request)) setIsRestoring(false);
    }
  }, [restoreGuard, selectedStudyId, study?.study_id]);

  async function onCreate(
    requestPayload: BayesianStudyCreateRequest,
  ): Promise<BayesianStudyResponse | null> {
    const request = createGuard.begin();
    setIsCreating(true);
    setError(null);
    try {
      const created = await createBayesianStudy(requestPayload);
      if (!createGuard.isCurrent(request)) return null;
      setStudy(created);
      setObservations({});
      setPendingTransition(null);
      setPendingStudyClose(false);
      return created;
    } catch (caught) {
      if (createGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      return null;
    } finally {
      if (createGuard.isCurrent(request)) setIsCreating(false);
    }
  }

  function requestTrialTransition(trialId: string, action: "complete" | "abandon") {
    if (action === "complete" && !Number.isFinite(Number(observations[trialId]))) {
      setError("bayesian_observation_invalid");
      return;
    }
    setError(null);
    setPendingTransition({ trialId, action });
  }

  async function confirmTrialTransition(): Promise<boolean> {
    if (pendingTransition === null || study === null) return false;
    const activeStudy = study;
    const { trialId, action } = pendingTransition;
    const objectiveValue = Number(observations[trialId]);
    if (action === "complete" && !Number.isFinite(objectiveValue)) {
      setError("bayesian_observation_invalid");
      return false;
    }
    const request = transitionGuard.begin();
    setIsSavingTrial(true);
    setError(null);
    try {
      if (action === "complete") {
        await recordBayesianObservation(activeStudy.study_id, trialId, {
          objective_value: objectiveValue,
          expected_history_revision_id:
            activeStudy.observation_history.history_revision_id,
        });
      } else {
        await abandonBayesianTrial(
          activeStudy.study_id,
          trialId,
          closeTarget === "abandoned"
            ? {
                expected_history_revision_id:
                  activeStudy.observation_history.history_revision_id,
                intent: "close_study",
              }
            : undefined,
        );
      }
      if (!transitionGuard.isCurrent(request)) return false;
      const restored = await fetchBayesianStudy(activeStudy.study_id);
      if (!transitionGuard.isCurrent(request)) return false;
      setStudy(restored);
      setObservations((current) => ({ ...current, [trialId]: "" }));
      setPendingTransition(null);
      return true;
    } catch (caught) {
      if (transitionGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      return false;
    } finally {
      if (transitionGuard.isCurrent(request)) setIsSavingTrial(false);
    }
  }

  async function confirmStudyClose(): Promise<boolean> {
    if (study === null || study.status !== "active") return false;
    const activeStudy = study;
    const request = closeGuard.begin();
    setIsClosing(true);
    setError(null);
    try {
      const response = await closeBayesianStudy(activeStudy.study_id, {
        target_status: closeTarget,
        reason_code: closeReason,
        note: closeNote.trim() || null,
        request_id: crypto.randomUUID(),
        expected_study_version_id: activeStudy.study_version_id,
        expected_history_revision_id:
          activeStudy.observation_history.history_revision_id,
        expected_observation_history_sha256:
          activeStudy.observation_history.observation_history_sha256,
      });
      if (!closeGuard.isCurrent(request)) return false;
      setStudy(response.study);
      setPendingStudyClose(false);
      setPendingTransition(null);
      return true;
    } catch (caught) {
      if (closeGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      return false;
    } finally {
      if (closeGuard.isCurrent(request)) setIsClosing(false);
    }
  }

  function setCloseTarget(target: StudyCloseTarget) {
    setCloseTargetState(target);
    setCloseReason(target === "completed" ? "confirmation_complete" : "study_cancelled");
    setPendingStudyClose(false);
  }

  function clearStudy() {
    restoreGuard.cancel();
    createGuard.cancel();
    transitionGuard.cancel();
    closeGuard.cancel();
    setStudy(null);
    setObservations({});
    setPendingTransition(null);
    setPendingStudyClose(false);
    setIsRestoring(false);
    setIsCreating(false);
    setIsSavingTrial(false);
    setIsClosing(false);
    setError(null);
  }

  return {
    clearStudy,
    closeNote,
    closeReason,
    closeTarget,
    confirmStudyClose,
    confirmTrialTransition,
    error,
    isClosing,
    isCreating,
    isRestoring,
    isSavingTrial,
    observations,
    onCreate,
    pendingStudyClose,
    pendingTransition,
    refreshStudy,
    requestTrialTransition,
    setCloseNote,
    setCloseReason,
    setCloseTarget,
    setError,
    setObservation: (trialId: string, value: string) =>
      setObservations((current) => ({ ...current, [trialId]: value })),
    setPendingStudyClose,
    setPendingTransition,
    study,
  };
}
