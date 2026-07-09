import { useEffect, useState } from "react";

import {
  fetchAnalysisRunComparison,
  type AnalysisRunComparisonResponse,
} from "./api";

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

  function resetAnalysisComparisonState() {
    setAnalysisComparisonLeftId(null);
    setAnalysisComparisonRightId(null);
    setAnalysisComparison(null);
    setAnalysisComparisonError(null);
  }

  function handleSelectAnalysisComparisonRun(side: "left" | "right", analysisId: string) {
    setAnalysisComparison(null);
    setAnalysisComparisonError(null);
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

    setIsComparingAnalysisRuns(true);
    setAnalysisComparisonError(null);
    try {
      const response = await fetchAnalysisRunComparison(
        analysisComparisonLeftId,
        analysisComparisonRightId,
      );
      setAnalysisComparison(response);
    } catch (error) {
      setAnalysisComparison(null);
      setAnalysisComparisonError(
        error instanceof Error ? error.message : "analysis_comparison_failed",
      );
    } finally {
      setIsComparingAnalysisRuns(false);
    }
  }

  useEffect(() => {
    resetAnalysisComparisonState();
  }, [resetKey]);

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
