import { useCallback, useEffect, useRef, useState } from "react";

import {
  deleteStoredAnalysisRun,
  fetchAnalysisRuns,
  fetchAnalysisRunDeletionPreflight,
  type AnalysisRunDeleteResponse,
  type AnalysisRunDeletionPreflightResponse,
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
  const [analysisRunDeletionPreflight, setAnalysisRunDeletionPreflight] =
    useState<AnalysisRunDeletionPreflightResponse | null>(null);
  const [analysisRunDeletion, setAnalysisRunDeletion] =
    useState<AnalysisRunDeleteResponse | null>(null);
  const [analysisRunDeletionError, setAnalysisRunDeletionError] = useState<string | null>(null);
  const [isLoadingAnalysisRunDeletionPreflight, setIsLoadingAnalysisRunDeletionPreflight] =
    useState(false);
  const [isDeletingAnalysisRun, setIsDeletingAnalysisRun] = useState(false);
  const historyRequest = useRef(createLatestRequestGuard()).current;
  const deletionPreflightRequest = useRef(createLatestRequestGuard()).current;
  const deletionRequest = useRef(createLatestRequestGuard()).current;

  const resetAnalysisRunDeletionState = useCallback(() => {
    deletionPreflightRequest.cancel();
    deletionRequest.cancel();
    setAnalysisRunDeletionPreflight(null);
    setAnalysisRunDeletion(null);
    setAnalysisRunDeletionError(null);
    setIsLoadingAnalysisRunDeletionPreflight(false);
    setIsDeletingAnalysisRun(false);
  }, [deletionPreflightRequest, deletionRequest]);

  const resetAnalysisHistoryState = useCallback(() => {
    historyRequest.cancel();
    resetAnalysisRunDeletionState();
    setAnalysisHistory(null);
    setAnalysisHistoryError(null);
    setIsLoadingAnalysisHistory(false);
    setAnalysisHistoryMethodId("");
    setAnalysisHistoryStatus("");
    setAnalysisHistoryStaleFilter("all");
    setAnalysisHistoryResultAvailabilityFilter("all");
    setAnalysisHistoryOffset(0);
  }, [historyRequest, resetAnalysisRunDeletionState]);

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

  async function loadAnalysisRunDeletionPreflight(analysisId: string) {
    deletionRequest.cancel();
    const request = deletionPreflightRequest.begin();
    setIsLoadingAnalysisRunDeletionPreflight(true);
    setAnalysisRunDeletionPreflight(null);
    setAnalysisRunDeletion(null);
    setAnalysisRunDeletionError(null);
    try {
      const response = await fetchAnalysisRunDeletionPreflight(analysisId);
      if (deletionPreflightRequest.isCurrent(request)) {
        setAnalysisRunDeletionPreflight(response);
      }
    } catch (error) {
      if (deletionPreflightRequest.isCurrent(request)) {
        setAnalysisRunDeletionError(
          error instanceof Error ? error.message : "analysis_run_deletion_preflight_failed",
        );
      }
    } finally {
      if (deletionPreflightRequest.isCurrent(request)) {
        setIsLoadingAnalysisRunDeletionPreflight(false);
      }
    }
  }

  async function deleteAnalysisRun(preflight: AnalysisRunDeletionPreflightResponse) {
    deletionPreflightRequest.cancel();
    const request = deletionRequest.begin();
    setIsLoadingAnalysisRunDeletionPreflight(false);
    setIsDeletingAnalysisRun(true);
    setAnalysisRunDeletion(null);
    setAnalysisRunDeletionError(null);
    try {
      const response = await deleteStoredAnalysisRun(preflight.analysis_id, {
        confirmation_analysis_id: preflight.analysis_id,
        expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
      });
      if (!deletionRequest.isCurrent(request)) {
        return;
      }
      setAnalysisRunDeletion(response);
      setAnalysisRunDeletionPreflight(null);
      await refreshAnalysisHistory();
    } catch (error) {
      if (deletionRequest.isCurrent(request)) {
        setAnalysisRunDeletionError(
          error instanceof Error ? error.message : "analysis_run_delete_failed",
        );
      }
    } finally {
      if (deletionRequest.isCurrent(request)) {
        setIsDeletingAnalysisRun(false);
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

  useEffect(() => {
    resetAnalysisRunDeletionState();
  }, [currentDatasetVersionId, resetAnalysisRunDeletionState, resetKey]);

  return {
    analysisHistory,
    analysisHistoryError,
    analysisHistoryMethodId,
    analysisHistoryOffset,
    analysisHistoryResultAvailabilityFilter,
    analysisHistoryStaleFilter,
    analysisHistoryStatus,
    analysisRunDeletion,
    analysisRunDeletionError,
    analysisRunDeletionPreflight,
    isDeletingAnalysisRun,
    isLoadingAnalysisHistory,
    isLoadingAnalysisRunDeletionPreflight,
    onChangeAnalysisHistoryFilters: handleChangeAnalysisHistoryFilters,
    onChangeAnalysisHistoryPage: handleChangeAnalysisHistoryPage,
    onRefreshAnalysisHistory: () => {
      void refreshAnalysisHistory();
    },
    onLoadAnalysisRunDeletionPreflight: (analysisId: string) => {
      void loadAnalysisRunDeletionPreflight(analysisId);
    },
    onDeleteAnalysisRun: (preflight: AnalysisRunDeletionPreflightResponse) => {
      void deleteAnalysisRun(preflight);
    },
    onClearAnalysisRunDeletion: resetAnalysisRunDeletionState,
    resetAnalysisHistoryState,
  };
}
