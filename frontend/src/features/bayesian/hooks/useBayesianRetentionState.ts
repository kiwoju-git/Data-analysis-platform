import { useEffect, useRef, useState } from "react";

import {
  deleteBayesianStudy,
  fetchBayesianStudyDeletionPreflight,
  type BayesianStudyDeletionPreflightResponse,
  type BayesianStudyResponse,
} from "../../../api";
import { createLatestRequestGuard } from "../../../latestRequest";
import { bayesianErrorCode } from "../bayesianDisplay";

export function useBayesianRetentionState(study: BayesianStudyResponse | null) {
  const [preflight, setPreflight] =
    useState<BayesianStudyDeletionPreflightResponse | null>(null);
  const [pendingDeletion, setPendingDeletion] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const checkGuard = useRef(createLatestRequestGuard()).current;
  const deleteGuard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    checkGuard.cancel();
    deleteGuard.cancel();
    setPreflight(null);
    setPendingDeletion(false);
    setIsChecking(false);
    setIsDeleting(false);
    setError(null);
  }, [checkGuard, deleteGuard, study?.study_id]);

  async function onCheck() {
    if (study === null || study.status === "active") return;
    const studyId = study.study_id;
    const request = checkGuard.begin();
    setIsChecking(true);
    setPendingDeletion(false);
    setError(null);
    try {
      const response = await fetchBayesianStudyDeletionPreflight(studyId);
      if (!checkGuard.isCurrent(request) || response.study_id !== studyId) return;
      setPreflight(response);
    } catch (caught) {
      if (checkGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
    } finally {
      if (checkGuard.isCurrent(request)) setIsChecking(false);
    }
  }

  async function onDelete(): Promise<boolean> {
    if (
      study === null ||
      preflight === null ||
      !preflight.eligible ||
      preflight.study_id !== study.study_id
    ) {
      return false;
    }
    const studyId = study.study_id;
    const request = deleteGuard.begin();
    setIsDeleting(true);
    setError(null);
    try {
      await deleteBayesianStudy(studyId, {
        confirmation_study_id: studyId,
        expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
      });
      if (!deleteGuard.isCurrent(request)) return false;
      setPreflight(null);
      setPendingDeletion(false);
      return true;
    } catch (caught) {
      if (deleteGuard.isCurrent(request)) setError(bayesianErrorCode(caught));
      return false;
    } finally {
      if (deleteGuard.isCurrent(request)) setIsDeleting(false);
    }
  }

  return {
    error,
    isChecking,
    isDeleting,
    onCheck,
    onDelete,
    pendingDeletion,
    preflight,
    setPendingDeletion,
  };
}
