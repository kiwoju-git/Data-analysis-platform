import type { AnalysisFilterSnapshot } from "./analyses";
import type { BayesianStudyCreateRequest } from "./bayesian";
import type { MixedFactorRequest } from "./boMixed";
import type { DatasetImportPreflightResponse } from "./boDatasetSource";

export interface DatasetImportRequest {
  schema_version: 1;
  name: string;
  dataset_version_id: string;
  expected_schema_hash: string;
  factor_mappings: { column_id: string; factor: MixedFactorRequest }[];
  response_mappings: { column_id: string; response_id: string | null }[];
  objective: BayesianStudyCreateRequest["objective"];
  constraints: BayesianStudyCreateRequest["constraints"];
  filter_snapshot: AnalysisFilterSnapshot;
  missing_policy: "reject" | "complete_case";
}

export interface DatasetImportCreateRequest extends DatasetImportRequest {
  request_id: string;
  expected_preflight_sha256: string;
}

export type { DatasetImportPreflightResponse };
