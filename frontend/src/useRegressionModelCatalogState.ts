import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchRegressionModels,
  type RegressionModelCatalogItem,
  type RegressionModelCatalogResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

const catalogPageSize = 20;

export interface RegressionModelCatalogState {
  catalog: RegressionModelCatalogResponse | null;
  error: string | null;
  isLoading: boolean;
  selectedModel: RegressionModelCatalogItem | null;
  selectedModelId: string | null;
  onPageChange: (offset: number) => void;
  onRefresh: () => void;
  onSelect: (modelId: string | null) => void;
}

export function useRegressionModelCatalogState(
  initialModelId: string | null,
): RegressionModelCatalogState {
  const [catalog, setCatalog] = useState<RegressionModelCatalogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(initialModelId);
  const requestGuard = useRef(createLatestRequestGuard()).current;
  const [refreshRevision, setRefreshRevision] = useState(0);

  useEffect(() => {
    setSelectedModelId(initialModelId);
  }, [initialModelId]);

  const load = useCallback(async () => {
    const request = requestGuard.begin();
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchRegressionModels(offset, catalogPageSize);
      if (requestGuard.isCurrent(request)) setCatalog(response);
    } catch (loadError) {
      if (requestGuard.isCurrent(request)) {
        setCatalog(null);
        setError(
          loadError instanceof Error ? loadError.message : "regression_model_catalog_failed",
        );
      }
    } finally {
      if (requestGuard.isCurrent(request)) setIsLoading(false);
    }
  }, [offset, requestGuard]);

  useEffect(() => {
    void load();
    return () => requestGuard.cancel();
  }, [load, refreshRevision, requestGuard]);

  return {
    catalog,
    error,
    isLoading,
    selectedModel:
      catalog?.models.find((item) => item.model_id === selectedModelId) ?? null,
    selectedModelId,
    onPageChange: (nextOffset) => setOffset(Math.max(0, nextOffset)),
    onRefresh: () => setRefreshRevision((value) => value + 1),
    onSelect: setSelectedModelId,
  };
}
