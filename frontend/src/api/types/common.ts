export interface HealthResponse {
  status: "ready";
  service: "datalab-studio-api";
  version: string;
}

export interface RuntimeCapabilities {
  asset_management: boolean;
  dataset_version_metadata: boolean;
  dataset_version_deletion: boolean;
  dataset_version_archiving: boolean;
  dataset_version_cascade_deletion: boolean;
  dataset_version_preserve_unverified_cleanup: boolean;
  regression_model_metadata: boolean;
  regression_model_deletion: boolean;
  dedicated_predict: boolean;
  dedicated_response_optimizer: boolean;
  bayesian_optimization: boolean;
}

export interface RuntimeInfoResponse {
  service: "datalab-studio-api";
  app_version: string;
  api_contract_version: number;
  metadata_schema_version: number;
  build_commit: string;
  capabilities: RuntimeCapabilities;
}

export interface WorkspaceSummaryResponse {
  visible_dataset_version_count: number;
  archived_dataset_version_count: number;
  regression_model_count: number;
  stored_analysis_count: number;
  export_report_count: number;
}
