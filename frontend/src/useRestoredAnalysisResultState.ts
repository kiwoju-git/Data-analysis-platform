import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchAnalysisRunResult,
  type AnalysisMethodListResponse,
  type AnalysisModuleId,
  type AnalysisResultEnvelope,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

interface UseRestoredAnalysisResultStateOptions {
  onRestoreIntent?: () => void;
  onRestoreCommitted?: () => void;
  analysisCatalog: AnalysisMethodListResponse | null;
  currentAnalysisId: string | null;
  currentDatasetVersionId: string | null;
  onRefreshAnalysisResultExports: (analysisId: string) => Promise<void>;
  onSelectMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
  resetKey: number;
}

export function useRestoredAnalysisResultState({
  onRestoreIntent,
  onRestoreCommitted,
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

  const cancelPendingRestore = useCallback(() => {
    restoreRequest.cancel();
    setRestoredAnalysisResultError(null);
    setIsRestoringAnalysisResult(false);
  }, [restoreRequest]);
  const resetRestoredAnalysisResultState = useCallback(() => {
    cancelPendingRestore();
    setRestoredAnalysisResult(null);
  }, [cancelPendingRestore]);

  async function restoreAnalysisRun(analysisId: string) {
    onRestoreIntent?.();
    const request = restoreRequest.begin();
    setIsRestoringAnalysisResult(true);
    setRestoredAnalysisResultError(null);
    let response: AnalysisResultEnvelope;
    try {
      response = await fetchAnalysisRunResult(analysisId);
      if (!restoreRequest.isCurrent(request)) {
        return;
      }
      if (response.analysis_id !== analysisId) {
        throw new Error("analysis_result_fetch_failed");
      }
    } catch (error) {
      if (restoreRequest.isCurrent(request)) {
        setRestoredAnalysisResultError(
          error instanceof Error ? error.message : "analysis_result_fetch_failed",
        );
        setIsRestoringAnalysisResult(false);
      }
      return;
    }
    onRestoreCommitted?.();
    setRestoredAnalysisResult(response);
    const method = analysisCatalog?.methods.find(
      (candidate) => candidate.method_id === response.method_id,
    );
    if (method !== undefined) {
      onSelectMethod(method.module_id, method.method_id);
    }
    try {
      await onRefreshAnalysisResultExports(analysisId);
    } catch {
      if (restoreRequest.isCurrent(request)) {
        setRestoredAnalysisResultError("analysis_export_list_fetch_failed");
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
    cancelPendingRestore,
    resetRestoredAnalysisResultState,
  };
}
