import { createLatestRequestGuard } from "../../latestRequest";
import type { DatasetImportCreateRequest } from "../../api/types/boDatasetImport";
import type { MixtureDatasetCreateRequest } from "../../api/boMixture";

export function createDatasetImportSession<T extends DatasetImportCreateRequest | MixtureDatasetCreateRequest = DatasetImportCreateRequest>() {
  const guard = createLatestRequestGuard();
  let attempt: T | null = null;
  return {
    begin: guard.begin,
    current: guard.isCurrent,
    invalidate() { guard.cancel(); attempt = null; },
    remember(body: T) { attempt = structuredClone(body); },
    retry: () => attempt === null ? null : structuredClone(attempt),
  };
}
