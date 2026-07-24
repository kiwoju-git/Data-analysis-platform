import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchAnalysisRunResult,
  fetchAnalysisRuns,
  type AnalysisResultEnvelope,
  type AnalysisRunListResponse,
  type AnalysisRunState,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

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
  const [offset, setOffset] = useState(0);
  const [methodId, setMethodId] = useState("");
  const [status, setStatus] = useState<AnalysisRunState | "">("succeeded");
  const [resultFilter, setResultFilter] = useState<ReportResultFilter>("available");
  const [staleFilter, setStaleFilter] = useState<ReportStaleFilter>("all");
  const [currentDatasetOnly, setCurrentDatasetOnly] = useState(false);
  const [selectedResult, setSelectedResult] = useState<AnalysisResultEnvelope | null>(null);
  const [selectedResultError, setSelectedResultError] = useState<string | null>(null);
  const [isLoadingResult, setIsLoadingResult] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(
    initialSelectedAnalysisId,
  );
  const listRequest = useRef(createLatestRequestGuard()).current;
  const resultRequest = useRef(createLatestRequestGuard()).current;
  const selectedAnalysisIdRef = useRef(selectedAnalysisId);
  selectedAnalysisIdRef.current = selectedAnalysisId;

  const refresh = useCallback(async () => {
    const request = listRequest.begin();
    setIsLoadingList(true);
    setListError(null);
    try {
      const response = await fetchAnalysisRuns({
        datasetVersionId: currentDatasetOnly ? currentDatasetVersionId : null,
        methodId: methodId === "" ? null : methodId,
        resultAvailable: resultFilter === "all" ? null : resultFilter === "available",
        status: status === "" ? null : status,
        stale: staleFilter === "all" ? null : staleFilter === "stale",
        limit: REPORT_PAGE_SIZE,
        offset,
      });
      if (listRequest.isCurrent(request)) {
        setList(response);
        if (response.returned_count === 0 && offset > 0) {
          setOffset(Math.max(0, offset - REPORT_PAGE_SIZE));
        }
      }
    } catch (error) {
      if (listRequest.isCurrent(request)) {
        setList(null);
        setListError(error instanceof Error ? error.message : "report_center_list_failed");
      }
    } finally {
      if (listRequest.isCurrent(request)) setIsLoadingList(false);
    }
  }, [
    currentDatasetOnly,
    currentDatasetVersionId,
    listRequest,
    methodId,
    offset,
    resultFilter,
    staleFilter,
    status,
  ]);

  const selectAnalysis = useCallback(async (
    analysisId: string,
    reconcileMissing = false,
  ) => {
    const request = resultRequest.begin();
    setSelectedAnalysisId(analysisId);
    setIsLoadingResult(true);
    setSelectedResult(null);
    setSelectedResultError(null);
    try {
      const response = await fetchAnalysisRunResult(analysisId);
      if (resultRequest.isCurrent(request)) {
        setSelectedResult(response);
        updateSelectedAnalysisQuery(analysisId);
      }
    } catch (error) {
      if (resultRequest.isCurrent(request)) {
        const code =
          error instanceof Error ? error.message : "report_center_result_failed";
        if (reconcileMissing && code === "analysis_run_not_found") {
          setSelectedAnalysisId(null);
          setSelectedResult(null);
          setSelectedResultError(null);
          updateSelectedAnalysisQuery(null);
          setNotice(
            "선택했던 결과가 데이터셋 정리 과정에서 함께 삭제되어 목록을 갱신했습니다.",
          );
          void refresh();
        } else {
          setSelectedResultError(code);
        }
      }
    } finally {
      if (resultRequest.isCurrent(request)) setIsLoadingResult(false);
    }
  }, [refresh, resultRequest]);

  useEffect(() => {
    void refresh();
    return () => listRequest.cancel();
  }, [refresh, listRequest]);

  const previousWorkspaceAssetRevisionRef = useRef(workspaceAssetRevision);
  useEffect(() => {
    if (previousWorkspaceAssetRevisionRef.current === workspaceAssetRevision) {
      return;
    }
    previousWorkspaceAssetRevisionRef.current = workspaceAssetRevision;
    void refresh();
    const selectedId = selectedAnalysisIdRef.current;
    if (selectedId !== null) void selectAnalysis(selectedId, true);
  }, [refresh, selectAnalysis, workspaceAssetRevision]);

  useEffect(() => {
    const analysisId = initialSelectedAnalysisId();
    if (analysisId !== null) void selectAnalysis(analysisId);
    return () => resultRequest.cancel();
  }, [resultRequest, selectAnalysis]);

  return {
    currentDatasetOnly,
    isLoadingList,
    isLoadingResult,
    list,
    listError,
    methodId,
    notice,
    offset,
    resultFilter,
    selectedAnalysisId,
    selectedResult,
    selectedResultError,
    staleFilter,
    status,
    onChangeCurrentDatasetOnly: (value: boolean) => { setCurrentDatasetOnly(value); setOffset(0); },
    onChangeMethodId: (value: string) => { setMethodId(value); setOffset(0); },
    onChangeOffset: (value: number) => setOffset(Math.max(0, value)),
    onChangeResultFilter: (value: ReportResultFilter) => { setResultFilter(value); setOffset(0); },
    onChangeStaleFilter: (value: ReportStaleFilter) => { setStaleFilter(value); setOffset(0); },
    onChangeStatus: (value: AnalysisRunState | "") => { setStatus(value); setOffset(0); },
    onRefresh: () => void refresh(),
    onSelectAnalysis: (analysisId: string) => void selectAnalysis(analysisId, true),
    onSelectedAnalysisDeleted: () => {
      resultRequest.cancel();
      setSelectedAnalysisId(null);
      setSelectedResult(null);
      setSelectedResultError(null);
      setIsLoadingResult(false);
      updateSelectedAnalysisQuery(null);
      void refresh();
    },
    onClearNotice: () => setNotice(null),
  };
}

function initialSelectedAnalysisId(): string | null {
  if (typeof window === "undefined") return null;
  return new URL(window.location.href).searchParams.get("analysis_id");
}

function updateSelectedAnalysisQuery(analysisId: string | null): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (analysisId === null) url.searchParams.delete("analysis_id");
  else url.searchParams.set("analysis_id", analysisId);
  window.history.replaceState(null, "", `${url.pathname}${url.search}`);
}
