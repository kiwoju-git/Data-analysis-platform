import type { AnalysisFilterSnapshot } from "./analyses";

export interface DatasetImportSource {
  dataset_id: string; dataset_version_id: string; schema_hash: string;
  canonical_sha256: string; raw_sha256: string; filter_sha256: string;
}
export interface DatasetImportCounts {
  n_total: number; n_filtered: number; n_missing: number; n_used: number;
  unique_coordinate_count: number; repeated_coordinate_count: number;
  conflicting_coordinate_count: number; warnings: string[];
}
export interface DatasetImportPreflightResponse extends DatasetImportCounts {
  schema_version: 1; source: DatasetImportSource; preflight_sha256: string;
}
export interface DatasetImportedInitialDesign extends DatasetImportCounts {
  policy: "dataset_observations_v1"; import_schema_version: 1 | 2;
  requested_size: number; generated_size: number; source: DatasetImportSource;
  source_row_indices: number[]; factor_columns: Record<string, string>;
  response_columns: Record<string, string>; missing_policy: "reject" | "complete_case";
  filter_snapshot: AnalysisFilterSnapshot; preflight_sha256: string;
  observations_sha256: string; request_id: string; request_sha256: string;
  runtime_provenance: Record<string, unknown>;
}
