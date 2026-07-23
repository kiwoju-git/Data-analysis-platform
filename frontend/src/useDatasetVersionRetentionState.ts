import { useEffect, useRef, useState } from "react";

import {
  deleteDatasetVersion,
  fetchDatasetVersionDeletionDependencies,
  fetchDatasetVersionDeletionPreflight,
  type DatasetDeletionDependencyAssetType,
  type DatasetDeletionDependencyPage,
  type DatasetDeletionOperationId,
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
  const [dependencies, setDependencies] =
    useState<DatasetDeletionDependencyPage | null>(null);
  const [error, setError] = useState<AssetManagementError | null>(null);
  const [isLoadingPreflight, setIsLoadingPreflight] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const preflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionRequest = useRef(createLatestRequestGuard()).current;
  const dependencyRequest = useRef(createLatestRequestGuard()).current;
  const onDeletedRef = useRef(onDeleted);
  onDeletedRef.current = onDeleted;

  useEffect(() => {
    preflightRequest.cancel();
    deletionRequest.cancel();
    dependencyRequest.cancel();
    setPreflight(null);
    setDeletion(null);
    setDependencies(null);
    setError(null);
    setIsLoadingPreflight(false);
    setIsDeleting(false);
  }, [deletionRequest, dependencyRequest, preflightRequest, versionId]);

  return {
    deletion,
    dependencies,
    error,
    isDeleting,
    isLoadingPreflight,
    preflight,
    onLoadDependencies: (
      assetType: DatasetDeletionDependencyAssetType | null,
      offset = 0,
    ) => {
      const request = dependencyRequest.begin();
      setError(null);
      void fetchDatasetVersionDeletionDependencies(
        versionId,
        assetType,
        offset,
        20,
      )
        .then((response) => {
          if (dependencyRequest.isCurrent(request)) setDependencies(response);
        })
        .catch((dependencyError) => {
          if (dependencyRequest.isCurrent(request)) {
            setError(
              classifyAssetManagementError(
                dependencyError,
                "dataset_version_dependencies_fetch_failed",
              ),
            );
          }
        });
    },
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
      operationId: DatasetDeletionOperationId = "delete_dataset_verified",
    ) => {
      const operation = current.available_operations.find(
        (item) => item.operation_id === operationId,
      );
      if (current.version_id !== versionId || !operation?.ready) return;
      const request = deletionRequest.begin();
      preflightRequest.cancel();
      setError(null);
      setIsLoadingPreflight(false);
      setIsDeleting(true);
      void deleteDatasetVersion(current, operationId)
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
