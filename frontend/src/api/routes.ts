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

export interface AttributeControlLimitSetsRouteParams {
  sourceDatasetVersionId?: string | null;
  chartType?: "p" | "np" | "c" | "u" | null;
  limit?: number;
  offset?: number;
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

  datasetVersions(limit: number, offset: number): string {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    return urlWithQuery("/dataset-versions", params);
  },

  analysisMethods(): string {
    return apiUrl("/analysis-methods");
  },

  attributeControlLimitSets({
    sourceDatasetVersionId,
    chartType,
    limit = 20,
    offset = 0,
  }: AttributeControlLimitSetsRouteParams = {}): string {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (sourceDatasetVersionId !== undefined && sourceDatasetVersionId !== null) {
      params.set("source_dataset_version_id", sourceDatasetVersionId);
    }
    if (chartType !== undefined && chartType !== null) {
      params.set("chart_type", chartType);
    }
    return urlWithQuery("/quality/attribute-control-limit-sets", params);
  },

  attributeControlLimitSetsBase(): string {
    return apiUrl("/quality/attribute-control-limit-sets");
  },

  attributeControlLimitSet(limitSetId: string): string {
    return apiUrl(`/quality/attribute-control-limit-sets/${pathId(limitSetId)}`);
  },

  attributeControlLimitSetDeletionPreflight(limitSetId: string): string {
    return apiUrl(
      `/quality/attribute-control-limit-sets/${pathId(limitSetId)}/deletion-preflight`,
    );
  },

  attributeControlMonitoringPreflight(limitSetId: string): string {
    return apiUrl(
      `/quality/attribute-control-limit-sets/${pathId(limitSetId)}/monitoring-preflight`,
    );
  },

  bayesianStudies(offset?: number, limit?: number): string {
    if (offset === undefined || limit === undefined) {
      return apiUrl("/bayesian-studies");
    }
    return urlWithQuery(
      "/bayesian-studies",
      new URLSearchParams({ offset: String(offset), limit: String(limit) }),
    );
  },

  bayesianStudy(studyId: string): string {
    return apiUrl(`/bayesian-studies/${pathId(studyId)}`);
  },

  bayesianStudyClose(studyId: string): string {
    return apiUrl(`/bayesian-studies/${pathId(studyId)}/close`);
  },

  bayesianStudyDeletionPreflight(studyId: string): string {
    return apiUrl(`/bayesian-studies/${pathId(studyId)}/deletion-preflight`);
  },

  bayesianStudyDelete(studyId: string): string {
    return apiUrl(`/bayesian-studies/${pathId(studyId)}`);
  },

  bayesianTrials(studyId: string, offset: number, limit: number): string {
    return urlWithQuery(
      `/bayesian-studies/${pathId(studyId)}/trials`,
      new URLSearchParams({ offset: String(offset), limit: String(limit) }),
    );
  },

  bayesianTrialObservation(studyId: string, trialId: string): string {
    return apiUrl(
      `/bayesian-studies/${pathId(studyId)}/trials/${pathId(trialId)}/observation`,
    );
  },

  bayesianTrialAbandon(studyId: string, trialId: string): string {
    return apiUrl(
      `/bayesian-studies/${pathId(studyId)}/trials/${pathId(trialId)}/abandon`,
    );
  },

  bayesianHistory(studyId: string, offset: number, limit: number): string {
    return urlWithQuery(
      `/bayesian-studies/${pathId(studyId)}/history`,
      new URLSearchParams({ offset: String(offset), limit: String(limit) }),
    );
  },

  bayesianHistoryRevision(studyId: string, historyRevisionId: string): string {
    return apiUrl(
      `/bayesian-studies/${pathId(studyId)}/history/${pathId(historyRevisionId)}`,
    );
  },

  bayesianRecommendations(studyId: string, offset?: number, limit?: number): string {
    const path = `/bayesian-studies/${pathId(studyId)}/recommendations`;
    if (offset === undefined || limit === undefined) {
      return apiUrl(path);
    }
    return urlWithQuery(
      path,
      new URLSearchParams({ offset: String(offset), limit: String(limit) }),
    );
  },

  bayesianRecommendation(studyId: string, recommendationId: string): string {
    return apiUrl(
      `/bayesian-studies/${pathId(studyId)}/recommendations/${pathId(recommendationId)}`,
    );
  },

  bayesianLatestRecommendation(studyId: string): string {
    return apiUrl(`/bayesian-studies/${pathId(studyId)}/recommendations/latest`);
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

  analysisRunDeletionPreflight(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/deletion-preflight`);
  },

  analysisRunDelete(analysisId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/deletion`);
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

  analysisRunExportDeletionPreflight(analysisId: string, exportId: string): string {
    return apiUrl(
      `/analysis-runs/${pathId(analysisId)}/exports/${pathId(exportId)}/deletion-preflight`,
    );
  },

  analysisRunExportDelete(analysisId: string, exportId: string): string {
    return apiUrl(`/analysis-runs/${pathId(analysisId)}/exports/${pathId(exportId)}`);
  },

  doeResponseSurfaceDesign(): string {
    return apiUrl("/doe-designs/response-surface");
  },

  doeResponseSurfaceDesignById(designId: string): string {
    return apiUrl(`/doe-designs/response-surface/${pathId(designId)}`);
  },

  doeResponseSurfaceResponses(designId: string): string {
    return apiUrl(`/doe-designs/response-surface/${pathId(designId)}/responses`);
  },

  doeResponseSurfaceAnalyses(designId: string): string {
    return apiUrl(`/doe-designs/response-surface/${pathId(designId)}/analyses`);
  },

  doeResponseSurfaceAnalysis(designId: string, analysisId: string): string {
    return apiUrl(
      `/doe-designs/response-surface/${pathId(designId)}/analyses/${pathId(analysisId)}`,
    );
  },

  doeResponseSurfaceOptimizations(designId: string): string {
    return apiUrl(`/doe-designs/response-surface/${pathId(designId)}/optimizations`);
  },

  doeResponseSurfaceOptimization(designId: string, optimizationId: string): string {
    return apiUrl(
      `/doe-designs/response-surface/${pathId(designId)}/optimizations/${pathId(optimizationId)}`,
    );
  },

  doeDesign(designId: string): string {
    return apiUrl(`/doe-designs/${pathId(designId)}`);
  },

  doeDesignResponses(designId: string): string {
    return apiUrl(`/doe-designs/${pathId(designId)}/responses`);
  },

  doeResponseRevisions(
    designId: string,
    responseName?: string,
    offset = 0,
    limit = 20,
  ): string {
    const path = `/doe-designs/${pathId(designId)}/response-revisions`;
    if (responseName === undefined) return apiUrl(path);
    return urlWithQuery(
      path,
      new URLSearchParams({
        response_name: responseName,
        offset: String(offset),
        limit: String(limit),
      }),
    );
  },

  doeResponseRevision(designId: string, responseRevisionId: string): string {
    return apiUrl(
      `/doe-designs/${pathId(designId)}/response-revisions/${pathId(responseRevisionId)}`,
    );
  },

  doeResponseRevisionAbandon(designId: string, responseRevisionId: string): string {
    return apiUrl(
      `/doe-designs/${pathId(designId)}/response-revisions/${pathId(responseRevisionId)}/abandon`,
    );
  },

  doeDesignAnalyses(designId: string): string {
    return apiUrl(`/doe-designs/${pathId(designId)}/analyses`);
  },

  doeDesignAnalysis(designId: string, analysisId: string): string {
    return apiUrl(
      `/doe-designs/${pathId(designId)}/analyses/${pathId(analysisId)}`,
    );
  },

  regressionPredictionPreflight(modelId: string): string {
    return apiUrl(`/regression-models/${pathId(modelId)}/prediction-preflight`);
  },

  regressionModel(modelId: string): string {
    return apiUrl(`/regression-models/${pathId(modelId)}`);
  },

  regressionModelDeletionPreflight(modelId: string): string {
    return apiUrl(`/regression-models/${pathId(modelId)}/deletion-preflight`);
  },

  regressionPredictions(modelId: string): string {
    return apiUrl(`/regression-models/${pathId(modelId)}/predictions`);
  },

  regressionPredictionRows(predictionId: string, limit: number, offset: number): string {
    const query = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    return apiUrl(`/regression-models/predictions/${pathId(predictionId)}/rows?${query}`);
  },

  regressionPredictionCsvExport(predictionId: string): string {
    return apiUrl(`/regression-models/predictions/${pathId(predictionId)}/exports/csv`);
  },

  gageRrPreflight(): string {
    return apiUrl("/quality/gage-rr/preflight");
  },
};
