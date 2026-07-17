import { useEffect, useRef, useState } from "react";

import {
  deleteRegressionModel,
  fetchRegressionModelDeletionPreflight,
  type RegressionModelDeleteResponse,
  type RegressionModelDeletionPreflightResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

export interface RegressionModelRetentionState {
  deletedModelId: string | null;
  deletion: RegressionModelDeleteResponse | null;
  error: string | null;
  isDeleting: boolean;
  isLoadingPreflight: boolean;
  preflight: RegressionModelDeletionPreflightResponse | null;
  onClear: () => void;
  onDelete: (preflight: RegressionModelDeletionPreflightResponse) => void;
  onLoadPreflight: () => void;
}

export function useRegressionModelRetentionState(
  modelId: string | null,
): RegressionModelRetentionState {
  const [preflight, setPreflight] =
    useState<RegressionModelDeletionPreflightResponse | null>(null);
  const [deletion, setDeletion] = useState<RegressionModelDeleteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingPreflight, setIsLoadingPreflight] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const preflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionRequest = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    preflightRequest.cancel();
    deletionRequest.cancel();
    setPreflight(null);
    setDeletion(null);
    setError(null);
    setIsLoadingPreflight(false);
    setIsDeleting(false);
  }, [deletionRequest, modelId, preflightRequest]);

  const clear = () => {
    preflightRequest.cancel();
    deletionRequest.cancel();
    setPreflight(null);
    setDeletion(null);
    setError(null);
    setIsLoadingPreflight(false);
    setIsDeleting(false);
  };

  return {
    deletedModelId: deletion?.model_id ?? null,
    deletion,
    error,
    isDeleting,
    isLoadingPreflight,
    preflight,
    onClear: clear,
    onLoadPreflight: () => {
      if (modelId === null) return;
      const request = preflightRequest.begin();
      setPreflight(null);
      setDeletion(null);
      setError(null);
      setIsLoadingPreflight(true);
      void fetchRegressionModelDeletionPreflight(modelId)
        .then((response) => {
          if (preflightRequest.isCurrent(request)) setPreflight(response);
        })
        .catch((fetchError) => {
          if (preflightRequest.isCurrent(request)) {
            setError(
              fetchError instanceof Error
                ? fetchError.message
                : "regression_model_deletion_preflight_failed",
            );
          }
        })
        .finally(() => {
          if (preflightRequest.isCurrent(request)) setIsLoadingPreflight(false);
        });
    },
    onDelete: (currentPreflight) => {
      if (modelId === null || currentPreflight.model_id !== modelId) return;
      const request = deletionRequest.begin();
      preflightRequest.cancel();
      setError(null);
      setIsLoadingPreflight(false);
      setIsDeleting(true);
      void deleteRegressionModel(modelId, {
        confirmation_model_id: modelId,
        expected_deletion_manifest_sha256:
          currentPreflight.deletion_manifest_sha256,
      })
        .then((response) => {
          if (deletionRequest.isCurrent(request)) {
            setDeletion(response);
            setPreflight(null);
          }
        })
        .catch((deleteError) => {
          if (deletionRequest.isCurrent(request)) {
            setError(
              deleteError instanceof Error
                ? deleteError.message
                : "regression_model_deletion_failed",
            );
          }
        })
        .finally(() => {
          if (deletionRequest.isCurrent(request)) setIsDeleting(false);
        });
    },
  };
}
