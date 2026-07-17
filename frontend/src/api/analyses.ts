import {
  apiErrorCode,
  fetchApi,
  filenameFromContentDisposition,
  triggerBrowserDownload,
} from "./client";
import { apiRoutes, type AnalysisRunsRouteParams } from "./routes";
import type {
  AnalysisMethodListResponse,
  AnalysisResultCsvExportResponse,
  AnalysisResultEnvelope,
  AnalysisResultExportListResponse,
  AnalysisResultExportDeleteRequest,
  AnalysisResultExportDeleteResponse,
  AnalysisResultExportDeletionPreflightResponse,
  AnalysisResultHtmlReportResponse,
  AnalysisResultJsonExportResponse,
  AnalysisRunDeleteRequest,
  AnalysisRunDeleteResponse,
  AnalysisRunComparisonResponse,
  AnalysisRunDeletionPreflightResponse,
  AnalysisRunListResponse,
  AnalysisRunRequest,
} from "./types";

export async function fetchAnalysisMethods(
  signal?: AbortSignal,
): Promise<AnalysisMethodListResponse> {
  const response = await fetchApi(apiRoutes.analysisMethods(), {
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_methods_failed"));
  }

  return (await response.json()) as AnalysisMethodListResponse;
}

export async function fetchAnalysisRuns({
  datasetVersionId,
  methodId,
  resultAvailable,
  limit = 50,
  offset = 0,
  stale,
  status,
}: AnalysisRunsRouteParams = {}): Promise<AnalysisRunListResponse> {
  const response = await fetchApi(apiRoutes.analysisRuns({
    datasetVersionId,
    methodId,
    resultAvailable,
    limit,
    offset,
    stale,
    status,
  }), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_history_fetch_failed"));
  }

  return (await response.json()) as AnalysisRunListResponse;
}

export async function fetchAnalysisRunComparison(
  leftAnalysisId: string,
  rightAnalysisId: string,
): Promise<AnalysisRunComparisonResponse> {
  const response = await fetchApi(apiRoutes.analysisRunComparison(leftAnalysisId, rightAnalysisId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_comparison_failed"));
  }

  return (await response.json()) as AnalysisRunComparisonResponse;
}

export async function createAnalysisRun(
  request: AnalysisRunRequest,
): Promise<AnalysisResultEnvelope> {
  const response = await fetchApi(apiRoutes.analysisRunsBase(), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_run_failed"));
  }

  return (await response.json()) as AnalysisResultEnvelope;
}

export async function fetchAnalysisRunResult(analysisId: string): Promise<AnalysisResultEnvelope> {
  const response = await fetchApi(apiRoutes.analysisRunResult(analysisId), {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_result_fetch_failed"));
  }

  return (await response.json()) as AnalysisResultEnvelope;
}

export async function fetchAnalysisRunDeletionPreflight(
  analysisId: string,
): Promise<AnalysisRunDeletionPreflightResponse> {
  const response = await fetchApi(apiRoutes.analysisRunDeletionPreflight(analysisId), {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(
      await apiErrorCode(response, "analysis_run_deletion_preflight_failed"),
    );
  }
  return (await response.json()) as AnalysisRunDeletionPreflightResponse;
}

export async function deleteStoredAnalysisRun(
  analysisId: string,
  request: AnalysisRunDeleteRequest,
): Promise<AnalysisRunDeleteResponse> {
  const response = await fetchApi(apiRoutes.analysisRunDelete(analysisId), {
    method: "DELETE",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_run_delete_failed"));
  }
  return (await response.json()) as AnalysisRunDeleteResponse;
}

export async function createAnalysisResultJsonExport(
  analysisId: string,
): Promise<AnalysisResultJsonExportResponse> {
  const response = await fetchApi(
    apiRoutes.analysisRunExportJson(analysisId),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_result_json_export_failed"));
  }

  return (await response.json()) as AnalysisResultJsonExportResponse;
}

export async function createAnalysisResultCsvExport(
  analysisId: string,
): Promise<AnalysisResultCsvExportResponse> {
  const response = await fetchApi(
    apiRoutes.analysisRunExportCsv(analysisId),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_result_csv_export_failed"));
  }

  return (await response.json()) as AnalysisResultCsvExportResponse;
}

export async function createAnalysisResultHtmlReport(
  analysisId: string,
): Promise<AnalysisResultHtmlReportResponse> {
  const response = await fetchApi(
    apiRoutes.analysisRunExportHtml(analysisId),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_result_html_report_failed"));
  }

  return (await response.json()) as AnalysisResultHtmlReportResponse;
}

export async function fetchAnalysisResultExports(
  analysisId: string,
): Promise<AnalysisResultExportListResponse> {
  const response = await fetchApi(
    apiRoutes.analysisRunExports(analysisId),
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_result_exports_fetch_failed"));
  }

  return (await response.json()) as AnalysisResultExportListResponse;
}

export async function downloadAnalysisResultExport(
  analysisId: string,
  exportId: string,
): Promise<void> {
  const response = await fetchApi(
    apiRoutes.analysisRunExportDownload(analysisId, exportId),
    {
      method: "GET",
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_result_export_download_failed"));
  }

  const blob = await response.blob();
  const filename =
    filenameFromContentDisposition(response.headers.get("content-disposition")) ??
    `datalab-analysis-${analysisId}-export-${exportId}`;
  triggerBrowserDownload(blob, filename);
}

export async function fetchAnalysisResultExportDeletionPreflight(
  analysisId: string,
  exportId: string,
): Promise<AnalysisResultExportDeletionPreflightResponse> {
  const response = await fetchApi(
    apiRoutes.analysisRunExportDeletionPreflight(analysisId, exportId),
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(
      await apiErrorCode(response, "analysis_export_deletion_preflight_failed"),
    );
  }
  return (await response.json()) as AnalysisResultExportDeletionPreflightResponse;
}

export async function deleteAnalysisResultExport(
  analysisId: string,
  exportId: string,
  request: AnalysisResultExportDeleteRequest,
): Promise<AnalysisResultExportDeleteResponse> {
  const response = await fetchApi(apiRoutes.analysisRunExportDelete(analysisId, exportId), {
    method: "DELETE",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_export_delete_failed"));
  }
  return (await response.json()) as AnalysisResultExportDeleteResponse;
}
