export interface UploadWarning {
  code: string;
  message: string;
}

export interface DelimiterCandidate {
  delimiter: string;
  label: string;
  score: number;
}

export interface ParsingSuggestion {
  kind: "delimited_text" | "xlsx";
  encoding_candidates: string[];
  suggested_encoding: string | null;
  delimiter_candidates: DelimiterCandidate[];
  suggested_delimiter: string | null;
  quote_char: string | null;
  decimal: string;
  thousands: string | null;
  has_header: boolean;
  header_row: number;
  data_start_row: number;
  xlsx_requires_sheet_selection: boolean;
}

export interface DatasetUploadResponse {
  dataset_id: string;
  original_filename: string;
  size_bytes: number;
  sha256: string;
  detected_format: "csv" | "tsv" | "xlsx" | "delimited_text";
  parsing: ParsingSuggestion;
  warnings: UploadWarning[];
  next_step: "confirm_schema";
}

export interface PastedDatasetRequest {
  content: string;
  original_filename?: string | null;
}

export interface ConfirmedParsingOptions {
  kind: "delimited_text" | "xlsx";
  encoding: string | null;
  delimiter: string | null;
  quote_char: string | null;
  decimal: string;
  thousands: string | null;
  has_header: boolean;
  header_row: number;
  data_start_row: number | null;
  missing_tokens: string[];
  xlsx_sheet_name: string | null;
}

export interface DatasetParsingConfirmationRequest {
  parsing: ConfirmedParsingOptions;
  columns: [];
}

export type DatasetMeasurementLevel =
  | "unknown"
  | "continuous"
  | "ordinal"
  | "nominal"
  | "binary"
  | "count"
  | "datetime"
  | "id";

export type DatasetColumnRole =
  | "unspecified"
  | "id"
  | "feature"
  | "target"
  | "group"
  | "time"
  | "order"
  | "subgroup_id"
  | "part_id"
  | "operator_id"
  | "replicate_id"
  | "sample_size"
  | "opportunities"
  | "factor"
  | "response";

export interface DatasetColumnResponse {
  column_id: string;
  version_id: string;
  column_index: number;
  original_name: string;
  display_name: string;
  data_type: "integer" | "decimal" | "boolean" | "datetime" | "text";
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface DatasetArtifactResponse {
  artifact_id: string;
  version_id: string;
  kind: string;
  path: string;
  sha256: string;
  media_type: string;
  size_bytes: number;
  created_at: string;
}

export interface DatasetVersionResponse {
  version_id: string;
  dataset_id: string;
  version_number: number;
  row_count: number;
  column_count: number;
  schema_hash: string;
  created_at: string;
  source_sha256: string;
  parsing: ConfirmedParsingOptions;
  columns: DatasetColumnResponse[];
  canonical_artifact: DatasetArtifactResponse | null;
}

export interface DatasetVersionCatalogItem {
  version_id: string;
  dataset_id: string;
  original_filename: string;
  version_number: number;
  row_count: number;
  column_count: number;
  created_at: string;
  user_label: string | null;
  note: string | null;
  pinned: boolean;
  metadata_updated_at: string | null;
}

export interface DatasetVersionMetadataUpdateRequest {
  user_label?: string | null;
  note?: string | null;
  pinned?: boolean | null;
  expected_metadata_updated_at?: string | null;
}

export interface DatasetVersionMetadataResponse {
  version_id: string;
  user_label: string | null;
  note: string | null;
  pinned: boolean;
  metadata_updated_at: string;
}

export interface DatasetVersionDeletionCounts {
  dataset_version_count: 1;
  dataset_root_count: number;
  dataset_column_count: number;
  dataset_artifact_count: number;
  artifact_file_count: number;
  artifact_file_bytes: number;
  raw_upload_file_count: number;
  raw_upload_file_bytes: number;
  sibling_version_count: number;
  analysis_run_count: number;
  regression_model_count: number;
  prediction_source_count: number;
  prediction_target_count: number;
  analysis_export_count: number;
  job_count: number;
  attribute_control_limit_set_count: number;
  phase_2_analysis_count: number;
}

export interface DatasetVersionDeletionPreflightResponse {
  preflight_schema_version: 2;
  version_id: string;
  dataset_id: string;
  row_count: number;
  column_count: number;
  version_number: number;
  deletion_scope: "version_only" | "dataset_root";
  deletion_ready: boolean;
  dependency_ready: boolean;
  integrity_state: "verified" | "legacy_repairable" | "unverified";
  integrity_issue_codes: string[];
  verified_delete_ready: boolean;
  metadata_only_cleanup_ready: boolean;
  preserved_unverified_file_count: number;
  blockers: string[];
  counts: DatasetVersionDeletionCounts;
  deletion_manifest_sha256: string;
  verified_deletion_manifest_sha256: string | null;
  metadata_only_deletion_manifest_sha256: string | null;
}

export interface DatasetVersionDeleteResponse {
  deletion_schema_version: 2;
  version_id: string;
  dataset_id: string;
  deletion_scope: "version_only" | "dataset_root";
  deletion_manifest_sha256: string;
  deleted_at: string;
  deleted_counts: DatasetVersionDeletionCounts;
  deletion_mode:
    | "verified_files_and_metadata"
    | "metadata_only_preserve_unverified_files";
  preserved_unverified_file_count: number;
  cleanup_status:
    | "deleted"
    | "quarantined_pending_cleanup"
    | "metadata_removed_files_preserved";
}

export interface DatasetVersionCatalogResponse {
  offset: number;
  limit: number;
  total: number;
  returned: number;
  has_previous: boolean;
  has_next: boolean;
  versions: DatasetVersionCatalogItem[];
}

export interface DatasetColumnSchemaUpdate {
  column_id: string;
  display_name: string;
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
}

export interface DatasetSchemaUpdateRequest {
  columns: DatasetColumnSchemaUpdate[];
}

export interface DatasetSchemaResponse {
  version_id: string;
  dataset_id: string;
  schema_hash: string;
  columns: DatasetColumnResponse[];
}

export interface DatasetPreviewRow {
  row_index: number;
  values: Array<string | null>;
}

export interface DatasetRowsPreviewResponse {
  version_id: string;
  offset: number;
  limit: number;
  total_rows: number;
  returned_rows: number;
  columns: DatasetColumnResponse[];
  rows: DatasetPreviewRow[];
}

export interface DatasetProfileIssue {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
}

export interface DatasetDateTimeFormatCandidate {
  format: string;
  n_matched: number;
}

export interface DatasetDateTimeProfile {
  n_datetime: number;
  n_non_datetime: number;
  datetime_min: string | null;
  datetime_max: string | null;
  timezone_aware_count: number;
  timezone_naive_count: number;
  mixed_timezone_awareness: boolean;
  format_candidates: DatasetDateTimeFormatCandidate[];
}

export interface DatasetColumnProfile {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  n_total: number;
  n_present: number;
  n_missing: number;
  missing_rate: number;
  unique_count: number;
  unique_count_capped: boolean;
  n_numeric: number;
  n_non_numeric: number;
  numeric_min: number | null;
  numeric_max: number | null;
  numeric_mean: number | null;
  datetime_profile: DatasetDateTimeProfile | null;
  constant: boolean;
  warnings: DatasetProfileIssue[];
}

export interface DatasetProfileResponse {
  profile_schema_version: number;
  version_id: string;
  dataset_id: string;
  row_count: number;
  column_count: number;
  schema_hash: string;
  computed_at: string;
  unique_count_limit: number;
  canonical_artifact: DatasetArtifactResponse | null;
  profile_artifact: DatasetArtifactResponse | null;
  preflight: {
    estimated_memory_bytes: number;
    duplicate_row_count: number;
    duplicate_row_count_capped: boolean;
    duplicate_row_check_limit: number;
  };
  columns: DatasetColumnProfile[];
  warnings: DatasetProfileIssue[];
}
