import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchResponseSurfaceAnalysisCatalog,
  type DoeResponseSurfaceAnalysisCatalogItem,
  type DoeResponseSurfaceAnalysisCatalogResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

const catalogPageSize = 20;

export interface ResponseSurfaceAnalysisCatalogState {
  catalog: DoeResponseSurfaceAnalysisCatalogResponse | null;
  error: string | null;
  isLoading: boolean;
  selectedSource: DoeResponseSurfaceAnalysisCatalogItem | null;
  selectedAnalysisId: string | null;
  selectedDesignId: string | null;
  onPageChange: (offset: number) => void;
  onRefresh: () => void;
  onSelect: (designId: string | null, analysisId: string | null) => void;
}

export function useResponseSurfaceAnalysisCatalogState(
  initialDesignId: string | null,
  initialAnalysisId: string | null,
): ResponseSurfaceAnalysisCatalogState {
  const [catalog, setCatalog] =
    useState<DoeResponseSurfaceAnalysisCatalogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selectedDesignId, setSelectedDesignId] = useState<string | null>(initialDesignId);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(initialAnalysisId);
  const [refreshRevision, setRefreshRevision] = useState(0);
  const requestGuard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    setSelectedDesignId(initialDesignId);
    setSelectedAnalysisId(initialAnalysisId);
  }, [initialAnalysisId, initialDesignId]);

  const load = useCallback(async () => {
    const request = requestGuard.begin();
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchResponseSurfaceAnalysisCatalog(offset, catalogPageSize);
      if (requestGuard.isCurrent(request)) setCatalog(response);
    } catch (loadError) {
      if (requestGuard.isCurrent(request)) {
        setCatalog(null);
        setError(
          loadError instanceof Error ? loadError.message : "doe_rsm_analysis_catalog_failed",
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
    selectedSource:
      catalog?.analyses.find(
        (item) =>
          item.analysis_id === selectedAnalysisId && item.design_id === selectedDesignId,
      ) ?? null,
    selectedAnalysisId,
    selectedDesignId,
    onPageChange: (nextOffset) => setOffset(Math.max(0, nextOffset)),
    onRefresh: () => setRefreshRevision((value) => value + 1),
    onSelect: (designId, analysisId) => {
      setSelectedDesignId(designId);
      setSelectedAnalysisId(analysisId);
    },
  };
}
