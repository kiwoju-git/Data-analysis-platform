import { getApiBaseUrl } from "./client";
import type { AnalysisRunState } from "./types";

const API_V1_PREFIX = "/api/v1";

function apiUrl(path: string): string {
  return `${getApiBaseUrl()}${API_V1_PREFIX}${path}`;
}

function pathId(value: string): string {
  return encodeURIComponent(value);
}

function urlWithQuery(path: string, params: URLSearchParams): string {
  const query = params.toString();
  return query.length === 0 ? apiUrl(path) : `${apiUrl(path)}?${query}`;
}

export interface AnalysisRunsRouteParams {
  datasetVersionId?: string | null;
  methodId?: string | null;
  resultAvailable?: boolean | null;
  limit?: number;
  offset?: number;
  stale?: boolean | null;
  status?: AnalysisRunState | null;
}

export const apiRoutes = {
  health(): string {
    return apiUrl("/health");
  },

  datasets(): string {
    return apiUrl("/datasets");
  },

  datasetPaste(): string {
    return apiUrl("/datasets/paste");
  },

  datasetConfirmParsing(datasetId: string): string {
    return apiUrl(`/datasets/${pathId(datasetId)}/confirm-parsing`);
  },

  datasetVersionSchema(versionId: string): string {
    return apiUrl(`/dataset-versions/${pathId(versionId)}/schema`);
  },

  datasetVersionRows(versionId: string, offset: number, limit: number): string {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    return urlWithQuery(`/dataset-versions/${pathId(versionId)}/rows`, params);
  },

  datasetVersionProfile(versionId: string): string {
    return apiUrl(`/dataset-versions/${pathId(versionId)}/profile`);
  },

  analysisMethods(): string {
    return apiUrl("/analysis-methods");
  },

  analysisRunsBase(): string {
    return apiUrl("/analysis-runs");
  },

  analysisRuns({
    datasetVersionId,
    methodId,
    resultAvailable,
    limit = 50,
    offset = 0,
    stale,
    status,
  }: AnalysisRunsRouteParams = {}): string {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (datasetVersionId !== undefined && datasetVersionId !== null) {
      params.set("dataset_version_id", datasetVersionId);
    }
    if (methodId !== undefined && methodId !== null && methodId.length > 0) {
      params.set("method_id", methodId);
    }
    if (status !== undefined && status !== null) {
      params.set("status", status);
    }
    if (stale !== undefined && stale !== null) {
      params.set("stale", String(stale));
    }
    if (resultAvailable !== undefined && resultAvailable !== null) {
      params.set("result_available", String(resultAvailable));
    }
    return urlWithQuery("/analysis-runs", params);
  },

  analysisRunComparison(leftAnalysisId: string, rightAnalysisId: string): string {
    const params = new URLSearchParams({
      left_analysis_id: leftAnalysisId,
      right_analysis_id: rightAnalysisId,
    });
    return urlWithQuery("/analysis-runs/comparison", params);
  },

  analysisRunResult(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/result`);
  },

  analysisRunExports(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/exports`);
  },

  analysisRunExportJson(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/exports/json`);
  },

  analysisRunExportCsv(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/exports/csv`);
  },

  analysisRunExportHtml(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/exports/html`);
  },

  analysisRunExportDownload(analysisId: string, exportId: string): string {
    return apiUrl(
      `/analysis-runs/${pathId(analysisId)}/exports/${pathId(exportId)}/download`,
    );
  },

  doeFactorialDesign(): string {
    return apiUrl("/doe-designs/factorial");
  },

  doeDesign(designId: string): string {
    return apiUrl(`/doe-designs/${pathId(designId)}`);
  },

  doeDesignResponses(designId: string): string {
    return apiUrl(`/doe-designs/${pathId(designId)}/responses`);
  },

  regressionPredictionPreflight(modelId: string): string {
    return apiUrl(`/regression-models/${pathId(modelId)}/prediction-preflight`);
  },

  regressionPredictions(modelId: string): string {
    return apiUrl(`/regression-models/${pathId(modelId)}/predictions`);
  },

  gageRrPreflight(): string {
    return apiUrl("/quality/gage-rr/preflight");
  },
};
