import { useEffect, useState } from "react";

import {
  fetchAnalysisRunResult,
  type AnalysisMethodListResponse,
  type AnalysisModuleId,
  type AnalysisResultEnvelope,
} from "./api";

interface UseRestoredAnalysisResultStateOptions {
  analysisCatalog: AnalysisMethodListResponse | null;
  currentAnalysisId: string | null;
  currentDatasetVersionId: string | null;
  onRefreshAnalysisResultExports: (analysisId: string) => Promise<void>;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  resetKey: number;
}

export function useRestoredAnalysisResultState({
  analysisCatalog,
  currentAnalysisId,
  currentDatasetVersionId,
  onRefreshAnalysisResultExports,
  onSelectMethod,
  resetKey,
}: UseRestoredAnalysisResultStateOptions) {
  const [restoredAnalysisResult, setRestoredAnalysisResult] =
    useState<AnalysisResultEnvelope | null>(null);
  const [restoredAnalysisResultError, setRestoredAnalysisResultError] = useState<string | null>(
    null,
  );
  const [isRestoringAnalysisResult, setIsRestoringAnalysisResult] = useState(false);

  function resetRestoredAnalysisResultState() {
    setRestoredAnalysisResult(null);
    setRestoredAnalysisResultError(null);
  }

  async function restoreAnalysisRun(analysisId: string) {
    setIsRestoringAnalysisResult(true);
    setRestoredAnalysisResultError(null);
    try {
      const response = await fetchAnalysisRunResult(analysisId);
      setRestoredAnalysisResult(response);
      const method = analysisCatalog?.methods.find(
        (candidate) => candidate.method_id === response.method_id,
      );
      if (method !== undefined) {
        onSelectMethod(method.module_id, method.method_id);
      }
      await onRefreshAnalysisResultExports(analysisId);
    } catch (error) {
      setRestoredAnalysisResult(null);
      setRestoredAnalysisResultError(
        error instanceof Error ? error.message : "analysis_result_fetch_failed",
      );
    } finally {
      setIsRestoringAnalysisResult(false);
    }
  }

  useEffect(() => {
    if (currentAnalysisId !== null || currentDatasetVersionId === null) {
      resetRestoredAnalysisResultState();
    }
  }, [currentAnalysisId, currentDatasetVersionId, resetKey]);

  return {
    isRestoringAnalysisResult,
    restoredAnalysisResult,
    restoredAnalysisResultError,
    onRestoreAnalysisRun: (analysisId: string) => {
      void restoreAnalysisRun(analysisId);
    },
    resetRestoredAnalysisResultState,
  };
}
