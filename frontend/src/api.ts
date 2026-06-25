export interface HealthResponse {
  status: "ready";
  service: "datalab-studio-api";
  version: string;
}

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

export type AnalysisModuleId =
  | "exploration"
  | "hypothesis"
  | "categorical"
  | "regression"
  | "quality"
  | "doe";

export type MethodAvailability = "available" | "planned" | "disabled";

export type AnalysisExecutionMode = "inline" | "job";

export interface AnalysisModuleDescriptor {
  module_id: AnalysisModuleId;
  label_ko: string;
  label_en: string;
  order: number;
}

export interface AnalysisMethodDescriptor {
  method_id: string;
  method_version: string;
  module_id: AnalysisModuleId;
  label_ko: string;
  label_en: string;
  availability: MethodAvailability;
  execution_mode: AnalysisExecutionMode;
  requires_dataset: boolean;
  order: number;
  disabled_reason: string | null;
}

export interface AnalysisMethodListResponse {
  modules: AnalysisModuleDescriptor[];
  methods: AnalysisMethodDescriptor[];
}

export interface AnalysisRunRequest {
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  filter_snapshot: {
    expression_version: number;
    conditions: Array<{
      column_id: string;
      operator:
        | "is_missing"
        | "is_not_missing"
        | "eq"
        | "ne"
        | "gt"
        | "gte"
        | "lt"
        | "lte";
      value?: string | number | null;
    }>;
  };
  roles: Record<string, string>;
  options: Record<string, unknown>;
}

export interface AnalysisWarning {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
}

export interface AnalysisProvenance {
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  source_schema_hash: string | null;
  filter_snapshot_sha256?: string | null;
  row_snapshot_sha256?: string | null;
  row_count_total?: number | null;
  row_count_included?: number | null;
  app_version: string;
}

export interface DescriptiveColumnSummary {
  column_id: string;
  column_index: number;
  display_name: string;
  data_type: DatasetColumnResponse["data_type"];
  measurement_level: DatasetMeasurementLevel;
  role: DatasetColumnRole;
  unit: string | null;
  n_total: number;
  n_used: number;
  n_missing: number;
  n_non_numeric: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  warnings: string[];
}

export interface DescriptiveStatisticsResult {
  schema_version: number;
  summary_type: "descriptive_statistics";
  missing_policy: string;
  quartile_method: string;
  std_definition: string;
  columns: DescriptiveColumnSummary[];
}

export interface AnalysisResultEnvelope {
  analysis_id: string;
  method_id: string;
  method_version: string;
  dataset_version_id: string | null;
  status: "succeeded" | "failed" | "cancelled";
  warnings: AnalysisWarning[];
  provenance: AnalysisProvenance;
  result: DescriptiveStatisticsResult | Record<string, unknown> | null;
}

export function getApiBaseUrl(): string {
  const configuredBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl === "string" && configuredBaseUrl.length > 0) {
    return configuredBaseUrl;
  }
  return "http://127.0.0.1:8000";
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ready" &&
    candidate.service === "datalab-studio-api" &&
    typeof candidate.version === "string"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/health`, {
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error("health_check_failed");
  }

  const payload: unknown = await response.json();
  if (!isHealthResponse(payload)) {
    throw new Error("invalid_health_response");
  }

  return payload;
}

export async function uploadDataset(file: File): Promise<DatasetUploadResponse> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${getApiBaseUrl()}/api/v1/datasets`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_upload_failed"));
  }

  return (await response.json()) as DatasetUploadResponse;
}

export async function confirmDatasetParsing(
  datasetId: string,
  request: DatasetParsingConfirmationRequest,
): Promise<DatasetVersionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/datasets/${datasetId}/confirm-parsing`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "parsing_confirmation_failed"));
  }

  return (await response.json()) as DatasetVersionResponse;
}

export async function updateDatasetSchema(
  versionId: string,
  request: DatasetSchemaUpdateRequest,
): Promise<DatasetSchemaResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/dataset-versions/${versionId}/schema`, {
    method: "PATCH",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "schema_update_failed"));
  }

  return (await response.json()) as DatasetSchemaResponse;
}

export async function fetchRowsPreview(
  versionId: string,
  offset: number,
  limit: number,
): Promise<DatasetRowsPreviewResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(
    `${getApiBaseUrl()}/api/v1/dataset-versions/${versionId}/rows?${params.toString()}`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "rows_preview_failed"));
  }

  return (await response.json()) as DatasetRowsPreviewResponse;
}

export async function fetchDatasetProfile(versionId: string): Promise<DatasetProfileResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/dataset-versions/${versionId}/profile`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "dataset_profile_failed"));
  }

  return (await response.json()) as DatasetProfileResponse;
}

export async function fetchAnalysisMethods(
  signal?: AbortSignal,
): Promise<AnalysisMethodListResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/analysis-methods`, {
    headers: {
      Accept: "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_methods_failed"));
  }

  return (await response.json()) as AnalysisMethodListResponse;
}

export async function createAnalysisRun(
  request: AnalysisRunRequest,
): Promise<AnalysisResultEnvelope> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/analysis-runs`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await apiErrorCode(response, "analysis_run_failed"));
  }

  return (await response.json()) as AnalysisResultEnvelope;
}

async function apiErrorCode(response: Response, fallback: string): Promise<string> {
  try {
    const payload: unknown = await response.json();
    if (typeof payload === "object" && payload !== null) {
      const error = (payload as Record<string, unknown>).error;
      if (typeof error === "object" && error !== null) {
        const code = (error as Record<string, unknown>).code;
        if (typeof code === "string" && code.length > 0) {
          return code;
        }
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}
