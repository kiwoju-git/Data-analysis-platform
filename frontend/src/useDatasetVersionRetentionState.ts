import { useEffect, useRef, useState } from "react";

import {
  deleteDatasetVersion,
  fetchDatasetVersionDeletionPreflight,
  type DatasetVersionDeleteResponse,
  type DatasetVersionDeletionPreflightResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";
import { classifyAssetManagementError, type AssetManagementError } from "./assetManagementErrors";

export function useDatasetVersionRetentionState(
  versionId: string,
  onDeleted: (response: DatasetVersionDeleteResponse) => void,
) {
  const [preflight, setPreflight] =
    useState<DatasetVersionDeletionPreflightResponse | null>(null);
  const [deletion, setDeletion] = useState<DatasetVersionDeleteResponse | null>(null);
  const [error, setError] = useState<AssetManagementError | null>(null);
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
  }, [deletionRequest, preflightRequest, versionId]);

  return {
    deletion,
    error,
    isDeleting,
    isLoadingPreflight,
    preflight,
    onLoadPreflight: () => {
      const request = preflightRequest.begin();
      setPreflight(null);
      setDeletion(null);
      setError(null);
      setIsLoadingPreflight(true);
      void fetchDatasetVersionDeletionPreflight(versionId)
        .then((response) => {
          if (preflightRequest.isCurrent(request) && response.version_id === versionId) {
            setPreflight(response);
          }
        })
        .catch((fetchError) => {
          if (preflightRequest.isCurrent(request)) {
            setError(
              classifyAssetManagementError(
                fetchError,
                "dataset_version_deletion_preflight_failed",
              ),
            );
          }
        })
        .finally(() => {
          if (preflightRequest.isCurrent(request)) setIsLoadingPreflight(false);
        });
    },
    onDelete: (
      current: DatasetVersionDeletionPreflightResponse,
      mode:
        | "verified_files_and_metadata"
        | "metadata_only_preserve_unverified_files" = "verified_files_and_metadata",
    ) => {
      const modeReady =
        mode === "verified_files_and_metadata"
          ? current.verified_delete_ready
          : current.metadata_only_cleanup_ready;
      if (current.version_id !== versionId || !modeReady) return;
      const request = deletionRequest.begin();
      preflightRequest.cancel();
      setError(null);
      setIsLoadingPreflight(false);
      setIsDeleting(true);
      void deleteDatasetVersion(current, mode)
        .then((response) => {
          if (!deletionRequest.isCurrent(request) || response.version_id !== versionId) return;
          setDeletion(response);
          setPreflight(null);
          onDeletedRef.current(response);
        })
        .catch((deleteError) => {
          if (deletionRequest.isCurrent(request)) {
            setError(
              classifyAssetManagementError(deleteError, "dataset_version_deletion_failed"),
            );
          }
        })
        .finally(() => {
          if (deletionRequest.isCurrent(request)) setIsDeleting(false);
        });
    },
  };
}
