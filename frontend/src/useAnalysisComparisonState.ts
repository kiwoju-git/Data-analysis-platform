import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchAnalysisRunComparison,
  type AnalysisRunComparisonResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

interface UseAnalysisComparisonStateOptions {
  resetKey: number;
}

export function useAnalysisComparisonState({ resetKey }: UseAnalysisComparisonStateOptions) {
  const [analysisComparisonLeftId, setAnalysisComparisonLeftId] = useState<string | null>(null);
  const [analysisComparisonRightId, setAnalysisComparisonRightId] = useState<string | null>(null);
  const [analysisComparison, setAnalysisComparison] =
    useState<AnalysisRunComparisonResponse | null>(null);
  const [analysisComparisonError, setAnalysisComparisonError] = useState<string | null>(null);
  const [isComparingAnalysisRuns, setIsComparingAnalysisRuns] = useState(false);
  const comparisonRequest = useRef(createLatestRequestGuard()).current;

  const resetAnalysisComparisonState = useCallback(() => {
    comparisonRequest.cancel();
    setAnalysisComparisonLeftId(null);
    setAnalysisComparisonRightId(null);
    setAnalysisComparison(null);
    setAnalysisComparisonError(null);
    setIsComparingAnalysisRuns(false);
  }, [comparisonRequest]);

  function handleSelectAnalysisComparisonRun(side: "left" | "right", analysisId: string) {
    comparisonRequest.cancel();
    setAnalysisComparison(null);
    setAnalysisComparisonError(null);
    setIsComparingAnalysisRuns(false);
    if (side === "left") {
      setAnalysisComparisonLeftId(analysisId);
      return;
    }
    setAnalysisComparisonRightId(analysisId);
  }

  async function compareAnalysisRuns() {
    if (analysisComparisonLeftId === null || analysisComparisonRightId === null) {
      setAnalysisComparisonError("analysis_comparison_requires_two_runs");
      return;
    }

    const request = comparisonRequest.begin();
    setIsComparingAnalysisRuns(true);
    setAnalysisComparisonError(null);
    try {
      const response = await fetchAnalysisRunComparison(
        analysisComparisonLeftId,
        analysisComparisonRightId,
      );
      if (comparisonRequest.isCurrent(request)) {
        setAnalysisComparison(response);
      }
    } catch (error) {
      if (comparisonRequest.isCurrent(request)) {
        setAnalysisComparison(null);
        setAnalysisComparisonError(
          error instanceof Error ? error.message : "analysis_comparison_failed",
        );
      }
    } finally {
      if (comparisonRequest.isCurrent(request)) {
        setIsComparingAnalysisRuns(false);
      }
    }
  }

  useEffect(() => {
    resetAnalysisComparisonState();
    return () => {
      comparisonRequest.cancel();
    };
  }, [comparisonRequest, resetAnalysisComparisonState, resetKey]);

  return {
    analysisComparison,
    analysisComparisonError,
    analysisComparisonLeftId,
    analysisComparisonRightId,
    isComparingAnalysisRuns,
    onCompareAnalysisRuns: () => {
      void compareAnalysisRuns();
    },
    onSelectAnalysisComparisonRun: handleSelectAnalysisComparisonRun,
    resetAnalysisComparisonState,
  };
}
