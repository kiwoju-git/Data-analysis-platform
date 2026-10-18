import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  fetchAnalysisRunResult,
  fetchAnalysisRunStatus,
  fetchAnalysisRuns,
  type AnalysisResultEnvelope,
  type AnalysisRunListResponse,
  type AnalysisRunState,
  type AnalysisRunStatusResponse,
} from "./api";
import { appLocationChangeEvent } from "./browserNavigation";
import { createLatestRequestGuard } from "./latestRequest";
import {
  readReportSelectionQuery,
  reportRequestErrorCode,
  reportSelectionLocation,
  validReportAnalysisId,
} from "./reportCenterQuery";

const REPORT_PAGE_SIZE = 20;

export type ReportStaleFilter = "all" | "fresh" | "stale";
export type ReportResultFilter = "all" | "available" | "unavailable";

export function useReportCenterState(
  currentDatasetVersionId: string | null,
  workspaceAssetRevision = 0,
) {
  const [list, setList] = useState<AnalysisRunListResponse | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [methodId, setMethodId] = useState("");
  const [status, setStatus] = useState<AnalysisRunState | "">("succeeded");
  const [resultFilter, setResultFilter] = useState<ReportResultFilter>("available");
  const [staleFilter, setStaleFilter] = useState<ReportStaleFilter>("all");
  const [currentDatasetOnly, setCurrentDatasetOnly] = useState(false);
  const [selectedResult, setSelectedResult] = useState<AnalysisResultEnvelope | null>(null);
  const [selectedResultError, setSelectedResultError] = useState<string | null>(null);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<AnalysisRunStatusResponse | null>(null);
  const [selectedStatusError, setSelectedStatusError] = useState<string | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);
  const [notice, setNotice] = useState<"report_center_result_removed" | null>(null);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const listRequest = useRef(createLatestRequestGuard()).current;
  const resultRequest = useRef(createLatestRequestGuard()).current;
  const statusRequest = useRef(createLatestRequestGuard()).current;
  const mounted = useRef(true);
  const selectedAnalysisIdRef = useRef<string | null>(null);
  const lastSelectionQuery = useRef<string | undefined>(undefined);

  const effectiveDatasetId = currentDatasetOnly ? currentDatasetVersionId : null;
  const listBlocked = currentDatasetOnly && effectiveDatasetId === null;
  const listScope = JSON.stringify([
    currentDatasetOnly, effectiveDatasetId, methodId, status, resultFilter, staleFilter,
  ]);
  const [pagination, setPagination] = useState({ scope: listScope, offset: 0 });
  const offset = pagination.scope === listScope ? pagination.offset : 0;
  const query = useMemo(() => ({
    datasetVersionId: effectiveDatasetId,
    methodId: methodId === "" ? null : methodId,
    resultAvailable: resultFilter === "all" ? null : resultFilter === "available",
    status: status === "" ? null : status,
    stale: staleFilter === "all" ? null : staleFilter === "stale",
    limit: REPORT_PAGE_SIZE,
    offset,
  }), [effectiveDatasetId, methodId, offset, resultFilter, staleFilter, status]);
  const queryKey = `${listScope}:${offset}`;
  const currentQueryKey = useRef(queryKey);
  currentQueryKey.current = queryKey;

  useEffect(() => {
    if (pagination.scope !== listScope) setPagination({ scope: listScope, offset: 0 });
  }, [listScope, pagination.scope]);

  const refresh = useCallback(async () => {
    if (!mounted.current) return;
    const request = listRequest.begin();
    setList(null);
    setListError(null);
    if (listBlocked) {
      setIsLoadingList(false);
      return;
    }
    const current = () => mounted.current && listRequest.isCurrent(request)
      && currentQueryKey.current === queryKey;
    setIsLoadingList(true);
    try {
      const response = await fetchAnalysisRuns(query);
      if (!current()) return;
      setList(response);
      if (response.returned_count === 0 && query.offset > 0) {
        setPagination({ scope: listScope, offset: Math.max(0, query.offset - REPORT_PAGE_SIZE) });
      }
    } catch (error) {
      if (current()) setListError(reportRequestErrorCode(error, "report_center_list_failed"));
    } finally {
      if (current()) setIsLoadingList(false);
    }
  }, [listBlocked, listRequest, listScope, query, queryKey]);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;

  const clearSelection = useCallback((error: string | null = null) => {
    resultRequest.cancel();
    statusRequest.cancel();
    selectedAnalysisIdRef.current = null;
    setSelectedAnalysisId(null);
    setSelectedResult(null);
    setSelectedResultError(error);
    setIsLoadingResult(false);
    setSelectedStatus(null);
    setSelectedStatusError(null);
    setIsLoadingStatus(false);
  }, [resultRequest, statusRequest]);

  const refreshSelectedStatus = useCallback(async (analysisId: string) => {
    if (!mounted.current || selectedAnalysisIdRef.current !== analysisId) return;
    const request = statusRequest.begin();
    const current = () => mounted.current && statusRequest.isCurrent(request)
      && selectedAnalysisIdRef.current === analysisId;
    setSelectedStatus(null);
    setSelectedStatusError(null);
    setIsLoadingStatus(true);
    try {
      const response = await fetchAnalysisRunStatus(analysisId);
      if (!current()) return;
      if (response.analysis_id !== analysisId) {
        setSelectedStatusError("report_center_result_identity_mismatch");
      } else setSelectedStatus(response);
    } catch (error) {
      if (current()) setSelectedStatusError(reportRequestErrorCode(error, "analysis_status_fetch_failed"));
    } finally {
      if (current()) setIsLoadingStatus(false);
    }
  }, [statusRequest]);

  const writeSelectionQuery = useCallback((analysisId: string | null) => {
    lastSelectionQuery.current = analysisId ?? "absent";
    if (typeof window === "undefined") return;
    window.history.replaceState(
      window.history.state, "", reportSelectionLocation(window.location.href, analysisId),
    );
  }, []);

  const selectAnalysis = useCallback(async (
    requestedId: string,
    writeQuery = true,
    refreshListOnMissing = true,
  ) => {
    if (!mounted.current) return;
    if (!validReportAnalysisId(requestedId)) {
      clearSelection("report_center_analysis_id_invalid");
      return;
    }
    const analysisId = requestedId.toLowerCase();
    const request = resultRequest.begin();
    selectedAnalysisIdRef.current = analysisId;
    setSelectedAnalysisId(analysisId);
    setIsLoadingResult(true);
    setSelectedResult(null);
    setSelectedResultError(null);
    setNotice(null);
    if (writeQuery) writeSelectionQuery(analysisId);
    void refreshSelectedStatus(analysisId);
    const current = () => mounted.current && resultRequest.isCurrent(request)
      && selectedAnalysisIdRef.current === analysisId;
    try {
      const response = await fetchAnalysisRunResult(analysisId);
      if (!current()) return;
      if (response.analysis_id !== analysisId) {
        setSelectedResultError("report_center_result_identity_mismatch");
        return;
      }
      setSelectedResult(response);
    } catch (error) {
      if (!current()) return;
      const code = reportRequestErrorCode(error, "report_center_result_failed");
      if (code === "analysis_run_not_found") {
        clearSelection();
        writeSelectionQuery(null);
        setNotice("report_center_result_removed");
        if (refreshListOnMissing) void refreshRef.current();
      } else setSelectedResultError(code);
    } finally {
      if (current()) setIsLoadingResult(false);
    }
  }, [clearSelection, refreshSelectedStatus, resultRequest, writeSelectionQuery]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      listRequest.cancel();
      resultRequest.cancel();
      statusRequest.cancel();
    };
  }, [listRequest, resultRequest, statusRequest]);

  useEffect(() => {
    void refresh();
    return () => listRequest.cancel();
  }, [refresh, listRequest, workspaceAssetRevision]);

  const previousWorkspaceAssetRevisionRef = useRef(workspaceAssetRevision);
  useEffect(() => {
    if (previousWorkspaceAssetRevisionRef.current === workspaceAssetRevision) return;
    previousWorkspaceAssetRevisionRef.current = workspaceAssetRevision;
    const selectedId = selectedAnalysisIdRef.current;
    if (selectedId !== null) void selectAnalysis(selectedId, false, false);
  }, [selectAnalysis, workspaceAssetRevision]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const syncSelection = () => {
      const selection = readReportSelectionQuery(window.location.href);
      const key = selection.kind === "valid" ? selection.analysisId : selection.kind;
      if (lastSelectionQuery.current === key) return;
      lastSelectionQuery.current = key;
      if (selection.kind === "valid") void selectAnalysis(selection.analysisId, false);
      else clearSelection(selection.kind === "invalid" ? selection.code : null);
    };
    syncSelection();
    window.addEventListener("popstate", syncSelection);
    window.addEventListener(appLocationChangeEvent, syncSelection);
    return () => {
      window.removeEventListener("popstate", syncSelection);
      window.removeEventListener(appLocationChangeEvent, syncSelection);
      resultRequest.cancel();
      lastSelectionQuery.current = undefined;
    };
  }, [clearSelection, resultRequest, selectAnalysis]);

  const changeFilter = (change: () => void) => {
    listRequest.cancel();
    setPagination({ scope: "", offset: 0 });
    change();
  };

  return {
    currentDatasetOnly, isLoadingList, isLoadingResult, list, listError, listBlocked,
    methodId, notice, offset, resultFilter, selectedAnalysisId, selectedResult,
    selectedResultError, staleFilter, status,
    selectedStatus, selectedStatusError, isLoadingStatus,
    onChangeCurrentDatasetOnly: (value: boolean) => {
      if (value !== currentDatasetOnly) changeFilter(() => setCurrentDatasetOnly(value));
    },
    onChangeMethodId: (value: string) => {
      if (value !== methodId) changeFilter(() => setMethodId(value));
    },
    onChangeOffset: (value: number) => {
      const next = Math.max(0, value);
      if (next !== offset) {
        listRequest.cancel();
        setPagination({ scope: listScope, offset: next });
      }
    },
    onChangeResultFilter: (value: ReportResultFilter) => {
      if (value !== resultFilter) changeFilter(() => setResultFilter(value));
    },
    onChangeStaleFilter: (value: ReportStaleFilter) => {
      if (value !== staleFilter) changeFilter(() => setStaleFilter(value));
    },
    onChangeStatus: (value: AnalysisRunState | "") => {
      if (value !== status) changeFilter(() => setStatus(value));
    },
    onRefresh: () => void refresh(),
    onSelectAnalysis: (analysisId: string) => void selectAnalysis(analysisId),
    onRetrySelectedResult: () => {
      const id = selectedAnalysisIdRef.current;
      if (id !== null) void selectAnalysis(id, false);
    },
    onRetrySelectedStatus: () => {
      const id = selectedAnalysisIdRef.current;
      if (id !== null && mounted.current) void refreshSelectedStatus(id);
    },
    onSelectedAnalysisDeleted: (deletedAnalysisId: string) => {
      if (!mounted.current) return;
      if (selectedAnalysisIdRef.current === deletedAnalysisId) {
        clearSelection();
        writeSelectionQuery(null);
      }
      void refreshRef.current();
    },
    onClearNotice: () => setNotice(null),
  };
}
