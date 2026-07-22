import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchDatasetVersions,
  fetchRegressionModels,
  updateDatasetVersionMetadata,
  updateRegressionModelMetadata,
  type DatasetVersionCatalogResponse,
  type DatasetVersionMetadataUpdateRequest,
  type RegressionModelCatalogResponse,
  type RegressionModelMetadataUpdateRequest,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

const pageSize = 20;

export interface AssetManagementState {
  datasetCatalog: DatasetVersionCatalogResponse | null;
  datasetError: string | null;
  datasetLoading: boolean;
  modelCatalog: RegressionModelCatalogResponse | null;
  modelError: string | null;
  modelLoading: boolean;
  savingId: string | null;
  onDatasetPageChange: (offset: number) => void;
  onModelPageChange: (offset: number) => void;
  onRefreshDatasets: () => void;
  onRefreshModels: () => void;
  onSaveDatasetMetadata: (
    versionId: string,
    request: DatasetVersionMetadataUpdateRequest,
  ) => Promise<boolean>;
  onSaveModelMetadata: (
    modelId: string,
    request: RegressionModelMetadataUpdateRequest,
  ) => Promise<boolean>;
}

export function useAssetManagementState(): AssetManagementState {
  const [datasetCatalog, setDatasetCatalog] =
    useState<DatasetVersionCatalogResponse | null>(null);
  const [modelCatalog, setModelCatalog] = useState<RegressionModelCatalogResponse | null>(null);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [modelLoading, setModelLoading] = useState(false);
  const [datasetOffset, setDatasetOffset] = useState(0);
  const [modelOffset, setModelOffset] = useState(0);
  const [datasetRevision, setDatasetRevision] = useState(0);
  const [modelRevision, setModelRevision] = useState(0);
  const [savingId, setSavingId] = useState<string | null>(null);
  const datasetRequest = useRef(createLatestRequestGuard()).current;
  const modelRequest = useRef(createLatestRequestGuard()).current;
  const saveRequest = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    const request = datasetRequest.begin();
    setDatasetLoading(true);
    setDatasetError(null);
    void fetchDatasetVersions(pageSize, datasetOffset)
      .then((response) => {
        if (datasetRequest.isCurrent(request)) setDatasetCatalog(response);
      })
      .catch((error) => {
        if (!datasetRequest.isCurrent(request)) return;
        setDatasetCatalog(null);
        setDatasetError(error instanceof Error ? error.message : "dataset_catalog_failed");
      })
      .finally(() => {
        if (datasetRequest.isCurrent(request)) setDatasetLoading(false);
      });
    return () => datasetRequest.cancel(request);
  }, [datasetOffset, datasetRequest, datasetRevision]);

  useEffect(() => {
    const request = modelRequest.begin();
    setModelLoading(true);
    setModelError(null);
    void fetchRegressionModels(modelOffset, pageSize)
      .then((response) => {
        if (modelRequest.isCurrent(request)) setModelCatalog(response);
      })
      .catch((error) => {
        if (!modelRequest.isCurrent(request)) return;
        setModelCatalog(null);
        setModelError(error instanceof Error ? error.message : "model_catalog_failed");
      })
      .finally(() => {
        if (modelRequest.isCurrent(request)) setModelLoading(false);
      });
    return () => modelRequest.cancel(request);
  }, [modelOffset, modelRequest, modelRevision]);

  const saveDatasetMetadata = useCallback(
    async (versionId: string, requestBody: DatasetVersionMetadataUpdateRequest) => {
      const request = saveRequest.begin();
      setSavingId(versionId);
      setDatasetError(null);
      try {
        await updateDatasetVersionMetadata(versionId, requestBody);
        if (!saveRequest.isCurrent(request)) return false;
        setDatasetRevision((revision) => revision + 1);
        return true;
      } catch (error) {
        if (saveRequest.isCurrent(request)) {
          setDatasetError(error instanceof Error ? error.message : "metadata_update_failed");
        }
        return false;
      } finally {
        if (saveRequest.isCurrent(request)) setSavingId(null);
      }
    },
    [saveRequest],
  );

  const saveModelMetadata = useCallback(
    async (modelId: string, requestBody: RegressionModelMetadataUpdateRequest) => {
      const request = saveRequest.begin();
      setSavingId(modelId);
      setModelError(null);
      try {
        await updateRegressionModelMetadata(modelId, requestBody);
        if (!saveRequest.isCurrent(request)) return false;
        setModelRevision((revision) => revision + 1);
        return true;
      } catch (error) {
        if (saveRequest.isCurrent(request)) {
          setModelError(error instanceof Error ? error.message : "metadata_update_failed");
        }
        return false;
      } finally {
        if (saveRequest.isCurrent(request)) setSavingId(null);
      }
    },
    [saveRequest],
  );

  return {
    datasetCatalog,
    datasetError,
    datasetLoading,
    modelCatalog,
    modelError,
    modelLoading,
    savingId,
    onDatasetPageChange: (offset) => setDatasetOffset(Math.max(0, offset)),
    onModelPageChange: (offset) => setModelOffset(Math.max(0, offset)),
    onRefreshDatasets: () => setDatasetRevision((revision) => revision + 1),
    onRefreshModels: () => setModelRevision((revision) => revision + 1),
    onSaveDatasetMetadata: saveDatasetMetadata,
    onSaveModelMetadata: saveModelMetadata,
  };
}
