import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchRegressionPredictions,
  fetchRegressionPredictionPreflight,
  type RegressionPredictionPreflightResponse,
  type RegressionPredictionResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

interface UseRegressionPredictionStateOptions {
  confidenceLevel: number;
  currentDatasetVersionId: string | null;
  initialPrediction?: RegressionPredictionResponse | null;
  modelId: string | null;
  onPredictionCreated?: (prediction: RegressionPredictionResponse) => void;
  targetDatasetVersionId: string | null;
}

export interface RegressionPredictionState {
  isRunningPrediction: boolean;
  isRunningPreflight: boolean;
  onRunPrediction: () => void;
  onRunPreflight: () => void;
  prediction: RegressionPredictionResponse | null;
  predictionError: string | null;
  preflight: RegressionPredictionPreflightResponse | null;
  preflightError: string | null;
}

export function useRegressionPredictionState({
  confidenceLevel,
  currentDatasetVersionId,
  initialPrediction = null,
  modelId,
  onPredictionCreated,
  targetDatasetVersionId,
}: UseRegressionPredictionStateOptions): RegressionPredictionState {
  const [preflight, setPreflight] = useState<RegressionPredictionPreflightResponse | null>(null);
  const [preflightError, setPreflightError] = useState<string | null>(null);
  const [isRunningPreflight, setIsRunningPreflight] = useState(false);
  const preflightRequest = useRef(createLatestRequestGuard()).current;
  const [prediction, setPrediction] = useState<RegressionPredictionResponse | null>(null);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [isRunningPrediction, setIsRunningPrediction] = useState(false);
  const predictionRequest = useRef(createLatestRequestGuard()).current;

  const reset = useCallback(() => {
    preflightRequest.cancel();
    predictionRequest.cancel();
    setPreflight(null);
    setPreflightError(null);
    setPrediction(null);
    setPredictionError(null);
    setIsRunningPreflight(false);
    setIsRunningPrediction(false);
  }, [predictionRequest, preflightRequest]);

  useEffect(() => {
    reset();
    if (
      initialPrediction !== null &&
      initialPrediction.model_id === modelId &&
      initialPrediction.target_dataset_version_id === targetDatasetVersionId
    ) {
      setPrediction(initialPrediction);
    }
    return reset;
  }, [
    currentDatasetVersionId,
    initialPrediction,
    modelId,
    reset,
    targetDatasetVersionId,
  ]);

  async function runPreflight() {
    if (
      currentDatasetVersionId === null ||
      modelId === null ||
      targetDatasetVersionId === null
    ) {
      setPreflightError("regression_model_manifest_required");
      return;
    }

    predictionRequest.cancel();
    setIsRunningPrediction(false);
    setPrediction(null);
    setPredictionError(null);
    const request = preflightRequest.begin();
    setIsRunningPreflight(true);
    setPreflight(null);
    setPreflightError(null);
    try {
      const response = await fetchRegressionPredictionPreflight(modelId, {
        dataset_version_id: targetDatasetVersionId,
      });
      if (preflightRequest.isCurrent(request)) {
        setPreflight(response);
      }
    } catch (error) {
      if (preflightRequest.isCurrent(request)) {
        setPreflight(null);
        setPreflightError(
          error instanceof Error ? error.message : "regression_prediction_preflight_failed",
        );
      }
    } finally {
      if (preflightRequest.isCurrent(request)) {
        setIsRunningPreflight(false);
      }
    }
  }

  async function runPrediction() {
    if (
      currentDatasetVersionId === null ||
      modelId === null ||
      targetDatasetVersionId === null
    ) {
      setPredictionError("regression_model_manifest_required");
      return;
    }
    if (
      preflight === null ||
      !preflight.prediction_ready ||
      preflight.model_id !== modelId ||
      preflight.target_dataset_version_id !== targetDatasetVersionId
    ) {
      setPredictionError("regression_prediction_preflight_required");
      return;
    }

    const request = predictionRequest.begin();
    setIsRunningPrediction(true);
    setPrediction(null);
    setPredictionError(null);
    try {
      const response = await fetchRegressionPredictions(modelId, {
        dataset_version_id: targetDatasetVersionId,
        confidence_level: confidenceLevel,
        missing_policy: "complete_case",
        include_intervals: true,
      });
      if (predictionRequest.isCurrent(request)) {
        setPrediction(response);
        onPredictionCreated?.(response);
      }
    } catch (error) {
      if (predictionRequest.isCurrent(request)) {
        setPrediction(null);
        setPredictionError(
          error instanceof Error ? error.message : "regression_prediction_failed",
        );
      }
    } finally {
      if (predictionRequest.isCurrent(request)) {
        setIsRunningPrediction(false);
      }
    }
  }

  return {
    isRunningPrediction,
    isRunningPreflight,
    onRunPrediction: () => {
      void runPrediction();
    },
    onRunPreflight: () => {
      void runPreflight();
    },
    prediction,
    predictionError,
    preflight,
    preflightError,
  };
}
