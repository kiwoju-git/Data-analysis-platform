import { useEffect, useState } from "react";

import {
  createAnalysisResultCsvExport,
  createAnalysisResultHtmlReport,
  createAnalysisResultJsonExport,
  downloadAnalysisResultExport,
  fetchAnalysisResultExports,
  type AnalysisResultCsvExportResponse,
  type AnalysisResultExportListResponse,
  type AnalysisResultHtmlReportResponse,
  type AnalysisResultJsonExportResponse,
} from "./api";

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

  function resetAnalysisExportState() {
    setAnalysisResultJsonExport(null);
    setAnalysisResultJsonExportError(null);
    setAnalysisResultCsvExport(null);
    setAnalysisResultCsvExportError(null);
    setAnalysisResultHtmlReport(null);
    setAnalysisResultHtmlReportError(null);
    setAnalysisResultExportDownloadError(null);
    setAnalysisResultExportList(null);
    setAnalysisResultExportListError(null);
  }

  function clearAnalysisExportErrors() {
    setAnalysisResultJsonExportError(null);
    setAnalysisResultCsvExportError(null);
    setAnalysisResultHtmlReportError(null);
    setAnalysisResultExportDownloadError(null);
  }

  async function refreshAnalysisResultExports(analysisId: string) {
    setIsLoadingAnalysisResultExportList(true);
    setAnalysisResultExportListError(null);
    try {
      const response = await fetchAnalysisResultExports(analysisId);
      setAnalysisResultExportList(response);
    } catch (error) {
      setAnalysisResultExportList(null);
      setAnalysisResultExportListError(
        error instanceof Error ? error.message : "analysis_result_exports_fetch_failed",
      );
    } finally {
      setIsLoadingAnalysisResultExportList(false);
    }
  }

  async function createJsonExport(analysisId: string) {
    setIsCreatingAnalysisResultJsonExport(true);
    setAnalysisResultJsonExportError(null);
    setAnalysisResultExportDownloadError(null);
    try {
      const response = await createAnalysisResultJsonExport(analysisId);
      setAnalysisResultJsonExport(response);
      await refreshAnalysisResultExports(analysisId);
    } catch (error) {
      setAnalysisResultJsonExport(null);
      setAnalysisResultJsonExportError(
        error instanceof Error ? error.message : "analysis_result_json_export_failed",
      );
    } finally {
      setIsCreatingAnalysisResultJsonExport(false);
    }
  }

  async function createCsvExport(analysisId: string) {
    setIsCreatingAnalysisResultCsvExport(true);
    setAnalysisResultCsvExportError(null);
    setAnalysisResultExportDownloadError(null);
    try {
      const response = await createAnalysisResultCsvExport(analysisId);
      setAnalysisResultCsvExport(response);
      await refreshAnalysisResultExports(analysisId);
    } catch (error) {
      setAnalysisResultCsvExport(null);
      setAnalysisResultCsvExportError(
        error instanceof Error ? error.message : "analysis_result_csv_export_failed",
      );
    } finally {
      setIsCreatingAnalysisResultCsvExport(false);
    }
  }

  async function createHtmlReport(analysisId: string) {
    setIsCreatingAnalysisResultHtmlReport(true);
    setAnalysisResultHtmlReportError(null);
    setAnalysisResultExportDownloadError(null);
    try {
      const response = await createAnalysisResultHtmlReport(analysisId);
      setAnalysisResultHtmlReport(response);
      await refreshAnalysisResultExports(analysisId);
    } catch (error) {
      setAnalysisResultHtmlReport(null);
      setAnalysisResultHtmlReportError(
        error instanceof Error ? error.message : "analysis_result_html_report_failed",
      );
    } finally {
      setIsCreatingAnalysisResultHtmlReport(false);
    }
  }

  async function downloadExport(analysisId: string, exportId: string) {
    setIsDownloadingAnalysisResultExport(true);
    setAnalysisResultExportDownloadError(null);
    try {
      await downloadAnalysisResultExport(analysisId, exportId);
    } catch (error) {
      setAnalysisResultExportDownloadError(
        error instanceof Error ? error.message : "analysis_result_export_download_failed",
      );
    } finally {
      setIsDownloadingAnalysisResultExport(false);
    }
  }

  useEffect(() => {
    resetAnalysisExportState();
    if (currentAnalysisId !== null) {
      void refreshAnalysisResultExports(currentAnalysisId);
    }
  }, [currentAnalysisId, currentDatasetVersionId, resetKey]);

  return {
    analysisResultCsvExport,
    analysisResultCsvExportError,
    analysisResultExportDownloadError,
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
    isLoadingAnalysisResultExportList,
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
    onRefreshAnalysisResultExports: refreshAnalysisResultExports,
    resetAnalysisExportState,
  };
}
