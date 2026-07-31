import { useEffect, useState } from "react";

import {
  fetchAnalysisRuns,
  fetchDatasetVersions,
  fetchRegressionModels,
  fetchWorkspaceSummary,
  type AnalysisRunListResponse,
  type DatasetVersionCatalogResponse,
  type RegressionModelCatalogResponse,
  type WorkspaceSummaryResponse,
} from "./api";

export interface ProjectResourceState<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
}

function loadingResource<T>(): ProjectResourceState<T> {
  return { data: null, error: null, isLoading: true };
}

function resolvedResource<T>(
  result: PromiseSettledResult<T>,
  fallbackError: string,
): ProjectResourceState<T> {
  if (result.status === "fulfilled") {
    return { data: result.value, error: null, isLoading: false };
  }
  return {
    data: null,
    error: result.reason instanceof Error ? result.reason.message : fallbackError,
    isLoading: false,
  };
}

export function useProjectOverviewState(workspaceAssetRevision = 0) {
  const [summary, setSummary] =
    useState<ProjectResourceState<WorkspaceSummaryResponse>>(loadingResource);
  const [recentDatasets, setRecentDatasets] =
    useState<ProjectResourceState<DatasetVersionCatalogResponse>>(loadingResource);
  const [recentAnalyses, setRecentAnalyses] =
    useState<ProjectResourceState<AnalysisRunListResponse>>(loadingResource);
  const [recentModels, setRecentModels] =
    useState<ProjectResourceState<RegressionModelCatalogResponse>>(loadingResource);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setSummary(loadingResource());
    setRecentDatasets(loadingResource());
    setRecentAnalyses(loadingResource());
    setRecentModels(loadingResource());
    void Promise.allSettled([
      fetchWorkspaceSummary(),
      fetchDatasetVersions(3, 0, "visible"),
      fetchAnalysisRuns({
        resultAvailable: true,
        status: "succeeded",
        limit: 3,
        offset: 0,
      }),
      fetchRegressionModels(0, 3),
    ]).then(([summaryResult, datasetsResult, analysesResult, modelsResult]) => {
      if (!active) return;
      setSummary(resolvedResource(summaryResult, "workspace_summary_fetch_failed"));
      setRecentDatasets(
        resolvedResource(datasetsResult, "dataset_catalog_fetch_failed"),
      );
      setRecentAnalyses(
        resolvedResource(analysesResult, "analysis_catalog_fetch_failed"),
      );
      setRecentModels(
        resolvedResource(modelsResult, "regression_model_catalog_fetch_failed"),
      );
    });
    return () => {
      active = false;
    };
  }, [revision, workspaceAssetRevision]);

  return {
    recentAnalyses,
    recentDatasets,
    recentModels,
    summary,
    onRetry: () => setRevision((current) => current + 1),
  };
}
