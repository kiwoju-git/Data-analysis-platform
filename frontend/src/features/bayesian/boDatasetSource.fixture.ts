import type { DatasetImportedInitialDesign } from "../../api/types/boDatasetSource";

export function datasetImportedInitialFixture(count = 4): DatasetImportedInitialDesign {
  return {
    policy: "dataset_observations_v1", import_schema_version: 1,
    requested_size: count, generated_size: count, n_total: count + 2, n_filtered: 1,
    n_missing: 1, n_used: count, unique_coordinate_count: count,
    repeated_coordinate_count: 0, conflicting_coordinate_count: 0, warnings: [],
    source: { dataset_id: "33333333-3333-4333-8333-000000000001", dataset_version_id: "33333333-3333-4333-8333-000000000002",
      schema_hash: "a".repeat(64), canonical_sha256: "b".repeat(64), raw_sha256: "c".repeat(64), filter_sha256: "d".repeat(64) },
    source_row_indices: Array.from({ length: count }, (_, index) => index + 2),
    factor_columns: { x: "column-x", material: "column-material" }, response_columns: { yield: "column-yield", cost: "column-cost" },
    missing_policy: "complete_case", filter_snapshot: { expression_version: 1, conditions: [] },
    preflight_sha256: "e".repeat(64), observations_sha256: "f".repeat(64),
    request_id: "33333333-3333-4333-8333-000000000003", request_sha256: "1".repeat(64),
    runtime_provenance: { app_version: "test", python_version: "3.10.11" },
  };
}
