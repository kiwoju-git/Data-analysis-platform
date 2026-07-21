import { useEffect, useRef, useState } from "react";

import {
  fetchDatasetVersions,
  type DatasetVersionCatalogItem,
  type DatasetVersionCatalogResponse,
} from "./api";
import { createLatestRequestGuard } from "./latestRequest";

export const activeDatasetCatalogPageSize = 20;

export interface DatasetVersionCatalogState {
  activeItem: DatasetVersionCatalogItem | null;
  catalog: DatasetVersionCatalogResponse | null;
  error: string | null;
  isLoading: boolean;
  isResolvingActiveItem: boolean;
  onPageChange: (offset: number) => void;
  onRefresh: () => void;
}

export function useDatasetVersionCatalogState(
  activeVersionId: string | null,
): DatasetVersionCatalogState {
  const [activeItem, setActiveItem] = useState<DatasetVersionCatalogItem | null>(null);
  const [catalog, setCatalog] = useState<DatasetVersionCatalogResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResolvingActiveItem, setIsResolvingActiveItem] = useState(false);
  const [offset, setOffset] = useState(0);
  const [refreshRevision, setRefreshRevision] = useState(0);
  const catalogRequest = useRef(createLatestRequestGuard()).current;
  const exactRequest = useRef(createLatestRequestGuard()).current;

  useEffect(() => {
    const request = catalogRequest.begin();
    exactRequest.cancel();
    setIsLoading(true);
    setError(null);
    fetchDatasetVersions(activeDatasetCatalogPageSize, offset)
      .then((response) => {
        if (!catalogRequest.isCurrent(request)) return;
        setCatalog(response);
      })
      .catch((fetchError) => {
        if (!catalogRequest.isCurrent(request)) return;
        setCatalog(null);
        setError(
          fetchError instanceof Error ? fetchError.message : "dataset_versions_fetch_failed",
        );
      })
      .finally(() => {
        if (catalogRequest.isCurrent(request)) setIsLoading(false);
      });
    return () => catalogRequest.cancel(request);
  }, [catalogRequest, exactRequest, offset, refreshRevision]);

  useEffect(() => {
    exactRequest.cancel();
    setIsResolvingActiveItem(false);
    if (activeVersionId === null) {
      setActiveItem(null);
      return;
    }
    const itemOnPage = catalog?.versions.find(
      (candidate) => candidate.version_id === activeVersionId,
    );
    if (itemOnPage !== undefined) {
      setActiveItem(itemOnPage);
      return;
    }
    if (catalog === null || catalog.total === 0) {
      setActiveItem(null);
      return;
    }

    const request = exactRequest.begin();
    setActiveItem(null);
    setIsResolvingActiveItem(true);
    void findCatalogItem(activeVersionId, catalog)
      .then((item) => {
        if (exactRequest.isCurrent(request)) setActiveItem(item);
      })
      .catch((fetchError) => {
        if (!exactRequest.isCurrent(request)) return;
        setError(
          fetchError instanceof Error ? fetchError.message : "dataset_version_lookup_failed",
        );
      })
      .finally(() => {
        if (exactRequest.isCurrent(request)) setIsResolvingActiveItem(false);
      });
    return () => exactRequest.cancel(request);
  }, [activeVersionId, catalog, exactRequest]);

  return {
    activeItem,
    catalog,
    error,
    isLoading,
    isResolvingActiveItem,
    onPageChange: (nextOffset) => setOffset(Math.max(0, nextOffset)),
    onRefresh: () => setRefreshRevision((revision) => revision + 1),
  };
}

async function findCatalogItem(
  versionId: string,
  currentPage: DatasetVersionCatalogResponse,
): Promise<DatasetVersionCatalogItem | null> {
  for (let offset = 0; offset < currentPage.total; offset += activeDatasetCatalogPageSize) {
    const page =
      offset === currentPage.offset
        ? currentPage
        : await fetchDatasetVersions(activeDatasetCatalogPageSize, offset);
    const item = page.versions.find((candidate) => candidate.version_id === versionId);
    if (item !== undefined) return item;
  }
  return null;
}
