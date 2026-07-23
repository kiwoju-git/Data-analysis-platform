import { useCallback, useEffect, useRef, useState } from "react";

import {
  deleteRegressionModel,
  fetchRegressionModelDeletionPreflight,
  fetchRegressionModelManifest,
  type RegressionModelDeleteResponse,
  type RegressionModelDeletionPreflightResponse,
  type RegressionModelManifestResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";
import {
  classifyAssetManagementError,
  type AssetManagementError,
} from "./assetManagementErrors";

export type RegressionModelAvailability =
  | "available"
  | "unavailable_or_deleted"
  | "integrity_error";

const integrityErrorCodes = new Set([
  "regression_model_manifest_missing",
  "regression_model_manifest_checksum_mismatch",
  "regression_model_manifest_invalid",
  "regression_model_manifest_path_invalid",
]);

export interface RegressionModelRetentionState {
  availability: RegressionModelAvailability | null;
  availabilityError: string | null;
  deletedModelId: string | null;
  deletion: RegressionModelDeleteResponse | null;
  error: string | null;
  errorDetail: AssetManagementError | null;
  isDeleting: boolean;
  isCheckingAvailability: boolean;
  isLoadingPreflight: boolean;
  manifest: RegressionModelManifestResponse | null;
  preflight: RegressionModelDeletionPreflightResponse | null;
  onClear: () => void;
  onDelete: (
    preflight: RegressionModelDeletionPreflightResponse,
    mode?: "model_only" | "model_and_predictions",
  ) => void;
  onLoadPreflight: () => void;
  onRetryAvailability: () => void;
}

export function useRegressionModelRetentionState(
  modelId: string | null,
): RegressionModelRetentionState {
  const [preflight, setPreflight] =
    useState<RegressionModelDeletionPreflightResponse | null>(null);
  const [deletion, setDeletion] = useState<RegressionModelDeleteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetail, setErrorDetail] = useState<AssetManagementError | null>(null);
  const [isLoadingPreflight, setIsLoadingPreflight] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [availability, setAvailability] =
    useState<RegressionModelAvailability | null>(null);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  const [manifest, setManifest] = useState<RegressionModelManifestResponse | null>(null);
  const availabilityRequest = useRef(createLatestRequestGuard()).current;
  const preflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionRequest = useRef(createLatestRequestGuard()).current;

  const checkAvailability = useCallback(() => {
    if (modelId === null) return;
    const request = availabilityRequest.begin();
    setAvailability(null);
    setAvailabilityError(null);
    setManifest(null);
    setIsCheckingAvailability(true);
    void fetchRegressionModelManifest(modelId)
      .then((response) => {
        if (availabilityRequest.isCurrent(request)) {
          setManifest(response);
          setAvailability("available");
        }
      })
      .catch((fetchError) => {
        if (!availabilityRequest.isCurrent(request)) return;
        const code =
          fetchError instanceof Error
            ? fetchError.message
            : "regression_model_availability_failed";
        setAvailabilityError(code);
        setManifest(null);
        if (code === "regression_model_not_found") {
          setAvailability("unavailable_or_deleted");
        } else if (integrityErrorCodes.has(code)) {
          setAvailability("integrity_error");
        }
      })
      .finally(() => {
        if (availabilityRequest.isCurrent(request)) setIsCheckingAvailability(false);
      });
  }, [availabilityRequest, modelId]);

  useEffect(() => {
    availabilityRequest.cancel();
    preflightRequest.cancel();
    deletionRequest.cancel();
    setPreflight(null);
    setDeletion(null);
    setError(null);
    setErrorDetail(null);
    setIsLoadingPreflight(false);
    setIsDeleting(false);
    setAvailability(null);
    setAvailabilityError(null);
    setManifest(null);
    setIsCheckingAvailability(false);
    if (modelId === null) return;
    checkAvailability();
  }, [availabilityRequest, checkAvailability, deletionRequest, modelId, preflightRequest]);

  const clear = () => {
    preflightRequest.cancel();
    deletionRequest.cancel();
    setPreflight(null);
    setDeletion(null);
    setError(null);
    setErrorDetail(null);
    setIsLoadingPreflight(false);
    setIsDeleting(false);
  };

  return {
    availability,
    availabilityError,
    deletedModelId: deletion?.model_id ?? null,
    deletion,
    error,
    errorDetail,
    isDeleting,
    isCheckingAvailability,
    isLoadingPreflight,
    manifest,
    preflight,
    onClear: clear,
    onLoadPreflight: () => {
      if (modelId === null) return;
      const request = preflightRequest.begin();
      setPreflight(null);
      setDeletion(null);
      setError(null);
      setErrorDetail(null);
      setIsLoadingPreflight(true);
      void fetchRegressionModelDeletionPreflight(modelId)
        .then((response) => {
          if (preflightRequest.isCurrent(request)) setPreflight(response);
        })
        .catch((fetchError) => {
          if (preflightRequest.isCurrent(request)) {
            const detail = classifyAssetManagementError(
              fetchError,
              "regression_model_deletion_preflight_failed",
            );
            setError(detail.code);
            setErrorDetail(detail);
          }
        })
        .finally(() => {
          if (preflightRequest.isCurrent(request)) setIsLoadingPreflight(false);
        });
    },
    onRetryAvailability: checkAvailability,
    onDelete: (currentPreflight, mode = "model_only") => {
      if (modelId === null || currentPreflight.model_id !== modelId) return;
      const request = deletionRequest.begin();
      preflightRequest.cancel();
      setError(null);
      setErrorDetail(null);
      setIsLoadingPreflight(false);
      setIsDeleting(true);
      void deleteRegressionModel(modelId, {
        confirmation_model_id: modelId,
        expected_deletion_manifest_sha256:
          mode === "model_and_predictions"
            ? (currentPreflight.cascade_deletion_manifest_sha256 ?? "")
            : currentPreflight.deletion_manifest_sha256,
        mode,
      })
        .then((response) => {
          if (deletionRequest.isCurrent(request)) {
            setDeletion(response);
            setPreflight(null);
            setAvailability("unavailable_or_deleted");
            setAvailabilityError("regression_model_not_found");
            setManifest(null);
          }
        })
        .catch((deleteError) => {
          if (deletionRequest.isCurrent(request)) {
            const detail = classifyAssetManagementError(
              deleteError,
              "regression_model_deletion_failed",
            );
            setError(detail.code);
            setErrorDetail(detail);
          }
        })
        .finally(() => {
          if (deletionRequest.isCurrent(request)) setIsDeleting(false);
        });
    },
  };
}
