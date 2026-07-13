import { useEffect, useRef, useState } from "react";

import {
  fetchDatasetVersions,
  type DatasetVersionCatalogItem,
  type DatasetVersionCatalogResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

const predictionTargetPageSize = 20;

export interface RegressionPredictionTargetState {
  catalog: DatasetVersionCatalogResponse | null;
  error: string | null;
  isLoading: boolean;
  selectedTarget: DatasetVersionCatalogItem | null;
  selectedTargetVersionId: string | null;
  onPageChange: (offset: number) => void;
  onSelect: (versionId: string) => void;
}

interface UseRegressionPredictionTargetStateOptions {
  activeModelId: string | null;
  currentVersionId: string | null;
}

export function useRegressionPredictionTargetState({
  activeModelId,
  currentVersionId,
}: UseRegressionPredictionTargetStateOptions): RegressionPredictionTargetState {
  const [catalog, setCatalog] = useState<DatasetVersionCatalogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selectedTargetVersionId, setSelectedTargetVersionId] = useState<string | null>(
    currentVersionId,
  );
  const [selectedTarget, setSelectedTarget] = useState<DatasetVersionCatalogItem | null>(null);
  const catalogRequest = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    catalogRequest.cancel();
    setCatalog(null);
    setError(null);
    setIsLoading(false);
    setOffset(0);
    setSelectedTargetVersionId(currentVersionId);
    setSelectedTarget(null);
  }, [activeModelId, catalogRequest, currentVersionId]);

  useEffect(() => {
    if (activeModelId === null || currentVersionId === null) {
      return;
    }

    const request = catalogRequest.begin();
    setIsLoading(true);
    setError(null);
    fetchDatasetVersions(predictionTargetPageSize, offset)
      .then((response) => {
        if (catalogRequest.isCurrent(request)) {
          setCatalog(response);
        }
      })
      .catch((fetchError) => {
        if (catalogRequest.isCurrent(request)) {
          setCatalog(null);
          setError(
            fetchError instanceof Error ? fetchError.message : "dataset_versions_fetch_failed",
          );
        }
      })
      .finally(() => {
        if (catalogRequest.isCurrent(request)) {
          setIsLoading(false);
        }
      });
  }, [activeModelId, catalogRequest, currentVersionId, offset]);

  function handleSelect(versionId: string) {
    setSelectedTargetVersionId(versionId);
    setSelectedTarget(
      versionId === currentVersionId
        ? null
        : (catalog?.versions.find((candidate) => candidate.version_id === versionId) ?? null),
    );
  }

  return {
    catalog,
    error,
    isLoading,
    selectedTarget,
    selectedTargetVersionId,
    onPageChange: (nextOffset) => {
      setOffset(Math.max(0, nextOffset));
    },
    onSelect: handleSelect,
  };
}
