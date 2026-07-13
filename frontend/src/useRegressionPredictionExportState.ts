import { useCallback, useEffect, useRef, useState } from "react";

import {
  createRegressionPredictionCsvExport,
  downloadAnalysisResultExport,
  type RegressionPredictionCsvExportResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

export interface RegressionPredictionExportState {
  csvExport: RegressionPredictionCsvExportResponse | null;
  error: string | null;
  isCreating: boolean;
  isDownloading: boolean;
  onCreate: () => void;
  onDownload: () => void;
}

export function useRegressionPredictionExportState(
  predictionId: string | null,
): RegressionPredictionExportState {
  const [csvExport, setCsvExport] = useState<RegressionPredictionCsvExportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const createRequest = useRef(createLatestRequestGuard()).current;
  const downloadRequest = useRef(createLatestRequestGuard()).current;

  const reset = useCallback(() => {
    createRequest.cancel();
    downloadRequest.cancel();
    setCsvExport(null);
    setError(null);
    setIsCreating(false);
    setIsDownloading(false);
  }, [createRequest, downloadRequest]);

  useEffect(() => {
    reset();
    return reset;
  }, [predictionId, reset]);

  async function createCsvExport() {
    if (predictionId === null) {
      return;
    }
    const request = createRequest.begin();
    setIsCreating(true);
    setError(null);
    try {
      const response = await createRegressionPredictionCsvExport(predictionId);
      if (createRequest.isCurrent(request)) {
        setCsvExport(response);
      }
    } catch (createError) {
      if (createRequest.isCurrent(request)) {
        setCsvExport(null);
        setError(
          createError instanceof Error
            ? createError.message
            : "regression_prediction_csv_export_failed",
        );
      }
    } finally {
      if (createRequest.isCurrent(request)) {
        setIsCreating(false);
      }
    }
  }

  async function downloadCsvExport() {
    if (predictionId === null || csvExport === null) {
      return;
    }
    const request = downloadRequest.begin();
    setIsDownloading(true);
    setError(null);
    try {
      await downloadAnalysisResultExport(predictionId, csvExport.export_id);
    } catch (downloadError) {
      if (downloadRequest.isCurrent(request)) {
        setError(
          downloadError instanceof Error
            ? downloadError.message
            : "analysis_result_export_download_failed",
        );
      }
    } finally {
      if (downloadRequest.isCurrent(request)) {
        setIsDownloading(false);
      }
    }
  }

  return {
    csvExport,
    error,
    isCreating,
    isDownloading,
    onCreate: () => {
      void createCsvExport();
    },
    onDownload: () => {
      void downloadCsvExport();
    },
  };
}
