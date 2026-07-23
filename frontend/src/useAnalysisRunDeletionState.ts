import { useEffect, useRef, useState } from "react";

import {
  deleteStoredAnalysisRun,
  fetchAnalysisRunDeletionPreflight,
  type AnalysisRunDeleteResponse,
  type AnalysisRunDeletionPreflightResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

export function useAnalysisRunDeletionState(
  analysisId: string | null,
  onDeleted: (response: AnalysisRunDeleteResponse) => void,
) {
  const [preflight, setPreflight] =
    useState<AnalysisRunDeletionPreflightResponse | null>(null);
  const [deletion, setDeletion] = useState<AnalysisRunDeleteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingPreflight, setIsLoadingPreflight] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const preflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionRequest = useRef(createLatestRequestGuard()).current;
  const onDeletedRef = useRef(onDeleted);
  onDeletedRef.current = onDeleted;

  useEffect(() => {
    preflightRequest.cancel();
    deletionRequest.cancel();
    setPreflight(null);
    setDeletion(null);
    setError(null);
    setIsLoadingPreflight(false);
    setIsDeleting(false);
  }, [analysisId, deletionRequest, preflightRequest]);

  return {
    preflight,
    deletion,
    error,
    isLoadingPreflight,
    isDeleting,
    onClear: () => {
      preflightRequest.cancel();
      deletionRequest.cancel();
      setPreflight(null);
      setDeletion(null);
      setError(null);
      setIsLoadingPreflight(false);
      setIsDeleting(false);
    },
    onLoadPreflight: () => {
      if (analysisId === null) return;
      const request = preflightRequest.begin();
      setPreflight(null);
      setDeletion(null);
      setError(null);
      setIsLoadingPreflight(true);
      void fetchAnalysisRunDeletionPreflight(analysisId)
        .then((response) => {
          if (
            preflightRequest.isCurrent(request) &&
            response.analysis_id === analysisId
          ) {
            setPreflight(response);
          }
        })
        .catch((requestError) => {
          if (preflightRequest.isCurrent(request)) {
            setError(
              requestError instanceof Error
                ? requestError.message
                : "analysis_run_deletion_preflight_failed",
            );
          }
        })
        .finally(() => {
          if (preflightRequest.isCurrent(request)) setIsLoadingPreflight(false);
        });
    },
    onDelete: (current: AnalysisRunDeletionPreflightResponse) => {
      if (
        analysisId === null ||
        current.analysis_id !== analysisId ||
        !current.deletion_ready
      ) {
        return;
      }
      const request = deletionRequest.begin();
      preflightRequest.cancel();
      setError(null);
      setIsLoadingPreflight(false);
      setIsDeleting(true);
      void deleteStoredAnalysisRun(analysisId, {
        confirmation_analysis_id: analysisId,
        expected_deletion_manifest_sha256:
          current.deletion_manifest_sha256,
      })
        .then((response) => {
          if (
            deletionRequest.isCurrent(request) &&
            response.analysis_id === analysisId
          ) {
            setDeletion(response);
            setPreflight(null);
            onDeletedRef.current(response);
          }
        })
        .catch((requestError) => {
          if (deletionRequest.isCurrent(request)) {
            setError(
              requestError instanceof Error
                ? requestError.message
                : "analysis_run_delete_failed",
            );
          }
        })
        .finally(() => {
          if (deletionRequest.isCurrent(request)) setIsDeleting(false);
        });
    },
  };
}
