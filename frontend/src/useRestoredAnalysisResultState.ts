import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchAnalysisRunResult,
  type AnalysisMethodListResponse,
  type AnalysisModuleId,
  type AnalysisResultEnvelope,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

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
  const restoreRequest = useRef(createLatestRequestGuard()).current;

  const resetRestoredAnalysisResultState = useCallback(() => {
    restoreRequest.cancel();
    setRestoredAnalysisResult(null);
    setRestoredAnalysisResultError(null);
    setIsRestoringAnalysisResult(false);
  }, [restoreRequest]);

  async function restoreAnalysisRun(analysisId: string) {
    const request = restoreRequest.begin();
    setIsRestoringAnalysisResult(true);
    setRestoredAnalysisResultError(null);
    try {
      const response = await fetchAnalysisRunResult(analysisId);
      if (!restoreRequest.isCurrent(request)) {
        return;
      }
      setRestoredAnalysisResult(response);
      const method = analysisCatalog?.methods.find(
        (candidate) => candidate.method_id === response.method_id,
      );
      if (method !== undefined) {
        onSelectMethod(method.module_id, method.method_id);
      }
      await onRefreshAnalysisResultExports(analysisId);
    } catch (error) {
      if (restoreRequest.isCurrent(request)) {
        setRestoredAnalysisResult(null);
        setRestoredAnalysisResultError(
          error instanceof Error ? error.message : "analysis_result_fetch_failed",
        );
      }
    } finally {
      if (restoreRequest.isCurrent(request)) {
        setIsRestoringAnalysisResult(false);
      }
    }
  }

  useEffect(() => {
    if (currentAnalysisId !== null || currentDatasetVersionId === null) {
      resetRestoredAnalysisResultState();
    }
  }, [currentAnalysisId, currentDatasetVersionId, resetRestoredAnalysisResultState]);

  useEffect(() => {
    resetRestoredAnalysisResultState();
  }, [resetKey, resetRestoredAnalysisResultState]);

  useEffect(
    () => () => {
      restoreRequest.cancel();
    },
    [restoreRequest],
  );

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
