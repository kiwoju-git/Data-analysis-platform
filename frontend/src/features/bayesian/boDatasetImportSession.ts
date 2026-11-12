import { createLatestRequestGuard } from "../../latestRequest";
import type { DatasetImportCreateRequest } from "../../api/types/boDatasetImport";

export function createDatasetImportSession() {
  const guard = createLatestRequestGuard();
  let attempt: DatasetImportCreateRequest | null = null;
  return {
    begin: guard.begin,
    current: guard.isCurrent,
    invalidate() { guard.cancel(); attempt = null; },
    remember(body: DatasetImportCreateRequest) { attempt = structuredClone(body); },
    retry: () => attempt === null ? null : structuredClone(attempt),
  };
}
