import { useCallback, useEffect, useRef, useState } from "react";

import { fetchBayesianStudies, type BayesianStudyListResponse } from "../../../api";
import { createLatestRequestGuard } from "../../../latestRequest";
import {
  BAYESIAN_CATALOG_PAGE_SIZE,
  bayesianErrorCode,
} from "../bayesianDisplay";

export function useBayesianStudyCatalogState(initialStudyId: string | null) {
  const [catalog, setCatalog] = useState<BayesianStudyListResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [selectedStudyId, setSelectedStudyId] = useState(initialStudyId);
  const [refreshRevision, setRefreshRevision] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const guard = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    const request = guard.begin();
    setIsLoading(true);
    setError(null);
    void fetchBayesianStudies(offset, BAYESIAN_CATALOG_PAGE_SIZE)
      .then((response) => {
        if (guard.isCurrent(request)) setCatalog(response);
      })
      .catch((caught: unknown) => {
        if (guard.isCurrent(request)) setError(bayesianErrorCode(caught));
      })
      .finally(() => {
        if (guard.isCurrent(request)) setIsLoading(false);
      });
    return () => guard.cancel();
  }, [guard, offset, refreshRevision]);

  const onRefresh = useCallback(() => {
    setRefreshRevision((current) => current + 1);
  }, []);

  const onSelect = useCallback((studyId: string | null) => {
    setSelectedStudyId(studyId);
  }, []);

  const onPageChange = useCallback((nextOffset: number) => {
    setOffset(Math.max(0, nextOffset));
  }, []);

  const onResetToFirstPage = useCallback(() => {
    setOffset(0);
    setRefreshRevision((current) => current + 1);
  }, []);

  const selectedSummary =
    catalog?.items.find((item) => item.study_id === selectedStudyId) ?? null;

  return {
    catalog,
    error,
    isLoading,
    offset,
    onPageChange,
    onRefresh,
    onResetToFirstPage,
    onSelect,
    selectedStudyId,
    selectedSummary,
  };
}
