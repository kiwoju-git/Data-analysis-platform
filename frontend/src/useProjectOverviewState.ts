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

export function useProjectOverviewState() {
  const [summary, setSummary] = useState<WorkspaceSummaryResponse | null>(null);
  const [recentDatasets, setRecentDatasets] =
    useState<DatasetVersionCatalogResponse | null>(null);
  const [recentAnalyses, setRecentAnalyses] =
    useState<AnalysisRunListResponse | null>(null);
  const [recentModels, setRecentModels] =
    useState<RegressionModelCatalogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    void Promise.all([
      fetchWorkspaceSummary(),
      fetchDatasetVersions(5, 0, "visible"),
      fetchAnalysisRuns({
        resultAvailable: true,
        status: "succeeded",
        limit: 5,
        offset: 0,
      }),
      fetchRegressionModels(0, 5),
    ])
      .then(([nextSummary, datasets, analyses, models]) => {
        if (!active) return;
        setSummary(nextSummary);
        setRecentDatasets(datasets);
        setRecentAnalyses(analyses);
        setRecentModels(models);
      })
      .catch((loadError) => {
        if (!active) return;
        setError(
          loadError instanceof Error
            ? loadError.message
            : "workspace_summary_fetch_failed",
        );
      });
    return () => {
      active = false;
    };
  }, [revision]);

  return {
    error,
    recentAnalyses,
    recentDatasets,
    recentModels,
    summary,
    onRetry: () => setRevision((current) => current + 1),
  };
}
