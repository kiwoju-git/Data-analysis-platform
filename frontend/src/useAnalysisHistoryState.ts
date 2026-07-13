import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchAnalysisRuns,
  type AnalysisRunListResponse,
  type AnalysisRunState,
} from "./api";
import type {
  AnalysisHistoryResultAvailabilityFilter,
  AnalysisHistoryStaleFilter,
} from "./analysisWorkbenchTypes";
import { createLatestRequestGuard } from "./latestRequest";

const ANALYSIS_HISTORY_PAGE_SIZE = 20;

interface AnalysisHistoryFilters {
  methodId: string;
  resultAvailability: AnalysisHistoryResultAvailabilityFilter;
  stale: AnalysisHistoryStaleFilter;
  status: AnalysisRunState | "";
}

interface UseAnalysisHistoryStateOptions {
  currentDatasetVersionId: string | null;
  refreshKey: string | null;
  resetKey: number;
}

function historyStaleFilterValue(filter: AnalysisHistoryStaleFilter): boolean | null {
  if (filter === "stale") {
    return true;
  }
  if (filter === "fresh") {
    return false;
  }
  return null;
}

function historyResultAvailabilityFilterValue(
  filter: AnalysisHistoryResultAvailabilityFilter,
): boolean | null {
  if (filter === "available") {
    return true;
  }
  if (filter === "unavailable") {
    return false;
  }
  return null;
}

function historyStatusFilterValue(status: AnalysisRunState | ""): AnalysisRunState | null {
  return status === "" ? null : status;
}

export function useAnalysisHistoryState({
  currentDatasetVersionId,
  refreshKey,
  resetKey,
}: UseAnalysisHistoryStateOptions) {
  const [analysisHistory, setAnalysisHistory] = useState<AnalysisRunListResponse | null>(null);
  const [analysisHistoryError, setAnalysisHistoryError] = useState<string | null>(null);
  const [isLoadingAnalysisHistory, setIsLoadingAnalysisHistory] = useState(false);
  const [analysisHistoryMethodId, setAnalysisHistoryMethodId] = useState("");
  const [analysisHistoryStatus, setAnalysisHistoryStatus] = useState<AnalysisRunState | "">("");
  const [analysisHistoryStaleFilter, setAnalysisHistoryStaleFilter] =
    useState<AnalysisHistoryStaleFilter>("all");
  const [analysisHistoryResultAvailabilityFilter, setAnalysisHistoryResultAvailabilityFilter] =
    useState<AnalysisHistoryResultAvailabilityFilter>("all");
  const [analysisHistoryOffset, setAnalysisHistoryOffset] = useState(0);
  const historyRequest = useRef(createLatestRequestGuard()).current;

  const resetAnalysisHistoryState = useCallback(() => {
    historyRequest.cancel();
    setAnalysisHistory(null);
    setAnalysisHistoryError(null);
    setIsLoadingAnalysisHistory(false);
    setAnalysisHistoryMethodId("");
    setAnalysisHistoryStatus("");
    setAnalysisHistoryStaleFilter("all");
    setAnalysisHistoryResultAvailabilityFilter("all");
    setAnalysisHistoryOffset(0);
  }, [historyRequest]);

  async function refreshAnalysisHistory() {
    if (currentDatasetVersionId === null) {
      historyRequest.cancel();
      setAnalysisHistory(null);
      setAnalysisHistoryError(null);
      setIsLoadingAnalysisHistory(false);
      return;
    }

    const request = historyRequest.begin();
    setIsLoadingAnalysisHistory(true);
    setAnalysisHistoryError(null);
    try {
      const response = await fetchAnalysisRuns({
        datasetVersionId: currentDatasetVersionId,
        methodId: analysisHistoryMethodId.length > 0 ? analysisHistoryMethodId : null,
        status: historyStatusFilterValue(analysisHistoryStatus),
        stale: historyStaleFilterValue(analysisHistoryStaleFilter),
        resultAvailable: historyResultAvailabilityFilterValue(
          analysisHistoryResultAvailabilityFilter,
        ),
        limit: ANALYSIS_HISTORY_PAGE_SIZE,
        offset: analysisHistoryOffset,
      });
      if (historyRequest.isCurrent(request)) {
        setAnalysisHistory(response);
      }
    } catch (error) {
      if (historyRequest.isCurrent(request)) {
        setAnalysisHistory(null);
        setAnalysisHistoryError(
          error instanceof Error ? error.message : "analysis_history_fetch_failed",
        );
      }
    } finally {
      if (historyRequest.isCurrent(request)) {
        setIsLoadingAnalysisHistory(false);
      }
    }
  }

  function handleChangeAnalysisHistoryFilters({
    methodId,
    resultAvailability,
    stale,
    status,
  }: AnalysisHistoryFilters) {
    setAnalysisHistoryMethodId(methodId);
    setAnalysisHistoryStatus(status);
    setAnalysisHistoryStaleFilter(stale);
    setAnalysisHistoryResultAvailabilityFilter(resultAvailability);
    setAnalysisHistoryOffset(0);
  }

  function handleChangeAnalysisHistoryPage(nextOffset: number) {
    setAnalysisHistoryOffset(Math.max(0, nextOffset));
  }

  useEffect(() => {
    if (currentDatasetVersionId === null) {
      resetAnalysisHistoryState();
      return;
    }

    const request = historyRequest.begin();
    setIsLoadingAnalysisHistory(true);
    fetchAnalysisRuns({
      datasetVersionId: currentDatasetVersionId,
      methodId: analysisHistoryMethodId.length > 0 ? analysisHistoryMethodId : null,
      status: historyStatusFilterValue(analysisHistoryStatus),
      stale: historyStaleFilterValue(analysisHistoryStaleFilter),
      resultAvailable: historyResultAvailabilityFilterValue(
        analysisHistoryResultAvailabilityFilter,
      ),
      limit: ANALYSIS_HISTORY_PAGE_SIZE,
      offset: analysisHistoryOffset,
    })
      .then((response) => {
        if (historyRequest.isCurrent(request)) {
          setAnalysisHistory(response);
          setAnalysisHistoryError(null);
        }
      })
      .catch((error) => {
        if (historyRequest.isCurrent(request)) {
          setAnalysisHistory(null);
          setAnalysisHistoryError(
            error instanceof Error ? error.message : "analysis_history_fetch_failed",
          );
        }
      })
      .finally(() => {
        if (historyRequest.isCurrent(request)) {
          setIsLoadingAnalysisHistory(false);
        }
      });

    return () => {
      historyRequest.cancel(request);
    };
  }, [
    analysisHistoryMethodId,
    analysisHistoryOffset,
    analysisHistoryResultAvailabilityFilter,
    analysisHistoryStaleFilter,
    analysisHistoryStatus,
    currentDatasetVersionId,
    historyRequest,
    refreshKey,
    resetAnalysisHistoryState,
    resetKey,
  ]);

  return {
    analysisHistory,
    analysisHistoryError,
    analysisHistoryMethodId,
    analysisHistoryOffset,
    analysisHistoryResultAvailabilityFilter,
    analysisHistoryStaleFilter,
    analysisHistoryStatus,
    isLoadingAnalysisHistory,
    onChangeAnalysisHistoryFilters: handleChangeAnalysisHistoryFilters,
    onChangeAnalysisHistoryPage: handleChangeAnalysisHistoryPage,
    onRefreshAnalysisHistory: () => {
      void refreshAnalysisHistory();
    },
    resetAnalysisHistoryState,
  };
}
