import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchRegressionPredictionRows,
  type RegressionPredictionRowsPageResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

const predictionPageSize = 25;

export interface RegressionPredictionRowsState {
  error: string | null;
  isLoading: boolean;
  page: RegressionPredictionRowsPageResponse | null;
  onPageChange: (offset: number) => void;
}

export function useRegressionPredictionRowsState(
  predictionId: string | null,
): RegressionPredictionRowsState {
  const [page, setPage] = useState<RegressionPredictionRowsPageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const rowsRequest = useRef(createLatestRequestGuard()).current;

  const loadPage = useCallback(
    async (activePredictionId: string, offset: number) => {
      const request = rowsRequest.begin();
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchRegressionPredictionRows(
          activePredictionId,
          predictionPageSize,
          Math.max(0, offset),
        );
        if (rowsRequest.isCurrent(request)) {
          setPage(response);
        }
      } catch (loadError) {
        if (rowsRequest.isCurrent(request)) {
          setPage(null);
          setError(
            loadError instanceof Error
              ? loadError.message
              : "regression_prediction_rows_failed",
          );
        }
      } finally {
        if (rowsRequest.isCurrent(request)) {
          setIsLoading(false);
        }
      }
    },
    [rowsRequest],
  );

  useEffect(() => {
    rowsRequest.cancel();
    setPage(null);
    setError(null);
    setIsLoading(false);
    if (predictionId !== null) {
      void loadPage(predictionId, 0);
    }
    return () => {
      rowsRequest.cancel();
    };
  }, [loadPage, predictionId, rowsRequest]);

  return {
    error,
    isLoading,
    page,
    onPageChange: (offset) => {
      if (predictionId !== null) {
        void loadPage(predictionId, offset);
      }
    },
  };
}
