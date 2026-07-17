import { useCallback, useEffect, useRef, useState } from "react";

import {
  createAnalysisResultCsvExport,
  createAnalysisResultHtmlReport,
  createAnalysisResultJsonExport,
  deleteAnalysisResultExport,
  downloadAnalysisResultExport,
  fetchAnalysisResultExportDeletionPreflight,
  fetchAnalysisResultExports,
  type AnalysisResultCsvExportResponse,
  type AnalysisResultExportListResponse,
  type AnalysisResultExportDeleteResponse,
  type AnalysisResultExportDeletionPreflightResponse,
  type AnalysisResultHtmlReportResponse,
  type AnalysisResultJsonExportResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

interface UseAnalysisExportStateOptions {
  currentAnalysisId: string | null;
  currentDatasetVersionId: string | null;
  resetKey: number;
}

export function useAnalysisExportState({
  currentAnalysisId,
  currentDatasetVersionId,
  resetKey,
}: UseAnalysisExportStateOptions) {
  const [analysisResultJsonExport, setAnalysisResultJsonExport] =
    useState<AnalysisResultJsonExportResponse | null>(null);
  const [analysisResultJsonExportError, setAnalysisResultJsonExportError] = useState<
    string | null
  >(null);
  const [isCreatingAnalysisResultJsonExport, setIsCreatingAnalysisResultJsonExport] =
    useState(false);
  const [analysisResultCsvExport, setAnalysisResultCsvExport] =
    useState<AnalysisResultCsvExportResponse | null>(null);
  const [analysisResultCsvExportError, setAnalysisResultCsvExportError] = useState<string | null>(
    null,
  );
  const [isCreatingAnalysisResultCsvExport, setIsCreatingAnalysisResultCsvExport] =
    useState(false);
  const [analysisResultHtmlReport, setAnalysisResultHtmlReport] =
    useState<AnalysisResultHtmlReportResponse | null>(null);
  const [analysisResultHtmlReportError, setAnalysisResultHtmlReportError] = useState<
    string | null
  >(null);
  const [isCreatingAnalysisResultHtmlReport, setIsCreatingAnalysisResultHtmlReport] =
    useState(false);
  const [analysisResultExportDownloadError, setAnalysisResultExportDownloadError] = useState<
    string | null
  >(null);
  const [isDownloadingAnalysisResultExport, setIsDownloadingAnalysisResultExport] =
    useState(false);
  const [analysisResultExportList, setAnalysisResultExportList] =
    useState<AnalysisResultExportListResponse | null>(null);
  const [analysisResultExportListError, setAnalysisResultExportListError] = useState<string | null>(
    null,
  );
  const [isLoadingAnalysisResultExportList, setIsLoadingAnalysisResultExportList] =
    useState(false);
  const [analysisResultExportDeletionPreflight, setAnalysisResultExportDeletionPreflight] =
    useState<AnalysisResultExportDeletionPreflightResponse | null>(null);
  const [analysisResultExportDeletion, setAnalysisResultExportDeletion] =
    useState<AnalysisResultExportDeleteResponse | null>(null);
  const [analysisResultExportDeletionError, setAnalysisResultExportDeletionError] = useState<
    string | null
  >(null);
  const [isLoadingAnalysisResultExportDeletionPreflight, setIsLoadingAnalysisResultExportDeletionPreflight] =
    useState(false);
  const [isDeletingAnalysisResultExport, setIsDeletingAnalysisResultExport] = useState(false);
  const exportListRequest = useRef(createLatestRequestGuard()).current;
  const jsonExportRequest = useRef(createLatestRequestGuard()).current;
  const csvExportRequest = useRef(createLatestRequestGuard()).current;
  const htmlReportRequest = useRef(createLatestRequestGuard()).current;
  const exportDownloadRequest = useRef(createLatestRequestGuard()).current;
  const exportDeletionPreflightRequest = useRef(createLatestRequestGuard()).current;
  const exportDeletionRequest = useRef(createLatestRequestGuard()).current;

  const cancelAnalysisExportRequests = useCallback(() => {
    exportListRequest.cancel();
    jsonExportRequest.cancel();
    csvExportRequest.cancel();
    htmlReportRequest.cancel();
    exportDownloadRequest.cancel();
    exportDeletionPreflightRequest.cancel();
    exportDeletionRequest.cancel();
  }, [
    csvExportRequest,
    exportDownloadRequest,
    exportDeletionPreflightRequest,
    exportDeletionRequest,
    exportListRequest,
    htmlReportRequest,
    jsonExportRequest,
  ]);

  const resetAnalysisExportState = useCallback(() => {
    cancelAnalysisExportRequests();
    setAnalysisResultJsonExport(null);
    setAnalysisResultJsonExportError(null);
    setAnalysisResultCsvExport(null);
    setAnalysisResultCsvExportError(null);
    setAnalysisResultHtmlReport(null);
    setAnalysisResultHtmlReportError(null);
    setAnalysisResultExportDownloadError(null);
    setAnalysisResultExportList(null);
    setAnalysisResultExportListError(null);
    setIsCreatingAnalysisResultJsonExport(false);
    setIsCreatingAnalysisResultCsvExport(false);
    setIsCreatingAnalysisResultHtmlReport(false);
    setIsDownloadingAnalysisResultExport(false);
    setIsLoadingAnalysisResultExportList(false);
    setAnalysisResultExportDeletionPreflight(null);
    setAnalysisResultExportDeletion(null);
    setAnalysisResultExportDeletionError(null);
    setIsLoadingAnalysisResultExportDeletionPreflight(false);
    setIsDeletingAnalysisResultExport(false);
  }, [cancelAnalysisExportRequests]);

  function clearAnalysisExportErrors() {
    setAnalysisResultJsonExportError(null);
    setAnalysisResultCsvExportError(null);
    setAnalysisResultHtmlReportError(null);
    setAnalysisResultExportDownloadError(null);
    setAnalysisResultExportDeletionError(null);
  }

  const refreshAnalysisResultExports = useCallback(async (analysisId: string) => {
    const request = exportListRequest.begin();
    setIsLoadingAnalysisResultExportList(true);
    setAnalysisResultExportListError(null);
    try {
      const response = await fetchAnalysisResultExports(analysisId);
      if (exportListRequest.isCurrent(request)) {
        setAnalysisResultExportList(response);
      }
    } catch (error) {
      if (exportListRequest.isCurrent(request)) {
        setAnalysisResultExportList(null);
        setAnalysisResultExportListError(
          error instanceof Error ? error.message : "analysis_result_exports_fetch_failed",
        );
      }
    } finally {
      if (exportListRequest.isCurrent(request)) {
        setIsLoadingAnalysisResultExportList(false);
      }
    }
  }, [exportListRequest]);

  async function createJsonExport(analysisId: string) {
    const request = jsonExportRequest.begin();
    setIsCreatingAnalysisResultJsonExport(true);
    setAnalysisResultJsonExportError(null);
    setAnalysisResultExportDownloadError(null);
    try {
      const response = await createAnalysisResultJsonExport(analysisId);
      if (jsonExportRequest.isCurrent(request)) {
        setAnalysisResultJsonExport(response);
        await refreshAnalysisResultExports(analysisId);
      }
    } catch (error) {
      if (jsonExportRequest.isCurrent(request)) {
        setAnalysisResultJsonExport(null);
        setAnalysisResultJsonExportError(
          error instanceof Error ? error.message : "analysis_result_json_export_failed",
        );
      }
    } finally {
      if (jsonExportRequest.isCurrent(request)) {
        setIsCreatingAnalysisResultJsonExport(false);
      }
    }
  }

  async function createCsvExport(analysisId: string) {
    const request = csvExportRequest.begin();
    setIsCreatingAnalysisResultCsvExport(true);
    setAnalysisResultCsvExportError(null);
    setAnalysisResultExportDownloadError(null);
    try {
      const response = await createAnalysisResultCsvExport(analysisId);
      if (csvExportRequest.isCurrent(request)) {
        setAnalysisResultCsvExport(response);
        await refreshAnalysisResultExports(analysisId);
      }
    } catch (error) {
      if (csvExportRequest.isCurrent(request)) {
        setAnalysisResultCsvExport(null);
        setAnalysisResultCsvExportError(
          error instanceof Error ? error.message : "analysis_result_csv_export_failed",
        );
      }
    } finally {
      if (csvExportRequest.isCurrent(request)) {
        setIsCreatingAnalysisResultCsvExport(false);
      }
    }
  }

  async function createHtmlReport(analysisId: string) {
    const request = htmlReportRequest.begin();
    setIsCreatingAnalysisResultHtmlReport(true);
    setAnalysisResultHtmlReportError(null);
    setAnalysisResultExportDownloadError(null);
    try {
      const response = await createAnalysisResultHtmlReport(analysisId);
      if (htmlReportRequest.isCurrent(request)) {
        setAnalysisResultHtmlReport(response);
        await refreshAnalysisResultExports(analysisId);
      }
    } catch (error) {
      if (htmlReportRequest.isCurrent(request)) {
        setAnalysisResultHtmlReport(null);
        setAnalysisResultHtmlReportError(
          error instanceof Error ? error.message : "analysis_result_html_report_failed",
        );
      }
    } finally {
      if (htmlReportRequest.isCurrent(request)) {
        setIsCreatingAnalysisResultHtmlReport(false);
      }
    }
  }

  async function downloadExport(analysisId: string, exportId: string) {
    const request = exportDownloadRequest.begin();
    setIsDownloadingAnalysisResultExport(true);
    setAnalysisResultExportDownloadError(null);
    try {
      await downloadAnalysisResultExport(analysisId, exportId);
    } catch (error) {
      if (exportDownloadRequest.isCurrent(request)) {
        setAnalysisResultExportDownloadError(
          error instanceof Error ? error.message : "analysis_result_export_download_failed",
        );
      }
    } finally {
      if (exportDownloadRequest.isCurrent(request)) {
        setIsDownloadingAnalysisResultExport(false);
      }
    }
  }

  async function loadExportDeletionPreflight(analysisId: string, exportId: string) {
    const request = exportDeletionPreflightRequest.begin();
    setIsLoadingAnalysisResultExportDeletionPreflight(true);
    setAnalysisResultExportDeletionPreflight(null);
    setAnalysisResultExportDeletion(null);
    setAnalysisResultExportDeletionError(null);
    try {
      const response = await fetchAnalysisResultExportDeletionPreflight(
        analysisId,
        exportId,
      );
      if (exportDeletionPreflightRequest.isCurrent(request)) {
        setAnalysisResultExportDeletionPreflight(response);
      }
    } catch (error) {
      if (exportDeletionPreflightRequest.isCurrent(request)) {
        setAnalysisResultExportDeletionError(
          error instanceof Error
            ? error.message
            : "analysis_export_deletion_preflight_failed",
        );
      }
    } finally {
      if (exportDeletionPreflightRequest.isCurrent(request)) {
        setIsLoadingAnalysisResultExportDeletionPreflight(false);
      }
    }
  }

  async function deleteExport(preflight: AnalysisResultExportDeletionPreflightResponse) {
    const request = exportDeletionRequest.begin();
    setIsDeletingAnalysisResultExport(true);
    setAnalysisResultExportDeletionError(null);
    try {
      const response = await deleteAnalysisResultExport(
        preflight.analysis_id,
        preflight.export_id,
        {
          confirmation_analysis_id: preflight.analysis_id,
          confirmation_export_id: preflight.export_id,
          expected_deletion_manifest_sha256: preflight.deletion_manifest_sha256,
        },
      );
      if (!exportDeletionRequest.isCurrent(request)) return;
      setAnalysisResultExportDeletion(response);
      setAnalysisResultExportDeletionPreflight(null);
      setAnalysisResultJsonExport((current) =>
        current?.export_id === preflight.export_id ? null : current,
      );
      setAnalysisResultCsvExport((current) =>
        current?.export_id === preflight.export_id ? null : current,
      );
      setAnalysisResultHtmlReport((current) =>
        current?.export_id === preflight.export_id ? null : current,
      );
      await refreshAnalysisResultExports(preflight.analysis_id);
    } catch (error) {
      if (exportDeletionRequest.isCurrent(request)) {
        setAnalysisResultExportDeletionError(
          error instanceof Error ? error.message : "analysis_export_delete_failed",
        );
      }
    } finally {
      if (exportDeletionRequest.isCurrent(request)) {
        setIsDeletingAnalysisResultExport(false);
      }
    }
  }

  useEffect(() => {
    resetAnalysisExportState();
    if (currentAnalysisId !== null) {
      void refreshAnalysisResultExports(currentAnalysisId);
    }
    return cancelAnalysisExportRequests;
  }, [
    cancelAnalysisExportRequests,
    currentAnalysisId,
    currentDatasetVersionId,
    refreshAnalysisResultExports,
    resetAnalysisExportState,
    resetKey,
  ]);

  return {
    analysisResultCsvExport,
    analysisResultCsvExportError,
    analysisResultExportDownloadError,
    analysisResultExportDeletion,
    analysisResultExportDeletionError,
    analysisResultExportDeletionPreflight,
    analysisResultExportList,
    analysisResultExportListError,
    analysisResultHtmlReport,
    analysisResultHtmlReportError,
    analysisResultJsonExport,
    analysisResultJsonExportError,
    isCreatingAnalysisResultCsvExport,
    isCreatingAnalysisResultHtmlReport,
    isCreatingAnalysisResultJsonExport,
    isDownloadingAnalysisResultExport,
    isDeletingAnalysisResultExport,
    isLoadingAnalysisResultExportList,
    isLoadingAnalysisResultExportDeletionPreflight,
    clearAnalysisExportErrors,
    onCreateAnalysisResultCsvExport: (analysisId: string) => {
      void createCsvExport(analysisId);
    },
    onCreateAnalysisResultHtmlReport: (analysisId: string) => {
      void createHtmlReport(analysisId);
    },
    onCreateAnalysisResultJsonExport: (analysisId: string) => {
      void createJsonExport(analysisId);
    },
    onDownloadAnalysisResultExport: (analysisId: string, exportId: string) => {
      void downloadExport(analysisId, exportId);
    },
    onLoadAnalysisResultExportDeletionPreflight: (analysisId: string, exportId: string) => {
      void loadExportDeletionPreflight(analysisId, exportId);
    },
    onDeleteAnalysisResultExport: (preflight: AnalysisResultExportDeletionPreflightResponse) => {
      void deleteExport(preflight);
    },
    onClearAnalysisResultExportDeletion: () => {
      exportDeletionPreflightRequest.cancel();
      setAnalysisResultExportDeletionPreflight(null);
      setAnalysisResultExportDeletionError(null);
      setIsLoadingAnalysisResultExportDeletionPreflight(false);
    },
    onRefreshAnalysisResultExports: refreshAnalysisResultExports,
    resetAnalysisExportState,
  };
}
